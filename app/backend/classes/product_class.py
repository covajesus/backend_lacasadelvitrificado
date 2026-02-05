from app.backend.db.models import ProductModel, SupplierModel, UnitFeatureModel, CategoryModel, LotModel, LotItemModel, UnitMeasureModel, InventoryLotItemModel, CustomerProductDiscountModel
from app.backend.classes.file_class import FileClass
from datetime import datetime
from sqlalchemy import func, or_

class ProductClass:
    def __init__(self, db):
        self.db = db

    def get_all(self, page=0, items_per_page=10, supplier_id=None, product_id=None):
        try:
            query = (
                self.db.query(
                    ProductModel.id,
                    SupplierModel.supplier.label("supplier"),
                    CategoryModel.category.label("category"),
                    ProductModel.code,
                    ProductModel.product
                )
                .join(SupplierModel, SupplierModel.id == ProductModel.supplier_id, isouter=True)
                .join(CategoryModel, CategoryModel.id == ProductModel.category_id, isouter=True)
            )
            
            # Aplicar filtros si se proporcionan
            if supplier_id:
                query = query.filter(ProductModel.supplier_id == supplier_id)
            
            if product_id:
                query = query.filter(ProductModel.id == product_id)
            
            # Ordenar por nombre del producto
            query = query.order_by(ProductModel.product)

            if page > 0:
                total_items = query.count()
                total_pages = (total_items + items_per_page - 1)

                if page < 1 or page > total_pages:
                    return {"status": "error", "message": "Invalid page number"}

                data = query.offset((page - 1) * items_per_page).limit(items_per_page).all()

                if not data:
                    return {"status": "error", "message": "No data found"}

                serialized_data = [{
                    "id": product.id,
                    "supplier": product.supplier,
                    "category": product.category,
                    "code": product.code,
                    "product": product.product
                } for product in data]

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
                    "id": product.id,
                    "supplier": product.supplier,
                    "category": product.category,
                    "code": product.code,
                    "product": product.product
                } for product in data]

                return serialized_data

        except Exception as e:
            error_message = str(e)
            return {"status": "error", "message": error_message}
    
    def get_list(self):
        try:
            data = (
                self.db.query(
                    ProductModel.id, 
                    ProductModel.code,
                    ProductModel.product,
                    UnitMeasureModel.unit_measure,
                    SupplierModel.supplier,
                    CategoryModel.category,
                    ProductModel.category_id,
                    ProductModel.photo,
                    ProductModel.catalog,
                    ProductModel.short_description,
                    ProductModel.description,
                    func.max(LotItemModel.public_sale_price).label("public_sale_price"),
                    func.max(LotItemModel.private_sale_price).label("private_sale_price")
                )
                .join(UnitMeasureModel, UnitMeasureModel.id == ProductModel.unit_measure_id, isouter=True)
                .join(SupplierModel, SupplierModel.id == ProductModel.supplier_id, isouter=True)
                .join(CategoryModel, CategoryModel.id == ProductModel.category_id, isouter=True)
                .join(LotItemModel, LotItemModel.product_id == ProductModel.id, isouter=True)
                .group_by(
                    ProductModel.id,
                    ProductModel.code,
                    ProductModel.product,
                    UnitMeasureModel.unit_measure,
                    SupplierModel.supplier,
                    CategoryModel.category,
                    ProductModel.category_id,
                    ProductModel.photo,
                    ProductModel.catalog,
                    ProductModel.short_description,
                    ProductModel.description
                )
                .order_by(ProductModel.product)
            )

            serialized_data = [{
                    "id": product.id,
                    "code": product.code,
                    "product": product.product,
                    "unit_measure": product.unit_measure,
                    "supplier": product.supplier,
                    "category": product.category,
                    "category_id": product.category_id,
                    "photo": product.photo,
                    "catalog": product.catalog,
                    "short_description": product.short_description,
                    "description": product.description,
                    "public_sale_price": product.public_sale_price if product.public_sale_price is not None else 0,
                    "private_sale_price": product.private_sale_price if product.private_sale_price is not None else 0
                } for product in data]

            return {
                "data": serialized_data
            }

        except Exception as e:
            error_message = str(e)
            return {"status": "error", "message": error_message}
        
    def store(self, product_inputs, photo, catalog):
        try:
            new_product = ProductModel(
                supplier_id=product_inputs.supplier_id,
                category_id=product_inputs.category_id,
                unit_measure_id=product_inputs.unit_measure_id,
                code=product_inputs.code,
                discount_percentage=product_inputs.discount_percentage,
                final_unit_cost=product_inputs.final_unit_cost,
                original_unit_cost=product_inputs.original_unit_cost,
                product=product_inputs.product,
                short_description=product_inputs.short_description,
                description=product_inputs.description,
                is_compound=product_inputs.is_compound,
                compound_product_id=product_inputs.compound_product_id,
                photo=photo,
                catalog=catalog,
                added_date=datetime.utcnow(),
                updated_date=datetime.utcnow()
            )

            self.db.add(new_product)
            self.db.commit()
            self.db.refresh(new_product)

            new_unit_feature = UnitFeatureModel(
                    product_id=new_product.id,
                    quantity_per_package=product_inputs.quantity_per_package,
                    quantity_per_pallet=product_inputs.quantity_per_pallet,
                    weight_per_unit=product_inputs.weight_per_unit,
                    weight_per_pallet=product_inputs.weight_per_pallet,
                    added_date=datetime.utcnow()
                )

            self.db.add(new_unit_feature)
            self.db.commit()
            self.db.refresh(new_unit_feature)

            return {
                "status": "Producto registrado exitosamente.",
                "product_id": new_product.id
            }

        except Exception as e:
            self.db.rollback()
            return {"status": "error", "message": str(e)}

    def sale_list_by_category(self, category_id):
        try:

            if category_id == 0 or category_id is None:
                data = (
                    self.db.query(
                        ProductModel.id, 
                        ProductModel.code,
                        ProductModel.product,
                        UnitMeasureModel.unit_measure,
                        SupplierModel.supplier,
                        CategoryModel.category,
                        ProductModel.category_id,
                        ProductModel.photo,
                        ProductModel.catalog,
                        ProductModel.short_description,
                        ProductModel.description,
                        func.max(LotItemModel.public_sale_price).label("public_sale_price"),
                        func.max(LotItemModel.private_sale_price).label("private_sale_price"),
                        func.sum(LotItemModel.quantity).label("total_stock"),
                        func.group_concat(LotModel.lot_number.op('ORDER BY')(LotModel.lot_number)).label("lot_numbers")
                    )
                    .join(UnitMeasureModel, UnitMeasureModel.id == ProductModel.unit_measure_id, isouter=True)
                    .join(SupplierModel, SupplierModel.id == ProductModel.supplier_id, isouter=True)
                    .join(CategoryModel, CategoryModel.id == ProductModel.category_id, isouter=True)
                    .join(LotItemModel, LotItemModel.product_id == ProductModel.id)
                    .join(LotModel, LotModel.id == LotItemModel.lot_id)
                    .group_by(
                        ProductModel.id,
                        ProductModel.code,
                        ProductModel.product,
                        UnitMeasureModel.unit_measure,
                        SupplierModel.supplier,
                        CategoryModel.category,
                        ProductModel.category_id,
                        ProductModel.photo,
                        ProductModel.catalog,
                        ProductModel.short_description,
                        ProductModel.description
                    )
                    .order_by(ProductModel.product)
                )
            else:
                data = (
                    self.db.query(
                        ProductModel.id, 
                        ProductModel.code,
                        ProductModel.product,
                        UnitMeasureModel.unit_measure,
                        SupplierModel.supplier,
                        CategoryModel.category,
                        ProductModel.category_id,
                        ProductModel.photo,
                        ProductModel.catalog,
                        ProductModel.short_description,
                        ProductModel.description,
                        ProductModel.discount_percentage,
                        ProductModel.final_unit_cost
                    )
                    .join(UnitMeasureModel, UnitMeasureModel.id == ProductModel.unit_measure_id, isouter=True)
                    .join(SupplierModel, SupplierModel.id == ProductModel.supplier_id, isouter=True)
                    .join(CategoryModel, CategoryModel.id == ProductModel.category_id, isouter=True)
                    .filter(ProductModel.category_id == category_id)
                    .group_by(
                        ProductModel.id,
                        ProductModel.code,
                        ProductModel.product,
                        UnitMeasureModel.unit_measure,
                        SupplierModel.supplier,
                        CategoryModel.category,
                        ProductModel.category_id,
                        ProductModel.photo,
                        ProductModel.catalog,
                        ProductModel.short_description,
                        ProductModel.description
                    )
                    .order_by(ProductModel.product)
                )

            serialized_data = [{
                    "id": product.id,
                    "code": product.code,
                    "product": product.product,
                    "unit_measure": product.unit_measure,
                    "supplier": product.supplier,
                    "category": product.category,
                    "category_id": product.category_id,
                    "photo": product.photo,
                    "catalog": product.catalog,
                    "short_description": product.short_description,
                    "description": product.description,
                } for product in data]

            return {
                "data": serialized_data
            }

        except Exception as e:
            error_message = str(e)
            return {"status": "error", "message": error_message}
        
    def sale_list(self, category_id):
        try:

            if category_id == 0 or category_id is None:
                data = (
                    self.db.query(
                        ProductModel.id, 
                        ProductModel.code,
                        ProductModel.product,
                        UnitMeasureModel.unit_measure,
                        SupplierModel.supplier,
                        CategoryModel.category,
                        ProductModel.category_id,
                        ProductModel.photo,
                        ProductModel.catalog,
                        ProductModel.short_description,
                        ProductModel.description,
                        func.max(LotItemModel.public_sale_price).label("public_sale_price"),
                        func.max(LotItemModel.private_sale_price).label("private_sale_price"),
                        func.sum(LotItemModel.quantity).label("total_stock"),
                        func.group_concat(LotModel.lot_number.op('ORDER BY')(LotModel.lot_number)).label("lot_numbers")
                    )
                    .join(UnitMeasureModel, UnitMeasureModel.id == ProductModel.unit_measure_id, isouter=True)
                    .join(SupplierModel, SupplierModel.id == ProductModel.supplier_id, isouter=True)
                    .join(CategoryModel, CategoryModel.id == ProductModel.category_id, isouter=True)
                    .join(LotItemModel, LotItemModel.product_id == ProductModel.id)
                    .join(LotModel, LotModel.id == LotItemModel.lot_id)
                    .group_by(
                        ProductModel.id,
                        ProductModel.code,
                        ProductModel.product,
                        UnitMeasureModel.unit_measure,
                        SupplierModel.supplier,
                        CategoryModel.category,
                        ProductModel.category_id,
                        ProductModel.photo,
                        ProductModel.catalog,
                        ProductModel.short_description,
                        ProductModel.description
                    )
                    .order_by(ProductModel.product)
                )
            else:
                data = (
                    self.db.query(
                        ProductModel.id, 
                        ProductModel.code,
                        ProductModel.product,
                        UnitMeasureModel.unit_measure,
                        SupplierModel.supplier,
                        CategoryModel.category,
                        ProductModel.category_id,
                        ProductModel.photo,
                        ProductModel.catalog,
                        ProductModel.short_description,
                        ProductModel.description,
                        func.max(LotItemModel.public_sale_price).label("public_sale_price"),
                        func.max(LotItemModel.private_sale_price).label("private_sale_price"),
                        func.sum(LotItemModel.quantity).label("total_stock"),
                        func.group_concat(LotModel.lot_number.op('ORDER BY')(LotModel.lot_number)).label("lot_numbers")
                    )
                    .join(UnitMeasureModel, UnitMeasureModel.id == ProductModel.unit_measure_id, isouter=True)
                    .join(SupplierModel, SupplierModel.id == ProductModel.supplier_id, isouter=True)
                    .join(CategoryModel, CategoryModel.id == ProductModel.category_id, isouter=True)
                    .join(LotItemModel, LotItemModel.product_id == ProductModel.id)
                    .join(LotModel, LotModel.id == LotItemModel.lot_id)
                    .filter(ProductModel.category_id == category_id)
                    .group_by(
                        ProductModel.id,
                        ProductModel.code,
                        ProductModel.product,
                        UnitMeasureModel.unit_measure,
                        SupplierModel.supplier,
                        CategoryModel.category,
                        ProductModel.category_id,
                        ProductModel.photo,
                        ProductModel.catalog,
                        ProductModel.short_description,
                        ProductModel.description
                    )
                    .order_by(ProductModel.product)
                )

            serialized_data = [{
                    "id": product.id,
                    "code": product.code,
                    "product": product.product,
                    "unit_measure": product.unit_measure,
                    "supplier": product.supplier,
                    "category": product.category,
                    "category_id": product.category_id,
                    "photo": product.photo,
                    "catalog": product.catalog,
                    "short_description": product.short_description,
                    "description": product.description,
                    "public_sale_price": product.public_sale_price if product.public_sale_price is not None else 0,
                    "private_sale_price": product.private_sale_price if product.private_sale_price is not None else 0,
                    "total_stock": product.total_stock if product.total_stock is not None else 0,
                    "lot_numbers": product.lot_numbers if product.lot_numbers else ""
                } for product in data]

            return {
                "data": serialized_data
            }

        except Exception as e:
            error_message = str(e)
            return {"status": "error", "message": error_message}
        
    def sale_data(self, id):
        try:
            # Consulta del producto
            data_query = (
                self.db.query(
                    ProductModel.id,
                    ProductModel.supplier_id,
                    ProductModel.category_id,
                    ProductModel.code,
                    ProductModel.product,
                    ProductModel.original_unit_cost,
                    ProductModel.short_description,
                    ProductModel.description,
                    ProductModel.unit_measure_id,
                    ProductModel.photo,
                    ProductModel.catalog,
                    func.max(LotItemModel.public_sale_price).label("public_sale_price"),
                    func.max(LotItemModel.private_sale_price).label("private_sale_price"),
                    func.sum(LotItemModel.quantity).label("total_stock"),
                    func.group_concat(LotModel.lot_number.op('ORDER BY')(LotModel.lot_number)).label("lot_numbers")
                )
                .join(LotItemModel, LotItemModel.product_id == ProductModel.id)
                .join(LotModel, LotModel.id == LotItemModel.lot_id)
                .filter(ProductModel.id == id)
                .group_by(
                    ProductModel.id,
                    ProductModel.supplier_id,
                    ProductModel.category_id,
                    ProductModel.code,
                    ProductModel.product,
                    ProductModel.original_unit_cost,
                    ProductModel.short_description,
                    ProductModel.description,
                    ProductModel.unit_measure_id,
                    ProductModel.photo,
                    ProductModel.catalog
                )
                .first()
            )

            if not data_query:
                return {"error": "No se encontraron datos para el producto especificado."}

            # Diccionario base del producto
            product_data = {
                "id": data_query.id,
                "supplier_id": data_query.supplier_id,
                "category_id": data_query.category_id,
                "code": data_query.code,
                "original_unit_cost": data_query.original_unit_cost,
                "product": data_query.product,
                "short_description": data_query.short_description,
                "description": data_query.description,
                "unit_measure_id": data_query.unit_measure_id,
                "photo": data_query.photo,
                "catalog": data_query.catalog,
                "public_sale_price": data_query.public_sale_price if data_query.public_sale_price is not None else 0,
                "private_sale_price": data_query.private_sale_price if data_query.private_sale_price is not None else 0,
                "total_stock": data_query.total_stock if data_query.total_stock is not None else 0,
                "lot_numbers": data_query.lot_numbers if data_query.lot_numbers else "",
                "features": None
            }

            if data_query.unit_measure_id == 1 or data_query.unit_measure_id == 2 or data_query.unit_measure_id == 3:
                features = self.db.query(UnitFeatureModel).filter(
                    UnitFeatureModel.product_id == id
                ).first()
                if features:
                    product_data["features"] = {
                        "product_id": features.product_id,
                        "quantity_per_package": features.quantity_per_package,
                        "quantity_per_pallet": features.quantity_per_pallet,
                        "weight_per_unit": features.weight_per_unit,
                        "weight_per_pallet": features.weight_per_pallet,
                        "added_date": features.added_date,
                        "updated_date": features.updated_date,
                    }

            return {"product_data": product_data}

        except Exception as e:
            return {"error": str(e)}
        
    def get(self, id):
        try:
            data_query = (
                self.db.query(
                    ProductModel.id,
                    ProductModel.supplier_id,
                    ProductModel.category_id,
                    ProductModel.code,
                    ProductModel.product,
                    ProductModel.original_unit_cost,
                    ProductModel.discount_percentage,
                    ProductModel.final_unit_cost,
                    ProductModel.short_description,
                    ProductModel.description,
                    ProductModel.unit_measure_id,
                    ProductModel.is_compound,
                    ProductModel.compound_product_id,
                    ProductModel.photo,
                    ProductModel.catalog,
                    func.max(LotItemModel.public_sale_price).label("public_sale_price"),
                    func.max(LotItemModel.private_sale_price).label("private_sale_price")
                )
                .join(LotItemModel, LotItemModel.product_id == ProductModel.id, isouter=True)
                .filter(ProductModel.id == id)
                .group_by(
                    ProductModel.id,
                    ProductModel.supplier_id,
                    ProductModel.category_id,
                    ProductModel.code,
                    ProductModel.product,
                    ProductModel.original_unit_cost,
                    ProductModel.discount_percentage,
                    ProductModel.final_unit_cost,
                    ProductModel.short_description,
                    ProductModel.description,
                    ProductModel.unit_measure_id,
                    ProductModel.is_compound,
                    ProductModel.compound_product_id,
                    ProductModel.photo,
                    ProductModel.catalog
                )
                .first()
            )

            if not data_query:
                return {"error": "No se encontraron datos para el producto especificado."}

            # Diccionario base del producto
            product_data = {
                "id": data_query.id,
                "supplier_id": data_query.supplier_id,
                "category_id": data_query.category_id,
                "code": data_query.code,
                "original_unit_cost": data_query.original_unit_cost,
                "final_unit_cost": data_query.final_unit_cost,
                "discount_percentage": data_query.discount_percentage,
                "product": data_query.product,
                "short_description": data_query.short_description,
                "description": data_query.description,
                "unit_measure_id": data_query.unit_measure_id,
                "is_compound": data_query.is_compound,
                "compound_product_id": data_query.compound_product_id,
                "photo": data_query.photo,
                "catalog": data_query.catalog,
                "public_sale_price": data_query.public_sale_price if data_query.public_sale_price is not None else 0,
                "private_sale_price": data_query.private_sale_price if data_query.private_sale_price is not None else 0,
                "features": None,
                "inventory": 0
            }

            if data_query.unit_measure_id == 1 or data_query.unit_measure_id == 2 or data_query.unit_measure_id == 3:
                features = self.db.query(UnitFeatureModel).filter(
                    UnitFeatureModel.product_id == id
                ).first()
                if features:
                    product_data["features"] = {
                        "product_id": features.product_id,
                        "quantity_per_package": features.quantity_per_package,
                        "quantity_per_pallet": features.quantity_per_pallet,
                        "weight_per_unit": features.weight_per_unit,
                        "weight_per_pallet": features.weight_per_pallet,
                        "added_date": features.added_date,
                        "updated_date": features.updated_date,
                    }

            # Obtener cantidad en inventario desde inventories_lots (InventoryLotItemModel)
            inventory_quantity = (
                self.db.query(func.sum(InventoryLotItemModel.quantity))
                .join(LotItemModel, LotItemModel.id == InventoryLotItemModel.lot_item_id)
                .filter(LotItemModel.product_id == id)
                .scalar()
            )

            product_data["inventory"] = int(inventory_quantity) if inventory_quantity else 0

            return {"product_data": product_data}

        except Exception as e:
            return {"error": str(e)}

    def budget(self, id, customer_id=None):
        """
        Obtiene los datos del producto para presupuesto.
        Devuelve lo mismo que get() pero con public_sale_price y discount_percentage del cliente.
        """
        try:
            # Obtener los mismos datos que get()
            data_query = (
                self.db.query(
                    ProductModel.id,
                    ProductModel.supplier_id,
                    ProductModel.category_id,
                    ProductModel.code,
                    ProductModel.product,
                    ProductModel.original_unit_cost,
                    ProductModel.discount_percentage,
                    ProductModel.final_unit_cost,
                    ProductModel.short_description,
                    ProductModel.description,
                    ProductModel.unit_measure_id,
                    ProductModel.is_compound,
                    ProductModel.compound_product_id,
                    ProductModel.photo,
                    ProductModel.catalog,
                    func.max(LotItemModel.public_sale_price).label("public_sale_price"),
                    func.max(LotItemModel.private_sale_price).label("private_sale_price")
                )
                .join(LotItemModel, LotItemModel.product_id == ProductModel.id, isouter=True)
                .filter(ProductModel.id == id)
                .group_by(
                    ProductModel.id,
                    ProductModel.supplier_id,
                    ProductModel.category_id,
                    ProductModel.code,
                    ProductModel.product,
                    ProductModel.original_unit_cost,
                    ProductModel.discount_percentage,
                    ProductModel.final_unit_cost,
                    ProductModel.short_description,
                    ProductModel.description,
                    ProductModel.unit_measure_id,
                    ProductModel.is_compound,
                    ProductModel.compound_product_id,
                    ProductModel.photo,
                    ProductModel.catalog
                )
                .first()
            )

            if not data_query:
                return {"error": "No se encontraron datos para el producto especificado."}

            # Obtener descuento del cliente para este producto si se proporciona customer_id
            customer_discount = None
            if customer_id:
                customer_discount_record = (
                    self.db.query(CustomerProductDiscountModel)
                    .filter(CustomerProductDiscountModel.customer_id == customer_id)
                    .filter(CustomerProductDiscountModel.product_id == id)
                    .first()
                )
                if customer_discount_record:
                    customer_discount = customer_discount_record.discount_percentage

            # Diccionario base del producto (igual que get)
            product_data = {
                "id": data_query.id,
                "supplier_id": data_query.supplier_id,
                "category_id": data_query.category_id,
                "code": data_query.code,
                "original_unit_cost": data_query.original_unit_cost,
                "final_unit_cost": data_query.final_unit_cost,
                "discount_percentage": data_query.discount_percentage,
                "product": data_query.product,
                "short_description": data_query.short_description,
                "description": data_query.description,
                "unit_measure_id": data_query.unit_measure_id,
                "is_compound": data_query.is_compound,
                "compound_product_id": data_query.compound_product_id,
                "photo": data_query.photo,
                "catalog": data_query.catalog,
                "public_sale_price": data_query.public_sale_price if data_query.public_sale_price is not None else 0,
                "private_sale_price": data_query.private_sale_price if data_query.private_sale_price is not None else 0,
                "customer_discount_percentage": customer_discount,
                "features": None,
                "inventory": 0
            }

            if data_query.unit_measure_id == 1 or data_query.unit_measure_id == 2 or data_query.unit_measure_id == 3:
                features = self.db.query(UnitFeatureModel).filter(
                    UnitFeatureModel.product_id == id
                ).first()
                if features:
                    product_data["features"] = {
                        "product_id": features.product_id,
                        "quantity_per_package": features.quantity_per_package,
                        "quantity_per_pallet": features.quantity_per_pallet,
                        "weight_per_unit": features.weight_per_unit,
                        "weight_per_pallet": features.weight_per_pallet,
                        "added_date": features.added_date,
                        "updated_date": features.updated_date,
                    }

            # Obtener cantidad en inventario
            inventory_quantity = (
                self.db.query(func.sum(InventoryLotItemModel.quantity))
                .join(LotItemModel, LotItemModel.id == InventoryLotItemModel.lot_item_id)
                .filter(LotItemModel.product_id == id)
                .scalar()
            )

            product_data["inventory"] = int(inventory_quantity) if inventory_quantity else 0

            return {"product_data": product_data}

        except Exception as e:
            return {"error": str(e)}

    def delete(self, id):
        try:
            product_data = self.db.query(ProductModel).filter(ProductModel.id == id).first()
            if product_data:
                photo_name = product_data.photo
                remote_path = f"{photo_name}"
                FileClass(self.db).delete(remote_path)

                catalog_name = product_data.catalog
                remote_path = f"{catalog_name}"
                FileClass(self.db).delete(remote_path)

                self.db.delete(product_data)
                self.db.commit()
                return 'success'
            else:
                return "No data found"
        except Exception as e:
            error_message = str(e)
            return f"Error: {error_message}"

    def update(self, id, form_data, photo_remote_path, catalog_remote_path):
        existing_product = self.db.query(ProductModel).filter(ProductModel.id == id).one_or_none()

        if not existing_product:
            return {"status": "error", "message": "No data found"}

        try:
            existing_product.supplier_id = form_data.supplier_id
            existing_product.category_id = form_data.category_id
            existing_product.code = form_data.code
            existing_product.product = form_data.product
            existing_product.short_description = form_data.short_description
            existing_product.description = form_data.description
            existing_product.discount_percentage = form_data.discount_percentage
            existing_product.original_unit_cost = form_data.original_unit_cost
            existing_product.final_unit_cost = form_data.final_unit_cost
            existing_product.unit_measure_id = form_data.unit_measure_id
            existing_product.is_compound = form_data.is_compound
            existing_product.compound_product_id = form_data.compound_product_id

            if photo_remote_path:
                if existing_product.photo:
                    FileClass(self.db).delete(existing_product.photo)
                existing_product.photo = photo_remote_path

            if catalog_remote_path:
                if existing_product.catalog:
                    FileClass(self.db).delete(existing_product.catalog)
                existing_product.catalog = catalog_remote_path

            existing_product.updated_date = datetime.utcnow()

            if form_data.unit_measure_id == 1 or form_data.unit_measure_id == 2 or form_data.unit_measure_id == 3:
                unit_feature = self.db.query(UnitFeatureModel).filter_by(product_id=id).first()
                if unit_feature:
                    unit_feature.quantity_per_package = form_data.quantity_per_package
                    unit_feature.quantity_per_pallet = form_data.quantity_per_pallet
                    unit_feature.weight_per_unit = form_data.weight_per_unit
                    unit_feature.weight_per_pallet = form_data.weight_per_pallet
                    unit_feature.updated_date = datetime.utcnow()
                else:
                    new_feature = UnitFeatureModel(
                        product_id=id,
                        quantity_per_package=form_data.quantity_per_package,
                        quantity_per_pallet=form_data.quantity_per_pallet,
                        weight_per_unit=form_data.weight_per_unit,
                        weight_per_pallet=form_data.weight_per_pallet,
                        added_date=datetime.utcnow(),
                        updated_date=datetime.utcnow()
                    )
                    self.db.add(new_feature)

            self.db.commit()
            self.db.refresh(existing_product)
            return {"status": "success", "message": "Product updated successfully"}

        except Exception as e:
            self.db.rollback()
            return {"status": "error", "message": str(e)}

    def get_products_by_supplier(self, supplier_identifier):
        """
        Obtiene productos filtrados por proveedor usando RUT o ID del proveedor.
        
        Args:
            supplier_identifier: RUT del proveedor (ej: "12345678-9") o ID del proveedor (ej: "123")
        
        Returns:
            Lista de productos del proveedor especificado
        """
        try:
            # Determinar si el identificador es un ID numérico o un RUT
            is_numeric_id = supplier_identifier.isdigit()
            
            query = (
                self.db.query(
                    ProductModel.id,
                    ProductModel.code,
                    ProductModel.product,
                    ProductModel.description,
                    ProductModel.photo,
                    ProductModel.catalog,
                    SupplierModel.supplier.label("supplier_name"),
                    SupplierModel.identification_number.label("supplier_rut"),
                    CategoryModel.category.label("category_name"),
                    UnitMeasureModel.unit_measure.label("unit_measure"),
                    ProductModel.added_date
                )
                .join(SupplierModel, SupplierModel.id == ProductModel.supplier_id)
                .join(CategoryModel, CategoryModel.id == ProductModel.category_id, isouter=True)
                .join(UnitMeasureModel, UnitMeasureModel.id == ProductModel.unit_measure_id, isouter=True)
            )
            
            # Filtrar por ID del proveedor o RUT
            if is_numeric_id:
                query = query.filter(SupplierModel.id == int(supplier_identifier))
            else:
                query = query.filter(SupplierModel.identification_number == supplier_identifier)
            
            # Ordenar por nombre del producto
            query = query.order_by(ProductModel.product)
            
            results = query.all()
            
            if not results:
                return {
                    "status": "success", 
                    "message": f"No se encontraron productos para el proveedor: {supplier_identifier}",
                    "data": []
                }
            
            # Formatear los resultados
            formatted_data = []
            for result in results:
                formatted_data.append({
                    "id": result.id,
                    "code": result.code,
                    "product": result.product,
                    "description": result.description,
                    "photo": result.photo,
                    "catalog": result.catalog,
                    "supplier_name": result.supplier_name,
                    "supplier_rut": result.supplier_rut,
                    "category_name": result.category_name,
                    "unit_measure": result.unit_measure,
                    "added_date": result.added_date.strftime("%Y-%m-%d %H:%M:%S") if result.added_date else None
                })
            
            return {
                "status": "success",
                "message": f"Se encontraron {len(formatted_data)} productos del proveedor: {results[0].supplier_name}",
                "data": formatted_data,
                "supplier_info": {
                    "supplier_name": results[0].supplier_name,
                    "supplier_rut": results[0].supplier_rut
                }
            }
            
        except Exception as e:
            return {"status": "error", "message": f"Error al obtener productos por proveedor: {str(e)}"}
    
    def search(self, search_term: str):
        """
        Busca productos por código o nombre usando LIKE.
        
        Args:
            search_term: Término de búsqueda que se buscará en code y product
        
        Returns:
            Lista de productos que coinciden con el término de búsqueda
        """
        try:
            if not search_term or not search_term.strip():
                return {
                    "status": "error",
                    "message": "El término de búsqueda no puede estar vacío",
                    "data": []
                }
            
            # Limpiar el término de búsqueda
            search_term = search_term.strip()
            
            # Crear el patrón LIKE con % al inicio y final para búsqueda parcial
            search_pattern = f"%{search_term}%"
            
            # Buscar en code y product usando LIKE con OR
            query = (
                self.db.query(
                    ProductModel.id,
                    ProductModel.code,
                    ProductModel.product,
                    ProductModel.description,
                    ProductModel.photo,
                    ProductModel.catalog,
                    ProductModel.category_id,
                    SupplierModel.supplier.label("supplier_name"),
                    CategoryModel.category.label("category_name"),
                    UnitMeasureModel.unit_measure.label("unit_measure"),
                    func.max(LotItemModel.public_sale_price).label("public_sale_price"),
                    func.max(LotItemModel.private_sale_price).label("private_sale_price")
                )
                .join(SupplierModel, SupplierModel.id == ProductModel.supplier_id, isouter=True)
                .join(CategoryModel, CategoryModel.id == ProductModel.category_id, isouter=True)
                .join(UnitMeasureModel, UnitMeasureModel.id == ProductModel.unit_measure_id, isouter=True)
                .join(LotItemModel, LotItemModel.product_id == ProductModel.id, isouter=True)
                .filter(
                    or_(
                        ProductModel.code.like(search_pattern),
                        ProductModel.product.like(search_pattern)
                    )
                )
                .group_by(
                    ProductModel.id,
                    ProductModel.code,
                    ProductModel.product,
                    ProductModel.description,
                    ProductModel.photo,
                    ProductModel.catalog,
                    ProductModel.category_id,
                    SupplierModel.supplier,
                    CategoryModel.category,
                    UnitMeasureModel.unit_measure
                )
                .order_by(ProductModel.product)
            )
            
            results = query.all()
            
            if not results:
                return {
                    "status": "success",
                    "message": f"No se encontraron productos que coincidan con '{search_term}'",
                    "data": [],
                    "count": 0
                }
            
            # Formatear los resultados
            formatted_data = []
            for result in results:
                formatted_data.append({
                    "id": result.id,
                    "code": result.code,
                    "product": result.product,
                    "description": result.description,
                    "photo": result.photo,
                    "catalog": result.catalog,
                    "category_id": result.category_id,
                    "category": result.category_name,
                    "supplier_name": result.supplier_name,
                    "unit_measure": result.unit_measure,
                    "public_sale_price": result.public_sale_price if result.public_sale_price is not None else 0,
                    "private_sale_price": result.private_sale_price if result.private_sale_price is not None else 0
                })
            
            return {
                "status": "success",
                "message": f"Se encontraron {len(formatted_data)} productos que coinciden con '{search_term}'",
                "data": formatted_data,
                "count": len(formatted_data)
            }
            
        except Exception as e:
            return {
                "status": "error",
                "message": f"Error al buscar productos: {str(e)}",
                "data": []
            }