import os
import asyncio
import json
import ntptime
from machine import reset, Timer
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

        for topic in config['topics']:
            log(f"Subscribing to {topic['topic']}")
            await client.subscribe(topic['topic'], 1)

        log(f"Subscribing to {config['commands_topic']} and {config['state_topic']}")
        await client.subscribe(config['commands_topic'], 1)
        await client.subscribe(config['state_topic'], 1)

        await publish_log_message({'status': "online"}, client=client, retain=True)

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

    for coroutine in (up, messages):
        asyncio.create_task(coroutine(client))

    while True:
        await asyncio.sleep(5)

mqtt_config["queue_len"] = 10
client = MQTTClient(mqtt_config)
try:
    asyncio.run(main(client))
finally:
    client.close()
