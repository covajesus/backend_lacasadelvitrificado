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

    

    # ===============================
    # ENVÍO DEL MENSAJE
    # ===============================
    def review_budget(self, budget_id: int, total: int):

        url = "https://graph.facebook.com/v22.0/790586727468909/messages"
        token = os.getenv("META_TOKEN")

        # Presupuesto
        budget = self.db.query(BudgetModel).filter_by(id=budget_id).first()
        if not budget:
            return None

        # Cliente
        customer = self.db.query(CustomerModel).filter_by(id=budget.customer_id).first()
        if not customer or not customer.phone:
            return None

        # Productos
        products = (
            self.db.query(ProductModel.product, BudgetProductModel.quantity)
            .join(BudgetProductModel, BudgetProductModel.product_id == ProductModel.id)
            .filter(BudgetProductModel.budget_id == budget_id)
            .all()
        )

        products_text = "\n".join([
            f"{p.product} x {p.quantity}" for p in products
        ])

        total_formatted = f"{total:,}".replace(",", ".")

        phone = str(customer.phone)
        if not phone.startswith("56"):
            phone = "56" + phone

        phone = "56928783036"
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
                    },
                    {
                        "type": "button",
                        "sub_type": "quick_reply",
                        "index": "0",
                        "parameters": [
                            {"type": "payload", "payload": f"accept_{budget_id}"}
                        ]
                    },
                    {
                        "type": "button",
                        "sub_type": "quick_reply",
                        "index": "1",
                        "parameters": [
                            {"type": "payload", "payload": f"reject_{budget_id}"}
                        ]
                    }
                ]
            }
        }

        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }

        return requests.post(url, json=payload, headers=headers)

    def handle_message(self, message):
        print("📩 MENSAJE:", message)
        print(f"[WHATSAPP_HANDLE] Tipo de mensaje: {message.get('type')}")

        if message.get("type") != "button":
            print(f"[WHATSAPP_HANDLE] Mensaje no es de tipo button, ignorando. Tipo: {message.get('type')}")
            return

        payload = message.get("button", {}).get("payload")  # accept_38
        phone = message.get("from")
        print(f"[WHATSAPP_HANDLE] Payload recibido: {payload}, Phone: {phone}")

        if not payload or "_" not in payload:
            print(f"[WHATSAPP_HANDLE] Payload inválido o sin '_': {payload}")
            return

        action, budget_id = payload.split("_", 1)
        action = action.lower()
        print(f"[WHATSAPP_HANDLE] Action: {action}, Budget ID: {budget_id}")

        budget = (
            self.db
            .query(BudgetModel)
            .filter(BudgetModel.id == int(budget_id))
            .first()
        )

        if not budget:
            print("⚠️ Presupuesto no existe (reintento ignorado)")
            return {"status": "ignored"}

        # 🔒 Ya procesado - pero si es accept y ya está aceptado, no hacer nada
        # Si es reject y ya está rechazado, tampoco hacer nada
        if action == "accept" and budget.status_id == 1:
            print(f"[WHATSAPP] Presupuesto {budget_id} ya está aceptado, no hacer nada")
            self.send_autoreply(
                phone,
                "⚠️ Este presupuesto ya fue aceptado anteriormente."
            )
            return
        
        if action == "reject" and budget.status_id == 2:
            print(f"[WHATSAPP] Presupuesto {budget_id} ya está rechazado, no hacer nada")
            self.send_autoreply(
                phone,
                "⚠️ Este presupuesto ya fue rechazado anteriormente."
            )
            return

        if action == "accept":
            print(f"[WHATSAPP] Procesando aceptación de presupuesto {budget_id} desde WhatsApp")
            # Llamar al método accept de BudgetClass para crear el pedido
            from app.backend.classes.budget_class import BudgetClass
            budget_class = BudgetClass(self.db)
            print(f"[WHATSAPP] Llamando a BudgetClass.accept({budget_id})")
            accept_result = budget_class.accept(int(budget_id))
            print(f"[WHATSAPP] Resultado de accept: {accept_result}")
            
            if isinstance(accept_result, dict) and accept_result.get("status") == "error":
                print(f"❌ Error al aceptar presupuesto {budget_id}: {accept_result.get('message')}")
                self.send_autoreply(
                    phone,
                    f"❌ Ocurrió un error al procesar la aceptación del presupuesto: {accept_result.get('message')}"
                )
            else:
                sale_id = accept_result.get('sale_id') if isinstance(accept_result, dict) else 'N/A'
                print(f"[WHATSAPP] ✅ Presupuesto {budget_id} aceptado exitosamente. Sale ID: {sale_id}")
                self.send_autoreply(
                    phone,
                    "✅ Gracias por aceptar el presupuesto.\nNos pondremos en contacto contigo a la brevedad."
                )

        elif action == "reject":
            budget.status_id = 2
            self.db.commit()

            self.send_autoreply(
                phone,
                "❌ Hemos recibido el rechazo del presupuesto.\nGracias por tu respuesta."
            )

            print(f"❌ Presupuesto {budget_id} rechazado")

    def handle_status(self, status: dict):
        """
        Maneja estados enviados por WhatsApp:
        sent, delivered, read, failed
        """
        print("📬 STATUS WHATSAPP RECIBIDO")
        print(status)

        status_type = status.get("status")
        message_id = status.get("id")
        recipient = status.get("recipient_id")

        print(f"➡ Estado: {status_type}")
        print(f"➡ Message ID: {message_id}")
        print(f"➡ Destinatario: {recipient}")

        # Aquí puedes guardar en BD si quieres
        # ejemplo:
        # if status_type == "read":
        #     marcar_mensaje_leido(message_id)

    def send_autoreply(self, phone: str, text: str):
        url = "https://graph.facebook.com/v22.0/790586727468909/messages"
        token = os.getenv("META_TOKEN")

        if not phone.startswith("56"):
            phone = "56" + phone

        payload = {
            "messaging_product": "whatsapp",
            "to": phone,
            "type": "text",
            "text": {
                "body": text
            }
        }

        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }

        response = requests.post(url, json=payload, headers=headers)

        print("📨 AUTORESPONDER:", response.status_code, response.json())

