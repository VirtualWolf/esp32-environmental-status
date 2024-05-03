import json
from mqtt_as import config

with open('config.json', 'r') as file:
    c = json.load(file)

# Settings for the MQTT library
config['client_id']             = c.get('client_id')
config['server']                = c.get('server')
config['port']                  = c.get('port', 1883)
config['ssid']                  = c.get('ssid')
config['wifi_pw']               = c.get('wifi_pw')
config['will']                  = f"logs/{c.get('client_id')}", '{"status": "offline"}', True, 1

config['ntp_server']             = c.get('ntp_server', 'time.cloudflare.com')
config['sda_pin']                = c.get('sda_pin', 23)
config['scl_pin']                = c.get('scl_pin', 22)

# Configuration for LED status
config['topics']                = c.get('topics')
config['led_brightness']        = c.get('led_brightness', 20)

# MQTT topics to subscribe to for receiving commands and emitting logs
config['state_topic']           = 'commands/displays'
config['commands_topic']        = f"commands/displays/{c.get('client_id')}"
config['logs_topic']            = f"logs/{c.get('client_id')}"
