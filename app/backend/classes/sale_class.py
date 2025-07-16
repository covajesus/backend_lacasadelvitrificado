from app.backend.db.models import SaleModel, CustomerModel, SaleProductModel, ProductModel, InventoryModel, UnitMeasureModel, SupplierModel, CategoryModel, LotItemModel, LotModel, InventoryMovementModel, InventoryLotItemModel
from datetime import datetime
from sqlalchemy import func

class SaleClass:
    def __init__(self, db):
        self.db = db

    def get_all(self, rol_id = None, rut = None, page=0, items_per_page=10):
        customer = self.db.query(CustomerModel).filter(CustomerModel.identification_number == rut).first()
        
        try:
            if rol_id == 1 or rol_id == 2:
                query = (
                    self.db.query(
                        SaleModel.id,
                        SaleModel.subtotal,
                        SaleModel.tax,
                        SaleModel.total,
                        SaleModel.status_id,
                        SaleModel.added_date,                
                    )
                    .order_by(SaleModel.added_date.desc())
                )
            else:
                print(rol_id)
                query = (
                    self.db.query(
                        SaleModel.id,
                        SaleModel.subtotal,
                        SaleModel.tax,
                        SaleModel.total,
                        SaleModel.status_id,
                        SaleModel.added_date,                
                    )
                    .filter(SaleModel.customer_id == customer.id)
                    .order_by(SaleModel.added_date.desc())
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
                    "id": sale.id,
                    "subtotal": sale.subtotal,
                    "tax": sale.tax,
                    "total": sale.total,
                    "status_id": sale.status_id,
                    "added_date": sale.added_date.strftime("%Y-%m-%d %H:%M:%S")
                } for sale in data]

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
                    "id": sale.id,
                    "subtotal": sale.subtotal,
                    "tax": sale.tax,
                    "total": sale.total,
                    "status_id": sale.status_id,
                    "added_date": sale.added_date.strftime("%Y-%m-%d %H:%M:%S")
                } for sale in data]

                return serialized_data

        except Exception as e:
            error_message = str(e)
            return {"status": "error", "message": error_message}

    def validate_inventory_existence(self, sale_inputs):
        insufficient_products = []

        for item in sale_inputs.cart:
            result = (
                self.db.query(
                    func.sum(LotItemModel.quantity).label("total_stock"),
                    InventoryModel.minimum_stock,
                    ProductModel.product.label("product_name")
                )
                .select_from(ProductModel)
                .join(UnitMeasureModel, UnitMeasureModel.id == ProductModel.unit_measure_id, isouter=True)
                .join(SupplierModel, SupplierModel.id == ProductModel.supplier_id, isouter=True)
                .join(CategoryModel, CategoryModel.id == ProductModel.category_id, isouter=True)
                .join(LotItemModel, LotItemModel.product_id == ProductModel.id)
                .join(LotModel, LotModel.id == LotItemModel.lot_id)
                .join(InventoryModel, InventoryModel.product_id == ProductModel.id)
                .filter(ProductModel.id == item.id)
                .group_by(ProductModel.id, InventoryModel.minimum_stock, ProductModel.product)
                .first()
            )

            if result:
                total_stock, minimum_stock, product_name = result
                if (total_stock - item.quantity) < minimum_stock:
                    insufficient_products.append(product_name)
            else:
                # Producto no encontrado o sin stock
                product = self.db.query(ProductModel.product).filter(ProductModel.id == item.id).scalar()
                insufficient_products.append(product or f"Producto {item.id}")

        if insufficient_products:
            return 0, insufficient_products  # Hay productos con stock insuficiente

        return 1, []  # Todo OK


    def store_inventory_movement(self, sale_id, sale_inputs):
        for item in sale_inputs.cart:
            lot_ids = item.lot_numbers.split(',')
            quantity_to_deduct = item.quantity  # Total por descontar

            for lot_id in lot_ids:
                lot_id = lot_id.strip()
                if not lot_id or quantity_to_deduct <= 0:
                    continue

                # Obtener el lote individual por número de lote y producto
                lot_item, lot = (
                    self.db.query(LotItemModel, LotModel)
                    .join(LotModel, LotModel.id == LotItemModel.lot_id)
                    .filter(LotModel.lot_number == lot_id)
                    .filter(LotItemModel.product_id == item.id)
                    .first()
                )

                if not lot_item or lot_item.quantity <= 0:
                    continue

                deduct_qty = min(quantity_to_deduct, lot_item.quantity)

                # Obtener inventario relacionado
                inventory = (
                    self.db.query(InventoryModel)
                    .join(LotModel, LotModel.id == lot.id)
                    .filter(InventoryModel.product_id == item.id)
                    .first()
                )

                if not inventory:
                    continue

                # Descontar cantidad del lote
                lot_item.quantity = lot_item.quantity - deduct_qty
                lot_item.updated_date = datetime.now()
                self.db.commit()

                # Descontar cantidad del inventario_lote
                inventory_lot = self.db.query(InventoryLotItemModel).filter(
                    InventoryLotItemModel.lot_item_id == lot_item.id
                ).first()
                
                if not inventory_lot:
                    print(f"[!] No se encontró inventario_lote para inventory_id={inventory.id}, lot_item_id={lot_item.id}")

                if inventory_lot:
                    inventory_lot.quantity -= deduct_qty
                    inventory_lot.updated_date = datetime.now()
                    self.db.commit()

                # Registrar movimiento
                inventory_movement = InventoryMovementModel(
                    inventory_id=inventory.id,
                    lot_item_id=lot_item.id,
                    movement_type_id=2,
                    quantity=(deduct_qty * -1),
                    unit_cost=lot_item.unit_cost,
                    public_sale_price=lot_item.public_sale_price,
                    private_sale_price=lot_item.private_sale_price,
                    reason="Venta",
                    added_date=datetime.now()
                )
                self.db.add(inventory_movement)
                self.db.commit()

                if sale_inputs.rol_id == 1 or sale_inputs.rol_id == 2:
                    price = item.private_sale_price
                else:
                    price = item.public_sale_price

                sale_product = SaleProductModel(
                    sale_id=sale_id,
                    product_id=item.id,
                    inventory_movement_id=inventory_movement.id,
                    inventory_id=inventory.id,
                    lot_item_id=lot_item.id,
                    quantity=item.quantity,
                    price=price
                )

                self.db.add(sale_product)
                self.db.commit()

                quantity_to_deduct -= deduct_qty

                if quantity_to_deduct <= 0:
                    break

    def store(self, sale_inputs, photo_path):
        try:
            status, failed_products = self.validate_inventory_existence(sale_inputs)

            if status == 0:
                return {
                    "status": "error",
                    "message": f"Stock insuficiente para los productos: {', '.join(failed_products)}"
                }

            if sale_inputs.rol_id == 1 or sale_inputs.rol_id == 2:
                customer_id = 1
                status_id = 4
            else:
                customer_data = self.db.query(CustomerModel).filter(CustomerModel.identification_number == sale_inputs.customer_rut).first()
                if not customer_data:
                    customer_id = 0
                customer_id = customer_data.id
                status_id = 1

            new_sale = SaleModel(
                customer_id=customer_id,
                shipping_method_id=sale_inputs.shipping_method_id,
                dte_type_id=sale_inputs.document_type_id,
                status_id=status_id,
                subtotal=sale_inputs.subtotal,
                tax=sale_inputs.tax,
                total=sale_inputs.total,
                payment_support=photo_path,
                delivery_address=sale_inputs.delivery_address,
                added_date=datetime.now()
            )
            self.db.add(new_sale)
            self.db.flush()
            self.db.commit()
            self.db.refresh(new_sale)

            self.store_inventory_movement(new_sale.id, sale_inputs)

            return {"status": "Venta registrada exitosamente.", "sale_id": new_sale.id}

        except Exception as e:
            self.db.rollback()
            raise e

    def reverse(self, sale_id):
        sales_products = self.db.query(SaleProductModel).filter(SaleProductModel.sale_id == sale_id).all()

        try:
            for sales_product in sales_products:
                inventory_movement = self.db.query(InventoryMovementModel).filter(
                    InventoryMovementModel.id == sales_product.inventory_movement_id
                ).first()

                inventory_lot_item = self.db.query(InventoryLotItemModel).filter(InventoryLotItemModel.inventory_id == sales_product.inventory_id).filter(InventoryLotItemModel.lot_item_id == inventory_movement.lot_item_id).first()
                new_quantity = inventory_lot_item.quantity + (inventory_movement.quantity * -1)
                inventory_lot_item.quantity = new_quantity
                inventory_lot_item.updated_date = datetime.now()
                self.db.commit()

                lot_items = self.db.query(LotItemModel).filter(LotItemModel.id == sales_product.lot_item_id).first()
                lot_items.quantity = int(lot_items.quantity) + int(sales_product.quantity)
                lot_items.updated_date = datetime.now()
                self.db.commit()

                self.db.delete(inventory_movement)
                self.db.commit()

            return "Inventory reject successfully"
        except Exception as e:
            self.db.rollback()
            return "Error trying to reject inventory"
        
    def get(self, id):
        try:
            data_query = self.db.query(
                SaleModel.id,
                SaleModel.subtotal,
                SaleModel.tax,
                SaleModel.total,
                SaleModel.status_id,
                SaleModel.dte_type_id,
                SaleModel.shipping_method_id,
                SaleModel.payment_support,
                SaleModel.delivery_address,
                SaleModel.added_date,
                CustomerModel.social_reason
            ).join(CustomerModel, CustomerModel.id == SaleModel.customer_id, isouter=True).filter(SaleModel.id == id).first()

            if data_query:
                sale_data = {
                    "id": data_query.id,
                    "subtotal": data_query.subtotal,
                    "tax": data_query.tax,
                    "total": data_query.total,
                    "status_id": data_query.status_id,
                    "dte_type_id": data_query.dte_type_id,
                    "shipping_method_id": data_query.shipping_method_id,
                    "payment_support": data_query.payment_support,
                    "delivery_address": data_query.delivery_address,
                    "added_date": data_query.added_date.strftime("%d-%m-%Y %H:%M:%S"),
                    "social_reason": data_query.social_reason
                }

                return {"sale_data": sale_data}

            else:
                return {"error": "No se encontraron datos para el campo especificado."}
            
        except Exception as e:
            return {"error": str(e)}
        
    
    def details(self, id):
        try:
            data_query = self.db.query(
                SaleProductModel.id,
                SaleProductModel.quantity,
                SaleModel.subtotal,
                SaleModel.tax,
                SaleModel.total,
                SaleModel.status_id,
                SaleModel.dte_type_id,
                SaleModel.shipping_method_id,
                SaleModel.payment_support,
                SaleModel.delivery_address,
                SaleModel.added_date,
                ProductModel.product
            ).join(SaleModel, SaleModel.id == SaleProductModel.sale_id, isouter=True).join(ProductModel, ProductModel.id == SaleProductModel.product_id, isouter=True).filter(SaleModel.id == id).all()

            if not data_query:
                return {"error": "No se encontraron datos para el campo especificado."}
            
            sale_data = []

            for data in data_query:
                sale_details = {
                    "id": data.id,
                    "quantity": data.quantity,
                    "subtotal": data.subtotal,
                    "tax": data.tax,
                    "total": data.total,
                    "status_id": data.status_id,
                    "dte_type_id": data.dte_type_id,
                    "shipping_method_id": data.shipping_method_id,
                    "payment_support": data.payment_support,
                    "delivery_address": data.delivery_address,
                    "added_date": data.added_date.strftime("%d-%m-%Y %H:%M:%S"),
                    "product": data.product
                }

                sale_data.append(sale_details)

            return {"sale_data": sale_data}
            
        except Exception as e:
            return {"error": str(e)}
        

    def change_status(self, id, status_id):
        existing_sale = self.db.query(SaleModel).filter(SaleModel.id == id).one_or_none()

        if not existing_sale:
            return "No data found"

        try:
            existing_sale.status_id = status_id
            existing_sale.updated_date = datetime.utcnow()

            self.db.commit()
            self.db.refresh(existing_sale)
            return "Sale updated successfully"
        except Exception as e:
            self.db.rollback()
            error_message = str(e)
            return {"status": "error", "message": error_message}