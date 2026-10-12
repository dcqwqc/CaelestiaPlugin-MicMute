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

## Shared Hotkeys action

This plugin publishes the stable action ID plugin.micmute.toggle through
hotkeys.actions.json for dcqwqc/CaelestiaPlugin-Hotkeys. The action toggles
the default microphone mute through PipeWire. The existing user-configurable
Right Shift hotkey and push-to-talk listener are preserved; the shared
registry does not yet take ownership of that independent evdev binding.
