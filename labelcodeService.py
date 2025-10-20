import http.server
import socketserver
import json
import pyautogui
import time
import config

class LabelCodeHandler(http.server.BaseHTTPRequestHandler):
    """Manipulador de requisições HTTP simples para receber e processar labelcodes"""
    
    def do_POST(self):
        """Processa requisições POST para o endpoint de trigger"""
        if self.path == config.ENDPOINT:
            try:
                # Lê o conteúdo do corpo da requisição
                content_length = int(self.headers['Content-Length'])
                post_data = self.rfile.read(content_length)
                data = json.loads(post_data)
                
                if 'labelcode' not in data:
                    self._send_error_response(400, "O campo 'labelcode' é obrigatório")
                    return
                
                labelcode = data['labelcode']
                if not labelcode:
                    self._send_error_response(400, "O labelcode não pode ser vazio")
                    return
                
                # Tenta digitar o labelcode
                resultado = self.digitar_codigo(labelcode)
                
                if resultado:
                    self.send_response(200)
                    self.send_header('Content-type', 'application/json')
                    self.end_headers()
                    response = {"success": True, "message": "Labelcode digitado com sucesso"}
                    self.wfile.write(json.dumps(response).encode('utf-8'))
                else:
                    self._send_error_response(500, "Erro ao digitar o labelcode")
                
            except json.JSONDecodeError:
                self._send_error_response(400, "JSON inválido no corpo da requisição")
            except Exception as e:
                self._send_error_response(500, f"Erro interno: {str(e)}")
        else:
            self._send_error_response(404, f"Endpoint não encontrado. Use {config.ENDPOINT}")
    
    def _send_error_response(self, status_code, message):
        """Envia uma resposta de erro formatada como JSON"""
        self.send_response(status_code)
        self.send_header('Content-type', 'application/json')
        self.end_headers()
        response = {"success": False, "error": message}
        self.wfile.write(json.dumps(response).encode('utf-8'))
    
    def digitar_codigo(self, codigo):
        """Função que digita o código recebido usando pyautogui"""
        try:
            print(f"Digitando código: {codigo}")
            time.sleep(0.1)  # Pequena pausa antes de digitar
            pyautogui.write(codigo)
            pyautogui.press('enter')
            print("Código digitado com sucesso!")
            return True
        except Exception as e:
            print(f"ERRO ao digitar código: {e}")
            return False
    
    def log_message(self, format, *args):
        """Personaliza o log das requisições"""
        print(f"[{self.log_date_time_string()}] {self.address_string()} - {format % args}")


def run_server(host, port):
    server_address = (host, port)
    
    try:
        with socketserver.TCPServer(server_address, LabelCodeHandler) as httpd:
            print(f"--- SERVIDOR DE LABELCODE INICIADO ---")
            print(f"Ouvindo em http://{host}:{port}")
            print(f"Endpoint para POST: {config.ENDPOINT}")
            print("Pressione Ctrl+C para encerrar o servidor")
            httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nServidor encerrado pelo usuário")
    except Exception as e:
        print(f"Erro ao iniciar servidor: {e}")


if __name__ == "__main__":
    LABELCODE_PORT = getattr(config, 'LABELCODE_PORT', 8001)
    run_server(config.HOST_IP, LABELCODE_PORT)