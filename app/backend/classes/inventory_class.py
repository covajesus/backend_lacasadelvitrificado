from app.backend.db.models import InventoryModel, ProductModel, LotModel, LotItemModel, InventoryLotItemModel, InventoryMovementModel, InventoryAuditModel
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
            print("Ajuste de inventario:", inventory_inputs)
            # Buscar el inventario
            inventory = self.db.query(InventoryModel).filter_by(id=inventory_inputs.inventory_id).first()
            if not inventory:
                return {"status": "error", "message": "Inventario no encontrado."}

            # Actualizar mínimos y máximos
            inventory.minimum_stock = inventory_inputs.minimum_stock
            inventory.maximum_stock = inventory_inputs.maximum_stock
            inventory.last_update = datetime.now()
            self.db.commit()

            # Buscar relación con ítem de lote
            inventory_lot = self.db.query(InventoryLotItemModel).filter_by(inventory_id=inventory.id).first()
            if not inventory_lot:
                return {"status": "error", "message": "Relación inventario-lote no encontrada."}

            inventory_lot_value = inventory_lot.quantity + (inventory_inputs.stock * -1)
            
            # Actualizar relación inventario-lote
            inventory_lot.quantity = inventory_lot_value
            inventory_lot.updated_date = datetime.now()
            self.db.commit()

            # Buscar ítem de lote
            lot_item = self.db.query(LotItemModel).filter_by(id=inventory_lot.lot_item_id).first()
            if not lot_item:
                return {"status": "error", "message": "Item del lote no encontrado."}

            lot_item_value = lot_item.quantity + (inventory_inputs.stock * -1)
            # Actualizar ítem del lote
            lot_item.product_id = inventory_inputs.product_id
            lot_item.quantity = lot_item_value
            lot_item.unit_cost = inventory_inputs.unit_cost
            lot_item.public_sale_price = inventory_inputs.public_sale_price
            lot_item.private_sale_price = inventory_inputs.private_sale_price
            lot_item.updated_date = datetime.now()
            self.db.commit()

            # Registrar el movimiento de inventario
            inventory_movement = InventoryMovementModel(
                inventory_id=inventory.id,
                lot_item_id=inventory_lot.lot_item_id,
                movement_type_id=3,
                quantity=(inventory_inputs.stock * -1),
                unit_cost=inventory_inputs.unit_cost,
                public_sale_price=inventory_inputs.public_sale_price,
                private_sale_price=inventory_inputs.private_sale_price,
                reason='Ajuste de inventario realizado.',
                added_date=datetime.now()
            )
            self.db.add(inventory_movement)
            self.db.commit()

            return {
                "status": "success",
                "message": "Ajuste de inventario registrado correctamente.",
                "inventory_id": inventory.id
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

            # Actualizar mínimos y máximos
            inventory.minimum_stock = inventory_inputs.minimum_stock
            inventory.maximum_stock = inventory_inputs.maximum_stock
            inventory.last_update = datetime.now()
            self.db.commit()

            # Buscar relación con ítem de lote
            inventory_lot = self.db.query(InventoryLotItemModel).filter_by(inventory_id=inventory.id).first()
            if not inventory_lot:
                return {"status": "error", "message": "Relación inventario-lote no encontrada."}
            
            inventory_lot_value = inventory_lot.quantity + (inventory_inputs.stock)

            # Actualizar relación inventario-lote
            inventory_lot.quantity = inventory_lot_value
            inventory_lot.updated_date = datetime.now()
            self.db.commit()

            # Buscar ítem de lote
            lot_item = self.db.query(LotItemModel).filter_by(id=inventory_lot.lot_item_id).first()
            if not lot_item:
                return {"status": "error", "message": "Item del lote no encontrado."}
            
            lot_item_value = lot_item.quantity + inventory_inputs.stock

            # Actualizar ítem del lote
            lot_item.product_id = inventory_inputs.product_id
            lot_item.quantity = lot_item_value
            lot_item.unit_cost = inventory_inputs.unit_cost
            lot_item.public_sale_price = inventory_inputs.public_sale_price
            lot_item.private_sale_price = inventory_inputs.private_sale_price
            lot_item.updated_date = datetime.now()
            self.db.commit()

            # Registrar el movimiento de inventario
            inventory_movement = InventoryMovementModel(
                inventory_id=inventory.id,
                lot_item_id=inventory_lot.lot_item_id,
                movement_type_id=4,
                quantity=inventory_inputs.stock,
                unit_cost=inventory_inputs.unit_cost,
                public_sale_price=inventory_inputs.public_sale_price,
                private_sale_price=inventory_inputs.private_sale_price,
                reason='Ajuste de inventario realizado.',
                added_date=datetime.now()
            )
            self.db.add(inventory_movement)
            self.db.commit()

            return {
                "status": "success",
                "message": "Ajuste de inventario registrado correctamente.",
                "inventory_id": inventory.id
            }

        except Exception as e:
            self.db.rollback()
            return {"status": "error", "message": str(e)}

    def store(self, inventory_inputs):
        try:
            existence_status = (
                self.db.query(InventoryModel)
                .join(InventoryLotItemModel, InventoryLotItemModel.inventory_id == InventoryModel.id)
                .join(LotItemModel, LotItemModel.id == InventoryLotItemModel.lot_item_id)
                .join(LotModel, LotModel.id == LotItemModel.lot_id)
                .filter(
                    InventoryModel.product_id == inventory_inputs.product_id,
                    LotModel.lot_number == inventory_inputs.lot_number
                )
                .count()
            )
    
            if existence_status == 0:
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

                # Crear lote asociado
                new_inventory_lot = InventoryLotItemModel(
                    inventory_id=new_inventory.id,
                    lot_item_id=new_lot_item.id,
                    quantity=inventory_inputs.stock,
                    added_date=datetime.now(),
                    updated_date=datetime.now()
                )
                self.db.add(new_inventory_lot)

                # Confirmar transacción
                self.db.commit()
                self.db.refresh(new_inventory_lot)

                # Crear lote asociado
                new_inventory_movement = InventoryMovementModel(
                    inventory_id=new_inventory.id,
                    lot_item_id=new_lot_item.id,
                    movement_type_id=1,
                    quantity=inventory_inputs.stock,
                    unit_cost=inventory_inputs.unit_cost,
                    public_sale_price=inventory_inputs.public_sale_price,
                    private_sale_price=inventory_inputs.private_sale_price,
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
                    inventory_id=new_inventory.id,
                    previous_stock=0,  # Asumiendo que es un nuevo inventario
                    new_stock=inventory_inputs.stock,
                    reason='Creación de inventario y lote.',
                    added_date=datetime.now()
                )
                self.db.add(new_inventory_audit)

                # Confirmar transacción
                self.db.commit()
                self.db.refresh(new_inventory_audit)

                return {
                    "status": "success",
                    "message": "Inventario y lote creados exitosamente.",
                    "inventory_id": new_inventory.id,
                    "lot_id": new_lot.id,
                    "lot_item_id": new_lot_item.id,
                    "inventory_lot_id": new_inventory_lot.id
                }
            else:
                return {"status": "error", "message": "El producto ya existe."}

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
