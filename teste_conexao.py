from pymodbus.client.sync import ModbusTcpClient

# --- CONFIGURAÇÕES DO TESTE ---
# Altere estes valores para corresponderem exatamente à configuração do seu CLP.

PLC_IP = '192.168.0.180'  # IP do seu CLP Escravo
PLC_PORT = 502  # Porta Modbus (padrão é 502)
SLAVE_ID = 1  # <-- O ID do Escravo configurado no CLP. ESTE É O VALOR MAIS IMPORTANTE A VERIFICAR.
ENDERECO_A_LER = 2  # <-- O endereço do Coil que você quer ler (no seu config.py estava 2).

# ---------------------------------

# Cria uma instância do cliente Modbus TCP (o nosso Mestre)
client = ModbusTcpClient(PLC_IP, port=PLC_PORT, timeout=3)

print("-" * 50)
print(f"A tentar ligar ao CLP em {PLC_IP}:{PLC_PORT}...")

try:
    # Tenta estabelecer a ligação com o CLP
    client.connect()

    # Verifica se a ligação foi realmente estabelecida
    if client.is_socket_open():
        print("SUCESSO: Ligação estabelecida com o CLP!")

        print(f"A tentar ler o Coil no endereço {ENDERECO_A_LER} do Escravo ID {SLAVE_ID}...")

        # Tenta ler 1 Coil a partir do endereço especificado
        # A sintaxe (address, count, unit) é a correta para a versão do pymodbus que você deve ter.
        resultado = client.read_coils(address=ENDERECO_A_LER, count=1, unit=SLAVE_ID)

        # Verifica se a leitura resultou num erro Modbus (ex: endereço não existe)
        if resultado.isError():
            print(f"\nERRO DE LEITURA: A ligação funcionou, mas o CLP respondeu com um erro.")
            print(f"  -> Resposta do CLP: {resultado}")
            print("\n  Causas prováveis:")
            print(f"  - O endereço de Coil '{ENDERECO_A_LER}' não existe ou não está acessível no CLP.")
            print(f"  - O Slave ID '{SLAVE_ID}' pode estar incorreto, embora a ligação tenha sido aceite.")

        # Se a leitura foi bem-sucedida
        else:
            valor_lido = resultado.bits[0]
            print("\n--- TESTE BEM-SUCEDIDO! ---")
            print(f"O valor do Coil no endereço {ENDERECO_A_LER} é: {valor_lido}")
            print("-----------------------------")

    else:
        print("\nFALHA NA LIGAÇÃO: Não foi possível estabelecer a ligação com o CLP.")
        print("  Verifique se o endereço IP, a porta e a sua ligação de rede estão corretos.")
        print("  Confirme também se a Firewall do Windows no PC do CLP não está a bloquear a porta 502.")

except Exception as e:
    print(f"\nOCORREU UM ERRO INESPERADO:")
    print(f"  -> Erro: {e}")
    print("\n  Isto geralmente acontece quando:")
    print("  - O CLP recusa ou fecha a ligação abruptamente (causa mais provável: 'SLAVE_ID' incorreto).")
    print("  - A sua versão do 'pymodbus' é muito antiga e incompatível (tente 'pip install --upgrade pymodbus').")

finally:
    # Garante que a ligação é sempre fechada no final do teste
    if client.is_socket_open():
        client.close()
        print("\nLigação com o CLP fechada.")
print("-" * 50)