import time
from dataclasses import dataclass

import certifi
import paho.mqtt.client as mqtt

import lib27gn950 as bias


@dataclass
class MQTT:
    devs: list
    host: str
    port: int
    mqtt_availability_topic: str
    mqtt_command_topic: str
    mqtt_contact_topic: str
    mqtt_user: str
    mqtt_password: str
    mqtt_tls: str

    def __post_init__(self):
        self.client = mqtt.Client()

    def connect(self, mqtt_checkbox):
        self.mqtt_checkbox = mqtt_checkbox
        self.client.on_connect = self.on_connect
        self.client.on_message = self.on_message
        self.client.on_disconnect = self.on_disconnect
        self.client.will_set(self.mqtt_availability_topic, "offline", 0, False)
        # https://stackoverflow.com/questions/70110392/mqtt-tls-certificate-verify-failed-self-signed-certificate
        if self.mqtt_tls:
            try:
                self.client.tls_set(certifi.where())
            except ValueError:
                pass

        self.client.username_pw_set(self.mqtt_user, self.mqtt_password)

        while True:
            if mqtt_checkbox.checkState() == 0:
                return

            try:
                if not self.client.is_connected():
                    self.client.connect(self.host, self.port, 60)
                    self.client.loop_forever()
                else:
                    return

            except Exception as e:
                print(e)

                mqtt_checkbox.setDisabled(True)
                time.sleep(5)

    def disconnect(self):
        print("Disconnect")

        self.client.publish(self.mqtt_availability_topic, "offline")
        self.client.disconnect()

    def on_connect(self, client, userdata, flags, rc):
        print("Connected with result code " + str(rc))

        client.subscribe(f"{self.mqtt_command_topic}/#")
        client.publish(self.mqtt_availability_topic, "online")
        self.mqtt_checkbox.setDisabled(False)

    def on_message(self, client, userdata, msg):
        match msg.payload.decode():
            case "on":
                bias.send_command(bias.control_commands["turn_on"], self.devs)
                client.publish(self.mqtt_contact_topic, "on")
            case "off":
                bias.send_command(bias.control_commands["turn_off"], self.devs)
                client.publish(self.mqtt_contact_topic, "off")

    def on_disconnect(self, client, userdata, rc):
        bias.send_command(bias.control_commands["turn_off"], self.devs)
        self.mqtt_checkbox.setDisabled(True)
