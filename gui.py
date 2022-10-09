#!/usr/bin/env python3

import re
import sys
from threading import Thread

import darkdetect
import hid
from PyQt5.QtCore import *
from PyQt5.QtGui import *
from PyQt5.QtWidgets import *

import lib27gn950
from helpers import read_config
from mqtt import MQTT


# https://pypi.org/project/hid/
# https://github.com/apmorton/pyhidapi


class Gui(QWidget):
    def __init__(self):
        super().__init__()
        self.config = read_config()
        self.devs = []

        self.m = MQTT(
            self.devs,
            self.config["mqtt_host"],
            self.config["mqtt_port"],
            self.config["mqtt_availability_topic"],
            self.config["mqtt_command_topic"],
            self.config["mqtt_contact_topic"],
            self.config["mqtt_user"],
            self.config["mqtt_password"],
        )
        # self.m.connect()
        # spawn_thread(self.m)

        self.init_ui()

    def _mqtt(self, checked):
        if not checked:
            self.m.disconnect()
        else:
            self.m.connect()

    def init_ui(self):
        self.setWindowTitle("27g950controller")

        mainLayout = QVBoxLayout(self)

        self.selectionMqttLayout = QHBoxLayout(self)

        self.selectionbuttonslayout = QHBoxLayout(self)
        self.selectionbuttonslayout.addWidget(QLabel("<b>Select monitors: </b>"))
        mainLayout.addLayout(self.selectionbuttonslayout)

        mainLayout.addWidget(QLabel(""))

        powerbuttonslayout = QGridLayout(self)
        powerbuttonslayout.addWidget(QLabel("<b>Power</b>"), 0, 0, 1, 2)
        self.selectionMqttLayout.addWidget(QLabel("<b>MQTT: </b>"))
        x = QCheckBox()
        x.setCheckState(0)
        if self.config["mqtt"]:
            spawn_thread(self.m, start=True)
            x.setCheckState(2)
        else:
            spawn_thread(self.m, start=False)

        x.stateChanged.connect(lambda checked: spawn_thread(self.m, start=checked))
        self.selectionMqttLayout.addWidget(x)
        # todo: create another qt thread that will bind to checkbox
        # Thread(target=self._mqtt, args=(x.checkState(),)).start()
        # self._mqtt(x.checkState())

        mainLayout.addLayout(self.selectionbuttonslayout)
        mainLayout.addLayout(self.selectionMqttLayout)

        mainLayout.addWidget(QLabel(""))

        powerbuttonslayout = QGridLayout(self)
        powerbuttonslayout.addWidget(QLabel("<b>Power</b>"), 0, 0, 1, 2)
        x = QPushButton("Turn off")
        x.clicked.connect(self.turn_off)
        powerbuttonslayout.addWidget(x, 1, 0)
        x = QPushButton("Turn on")
        x.clicked.connect(self.turn_on)
        powerbuttonslayout.addWidget(x, 1, 1)
        mainLayout.addLayout(powerbuttonslayout)

        mainLayout.addWidget(QLabel(""))

        brightnessbuttonslayout = QGridLayout(self)
        brightnessbuttonslayout.addWidget(QLabel("<b>Brightness</b>"), 0, 0, 1, 6)
        for i in range(1, 13):
            x = QPushButton(str(i))
            x.clicked.connect(lambda _, i=i: self.set_brightness(i))
            row = 1 + i // 7
            col = i - 1 - (6 if i > 6 else 0)
            brightnessbuttonslayout.addWidget(x, row, col)
        mainLayout.addLayout(brightnessbuttonslayout)

        mainLayout.addWidget(QLabel(""))

        configbuttonslayout = QGridLayout(self)
        configbuttonslayout.addWidget(QLabel("<b>Lighting mode</b>"), 0, 0, 1, 4)
        for i in range(4):
            x = QPushButton(f"Color {i+1}")
            x.clicked.connect(lambda _, i=i: self.set_static_color(i + 1))
            configbuttonslayout.addWidget(x, 1, i)
        x = QPushButton("Peaceful")
        x.clicked.connect(self.set_peaceful_color)
        configbuttonslayout.addWidget(x, 2, 0, 1, 2)
        x = QPushButton("Dynamic")
        x.clicked.connect(self.set_dynamic_color)
        configbuttonslayout.addWidget(x, 2, 2, 1, 2)
        mainLayout.addLayout(configbuttonslayout)

        mainLayout.addWidget(QLabel(""))

        editbuttonsentrylayout = QHBoxLayout(self)
        editbuttonsbuttonslayout = QHBoxLayout(self)
        x = QLabel("Enter new color: ")
        editbuttonsentrylayout.addWidget(x)
        self.colorInputBox = QLineEdit("27e5ff")
        self.colorInputBox.setFixedWidth(150)
        self.colorInputBox.setAlignment(Qt.AlignCenter)
        font = QFont()
        font.setFamily("Monospace")
        font.setStyleHint(QFont.TypeWriter)
        self.colorInputBox.setFont(font)
        self.colorInputBox.textChanged.connect(self.validate_new_color)
        editbuttonsentrylayout.addWidget(self.colorInputBox)
        self.colorValidationOutputBox = QLabel("valid")
        self.colorValidationOutputBox.setAlignment(Qt.AlignRight)
        editbuttonsentrylayout.addWidget(self.colorValidationOutputBox)
        for i in range(4):
            x = QPushButton(f"Set {i+1}")
            x.clicked.connect(lambda _, i=i: self.set_color(i + 1))
            editbuttonsbuttonslayout.addWidget(x)
        editbuttonslayout = QVBoxLayout(self)

        editbuttonslayout.addWidget(QLabel("<b>Edit static colors</b>"))
        editbuttonslayout.addLayout(editbuttonsentrylayout)
        editbuttonslayout.addLayout(editbuttonsbuttonslayout)
        mainLayout.addLayout(editbuttonslayout)

    def init_monitors(self):
        monitors = lib27gn950.find_monitors()
        if not monitors:
            for item in self.layout().children():
                self.layout().removeItem(item)
            self.layout().addWidget(QLabel("No monitors found"))
            return

        for monitor in monitors:
            self.devs.append(hid.Device(path=monitor["path"]))

        self.selection = list(range(len(self.devs)))

        for i in self.selection:
            x = QCheckBox(str(i + 1))
            x.setCheckState(2)
            x.stateChanged.connect(
                lambda checked, i=i: self.update_selection(i, checked)
            )
            self.selectionbuttonslayout.addWidget(x)

    def cleanup(self):
        if hasattr(self, "devs"):
            for dev in self.devs:
                dev.close()

    def is_valid_color(self, color):
        return re.match("^[0-9a-f]{6}$", color)

    def validate_new_color(self, text):
        s = "valid" if self.is_valid_color(text.lower()) else "invalid"
        self.colorValidationOutputBox.setText(s)

    def update_selection(self, monitor_num, checked):
        if checked == 0:
            self.selection.remove(monitor_num)
        elif checked == 2:
            self.selection.append(monitor_num)

    def send_command(self, cmd):
        devs = []
        for i in self.selection:
            devs.append(self.devs[i])
        lib27gn950.send_command(cmd, devs)

    def turn_on(self):
        cmd = lib27gn950.control_commands["turn_on"]
        self.send_command(cmd)

    def turn_off(self):
        cmd = lib27gn950.control_commands["turn_off"]
        self.send_command(cmd)

    def set_static_color(self, color):
        cmd = lib27gn950.control_commands["color" + str(color)]
        self.send_command(cmd)

    def set_peaceful_color(self):
        cmd = lib27gn950.control_commands["color_peaceful"]
        self.send_command(cmd)

    def set_dynamic_color(self):
        cmd = lib27gn950.control_commands["color_dynamic"]
        self.send_command(cmd)

    def set_brightness(self, brt):
        cmd = lib27gn950.brightness_commands[brt]
        self.send_command(cmd)

    def set_color(self, slot):
        color = self.colorInputBox.text().lower()
        if not self.is_valid_color(color):
            return
        cmd = lib27gn950.get_set_color_command(slot, color)
        self.send_command(cmd)


def spawn_thread(m, start=False):
    if start:
        t = Thread(target=m.connect)
        t.start()
    else:
        m.disconnect()
        pass


class Tray(QSystemTrayIcon):
    def __init__(self, app, gui):
        super().__init__()
        self.app = app
        self.gui = gui

        if darkdetect.isLight():
            icon = QIcon("icon-black.png")
        else:
            icon = QIcon("icon-white.png")

        self.setIcon(icon)
        self.setVisible(True)

        self.activated.connect(self.clicked)

    def clicked(self, reason, *args):
        match reason:
            case QSystemTrayIcon.Trigger:
                self.activate_window()
            case QSystemTrayIcon.Context:
                pass

    def activate_window(self):
        self.gui.show()
        self.gui.window().raise_()


app = QApplication(sys.argv)
app.setQuitOnLastWindowClosed(False)

try:
    x = Gui()
    tray = Tray(app, x)
    menu = QMenu()

    # Add a Quit option to the menu.
    # todo: quit doesn't work properly when mqtt is on
    quit = QAction("Quit")
    quit.triggered.connect(app.quit)
    menu.addAction(quit)

    tray.setContextMenu(menu)

    x.init_monitors()
    x.show()
    sys.exit(app.exec_())

finally:
    if "x" in locals():
        x.cleanup()
