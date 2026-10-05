import QtQuick
import Quickshell.Io
import Caelestia.Plugins
import qs.utils

Item {
    id: root

    property SettingsObject settings: null
    readonly property string helper: Paths.toLocalFile(Qt.resolvedUrl("scripts/mic-mute.py"))
    readonly property bool wanted: settings?.enabled ?? true

    visible: false
    implicitWidth: 0
    implicitHeight: 0

    function daemonArgs(): var {
        const mode = String(settings?.mode ?? "Toggle mute") === "Push to talk"
            ? "push-to-talk"
            : "toggle";
        return [
            "python3",
            helper,
            "daemon",
            "--key", String(settings?.hotkey ?? "Right Shift"),
            "--mode", mode,
            "--sounds", (settings?.playSounds ?? true) ? "1" : "0"
        ];
    }

    function restartDaemon(): void {
        daemon.running = false;
        restartTimer.restart();
    }

    onSettingsChanged: restartDaemon()
    onWantedChanged: restartDaemon()
    Component.onCompleted: restartDaemon()

    Connections {
        target: root.settings
        function onChanged(): void { root.restartDaemon(); }
    }

    Timer {
        id: restartTimer
        interval: 180
        repeat: false
        onTriggered: {
            if (!root.wanted)
                return;
            daemon.command = root.daemonArgs();
            daemon.running = true;
        }
    }

    Timer {
        id: crashRestart
        interval: 1200
        repeat: false
        onTriggered: {
            if (root.wanted && !daemon.running) {
                daemon.command = root.daemonArgs();
                daemon.running = true;
            }
        }
    }

    Process {
        id: daemon
        running: false
        onExited: code => {
            if (root.wanted && !restartTimer.running)
                crashRestart.restart();
        }
    }
}
