import redis
import time
import random
import datetime
from threading import Thread
import serial

# Configuração do Redis
r = redis.Redis(host='10.0.0.185', port=6379, db=0)
arduino = serial.Serial('/dev/ttyACM0', 9600)
time.sleep(2)


# Função para enviar dados de sensores
def publish_sensor_data():
    while True:
        luminosidade = random.uniform(0, 100)  # Luminosidade em uma escala de 0 a 100
        temperatura = random.uniform(15, 35)  # Temperatura em Celsius
        umidade = random.uniform(30, 70)  # Umidade em percentual
        timestamp = datetime.datetime.now().strftime('%H:%M:%S')  # Formata apenas o horário

        # Armazena os dados no Redis
        r.set('readLuminosidade', f'{luminosidade:.2f}- {timestamp}')
        r.set('readTemperatura', f'{temperatura:.2f}- {timestamp}')
        r.set('readUmidade', f'{umidade:.2f}- {timestamp}')

        # Publica os dados nos canais
        r.publish('readLuminosidade', f'{luminosidade:.2f}- {timestamp}')
        r.publish('readTemperatura', f'{temperatura:.2f}- {timestamp}')
        r.publish('readUmidade', f'{umidade:.2f}- {timestamp}')

        # Log dos dados enviados
        print(f"Dados enviados: {timestamp}", {
            "Luminosidade": f"{luminosidade:.2f}",
            "Temperatura": f"{temperatura:.2f}",
            "Umidade": f"{umidade:.2f}"
        })

        time.sleep(20)  # Espera de 5 segundos antes de enviar novos dados



# Função para ouvir comandos do cliente
def listen_to_commands():
    pubsub = r.pubsub()
    pubsub.subscribe(['ligarIrrigador', 'ligarLampada', 'ligarAquecedor', 'ligarRefrigerador', 'pilotoAutomatico'])

    for message in pubsub.listen():
        if message['type'] == 'message':
            channel = message['channel'].decode('utf-8')
            command = message['data'].decode('utf-8')
            print(f"Recebido comando '{command}' no canal '{channel}'")

            # Lógica de resposta para os comandos recebidos
            if channel == 'ligarIrrigador':
                print("RECEBIDO EM ligarIrrigador comando: " + command)
                if (command == 'ON'):
                    print("Irrigador ligado")
                    enviar_comando('ligarIrrigador_ON')
                if (command == 'OFF'):
                    print("Irrigador desligado")
                    enviar_comando('ligarIrrigador_OFF')
            elif channel == 'ligarLampada':
                print("RECEBIDO EM ligarLampada comando: " + command)
                if (command == 'ON'):
                    print("Lampada ligada")
                    enviar_comando('ligarLampada_ON')
                if (command == 'OFF'):
                    print("Lampada desligada")
                    enviar_comando('ligarLampada_OFF')
            elif channel == 'ligarAquecedor':
                print("RECEBIDO EM ligarAquecedor comando: " + command)
                if (command == 'ON'):
                    print('Aquecedor ligado')
                    enviar_comando('ligarAquecedor_ON')
                if (command == 'OFF'):
                    print('Aquecedor desligado')
                    enviar_comando('ligarAquecedor_OFF')
            elif channel == 'ligarRefrigerador':
                print("RECEBIDO EM ligarRefrigerador comando: " + command)
                if (command == 'ON'):
                    print("Refrigerador ligado")
                    enviar_comando('ligarRefrigerador_ON')
                if (command == 'OFF'):
                    enviar_comando('ligarRefrigerador_OFF')
                    print("Refrigerador desligado")
            elif channel == 'pilotoAutomatico':
                global auto_mode
                print("RECEBIDO EM pilotoAutomatico comando: " + command)
                if command == 'ON':
                    auto_mode = True
                    print("Piloto automático ativado.")
                elif command == 'OFF':
                    auto_mode = False
                    print("Piloto automático desativado.")




def enviar_comando(comando):
    arduino.write(comando.encode())  # Envia o comando como bytes
    print(f"Comando enviado: {comando}")
    time.sleep(3)  # Adicione um pequeno atraso (ajuste conforme necessário)


# Função para monitorar sensores e controlar atuadores automaticamente
def piloto_automatico():
    global auto_mode
    print(f"Piloto automático ativo? {auto_mode}")
    while True:
        if auto_mode:
            try:
                # Obtenha os dados atuais do Redis
                temp_data = r.get('readTemperatura')
                umi_data = r.get('readUmidade')
                lum_data = r.get('readLuminosidade')

                if temp_data and umi_data and lum_data:
                    temp = float(temp_data.decode('utf-8').split('-')[0])
                    umi = float(umi_data.decode('utf-8').split('-')[0])
                    lum = float(lum_data.decode('utf-8').split('-')[0])

                    # Verifique os limites e atue
                    #if temp > 30:
                    #    print("Piloto automatico mandou ligar o Refrigerador")
                    #    enviar_comando('ligarRefrigerador_ON')
                    if temp < 60:
                        print("Piloto automatico mandou ligar o Aquecedor")
                        enviar_comando('ligarAquecedor_ON')

                    if umi < 60:
                        print("Piloto automatico mandou ligar o Irrigador")
                        enviar_comando('ligarIrrigador_ON')

                    if lum < 60:
                        print("Piloto automatico mandou ligar a Lampada")
                        enviar_comando('ligarLampada_ON')

                    # Ações de desligamento automático
                    #if temp <= 25:
                    #    print("Piloto automatico mandou desligar o Refrigerador")
                    #    enviar_comando('ligarRefrigerador_OFF')
                    if temp >= 61:
                        print("Piloto automatico mandou desligar o Aquecedor")
                        enviar_comando('ligarAquecedor_OFF')
                    if umi >= 61:
                        print("Piloto automatico mandou desligar o Refrigerador")
                        enviar_comando('ligarIrrigador_OFF')
                    if lum >= 61:
                        print("Piloto automatico mandou desligar a Lampada")
                        enviar_comando('ligarLampada_OFF')
                else:
                    print("Erro: Dados dos sensores não disponíveis.")
            except Exception as e:
                print(f"Erro no piloto automático: {e}")
        time.sleep(20)  # Intervalo para verificar os sensores



if __name__ == '__main__':
    try:
        print("Servidor iniciado...")

        # Define o estado inicial do piloto automático
        global auto_mode
        auto_mode = False  # Defina como True ou False dependendo do estado inicial desejado

        # Inicia as threads
        Thread(target=publish_sensor_data, daemon=True).start()
        Thread(target=listen_to_commands, daemon=True).start()
        Thread(target=piloto_automatico, daemon=True).start()

        # Mantém o programa em execução
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("Encerrando servidor...")
        r.publish('readLuminosidade', '404')
        r.publish('readTemperatura', '404')
        r.publish('readUmidade', '404')
        arduino.close()
