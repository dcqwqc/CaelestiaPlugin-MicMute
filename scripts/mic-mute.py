#!/usr/bin/env python3
"""Global microphone mute / push-to-talk helper for Caelestia MicMute."""

from __future__ import annotations

import argparse
import math
import os
import re
import selectors
import signal
import struct
import subprocess
import sys
import time
import wave
from pathlib import Path

EV_KEY = 0x01
INPUT_EVENT = struct.Struct("llHHi")

KEY_CODES = {
    "Right Shift": 54,
    "Left Shift": 42,
    "Right Ctrl": 97,
    "Left Ctrl": 29,
    "Right Alt": 100,
    "Left Alt": 56,
    "F10": 68,
    "F11": 87,
    "F12": 88,
}

VIRTUAL_MARKERS = (
    "virtual",
    "ydotool",
    "uinput",
    "libvirtualhid",
)


def run(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(args, text=True, capture_output=True, check=False)


def input_sources() -> list[str]:
    result = run("pactl", "list", "short", "sources")
    if result.returncode != 0:
        return []
    sources: list[str] = []
    for line in result.stdout.splitlines():
        fields = line.split("\t")
        if len(fields) < 2:
            continue
        name = fields[1].strip()
        if not name or name.endswith(".monitor"):
            continue
        sources.append(name)
    return sources


def source_muted(name: str) -> bool:
    result = run("pactl", "get-source-mute", name)
    return result.returncode == 0 and "yes" in result.stdout.lower()


def all_muted() -> bool:
    sources = input_sources()
    if not sources:
        result = run("wpctl", "get-volume", "@DEFAULT_AUDIO_SOURCE@")
        return "[MUTED]" in result.stdout.upper()
    return all(source_muted(name) for name in sources)


def set_all_muted(muted: bool) -> bool:
    sources = input_sources()
    value = "1" if muted else "0"
    ok = False

    for name in sources:
        result = run("pactl", "set-source-mute", name, value)
        ok = ok or result.returncode == 0

    if not sources:
        result = run("wpctl", "set-mute", "@DEFAULT_AUDIO_SOURCE@", value)
        ok = result.returncode == 0

    return ok


def cache_dir() -> Path:
    base = Path(os.environ.get("XDG_CACHE_HOME", Path.home() / ".cache"))
    path = base / "caelestia-micmute"
    path.mkdir(parents=True, exist_ok=True)
    return path


def synth_sound(kind: str) -> Path:
    path = cache_dir() / f"{kind}.wav"
    if path.exists():
        return path

    sample_rate = 48000
    first, second = ((760.0, 500.0) if kind == "mute" else (500.0, 760.0))
    segments = ((first, 0.055), (second, 0.075))
    samples: list[int] = []

    for frequency, duration in segments:
        count = max(1, int(sample_rate * duration))
        for index in range(count):
            t = index / sample_rate
            fade_in = min(1.0, index / max(1, int(sample_rate * 0.008)))
            fade_out = min(1.0, (count - index - 1) / max(1, int(sample_rate * 0.018)))
            envelope = min(fade_in, fade_out)
            value = 0.11 * envelope * math.sin(2.0 * math.pi * frequency * t)
            samples.append(int(max(-1.0, min(1.0, value)) * 32767))

    with wave.open(str(path), "wb") as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(sample_rate)
        wav.writeframes(struct.pack("<" + "h" * len(samples), *samples))
    return path


def play_sound(kind: str, enabled: bool) -> None:
    if not enabled:
        return
    try:
        sound = synth_sound(kind)
        subprocess.Popen(
            ["paplay", str(sound)],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            start_new_session=True,
        )
    except Exception:
        pass


def mute(sounds: bool, announce: bool = True) -> None:
    if all_muted():
        return
    if set_all_muted(True) and announce:
        play_sound("mute", sounds)


def unmute(sounds: bool, announce: bool = True) -> None:
    if not all_muted():
        return
    if set_all_muted(False) and announce:
        play_sound("unmute", sounds)


def toggle(sounds: bool) -> None:
    if all_muted():
        if set_all_muted(False):
            play_sound("unmute", sounds)
    else:
        if set_all_muted(True):
            play_sound("mute", sounds)


def keyboard_device_paths() -> list[str]:
    try:
        raw = Path("/proc/bus/input/devices").read_text(errors="ignore")
    except OSError:
        return []

    paths: list[str] = []
    for block in raw.split("\n\n"):
        handlers_match = re.search(r"^H:\s+Handlers=(.+)$", block, re.MULTILINE)
        if not handlers_match:
            continue
        handlers = handlers_match.group(1)
        if "kbd" not in handlers or "sysrq" not in handlers:
            continue

        name_match = re.search(r'^N:\s+Name="(.*)"$', block, re.MULTILINE)
        name = name_match.group(1) if name_match else ""
        lower = name.lower()
        if any(marker in lower for marker in VIRTUAL_MARKERS):
            continue

        event_match = re.search(r"\bevent\d+\b", handlers)
        if not event_match:
            continue
        path = f"/dev/input/{event_match.group(0)}"
        if os.path.exists(path) and os.access(path, os.R_OK):
            paths.append(path)

    return sorted(set(paths))


class KeyboardReader:
    def __init__(self) -> None:
        self.selector = selectors.DefaultSelector()
        self.files: dict[int, tuple[object, str]] = {}
        self.buffers: dict[int, bytes] = {}

    def open_devices(self) -> None:
        wanted = set(keyboard_device_paths())
        existing = {path for _, path in self.files.values()}

        for fd, (file_obj, path) in list(self.files.items()):
            if path in wanted:
                continue
            try:
                self.selector.unregister(file_obj)
            except Exception:
                pass
            try:
                file_obj.close()
            except Exception:
                pass
            self.files.pop(fd, None)
            self.buffers.pop(fd, None)

        for path in sorted(wanted - existing):
            try:
                file_obj = open(path, "rb", buffering=0)
                os.set_blocking(file_obj.fileno(), False)
                self.selector.register(file_obj, selectors.EVENT_READ)
                self.files[file_obj.fileno()] = (file_obj, path)
                self.buffers[file_obj.fileno()] = b""
            except OSError:
                continue

    def events(self, timeout: float = 1.0):
        for key, _ in self.selector.select(timeout):
            file_obj = key.fileobj
            fd = file_obj.fileno()
            try:
                chunk = os.read(fd, INPUT_EVENT.size * 64)
            except BlockingIOError:
                continue
            except OSError:
                continue

            if not chunk:
                continue

            data = self.buffers.get(fd, b"") + chunk
            usable = len(data) - (len(data) % INPUT_EVENT.size)
            self.buffers[fd] = data[usable:]

            for offset in range(0, usable, INPUT_EVENT.size):
                _, _, event_type, code, value = INPUT_EVENT.unpack_from(data, offset)
                yield event_type, code, value

    def close(self) -> None:
        for file_obj, _ in list(self.files.values()):
            try:
                self.selector.unregister(file_obj)
            except Exception:
                pass
            try:
                file_obj.close()
            except Exception:
                pass
        self.files.clear()
        self.buffers.clear()
        self.selector.close()


def daemon(key_name: str, mode: str, sounds: bool) -> int:
    if key_name not in KEY_CODES:
        print(f"Unsupported hotkey: {key_name}", file=sys.stderr)
        return 2

    key_code = KEY_CODES[key_name]
    reader = KeyboardReader()
    reader.open_devices()
    running = True
    last_scan = 0.0
    held = False

    def stop(*_args) -> None:
        nonlocal running
        running = False

    signal.signal(signal.SIGTERM, stop)
    signal.signal(signal.SIGINT, stop)

    if mode == "push-to-talk":
        mute(sounds=False, announce=False)

    try:
        while running:
            now = time.monotonic()
            if now - last_scan >= 5.0:
                reader.open_devices()
                last_scan = now

            if not reader.files:
                time.sleep(0.5)
                continue

            for event_type, code, value in reader.events(timeout=0.8):
                if event_type != EV_KEY or code != key_code:
                    continue

                if mode == "toggle":
                    if value == 1:
                        toggle(sounds)
                    continue

                if value == 1 and not held:
                    held = True
                    unmute(sounds)
                elif value == 0 and held:
                    held = False
                    mute(sounds)
    finally:
        if mode == "push-to-talk":
            mute(sounds=False, announce=False)
        reader.close()

    return 0


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=("daemon", "toggle", "mute", "unmute", "status"))
    parser.add_argument("--key", default="Right Shift")
    parser.add_argument("--mode", choices=("toggle", "push-to-talk"), default="toggle")
    parser.add_argument("--sounds", choices=("0", "1"), default="1")
    args = parser.parse_args()
    sounds = args.sounds == "1"

    if args.command == "daemon":
        return daemon(args.key, args.mode, sounds)
    if args.command == "toggle":
        toggle(sounds)
        return 0
    if args.command == "mute":
        mute(sounds)
        return 0
    if args.command == "unmute":
        unmute(sounds)
        return 0

    print("muted" if all_muted() else "live")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
