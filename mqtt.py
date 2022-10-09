from dataclasses import dataclass
from sys import exit

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

    def __post_init__(self):
        self.client = mqtt.Client()

    def connect(self):
        self.client.on_connect = self.on_connect
        self.client.on_message = self.on_message
        self.client.on_disconnect = self.on_disconnect
        self.client.will_set(self.mqtt_availability_topic, "offline", 0, False)

        self.client.username_pw_set(self.mqtt_user, self.mqtt_password)

        try:
            self.client.connect(self.host, self.port, 60)
        except TimeoutError:
            print("Connection error")
            exit(0)

        # client.publish(self.mqtt_contact_topic, 'off', retain=True)
        self.client.loop_forever()

    def disconnect(self):
        self.client.publish(self.mqtt_contact_topic, "off")
        self.client.publish(self.mqtt_availability_topic, "offline")
        self.client.disconnect()

    def on_connect(self, client, userdata, flags, rc):
        print("Connected with result code " + str(rc))

        client.subscribe(f"{self.mqtt_command_topic}/#")
        client.publish(self.mqtt_availability_topic, "online")

    def on_message(self, client, userdata, msg):
        match msg.payload.decode():
            case "on":
                bias.send_command(bias.control_commands["turn_on"], self.devs)
                client.publish(self.mqtt_contact_topic, "on")
            case "off":
                bias.send_command(bias.control_commands["turn_off"], self.devs)
                client.publish(self.mqtt_contact_topic, "off")

    def on_disconnect(self, client, userdata, rc):
        print("Connection error")
        bias.send_command(bias.control_commands["turn_off"], self.devs)
