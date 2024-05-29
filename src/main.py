import os
import asyncio
import json
import ntptime
from neopixel import NeoPixel
from machine import Pin, reset, Timer
from mqtt_as import MQTTClient, config as mqtt_config
from config import config
from leds import update_leds
from admin import handle_command
from logger import log, publish_error_message, publish_log_message

def set_time():
    ntptime.host = config['ntp_server']

    log(f'Setting time using server {ntptime.host}')

    try:
        ntptime.settime()
    except OSError:
        log(f'Failed to contact NTP server at {ntptime.host}')
        reset()

def set_connection_status(state):
    # When the wifi and MQTT broker are both successfully connected turn the LED off
    if state:
        log('Wifi and MQTT broker are up')

        if config['neopixel_pin'] is not None:
            pixel.fill((0,0,0))
            pixel.write()
        else:
            led.value(0)

    # Either wifi or the MQTT broker are down to so turn the LED on
    else:
        log('Wifi or MQTT broker is down')

        if config['neopixel_pin'] is not None:
            pixel.fill((100,0,0))
            pixel.write()
        else:
            led.value(1)

async def messages(client):
    async for tpc, msg, retained in client.queue:
        topic = tpc.decode()
        payload = json.loads(msg.decode())

        try:
            if topic in (config['commands_topic'], config['state_topic']):
                await handle_command(topic=topic, payload=payload, client=client)
            else:
                await update_leds(topic=topic, payload=payload)
        except ValueError as e:
            publish_error_message(error={'error': 'Message was not JSON'}, client=client, exception=e)
        except Exception as e:
            publish_error_message(error={'error': 'Something went wrong'}, client=client, exception=e)

async def up(client):
    while True:
        await client.up.wait()
        client.up.clear()
        set_connection_status(True)

        for topic in config['topics']:
            log(f"Subscribing to {topic['topic']}")
            await client.subscribe(topic['topic'], 1)

        log(f"Subscribing to {config['commands_topic']} and {config['state_topic']}")
        await client.subscribe(config['commands_topic'], 1)
        await client.subscribe(config['state_topic'], 1)

        await publish_log_message({'status': "online"}, client=client, retain=True)

async def down(client):
    while True:
        await client.down.wait()
        client.down.clear()
        set_connection_status(False)

# The onboard NeoPixel on the Adafruit QT Py doesn't have power enabled by default so we need to turn it on first
if config['neopixel_pin'] is not None and config['neopixel_power_pin'] is not None:
    power_pin = Pin(config['neopixel_power_pin'], Pin.OUT)
    power_pin.on()

# Use the onboard NeoPixel LED for status indicators if the appropriate configuration options are set
if config['neopixel_pin'] is not None:
    pin = Pin(config['neopixel_pin'], Pin.OUT)
    pixel = NeoPixel(pin, 1)
else:
    led = Pin(config['led_pin'], Pin.OUT)

set_connection_status(False)

async def main(client):
    try:
        await client.connect()
    except OSError:
        log('Connection to wifi or MQTT broker failed')
        reset()

    # Run an initial NTP sync on board start
    ntptime.host = config['ntp_server']
    ntptime.settime()

    # Synchronise with the NTP server once a day
    if (os.uname().sysname == 'esp32'):
        set_time_timer = Timer(0)
    else:
        set_time_timer = Timer()

    set_time_timer.init(mode=Timer.PERIODIC, period=86400000, callback=set_time)

    for coroutine in (up, down, messages):
        asyncio.create_task(coroutine(client))

    while True:
        await asyncio.sleep(5)

mqtt_config["queue_len"] = 10
client = MQTTClient(mqtt_config)
try:
    asyncio.run(main(client))
finally:
    client.close()
