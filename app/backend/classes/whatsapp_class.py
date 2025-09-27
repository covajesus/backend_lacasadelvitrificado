import requests
import os
from dotenv import load_dotenv
load_dotenv() 

class WhatsappClass:
    def __init__(self, db):
        self.db = db

    def send(self): 
        url = "https://graph.facebook.com/v22.0/790586727468909/messages"
        token = os.getenv('META_TOKEN')

        payload = {
            "messaging_product": "whatsapp",
            "to": "56979670323",  # Número destino
            "type": "template",
            "template": {
                "name": "envio_dte_cliente_generado_v2",  # nombre EXACTO de tu plantilla
                "language": {"code": "es"},
                "components": [
                    {
                        "type": "body",
                        "parameters": [
                            {"type": "text", "text": "Boleta Electrónica"}, 
                            {"type": "text", "text": "5544"},       # N° Boleta
                            {"type": "text", "text": "28-07-2022"}, # Fecha
                            {"type": "text", "text": "50000"},      # Monto
                        ]
                    },
                    {
                        "type": "button",
                        "sub_type": "url",
                        "index": "0",
                        "parameters": [
                            {
                                "type": "text",
                                "text": "2000"  # valor dinámico para {{1}}
                            }
                        ]
                    }
                ]
            }
        }

        print

        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }

        response = requests.post(url, json=payload, headers=headers)

        print(response.status_code)
        print(response.json())