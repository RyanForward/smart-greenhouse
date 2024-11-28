from flask import Flask, render_template, request, jsonify
from datetime import datetime
import threading
import redis
import webbrowser

app = Flask(__name__)

r = redis.Redis(host='200.235.94.128', port=6379, db=0)
sensor_data = {'readLuminosidade': '', 'readTemperatura': '', 'readUmidade': ''}
auto_mode = False

def listen_to_sensors():
    pubsub = r.pubsub()
    pubsub.subscribe(['readLuminosidade', 'readTemperatura', 'readUmidade'])
    
    for message in pubsub.listen():
        if message['type'] == 'message':
            channel = message['channel'].decode('utf-8')
            data = message['data'].decode('utf-8')
            sensor_data[channel] = data

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/get_data')
def get_data():
    try:
        print('sensor_data: ', sensor_data['readLuminosidade'])
        if sensor_data['readLuminosidade'] != '404':
            return jsonify(sensor_data)
        else:
            return
    except redis.exceptions.ConnectionError:
        return jsonify({"error": "Redis server is unavailable"}), 503


threading.Thread(target=listen_to_sensors, daemon=True).start()

@app.route('/send_command', methods=['POST'])
def send_command():
    global auto_mode
    data = request.get_json()
    
    channel = data.get('channel') 
    command = data.get('command')

    if not channel or not command:
        return jsonify(success=False, error="Dados inválidos"), 400

    if channel == "pilotoAutomatico":
        auto_mode = command.upper() == "ON"
        r.publish('pilotoAutomatico', command)
    else:
        r.publish(channel, command)

    print(f"Comando '{command}' enviado para '{channel}'")
    return jsonify(success=True)


if __name__ == '__main__':
    
    host_ip = '0.0.0.0'
    port = 5000
    print(f"Abra seu navegador e acesse http://{host_ip}:{port}")
    url = f"http://127.0.0.1:{port}"
    webbrowser.open(url)
    
    app.run(host=host_ip, port=port)
