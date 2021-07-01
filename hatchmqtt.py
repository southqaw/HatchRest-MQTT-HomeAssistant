import paho.mqtt.client as mqtt
import json
import configparser
import argparse
import hatchrestbluepy
from hatchrestbluepy.constants import HatchRestSound
from typing import List, Dict
import time


MQTT_CONFIG = "/opt/HatchMQTT/mqtt.ini"
JSON_LOC = "/opt/HatchMQTT"


class HatchMQTT:
    def __init__(self, addr: str, topics: List):
        self.device = hatchrestbluepy.HatchRest(addr=addr)
        self._parse_topics(topics)

    def _parse_topics(self, topics: List) -> None:
        self.configs = {'light': topics['light_config'],
                        'sound': topics['sound_config'],
                        'switch': topics['switch_config']
                        }
        self.states = {'light': topics['light_state'],
                       'sound': topics['sound_state'],
                       'switch': topics['switch_state'],
                       'sound_vol': topics['sound_vol_state']
                       }
        self.cmds = {'light': topics['light_cmd'],
                     'sound': topics['sound_cmd'],
                     'switch': topics['switch_cmd'],
                     'sound_vol': topics['sound_vol_cmd']
                     }

    def generate_light_schema(self) -> Dict:
        schema = {}
        if self.device.brightness > 0:
            schema['state'] = "ON"
        else:
            schema['state'] = "OFF"
        schema['brightness'] = self.device.brightness
        schema['color'] = {}
        schema['color']['r'] = self.device.color[0]
        schema['color']['g'] = self.device.color[1]
        schema['color']['b'] = self.device.color[2]
        schema['color_mode'] = "rgb"
        return schema

    def set_light(self, schema) -> None:
        schema = json.loads(schema)
        if schema['state'] == 'OFF':
            self.device.set_brightness(0)
            return
        if 'brightness' in schema and 'color' in schema:
            self.device.set_light(schema['color']['r'],
                                  schema['color']['g'],
                                  schema['color']['b'],
                                  schema['brightness'])
        else:
            if 'brightness' in schema:
                self.device.set_brightness(schema['brightness'])
            if 'color' in schema:
                self.device.set_color(schema['color']['r'],
                                      schema['color']['g'],
                                      schema['color']['b'])
        # Default to 50% brightness
        if self.device.brightness == 0:
            self.device.set_brightness(127)


def ha_discover(client: mqtt.Client, userdata: HatchMQTT) -> None:
    """
    Open 3 json files, send contents to the correct topics
    """
    configs = [
               ('{}/lightconfig.json'.format(JSON_LOC), userdata.configs['light']),
               ('{}/soundconfig.json'.format(JSON_LOC), userdata.configs['sound']),
               ('{}/switchconfig.json'.format(JSON_LOC), userdata.configs['switch'])
              ]
    for config in configs:
        with open(config[0], 'r') as f:
            conf_json = json.loads(f.read())
            client.publish(config[1], json.dumps(conf_json))


def ha_update_states(client: mqtt.Client, userdata: HatchMQTT) -> None:
    volume = int((userdata.device.volume/255)*100)
    client.publish(userdata.states['sound_vol'], volume)
    sound_state = 'OFF' if userdata.device.sound == 0 else 'ON'
    client.publish(userdata.states['sound'], sound_state)
    client.publish(userdata.states['light'], json.dumps(userdata.generate_light_schema()))
    power_state = 'ON' if userdata.device.power else 'OFF'
    client.publish(userdata.states['switch'], power_state)


def on_connect(client: mqtt.Client, userdata: HatchMQTT, flags, rc) -> None:
    for topic in userdata.cmds.keys():
        client.subscribe(userdata.cmds[topic])
    ha_discover(client, userdata)
    ha_update_states(client, userdata)
    print("Connected")


def on_message(client: mqtt.Client, userdata: HatchMQTT, msg: mqtt.MQTTMessage) -> None:
    if userdata.device.power:
        if msg.topic == userdata.cmds['light']:
            userdata.set_light(msg.payload)
        elif msg.topic == userdata.cmds['sound']:
            if msg.payload == b'ON':
                userdata.device.set_sound(HatchRestSound.noise)
            else:
                userdata.device.set_sound(HatchRestSound.none)
        elif msg.topic == userdata.cmds['sound_vol']:
            userdata.device.set_volume(int((int(msg.payload)/100)*255))
    if msg.topic == userdata.cmds['switch']:
        if msg.payload == b'ON':
            userdata.device.power_on()
        else:
            userdata.device.power_off()
    userdata.device._refresh_data()
    ha_update_states(client, userdata)


parser = argparse.ArgumentParser()
parser.add_argument('-c', '--config', default=MQTT_CONFIG, help="configuration file")
parser.add_argument('-v', '--verbose', action='store_true', help="verbose messages")
args = parser.parse_args()

conf = configparser.ConfigParser()
conf.read(args.config)

host = conf.get('mqtt', 'host')
port = int(conf.get('mqtt', 'port'))

tries = 0
while tries < 5:
    try:
        hatch = HatchMQTT(conf['device']['addr'], conf['hass'])
        break
    except Exception:
        tries = tries + 1
        time.sleep(0.5)
if tries == 5:
    exit(1)

client = mqtt.Client(userdata=hatch)
client.enable_logger()
client.on_connect = on_connect
client.on_message = on_message

client.connect(host, port, 60)

client.loop_start()
try:
    while True:
        ha_update_states(client, hatch)
        time.sleep(2)
except KeyboardInterrupt:
    hatch.device.disconnect()
    exit(0)
