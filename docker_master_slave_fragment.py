from flask import Flask, request, jsonify, abort
import docker
from functools import wraps
import json

app = Flask(__name__)
client = docker.from_env()

@app.route('/start', methods=['POST'])
def start_container():
    image = request.args.get('image')
    env_file = request.args.get('env_file', '') 

    if not config_exis(env_file):
        create_config(env_file)

    if check_if_cfg_fresh(env_file):
        return jsonify({'status': 'error', 'message': 'Config file is not configured'}), 400
    
    container_name = request.args.get('container_name', None)

    if not image or not env_file or not container_name:
        return jsonify({'status': 'error', 'message': 'Missing required parameters'}), 400

    env_file_path_in_container = '/app/.env'  
    volumes = {env_file: {'bind': env_file_path_in_container, 'mode': 'ro'}}

    try:
        container = client.containers.run(
            image,
            name=container_name,
            volumes=volumes,
            environment={'ENV_FILE_PATH': env_file_path_in_container},
            detach=True
        )
        return jsonify({'status': 'started', 'container_id': container.id})
    except docker.errors.ContainerError as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500
    except docker.errors.ImageNotFound:
        return jsonify({'status': 'error', 'message': 'Image not found'}), 404
    except docker.errors.APIError as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

def require_api_key(view_function):
    @wraps(view_function)
    ####

@app.route('/stop', methods=['POST'])
@require_api_key

def stop_container():
    container_id = request.args.get('container_id')
    container = client.containers.get(container_id)
    container.stop()
    return jsonify({'status': 'stopped', 'container_id': container_id})


@app.route('/hardstop', methods=['POST'])
@require_api_key

def hardstop():
    container_id = request.args.get('container_id')
    container = client.containers.get(container_id)
    container.stop()
    container.remove()
    return jsonify({'status': 'stopped', 'container_id': container_id})


@app.route('/remove', methods=['POST'])
@require_api_key

def remove_container():
    container_id = request.args.get('container_id')
    container = client.containers.get(container_id)
    container.remove()
    return jsonify({'status': 'removed', 'container_id': container_id})

@app.route('/restart', methods=['POST'])
@require_api_key

def restart_container():
    container_id = request.args.get('container_id')
    install_file = request.args.get('install_file')
    container = client.containers.get(container_id)
    container.restart()
    # Assuming installation file needs to be re-applied or checked after restart
    return jsonify({'status': 'restarted', 'container_id': container_id})

@app.route('/status', methods=['GET'])
@require_api_key

def get_status():
    container_id = request.args.get('container_id')
    container = client.containers.get(container_id)
    return jsonify({'status': container.status, 'container_id': container_id})

@app.route('/log', methods=['GET'])
@require_api_key

def get_logs():
    container_id = request.args.get('container_id')
    container = client.containers.get(container_id)
    logs = container.logs().decode('utf-8')
    return jsonify({'logs': logs, 'container_id': container_id})

@app.route('/config_read', methods=['GET'])
@require_api_key

def read_config():
    file_path = request.args.get('file_path')
    with open(file_path, 'r') as file:
        content = file.read()
    return jsonify({'file_path': file_path, 'content': content})

        
@app.route('/config_edit', methods=['POST'])
@require_api_key
def config_edit():
    file_path = request.args.get('file_path')
    new_content = request.form.get('new_content')

    try:
        config_data = json.loads(new_content)  # Safely parse JSON input
    except json.JSONDecodeError:
        return jsonify({'status': 'error', 'message': 'Invalid JSON format'}), 400

    required_keys = {
        "PRIVATE_KEY": str, "RPC_ENDPOINT": str, "RPC_WEBSOCKET_ENDPOINT": str, "COMMITMENT_LEVEL": str,
        "TRANSACTION_EXECUTOR": str, "COMPUTE_UNIT_LIMIT": int, "COMPUTE_UNIT_PRICE": int, "CUSTOM_FEE": float,
        "QUOTE_AMOUNT": float, "AUTO_BUY_DELAY": int, "MAX_BUY_RETRIES": int, "BUY_SLIPPAGE": int, "AUTO_SELL": bool,
        "MAX_SELL_RETRIES": int, "AUTO_SELL_DELAY": int, "SKIP_SELL": int, "LQ_BELOW": int, "SELL_RETRY_DELAY": int,
        "PRICE_CHECK_INTERVAL": int, "PRICE_CHECK_DURATION": int, "SELL_SLIPPAGE": int, "TAKE_PROFIT_1": int,
        "PROFIT_AMOUNT_1": int, "TAKE_PROFIT_2": int, "PROFIT_AMOUNT_2": int, "TAKE_PROFIT_3": int, "PROFIT_AMOUNT_3": int,
        "TAKE_PROFIT_4": int, "PROFIT_AMOUNT_4": int, "STOP_LOSS_1": int, "LOSS_AMOUNT_1": int, "STOP_LOSS_2": int,
        "LOSS_AMOUNT_2": int, "STOP_LOSS_3": int, "LOSS_AMOUNT_3": int, "STOP_LOSS_4": int, "LOSS_AMOUNT_4": int,
        "FILTER_CHECK_DURATION": int, "FILTER_CHECK_INTERVAL": int, "CONSECUTIVE_FILTER_MATCHES": int, "CHECK_IF_MUTABLE": bool,
        "CHECK_IF_SOCIALS": bool, "CHECK_IF_MINT_IS_RENOUNCED": bool, "CHECK_IF_FREEZABLE": bool, "CHECK_IF_BURNED": bool,
        "MIN_POOL_SIZE": int, "MAX_POOL_SIZE": int
    }

    errors = {}
    for key, expected_type in required_keys.items():
        value = config_data.get(key, "")
        if isinstance(value, expected_type) and (value != "" if isinstance(value, str) else True):
            continue
        else:
            errors[key] = f'Expected type {expected_type.__name__}, got {type(value).__name__} or empty/null value'

    if errors:
        return jsonify({'status': 'error', 'message': 'Configuration validation errors', 'errors': errors}), 400

    # If all validations pass, write to file
    with open(file_path, 'w') as file:
        file.write(json.dumps(config_data, indent=4))
    
    return jsonify({'file_path': file_path, 'updated': True})

@app.route('/config_display', methods=['GET'])
@require_api_key
def config_display():
    file_path = request.args.get('file_path')
    # Try to open the file and read its content. If file doesn't exist, create it and add default content.
    try:
        with open(file_path, 'r') as file:
            content = file.read()
    except FileNotFoundError:
        # If file does not exist, create it with initial content and read the content.
        create_config(file_path)
        with open(file_path, 'r') as file:
            content = file.read()
    return jsonify({'file_path': file_path, 'content': content})


def config_exis(file_path):
    try:
        with open(file_path, 'r') as file:
            return True
    except FileNotFoundError:
        return False
    
def create_config(file_path):
    with open(file_path, 'w') as file:
        file.write('''
FIRST_CONFIG==VALUE
        ''')

def check_if_cfg_fresh(file_path):
    with open(file_path, 'r') as file:
        content = file.read()
        if 'FIRST_CONFIG=' in content:
            print('Config file is not configured')
            return True

    
if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5001)
