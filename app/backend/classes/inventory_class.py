from app.backend.db.models import (
    InventoryModel,
    ProductModel,
    LotModel,
    LotItemModel,
    PreInventoryStockModel,
    InventoryMovementModel,
    InventoryAuditModel,
    MovementTypeModel,
    SaleProductModel,
    UnitFeatureModel,
)
from datetime import datetime
from sqlalchemy import func

from app.backend.classes.inventory_stock import (
    AVERAGE_UNIT_COST_EXCLUDED_MOVEMENT_TYPE_IDS,
    stock_sum_for_inventory,
    stock_sum_for_product,
    average_unit_cost_for_product,
)

class InventoryClass:
    def __init__(self, db):
        self.db = db

    def _quantity_per_package_for_product(self, product_id: int) -> int:
        """``unit_features.quantity_per_package``; si no hay fila o es 0 → 1."""
        row = (
            self.db.query(UnitFeatureModel)
            .filter(UnitFeatureModel.product_id == product_id)
            .first()
        )
        if row and row.quantity_per_package:
            q = int(row.quantity_per_package)
            return q if q > 0 else 1
        return 1

    def get_all(self, page=0, items_per_page=10):
        try:
            stock_sq = (
                self.db.query(
                    InventoryModel.product_id.label("pid"),
                    func.coalesce(func.sum(InventoryMovementModel.quantity), 0).label("stock_sum"),
                )
                .join(
                    InventoryMovementModel,
                    InventoryMovementModel.inventory_id == InventoryModel.id,
                )
                .group_by(InventoryModel.product_id)
                .subquery()
            )
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
                    func.coalesce(func.max(stock_sq.c.stock_sum), 0).label("stock"),
                )
                .join(ProductModel, ProductModel.id == InventoryModel.product_id, isouter=True)
                .join(LotItemModel, LotItemModel.product_id == ProductModel.id, isouter=True)
                .join(LotModel, LotModel.id == LotItemModel.lot_id, isouter=True)
                .outerjoin(stock_sq, stock_sq.c.pid == InventoryModel.product_id)
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

                serialized_data = []
                for inventory in data:
                    ac = average_unit_cost_for_product(self.db, inventory.product_id)
                    serialized_data.append({
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
                        "average_cost": round(float(ac), 2) if ac else None,
                    })

                return {
                    "total_items": total_items,
                    "total_pages": total_pages,
                    "current_page": page,
                    "items_per_page": items_per_page,
                    "data": serialized_data
                }

            else:
                data = query.all()

                serialized_data = []
                for inventory in data:
                    ac = average_unit_cost_for_product(self.db, inventory.product_id)
                    serialized_data.append({
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
                        "average_cost": round(float(ac), 2) if ac else None,
                    })

                return serialized_data

        except Exception as e:
            return {"status": "error", "message": str(e)}

    
    def get(self, id):
        try:
            inv = self.db.query(InventoryModel).filter(InventoryModel.id == id).first()
            if not inv:
                return {"error": "No se encontraron datos para el campo especificado."}

            stock = stock_sum_for_inventory(self.db, id)

            # Fila de referencia para edición: preferir primera **no salida** (entrada/ajuste).
            ref_mov = (
                self.db.query(InventoryMovementModel)
                .filter(InventoryMovementModel.inventory_id == inv.id)
                .filter(
                    ~InventoryMovementModel.movement_type_id.in_(
                        AVERAGE_UNIT_COST_EXCLUDED_MOVEMENT_TYPE_IDS
                    )
                )
                .order_by(InventoryMovementModel.id.asc())
                .first()
            )
            if ref_mov is None:
                ref_mov = (
                    self.db.query(InventoryMovementModel)
                    .filter(InventoryMovementModel.inventory_id == inv.id)
                    .order_by(InventoryMovementModel.id.asc())
                    .first()
                )
            inventory_movement_id = ref_mov.id if ref_mov else None
            movement_lot_item_id = ref_mov.lot_item_id if ref_mov else None

            lot_item = None
            if movement_lot_item_id is not None:
                lot_item = self.db.query(LotItemModel).filter_by(id=movement_lot_item_id).first()

            if not lot_item:
                lot_item = (
                    self.db.query(LotItemModel)
                    .filter(LotItemModel.product_id == inv.product_id)
                    .order_by(LotItemModel.id.desc())
                    .first()
                )

            lot_number = None
            arrival_date = None
            public_sale_price = None
            private_sale_price = None
            lot_item_id = None

            if lot_item:
                lot_item_id = lot_item.id
                public_sale_price = lot_item.public_sale_price
                private_sale_price = lot_item.private_sale_price
                if lot_item.lot_id:
                    lot = self.db.query(LotModel).filter_by(id=lot_item.lot_id).first()
                    if lot:
                        lot_number = lot.lot_number
                        arrival_date = lot.arrival_date.isoformat() if lot.arrival_date else None

            if ref_mov is not None and ref_mov.unit_cost is not None:
                unit_cost = int(ref_mov.unit_cost)
            else:
                unit_cost = int(average_unit_cost_for_product(self.db, inv.product_id))

            inventory_data = {
                "id": inv.id,
                "inventory_movement_id": inventory_movement_id,
                "lot_item_id": lot_item_id,
                "product_id": inv.product_id,
                "location_id": inv.location_id,
                "stock": stock,
                "minimum_stock": inv.minimum_stock,
                "maximum_stock": inv.maximum_stock,
                "public_sale_price": public_sale_price,
                "private_sale_price": private_sale_price,
                "unit_cost": unit_cost,
                "lot_number": lot_number,
                "arrival_date": arrival_date,
            }

            return {"inventory_data": inventory_data}

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
            inventory.minimum_stock = int(inventory_inputs.minimum_stock)
            inventory.maximum_stock = int(inventory_inputs.maximum_stock)
            inventory.last_update = datetime.now()

            new_uc = int(inventory_inputs.unit_cost or 0)

            first_mov = (
                self.db.query(InventoryMovementModel)
                .filter(InventoryMovementModel.inventory_id == inventory.id)
                .filter(
                    ~InventoryMovementModel.movement_type_id.in_(
                        AVERAGE_UNIT_COST_EXCLUDED_MOVEMENT_TYPE_IDS
                    )
                )
                .order_by(InventoryMovementModel.id.asc())
                .first()
            )
            if first_mov is None:
                first_mov = (
                    self.db.query(InventoryMovementModel)
                    .filter(InventoryMovementModel.inventory_id == inventory.id)
                    .order_by(InventoryMovementModel.id.asc())
                    .first()
                )

            req_mid = inventory_inputs.inventory_movement_id
            if req_mid is not None:
                try:
                    req_mid = int(req_mid)
                except (TypeError, ValueError):
                    req_mid = None

            target_mov = None
            if req_mid is not None:
                target_mov = (
                    self.db.query(InventoryMovementModel)
                    .filter(
                        InventoryMovementModel.id == req_mid,
                        InventoryMovementModel.inventory_id == inventory.id,
                    )
                    .first()
                )

            # Costo: solo la fila ``inventories_movements.id`` indicada (no salidas 2/3).
            if target_mov is not None and target_mov.movement_type_id not in AVERAGE_UNIT_COST_EXCLUDED_MOVEMENT_TYPE_IDS:
                target_mov.unit_cost = new_uc

            ref_mov = target_mov or first_mov
            lot_item_id = ref_mov.lot_item_id if ref_mov else None
            lot_item_for_private = None
            if lot_item_id is not None:
                lot_item = self.db.query(LotItemModel).filter_by(id=lot_item_id).first()
                if lot_item:
                    lot_item_for_private = lot_item
                    lot = self.db.query(LotModel).filter_by(id=lot_item.lot_id).first()
                    if lot:
                        product = self.db.query(ProductModel).filter(ProductModel.id == inventory_inputs.product_id).first()
                        lot.supplier_id = product.supplier_id if product else None
                        lot.lot_number = inventory_inputs.lot_number
                        lot.arrival_date = inventory_inputs.arrival_date
                        lot.updated_date = datetime.now()
                    lot_item.product_id = inventory_inputs.product_id
                    lot_item.public_sale_price = inventory_inputs.public_sale_price
                    lot_item.updated_date = datetime.now()

                current = stock_sum_for_inventory(self.db, inventory.id)
                target = int(inventory_inputs.stock or 0)
                delta = target - current
                if delta != 0:
                    movement_uc = new_uc or int(
                        average_unit_cost_for_product(self.db, inventory_inputs.product_id)
                        or 0
                    )
                    self.db.add(
                        InventoryMovementModel(
                            inventory_id=inventory.id,
                            lot_item_id=lot_item_id,
                            movement_type_id=4,
                            quantity=delta,
                            unit_cost=movement_uc,
                            reason="Ajuste por actualización de inventario",
                            added_date=datetime.now(),
                        )
                    )

            # Precio privado = costo medio × paquete; mismo valor en **todos** los ``lot_items`` del producto
            if lot_item_for_private is not None:
                self.db.flush()
                pid = int(inventory_inputs.product_id)
                avg_uc = int(average_unit_cost_for_product(self.db, pid) or 0)
                qpp = self._quantity_per_package_for_product(pid)
                new_private = float(int(round(float(avg_uc) * float(qpp))))
                now = datetime.now()
                self.db.query(LotItemModel).filter(LotItemModel.product_id == pid).update(
                    {
                        LotItemModel.private_sale_price: new_private,
                        LotItemModel.updated_date: now,
                    },
                    synchronize_session=False,
                )

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

            unit_cost = int(average_unit_cost_for_product(self.db, product_id))
            print(f"[+] Costo medio desde movimientos: {unit_cost}")

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
                "message": "Ajuste de inventario (salida) registrado correctamente.",
                "inventory_id": inventory.id,
                "movement_id": inventory_movement.id,
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
                # Crear nuevo lot_item; el saldo queda en inventories_movements
                lot_item = LotItemModel(
                    lot_id=lot.id,
                    product_id=product_id,
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
                lot_item.public_sale_price = inventory_inputs.public_sale_price
                lot_item.private_sale_price = inventory_inputs.private_sale_price
                lot_item.updated_date = datetime.now()
                self.db.commit()
                print(f"[+] Lot_item actualizado para producto {product_id}")

            movement_unit_cost = self.weighted_unit_cost_after_purchase(
                product_id, inventory_inputs.stock, inventory_inputs.unit_cost
            )
            print(f"[+] Unit cost para movimiento (ponderado desde movimientos): {movement_unit_cost}")

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
                "message": "Ajuste de inventario registrado correctamente.",
                "inventory_id": inventory.id,
                "lot_id": lot.id,
                "lot_item_id": lot_item.id,
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
    
    def weighted_unit_cost_after_purchase(self, product_id, incoming_qty, incoming_unit_cost):
        """
        Costo medio unitario después de una entrada de mercadería, usando saldo y costo
        actuales derivados de ``inventories_movements`` (misma lógica que el kardex histórico).
        """
        current_qty = stock_sum_for_product(self.db, product_id)
        current_avg = average_unit_cost_for_product(self.db, product_id) if current_qty > 0 else 0
        iq = int(incoming_qty or 0)
        ic = float(incoming_unit_cost or 0)
        new_total_qty = current_qty + iq
        if iq <= 0:
            return int(round(current_avg)) if current_qty > 0 else 0
        if new_total_qty <= 0:
            return int(round(ic))
        new_avg = (current_qty * float(current_avg) + iq * ic) / float(new_total_qty)
        return int(round(new_avg))

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
                # Usar el inventario existente: alinear cabecera con el formulario (antes no se
                # actualizaba ``location_id`` y quedaba la ubicación antigua al agregar un lote).
                inventory_id = existing_inventory.id
                existing_inventory.location_id = inventory_inputs.location_id
                existing_inventory.minimum_stock = inventory_inputs.minimum_stock
                existing_inventory.maximum_stock = inventory_inputs.maximum_stock
                existing_inventory.last_update = datetime.now()
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
                public_sale_price=inventory_inputs.public_sale_price,
                private_sale_price=inventory_inputs.private_sale_price,
                added_date=datetime.now(),
                updated_date=datetime.now()
            )
            self.db.add(new_lot_item)

            # Confirmar transacción
            self.db.commit()
            self.db.refresh(new_lot_item)

            movement_unit_cost = self.weighted_unit_cost_after_purchase(
                inventory_inputs.product_id, inventory_inputs.stock, inventory_inputs.unit_cost
            )
            print(f"[+] Unit cost para movimiento (ponderado desde movimientos): {movement_unit_cost}")

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

            movements = (
                self.db.query(InventoryMovementModel)
                .filter(InventoryMovementModel.inventory_id == inventory.id)
                .all()
            )
            lot_item_ids = {m.lot_item_id for m in movements if m.lot_item_id is not None}
            for movement in movements:
                self.db.delete(movement)
            self.db.flush()

            audits = self.db.query(InventoryAuditModel).filter_by(inventory_id=inventory.id).all()
            for audit in audits:
                self.db.delete(audit)

            for lid in lot_item_ids:
                if (
                    self.db.query(InventoryMovementModel)
                    .filter(InventoryMovementModel.lot_item_id == lid)
                    .count()
                    > 0
                ):
                    continue
                lot_item = self.db.query(LotItemModel).filter_by(id=lid).first()
                if lot_item:
                    lot_id = lot_item.lot_id
                    self.db.delete(lot_item)
                    self.db.flush()
                    if lot_id and not self.db.query(LotItemModel).filter_by(lot_id=lot_id).first():
                        lot = self.db.query(LotModel).filter_by(id=lot_id).first()
                        if lot:
                            self.db.delete(lot)

            # Eliminar inventario
            self.db.delete(inventory)

            # Confirmar
            self.db.commit()

            return {"status": "success", "message": "Inventario y relaciones eliminadas correctamente."}

        except Exception as e:
            self.db.rollback()
            return {"status": "error", "message": str(e)}

    def get_movements_by_product_id(self, product_id: int):
        """
        Todos los registros de ``inventories_movements`` cuyo ``inventory_id`` pertenece
        a un inventario del ``product_id`` indicado.
        """
        try:
            if not self.db.query(ProductModel.id).filter(ProductModel.id == product_id).first():
                return {"status": "error", "message": "Producto no encontrado."}

            rows = (
                self.db.query(
                    InventoryMovementModel.id,
                    InventoryMovementModel.inventory_id,
                    InventoryMovementModel.lot_item_id,
                    InventoryMovementModel.movement_type_id,
                    InventoryMovementModel.quantity,
                    InventoryMovementModel.unit_cost,
                    InventoryMovementModel.reason,
                    InventoryMovementModel.added_date,
                    MovementTypeModel.movement_type.label("movement_type"),
                )
                .join(InventoryModel, InventoryModel.id == InventoryMovementModel.inventory_id)
                .outerjoin(
                    MovementTypeModel,
                    MovementTypeModel.id == InventoryMovementModel.movement_type_id,
                )
                .filter(InventoryModel.product_id == product_id)
                .order_by(
                    InventoryMovementModel.added_date.desc(),
                    InventoryMovementModel.id.desc(),
                )
                .all()
            )

            return [
                {
                    "id": row.id,
                    "inventory_id": row.inventory_id,
                    "lot_item_id": row.lot_item_id,
                    "movement_type_id": row.movement_type_id,
                    "movement_type": row.movement_type,
                    "quantity": int(row.quantity) if row.quantity is not None else 0,
                    "unit_cost": int(row.unit_cost) if row.unit_cost is not None else 0,
                    "reason": row.reason,
                    "added_date": row.added_date.strftime("%Y-%m-%d %H:%M:%S")
                    if row.added_date
                    else None,
                }
                for row in rows
            ]
        except Exception as e:
            return {"status": "error", "message": str(e)}

    def delete_movement_by_id(self, movement_id: int, product_id: int):
        """
        Elimina una fila de ``inventories_movements`` si su inventario es del ``product_id``.
        No recalcula costos agregados ni lotes; solo borra el registro del movimiento.

        No permite borrar si existe una fila en ``sales_products`` que referencia el movimiento.
        """
        try:
            if not self.db.query(ProductModel.id).filter(ProductModel.id == product_id).first():
                return {"status": "error", "message": "Producto no encontrado."}

            mov = (
                self.db.query(InventoryMovementModel)
                .filter(InventoryMovementModel.id == movement_id)
                .first()
            )
            if not mov:
                return {"status": "error", "message": "Movimiento no encontrado."}

            inv = (
                self.db.query(InventoryModel)
                .filter(InventoryModel.id == mov.inventory_id)
                .first()
            )
            if not inv or int(inv.product_id) != int(product_id):
                return {"status": "error", "message": "El movimiento no corresponde a este producto."}

            linked = (
                self.db.query(SaleProductModel)
                .filter(SaleProductModel.inventory_movement_id == movement_id)
                .first()
            )
            if linked:
                return {
                    "status": "error",
                    "message": "No se puede eliminar: el movimiento está vinculado a una venta.",
                }

            self.db.delete(mov)
            self.db.commit()
            return {"status": "success", "message": "Movimiento eliminado correctamente."}
        except Exception as e:
            self.db.rollback()
            return {"status": "error", "message": str(e)}
