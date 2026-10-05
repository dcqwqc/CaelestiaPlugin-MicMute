import QtQuick
import Caelestia.Config
import qs.components
import qs.services

Item {
    id: root

    implicitWidth: icon.implicitHeight + Tokens.padding.small
    implicitHeight: icon.implicitHeight

    MaterialIcon {
        id: icon
        anchors.centerIn: parent
        animate: true
        text: Audio.sourceMuted ? "mic_off" : "mic"
        color: Audio.sourceMuted ? Colours.palette.m3error : Colours.palette.m3onSurface
        fontStyle: Tokens.font.icon.small
        fill: Audio.sourceMuted ? 1 : 0
    }
}
