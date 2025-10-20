HOST_IP = "0.0.0.0"  # Usar 0.0.0.0 é mais robusto que um IP específico
PORTA = 8000
ENDPOINT = "/trigger"

LABELCODE_PORT = 8001  # porta para o serviço de input do labelcode

PLC_IP = '192.168.0.180'  # Nome da variável corrigido
PLC_PORT = 502
# IMPORTANTE: Este ID tem de corresponder exatamente ao ID configurado no CLP.
SLAVE_ID = 0
# --- ENDEREÇOS MODBUS A SEREM LIDOS ---
# Endereço do Coil no CLP que indica se a máquina está pronta.
COIL_MAQUINA_PRONTA = 2 # Nome da variável corrigido e valor atualizado