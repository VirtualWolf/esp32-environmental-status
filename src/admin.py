from platform import platform
import gc
import json
import os
from machine import reset
from config import config
from leds import toggle_leds
from logger import publish_log_message, publish_error_message

async def handle_command(topic, payload, client):
    try:
        if topic == config['state_topic'] and 'is_on' in payload and isinstance(payload['is_on'], bool):
            await toggle_leds(is_on=payload['is_on'], client=client)
        elif topic == config['commands_topic'] and 'command' in payload:
            if payload['command'] == 'get_config':
                await get_config(client)

            if payload['command'] == 'get_system_info':
                await get_system_info(client)

            if payload['command'] == 'update_config' and 'config' in payload:
                await update_config(incoming_config=payload.get('config'), client=client)

            if payload['command'] == 'restart':
                await publish_log_message(message={
                    'message': 'Restarting...',
                    'status': 'offline',
                }, client=client)
                reset()

    except Exception as e:
        await publish_error_message(error={'error': 'Something went wrong'}, exception=e, client=client)



async def get_config(client):
    with open('config.json', 'r') as file:
        current_config = json.load(file)

    await publish_log_message(message={'config': current_config}, client=client)



async def get_system_info(client):
    filesystem_stats = os.statvfs('/')
    block_size = filesystem_stats[0]
    total_blocks = filesystem_stats[2]
    free_blocks = filesystem_stats[3]

    free_memory = gc.mem_free()

    system_info = {
        "micropython_version": platform(),
        "free_memory": f'{(free_memory/1024):.2f}KB',
        "total_space": f'{(block_size * total_blocks)/1024:.0f}KB',
        "free_space": f'{(block_size * free_blocks)/1024:.0f}KB'
    }

    await publish_log_message(message=system_info, client=client)



async def update_config(incoming_config, client):
    try:
        with open('config.json', 'r') as file:
            current_config = json.load(file)

        config_key = next(iter(incoming_config.keys()))
        config_value = next(iter(incoming_config.values()))

        required_config_keys = ['client_id', 'server', 'port', 'ssid', 'wifi_pw']

        if config_key in required_config_keys and not config_value:
            await publish_log_message(message={
                'error': f"Cannot unset required configuration '{config_key}'",
                'config': current_config
            }, client=client)

            return


        if config_value == '':
            del current_config[config_key]
        else:
            current_config.update(incoming_config)

        with open('config.json', 'w') as file:
            json.dump(current_config, file)

        await publish_log_message(message={
            'message': 'Configuration updated, restarting board...',
            'config': current_config,
            'status': 'offline',
        }, client=client)

        reset()
    except Exception as e:
        await publish_error_message(error={'error': 'Failed to update configuration'}, exception=e, client=client)
