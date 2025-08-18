from app.backend.db.models import CustomerModel, RegionModel, CommuneModel, CustomerProductDiscountModel
from datetime import datetime

class CustomerClass:
    def __init__(self, db):
        self.db = db

    def discounts(self, rut):
        try:
            customer_id = self.db.query(CustomerModel.id).filter(CustomerModel.identification_number == rut).first()

            data = (
                self.db.query(
                    CustomerProductDiscountModel.id, 
                    CustomerProductDiscountModel.product_id,
                    CustomerProductDiscountModel.customer_id,
                    CustomerProductDiscountModel.discount_percentage
                )
                .filter(CustomerProductDiscountModel.customer_id == customer_id)
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

    def get_all(self, page=0, items_per_page=10):
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
        
    def delete(self, id):
        try:
            data = self.db.query(CustomerModel).filter(CustomerModel.id == id).first()
            if data:
                self.db.delete(data)
                self.db.commit()
                return 'success'
            else:
                return "No data found"
        except Exception as e:
            error_message = str(e)
            return f"Error: {error_message}"