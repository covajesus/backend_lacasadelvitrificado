from fastapi import HTTPException
from app.backend.db.models import ShoppingModel, ShoppingProductModel, SupplierModel, LotModel, ProductModel, UnitMeasureModel, CategoryModel, PreInventoryStockModel, UnitFeatureModel, InventoryModel, LotItemModel
from app.backend.schemas import ShoppingCreateInput
from app.backend.classes.product_class import ProductClass
from datetime import datetime

class ShoppingClass:
    def __init__(self, db):
        self.db = db

    def list_all(self):
        try:
            data = (
                self.db.query(
                    ShoppingModel.id,
                    ShoppingModel.shopping_number,
                    ShoppingModel.supplier_id,
                    ShoppingModel.status_id,
                    ShoppingModel.email,
                    ShoppingModel.total,
                    SupplierModel.supplier,
                    ShoppingModel.added_date
                )
                .join(SupplierModel, SupplierModel.id == ShoppingModel.supplier_id)
                .order_by(ShoppingModel.id.desc())
                .all()
            )

            return [{
                "id": shopping.id,
                "shopping_number": shopping.shopping_number,
                "supplier_id": shopping.supplier_id,
                "status_id": shopping.status_id,
                "email": shopping.email,
                "total": str(shopping.total),
                "supplier": shopping.supplier,
                "added_date": shopping.added_date.strftime("%d-%m-%Y")
            } for shopping in data]

        except Exception as e:
            return {"status": "error", "message": str(e)}

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
                "total_amount": sp.total_amount,
                "quantity_to_buy": sp.quantity_to_buy,
                "discount_percentage": sp.discount_percentage
            })

        return ShoppingCreateInput(
            shopping_number=shopping.shopping_number,
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
                    ShoppingModel.shopping_number,
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
                    "shopping_number": shopping.shopping_number,
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
                    "shopping_number": shopping.shopping_number,
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
    
    def get_list(self):
        try:
            query = (
                self.db.query(
                    ShoppingModel.id,
                    ShoppingModel.shopping_number,
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

            data = query.all()

            serialized_data = [{
                "id": shopping.id,
                "shopping_number": shopping.shopping_number,
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
    
    def get_shopping_products_detail(self, shopping_id):
        try:
            query = (
                self.db.query(
                    ShoppingProductModel.id,
                    ShoppingProductModel.shopping_id,
                    ShoppingProductModel.product_id,
                    ShoppingProductModel.unit_measure_id,
                    ShoppingProductModel.quantity,
                    ShoppingProductModel.quantity_to_buy,
                    ShoppingProductModel.original_unit_cost,
                    ShoppingProductModel.discount_percentage,
                    ShoppingProductModel.final_unit_cost,
                    ShoppingProductModel.total_amount,
                    ProductModel.product,
                    ProductModel.code,
                    UnitMeasureModel.unit_measure,
                    CategoryModel.category,
                    ShoppingProductModel.added_date
                )
                .join(ProductModel, ProductModel.id == ShoppingProductModel.product_id)
                .join(UnitMeasureModel, UnitMeasureModel.id == ShoppingProductModel.unit_measure_id)
                .join(CategoryModel, CategoryModel.id == ProductModel.category_id)
                .filter(ShoppingProductModel.shopping_id == shopping_id)
                .order_by(ShoppingProductModel.id)
            )

            data = query.all()

            if not data:
                return {"status": "error", "message": "No products found for this shopping"}

            serialized_data = [{
                "id": item.id,
                "shopping_id": item.shopping_id,
                "product_id": item.product_id,
                "product": item.product,
                "code": item.code,
                "unit_measure_id": item.unit_measure_id,
                "unit_measure": item.unit_measure,
                "category": item.category,
                "quantity": item.quantity,
                "quantity_to_buy": str(item.quantity_to_buy) if item.quantity_to_buy else "0",
                "original_unit_cost": str(item.original_unit_cost) if item.original_unit_cost else "0",
                "discount_percentage": item.discount_percentage,
                "final_unit_cost": str(item.final_unit_cost) if item.final_unit_cost else "0",
                "total_amount": str(item.total_amount) if item.total_amount else "0",
                "added_date": item.added_date.strftime("%d-%m-%Y %H:%M:%S") if item.added_date else None
            } for item in data]

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
                    ShoppingProductModel.quantity_to_buy,
                    ShoppingProductModel.unit_measure_id,
                    UnitMeasureModel.unit_measure,
                    ProductModel.product,
                    CategoryModel.category,
                    ProductModel.code,
                    ShoppingProductModel.original_unit_cost,
                    ShoppingProductModel.discount_percentage,
                    ShoppingProductModel.total_amount,
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
                    "quantity_to_buy": shopping_product.quantity_to_buy,
                    "category": shopping_product.category,
                    "discount_percentage": shopping_product.discount_percentage,
                    "total_amount": shopping_product.total_amount,
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
                    "quantity_to_buy": shopping_product.quantity_to_buy,
                    "category": shopping_product.category,
                    "discount_percentage": shopping_product.discount_percentage,
                    "total_amount": shopping_product.total_amount,
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
                    ShoppingProductModel.quantity_to_buy,
                    ShoppingProductModel.unit_measure_id,
                    UnitMeasureModel.unit_measure,
                    ProductModel.product,
                    UnitFeatureModel.quantity_per_package,
                    CategoryModel.category,
                    ProductModel.code,
                    ShoppingProductModel.original_unit_cost,
                    ShoppingProductModel.discount_percentage,
                    ShoppingProductModel.total_amount,
                    ShoppingProductModel.final_unit_cost
                )
                .join(ProductModel, ProductModel.id == ShoppingProductModel.product_id)
                .join(UnitMeasureModel, UnitMeasureModel.id == ShoppingProductModel.unit_measure_id)
                .join(CategoryModel, CategoryModel.id == ProductModel.category_id)
                .outerjoin(UnitFeatureModel, UnitFeatureModel.product_id == ShoppingProductModel.product_id)
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
                    "quantity_per_package": shopping_product.quantity_per_package,
                    "code": shopping_product.code,
                    "original_unit_cost": shopping_product.original_unit_cost,
                    "final_unit_cost": shopping_product.final_unit_cost,
                    "quantity_to_buy": shopping_product.quantity_to_buy,
                    "category": shopping_product.category,
                    "discount_percentage": shopping_product.discount_percentage,
                    "total_amount": shopping_product.total_amount
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
                    "quantity_per_package": shopping_product.quantity_per_package,
                    "code": shopping_product.code,
                    "original_unit_cost": shopping_product.original_unit_cost,
                    "quantity_to_buy": shopping_product.quantity_to_buy,
                    "category": shopping_product.category,
                    "discount_percentage": shopping_product.discount_percentage,
                    "total_amount": shopping_product.total_amount,
                    "final_unit_cost": shopping_product.final_unit_cost
                } for shopping_product in data]

                return serialized_data

        except Exception as e:
            error_message = str(e)
            return {"status": "error", "message": error_message}
        
    def get(self, id):
        try:
            data_query = self.db.query(ShoppingModel).filter(ShoppingModel.id == id).first()

            if not data_query:
                return {"error": "No se encontraron datos para la compra especificado."}
            
            # Obtener el nombre del proveedor
            supplier = self.db.query(SupplierModel.supplier).filter(SupplierModel.id == data_query.supplier_id).first()

            shopping_data = {
                "id": data_query.id,
                "shopping_number": data_query.shopping_number,
                "supplier_id": data_query.supplier_id,
                "status_id": data_query.status_id,
                "email": data_query.email,
                "total": str(data_query.total) if data_query.total else None,
                "supplier": supplier.supplier if supplier else None,
                "added_date": data_query.added_date.strftime("%d-%m-%Y") if data_query.added_date else None,
                "prepaid_status_id": data_query.prepaid_status_id,
                "maritime_freight": data_query.maritime_freight,
                "merchandise_insurance": data_query.merchandise_insurance,
                "manifest_opening": data_query.manifest_opening,
                "deconsolidation": data_query.deconsolidation,
                "land_freight": data_query.land_freight,
                "port_charges": data_query.port_charges,
                "tax_explosive_product": data_query.tax_explosive_product,
                "honoraries": data_query.honoraries,
                "physical_assessment_expenses": data_query.physical_assessment_expenses,
                "administrative_expenses": data_query.administrative_expenses,
                "folder_processing": data_query.folder_processing,
                "valija_expenses": data_query.valija_expenses,
                "dollar_value": data_query.dollar_value,
                "wire_transfer_amount": data_query.wire_transfer_amount,
                "wire_transfer_date": data_query.wire_transfer_date.strftime("%Y-%m-%d") if data_query.wire_transfer_date else None,
                "commission": data_query.commission,
                "exchange_rate": data_query.exchange_rate,
                "extra_expenses": data_query.extra_expenses,
                "euro_value": data_query.euro_value,
                "payment_support": data_query.payment_support,
                "customs_company_support": data_query.customs_company_support,
                "updated_date": data_query.updated_date.strftime("%d-%m-%Y %H:%M:%S") if data_query.updated_date else None
            }

            return {"shopping_data": shopping_data}

        except Exception as e:
            return {"error": str(e)}

    def store_payment_documents(self, id, form_data):
        try:
            shopping = self.db.query(ShoppingModel).filter(ShoppingModel.id == id).first()
            if not shopping:
                return {"error": "Shopping not found"}

            print("Payment documents:", form_data)

            shopping.euro_value = form_data.euro_value
            shopping.status_id = 5

            self.db.commit()
            return {"message": "Payment documents stored successfully"}
        except Exception as e:
            return {"error": str(e)}
         
    def store_customs_company_documents(self, id, form_data):
        try:
            shopping = self.db.query(ShoppingModel).filter(ShoppingModel.id == id).first()
            if not shopping:
                return {"error": "Shopping not found"}
            
            print("Customs company documents:", form_data)

            # Calcular merchandise_insurance en pesos solo si ambos valores existen
            merchandise_insurance_in_pesos = None
            if form_data.merchandise_insurance and form_data.dollar_value:
                dollar_value = float(form_data.dollar_value)
                merchandise_insurance = float(form_data.merchandise_insurance)
                merchandise_insurance_in_pesos = merchandise_insurance * dollar_value

            shopping.maritime_freight = form_data.maritime_freight
            shopping.status_id = 4
            shopping.merchandise_insurance = merchandise_insurance_in_pesos
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
            shopping.tax_explosive_product = form_data.tax_explosive_product
            shopping.commission = form_data.commission

            self.db.commit()
            return {"message": "Customs company documents stored successfully"}
        except Exception as e:
            return {"error": str(e)}

    def store(self, data):
        try:
            new_shopping = ShoppingModel(
                    shopping_number=data.shopping_number,
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
                    quantity_to_buy=product.quantity_to_buy,
                    original_unit_cost=product.original_unit_cost,
                    discount_percentage=product.discount_percentage,
                    final_unit_cost=product.final_unit_cost,
                    total_amount=product.total_amount,
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
            existing_shopping.shopping_number = data.shopping_number
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
                    quantity_to_buy=product.quantity_to_buy,
                    original_unit_cost=product.original_unit_cost,
                    discount_percentage=product.discount_percentage,
                    final_unit_cost=product.final_unit_cost,
                    total_amount=product.total_amount,
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

    def calculate_unit_cost_for_product(self, shopping_id, product_id, quantity):
        """
        Calcula el unit_cost para un producto específico basado en:
        1. final_unit_cost del producto convertido de euros a pesos
        2. Costo de envío distribuido proporcionalmente por peso
        3. Costo final por litro/peso/unidad según la unidad de medida
        """
        try:
            # Obtener los datos del shopping con todos los costos de envío
            shopping = self.db.query(ShoppingModel).filter(ShoppingModel.id == shopping_id).first()
            if not shopping:
                print(f"Shopping {shopping_id} no encontrado")
                return 0

            # Obtener el exchange_rate para convertir euros a pesos
            exchange_rate = shopping.exchange_rate or 1
            print(f"Exchange rate (pesos por euro): {exchange_rate}")

            # Obtener el producto y su final_unit_cost del shopping
            shopping_product = (
                self.db.query(ShoppingProductModel)
                .filter(
                    ShoppingProductModel.shopping_id == shopping_id,
                    ShoppingProductModel.product_id == product_id
                )
                .first()
            )

            if not shopping_product:
                print(f"Producto {product_id} no encontrado en shopping {shopping_id}")
                return 0

            # Convertir final_unit_cost de euros a pesos
            final_unit_cost_euros = shopping_product.final_unit_cost or 0
            final_unit_cost_pesos = final_unit_cost_euros * exchange_rate

            print(f"Final unit cost del producto:")
            print(f"  - En euros: €{final_unit_cost_euros:.2f}")
            print(f"  - En pesos: ${final_unit_cost_pesos:.2f}")

            # Calcular el total de costos de envío
            total_shipping_costs = (
                (shopping.maritime_freight or 0) +
                (shopping.merchandise_insurance or 0) +
                (shopping.manifest_opening or 0) +
                (shopping.deconsolidation or 0) +
                (shopping.land_freight or 0) +
                (shopping.port_charges or 0) +
                (shopping.honoraries or 0) +
                (shopping.physical_assessment_expenses or 0) +
                (shopping.administrative_expenses or 0) +
                (shopping.folder_processing or 0) +
                (shopping.valija_expenses or 0) +
                (shopping.extra_expenses or 0) +
                (shopping.commission or 0)
            )

            print(f"Total de costos de envío (PESOS): ${total_shipping_costs:.2f}")

            # Obtener todos los productos del pre-inventario para este shopping
            pre_inventory_products = (
                self.db.query(
                    PreInventoryStockModel.product_id,
                    PreInventoryStockModel.stock,
                    UnitFeatureModel.weight_per_unit
                )
                .join(UnitFeatureModel, UnitFeatureModel.product_id == PreInventoryStockModel.product_id)
                .filter(PreInventoryStockModel.shopping_id == shopping_id)
                .all()
            )

            if not pre_inventory_products:
                print(f"No se encontraron productos de pre-inventario para shopping {shopping_id}")
                # Si no hay datos de envío, solo devolver el costo del producto convertido
                return final_unit_cost_pesos

            # Calcular el peso total de todos los productos
            total_weight = 0
            product_weights = {}
            
            for item in pre_inventory_products:
                try:
                    weight_per_unit = float(item.weight_per_unit) if item.weight_per_unit else 0
                    product_total_weight = item.stock * weight_per_unit
                    total_weight += product_total_weight
                    product_weights[item.product_id] = product_total_weight
                    print(f"Producto {item.product_id}: {item.stock} unidades x {weight_per_unit} kg = {product_total_weight} kg")
                except (ValueError, TypeError):
                    print(f"Warning: weight_per_unit inválido para producto {item.product_id}: {item.weight_per_unit}")
                    product_weights[item.product_id] = 0

            print(f"Peso total de todos los productos: {total_weight} kg")

            # Calcular el costo de envío proporcional POR LITRO/KG/UNIDAD
            shipping_cost_per_unit = 0
            if total_weight > 0:
                product_weight = product_weights.get(product_id, 0)
                
                if product_weight > 0:
                    # Aplicar la fórmula: (peso_producto * 100) / peso_total * total_costos / 100
                    percentage = (product_weight * 100) / total_weight
                    shipping_cost_total = (percentage * total_shipping_costs) / 100
                    
                    # DIVIDIR entre la cantidad total (stock) para obtener el costo por litro/kg/unidad
                    shipping_cost_per_unit = shipping_cost_total / quantity if quantity > 0 else 0
                    
                    print(f"Costo de envío proporcional:")
                    print(f"  - Peso del producto: {product_weight} kg ({percentage:.2f}% del total)")
                    print(f"  - Costo total de envío asignado: ${shipping_cost_total:.2f}")
                    print(f"  - Cantidad total: {quantity} unidades")
                    print(f"  - Costo de envío POR UNIDAD: ${shipping_cost_per_unit:.2f}")

            # Calcular el costo total por unidad (producto + envío)
            total_unit_cost = final_unit_cost_pesos + shipping_cost_per_unit

            # Obtener información de la unidad de medida para mostrar costo por litro/kg/unidad
            unit_measure = (
                self.db.query(UnitMeasureModel.unit_measure)
                .filter(UnitMeasureModel.id == shopping_product.unit_measure_id)
                .first()
            )
            
            unit_measure_name = unit_measure.unit_measure if unit_measure else "unidad"

            print(f"\nRESUMEN FINAL:")
            print(f"  - Costo del producto (pesos): ${final_unit_cost_pesos:.2f}")
            print(f"  - Costo de envío por unidad: ${shipping_cost_per_unit:.2f}")
            print(f"  - COSTO TOTAL por {unit_measure_name}: ${total_unit_cost:.2f}")

            return total_unit_cost

        except Exception as e:
            print(f"Error calculando unit_cost para producto {product_id}: {e}")
            return 0

    def test_calculate_unit_costs(self, shopping_id):
        """
        Función de prueba para mostrar el cálculo de unit_cost para todos los productos de un shopping
        """
        print(f"\n=== CALCULANDO UNIT_COSTS PARA SHOPPING {shopping_id} ===\n")
        
        try:
            # Obtener todos los productos del pre-inventario
            pre_inventory_products = (
                self.db.query(
                    PreInventoryStockModel.product_id,
                    PreInventoryStockModel.stock,
                    ProductModel.product
                )
                .join(ProductModel, ProductModel.id == PreInventoryStockModel.product_id)
                .filter(PreInventoryStockModel.shopping_id == shopping_id)
                .all()
            )

            if not pre_inventory_products:
                print("No se encontraron productos en el pre-inventario")
                return

            total_calculated_cost = 0
            
            for item in pre_inventory_products:
                unit_cost = self.calculate_unit_cost_for_product(
                    shopping_id, 
                    item.product_id, 
                    item.stock
                )
                
                total_product_cost = unit_cost * item.stock
                total_calculated_cost += total_product_cost
                
                print(f"\nRESUMEN - {item.product}:")
                print(f"  - Product ID: {item.product_id}")
                print(f"  - Cantidad: {item.stock}")
                print(f"  - COSTO TOTAL (producto + envío): ${unit_cost:.2f}")
                print(f"  - Costo total del producto: ${total_product_cost:.2f}")
                print("-" * 50)

            print(f"\nTOTAL DE COSTOS DISTRIBUIDOS (PESOS): ${total_calculated_cost:.2f}")
            print(f"=== FIN DEL CÁLCULO ===\n")

        except Exception as e:
            print(f"Error en test_calculate_unit_costs: {e}")

    def get_inventories_by_shopping_id(self, shopping_id):
        try:
            # Buscar directamente productos del shopping sin depender del lot_number en PreInventoryStockModel
            # porque el lot_number en PreInventoryStockModel puede no coincidir con el lot_number real del LotModel
            inventories_data = (
                self.db.query(
                    InventoryModel.id.label("inventory_id"),
                    InventoryModel.product_id,
                    ProductModel.product.label("product_name"),
                    ProductModel.code.label("product_code"),
                    LotItemModel.public_sale_price,
                    LotItemModel.private_sale_price,
                    LotModel.arrival_date,
                    LotItemModel.quantity,
                    LotItemModel.unit_cost,
                    LotModel.lot_number,
                    LotItemModel.id.label("lot_item_id")
                )
                .join(LotItemModel, LotItemModel.product_id == InventoryModel.product_id)
                .join(LotModel, LotModel.id == LotItemModel.lot_id)
                .join(ProductModel, ProductModel.id == InventoryModel.product_id)
                .join(PreInventoryStockModel, PreInventoryStockModel.product_id == InventoryModel.product_id)
                .filter(PreInventoryStockModel.shopping_id == shopping_id)
                .order_by(InventoryModel.product_id, LotItemModel.id.desc())
                .all()
            )
            
            if not inventories_data:
                return {"status": "success", "message": "No se encontraron inventarios para este shopping", "data": []}
            
            # Deduplicar por producto_id manualmente (tomar el primer lot_item por producto)
            products_seen = set()
            formatted_data = []
            
            for item in inventories_data:
                # Si ya procesamos este producto, saltarlo
                if item.product_id in products_seen:
                    continue
                    
                products_seen.add(item.product_id)
                
                formatted_data.append({
                    "inventory_id": item.inventory_id,
                    "product_id": item.product_id,
                    "product_name": item.product_name,
                    "product_code": item.product_code,
                    "quantity": item.quantity,
                    "unit_cost": float(item.unit_cost) if item.unit_cost else 0,
                    "public_sale_price": float(item.public_sale_price) if item.public_sale_price else 0,
                    "private_sale_price": float(item.private_sale_price) if item.private_sale_price else 0,
                    "arrival_date": item.arrival_date.strftime("%Y-%m-%d") if item.arrival_date else None,
                    "lot_number": item.lot_number
                })
            
            return {
                "status": "success",
                "message": f"Se encontraron {len(formatted_data)} inventarios",
                "shopping_id": shopping_id,
                "data": formatted_data
            }
            
        except Exception as e:
            return {"status": "error", "message": f"Error al obtener inventarios: {str(e)}"}