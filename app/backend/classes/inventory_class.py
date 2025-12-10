from app.backend.db.models import InventoryModel, ProductModel, LotModel, LotItemModel, PreInventoryStockModel, InventoryLotItemModel, InventoryMovementModel, InventoryAuditModel, KardexValuesModel
from datetime import datetime
from sqlalchemy import func

class InventoryClass:
    def __init__(self, db):
        self.db = db

    def get_all(self, page=0, items_per_page=10):
        try:
            query = (
                self.db.query(
                    func.min(InventoryModel.id).label("id"),
                    InventoryModel.product_id,
                    func.min(InventoryModel.location_id).label("location_id"),
                    func.min(InventoryModel.minimum_stock).label("minimum_stock"),
                    func.min(InventoryModel.maximum_stock).label("maximum_stock"),
                    func.min(InventoryModel.added_date).label("added_date"),
                    func.min(InventoryModel.last_update).label("last_update"),
                    ProductModel.product,
                    func.min(LotItemModel.public_sale_price).label("public_sale_price"),
                    func.min(LotItemModel.private_sale_price).label("private_sale_price"),
                    func.avg(LotItemModel.unit_cost).label("average_cost"),
                    func.avg(LotItemModel.quantity).label("stock"),
                )
                .join(ProductModel, ProductModel.id == InventoryModel.product_id, isouter=True)
                .join(LotItemModel, LotItemModel.product_id == ProductModel.id, isouter=True)
                .join(LotModel, LotModel.id == LotItemModel.lot_id, isouter=True)
                .group_by(InventoryModel.product_id, ProductModel.product, LotModel.lot_number)
                .order_by(func.min(InventoryModel.id))
            )

            if page > 0:
                total_items = query.count()
                total_pages = (total_items + items_per_page - 1) // items_per_page

                if page < 1 or page > total_pages:
                    return {"status": "error", "message": "Invalid page number"}

                data = query.offset((page - 1) * items_per_page).limit(items_per_page).all()

                if not data:
                    return {"status": "error", "message": "No data found"}

                serialized_data = [{
                    "id": inventory.id,
                    "product_id": inventory.product_id,
                    "location_id": inventory.location_id,
                    "public_sale_price": inventory.public_sale_price,
                    "private_sale_price": inventory.private_sale_price,
                    "minimum_stock": inventory.minimum_stock,
                    "stock": inventory.stock,
                    "maximum_stock": inventory.maximum_stock,
                    "added_date": inventory.added_date.strftime('%Y-%m-%d %H:%M:%S') if inventory.added_date else None,
                    "last_update": inventory.last_update.strftime('%Y-%m-%d %H:%M:%S') if inventory.last_update else None,
                    "product": inventory.product,
                    "average_cost": round(inventory.average_cost, 2) if inventory.average_cost is not None else None
                } for inventory in data]

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
                    "id": inventory.id,
                    "product_id": inventory.product_id,
                    "location_id": inventory.location_id,
                    "public_sale_price": inventory.public_sale_price,
                    "private_sale_price": inventory.private_sale_price,
                    "minimum_stock": inventory.minimum_stock,
                    "stock": inventory.stock,
                    "maximum_stock": inventory.maximum_stock,
                    "added_date": inventory.added_date.strftime('%Y-%m-%d %H:%M:%S') if inventory.added_date else None,
                    "last_update": inventory.last_update.strftime('%Y-%m-%d %H:%M:%S') if inventory.last_update else None,
                    "product": inventory.product,
                    "average_cost": round(inventory.average_cost, 2) if inventory.average_cost is not None else None
                } for inventory in data]

                return serialized_data

        except Exception as e:
            return {"status": "error", "message": str(e)}

    
    def get(self, id):
        try:
            data_query = (
                self.db.query(
                    InventoryModel.id,
                    InventoryModel.product_id,
                    InventoryModel.location_id,
                    LotItemModel.quantity.label("stock"),
                    InventoryModel.minimum_stock,
                    InventoryModel.maximum_stock,
                    LotItemModel.id.label("lot_item_id"),
                    LotItemModel.public_sale_price,
                    LotItemModel.private_sale_price,
                    LotItemModel.unit_cost
                )
                .join(ProductModel, ProductModel.id == InventoryModel.product_id, isouter=True)
                .join(LotItemModel, LotItemModel.product_id == ProductModel.id, isouter=True)
                .order_by(InventoryModel.id)
            ).filter(InventoryModel.id == id).first()

            if data_query:
                inventory_data = {
                    "id": data_query.id,
                    "lot_item_id": data_query.lot_item_id,
                    "product_id": data_query.product_id,
                    "location_id": data_query.location_id,
                    "stock": data_query.stock,
                    "minimum_stock": data_query.minimum_stock,
                    "maximum_stock": data_query.maximum_stock,
                    "public_sale_price": data_query.public_sale_price,
                    "private_sale_price": data_query.private_sale_price,
                    "unit_cost": data_query.unit_cost
                }

                return {"inventory_data": inventory_data}

            else:
                return {"error": "No se encontraron datos para el campo especificado."}

        except Exception as e:
            error_message = str(e)
            return {"status": "error", "message": error_message}
    
    def update(self, id: int, inventory_inputs):
        try:
            # Buscar inventario
            inventory = self.db.query(InventoryModel).filter_by(id=id).first()
            if not inventory:
                return {"status": "error", "message": "Inventario no encontrado."}

            # Actualizar campos del inventario
            inventory.product_id = inventory_inputs.product_id
            inventory.location_id = inventory_inputs.location_id
            inventory.minimum_stock = inventory_inputs.minimum_stock
            inventory.maximum_stock = inventory_inputs.maximum_stock
            inventory.last_update = datetime.now()

            # Obtener relaciones
            inventory_lot = self.db.query(InventoryLotItemModel).filter_by(inventory_id=inventory.id).first()
            if inventory_lot:
                lot_item = self.db.query(LotItemModel).filter_by(id=inventory_lot.lot_item_id).first()
                if lot_item:
                    lot = self.db.query(LotModel).filter_by(id=lot_item.lot_id).first()

                    # Actualizar lote
                    if lot:
                        product = self.db.query(ProductModel).filter(ProductModel.id == inventory_inputs.product_id).first()
                        lot.supplier_id = product.supplier_id if product else None
                        lot.lot_number = inventory_inputs.lot_number
                        lot.arrival_date = inventory_inputs.arrival_date
                        lot.updated_date = datetime.now()

                    # Actualizar ítem del lote
                    lot_item.product_id = inventory_inputs.product_id
                    lot_item.quantity = inventory_inputs.stock
                    lot_item.unit_cost = inventory_inputs.unit_cost
                    lot_item.public_sale_price = inventory_inputs.public_sale_price
                    lot_item.private_sale_price = inventory_inputs.private_sale_price
                    lot_item.updated_date = datetime.now()

                # Actualizar inventario-lote relación
                inventory_lot.quantity = inventory_inputs.stock
                inventory_lot.updated_date = datetime.now()

            self.db.commit()
            self.db.refresh(inventory)

            return {
                "status": "success",
                "message": "Inventario actualizado correctamente.",
                "inventory_id": inventory.id
            }

        except Exception as e:
            self.db.rollback()
            return {"status": "error", "message": str(e)}

    def remove_adjustment(self, inventory_inputs):
        try:
            print("Ajuste de inventario (salida):", inventory_inputs)
            # Buscar el inventario
            inventory = self.db.query(InventoryModel).filter_by(id=inventory_inputs.inventory_id).first()
            if not inventory:
                return {"status": "error", "message": "Inventario no encontrado."}

            # Obtener product_id del inventario si no se proporciona
            product_id = inventory_inputs.product_id or inventory.product_id
            if not product_id:
                return {"status": "error", "message": "Product ID no encontrado."}

            # NO actualizar mínimos y máximos - solo actualizar fecha
            inventory.last_update = datetime.now()
            self.db.commit()

            # Calcular precios promedio de los lot_items existentes del mismo producto
            lot_items_prices = (
                self.db.query(
                    func.avg(LotItemModel.public_sale_price).label("avg_public_price"),
                    func.avg(LotItemModel.private_sale_price).label("avg_private_price")
                )
                .filter(LotItemModel.product_id == product_id)
                .first()
            )

            avg_public_price = int(lot_items_prices.avg_public_price or 0)
            avg_private_price = int(lot_items_prices.avg_private_price or 0)

            print(f"[+] Precios promedio calculados para producto {product_id}:")
            print(f"    - Precio público promedio: {avg_public_price}")
            print(f"    - Precio privado promedio: {avg_private_price}")

            # Obtener costo del kardex
            kardex_record = (
                self.db.query(KardexValuesModel)
                .filter(KardexValuesModel.product_id == product_id)
                .first()
            )

            if not kardex_record:
                return {"status": "error", "message": "No se encontró registro de kardex para este producto."}

            unit_cost = kardex_record.average_cost
            print(f"[+] Costo obtenido del kardex: {unit_cost}")

            # Reducir cantidad en kardex SIN actualizar costo promedio
            new_quantity = kardex_record.quantity - inventory_inputs.stock
            if new_quantity < 0:
                new_quantity = 0

            kardex_record.quantity = new_quantity
            kardex_record.updated_date = datetime.now()
            self.db.commit()

            print(f"[+] Kardex actualizado para producto {product_id}:")
            print(f"    - Cantidad anterior: {kardex_record.quantity + inventory_inputs.stock}")
            print(f"    - Cantidad removida: {inventory_inputs.stock}")
            print(f"    - Nueva cantidad: {new_quantity}")
            print(f"    - Costo promedio se mantiene: {kardex_record.average_cost}")

            # Registrar el movimiento de inventario (solo aquí)
            inventory_movement = InventoryMovementModel(
                inventory_id=inventory.id,
                lot_item_id=0,  # 0 para remove adjustment
                movement_type_id=3,  # Tipo de movimiento: Salida
                quantity=(inventory_inputs.stock * -1),  # Cantidad negativa para salida
                unit_cost=unit_cost,
                reason='Ajuste de inventario (salida) realizado.',
                added_date=datetime.now()
            )
            self.db.add(inventory_movement)
            self.db.commit()

            return {
                "status": "success",
                "message": "Ajuste de inventario (salida) registrado correctamente. Kardex actualizado.",
                "inventory_id": inventory.id,
                "movement_id": inventory_movement.id,
                "kardex_updated": {
                    "previous_quantity": kardex_record.quantity + inventory_inputs.stock,
                    "removed_quantity": inventory_inputs.stock,
                    "new_quantity": new_quantity,
                    "average_cost": kardex_record.average_cost
                }
            }

        except Exception as e:
            self.db.rollback()
            return {"status": "error", "message": str(e)}

    def add_adjustment(self, inventory_inputs):
        try:
            print("Ajuste de inventario:", inventory_inputs)
            # Buscar el inventario
            inventory = self.db.query(InventoryModel).filter_by(id=inventory_inputs.inventory_id).first()
            if not inventory:
                return {"status": "error", "message": "Inventario no encontrado."}

            # Obtener product_id del inventario si no se proporciona
            product_id = inventory_inputs.product_id or inventory.product_id
            if not product_id:
                return {"status": "error", "message": "Product ID no encontrado."}

            # NO actualizar mínimos y máximos - solo actualizar fecha
            inventory.last_update = datetime.now()
            self.db.commit()

            # Buscar o crear el lote
            lot = (
                self.db.query(LotModel)
                .filter(LotModel.lot_number == inventory_inputs.lot_number)
                .filter(LotModel.supplier_id == inventory.supplier_id if hasattr(inventory, 'supplier_id') else None)
                .first()
            )

            if not lot:
                # Crear nuevo lote
                lot = LotModel(
                    supplier_id=inventory.supplier_id if hasattr(inventory, 'supplier_id') else 1,
                    lot_number=inventory_inputs.lot_number,
                    arrival_date=datetime.now(),
                    added_date=datetime.now(),
                    updated_date=datetime.now()
                )
                self.db.add(lot)
                self.db.commit()
                self.db.refresh(lot)
                print(f"[+] Nuevo lote creado: {inventory_inputs.lot_number}")

            # Buscar o crear lot_item
            lot_item = (
                self.db.query(LotItemModel)
                .filter(LotItemModel.lot_id == lot.id)
                .filter(LotItemModel.product_id == product_id)
                .first()
            )

            if not lot_item:
                # Crear nuevo lot_item
                lot_item = LotItemModel(
                    lot_id=lot.id,
                    product_id=product_id,
                    quantity=inventory_inputs.stock,
                    unit_cost=inventory_inputs.unit_cost,
                    public_sale_price=inventory_inputs.public_sale_price,
                    private_sale_price=inventory_inputs.private_sale_price,
                    added_date=datetime.now(),
                    updated_date=datetime.now()
                )
                self.db.add(lot_item)
                self.db.commit()
                self.db.refresh(lot_item)
                print(f"[+] Nuevo lot_item creado para producto {product_id}")
            else:
                # Actualizar lot_item existente
                lot_item.quantity = lot_item.quantity + inventory_inputs.stock
                lot_item.unit_cost = inventory_inputs.unit_cost
                lot_item.public_sale_price = inventory_inputs.public_sale_price
                lot_item.private_sale_price = inventory_inputs.private_sale_price
                lot_item.updated_date = datetime.now()
                self.db.commit()
                print(f"[+] Lot_item actualizado para producto {product_id}")

            # Buscar o crear inventory_lot
            inventory_lot = (
                self.db.query(InventoryLotItemModel)
                .filter(InventoryLotItemModel.inventory_id == inventory.id)
                .filter(InventoryLotItemModel.lot_item_id == lot_item.id)
                .first()
            )

            if not inventory_lot:
                # Crear nuevo inventory_lot
                inventory_lot = InventoryLotItemModel(
                    inventory_id=inventory.id,
                    lot_item_id=lot_item.id,
                    quantity=inventory_inputs.stock,
                    added_date=datetime.now(),
                    updated_date=datetime.now()
                )
                self.db.add(inventory_lot)
                self.db.commit()
                self.db.refresh(inventory_lot)
                print(f"[+] Nuevo inventory_lot creado")
            else:
                # Actualizar inventory_lot existente
                inventory_lot.quantity = inventory_lot.quantity + inventory_inputs.stock
                inventory_lot.updated_date = datetime.now()
                self.db.commit()
                print(f"[+] Inventory_lot actualizado")

            # Actualizar kardex con la nueva cantidad y recalcular costo promedio
            self.update_kardex_values(
                product_id=product_id,
                new_quantity=inventory_inputs.stock,
                new_unit_cost=inventory_inputs.unit_cost
            )

            # Obtener unit_cost del kardex para el movimiento (si existe)
            kardex_record = (
                self.db.query(KardexValuesModel)
                .filter(KardexValuesModel.product_id == product_id)
                .first()
            )
            
            movement_unit_cost = kardex_record.average_cost if kardex_record else inventory_inputs.unit_cost
            print(f"[+] Unit cost para movimiento: {movement_unit_cost} (del kardex: {kardex_record.average_cost if kardex_record else 'N/A'})")

            # Registrar el movimiento de inventario
            inventory_movement = InventoryMovementModel(
                inventory_id=inventory.id,
                lot_item_id=lot_item.id,
                movement_type_id=4,
                quantity=inventory_inputs.stock,
                unit_cost=movement_unit_cost,  # Usa costo del kardex si existe
                reason='Ajuste de inventario realizado.',
                added_date=datetime.now()
            )
            self.db.add(inventory_movement)
            self.db.commit()

            return {
                "status": "success",
                "message": "Ajuste de inventario registrado correctamente. Kardex actualizado.",
                "inventory_id": inventory.id,
                "lot_id": lot.id,
                "lot_item_id": lot_item.id,
                "inventory_lot_id": inventory_lot.id
            }

        except Exception as e:
            self.db.rollback()
            return {"status": "error", "message": str(e)}

    def pre_save_inventory_quantities(self, shopping_id: int, data):
        try:
            for item in data.items:
                new_pre_inventory_stock = PreInventoryStockModel(
                    product_id=item.product_id,
                    shopping_id=shopping_id,
                    stock=item.stock
                )
                self.db.add(new_pre_inventory_stock)
                self.db.commit()
 
        except Exception as e:
            self.db.rollback()
            return {"status": "error", "message": str(e)}
    
    def update_kardex_values(self, product_id, new_quantity, new_unit_cost):
        """
        Actualiza los valores del kardex para un producto específico.
        Calcula el costo promedio usando el método kardex.
        
        Ejemplo:
        Saldo inicial: 100 unidades × 36.000 = 3.600.000
        Compra: 50 unidades × 42.000 = 2.100.000
        Nuevo total disponible:
        - Unidades: 100 + 50 = 150
        - Valor: 3.600.000 + 2.100.000 = 5.700.000
        - Costo promedio unitario nuevo: 5.700.000 / 150 = 38.000
        """
        try:
            # Buscar el registro de kardex existente para este producto
            kardex_record = (
                self.db.query(KardexValuesModel)
                .filter(KardexValuesModel.product_id == product_id)
                .first()
            )
            
            if kardex_record:
                # Calcular el nuevo costo promedio usando kardex
                current_quantity = kardex_record.quantity
                current_average_cost = float(kardex_record.average_cost)
                
                # Calcular valores actuales
                current_total_value = current_quantity * current_average_cost
                new_total_value = new_quantity * new_unit_cost
                
                # Nuevos totales
                new_total_quantity = current_quantity + new_quantity
                new_total_value_sum = current_total_value + new_total_value
                
                # Calcular nuevo costo promedio
                if new_total_quantity > 0:
                    new_average_cost = new_total_value_sum / new_total_quantity
                else:
                    new_average_cost = new_unit_cost
                
                # Actualizar el registro existente
                kardex_record.quantity = new_total_quantity
                kardex_record.average_cost = int(round(new_average_cost))
                kardex_record.updated_date = datetime.now()
                
                print(f"[+] Kardex actualizado para producto {product_id}:")
                print(f"    - Cantidad anterior: {current_quantity}")
                print(f"    - Cantidad nueva: {new_quantity}")
                print(f"    - Total cantidad: {new_total_quantity}")
                print(f"    - Costo promedio anterior: {current_average_cost}")
                print(f"    - Costo promedio nuevo: {new_average_cost}")
                
            else:
                # Crear nuevo registro de kardex
                kardex_record = KardexValuesModel(
                    product_id=product_id,
                    quantity=new_quantity,
                    average_cost=int(round(new_unit_cost)),
                    added_date=datetime.now(),
                    updated_date=datetime.now()
                )
                self.db.add(kardex_record)
                
                print(f"[+] Nuevo kardex creado para producto {product_id}:")
                print(f"    - Cantidad: {new_quantity}")
                print(f"    - Costo promedio: {new_unit_cost}")
            
            self.db.commit()
            return kardex_record
            
        except Exception as e:
            self.db.rollback()
            print(f"[!] Error actualizando kardex para producto {product_id}: {str(e)}")
            raise e
        
    def store(self, inventory_inputs):
        try:
            # Verificar si el producto ya existe en la tabla inventory (solo por product_id)
            existing_inventory = (
                self.db.query(InventoryModel)
                .filter(InventoryModel.product_id == inventory_inputs.product_id)
                .first()
            )
    
            if not existing_inventory:
                # Crear inventario
                new_inventory = InventoryModel(
                    product_id=inventory_inputs.product_id,
                    location_id=inventory_inputs.location_id,
                    minimum_stock=inventory_inputs.minimum_stock,
                    maximum_stock=inventory_inputs.maximum_stock,
                    added_date=datetime.now(),
                    last_update=datetime.now()
                )
                self.db.add(new_inventory)
                self.db.flush()  # Para obtener el ID antes del commit
                self.db.refresh(new_inventory)
                inventory_id = new_inventory.id
                print(f"[+] Nuevo inventario creado con ID: {inventory_id}")
            else:
                # Usar el inventario existente
                inventory_id = existing_inventory.id
                print(f"[+] Usando inventario existente con ID: {inventory_id}")

            product = self.db.query(ProductModel).filter(ProductModel.id == inventory_inputs.product_id).first()

            # Crear lote asociado
            new_lot = LotModel(
                supplier_id=product.supplier_id,
                lot_number=inventory_inputs.lot_number,
                arrival_date=inventory_inputs.arrival_date,
                added_date=datetime.now(),
                updated_date=datetime.now()
            )
            self.db.add(new_lot)

            # Confirmar transacción
            self.db.commit()
            self.db.refresh(new_lot)
            
            # Actualizar el status_id del shopping a 7 si viene de un shopping
            if hasattr(inventory_inputs, 'shopping_id') and inventory_inputs.shopping_id:
                from app.backend.db.models import ShoppingModel
                shopping = self.db.query(ShoppingModel).filter(ShoppingModel.id == inventory_inputs.shopping_id).first()
                if shopping:
                    shopping.status_id = 7
                    shopping.updated_date = datetime.now()
                    self.db.commit()
                    print(f"Shopping {inventory_inputs.shopping_id} actualizado a status_id = 7")
            
            # Crear lote asociado
            new_lot_item = LotItemModel(
                lot_id=new_lot.id,
                product_id=inventory_inputs.product_id,
                quantity=inventory_inputs.stock,
                unit_cost=inventory_inputs.unit_cost,
                public_sale_price=inventory_inputs.public_sale_price,
                private_sale_price=inventory_inputs.private_sale_price,
                added_date=datetime.now(),
                updated_date=datetime.now()
            )
            self.db.add(new_lot_item)

            # Confirmar transacción
            self.db.commit()
            self.db.refresh(new_lot_item)

            # Actualizar kardex_values con el nuevo lote
            self.update_kardex_values(
                product_id=inventory_inputs.product_id,
                new_quantity=inventory_inputs.stock,
                new_unit_cost=inventory_inputs.unit_cost
            )

            # Crear lote asociado
            new_inventory_lot = InventoryLotItemModel(
                inventory_id=inventory_id,  # Usar el inventory_id (nuevo o existente)
                lot_item_id=new_lot_item.id,
                quantity=inventory_inputs.stock,
                added_date=datetime.now(),
                updated_date=datetime.now()
            )
            self.db.add(new_inventory_lot)

            # Confirmar transacción
            self.db.commit()
            self.db.refresh(new_inventory_lot)

            # Obtener unit_cost del kardex para el movimiento (si existe)
            kardex_record = (
                self.db.query(KardexValuesModel)
                .filter(KardexValuesModel.product_id == inventory_inputs.product_id)
                .first()
            )
            
            movement_unit_cost = kardex_record.average_cost if kardex_record else inventory_inputs.unit_cost
            print(f"[+] Unit cost para movimiento: {movement_unit_cost} (del kardex: {kardex_record.average_cost if kardex_record else 'N/A'})")

            # Crear lote asociado
            new_inventory_movement = InventoryMovementModel(
                inventory_id=inventory_id,  # Usar el inventory_id (nuevo o existente)
                lot_item_id=new_lot_item.id,
                movement_type_id=1,
                quantity=inventory_inputs.stock,
                unit_cost=movement_unit_cost,  # Usa costo del kardex si existe
                reason='Agregado producto al inventario.',
                added_date=datetime.now()
            )
            self.db.add(new_inventory_movement)

            # Confirmar transacción
            self.db.commit()
            self.db.refresh(new_inventory_movement)

            # Crear lote asociado
            new_inventory_audit = InventoryAuditModel(
                user_id=inventory_inputs.user_id,
                inventory_id=inventory_id,  # Usar el inventory_id (nuevo o existente)
                previous_stock=0,  # Asumiendo que es un nuevo inventario
                new_stock=inventory_inputs.stock,
                reason='Creación de inventario y lote.' if not existing_inventory else 'Agregado lote a inventario existente.',
                added_date=datetime.now()
            )
            self.db.add(new_inventory_audit)

            # Confirmar transacción
            self.db.commit()

            message = "Inventario y lote creados exitosamente." if not existing_inventory else "Lote agregado a inventario existente."
            
            return {
                "status": "success",
                "message": message,
                "inventory_id": inventory_id,
                "lot_id": new_lot.id,
                "lot_item_id": new_lot_item.id,
                "inventory_lot_id": new_inventory_lot.id
            }

        except Exception as e:
            self.db.rollback()
            return {"status": "error", "message": str(e)}
        
    def delete(self, id):
        try:
            # Buscar inventario
            inventory = self.db.query(InventoryModel).filter_by(id=id).first()
            if not inventory:
                return {"status": "error", "message": "Inventario no encontrado."}

            # Buscar vínculos con lotes
            inventory_lot = self.db.query(InventoryLotItemModel).filter_by(inventory_id=inventory.id).first()

            if inventory_lot:
                # Buscar movimientos del inventario
                movements = self.db.query(InventoryMovementModel).filter_by(
                    inventory_id=inventory.id,
                    lot_item_id=inventory_lot.lot_item_id
                ).all()
                for movement in movements:
                    self.db.delete(movement)

                # Buscar auditorías
                audits = self.db.query(InventoryAuditModel).filter_by(inventory_id=inventory.id).all()
                for audit in audits:
                    self.db.delete(audit)

                # Buscar lot_item
                lot_item = self.db.query(LotItemModel).filter_by(id=inventory_lot.lot_item_id).first()
                if lot_item:
                    # Buscar lote
                    lot = self.db.query(LotModel).filter_by(id=lot_item.lot_id).first()

                    # Eliminar lot_item
                    self.db.delete(lot_item)

                    # Eliminar lote si existe
                    if lot:
                        self.db.delete(lot)

                # Eliminar vínculo inventario-lote
                self.db.delete(inventory_lot)

            # Eliminar inventario
            self.db.delete(inventory)

            # Confirmar
            self.db.commit()

            return {"status": "success", "message": "Inventario y relaciones eliminadas correctamente."}

        except Exception as e:
            self.db.rollback()
            return {"status": "error", "message": str(e)}
