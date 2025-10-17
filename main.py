import http.server
import socketserver
import json
import pyautogui
import time
import threading

# Importa o cliente Modbus e as configurações do nosso ficheiro local
from pymodbus.client.sync import ModbusTcpClient
import config

# --- DADOS PARTILHADOS ENTRE THREADS ---
modbus_data = {
    "maquina_pronta": False,
    "connection_status": "A iniciar..."
}
lock = threading.Lock()

class ModbusWatcher(threading.Thread):
    """Thread Mestre, monitorizando o CLP em segundo plano e podendo escrever registros."""

    def __init__(self):
        super().__init__()
        self.client = ModbusTcpClient(config.PLC_IP, port=config.PLC_PORT, timeout=3)
        self.daemon = True

    def run(self):
        print("--- VIGILANTE MODBUS (MESTRE) INICIADO ---")
        while True:
            try:
                if not self.client.is_socket_open():
                    print(f"[Modbus] A ligar ao CLP Escravo em {config.PLC_IP}...")
                    self.client.connect()

                if self.client.is_socket_open():
                    # --- LEITURA ---
                    result = self.client.read_holding_registers(
                        address=0,
                        count=10,
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

                    write_result = self.client.write_register(
                        address=0,   # registrador que deseja escrever
                        value=44,   # valor a escrever
                        unit=config.SLAVE_ID
                    )

                    if not write_result.isError():
                        print("[Modbus] Valor escrito com sucesso no registrador 0!")
                    else:
                        print(f"[Modbus] Erro ao escrever no CLP: {write_result}")

                else:
                    raise ConnectionError("Falha ao abrir o socket para o CLP.")

            except Exception as e:
                print(f"[Modbus] Erro de comunicação: {e}")
                with lock:
                    modbus_data["connection_status"] = "Erro de Ligação"
                    modbus_data["maquina_pronta"] = False
                self.client.close()

            time.sleep(1)



# --- FUNÇÃO DE AUTOMAÇÃO ---
def digitar_labelcode(code: str):
    """Função que executa a ação de automação final: digitar o código."""
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


# --- MANIPULADOR DE PEDIDOS HTTP ---
class SimpleTriggerHandler(http.server.BaseHTTPRequestHandler):
    """Processa os pedidos HTTP, agora com verificação do CLP."""

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
                else:
                    print("ERRO: Pedido recebido sem a chave 'labelcode'.")
                    self.send_error(400, "Pedido inválido: a chave 'labelcode' é obrigatória.")

            except Exception as e:
                print(f"ERRO inesperado no servidor: {e}")
                self.send_error(500, f"Erro interno do servidor: {e}")
        else:
            self.send_error(404, "Endpoint não encontrado. Use " + config.ENDPOINT)

    def log_message(self, format, *args):
        return


# --- INÍCIO DA APLICAÇÃO ---
if __name__ == "__main__":
    # Inicia a thread do Modbus para monitorizar o CLP em segundo plano
    modbus_thread = ModbusWatcher()
    modbus_thread.start()

    # Configura e inicia o servidor HTTP para aguardar os gatilhos
    with socketserver.TCPServer((config.HOST_IP, config.PORTA), SimpleTriggerHandler) as httpd:
        print(f"--- SERVIDOR DE GATILHO SIMPLES INICIADO ---")
        print(f"A ouvir em http://{config.HOST_IP}:{config.PORTA}")
        print(f"A aguardar por pedidos POST no endpoint: {config.ENDPOINT}")
        httpd.serve_forever()





"""
import uvicorn
import threading
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

# Importa as classes da versão ANTIGA (v2.x) do Pymodbus
from pymodbus.server.sync import StartTcpServer
from pymodbus.datastore import ModbusSequentialDataBlock, ModbusServerContext

# Importa as configurações do nosso ficheiro local config.py
import config

# --- MEMÓRIA DO NOSSO ESCRAVO MODBUS (DATASTORE) ---

# 1. Criamos os blocos de memória individuais que irão guardar os nossos dados
datablock_coils = ModbusSequentialDataBlock(0, [False] * 200)
datablock_registers = ModbusSequentialDataBlock(0, [0] * 200)

# 2. Criamos uma "loja" (store) que é um dicionário com os nossos blocos de dados.
store = {
    "co": datablock_coils,
    "hr": datablock_registers,
    "di": ModbusSequentialDataBlock(0, [False] * 200),
    "ir": ModbusSequentialDataBlock(0, [0] * 200),
}

# 3. Criamos o contexto do servidor, associando a nossa loja ao ID do escravo.
context = ModbusServerContext(slaves={config.SLAVE_ID: store}, single=False)


# --- LÓGICA DO SERVIDOR MODBUS ---
def run_modbus_server():
    print(f"--- SERVIDOR MODBUS (ESCRAVO) INICIADO na porta {config.MODBUS_PORT} ---")
    # A função StartTcpServer bloqueia, por isso deve ser executada numa thread
    StartTcpServer(context=context, address=("", config.MODBUS_PORT))


# --- LÓGICA DO SERVIDOR WEB (PONTO DE ENTRADA / GATILHO) ---

app = FastAPI(title="Servidor de Gatilho para Escravo Modbus", version="2.5.3-compat-final")

class TriggerPayload(BaseModel):
    labelcode: str

def converter_string_para_registos(texto: str, max_len: int) -> list[int]:
    texto_cortado = texto[:max_len]
    valores_numericos = [ord(char) for char in texto_cortado]
    valores_finais = valores_numericos + [0] * (max_len - len(valores_numericos))
    return valores_finais

@app.post("/trigger")
def trigger_automation(payload: TriggerPayload):
    print(f"Gatilho recebido! LabelCode: {payload.labelcode}")

    try:
        valores_registos = converter_string_para_registos(
            payload.labelcode,
            config.MAX_CARACTERES_LABELCODE
        )
        print(f"A converter para valores de registo: {valores_registos}")

        # Escrevemos os valores diretamente nos blocos de dados
        print(f"A escrever valores no endereço de início {config.REG_LABELCODE_INICIO}...")
        datablock_registers.setValues(
            config.REG_LABELCODE_INICIO,
            valores_registos
        )

        print(f"A sinalizar novo código no Coil {config.COIL_NOVO_CODIGO_CHEGOU}...")
        datablock_coils.setValues(
            config.COIL_NOVO_CODIGO_CHEGOU,
            [True]
        )

        print("Dados armazenados no escravo Modbus com sucesso.")
        return {"ok": True, "message": f"LabelCode '{payload.labelcode}' armazenado."}

    except Exception as e:
        print(f"ERRO CRÍTICO ao tentar escrever na memória Modbus: {e}")
        raise HTTPException(
            status_code=500, detail=f"Ocorreu um erro interno: {e}"
        )

# Evento de startup da aplicação FastAPI
@app.on_event("startup")
def startup_event():
    modbus_thread = threading.Thread(target=run_modbus_server, daemon=True)
    modbus_thread.start()


if __name__ == "__main__":
    print(f"--- SERVIDOR DE GATILHO HTTP INICIADO em http://{config.HOST_IP}:{config.HOST_PORT} ---")
    print("A aguardar por pedidos no endpoint POST /trigger...")
    uvicorn.run(app, host=config.HOST_IP, port=config.HOST_PORT)

"""