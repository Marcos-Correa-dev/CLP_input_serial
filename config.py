"""
HOST_IP = "192.168.0.207"
HOST_PORT = 8000

HOST_MODBUS_IP = "192.168.0.180"
MODBUS_PORT = 502
SLAVE_ID = 1


REG_LABELCODE_INICIO = 0

MAX_CARACTERES_LABELCODE = 50

COIL_NOVO_CODIGO_CHEGOU = 2
"""

# Ficheiro de Configurações da Automação

# --- CONFIGURAÇÕES DO SERVIDOR HTTP (Onde a nossa aplicação ouve) ---
# Ouve em todas as interfaces de rede para receber o gatilho da câmara.
HOST_IP = "0.0.0.0"  # Usar 0.0.0.0 é mais robusto que um IP específico
PORTA = 8000
ENDPOINT = "/trigger"

# --- CONFIGURAÇÕES DO CLP ESCRAVO (A quem nos vamos ligar) ---
PLC_IP = '192.168.0.180'  # Nome da variável corrigido
PLC_PORT = 502
# IMPORTANTE: Este ID tem de corresponder exatamente ao ID configurado no CLP.
SLAVE_ID = 1

# --- ENDEREÇOS MODBUS A SEREM LIDOS ---
# Endereço do Coil no CLP que indica se a máquina está pronta.
COIL_MAQUINA_PRONTA = 2 # Nome da variável corrigido e valor atualizado