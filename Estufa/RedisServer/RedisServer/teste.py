import serial
import time

# Configuração da porta serial (ajuste '/dev/ttyACM0' para o seu caso)
arduino = serial.Serial('/dev/ttyACM0', 9600)  # No Windows, seria algo como 'COM3'
time.sleep(2)  # Aguarda 2 segundos para a inicialização do Arduino

# Função para enviar um comando ao Arduino
def enviar_comando(comando):
    arduino.write(comando.encode())  # Envia o comando como bytes
    print(f"Comando enviado: {comando}")

# Exemplo de comando para acender um LED
if __name__ == '__main__':
    try:
        enviar_comando('ligarIrrigador_ON')
    except Exception as e:
        print(f"Erro: {e}")
    finally:
        arduino.close()  # Fecha a conexão serial
