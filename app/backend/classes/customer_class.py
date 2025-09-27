from app.backend.db.models import CustomerModel, RegionModel, CommuneModel, CustomerProductDiscountModel, SettingModel, UserModel
from datetime import datetime

class CustomerClass:
    def __init__(self, db):
        self.db = db

    def discounts(self, identification_number):
        try:
            customer = self.db.query(CustomerModel.id).filter(CustomerModel.identification_number == identification_number).first()

            data = (
                self.db.query(
                    CustomerProductDiscountModel.id, 
                    CustomerProductDiscountModel.product_id,
                    CustomerProductDiscountModel.customer_id,
                    CustomerProductDiscountModel.discount_percentage
                )
                .filter(CustomerProductDiscountModel.customer_id == customer.id)
                .order_by(CustomerProductDiscountModel.id)
            )

            serialized_data = [{
                "id": customer_product_discount.id,
                "product_id": customer_product_discount.product_id,
                "customer_id": customer_product_discount.customer_id,
                "discount_percentage": customer_product_discount.discount_percentage
            } for customer_product_discount in data]

            return {
                "data": serialized_data
            }

        except Exception as e:
            error_message = str(e)
            return {"status": "error", "message": error_message}

    def get_all(self, page=0, items_per_page=10, name=None, rut=None):
        try:
            query = (
                self.db.query(
                    CustomerModel.id, 
                    CustomerModel.social_reason,
                    CustomerModel.identification_number,
                    CustomerModel.address,
                    CustomerModel.phone,
                    CustomerModel.email
                )
                .order_by(CustomerModel.id)
            )

            # Aplicar filtros de búsqueda si se proporcionan
            if name and name.strip():
                query = query.filter(CustomerModel.social_reason.ilike(f"%{name.strip()}%"))

            if rut and rut.strip():
                query = query.filter(CustomerModel.identification_number == rut.strip())

            if page > 0:
                total_items = query.count()
                total_pages = (total_items + items_per_page - 1)

                if page < 1 or page > total_pages:
                    return {"status": "error", "message": "Invalid page number"}

                data = query.offset((page - 1) * items_per_page).limit(items_per_page).all()

                if not data:
                    return {"status": "error", "message": "No data found"}

                serialized_data = [{
                    "id": customer.id,
                    "social_reason": customer.social_reason,
                    "identification_number": customer.identification_number,
                    "address": customer.address,
                    "phone": customer.phone,
                } for customer in data]

                return {
                    "total_items": total_items,
                    "total_pages": total_pages,
                    "current_page": page,
                    "items_per_page": items_per_page,
                    "data": serialized_data
                }

            else:
                data = query.all()

                serialized_data = [{
                    "id": customer.id,
                    "social_reason": customer.social_reason,
                    "identification_number": customer.identification_number,
                    "address": customer.address,
                    "phone": customer.phone,
                } for customer in data]

                return serialized_data

        except Exception as e:
            error_message = str(e)
            return {"status": "error", "message": error_message}
    
    def update(self, id, form_data):
        existing_customer = self.db.query(CustomerModel).filter(CustomerModel.id == id).one_or_none()

        if not existing_customer:
            return "No data found"

        try:
            existing_customer.identification_number = form_data.identification_number
            existing_customer.social_reason = form_data.social_reason
            existing_customer.region_id = form_data.region_id
            existing_customer.activity = form_data.activity
            existing_customer.commune_id = form_data.commune_id
            existing_customer.address = form_data.address
            existing_customer.phone = form_data.phone
            existing_customer.email = form_data.email
            existing_customer.updated_date = datetime.utcnow()

            self.db.commit()
            self.db.refresh(existing_customer)

            # Manejar actualización de descuentos de productos
            if hasattr(form_data, 'product_discounts') and form_data.product_discounts:
                # Eliminar descuentos existentes
                existing_discounts = self.db.query(CustomerProductDiscountModel).filter(
                    CustomerProductDiscountModel.customer_id == id
                ).all()
                
                for discount in existing_discounts:
                    self.db.delete(discount)
                
                # Agregar nuevos descuentos
                for product_id, discount_percentage in form_data.product_discounts.items():
                    if discount_percentage > 0:
                        discount_record = CustomerProductDiscountModel(
                            customer_id=id,
                            product_id=int(product_id),
                            discount_percentage=float(discount_percentage)
                        )
                        self.db.add(discount_record)
                
                self.db.commit()

            return "Customer updated successfully"
        except Exception as e:
            self.db.rollback()
            error_message = str(e)
            return {"status": "error", "message": error_message}
        
    def store(self, customer_inputs):
        try:
            new_customer = CustomerModel(
                region_id=customer_inputs.region_id,
                commune_id=customer_inputs.commune_id,
                identification_number=customer_inputs.identification_number,
                social_reason=customer_inputs.social_reason,
                activity=customer_inputs.activity,
                address=customer_inputs.address,
                phone=customer_inputs.phone,
                email=customer_inputs.email,
                added_date=datetime.utcnow(),
                updated_date=datetime.utcnow()
            )

            self.db.add(new_customer)
            self.db.commit()
            self.db.refresh(new_customer)

            if customer_inputs.product_discounts:
                for product_id, discount_percentage in customer_inputs.product_discounts.items():
                    if discount_percentage > 0:
                        discount_record = CustomerProductDiscountModel(
                            customer_id=new_customer.id,
                            product_id=int(product_id),
                            discount_percentage=float(discount_percentage)
                        )
                        self.db.add(discount_record)
                
                self.db.commit()

            return {
                "status": "Cliente registrado exitosamente.",
                "customer_id": new_customer.id
            }

        except Exception as e:
            self.db.rollback()
            return {"status": "error", "message": str(e)}

    def get_by_identification_number(self, identification_number):
        customer = self.db.query(CustomerModel).filter(CustomerModel.identification_number == identification_number).first()

        if not customer:
            return {"status": "error", "message": "No data found"}
        
        return customer
    
    def get(self, id):
        try:
            data_query = self.db.query(
                CustomerModel,
                RegionModel.id.label("region_id"),
                CommuneModel.id.label("commune_id")
            ).join(RegionModel, RegionModel.id == CustomerModel.region_id, isouter=True).join(CommuneModel, CommuneModel.id == CustomerModel.commune_id, isouter=True).filter(CustomerModel.id == id).first()

            if data_query:
                customer_data = {
                    "id": data_query.CustomerModel.id,
                    "social_reason": data_query.CustomerModel.social_reason,
                    "identification_number": data_query.CustomerModel.identification_number,
                    "address": data_query.CustomerModel.address,
                    "phone": data_query.CustomerModel.phone,
                    "email": data_query.CustomerModel.email,
                    "region_id": int(data_query.region_id) if data_query.region_id is not None else None,
                    "commune_id": int(data_query.commune_id) if data_query.commune_id is not None else None,
                    "activity": data_query.CustomerModel.activity,
                }

                return {"customer_data": customer_data}

            else:
                return {"error": "No se encontraron datos para el campo especificado."}
            
        except Exception as e:
            return {"error": str(e)}
        
    def apply_settings_discount(self, customer_id, product_id):
        """
        Aplica el descuento de settings a un producto específico para un cliente
        """
        try:
            # Obtener el descuento de settings
            setting = self.db.query(SettingModel).filter(SettingModel.id == 1).first()
            
            if not setting or not setting.prepaid_discount:
                return {"status": "error", "message": "No se encontró descuento en configuración"}
            
            discount_percentage = setting.prepaid_discount
            
            # Verificar si ya existe un descuento para este producto/cliente
            existing_discount = self.db.query(CustomerProductDiscountModel).filter(
                CustomerProductDiscountModel.customer_id == customer_id,
                CustomerProductDiscountModel.product_id == product_id
            ).first()
            
            if existing_discount:
                # Actualizar el descuento existente
                existing_discount.discount_percentage = discount_percentage
                message = f"Descuento actualizado a {discount_percentage}% desde configuración"
            else:
                # Crear nuevo descuento
                new_discount = CustomerProductDiscountModel(
                    customer_id=customer_id,
                    product_id=product_id,
                    discount_percentage=discount_percentage
                )
                self.db.add(new_discount)
                message = f"Descuento de {discount_percentage}% aplicado desde configuración"
            
            self.db.commit()
            
            return {
                "status": "success", 
                "message": message,
                "discount_percentage": discount_percentage
            }
            
        except Exception as e:
            self.db.rollback()
            return {"status": "error", "message": str(e)}

    def delete_product_discount(self, customer_id, product_id):
        """
        Elimina un descuento específico de producto para un cliente
        """
        try:
            # Buscar el descuento específico
            discount = self.db.query(CustomerProductDiscountModel).filter(
                CustomerProductDiscountModel.customer_id == customer_id,
                CustomerProductDiscountModel.product_id == product_id
            ).first()
            
            if not discount:
                return {"status": "error", "message": "Descuento no encontrado"}
            
            # Eliminar el descuento
            self.db.delete(discount)
            self.db.commit()
            
            return {"status": "success", "message": "Descuento eliminado exitosamente"}
            
        except Exception as e:
            self.db.rollback()
            return {"status": "error", "message": str(e)}

    def show(self, rut):
        """Obtiene información completa del cliente y usuario asociado por RUT"""
        try:
            # Buscar el cliente por RUT
            customer = self.db.query(CustomerModel).filter(CustomerModel.identification_number == rut).first()
            if not customer:
                return {"status": "error", "message": "Cliente no encontrado"}
            
            # Buscar el usuario asociado por RUT
            user = self.db.query(UserModel).filter(UserModel.rut == rut).first()
            
            # Obtener información de región y comuna por separado
            region = None
            commune = None
            
            if customer.region_id:
                region_obj = self.db.query(RegionModel).filter(RegionModel.id == customer.region_id).first()
                region = region_obj.region if region_obj else None
            
            if customer.commune_id:
                commune_obj = self.db.query(CommuneModel).filter(CommuneModel.id == customer.commune_id).first()
                commune = commune_obj.commune if commune_obj else None
            
            # Preparar datos del cliente
            customer_data = {
                "id": customer.id,
                "identification_number": customer.identification_number,
                "social_reason": customer.social_reason,
                "activity": customer.activity,
                "address": customer.address,
                "phone": customer.phone,
                "email": customer.email,
                "region_id": customer.region_id,
                "commune_id": customer.commune_id,
                "region_name": region,
                "commune_name": commune,
                "added_date": customer.added_date.strftime("%Y-%m-%d %H:%M:%S") if customer.added_date else None,
                "updated_date": customer.updated_date.strftime("%Y-%m-%d %H:%M:%S") if customer.updated_date else None
            }
            
            # Preparar datos del usuario si existe
            user_data = None
            if user:
                user_data = {
                    "id": user.id,
                    "rol_id": user.rol_id,
                    "rut": user.rut,
                    "full_name": user.full_name,
                    "email": user.email,
                    "phone": user.phone,
                    "added_date": user.added_date.strftime("%Y-%m-%d %H:%M:%S") if user.added_date else None,
                    "updated_date": user.updated_date.strftime("%Y-%m-%d %H:%M:%S") if user.updated_date else None
                }
            
            return {
                "status": "success",
                "customer": customer_data,
                "user": user_data
            }
            
        except Exception as e:
            return {"status": "error", "message": str(e)}

    def profile_update(self, rut, profile_data):
        """Actualiza el perfil del cliente por RUT"""
        try:
            # Buscar el cliente por RUT
            customer = self.db.query(CustomerModel).filter(CustomerModel.identification_number == rut).first()
            if not customer:
                return {"status": "error", "message": "Cliente no encontrado"}
            
            # Actualizar solo los campos que se proporcionaron
            if profile_data.social_reason is not None:
                customer.social_reason = profile_data.social_reason
            if profile_data.activity is not None:
                customer.activity = profile_data.activity
            if profile_data.address is not None:
                customer.address = profile_data.address
            if profile_data.phone is not None:
                customer.phone = profile_data.phone
            if profile_data.email is not None:
                customer.email = profile_data.email
            if profile_data.region_id is not None:
                customer.region_id = profile_data.region_id
            if profile_data.commune_id is not None:
                customer.commune_id = profile_data.commune_id
            
            # Actualizar fecha de modificación
            customer.updated_date = datetime.now()
            
            # Guardar cambios
            self.db.commit()
            
            return {"status": "success", "message": "Perfil actualizado exitosamente"}
            
        except Exception as e:
            self.db.rollback()
            return {"status": "error", "message": str(e)}

    def delete(self, id):
        try:
            # Buscar el cliente
            customer = self.db.query(CustomerModel).filter(CustomerModel.id == id).first()
            if not customer:
                return "No data found"
            
            # Buscar el usuario asociado por RUT
            user = self.db.query(UserModel).filter(UserModel.rut == customer.identification_number).first()
            
            # Eliminar el cliente
            self.db.delete(customer)
            
            # Eliminar el usuario si existe
            if user:
                self.db.delete(user)
            
            self.db.commit()
            return 'success'
            
        except Exception as e:
            self.db.rollback()
            error_message = str(e)
            return f"Error: {error_message}"