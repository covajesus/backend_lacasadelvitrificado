import requests
import os
import hashlib
from dotenv import load_dotenv
from datetime import datetime
from app.backend.classes.setting_class import SettingClass
from app.backend.db.models import UserModel, BudgetModel, CustomerModel, BudgetProductModel, ProductModel, WhatsAppMessageModel
load_dotenv() 

class WhatsappClass:
    def __init__(self, db):
        self.db = db

    def send_dte(self, customer_phone, dte_type, folio, date, amount, dynamic_value, sale_id: int = None): 
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
        response_data = response.json()
        print(f"[WHATSAPP] Response: {response_data}")
        
        # Guardar el message_id si el envío fue exitoso
        if response.status_code == 200 and "messages" in response_data:
            message_id = response_data["messages"][0].get("id")
            if message_id:
                self._save_message(
                    message_id=message_id,
                    recipient_phone=customer_phone_formatted,
                    message_type="template",
                    template_name="envio_dte_cliente_generado_v5",
                    status="sent",
                    sale_id=sale_id
                )
        
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
        response_data = response.json()
        print(f"[WHATSAPP ALERT] Response: {response_data}")
        
        # Guardar el message_id si el envío fue exitoso
        if response.status_code == 200 and "messages" in response_data:
            message_id = response_data["messages"][0].get("id")
            if message_id:
                self._save_message(
                    message_id=message_id,
                    recipient_phone=admin_phone_formatted,
                    message_type="template",
                    template_name="alerta_nueva_orden",
                    status="sent"
                )
        
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
        response_data = response.json()
        print(f"[WHATSAPP ALERT] Response: {response_data}")
        
        # Guardar el message_id si el envío fue exitoso
        if response.status_code == 200 and "messages" in response_data:
            message_id = response_data["messages"][0].get("id")
            if message_id:
                self._save_message(
                    message_id=message_id,
                    recipient_phone=customer_phone_formatted,
                    message_type="template",
                    template_name="alerta_pedido_enviado",
                    status="sent"
                )
        
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
        response_data = response.json()
        print(f"[WHATSAPP ALERT] Response: {response_data}")
        
        # Guardar el message_id si el envío fue exitoso
        if response.status_code == 200 and "messages" in response_data:
            message_id = response_data["messages"][0].get("id")
            if message_id:
                self._save_message(
                    message_id=message_id,
                    recipient_phone=customer_phone_formatted,
                    message_type="template",
                    template_name="alerta_pago_rechazado",
                    status="sent"
                )
        
        return response

    

    # ===============================
    # ENVÍO DEL MENSAJE
    # ===============================
    def review_budget(self, budget_id: int, total: int, customer_phone: str = None, customer_name: str = None):

        url = "https://graph.facebook.com/v22.0/790586727468909/messages"
        token = os.getenv("META_TOKEN")

        # Presupuesto
        budget = self.db.query(BudgetModel).filter_by(id=budget_id).first()
        if not budget:
            return None

        # Cliente - Si se proporcionan customer_phone y customer_name, usarlos directamente
        # Si no, buscar en la base de datos
        if customer_phone and customer_name:
            phone = customer_phone
            customer_name_used = customer_name
        else:
            customer = self.db.query(CustomerModel).filter_by(id=budget.customer_id).first()
            if not customer or not customer.phone:
                return None
            phone = customer.phone
            customer_name_used = customer.social_reason

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

        phone = str(phone)
        if not phone.startswith("56"):
            phone = "56" + phone

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

        response = requests.post(url, json=payload, headers=headers)
        response_data = response.json()
        print(f"[WHATSAPP] Response: {response_data}")
        
        # Guardar el message_id si el envío fue exitoso
        if response.status_code == 200 and "messages" in response_data:
            message_id = response_data["messages"][0].get("id")
            if message_id:
                self._save_message(
                    message_id=message_id,
                    recipient_phone=phone,
                    message_type="template",
                    template_name="revision_presupuesto",
                    status="sent",
                    budget_id=budget_id
                )
        
        return response

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
        try:
            print("📬 STATUS WHATSAPP RECIBIDO")
            print(f"📬 Status completo: {status}")

            status_type = status.get("status")
            message_id = status.get("id", "").strip()
            recipient = status.get("recipient_id")
            error = status.get("errors", [])
            error_code = error[0].get("code") if error and len(error) > 0 else None
            error_message = error[0].get("message") if error and len(error) > 0 else None

            print(f"➡ Estado: {status_type}")
            print(f"➡ Message ID: '{message_id}' (tipo: {type(message_id)})")
            print(f"➡ Destinatario: {recipient}")
            if error_code:
                print(f"➡ Error Code: {error_code}")
                print(f"➡ Error Message: {error_message}")

            # Validar que tenemos message_id
            if not message_id:
                print("⚠️ ERROR: No se recibió message_id en el status")
                return

            # Buscar el mensaje en la BD por message_id
            print(f"🔍 Buscando mensaje con message_id: '{message_id}'")
            whatsapp_message = (
                self.db.query(WhatsAppMessageModel)
                .filter(WhatsAppMessageModel.message_id == message_id)
                .first()
            )

            if whatsapp_message:
                print(f"✅ Mensaje encontrado en BD (ID: {whatsapp_message.id})")
                print(f"   Estado actual: {whatsapp_message.status}")
                print(f"   Nuevo estado: {status_type}")
                
                # Actualizar el estado del mensaje
                whatsapp_message.status = status_type
                whatsapp_message.updated_date = datetime.now()

                if status_type == "sent":
                    whatsapp_message.sent_date = datetime.now()
                    print(f"   📤 Actualizado sent_date")
                elif status_type == "delivered":
                    whatsapp_message.delivered_date = datetime.now()
                    print(f"   📬 Actualizado delivered_date")
                elif status_type == "read":
                    whatsapp_message.read_date = datetime.now()
                    print(f"   👁️ Actualizado read_date")
                elif status_type == "failed":
                    whatsapp_message.error_code = str(error_code) if error_code else None
                    whatsapp_message.error_message = error_message
                    print(f"   ❌ Actualizado error_code y error_message")

                try:
                    self.db.commit()
                    print(f"✅ Estado actualizado en BD: {status_type} para mensaje {message_id}")
                except Exception as commit_error:
                    print(f"❌ ERROR al hacer commit: {str(commit_error)}")
                    self.db.rollback()
                    raise
            else:
                print(f"⚠️ Mensaje NO encontrado en BD con message_id: '{message_id}'")
                print(f"   Buscando todos los message_id en BD para comparar...")
                all_messages = self.db.query(WhatsAppMessageModel.message_id).all()
                print(f"   Total de mensajes en BD: {len(all_messages)}")
                if all_messages:
                    print(f"   Primeros 5 message_id en BD: {[m[0] for m in all_messages[:5]]}")
                
                # Si no existe, crear un nuevo registro (puede pasar si el webhook llega antes de guardar)
                print(f"   Creando nuevo registro...")
                new_message = WhatsAppMessageModel(
                    message_id=message_id,
                    recipient_phone=recipient,
                    status=status_type,
                    error_code=str(error_code) if error_code else None,
                    error_message=error_message,
                    sent_date=datetime.now() if status_type == "sent" else None,
                    delivered_date=datetime.now() if status_type == "delivered" else None,
                    read_date=datetime.now() if status_type == "read" else None
                )
                self.db.add(new_message)
                try:
                    self.db.commit()
                    print(f"✅ Nuevo registro creado para mensaje {message_id} con estado {status_type}")
                except Exception as commit_error:
                    print(f"❌ ERROR al crear nuevo registro: {str(commit_error)}")
                    self.db.rollback()
                    raise
                    
        except Exception as e:
            print(f"❌ ERROR en handle_status: {str(e)}")
            import traceback
            traceback.print_exc()
            self.db.rollback()

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
        
        # Guardar el message_id si el envío fue exitoso
        if response.status_code == 200:
            response_data = response.json()
            if "messages" in response_data:
                message_id = response_data["messages"][0].get("id")
                if message_id:
                    self._save_message(
                        message_id=message_id,
                        recipient_phone=phone,
                        message_type="text",
                        status="sent"
                    )

    def _save_message(self, message_id: str, recipient_phone: str, message_type: str, template_name: str = None, status: str = "sent", budget_id: int = None, sale_id: int = None):
        """
        Guarda un mensaje de WhatsApp en la BD
        """
        try:
            # Verificar si ya existe
            existing = (
                self.db.query(WhatsAppMessageModel)
                .filter(WhatsAppMessageModel.message_id == message_id)
                .first()
            )
            
            if existing:
                # Actualizar si ya existe
                existing.status = status
                existing.updated_date = datetime.now()
                if budget_id is not None:
                    existing.budget_id = budget_id
                if sale_id is not None:
                    existing.sale_id = sale_id
            else:
                # Crear nuevo registro
                whatsapp_message = WhatsAppMessageModel(
                    message_id=message_id,
                    recipient_phone=recipient_phone,
                    message_type=message_type,
                    template_name=template_name,
                    budget_id=budget_id,
                    sale_id=sale_id,
                    status=status,
                    sent_date=datetime.now()
                )
                self.db.add(whatsapp_message)
            
            self.db.commit()
            print(f"✅ Mensaje guardado/actualizado en BD: {message_id} (budget_id: {budget_id}, sale_id: {sale_id})")
        except Exception as e:
            print(f"❌ Error guardando mensaje en BD: {str(e)}")
            self.db.rollback()

    def get_messages_by_budget(self, budget_id: int):
        """
        Obtiene todos los mensajes de WhatsApp relacionados con un presupuesto
        """
        messages = (
            self.db.query(WhatsAppMessageModel)
            .filter(WhatsAppMessageModel.budget_id == budget_id)
            .order_by(WhatsAppMessageModel.added_date.desc())
            .all()
        )
        return messages

    def get_messages_by_sale(self, sale_id: int):
        """
        Obtiene todos los mensajes de WhatsApp relacionados con una venta
        """
        messages = (
            self.db.query(WhatsAppMessageModel)
            .filter(WhatsAppMessageModel.sale_id == sale_id)
            .order_by(WhatsAppMessageModel.added_date.desc())
            .all()
        )
        return messages

    def get_message_by_id(self, message_id: str):
        """
        Obtiene un mensaje por su message_id de WhatsApp
        """
        message = (
            self.db.query(WhatsAppMessageModel)
            .filter(WhatsAppMessageModel.message_id == message_id)
            .first()
        )
        return message

    def get_all_messages(self, budget_id: int = None, sale_id: int = None, status: str = None, limit: int = 100):
        """
        Obtiene todos los mensajes con filtros opcionales
        """
        query = self.db.query(WhatsAppMessageModel)
        
        if budget_id:
            query = query.filter(WhatsAppMessageModel.budget_id == budget_id)
        if sale_id:
            query = query.filter(WhatsAppMessageModel.sale_id == sale_id)
        if status:
            query = query.filter(WhatsAppMessageModel.status == status)
        
        messages = query.order_by(WhatsAppMessageModel.added_date.desc()).limit(limit).all()
        return messages
