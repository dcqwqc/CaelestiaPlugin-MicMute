# CaelestiaPlugin-MicMute

A small Caelestia plugin that turns a keyboard key into a global microphone control.

## Defaults

- Hotkey: **Right Shift**
- Mode: **Toggle mute**
- Feedback: short mute/unmute sounds
- Indicator: mic icon in the Caelestia bar; red crossed mic while muted

## Modes

- **Toggle mute** — press the hotkey once to mute every real audio input source, press again to unmute.
- **Push to talk** — inputs stay muted until the hotkey is held.

The helper uses Linux evdev directly (no Python dependency) and PipeWire/PulseAudio-compatible pactl for microphone state.
