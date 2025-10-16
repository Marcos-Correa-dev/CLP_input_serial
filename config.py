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


HOST_IP = "0.0.0.0"  # Usar 0.0.0.0 é mais robusto que um IP específico
PORTA = 8000
ENDPOINT = "/trigger"

PLC_IP = '192.168.0.180'  # Nome da variável corrigido
PLC_PORT = 502
# IMPORTANTE: Este ID tem de corresponder exatamente ao ID configurado no CLP.
SLAVE_ID = 0
# --- ENDEREÇOS MODBUS A SEREM LIDOS ---
# Endereço do Coil no CLP que indica se a máquina está pronta.
COIL_MAQUINA_PRONTA = 2 # Nome da variável corrigido e valor atualizado