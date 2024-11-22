from flask import Flask, render_template, request, jsonify
from datetime import datetime
import threading
import redis
import webbrowser

app = Flask(__name__)

# Configuração do Redis
r = redis.Redis(host='10.0.0.185', port=6379, db=0)
sensor_data = {'readLuminosidade': '', 'readTemperatura': '', 'readUmidade': ''}
auto_mode = False

# Função para ouvir os dados do servidor
def listen_to_sensors():
    pubsub = r.pubsub()
    pubsub.subscribe(['readLuminosidade', 'readTemperatura', 'readUmidade'])
    
    for message in pubsub.listen():
        if message['type'] == 'message':
            channel = message['channel'].decode('utf-8')
            data = message['data'].decode('utf-8')
            # Atualiza os dados de sensor apenas com a nova mensagem
            sensor_data[channel] = data

# Rota principal para renderizar o HTML
@app.route('/')
def home():
    return render_template('index.html')

# Rota para o frontend buscar dados de sensores
@app.route('/get_data')
def get_data():
    try:
        # Tenta se conectar ao Redis
        print('sensor_data: ', sensor_data['readLuminosidade'])
        if sensor_data['readLuminosidade'] != '404':
            return jsonify(sensor_data)
        else:
            return
    except redis.exceptions.ConnectionError:
        # Retorna um erro caso o Redis esteja inativo
        return jsonify({"error": "Redis server is unavailable"}), 503


# Inicia a thread para ouvir os dados do servidor
threading.Thread(target=listen_to_sensors, daemon=True).start()

# Rota para receber comandos do frontend
@app.route('/send_command', methods=['POST'])
def send_command():
    global auto_mode
    data = request.get_json()
    channel = data['channel']
    command = data['command']

    if channel == "pilotoAutomatico":
        auto_mode = command == "ON"
        r.publish('pilotoAutomatico', command)
    else:
        r.publish(channel, command)

    return jsonify(success=True)


if __name__ == '__main__':
    # Abre a interface no navegador automaticamente apenas uma vez
    port = 5000
    url = f"http://127.0.0.1:{port}"
    print(f"Abra seu navegador e acesse {url}")
    
    # Abre o navegador automaticamente apenas uma vez
    webbrowser.open(url)
    
    app.run(port=port)
