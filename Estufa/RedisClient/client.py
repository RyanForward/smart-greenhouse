from flask import Flask, render_template, request, jsonify
from datetime import datetime
import threading
import redis
import json

app = Flask(__name__)

r = redis.Redis(host='200.235.94.128', port=6379, db=0)
sensor_data = {'readLuminosidade': '', 'readTemperatura': '', 'readUmidade': ''}
atuadores_status = {'estadoIrrigador': 'OFF', 'estadoLampada': 'OFF',              
                    'estadoAquecedor': 'OFF', 'estadoRefrigerador': 'OFF'}
auto_mode = False
limites_atuadores = {'umidade': None, 'temperatura': None, 'luminosidade': None}

def listen_to_sensors():                                   
    pubsub = r.pubsub()
    pubsub.subscribe(['readLuminosidade', 'readTemperatura', 'readUmidade', 'StatusAtuadores'])

    for message in pubsub.listen():
        if message['type'] == 'message':
            channel = message['channel'].decode('utf-8')
            data = message['data'].decode('utf-8')
            if channel == 'StatusAtuadores':                
                atuador, estado = data.split(':')
                atuadores_status[atuador] = estado
                historico_key = f"historico_{atuador}"
                r.rpush(historico_key, f"{estado} - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            else:
                sensor_data[channel] = data

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/get_data')
def get_data():
    try:
        historico = {
            atuador: r.lrange(f"historico_{atuador}", 0, -1) for atuador in atuadores_status.keys()
        }
        historico = {k: [item.decode('utf-8') for item in v] for k, v in historico.items()}

        response_data = sensor_data.copy()
        response_data['atuadores'] = atuadores_status 
        response_data['historico'] = historico
        response_data['limites'] = limites_atuadores

        return jsonify(response_data)
    except redis.exceptions.ConnectionError:
        return jsonify({"error": "Servidor Redis não está disponível"}), 503

threading.Thread(target=listen_to_sensors, daemon=True).start()

@app.route('/check_limits', methods=['GET'])
def check_limits():         
    global limites_atuadores
    if None in limites_atuadores.values():
        return jsonify({"limitsSet": False})
    return jsonify({"limitsSet": True})

@app.route('/send_command', methods=['POST'])
def send_command():                 
    global auto_mode, limites_atuadores
    data = request.get_json()
    channel = data.get('channel')  
    command = data.get('command')  

    if auto_mode and channel not in ["pilotoAutomatico", "limitesAtuadores"]:
        return jsonify({"error": "Não é possível enviar comandos manuais enquanto o piloto automático está ativado."}), 403

    if channel == "pilotoAutomatico" and command == "ON":
        if None in limites_atuadores.values():
            return jsonify({"error": "Defina os limites de umidade, temperatura e luminosidade antes de ativar o piloto automático."}), 403
        auto_mode = True 
        r.publish('pilotoAutomatico', command)
        return jsonify({"success": "Piloto automático ativado com sucesso."})

    elif channel == "pilotoAutomatico" and command == "OFF":
        auto_mode = False
        r.publish('pilotoAutomatico', command)
        return jsonify({"success": "Piloto automático desativado com sucesso."})

    elif channel == "limitesAtuadores":
        try:
            limites = command.split(',')      
            if len(limites) == 3:
                limites_atuadores['umidade'] = int(limites[0])
                limites_atuadores['temperatura'] = float(limites[1])
                limites_atuadores['luminosidade'] = float(limites[2])
                r.publish('opcoesLimites', command) 
                return jsonify({"success": "Limites atualizados com sucesso.", "novos_limites": limites_atuadores})
            else:
                raise ValueError("O comando não contém três valores válidos.")
        except (ValueError) as e:
            return jsonify({"error": f"Formato de limites inválido. Erro: {e}"}), 400
    else:
        r.publish(channel, command)
        return jsonify(success=True)



if __name__ == '__main__':
    host_ip = '0.0.0.0'
    port = 5000
    print(f"Acesse http://<seu_ip_local>:5000")
    app.run(host=host_ip, port=port)

