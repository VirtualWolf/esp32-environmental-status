# esp32-environmental-status

This is an application for an ESP32 (or a Raspberry Pi Pico W) hooked up to a [PiicoDev 3x RGB LED module](https://core-electronics.com.au/piicodev-3x-rgb-led-module.html) to display a colour representation of up to three different measurements received via JSON from MQTT topics. I'm using it with the data received from my [esp32-sensor-reader-mqtt](https://github.com/VirtualWolf/esp32-sensor-reader-mqtt/) devices.

# Configuration

It requires a file called `config.json` in the `src` directory:

```json
{
    "client_id": "<mqtt-client-id>",
    "server": "<mqtt-broker-address>",
    "port": 1883,
    "ssid": "<wifi network name>",
    "wifi_pw": "<wifi password>",
    "topics": [...]
}
```

The `topics` array is filled out with something like the following, with the `topic` to subscribe to and the `value` to pull out from the messages received on that topic. The `thresholds` and `colours` fields need to have the same number of elements, and for a datapoint of a given value the matching colour will be used for values above that threshold but less than the next one:

```json
    "topics": [
        {
            "topic": "home/outdoor/weather",
            "value": "dew_point",
            "thresholds": [0, 10, 13, 16, 18, 21, 24],
            "colours": ["blue", "light_green", "green", "yellow", "orange", "dark_orange", "red"]
        },
        {
            "topic": "home/outdoor/airquality",
            "value": "pm_2_5",
            "thresholds": [0, 50, 100, 150],
            "colours": ["green", "yellow", "orange", "red"]
        },
        {
            "topic": "home/indoor/airquality",
            "value": "aqi",
            "thresholds": [1, 2, 3, 4, 5],
            "colours": ["blue", "green", "yellow", "orange", "red"]
        }
    ]
```

So for example, a `dew_point` value of 13.5 means the top LED in the module will light up `green`. The colours are defined in [leds.py](src/leds.py).

Once configured, copy the whole contents of the `src` directory to the board with [mpremote](https://docs.micropython.org/en/latest/reference/mpremote.html) and restart it when it's finished:

```
$ cd src
$ mpremote connect port:/dev/tty.SLAB_USBtoUART cp -r . : + reset"
```

(Substituting `/dev/tty.SLAB_USBtoUART` for your specific board's serial port.)

## Other configuration

When running on an ESP32, the SDA and SCL pins also need to be specified, and default to 23 and 22 respectively if not given:

```json
    "sda_pin": 23,
    "scl_pin": 22
```

You can use your own NTP server instead of `time.cloudflare.com` for time setting on board startup:

```json
    "ntp_server": "10.0.0.1"
```

The LED brightness defaults to 20 (out of 255) but this can be configured with the `led_brightness` option:

```json
    "led_brightness": 100
```

# Turning the LEDs on and off, and checking and updating configuration
The ESP32 will subscribe to the topic `commands/displays` and `commands/displays/<CLIENT_ID>` to listen for commands, and will publish log messages to `logs/<CLIENT_ID>`.

## Turning LEDs off

Send a message to the `commands/displays` topic with the following payload:

```json
{
    "is_on": false
}
```

This will turn off the LEDs and they will remain off until a message with the body `"is_on": true` is received on that same topic.

## Get current config

Send a message to the `commands/displays/<CLIENT_ID>` topic with the following payload:

```json
{
    "command": "get_config"
}
```

And the current contents of `config.json` will be published to `logs/<CLIENT_ID>` so you can see how a given board is configured.

## Get system info
Send a message to the `commands/displays/<CLIENT_ID>` topic with the following payload:

```json
{
    "command": "get_system_info"
}
```

And a message will be published to to `logs/<CLIENT_ID>` with the MicroPython version of the board, the value of `gc.free_mem()`, and how much free space is available on the root volume.

## Updating configuration
Send a message to the `commands/displays/<CLIENT_ID>` topic with the following payload:

```json
{
    "command": "update_config",
    "config": {
        "server": "<broker-address>"
    }
}
```

And the board will trigger an update of the `config.json` file for the given fields in the `config` object. In the example above, this would update _just_ the `server` value and all the other existing values will be kept. Once the update is finished, the ESP32 will restart.

To _remove_ a configuration option, send the configuration option with an empty string:

```json
{
    "config": {
        "ntp_server": ""
    }
}
```

Note that the _required_ options (`client_id`, `server`, `port`, `ssid`, and `wifi_pw`) cannot be deleted, only updated to new values.

## Restarting the board
Send a message to the `commands/displays/<CLIENT_ID>` topic with the following payload:

```json
{
    "command": "restart"
}
```

And the board will run a `machine.reset()` and restart itself.
