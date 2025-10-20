import http.server
import socketserver
import json
import pyautogui
import time
import threading

from pymodbus.client.sync import ModbusTcpClient
import config

modbus_data = {
    "maquina_pronta": False,
    "connection_status": "A iniciar...",
    "posicoes_bandeja": [False] * 8,  # 8 posições da bandeja (bits)
    "posicao_para_testar": None,      # Qual posição foi solicitada para teste
    "serial_numbers": [""] * 8,       # Serial numbers lidos pela câmera Keyence
}
lock = threading.Lock()

class ModbusWatcher(threading.Thread):
    def __init__(self):
        super().__init__()
        self.client = ModbusTcpClient(config.PLC_IP, port=config.PLC_PORT, timeout=3)
        self.daemon = True
        self.last_posicao_teste = None

    def run(self):
        print("--- VIGILANTE MODBUS (MESTRE) INICIADO ---")
        while True:
            try:
                if not self.client.is_socket_open():
                    print(f"[Modbus] A ligar ao CLP Escravo em {config.PLC_IP}...")
                    self.client.connect()

                if self.client.is_socket_open():
                    # --- LEITURA DOS REGISTRADORES PRINCIPAIS ---
                    result = self.client.read_holding_registers(
                        address=0,
                        count=16,
                        unit=config.SLAVE_ID
                    )

                    if not result.isError():
                        print(f"[Modbus] Leitura bem-sucedida. Valores: {result.registers}")
                        with lock:
                            modbus_data["connection_status"] = "Ligado"
                            modbus_data["maquina_pronta"] = True
                    else:
                        print(f"[Modbus] Erro na leitura: {result}")
                        raise ConnectionError("O CLP rejeitou o pedido de leitura.")

                    try:
                        # Endereço do registrador que contém as 8 posições (bits)
                        # Ajuste este endereço conforme a configuração do seu CLP
                        bandeja_address = 100  # Endereço onde pode ser ajustável para o correto
                        bandeja_result = self.client.read_holding_registers(
                            address=bandeja_address,
                            count=1,  # Apenas 1 registrador que contém os 8 bits
                            unit=config.SLAVE_ID
                        )
                        
                        if not bandeja_result.isError():
                            # Converter o valor do registrador em 8 bits individuais
                            valor_registrador = bandeja_result.registers[0]
                            print(f"[Modbus] Leitura do registrador da bandeja: {valor_registrador}")
                            
                            # Converter para bits
                            posicoes = []
                            for i in range(8):
                                bit_set = (valor_registrador & (1 << i)) != 0
                                posicoes.append(bit_set)
                            
                            with lock:
                                modbus_data["posicoes_bandeja"] = posicoes
                            
                            # Verificar se alguma posição está solicitando teste
                            posicao_teste = None
                            if valor_registrador > 0:
                                # Encontrar qual bit está ativo - prioridade para o bit de menor índice
                                for i in range(8):
                                    if (valor_registrador & (1 << i)) != 0:
                                        posicao_teste = i
                                        break
                            
                            with lock:
                                modbus_data["posicao_para_testar"] = posicao_teste
                            
                            # Se a posição para testar mudou, acionar a digitação do serial
                            if posicao_teste is not None and posicao_teste != self.last_posicao_teste:
                                print(f"[Modbus] Solicitação para testar a posição {posicao_teste}")
                                self.last_posicao_teste = posicao_teste
                                
                                # Iniciar uma thread para digitar o serial correspondente
                                threading.Thread(
                                    target=self.processar_teste_posicao, 
                                    args=(posicao_teste,)
                                ).start()
                                
                        else:
                            print(f"[Modbus] Erro ao ler registrador da bandeja: {bandeja_result}")
                    except Exception as e:
                        print(f"[Modbus] Erro ao processar registrador da bandeja: {e}")
                    
                    # --- LEITURA DOS SERIAL NUMBERS ---
                    try:
                        # Aqui assumimos que os serial numbers estão em registradores separados
                        # Ajuste conforme a configuração do seu CLP
                        for i in range(8):
                            if modbus_data["posicoes_bandeja"][i]:  # Se houver uma placa nesta posição
                                # Ajuste o endereço base e offset conforme seu CLP
                                serial_address = 200 + (i * 10)  # Exemplo: 10 registros por serial
                                serial_result = self.client.read_holding_registers(
                                    address=serial_address,
                                    count=10,  # Número de registros para cada serial
                                    unit=config.SLAVE_ID
                                )
                                
                                if not serial_result.isError():
                                    # Converter registros para string
                                    serial_number = self.converter_registros_para_serial(serial_result.registers)
                                    with lock:
                                        modbus_data["serial_numbers"][i] = serial_number
                                    print(f"[Modbus] Serial na posição {i}: {serial_number}")
                                else:
                                    print(f"[Modbus] Erro ao ler serial da posição {i}: {serial_result}")
                    except Exception as e:
                        print(f"[Modbus] Erro ao processar leitura de seriais: {e}")

                    # --- ESCRITA DE CONFIRMAÇÃO SE NECESSÁRIO ---
                    # Aqui você pode adicionar código para escrever de volta no CLP confirmando que 
                    # o teste foi iniciado ou concluído

                else:
                    raise ConnectionError("Falha ao abrir o socket para o CLP.")

            except Exception as e:
                print(f"[Modbus] Erro de comunicação: {e}")
                with lock:
                    modbus_data["connection_status"] = "Erro de Ligação"
                    modbus_data["maquina_pronta"] = False
                self.client.close()

            time.sleep(0.5)  # Reduzido para reagir mais rápido
    
    def processar_teste_posicao(self, posicao):
        """Processa a solicitação para testar uma posição específica"""
        try:
            # Obter o serial number correspondente à posição
            with lock:
                serial = modbus_data["serial_numbers"][posicao]
                posicao_ocupada = modbus_data["posicoes_bandeja"][posicao]
            
            if not posicao_ocupada:
                print(f"[Teste] Erro: Posição {posicao} está vazia")
                return
            
            if not serial:
                print(f"[Teste] Erro: Nenhum serial number encontrado na posição {posicao}")
                return
            
            # Digitar o serial number no software da Samsung
            print(f"[Teste] Digitando serial da posição {posicao}: {serial}")
            success, message = digitar_labelcode(serial)
            
            if success:
                print(f"[Teste] Serial digitado com sucesso: {serial}")
                
                # Aqui você pode adicionar código para confirmar ao CLP que o serial foi digitado
                try:
                    # Exemplo: escrever em um registrador de confirmação
                    confirmacao_address = 150  # Ajuste conforme necessário
                    self.client.write_register(
                        address=confirmacao_address,
                        value=posicao + 1,  # +1 para evitar valor zero, que poderia ser interpretado como "sem confirmação"
                        unit=config.SLAVE_ID
                    )
                    print(f"[Teste] Confirmação enviada para o CLP: posição {posicao}")
                except Exception as e:
                    print(f"[Teste] Erro ao confirmar ao CLP: {e}")
            else:
                print(f"[Teste] Erro ao digitar serial: {message}")
        
        except Exception as e:
            print(f"[Teste] Erro ao processar teste para posição {posicao}: {e}")
    
    def converter_registros_para_serial(self, registers):
        """Converte os registros do Modbus em uma string de serial number"""
        try:
            # Método 1: Assumindo que cada registro contém um caractere ASCII
            chars = [chr(reg) for reg in registers if 32 <= reg <= 126]  # Filtra caracteres imprimíveis
            return ''.join(chars).strip()
            
            # Método Alternativo: Se os registros forem codificados de outra forma
            # return ''.join([format(reg, 'X') for reg in registers])  # Formato hexadecimal
        except Exception as e:
            print(f"[Modbus] Erro na conversão de registros para serial: {e}")
            return ""


def digitar_labelcode(code: str):
    try:
        print(f"Ação: A digitar o LabelCode '{code}'...")
        time.sleep(0.1)
        pyautogui.write(code)
        pyautogui.press('enter')
        print("Ação: Concluída com sucesso.")
        return True, "Digitado com sucesso."
    except Exception as e:
        print(f"ERRO CRÍTICO ao tentar digitar com PyAutoGUI: {e}")
        return False, f"Erro de automação: {e}"


class SimpleTriggerHandler(http.server.BaseHTTPRequestHandler):

    def do_POST(self):
        if self.path == config.ENDPOINT:
            try:
                # --- VERIFICAÇÃO DO ESTADO DO CLP ANTES DE PROSSEGUIR ---
                with lock:
                    maquina_esta_pronta = modbus_data.get("maquina_pronta", False)
                    status_conexao = modbus_data.get("connection_status", "Erro")

                if status_conexao != "Ligado":
                    print("FALHA: Sem ligação ao CLP.")
                    self.send_error(503, "Não foi possível verificar o estado do CLP (Service Unavailable).")
                    return

                if not maquina_esta_pronta:
                    print("FALHA: A máquina não está pronta (Coil do CLP está FALSE).")
                    self.send_error(409, "O CLP indicou que a máquina não está pronta (Conflict).")
                    return
                # --- FIM DA VERIFICAÇÃO ---

                # Se a verificação passou, processa o pedido
                content_length = int(self.headers['Content-Length'])
                post_data = self.rfile.read(content_length)
                data = json.loads(post_data)

                # Opção 1: Processar labelcode diretamente (compatibilidade)
                labelcode = data.get('labelcode')
                if labelcode:
                    print(f"Gatilho recebido! LabelCode: {labelcode}")
                    success, message = digitar_labelcode(labelcode)

                    if success:
                        self.send_response(200)
                        self.send_header('Content-type', 'application/json')
                        self.end_headers()
                        response = {"ok": True, "message": message}
                        self.wfile.write(json.dumps(response).encode('utf-8'))
                    else:
                        self.send_error(500, message)
                    return
                
                # Opção 2: Processar serial de uma posição específica da bandeja
                posicao = data.get('posicao')
                if posicao is not None and 0 <= posicao < 8:
                    with lock:
                        serial = modbus_data["serial_numbers"][posicao]
                        posicao_ocupada = modbus_data["posicoes_bandeja"][posicao]
                    
                    if not posicao_ocupada:
                        self.send_error(400, f"Posição {posicao} está vazia (não há placa).")
                        return
                    
                    if not serial:
                        self.send_error(404, f"Nenhum serial number encontrado na posição {posicao}.")
                        return
                    
                    print(f"Gatilho recebido! Digitar serial da posição {posicao}: {serial}")
                    success, message = digitar_labelcode(serial)
                    
                    if success:
                        self.send_response(200)
                        self.send_header('Content-type', 'application/json')
                        self.end_headers()
                        response = {"ok": True, "message": message, "serial": serial}
                        self.wfile.write(json.dumps(response).encode('utf-8'))
                    else:
                        self.send_error(500, message)
                    return
                
                # Se não encontrou nem labelcode nem posição válida
                print("ERRO: Pedido recebido sem a chave 'labelcode' ou 'posicao' válida.")
                self.send_error(400, "Pedido inválido: forneça 'labelcode' ou 'posicao' (0-7).")

            except Exception as e:
                print(f"ERRO inesperado no servidor: {e}")
                self.send_error(500, f"Erro interno do servidor: {e}")
        # Endpoint para consulta do estado das posições da bandeja
        elif self.path == "/status":
            try:
                with lock:
                    status = {
                        "connection": modbus_data["connection_status"],
                        "maquina_pronta": modbus_data["maquina_pronta"],
                        "posicoes_bandeja": modbus_data["posicoes_bandeja"],
                        "posicoes_bandeja": modbus_data["posicoes_bandeja"],
                        "serial_numbers": modbus_data["serial_numbers"]
                    }
                
                self.send_response(200)
                self.send_header('Content-type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps(status).encode('utf-8'))
            except Exception as e:
                print(f"ERRO ao enviar status: {e}")
                self.send_error(500, f"Erro interno: {e}")
        else:
            self.send_error(404, "Endpoint não encontrado. Use " + config.ENDPOINT + " ou /status")

    def log_message(self, format, *args):
        return


if __name__ == "__main__":

    modbus_thread = ModbusWatcher()
    modbus_thread.start()

    with socketserver.TCPServer((config.HOST_IP, config.PORTA), SimpleTriggerHandler) as httpd:
        print(f"--- SERVIDOR DE GATILHO SIMPLES INICIADO ---")
        print(f"A ouvir em http://{config.HOST_IP}:{config.PORTA}")
        print(f"A aguardar por pedidos POST no endpoint: {config.ENDPOINT}")
        httpd.serve_forever()