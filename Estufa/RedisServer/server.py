import redis
import time
import random
import datetime
from threading import Thread
import serial

r = redis.Redis(host='10.0.0.185', port=6379, db=0)
arduino = serial.Serial('/dev/ttyACM0', 9600)
time.sleep(2)

limiteTemp = 30;
limiteLuz = 700;
inversorUmi = 0;            ##Ao contrario dos demais, umidade é booleano

# Variáveis serão salvas usando as estrutura de variáveis disponibilizada pelo redis
r.set('estadoIrrigador', 'OFF')
r.set('estadoLampada', 'OFF')
r.set('estadoAquecedor', 'OFF')
r.set('estadoRefrigerador', 'OFF')


def publish_sensor_data():
    while True:
        if arduino.in_waiting > 0:
            try:
                linha = arduino.readline().decode('utf-8').strip()

                partes = linha.split(';')
                dados = {parte.split(':')[0]: parte.split(':')[1] for parte in partes if ':' in parte}

                luminosidade = float(dados.get("LDR", 0))
                umidade = int(dados.get("UMIDADE", 0))
                temperatura = float(dados.get("TEMPERATURA", 0))
                timestamp = datetime.datetime.now().strftime('%H:%M:%S')

                r.set('readLuminosidade', f'{luminosidade:.2f}- {timestamp}')
                r.set('readUmidade', f'{umidade}- {timestamp}')
                r.set('readTemperatura', f'{temperatura:.2f}- {timestamp}')
                r.publish('readLuminosidade', f'{luminosidade:.2f}- {timestamp}')
                r.publish('readUmidade', f'{umidade}- {timestamp}')
                r.publish('readTemperatura', f'{temperatura:.2f}- {timestamp}')

                print(f"Dados enviados: {timestamp}", {
                    "Luminosidade": f"{luminosidade:.2f}",
                    "Umidade": f"{umidade}",
                    "Temperatura": f"{temperatura:.2f}"
                })

            except Exception as e:
                print(f"Erro ao processar dados do Arduino: {e}")

        time.sleep(1)


def process_command_buffer():   #Estamos usando a estrutura de fila do proprio redis
    while True:
        try:
            command = r.lpop('command_buffer')
            if command:
                command = command.decode('utf-8')
                print(f"Processando comando do buffer: {command}")
                enviar_comando(command)
            else:
                time.sleep(0.5)
        except Exception as e:
            print(f"Erro ao processar buffer de comandos: {e}")

def listen_to_commands():
    pubsub = r.pubsub()
    pubsub.subscribe(['toggleIrrigador', 'toggleLampada', 'toggleAquecedor', 'toggleRefrigerador', 'pilotoAutomatico', 'opcoesLimites'])

    global limiteTemp, limiteLuz, inversorUmi, auto_mode  # Variáveis globais para controle dos limites

    for message in pubsub.listen():
        if message['type'] == 'message':
            channel = message['channel'].decode('utf-8')
            command = message['data'].decode('utf-8')
            print(f"Recebido comando '{command}' no canal '{channel}'")
            if channel == 'opcoesLimites':
                try:
                    # Quebra a string de limites
                    limites = command.split(',')
                    if len(limites) == 3:
                        # Atualiza os valores globais dos limites
                        inversorUmi = int(limites[0])  # Umidade
                        limiteTemp = float(limites[1])  # Temperatura
                        limiteLuz = float(limites[2])   # Luminosidade

                        print(f"Limites atualizados: Umidade={inversorUmi}, Temperatura={limiteTemp}, Luminosidade={limiteLuz}")
                    else:
                        print(f"Erro: Formato de mensagem inválido no canal 'opcoesLimites'. Dados recebidos: {command}")
                except Exception as e:
                    print(f"Erro ao processar limites recebidos no canal 'opcoesLimites': {e}")

            # Mapeia os estados dos atuadores usando o Redis
            estado_chave = {
                'toggleIrrigador': 'estadoIrrigador',
                'toggleLampada': 'estadoLampada',
                'toggleAquecedor': 'estadoAquecedor',
                'toggleRefrigerador': 'estadoRefrigerador'
            }

            # Ao chegar um comando para o atuador, primeiro verifica se o atuador já está cumprindo aquele comando
            if channel in estado_chave:
                estado_atual = r.get(estado_chave[channel])
                estado_atual = estado_atual.decode('utf-8') if estado_atual else None

                # Buffer apenas recebe comandos diferentes dos estados atuais
                if command != estado_atual:
                    r.rpush('command_buffer', f"{channel}_{command}")
                    r.set(estado_chave[channel], command)  # Atualiza o estado no Redis
                    r.publish('StatusAtuadores', f"{estado_chave[channel]}:{command}")  # Notifica cliente
                    print(f"Estado atualizado para '{command}' e comando enviado ao buffer.")
                else:
                    print(f"Comando '{command}' ignorado. Estado atual já é '{estado_atual}'.")

            # Controle do piloto automático, ligando ou desligando dependendo da mensagem que chega no canal
            if channel == 'pilotoAutomatico':
                if command == 'ON':
                    auto_mode = True
                    r.set('estadoPilotoAutomatico', 'ON')
                elif command == 'OFF':
                    auto_mode = False
                    r.set('estadoPilotoAutomatico', 'OFF')
                print(f"Piloto automático ativo? {auto_mode}")



def enviar_comando(comando):
    arduino.write(comando.encode())
    print(f"Comando enviado: {comando}")
    time.sleep(3)

def piloto_automatico():
    global auto_mode
    print(f"Piloto automático ativo? {auto_mode}")
    r.set('estadoPilotoAutomatico', 'OFF')  # Piloto começa como desligado

    while True:     #Se estriver ligado:
        if auto_mode:
            try:
                temp_data = r.get('readTemperatura')        #Pega os dados de leitura mais atuais via variaveis do Redis
                umi_data = r.get('readUmidade')
                lum_data = r.get('readLuminosidade')

                print("Piloto Automatico em operacao")

                if temp_data and umi_data and lum_data:
                    temp = float(temp_data.decode('utf-8').split('-')[0])
                    umi = int(umi_data.decode('utf-8').split('-')[0])  # Sensor retorna 0 (molhado) ou 1 (seco)
                    lum = float(lum_data.decode('utf-8').split('-')[0])

                    # Controle do refrigerador
                    estado_refrigerador = r.get('estadoRefrigerador')
                    estado_refrigerador = estado_refrigerador.decode('utf-8') if estado_refrigerador else 'OFF'

                    #Se a temperatura for maior que o limite estabelecido, liga o refrigerador
                    if temp >= limiteTemp and estado_refrigerador != 'ON':
                        r.rpush('command_buffer', 'toggleRefrigerador_ON')
                        print("Piloto automatico mandou LIGAR refrigerador")
                        r.set('estadoRefrigerador', 'ON')
                        r.publish('StatusAtuadores', 'estadoRefrigerador:ON')  # Notifica cliente de que foi ligado
                    #Se a temperatura for menor do que o limite estabelecido, desliga o refrigerador
                    elif temp < limiteTemp and estado_refrigerador != 'OFF':
                        r.rpush('command_buffer', 'toggleRefrigerador_OFF')
                        print("Piloto automatico mandou DESLIGAR refrigerador")
                        r.set('estadoRefrigerador', 'OFF')
                        r.publish('StatusAtuadores', 'estadoRefrigerador:OFF')  # Notifica cliente de que foi desligado

                    # Controle do aquecedor
                    estado_aquecedor = r.get('estadoAquecedor')
                    estado_aquecedor = estado_aquecedor.decode('utf-8') if estado_aquecedor else 'OFF'

                    # Se temperatura está abaixo do limite, liga o aquecedor
                    if temp < limiteTemp and estado_aquecedor != 'ON':
                        r.rpush('command_buffer', 'toggleAquecedor_ON')
                        print("Piloto automatico mandou LIGAR aquecedor")
                        r.set('estadoAquecedor', 'ON')
                        r.publish('StatusAtuadores', 'estadoAquecedor:ON')  # Notifica cliente de que foi ligado
                    # Se temperatura está acima do limite, desliga o aquecedor
                    elif temp >= limiteTemp and estado_aquecedor != 'OFF':
                        r.rpush('command_buffer', 'toggleAquecedor_OFF')
                        print("Piloto automatico mandou DESLIGAR aquecedor")
                        r.set('estadoAquecedor', 'OFF')
                        r.publish('StatusAtuadores', 'estadoAquecedor:OFF')  # Notifica cliente de que foi desligado

                    # Controle do irrigador
                    estado_irrigador = r.get('estadoIrrigador')
                    estado_irrigador = estado_irrigador.decode('utf-8') if estado_irrigador else 'OFF'

                    # Se o sensor lê 0 (Molhado) e o limite definido foi Atuar quando molhado, liga
                    # Se o sensor lẽ 1 (Seco) e o limite definido foi Atuar quando seco, liga
                    if (umi == 0 and inversorUmi == 1 and estado_irrigador != 'ON') or \
                       (umi == 1 and inversorUmi == 0 and estado_irrigador != 'ON'):
                        r.rpush('command_buffer', 'toggleIrrigador_ON')
                        print("Piloto automatico mandou LIGAR Irrigador")
                        r.set('estadoIrrigador', 'ON')
                        r.publish('StatusAtuadores', 'estadoIrrigador:ON')  # Notifica cliente de que foi ligado

                    # Se o sensor lê 1 (Seco) e o limite definido foi Atuar quando molhado, desliga
                    # Se o sensor lẽ 0 (Molhado) e o limite definido foi Atuar quando seco, desliga
                    elif estado_irrigador != 'OFF' and \
                        ((umi == 1 and inversorUmi == 1) or (umi == 0 and inversorUmi == 0)):
                        r.rpush('command_buffer', 'toggleIrrigador_OFF')
                        print("Piloto automatico mandou DESLIGAR irrigador")
                        r.set('estadoIrrigador', 'OFF')
                        r.publish('StatusAtuadores', 'estadoIrrigador:OFF')  # Notifica cliente de que foi desligado

                    # Controle da lâmpada
                    estado_lampada = r.get('estadoLampada')
                    estado_lampada = estado_lampada.decode('utf-8') if estado_lampada else 'OFF'

                    if lum > limiteLuz and estado_lampada != 'ON':
                        r.rpush('command_buffer', 'toggleLampada_ON')
                        print("Piloto automatico mandou LIGAR lampada")
                        r.set('estadoLampada', 'ON')
                        r.publish('StatusAtuadores', 'estadoLampada:ON')  # Notifica cliente de que foi ligado
                    elif lum <= limiteLuz and estado_lampada != 'OFF':
                        r.rpush('command_buffer', 'toggleLampada_OFF')
                        print("Piloto automatico mandou DESLIGAR lâmpada")
                        r.set('estadoLampada', 'OFF')
                        r.publish('StatusAtuadores', 'estadoLampada:OFF')  # Notifica cliente de que foi desligado

                else:
                    print("Erro: Dados dos sensores não disponíveis.")
            except Exception as e:
                print(f"Erro no piloto automático: {e}")

        time.sleep(5)  # Intervalo para verificar os sensores


if __name__ == '__main__':
    try:
        print("Servidor iniciado...")

        global auto_mode
        auto_mode = False

        # Threads para as operaçoes agirem de forma independente.
        Thread(target=publish_sensor_data, daemon=True).start()
        Thread(target=listen_to_commands, daemon=True).start()
        Thread(target=piloto_automatico, daemon=True).start()
        Thread(target=process_command_buffer, daemon=True).start()

        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("Encerrando servidor...")
        arduino.close()