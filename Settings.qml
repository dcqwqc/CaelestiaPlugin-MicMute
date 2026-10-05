import Caelestia.Plugins

SettingsObject {
    id: root

    property bool enabled: true
    SettingMeta on enabled {
        label: "Microphone hotkey"
        description: "Enable the global microphone mute hotkey."
        icon: "mic_off"
        inputType: SettingMeta.Switch
    }

    property string mode: "Toggle mute"
    SettingMeta on mode {
        label: "Hotkey mode"
        description: "Toggle mute switches state on every press. Push to talk stays muted except while the key is held."
        icon: "keyboard_voice"
        inputType: SettingMeta.SplitButton
        options: ["Toggle mute", "Push to talk"]
    }

    property string hotkey: "Right Shift"
    SettingMeta on hotkey {
        label: "Hotkey"
        description: "Global key used for microphone control. Default: Right Shift."
        icon: "keyboard"
        inputType: SettingMeta.SplitButton
        options: ["Right Shift", "Left Shift", "Right Ctrl", "Left Ctrl", "Right Alt", "Left Alt", "F10", "F11", "F12"]
    }

    property bool playSounds: true
    SettingMeta on playSounds {
        label: "Mute sounds"
        description: "Play a short descending sound when muted and an ascending sound when unmuted."
        icon: "music_note"
        inputType: SettingMeta.Switch
    }
}
