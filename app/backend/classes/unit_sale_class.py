from datetime import datetime
from decimal import Decimal, ROUND_HALF_UP

from sqlalchemy import func

from app.backend.classes.sale_class import SaleClass, _inventory_movement_added_at
from app.backend.classes.inventory_stock import (
    stock_sum_for_product,
    sale_acceptance_unit_cost_from_movements,
)
from app.backend.db.models import (
    UnitSaleRequestModel,
    UnitSaleRequestItemModel,
    ProductModel,
    UnitMeasureModel,
    UnitFeatureModel,
    LotItemModel,
    CustomerModel,
    CustomerProductDiscountModel,
    SaleModel,
    SaleProductModel,
    InventoryModel,
    InventoryMovementModel,
)

UNIT_SALE_REASON_PREFIX = "Venta unitaria"
UNIT_SALE_SALE_STATUS_ID = 4
TAX_RATE = Decimal("0.19")


class UnitSaleClass:
    def __init__(self, db):
        self.db = db

    def _get_product_pricing(self, product_id: int, customer_id=None):
        row = (
            self.db.query(
                ProductModel.id,
                ProductModel.product,
                UnitMeasureModel.unit_measure,
                UnitFeatureModel.quantity_per_package,
                func.max(LotItemModel.public_sale_price).label("public_sale_price"),
            )
            .outerjoin(UnitMeasureModel, UnitMeasureModel.id == ProductModel.unit_measure_id)
            .outerjoin(UnitFeatureModel, UnitFeatureModel.product_id == ProductModel.id)
            .outerjoin(LotItemModel, LotItemModel.product_id == ProductModel.id)
            .filter(ProductModel.id == product_id)
            .group_by(
                ProductModel.id,
                ProductModel.product,
                UnitMeasureModel.unit_measure,
                UnitFeatureModel.quantity_per_package,
            )
            .first()
        )
        if not row:
            return None

        qpp = Decimal(str(row.quantity_per_package or 1))
        if qpp <= 0:
            qpp = Decimal("1")

        package_price = Decimal(str(row.public_sale_price or 0))
        discount_pct = Decimal("0")
        if customer_id:
            discount_record = (
                self.db.query(CustomerProductDiscountModel)
                .filter(CustomerProductDiscountModel.customer_id == customer_id)
                .filter(CustomerProductDiscountModel.product_id == product_id)
                .first()
            )
            if discount_record and discount_record.discount_percentage:
                discount_pct = Decimal(str(discount_record.discount_percentage))

        if discount_pct > 0:
            package_price = (
                package_price * (Decimal("100") - discount_pct) / Decimal("100")
            ).quantize(Decimal("1"), rounding=ROUND_HALF_UP)

        unit_price = (package_price / qpp).quantize(Decimal("1"), rounding=ROUND_HALF_UP)

        return {
            "product_id": row.id,
            "product_name": row.product,
            "unit_measure": row.unit_measure or "",
            "quantity_per_package": float(qpp),
            "package_price": float(package_price),
            "unit_price": float(unit_price),
        }

    def _get_product_info(self, product_id: int, customer_id=None):
        return self._get_product_pricing(product_id, customer_id)

    def get_products(self):
        try:
            rows = (
                self.db.query(
                    ProductModel.id,
                    ProductModel.product,
                    UnitMeasureModel.unit_measure,
                )
                .outerjoin(UnitMeasureModel, UnitMeasureModel.id == ProductModel.unit_measure_id)
                .order_by(ProductModel.product)
                .all()
            )
            data = [
                {
                    "id": row.id,
                    "product": row.product,
                    "unit_measure": row.unit_measure or "",
                }
                for row in rows
            ]
            return {"data": data}
        except Exception as e:
            return {"status": "error", "message": str(e)}

    def get_product(self, product_id: int, customer_id=None):
        try:
            info = self._get_product_pricing(product_id, customer_id)
            if not info:
                return {"status": "error", "message": "Producto no encontrado"}
            return {
                "id": info["product_id"],
                "product": info["product_name"],
                "unit_measure": info["unit_measure"],
                "quantity_per_package": info["quantity_per_package"],
                "package_price": info["package_price"],
                "unit_price": info["unit_price"],
            }
        except Exception as e:
            return {"status": "error", "message": str(e)}

    def _inventory_units(self, unit_quantity) -> int:
        d = Decimal(str(unit_quantity))
        if d <= 0:
            return 0
        return int(d.quantize(Decimal("1"), rounding=ROUND_HALF_UP))

    def _serialize_item(self, item):
        return {
            "id": item.id,
            "product_id": item.product_id,
            "product_name": item.product_name,
            "unit_quantity": float(item.unit_quantity) if item.unit_quantity is not None else 0,
            "unit_price": float(item.unit_price) if item.unit_price is not None else 0,
            "line_total": float(item.line_total) if item.line_total is not None else 0,
            "unit_measure": item.unit_measure or "",
        }

    def _items_quantity_summary(self, unit_sale_request_id):
        items = (
            self.db.query(UnitSaleRequestItemModel)
            .filter(UnitSaleRequestItemModel.unit_sale_request_id == unit_sale_request_id)
            .all()
        )
        if not items:
            return {
                "items_count": 0,
                "total_quantity": 0,
                "quantity_label": "—",
            }

        by_unit = {}
        for item in items:
            unit = (item.unit_measure or "").strip() or "u."
            amount = float(item.unit_quantity or 0)
            by_unit[unit] = by_unit.get(unit, 0) + amount

        parts = []
        for unit, total in by_unit.items():
            if total == int(total):
                parts.append(f"{int(total)} {unit}")
            else:
                parts.append(f"{total:g} {unit}")

        return {
            "items_count": len(items),
            "total_quantity": sum(by_unit.values()),
            "quantity_label": ", ".join(parts),
        }

    def _serialize_request(self, request, items_summary=None):
        summary = items_summary or {}
        return {
            "id": request.id,
            "customer_id": request.customer_id,
            "customer_rut": request.customer_rut,
            "customer_name": request.customer_name,
            "notes": request.notes or "",
            "sale_id": request.sale_id,
            "subtotal": float(request.subtotal or 0),
            "tax": float(request.tax or 0),
            "total": float(request.total or 0),
            "items_count": summary.get("items_count", 0),
            "quantity_label": summary.get("quantity_label", "—"),
            "added_date": request.added_date.strftime("%Y-%m-%d %H:%M:%S") if request.added_date else None,
            "updated_date": request.updated_date.strftime("%Y-%m-%d %H:%M:%S") if request.updated_date else None,
        }

    def _delivery_address(self, unit_sale_request_id, customer_name, customer_rut):
        return (
            f"[VENTA UNITARIA #{unit_sale_request_id}] {customer_name} · RUT {customer_rut} · "
            f"Cobro aplicado · Descuento inventario automático"
        )

    def _calculate_totals(self, items):
        subtotal = sum(Decimal(str(item.line_total or 0)) for item in items)
        tax = (subtotal * TAX_RATE).quantize(Decimal("1"), rounding=ROUND_HALF_UP)
        total = subtotal + tax
        return subtotal, tax, total

    def _validate_stock(self, items):
        for item in items:
            base_units = self._inventory_units(item.unit_quantity)
            if base_units <= 0:
                continue
            available = stock_sum_for_product(self.db, item.product_id)
            if available < base_units:
                unit = item.unit_measure or "u."
                raise ValueError(
                    f"Stock insuficiente para {item.product_name}. "
                    f"Disponible: {available} {unit}, solicitado: {base_units} {unit}."
                )

    def _reverse_sale_inventory(self, sale_id):
        sale_helper = SaleClass(self.db)
        sales_products = (
            self.db.query(SaleProductModel)
            .filter(SaleProductModel.sale_id == sale_id)
            .all()
        )
        for sales_product in sales_products:
            if not sales_product.inventory_movement_id:
                continue
            inventory_movement = (
                self.db.query(InventoryMovementModel)
                .filter(InventoryMovementModel.id == sales_product.inventory_movement_id)
                .first()
            )
            if not inventory_movement:
                continue

            reverse_quantity = sale_helper._sale_movement_reverse_base_units(
                sale_id, sales_product, inventory_movement
            )
            if reverse_quantity <= 0:
                continue

            return_uc = sale_acceptance_unit_cost_from_movements(self.db, sales_product.product_id)
            self.db.add(
                InventoryMovementModel(
                    inventory_id=inventory_movement.inventory_id,
                    lot_item_id=inventory_movement.lot_item_id,
                    movement_type_id=1,
                    quantity=reverse_quantity,
                    unit_cost=return_uc,
                    reason=f"Reversa {UNIT_SALE_REASON_PREFIX}|sale_id={sale_id}",
                    added_date=_inventory_movement_added_at(),
                )
            )
            sale_helper._reverse_fifo_lot_consumptions(sale_id, sales_product.product_id)

        self.db.query(SaleProductModel).filter(SaleProductModel.sale_id == sale_id).delete()
        self.db.flush()

    def _deduct_lines_on_sale(self, sale_id, items):
        sale_helper = SaleClass(self.db)

        for item in items:
            effective_qty = self._inventory_units(item.unit_quantity)
            if effective_qty <= 0:
                continue

            movement_unit_cost = sale_acceptance_unit_cost_from_movements(self.db, item.product_id)
            main_movement, exit_error = sale_helper._create_consolidated_sale_inventory_exit(
                sale_id,
                item.product_id,
                effective_qty,
                movement_unit_cost,
                reason_prefix=UNIT_SALE_REASON_PREFIX,
            )
            if exit_error:
                raise ValueError(exit_error)

            inventory = (
                self.db.query(InventoryModel)
                .filter(InventoryModel.id == main_movement.inventory_id)
                .first()
            )

            line_price = int(Decimal(str(item.line_total or 0)).quantize(Decimal("1"), rounding=ROUND_HALF_UP))
            self.db.add(
                SaleProductModel(
                    sale_id=sale_id,
                    product_id=item.product_id,
                    inventory_movement_id=main_movement.id,
                    inventory_id=inventory.id if inventory else None,
                    lot_item_id=main_movement.lot_item_id,
                    quantity=1,
                    price=line_price,
                )
            )

        self.db.flush()

    def _create_or_refresh_sale(self, unit_sale_request, items):
        if not unit_sale_request.customer_id:
            raise ValueError("Cliente inválido para generar el pedido de venta unitaria.")

        subtotal, tax, total = self._calculate_totals(items)
        now = datetime.now()
        delivery = self._delivery_address(
            unit_sale_request.id,
            unit_sale_request.customer_name,
            unit_sale_request.customer_rut,
        )

        unit_sale_request.subtotal = subtotal
        unit_sale_request.tax = tax
        unit_sale_request.total = total

        if unit_sale_request.sale_id:
            sale = (
                self.db.query(SaleModel)
                .filter(SaleModel.id == unit_sale_request.sale_id)
                .first()
            )
            if sale:
                self._reverse_sale_inventory(sale.id)
                self._validate_stock(items)
                sale.customer_id = unit_sale_request.customer_id
                sale.delivery_address = delivery
                sale.subtotal = int(subtotal)
                sale.tax = int(tax)
                sale.total = int(total)
                sale.status_id = UNIT_SALE_SALE_STATUS_ID
                sale.updated_date = now
                self._deduct_lines_on_sale(sale.id, items)
                return sale.id

        self._validate_stock(items)

        new_sale = SaleModel(
            customer_id=unit_sale_request.customer_id,
            shipping_method_id=1,
            dte_type_id=2,
            dte_status_id=2,
            status_id=UNIT_SALE_SALE_STATUS_ID,
            subtotal=int(subtotal),
            tax=int(tax),
            shipping_cost=0,
            total=int(total),
            payment_support=None,
            delivery_address=delivery,
            added_date=now,
            updated_date=now,
        )
        self.db.add(new_sale)
        self.db.flush()

        self._deduct_lines_on_sale(new_sale.id, items)
        unit_sale_request.sale_id = new_sale.id
        return new_sale.id

    def get_all(self, page=0, items_per_page=10, rut=None, customer_name=None, rol_id=None, user_rut=None):
        try:
            query = self.db.query(UnitSaleRequestModel).order_by(UnitSaleRequestModel.added_date.desc())

            if rut and rut.strip():
                query = query.filter(UnitSaleRequestModel.customer_rut == rut.strip())

            if customer_name and customer_name.strip():
                query = query.filter(UnitSaleRequestModel.customer_name.ilike(f"%{customer_name.strip()}%"))

            if rol_id not in (1, 2, 6) and user_rut:
                query = query.filter(UnitSaleRequestModel.customer_rut == str(user_rut).strip())

            if page > 0:
                total_items = query.count()
                total_pages = max((total_items + items_per_page - 1) // items_per_page, 1)

                if page < 1 or page > total_pages:
                    return {"status": "error", "message": "Invalid page number"}

                rows = query.offset((page - 1) * items_per_page).limit(items_per_page).all()
                if not rows:
                    return {"status": "error", "message": "No data found"}

                serialized = []
                for row in rows:
                    summary = self._items_quantity_summary(row.id)
                    serialized.append(self._serialize_request(row, summary))

                return {
                    "total_items": total_items,
                    "total_pages": total_pages,
                    "current_page": page,
                    "items_per_page": items_per_page,
                    "data": serialized,
                }

            rows = query.all()
            return [
                self._serialize_request(row, self._items_quantity_summary(row.id))
                for row in rows
            ]
        except Exception as e:
            return {"status": "error", "message": str(e)}

    def get(self, unit_sale_id):
        try:
            request = (
                self.db.query(UnitSaleRequestModel)
                .filter(UnitSaleRequestModel.id == unit_sale_id)
                .first()
            )
            if not request:
                return {"status": "error", "message": "Unit sale request not found"}

            items = (
                self.db.query(UnitSaleRequestItemModel)
                .filter(UnitSaleRequestItemModel.unit_sale_request_id == unit_sale_id)
                .order_by(UnitSaleRequestItemModel.id)
                .all()
            )

            payload = self._serialize_request(request, self._items_quantity_summary(unit_sale_id))
            payload["items"] = [self._serialize_item(item) for item in items]
            return payload
        except Exception as e:
            return {"status": "error", "message": str(e)}

    def _resolve_customer_id(self, customer_rut, customer_id=None):
        if customer_id:
            return customer_id
        if not customer_rut:
            return None
        customer = (
            self.db.query(CustomerModel)
            .filter(CustomerModel.identification_number == customer_rut.strip())
            .first()
        )
        return customer.id if customer else None

    def _build_items(self, unit_sale_request_id, items_input, customer_id=None):
        created_items = []
        for item_input in items_input:
            qty = Decimal(str(item_input.unit_quantity))
            if qty <= 0:
                continue

            product_info = self._get_product_pricing(item_input.product_id, customer_id)
            if not product_info:
                raise ValueError(f"El producto {item_input.product_id} no existe.")

            unit_price = Decimal(str(product_info["unit_price"]))
            if unit_price <= 0:
                raise ValueError(
                    f"El producto {product_info['product_name']} no tiene precio de venta configurado."
                )

            line_total = (qty * unit_price).quantize(Decimal("1"), rounding=ROUND_HALF_UP)
            now = datetime.now()
            created_items.append(
                UnitSaleRequestItemModel(
                    unit_sale_request_id=unit_sale_request_id,
                    product_id=product_info["product_id"],
                    product_name=product_info["product_name"],
                    unit_quantity=qty,
                    unit_price=unit_price,
                    line_total=line_total,
                    unit_measure=product_info["unit_measure"],
                    added_date=now,
                    updated_date=now,
                )
            )
        return created_items

    def store(self, unit_sale_inputs):
        try:
            if not unit_sale_inputs.items:
                return {"status": "error", "message": "Debe agregar al menos un producto."}

            now = datetime.now()
            customer_id = self._resolve_customer_id(
                unit_sale_inputs.customer_rut,
                unit_sale_inputs.customer_id,
            )

            new_request = UnitSaleRequestModel(
                customer_id=customer_id,
                customer_rut=unit_sale_inputs.customer_rut.strip(),
                customer_name=unit_sale_inputs.customer_name.strip(),
                notes=(unit_sale_inputs.notes or "").strip() or None,
                added_date=now,
                updated_date=now,
            )
            self.db.add(new_request)
            self.db.flush()

            items = self._build_items(new_request.id, unit_sale_inputs.items, customer_id)
            if not items:
                self.db.rollback()
                return {"status": "error", "message": "Debe agregar al menos un producto con cantidad válida."}

            self.db.add_all(items)
            self.db.flush()

            self._create_or_refresh_sale(new_request, items)
            self.db.commit()
            return "success"
        except ValueError as e:
            self.db.rollback()
            return {"status": "error", "message": str(e)}
        except Exception as e:
            self.db.rollback()
            return {"status": "error", "message": str(e)}

    def update(self, unit_sale_id, unit_sale_inputs):
        try:
            request = (
                self.db.query(UnitSaleRequestModel)
                .filter(UnitSaleRequestModel.id == unit_sale_id)
                .first()
            )
            if not request:
                return {"status": "error", "message": "Unit sale request not found"}

            if not unit_sale_inputs.items:
                return {"status": "error", "message": "Debe agregar al menos un producto."}

            customer_id = self._resolve_customer_id(
                unit_sale_inputs.customer_rut,
                unit_sale_inputs.customer_id,
            )

            request.customer_id = customer_id
            request.customer_rut = unit_sale_inputs.customer_rut.strip()
            request.customer_name = unit_sale_inputs.customer_name.strip()
            request.notes = (unit_sale_inputs.notes or "").strip() or None
            request.updated_date = datetime.now()

            self.db.query(UnitSaleRequestItemModel).filter(
                UnitSaleRequestItemModel.unit_sale_request_id == unit_sale_id
            ).delete()

            items = self._build_items(unit_sale_id, unit_sale_inputs.items, customer_id)
            if not items:
                self.db.rollback()
                return {"status": "error", "message": "Debe agregar al menos un producto con cantidad válida."}

            self.db.add_all(items)
            self.db.flush()

            self._create_or_refresh_sale(request, items)
            self.db.commit()
            return "success"
        except ValueError as e:
            self.db.rollback()
            return {"status": "error", "message": str(e)}
        except Exception as e:
            self.db.rollback()
            return {"status": "error", "message": str(e)}

    def delete(self, unit_sale_id):
        try:
            request = (
                self.db.query(UnitSaleRequestModel)
                .filter(UnitSaleRequestModel.id == unit_sale_id)
                .first()
            )
            if not request:
                return {"status": "error", "message": "Unit sale request not found"}

            if request.sale_id:
                self._reverse_sale_inventory(request.sale_id)
                sale = self.db.query(SaleModel).filter(SaleModel.id == request.sale_id).first()
                if sale:
                    sale.status_id = 3
                    sale.updated_date = datetime.now()

            self.db.query(UnitSaleRequestItemModel).filter(
                UnitSaleRequestItemModel.unit_sale_request_id == unit_sale_id
            ).delete()
            self.db.delete(request)
            self.db.commit()
            return "success"
        except Exception as e:
            self.db.rollback()
            return {"status": "error", "message": str(e)}
