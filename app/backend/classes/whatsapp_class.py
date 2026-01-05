import requests
import os
import hashlib
from dotenv import load_dotenv
from app.backend.classes.setting_class import SettingClass
from app.backend.db.models import UserModel, BudgetModel, CustomerModel, BudgetProductModel, ProductModel
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

    def review_budget(self, budget_id, total):
        url = "https://graph.facebook.com/v22.0/790586727468909/messages"
        token = os.getenv("META_TOKEN")

        # 1️⃣ Obtener presupuesto
        budget = (
            self.db.query(BudgetModel)
            .filter(BudgetModel.id == budget_id)
            .first()
        )

        if not budget:
            print("[WHATSAPP] Presupuesto no encontrado")
            return None

        # 2️⃣ Obtener cliente
        customer = (
            self.db.query(CustomerModel)
            .filter(CustomerModel.id == budget.customer_id)
            .first()
        )

        if not customer or not customer.phone:
            print("[WHATSAPP] Cliente sin teléfono")
            return None

        # 3️⃣ Obtener productos
        products = (
            self.db.query(
                ProductModel.product,
                BudgetProductModel.quantity
            )
            .join(BudgetProductModel, BudgetProductModel.product_id == ProductModel.id)
            .filter(BudgetProductModel.budget_id == budget_id)
            .all()
        )

        # 4️⃣ Formatear productos (con saltos de línea)
        products_text = "\n".join([
            f"{p.product} x {p.quantity}" for p in products
        ])

        # 5️⃣ Formatear total
        total_formatted = f"{total:,}".replace(",", ".") + " CLP"

        # 6️⃣ Formatear teléfono (Chile)
        phone = str(customer.phone).strip()
        if not phone.startswith("56"):
            phone = "56" + phone

        # 7️⃣ Payload CORRECTO
        payload = {
            "messaging_product": "whatsapp",
            "to": phone,
            "type": "template",
            "template": {
                "name": "revision_presupuesto",
                "language": {"code": "es"},
                "components": [
                    {
                        "type": "body",
                        "parameters": [
                            {"type": "text", "text": str(budget_id)},
                            {"type": "text", "text": total_formatted},
                            {"type": "text", "text": products_text}
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

        print("[WHATSAPP] STATUS:", response.status_code)
        print("[WHATSAPP] RESPONSE:", response.text)

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
        try:
            from_number = message.get("from")
            message_type = message.get("type")

            print(f"[WHATSAPP MESSAGE] From: {from_number}, Type: {message_type}")

            # 🔘 BOTONES (Aceptar / Rechazar)
            if message_type == "button":
                button_text = message.get("button", {}).get("text")

                print(f"[WHATSAPP BUTTON] Action: {button_text}")

                # 🔑 Obtener presupuesto asociado a ese teléfono
                budget_id = self.get_budget_id_by_phone(from_number)

                if not budget_id:
                    print("[WHATSAPP BUTTON] No budget context found")
                    return

                if button_text == "Aceptar":
                    self.approve_budget(budget_id)

                elif button_text == "Rechazar":
                    self.reject_budget(budget_id)

            # 💬 TEXTO NORMAL
            elif message_type == "text":
                text_body = message.get("text", {}).get("body", "")
                print(f"[WHATSAPP TEXT] {text_body}")

            return {"status": "success"}

        except Exception as e:
            print(f"[WHATSAPP MESSAGE ERROR] {str(e)}")


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