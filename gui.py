#!/usr/bin/env python3
import logging
import os
import re
import sys
from math import ceil
from threading import Thread

import darkdetect
import hid
from PyQt5.QtCore import *
from PyQt5.QtGui import *
from PyQt5.QtWidgets import *

import lib27gn950
from helpers import Config
from mqtt import MQTT

log = logging.getLogger(__name__)

# https://pypi.org/project/hid/
# https://github.com/apmorton/pyhidapi


class Gui(QWidget):
    def __init__(self):
        super().__init__()
        self.config = Config()
        self.devs = []
        self.is_mqtt_available = hasattr(self.config, "mqtt")
        if self.is_mqtt_available:
            self.m = MQTT(
                self.devs,
                self.config.mqtt_host,
                self.config.mqtt_port,
                self.config.mqtt_availability_topic,
                self.config.mqtt_command_topic,
                self.config.mqtt_contact_topic,
                self.config.mqtt_user,
                self.config.mqtt_password,
                self.config.mqtt_tls,
            )

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
        # ugly
        if self.is_mqtt_available:
            if self.config.mqtt:
                self.start_mqtt(x)
                x.setCheckState(2)
            else:
                self.stop_mqtt()
        else:
            x.setDisabled(True)

        x.stateChanged.connect(
            lambda checked: self.start_mqtt(x) if checked == 2 else self.stop_mqtt()
        )
        self.selectionMqttLayout.addWidget(x)

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

        mainLayout.addWidget(QLabel("Brightness"))
        groupBox = QGroupBox()

        slider = QSlider(Qt.Horizontal)
        slider.setFocusPolicy(Qt.StrongFocus)
        slider.setTickPosition(QSlider.TicksBothSides)
        slider.setTickInterval(10)
        slider.setSingleStep(1)

        vbox = QVBoxLayout()
        vbox.addWidget(slider)
        groupBox.setLayout(vbox)

        mainLayout.addWidget(groupBox)
        slider.valueChanged.connect(self._on_slider)

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
        if brt < 1 or brt > 12:
            self.turn_off()
        else:
            self.turn_on()
            cmd = lib27gn950.brightness_commands[brt]
            self.send_command(cmd)

    def set_color(self, slot):
        color = self.colorInputBox.text().lower()
        if not self.is_valid_color(color):
            return
        cmd = lib27gn950.get_set_color_command(slot, color)
        self.send_command(cmd)

    def _on_slider(self, value):
        brightness = value * 0.12
        self.set_brightness(ceil(brightness))

    def start_mqtt(self, checkbox):
        if not self.is_mqtt_available:
            return

        t = Thread(
            target=self.m.connect, args=(lambda e: self._on_mqtt_error(e, checkbox),)
        )
        t.start()

    def stop_mqtt(self):
        if not self.is_mqtt_available:
            return
        self.m.disconnect()

    @staticmethod
    def _on_mqtt_error(e, checkbox):
        log.error(e)
        checkbox.setCheckState(1)
        checkbox.setDisabled(True)
        # QErrorMessage().showMessage("Connection error")  # doesn't work


class Tray(QSystemTrayIcon):
    def __init__(self, app, gui):
        super().__init__()
        self.app = app
        self.gui = gui

        basedir = os.path.dirname(__file__)
        if darkdetect.isLight():
            icon = QIcon(os.path.join(basedir, "icon-black.png"))
        else:
            icon = QIcon(os.path.join(basedir, "icon-white.png"))

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

    def quit_action(self):
        self.gui.stop_mqtt()
        self.app.quit()


app = QApplication(sys.argv)
app.setQuitOnLastWindowClosed(False)

try:
    x = Gui()
    tray = Tray(app, x)
    menu = QMenu()

    quit = QAction("Quit")
    quit.triggered.connect(tray.quit_action)
    menu.addAction(quit)
    tray.setContextMenu(menu)

    x.init_ui()
    x.init_monitors()
    x.show()
    sys.exit(app.exec_())

finally:
    if "x" in locals():
        x.cleanup()
