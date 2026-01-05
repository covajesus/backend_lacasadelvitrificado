from datetime import datetime
from sqlalchemy import func
from app.backend.db.models import (
    BudgetModel,
    BudgetProductModel,
    CustomerModel,
    ProductModel,
    SaleModel,
    SaleProductModel,
    InventoryModel,
    LotItemModel,
    LotModel,
    InventoryMovementModel,
    KardexValuesModel,
    InventoryLotItemModel
)
from app.backend.classes.whatsapp_class import WhatsappClass

class BudgetClass:
    def __init__(self, db):
        self.db = db

    def serialize_budget(self, budget_row):
        return {
            "id": budget_row.id,
            "customer_id": budget_row.customer_id,
            "customer_name": budget_row.customer_name,
            "status_id": budget_row.status_id if hasattr(budget_row, "status_id") else None,
            "subtotal": budget_row.subtotal,
            "shipping": budget_row.shipping if budget_row.shipping is not None else 0,
            "tax": budget_row.tax,
            "total": budget_row.total,
            "added_date": budget_row.added_date.strftime("%Y-%m-%d %H:%M:%S") if budget_row.added_date else None,
            "updated_date": budget_row.updated_date.strftime("%Y-%m-%d %H:%M:%S") if budget_row.updated_date else None
        }

    def get_all(self, rol_id=None, rut=None, page=0, items_per_page=10, identification_number=None, social_reason=None):
        try:
            # Obtener customer_id desde rut si no es rol 1 o 2
            customer = None
            if rut and (rol_id != 1 and rol_id != 2):
                # Convertir rut a string si es necesario
                rut_str = str(rut) if rut else None
                customer = (
                    self.db.query(CustomerModel)
                    .filter(CustomerModel.identification_number == rut_str)
                    .first()
                )

            query = (
                self.db.query(
                    BudgetModel.id,
                    BudgetModel.customer_id,
                    CustomerModel.social_reason.label("customer_name"),
                    BudgetModel.status_id,
                    BudgetModel.subtotal,
                    BudgetModel.shipping,
                    BudgetModel.tax,
                    BudgetModel.total,
                    BudgetModel.added_date,
                    BudgetModel.updated_date
                )
                .join(CustomerModel, CustomerModel.id == BudgetModel.customer_id, isouter=True)
                .order_by(BudgetModel.added_date.desc())
            )

            # Si rol_id es 1 o 2, mostrar todo. Si no, filtrar por customer_id
            if rol_id != 1 and rol_id != 2:
                if customer:
                    query = query.filter(BudgetModel.customer_id == customer.id)
                else:
                    # Si no se encuentra el cliente, retornar lista vacía
                    query = query.filter(BudgetModel.customer_id == -1)

            # Aplicar filtros de búsqueda si se proporcionan
            if identification_number and identification_number.strip():
                query = query.filter(CustomerModel.identification_number == identification_number.strip())

            if social_reason and social_reason.strip():
                query = query.filter(CustomerModel.social_reason.ilike(f"%{social_reason.strip()}%"))

            if page > 0:
                total_items = query.count()
                total_pages = (total_items + items_per_page - 1) // items_per_page

                if page < 1 or (total_pages > 0 and page > total_pages):
                    return {"status": "error", "message": "Invalid page number"}

                data = query.offset((page - 1) * items_per_page).limit(items_per_page).all()

                if not data:
                    return {"status": "error", "message": "No data found"}

                serialized_data = [self.serialize_budget(item) for item in data]

                return {
                    "total_items": total_items,
                    "total_pages": total_pages,
                    "current_page": page,
                    "items_per_page": items_per_page,
                    "data": serialized_data
                }

            data = query.all()
            return [self.serialize_budget(item) for item in data]

        except Exception as e:
            return {"status": "error", "message": str(e)}

    def get(self, budget_id):
        try:
            budget = (
                self.db.query(
                    BudgetModel.id,
                    BudgetModel.customer_id,
                    CustomerModel.social_reason.label("customer_name"),
                    BudgetModel.status_id,
                    BudgetModel.subtotal,
                    BudgetModel.shipping,
                    BudgetModel.tax,
                    BudgetModel.total,
                    BudgetModel.added_date,
                    BudgetModel.updated_date
                )
                .join(CustomerModel, CustomerModel.id == BudgetModel.customer_id, isouter=True)
                .filter(BudgetModel.id == budget_id)
                .first()
            )

            if not budget:
                return {"status": "error", "message": "Budget not found"}

            products = (
                self.db.query(
                    BudgetProductModel.id,
                    BudgetProductModel.product_id,
                    ProductModel.product.label("product_name"),
                    BudgetProductModel.quantity,
                    BudgetProductModel.total
                )
                .join(ProductModel, ProductModel.id == BudgetProductModel.product_id, isouter=True)
                .filter(BudgetProductModel.budget_id == budget_id)
                .all()
            )

            product_data = [{
                "id": item.id,
                "product_id": item.product_id,
                "product_name": item.product_name,
                "quantity": item.quantity,
                "total": item.total
            } for item in products]

            return {
                "budget": self.serialize_budget(budget),
                "products": product_data
            }

        except Exception as e:
            return {"status": "error", "message": str(e)}

    def store(self, budget_inputs):
        try:
            customer = self.db.query(CustomerModel).filter(CustomerModel.id == budget_inputs.customer_id).first()
            if not customer:
                return {"status": "error", "message": "Customer not found"}

            calculated_subtotal = 0
            products_payload = []

            for product in budget_inputs.products:
                amount = product.amount
                if amount is None or amount <= 0:
                    amount = round(product.sale_price * product.quantity)

                amount = int(amount)

                products_payload.append({
                    "product_id": product.product_id,
                    "quantity": product.quantity,
                    "total": amount
                })
                calculated_subtotal += amount

            subtotal = int(budget_inputs.subtotal) if budget_inputs.subtotal > 0 else calculated_subtotal
            shipping = int(budget_inputs.shipping) if budget_inputs.shipping else 0
            tax = int(budget_inputs.tax)
            total = int(budget_inputs.total) if budget_inputs.total > 0 else subtotal + shipping + tax

            new_budget = BudgetModel(
                customer_id=budget_inputs.customer_id,
                status_id=0,
                subtotal=subtotal,
                shipping=shipping,
                tax=tax,
                total=total,
                added_date=datetime.now(),
                updated_date=datetime.now()
            )

            self.db.add(new_budget)
            self.db.flush()

            for product in products_payload:
                new_product = BudgetProductModel(
                    budget_id=new_budget.id,
                    product_id=product["product_id"],
                    quantity=product["quantity"],
                    total=product["total"],
                    added_date=datetime.now(),
                    updated_date=datetime.now()
                )
                self.db.add(new_product)

            self.db.commit()
            self.db.refresh(new_budget)

            # Enviar notificación de WhatsApp para revisar el presupuesto
            try:
                WhatsappClass(self.db).review_budget(
                    budget_id=new_budget.id,
                    total=total
                )
            except Exception as whatsapp_error:
                print(f"Error al enviar WhatsApp de review_budget: {str(whatsapp_error)}")
                # No fallar el proceso si falla el WhatsApp

            return {"status": "success", "budget_id": new_budget.id}

        except Exception as e:
            self.db.rollback()
            return {"status": "error", "message": str(e)}

    def accept(self, budget_id, dte_type_id=None):
        try:
            # Usar with_for_update() para bloquear la fila y prevenir race conditions
            budget = (
                self.db.query(BudgetModel)
                .filter(BudgetModel.id == budget_id)
                .with_for_update()  # Bloquea la fila hasta que se complete la transacción
                .first()
            )

            if not budget:
                return {"status": "error", "message": "Budget not found"}

            # Verificar estado después de bloquear la fila
            if budget.status_id == 1:
                return {"status": "error", "message": "Budget already accepted"}

            # Obtener el cliente para obtener su dirección
            customer = (
                self.db.query(CustomerModel)
                .filter(CustomerModel.id == budget.customer_id)
                .first()
            )

            if not customer:
                return {"status": "error", "message": "Customer not found"}

            # Determinar shipping_method_id y delivery_address según shipping
            shipping_method_id = None
            delivery_address = None
            
            if budget.shipping and budget.shipping != 0:
                shipping_method_id = 1
                delivery_address = customer.address if customer.address else None

            # Crear solo el SaleModel
            new_sale = SaleModel(
                customer_id=budget.customer_id,
                shipping_method_id=shipping_method_id,
                dte_type_id=dte_type_id,
                status_id=1,
                subtotal=budget.subtotal,
                tax=budget.tax,
                shipping_cost=budget.shipping,
                total=budget.total,
                payment_support=None,
                delivery_address=delivery_address,
                added_date=datetime.now(),
                updated_date=datetime.now()
            )

            self.db.add(new_sale)
            self.db.flush()

            # Cambiar status del presupuesto
            budget.status_id = 1
            budget.updated_date = datetime.now()

            self.db.commit()
            self.db.refresh(new_sale)

            return {"status": "success", "sale_id": new_sale.id}

        except Exception as e:
            self.db.rollback()
            return {"status": "error", "message": str(e)}

    def reject(self, budget_id):
        try:
            budget = (
                self.db.query(BudgetModel)
                .filter(BudgetModel.id == budget_id)
                .first()
            )

            if not budget:
                return {"status": "error", "message": "Budget not found"}

            budget.status_id = 2
            budget.updated_date = datetime.now()

            self.db.commit()

            return {"status": "success", "message": "Budget rejected"}

        except Exception as e:
            self.db.rollback()
            return {"status": "error", "message": str(e)}

    def delete(self, budget_id):
        try:
            # Buscar el budget
            budget = (
                self.db.query(BudgetModel)
                .filter(BudgetModel.id == budget_id)
                .first()
            )

            if not budget:
                return {"status": "error", "message": "Presupuesto no encontrado"}

            # Buscar y eliminar todos los productos relacionados
            budget_products = (
                self.db.query(BudgetProductModel)
                .filter(BudgetProductModel.budget_id == budget_id)
                .all()
            )

            # Eliminar cada producto relacionado
            for product in budget_products:
                self.db.delete(product)

            # Eliminar el budget
            self.db.delete(budget)

            # Confirmar cambios
            self.db.commit()

            return {"status": "success", "message": "Presupuesto y productos relacionados eliminados correctamente"}

        except Exception as e:
            self.db.rollback()
            error_message = str(e)
            return {"status": "error", "message": f"Error al eliminar el presupuesto: {error_message}"}