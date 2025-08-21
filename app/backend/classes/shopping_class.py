from fastapi import HTTPException
from app.backend.db.models import ShoppingModel, ShoppingProductModel, SupplierModel, LotModel, ProductModel, UnitMeasureModel, CategoryModel, PreInventoryStockModel
from app.backend.schemas import ShoppingCreateInput
from app.backend.classes.product_class import ProductClass
from datetime import datetime

class ShoppingClass:
    def __init__(self, db):
        self.db = db

    def confirm(self, id):
        existing_shopping = self.db.query(ShoppingModel).filter(ShoppingModel.id == id).one_or_none()

        if not existing_shopping:
            return "No data found"

        try:
            existing_shopping.status_id = 2
            existing_shopping.updated_date = datetime.utcnow()

            self.db.commit()
            self.db.refresh(existing_shopping)
            return "Shopping updated successfully"
        except Exception as e:
            self.db.rollback()
            error_message = str(e)
            return {"status": "error", "message": error_message}
    
    def send_customs_company_email(self, id, email):
        existing_shopping = self.db.query(ShoppingModel).filter(ShoppingModel.id == id).one_or_none()

        if not existing_shopping:
            return "No data found"

        try:
            existing_shopping.status_id = 3
            existing_shopping.customs_company_email = email
            existing_shopping.updated_date = datetime.utcnow()

            self.db.commit()
            self.db.refresh(existing_shopping)
            return "Shopping updated successfully"
        except Exception as e:
            self.db.rollback()
            error_message = str(e)
            return {"status": "error", "message": error_message}
        
    def get_shopping_data(self, shopping_id: int) -> ShoppingCreateInput:
        shopping = self.db.query(ShoppingModel).filter(ShoppingModel.id == shopping_id).first()
        if not shopping:
            raise HTTPException(status_code=404, detail="Shopping not found")

        shopping_products = (
            self.db.query(ShoppingProductModel)
            .filter(ShoppingProductModel.shopping_id == shopping_id)
            .all()
        )

        products = []
        for sp in shopping_products:
            product = ProductClass(self.db).get(sp.product_id)
            if not product:
                continue
            category_id = product["product_data"]["category_id"]

            products.append({
                "product_id": sp.product_id,
                "unit_measure_id": sp.unit_measure_id,
                "quantity": sp.quantity,
                "original_unit_cost": sp.original_unit_cost,
                "final_unit_cost": sp.final_unit_cost,
                "category_id": category_id,
                "amount": sp.amount,
                "quantity_per_package": sp.quantity_per_package,
                "discount_percentage": sp.discount_percentage
            })

        return ShoppingCreateInput(
            supplier_id=shopping.supplier_id,
            email=shopping.email,
            total=float(shopping.total),
            products=products
        )
        
    def get_all(self, page=0, items_per_page=10):
        try:
            query = (
                self.db.query(
                    ShoppingModel.id,
                    ShoppingModel.supplier_id,
                    ShoppingModel.status_id,
                    ShoppingModel.email,
                    ShoppingModel.total,
                    SupplierModel.supplier,
                    ShoppingModel.added_date
                )
                .join(SupplierModel, SupplierModel.id == ShoppingModel.supplier_id)
                .order_by(ShoppingModel.id.desc())
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
                    "id": shopping.id,
                    "supplier_id": shopping.supplier_id,
                    "status_id": shopping.status_id,
                    "email": shopping.email,
                    "total": str(shopping.total),
                    "supplier": shopping.supplier,
                    "added_date": shopping.added_date.strftime("%d-%m-%Y")
                } for shopping in data]

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
                    "id": shopping.id,
                    "supplier_id": shopping.supplier_id,
                    "status_id": shopping.status_id,
                    "email": shopping.email,
                    "total": str(shopping.total),
                    "supplier": shopping.supplier,
                    "added_date": shopping.added_date.strftime("%d-%m-%Y")
                } for shopping in data]

                return serialized_data

        except Exception as e:
            error_message = str(e)
            return {"status": "error", "message": error_message}
    
    def get_pre_inventory_products(self, id, page=0, items_per_page=10000):
        try:
            query = (
                self.db.query(
                    ShoppingProductModel.product_id,
                    ShoppingProductModel.quantity,
                    ShoppingProductModel.quantity_per_package,
                    ShoppingProductModel.unit_measure_id,
                    UnitMeasureModel.unit_measure,
                    ProductModel.product,
                    CategoryModel.category,
                    ProductModel.code,
                    ShoppingProductModel.original_unit_cost,
                    ShoppingProductModel.discount_percentage,
                    ShoppingProductModel.amount,
                    ShoppingProductModel.final_unit_cost,
                    PreInventoryStockModel.stock,
                    PreInventoryStockModel.lot_number
                )
                .join(PreInventoryStockModel, PreInventoryStockModel.product_id == ShoppingProductModel.product_id)
                .join(ProductModel, ProductModel.id == ShoppingProductModel.product_id)
                .join(UnitMeasureModel, UnitMeasureModel.id == ShoppingProductModel.unit_measure_id)
                .join(CategoryModel, CategoryModel.id == ProductModel.category_id)
                .filter(ShoppingProductModel.shopping_id == id)
                .filter(PreInventoryStockModel.shopping_id == id)
                .order_by(ShoppingProductModel.id)
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
                    "product_id": shopping_product.product_id,
                    "quantity": shopping_product.quantity,
                    "unit_measure_id": shopping_product.unit_measure_id,
                    "unit_measure": shopping_product.unit_measure,
                    "product": shopping_product.product,
                    "code": shopping_product.code,
                    "original_unit_cost": shopping_product.original_unit_cost,
                    "final_unit_cost": shopping_product.final_unit_cost,
                    "quantity_per_package": shopping_product.quantity_per_package,
                    "category": shopping_product.category,
                    "discount_percentage": shopping_product.discount_percentage,
                    "amount": shopping_product.amount,
                    "stock": shopping_product.stock,
                    "lot_number": shopping_product.lot_number
                } for shopping_product in data]

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
                    "product_id": shopping_product.product_id,
                    "quantity": shopping_product.quantity,
                    "unit_measure_id": shopping_product.unit_measure_id,
                    "unit_measure": shopping_product.unit_measure,
                    "product": shopping_product.product,
                    "code": shopping_product.code,
                    "original_unit_cost": shopping_product.original_unit_cost,
                    "quantity_per_package": shopping_product.quantity_per_package,
                    "category": shopping_product.category,
                    "discount_percentage": shopping_product.discount_percentage,
                    "amount": shopping_product.amount,
                    "final_unit_cost": shopping_product.final_unit_cost,
                    "stock": shopping_product.stock,
                    "lot_number": shopping_product.lot_number
                } for shopping_product in data]

                return serialized_data

        except Exception as e:
            error_message = str(e)
            return {"status": "error", "message": error_message}
        
    def get_products(self, id, page=0, items_per_page=10000):
        try:
            query = (
                self.db.query(
                    ShoppingProductModel.product_id,
                    ShoppingProductModel.quantity,
                    ShoppingProductModel.quantity_per_package,
                    ShoppingProductModel.unit_measure_id,
                    UnitMeasureModel.unit_measure,
                    ProductModel.product,
                    CategoryModel.category,
                    ProductModel.code,
                    ShoppingProductModel.original_unit_cost,
                    ShoppingProductModel.discount_percentage,
                    ShoppingProductModel.amount,
                    ShoppingProductModel.final_unit_cost
                )
                .join(ProductModel, ProductModel.id == ShoppingProductModel.product_id)
                .join(UnitMeasureModel, UnitMeasureModel.id == ShoppingProductModel.unit_measure_id)
                .join(CategoryModel, CategoryModel.id == ProductModel.category_id)
                .filter(ShoppingProductModel.shopping_id == id)
                .order_by(ShoppingProductModel.id)
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
                    "product_id": shopping_product.product_id,
                    "quantity": shopping_product.quantity,
                    "unit_measure_id": shopping_product.unit_measure_id,
                    "unit_measure": shopping_product.unit_measure,
                    "product": shopping_product.product,
                    "code": shopping_product.code,
                    "original_unit_cost": shopping_product.original_unit_cost,
                    "final_unit_cost": shopping_product.final_unit_cost,
                    "quantity_per_package": shopping_product.quantity_per_package,
                    "category": shopping_product.category,
                    "discount_percentage": shopping_product.discount_percentage,
                    "amount": shopping_product.amount
                } for shopping_product in data]

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
                    "product_id": shopping_product.product_id,
                    "quantity": shopping_product.quantity,
                    "unit_measure_id": shopping_product.unit_measure_id,
                    "unit_measure": shopping_product.unit_measure,
                    "product": shopping_product.product,
                    "code": shopping_product.code,
                    "original_unit_cost": shopping_product.original_unit_cost,
                    "quantity_per_package": shopping_product.quantity_per_package,
                    "category": shopping_product.category,
                    "discount_percentage": shopping_product.discount_percentage,
                    "amount": shopping_product.amount,
                    "final_unit_cost": shopping_product.final_unit_cost
                } for shopping_product in data]

                return serialized_data

        except Exception as e:
            error_message = str(e)
            return {"status": "error", "message": error_message}
        
    def get(self, id):
        try:
            data_query = self.db.query(
                ShoppingModel.id,
                ShoppingModel.supplier_id,
                ShoppingModel.status_id,
                ShoppingModel.email,
                ShoppingModel.total,
                SupplierModel.supplier,
                ShoppingModel.added_date
            ).filter(ShoppingModel.id == id).join(SupplierModel, SupplierModel.id == ShoppingModel.supplier_id).first()

            if not data_query:
                return {"error": "No se encontraron datos para la compra especificado."}

            shopping_data = {
                "id": data_query.id,
                "supplier_id": data_query.supplier_id,
                "status_id": data_query.status_id,
                "email": data_query.email,
                "total": str(data_query.total),
                "supplier": data_query.supplier,
                "added_date": data_query.added_date.strftime("%d-%m-%Y")
            }

            return {"shopping_data": shopping_data}

        except Exception as e:
            return {"error": str(e)}

    def store_payment_documents(self, id, form_data, support_remote_path):
        try:
            shopping = self.db.query(ShoppingModel).filter(ShoppingModel.id == id).first()
            if not shopping:
                return {"error": "Shopping not found"}

            print("Payment documents:", form_data)

            shopping.wire_transfer_amount = form_data.wire_transfer_amount
            shopping.status_id = 5
            shopping.wire_transfer_date = form_data.wire_transfer_date
            shopping.commission = form_data.commission
            shopping.exchange_rate = form_data.exchange_rate
            shopping.extra_expenses = form_data.extra_expenses
            shopping.payment_support = support_remote_path

            self.db.commit()
            return {"message": "Payment documents stored successfully"}
        except Exception as e:
            return {"error": str(e)}
         
    def store_customs_company_documents(self, id, form_data, support_remote_path):
        try:
            shopping = self.db.query(ShoppingModel).filter(ShoppingModel.id == id).first()
            if not shopping:
                return {"error": "Shopping not found"}
            
            print("Customs company documents:", form_data)

            shopping.maritime_freight = form_data.maritime_freight
            shopping.status_id = 4
            shopping.merchandise_insurance = form_data.merchandise_insurance
            shopping.manifest_opening = form_data.manifest_opening
            shopping.deconsolidation = form_data.deconsolidation
            shopping.land_freight = form_data.land_freight
            shopping.port_charges = form_data.port_charges
            shopping.honoraries = form_data.honoraries
            shopping.physical_assessment_expenses = form_data.physical_assessment_expenses
            shopping.administrative_expenses = form_data.administrative_expenses
            shopping.dollar_value = form_data.dollar_value
            shopping.folder_processing = form_data.folder_processing
            shopping.valija_expenses = form_data.valija_expenses
            shopping.customs_company_support = support_remote_path

            self.db.commit()
            return {"message": "Customs company documents stored successfully"}
        except Exception as e:
            return {"error": str(e)}

    def store(self, data):
        try:
            new_shopping = ShoppingModel(
                    supplier_id=data.supplier_id,
                    email=data.email,
                    prepaid_status_id=data.prepaid_status_id,
                    status_id=1,
                    total=data.total,
                    added_date=datetime.utcnow(),
                    updated_date=datetime.utcnow()
                )

            self.db.add(new_shopping)
            self.db.commit()
            self.db.refresh(new_shopping)

            for product in data.products:
                new_shopping_product = ShoppingProductModel(
                    shopping_id=new_shopping.id,
                    product_id=product.product_id,
                    unit_measure_id=product.unit_measure_id,
                    quantity=product.quantity,
                    quantity_per_package=product.quantity_per_package,
                    original_unit_cost=product.original_unit_cost,
                    discount_percentage=product.discount_percentage,
                    final_unit_cost=product.final_unit_cost,
                    amount=product.amount,
                    added_date=datetime.utcnow(),
                    updated_date=datetime.utcnow()
                )
                self.db.add(new_shopping_product)
                self.db.commit()
                self.db.refresh(new_shopping_product)

            return {"detail": "Shopping stored successfully", "shopping_id": new_shopping.id}
        except Exception as e:
            print("Error:", e)
            raise HTTPException(status_code=500, detail="Error to store shopping")

    def save_pre_inventory_quantities(self, shopping_id, items):
        try:
            existing_shopping = self.db.query(ShoppingModel).filter(ShoppingModel.id == shopping_id).one_or_none()

            if not existing_shopping:
                raise HTTPException(status_code=404, detail="Shopping not found")
            
            existing_shopping.status_id = 6
            existing_shopping.updated_date = datetime.utcnow()
            self.db.commit()
            self.db.refresh(existing_shopping)
           
            last_lot = self.db.query(LotModel.lot_number).order_by(LotModel.lot_number.desc()).first()

            next_lot_number = last_lot.lot_number + 1 if last_lot else 1
            
            for item in items:
                new_pre_inventory = PreInventoryStockModel(
                    shopping_id=shopping_id,
                    product_id=item.product_id,
                    lot_number=next_lot_number,
                    stock=item.stock,
                    added_date=datetime.utcnow(),
                    updated_date=datetime.utcnow()
                )
                self.db.add(new_pre_inventory)
            self.db.commit()
            return {"message": "Pre-inventory quantities saved successfully"}
        except Exception as e:
            print("Error:", e)
            raise HTTPException(status_code=500, detail="Error to save pre-inventory quantities")

    def update(self, id, data):
        """
        Actualiza una compra existente y sus productos asociados
        """
        try:
            existing_shopping = self.db.query(ShoppingModel).filter(ShoppingModel.id == id).one_or_none()

            if not existing_shopping:
                return {"status": "error", "message": "Shopping not found"}

            # Actualizar solo los datos que se guardan en la base de datos
            existing_shopping.supplier_id = data.supplier_id
            existing_shopping.email = data.email  # Solo el email principal
            existing_shopping.total = data.total
            existing_shopping.updated_date = datetime.utcnow()
            
            # Solo actualizar prepaid_status_id si está presente
            if hasattr(data, 'prepaid_status_id') and data.prepaid_status_id:
                existing_shopping.prepaid_status_id = data.prepaid_status_id

            self.db.commit()
            self.db.refresh(existing_shopping)

            # Eliminar productos existentes
            existing_products = self.db.query(ShoppingProductModel).filter(
                ShoppingProductModel.shopping_id == id
            ).all()
            
            for product in existing_products:
                self.db.delete(product)
            
            self.db.commit()

            # Agregar nuevos productos
            for product in data.products:
                new_shopping_product = ShoppingProductModel(
                    shopping_id=id,
                    product_id=product.product_id,
                    unit_measure_id=product.unit_measure_id,
                    quantity=product.quantity,
                    quantity_per_package=product.quantity_per_package,
                    original_unit_cost=product.original_unit_cost,
                    discount_percentage=product.discount_percentage,
                    final_unit_cost=product.final_unit_cost,
                    amount=product.amount,
                    added_date=datetime.utcnow(),
                    updated_date=datetime.utcnow()
                )
                self.db.add(new_shopping_product)
            
            self.db.commit()

            return {"status": "success", "message": "Shopping updated successfully", "shopping_id": id}

        except Exception as e:
            self.db.rollback()
            print("Error:", e)
            return {"status": "error", "message": str(e)}