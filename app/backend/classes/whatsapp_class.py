import requests
import os
import hashlib
from dotenv import load_dotenv
from app.backend.classes.setting_class import SettingClass
from app.backend.db.models import UserModel, BudgetModel, CustomerModel
load_dotenv() 

class WhatsappClass:
    def __init__(self, db):
        self.db = db

    def send_dte(self, customer_phone, dte_type, folio, date, amount, dynamic_value): 
        url = "https://graph.facebook.com/v22.0/790586727468909/messages"
        token = os.getenv('META_TOKEN')

        # Formatear el número de teléfono
        phone_str = str(customer_phone).strip()
        if not phone_str.startswith("56"):
            customer_phone_formatted = "56" + phone_str
        else:
            customer_phone_formatted = phone_str

        payload = {
            "messaging_product": "whatsapp",
            "to": customer_phone_formatted,
            "type": "template",
            "template": {
                "name": "envio_dte_cliente_generado_v5",  # nombre EXACTO de tu plantilla
                "language": {"code": "es"},
                "components": [
                    {
                        "type": "body",
                        "parameters": [
                            {"type": "text", "text": dte_type}, 
                            {"type": "text", "text": str(folio)},       # N° Boleta/Factura
                            {"type": "text", "text": date},             # Fecha
                            {"type": "text", "text": str(amount)},      # Monto
                        ]
                    },
                    {
                        "type": "button",
                        "sub_type": "url",
                        "index": "0",
                        "parameters": [
                            {
                                "type": "text",
                                "text": str(dynamic_value)  # valor dinámico para {{1}}
                            }
                        ]
                    }
                ]
            }
        }

        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }

        response = requests.post(url, json=payload, headers=headers)

        print(f"[WHATSAPP] Status: {response.status_code}")
        print(f"[WHATSAPP] Response: {response.json()}")
        
        return response

    def send_new_order_alert(self, customer_name): 
        url = "https://graph.facebook.com/v22.0/790586727468909/messages"
        token = os.getenv('META_TOKEN')        
        setting_data = SettingClass(self.db).get(1)
        admin_phone = setting_data["setting_data"]["phone"]

        # Formatear el número de teléfono
        phone_str = str(admin_phone).strip()
        if not phone_str.startswith("56"):
            admin_phone_formatted = "56" + phone_str
        else:
            admin_phone_formatted = phone_str

        payload = {
            "messaging_product": "whatsapp",
            "to": admin_phone_formatted,
            "type": "template",
            "template": {
                "name": "alerta_nueva_orden",
                "language": {"code": "es"},
                "components": [
                    {
                        "type": "body",
                        "parameters": [
                            {"type": "text", "text": customer_name}
                        ]
                    }
                ]
            }
        }

        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }

        response = requests.post(url, json=payload, headers=headers)

        print(f"[WHATSAPP ALERT] Status: {response.status_code}")
        print(f"[WHATSAPP ALERT] Response: {response.json()}")
        
        return response

    def send_order_delivered_alert(self, customer_phone, id): 
        url = "https://graph.facebook.com/v22.0/790586727468909/messages"
        token = os.getenv('META_TOKEN')        

        # Formatear el número de teléfono
        phone_str = str(customer_phone).strip()
        if not phone_str.startswith("56"):
            customer_phone_formatted = "56" + phone_str
        else:
            customer_phone_formatted = phone_str

        payload = {
            "messaging_product": "whatsapp",
            "to": customer_phone_formatted,
            "type": "template",
            "template": {
                "name": "alerta_pedido_enviado",
                "language": {"code": "es"},
                "components": [
                    {
                        "type": "body",
                        "parameters": [
                            {"type": "text", "text": id}
                        ]
                    }
                ]
            }
        }

        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }

        response = requests.post(url, json=payload, headers=headers)

        print(f"[WHATSAPP ALERT] Status: {response.status_code}")
        print(f"[WHATSAPP ALERT] Response: {response.json()}")
        
        return response

    def send_rejected_payment_alert(self, customer_phone, id): 
        url = "https://graph.facebook.com/v22.0/790586727468909/messages"
        token = os.getenv('META_TOKEN')        

        # Formatear el número de teléfono
        phone_str = str(customer_phone).strip()
        if not phone_str.startswith("56"):
            customer_phone_formatted = "56" + phone_str
        else:
            customer_phone_formatted = phone_str

        payload = {
            "messaging_product": "whatsapp",
            "to": customer_phone_formatted,
            "type": "template",
            "template": {
                "name": "alerta_pago_rechazado",
                "language": {"code": "es"},
                "components": [
                    {
                        "type": "body",
                        "parameters": [
                            {"type": "text", "text": id}
                        ]
                    }
                ]
            }
        }

        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }

        response = requests.post(url, json=payload, headers=headers)

        print(f"[WHATSAPP ALERT] Status: {response.status_code}")
        print(f"[WHATSAPP ALERT] Response: {response.json()}")
        
        return response

    def review_budget(self, budget_id, customer_name, total): 
        url = "https://graph.facebook.com/v22.0/790586727468909/messages"
        token = os.getenv('META_TOKEN')        

        # Buscar el presupuesto y el cliente para obtener su teléfono
        budget = (
            self.db.query(BudgetModel)
            .filter(BudgetModel.id == budget_id)
            .first()
        )

        if not budget:
            print(f"[WHATSAPP REVIEW BUDGET] No se encontró presupuesto {budget_id}")
            return None

        customer = (
            self.db.query(CustomerModel)
            .filter(CustomerModel.id == budget.customer_id)
            .first()
        )

        if not customer or not customer.phone:
            print(f"[WHATSAPP REVIEW BUDGET] No se encontró teléfono para el cliente {budget.customer_id}")
            return None

        customer_phone = customer.phone

        # Generar token MD5 con budget_id y rut del cliente
        token_string = f"{budget_id}_{customer.identification_number}_{customer.id}"
        token_md5 = hashlib.md5(token_string.encode()).hexdigest()

        # URL dinámica asociada al presupuesto (ajustar según frontend/backend)
        login_url = f"{budget_id}"

        # Formatear el número de teléfono del cliente
        phone_str = str(customer_phone).strip()
        if not phone_str.startswith("56"):
            customer_phone_formatted = "56" + phone_str
        else:
            customer_phone_formatted = phone_str

        payload = {
            "messaging_product": "whatsapp",
            "to": customer_phone_formatted,
            "type": "template",
            "template": {
                "name": "revision_presupuesto",
                "language": {"code": "es"},
                "components": [
                    {
                        "type": "body",
                        "parameters": [
                            {"type": "text", "text": str(budget_id)}
                        ]
                    },
                    {
                        "type": "button",
                        "sub_type": "url",
                        "index": "0",
                        "parameters": [
                            {
                                "type": "text",
                                "text": login_url
                            }
                        ]
                    }
                ]
            }
        }

        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }

        response = requests.post(url, json=payload, headers=headers)

        print(f"[WHATSAPP REVIEW BUDGET] Status: {response.status_code}")
        print(f"[WHATSAPP REVIEW BUDGET] Response: {response.json()}")
        print(f"[WHATSAPP REVIEW BUDGET] Token MD5: {token_md5}")
        print(f"[WHATSAPP REVIEW BUDGET] Login URL: {login_url}")
        
        return response

    def process_webhook(self, body):
        """
        Procesa los eventos recibidos del webhook de WhatsApp
        """
        try:
            print(f"[WHATSAPP WEBHOOK] Received: {body}")
            
            # WhatsApp envía los eventos en body['entry']
            if 'entry' in body:
                for entry in body['entry']:
                    if 'changes' in entry:
                        for change in entry['changes']:
                            if 'value' in change:
                                value = change['value']
                                
                                # Procesar mensajes recibidos
                                if 'messages' in value:
                                    for message in value['messages']:
                                        self.handle_message(message)
                                
                                # Procesar estados de mensajes
                                if 'statuses' in value:
                                    for status in value['statuses']:
                                        self.handle_status(status)
            
            return {"status": "success", "message": "Webhook processed"}
        except Exception as e:
            print(f"[WHATSAPP WEBHOOK] Error: {str(e)}")
            return {"status": "error", "message": str(e)}

    def handle_message(self, message):
        """
        Maneja un mensaje recibido de WhatsApp
        """
        try:
            message_id = message.get('id')
            from_number = message.get('from')
            message_type = message.get('type')
            timestamp = message.get('timestamp')
            
            print(f"[WHATSAPP MESSAGE] ID: {message_id}, From: {from_number}, Type: {message_type}")
            
            # Aquí puedes agregar lógica para procesar diferentes tipos de mensajes
            if message_type == 'text':
                text_body = message.get('text', {}).get('body', '')
                print(f"[WHATSAPP MESSAGE] Text: {text_body}")
            elif message_type == 'image':
                print(f"[WHATSAPP MESSAGE] Image received")
            elif message_type == 'document':
                print(f"[WHATSAPP MESSAGE] Document received")
            
            return {"status": "success"}
        except Exception as e:
            print(f"[WHATSAPP MESSAGE] Error handling message: {str(e)}")
            return {"status": "error", "message": str(e)}

    def handle_status(self, status):
        """
        Maneja el estado de un mensaje enviado
        """
        try:
            message_id = status.get('id')
            status_type = status.get('status')
            timestamp = status.get('timestamp')
            
            print(f"[WHATSAPP STATUS] Message ID: {message_id}, Status: {status_type}")
            
            # Aquí puedes agregar lógica para actualizar el estado de los mensajes
            # Por ejemplo, guardar en base de datos cuando un mensaje fue entregado o leído
            
            return {"status": "success"}
        except Exception as e:
            print(f"[WHATSAPP STATUS] Error handling status: {str(e)}")
            return {"status": "error", "message": str(e)}

    def verify_webhook(self, query_params):
        """
        Verifica el webhook cuando WhatsApp hace la verificación inicial
        """
        try:
            mode = query_params.get('hub.mode')
            token = query_params.get('hub.verify_token')
            challenge = query_params.get('hub.challenge')
            
            # Obtener el verify_token desde variables de entorno
            verify_token = os.getenv('WHATSAPP_VERIFY_TOKEN', 'your_verify_token_here')
            
            print(f"[WHATSAPP VERIFY] Mode: {mode}, Token: {token}, Challenge: {challenge}")
            
            # Verificar que el token coincida
            if mode == 'subscribe' and token == verify_token:
                print("[WHATSAPP VERIFY] Webhook verified successfully")
                # Retornar el challenge (WhatsApp espera el challenge como respuesta)
                return challenge if challenge else "OK"
            else:
                print("[WHATSAPP VERIFY] Webhook verification failed")
                return {"status": "error", "message": "Verification failed"}
        except Exception as e:
            print(f"[WHATSAPP VERIFY] Error: {str(e)}")
            return {"status": "error", "message": str(e)}