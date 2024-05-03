import os
from config import config
from logger import publish_log_message
from PiicoDev_RGB import PiicoDev_RGB

colours = {
    'red':          [255,0,0],
    'dark_orange':  [255,80,0],
    'orange':       [255,140,0],
    'yellow':       [255,180,0],
    'green':        [0,255,0],
    'light_green':  [100,255,100],
    'blue':         [0,255,255],
}

if os.uname().sysname == 'esp32':
    leds = PiicoDev_RGB(bright=config['led_brightness'], bus=0, sda=config['sda_pin'], scl=config['scl_pin'])
else:
    leds = PiicoDev_RGB(bright=config['led_brightness'])

leds.pwrLED(False)
LEDS_ON = True

async def toggle_leds(is_on, client):
    global leds
    global LEDS_ON

    if is_on:
        await publish_log_message(message={'message': 'Enabling LEDs'}, client=client)
        LEDS_ON = True
    else:
        leds.clear()
        await publish_log_message(message={'message': 'Disabling LEDs'}, client=client)
        LEDS_ON = False

async def update_leds(topic, payload):
    global leds
    global LEDS_ON

    if LEDS_ON is False:
        return

    led_number = next(
        index for (index, item) in enumerate(config['topics'])
        if item['topic'] == topic
    )

    received_value = payload[config['topics'][led_number]['value']]

    thresholds = config['topics'][led_number]['thresholds']
    threshold_colours = config['topics'][led_number]['colours']

    for (index, item) in enumerate(thresholds[:-1]):
        current_threshold, next_threshold = item, thresholds[index + 1]

        if current_threshold <= received_value < next_threshold:
            leds.setPixel(led_number, colours[threshold_colours[index]])

            break
        else:
            leds.setPixel(led_number, colours[threshold_colours[-1]])

    leds.show()
