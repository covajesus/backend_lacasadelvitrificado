import re
from datetime import datetime
from decimal import Decimal
from sqlalchemy import func

from app.backend.classes.sale_class import SaleClass, _inventory_movement_added_at
from app.backend.classes.inventory_stock import (
    stock_sum_for_product,
    sale_acceptance_unit_cost_from_movements,
)
from app.backend.db.models import (
    SampleRequestModel,
    SampleRequestItemModel,
    ProductModel,
    UnitFeatureModel,
    UnitMeasureModel,
    CustomerModel,
    SaleModel,
    SaleProductModel,
    InventoryModel,
    InventoryMovementModel,
)

SAMPLE_REASON_PREFIX = "Muestra"
SAMPLE_SALE_STATUS_ID = 4


def parse_sample_size(value) -> Decimal:
    if value is None:
        return Decimal("0")
    normalized = str(value).strip().replace(",", ".")
    match = re.search(r"[\d.]+", normalized)
    if not match:
        return Decimal("0")
    try:
        return Decimal(match.group())
    except Exception:
        return Decimal("0")


class SampleClass:
    def __init__(self, db):
        self.db = db

    def _get_product_sample_info(self, product_id: int):
        row = (
            self.db.query(
                ProductModel.id,
                ProductModel.product,
                func.max(UnitFeatureModel.sample_size).label("sample_size"),
                UnitMeasureModel.unit_measure,
            )
            .outerjoin(UnitFeatureModel, UnitFeatureModel.product_id == ProductModel.id)
            .outerjoin(UnitMeasureModel, UnitMeasureModel.id == ProductModel.unit_measure_id)
            .filter(ProductModel.id == product_id)
            .group_by(ProductModel.id, ProductModel.product, UnitMeasureModel.unit_measure)
            .first()
        )
        if not row:
            return None
        sample_size_label = (row.sample_size or "").strip()
        if not sample_size_label:
            return None
        return {
            "product_id": row.id,
            "product_name": row.product,
            "sample_size_label": sample_size_label,
            "sample_size": parse_sample_size(sample_size_label),
            "unit_measure": row.unit_measure or "",
        }

    def get_products_with_samples(self):
        try:
            rows = (
                self.db.query(
                    ProductModel.id,
                    ProductModel.product,
                    func.max(UnitFeatureModel.sample_size).label("sample_size"),
                    UnitMeasureModel.unit_measure,
                )
                .outerjoin(UnitFeatureModel, UnitFeatureModel.product_id == ProductModel.id)
                .outerjoin(UnitMeasureModel, UnitMeasureModel.id == ProductModel.unit_measure_id)
                .group_by(ProductModel.id, ProductModel.product, UnitMeasureModel.unit_measure)
                .order_by(ProductModel.product)
                .all()
            )

            data = []
            for row in rows:
                sample_size_label = (row.sample_size or "").strip()
                if not sample_size_label:
                    continue
                sample_size = parse_sample_size(sample_size_label)
                data.append(
                    {
                        "id": row.id,
                        "product": row.product,
                        "sample_size": sample_size_label,
                        "sample_size_value": float(sample_size) if sample_size > 0 else 0,
                        "unit_measure": row.unit_measure or "",
                    }
                )

            return {"data": data}
        except Exception as e:
            return {"status": "error", "message": str(e)}

    def get_sample_product(self, product_id: int):
        try:
            info = self._get_product_sample_info(product_id)
            if not info:
                return {"status": "error", "message": "Producto sin muestra configurada"}

            return {
                "id": info["product_id"],
                "product": info["product_name"],
                "sample_size": info["sample_size_label"],
                "sample_size_value": float(info["sample_size"]),
                "unit_measure": info["unit_measure"],
            }
        except Exception as e:
            return {"status": "error", "message": str(e)}

    def _serialize_item(self, item):
        return {
            "id": item.id,
            "product_id": item.product_id,
            "product_name": item.product_name,
            "sample_quantity": item.sample_quantity,
            "sample_size": float(item.sample_size) if item.sample_size is not None else 0,
            "sample_size_label": item.sample_size_label,
            "total_amount": float(item.total_amount) if item.total_amount is not None else 0,
            "unit_measure": item.unit_measure or "",
        }

    def _items_quantity_summary(self, sample_request_id):
        items = (
            self.db.query(SampleRequestItemModel)
            .filter(SampleRequestItemModel.sample_request_id == sample_request_id)
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
            amount = float(item.total_amount or 0)
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
            "items_count": summary.get("items_count", 0),
            "total_quantity": summary.get("total_quantity", 0),
            "quantity_label": summary.get("quantity_label", "—"),
            "added_date": request.added_date.strftime("%Y-%m-%d %H:%M:%S") if request.added_date else None,
            "updated_date": request.updated_date.strftime("%Y-%m-%d %H:%M:%S") if request.updated_date else None,
        }

    def _sample_delivery_address(self, sample_request_id, customer_name, customer_rut):
        return (
            f"[MUESTRA #{sample_request_id}] {customer_name} · RUT {customer_rut} · "
            f"Sin cobro · Descuento inventario automático"
        )

    def _validate_sample_stock(self, items):
        for item in items:
            base_units = int(Decimal(item.total_amount or 0))
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
        """Revierte salidas de inventario de un pedido de muestra (sin commit)."""
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
                    reason=f"Reversa {SAMPLE_REASON_PREFIX}|sale_id={sale_id}",
                    added_date=_inventory_movement_added_at(),
                )
            )
            sale_helper._reverse_fifo_lot_consumptions(sale_id, sales_product.product_id)

        self.db.query(SaleProductModel).filter(SaleProductModel.sale_id == sale_id).delete()
        self.db.flush()

    def _deduct_sample_lines_on_sale(self, sale_id, sample_request, items):
        """Descuenta inventario y crea líneas en sales_products (precio 0)."""
        sale_helper = SaleClass(self.db)

        for item in items:
            effective_qty = int(Decimal(item.total_amount or 0))
            if effective_qty <= 0:
                continue

            movement_unit_cost = sale_acceptance_unit_cost_from_movements(self.db, item.product_id)
            main_movement, exit_error = sale_helper._create_consolidated_sale_inventory_exit(
                sale_id,
                item.product_id,
                effective_qty,
                movement_unit_cost,
                reason_prefix=SAMPLE_REASON_PREFIX,
            )
            if exit_error:
                raise ValueError(exit_error)

            inventory = (
                self.db.query(InventoryModel)
                .filter(InventoryModel.id == main_movement.inventory_id)
                .first()
            )

            self.db.add(
                SaleProductModel(
                    sale_id=sale_id,
                    product_id=item.product_id,
                    inventory_movement_id=main_movement.id,
                    inventory_id=inventory.id if inventory else None,
                    lot_item_id=main_movement.lot_item_id,
                    quantity=int(item.sample_quantity or 0),
                    price=0,
                )
            )

        self.db.flush()

    def _create_or_refresh_sample_sale(self, sample_request, items):
        """
        Crea pedido a $0, descuenta inventario con motivo Muestra y vincula sale_id.
        Si ya existía pedido, revierte inventario y regenera líneas.
        """
        if not sample_request.customer_id:
            raise ValueError("Cliente inválido para generar el pedido de muestra.")

        now = datetime.now()
        delivery = self._sample_delivery_address(
            sample_request.id,
            sample_request.customer_name,
            sample_request.customer_rut,
        )

        if sample_request.sale_id:
            sale = (
                self.db.query(SaleModel)
                .filter(SaleModel.id == sample_request.sale_id)
                .first()
            )
            if sale:
                self._reverse_sale_inventory(sale.id)
                self._validate_sample_stock(items)
                sale.customer_id = sample_request.customer_id
                sale.delivery_address = delivery
                sale.subtotal = 0
                sale.tax = 0
                sale.shipping_cost = 0
                sale.total = 0
                sale.status_id = SAMPLE_SALE_STATUS_ID
                sale.updated_date = now
                self._deduct_sample_lines_on_sale(sale.id, sample_request, items)
                return sale.id

        self._validate_sample_stock(items)

        new_sale = SaleModel(
            customer_id=sample_request.customer_id,
            shipping_method_id=1,
            dte_type_id=2,
            dte_status_id=2,
            status_id=SAMPLE_SALE_STATUS_ID,
            subtotal=0,
            tax=0,
            shipping_cost=0,
            total=0,
            payment_support=None,
            delivery_address=delivery,
            added_date=now,
            updated_date=now,
        )
        self.db.add(new_sale)
        self.db.flush()

        self._deduct_sample_lines_on_sale(new_sale.id, sample_request, items)
        sample_request.sale_id = new_sale.id
        return new_sale.id

    def get_all(self, page=0, items_per_page=10, rut=None, customer_name=None, rol_id=None, user_rut=None):
        try:
            query = self.db.query(SampleRequestModel).order_by(SampleRequestModel.added_date.desc())

            if rut and rut.strip():
                query = query.filter(SampleRequestModel.customer_rut == rut.strip())

            if customer_name and customer_name.strip():
                query = query.filter(SampleRequestModel.customer_name.ilike(f"%{customer_name.strip()}%"))

            if rol_id not in (1, 2, 6) and user_rut:
                query = query.filter(SampleRequestModel.customer_rut == str(user_rut).strip())

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

    def get(self, sample_id):
        try:
            request = self.db.query(SampleRequestModel).filter(SampleRequestModel.id == sample_id).first()
            if not request:
                return {"status": "error", "message": "Sample request not found"}

            items = (
                self.db.query(SampleRequestItemModel)
                .filter(SampleRequestItemModel.sample_request_id == sample_id)
                .order_by(SampleRequestItemModel.id)
                .all()
            )

            payload = self._serialize_request(request, self._items_quantity_summary(sample_id))
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

    def _build_items(self, sample_request_id, items_input):
        created_items = []
        for item_input in items_input:
            if item_input.sample_quantity <= 0:
                continue

            product_info = self._get_product_sample_info(item_input.product_id)
            if not product_info:
                raise ValueError(f"El producto {item_input.product_id} no tiene tamaño de muestra configurado.")

            total_amount = product_info["sample_size"] * Decimal(item_input.sample_quantity)
            now = datetime.now()
            created_items.append(
                SampleRequestItemModel(
                    sample_request_id=sample_request_id,
                    product_id=product_info["product_id"],
                    product_name=product_info["product_name"],
                    sample_quantity=item_input.sample_quantity,
                    sample_size=product_info["sample_size"],
                    sample_size_label=product_info["sample_size_label"],
                    total_amount=total_amount,
                    unit_measure=product_info["unit_measure"],
                    added_date=now,
                    updated_date=now,
                )
            )
        return created_items

    def store(self, sample_inputs):
        try:
            if not sample_inputs.items:
                return {"status": "error", "message": "Debe agregar al menos un producto."}

            now = datetime.now()
            customer_id = self._resolve_customer_id(
                sample_inputs.customer_rut,
                sample_inputs.customer_id,
            )

            new_request = SampleRequestModel(
                customer_id=customer_id,
                customer_rut=sample_inputs.customer_rut.strip(),
                customer_name=sample_inputs.customer_name.strip(),
                notes=(sample_inputs.notes or "").strip() or None,
                added_date=now,
                updated_date=now,
            )
            self.db.add(new_request)
            self.db.flush()

            items = self._build_items(new_request.id, sample_inputs.items)
            if not items:
                self.db.rollback()
                return {"status": "error", "message": "Debe agregar al menos un producto con cantidad válida."}

            self.db.add_all(items)
            self.db.flush()

            self._create_or_refresh_sample_sale(new_request, items)
            self.db.commit()
            return "success"
        except ValueError as e:
            self.db.rollback()
            return {"status": "error", "message": str(e)}
        except Exception as e:
            self.db.rollback()
            return {"status": "error", "message": str(e)}

    def update(self, sample_id, sample_inputs):
        try:
            request = self.db.query(SampleRequestModel).filter(SampleRequestModel.id == sample_id).first()
            if not request:
                return {"status": "error", "message": "Sample request not found"}

            if not sample_inputs.items:
                return {"status": "error", "message": "Debe agregar al menos un producto."}

            customer_id = self._resolve_customer_id(
                sample_inputs.customer_rut,
                sample_inputs.customer_id,
            )

            request.customer_id = customer_id
            request.customer_rut = sample_inputs.customer_rut.strip()
            request.customer_name = sample_inputs.customer_name.strip()
            request.notes = (sample_inputs.notes or "").strip() or None
            request.updated_date = datetime.now()

            self.db.query(SampleRequestItemModel).filter(
                SampleRequestItemModel.sample_request_id == sample_id
            ).delete()

            items = self._build_items(sample_id, sample_inputs.items)
            if not items:
                self.db.rollback()
                return {"status": "error", "message": "Debe agregar al menos un producto con cantidad válida."}

            self.db.add_all(items)
            self.db.flush()

            self._create_or_refresh_sample_sale(request, items)
            self.db.commit()
            return "success"
        except ValueError as e:
            self.db.rollback()
            return {"status": "error", "message": str(e)}
        except Exception as e:
            self.db.rollback()
            return {"status": "error", "message": str(e)}

    def delete(self, sample_id):
        try:
            request = self.db.query(SampleRequestModel).filter(SampleRequestModel.id == sample_id).first()
            if not request:
                return {"status": "error", "message": "Sample request not found"}

            if request.sale_id:
                self._reverse_sale_inventory(request.sale_id)
                sale = self.db.query(SaleModel).filter(SaleModel.id == request.sale_id).first()
                if sale:
                    sale.status_id = 3
                    sale.updated_date = datetime.now()

            self.db.query(SampleRequestItemModel).filter(
                SampleRequestItemModel.sample_request_id == sample_id
            ).delete()
            self.db.delete(request)
            self.db.commit()
            return "success"
        except Exception as e:
            self.db.rollback()
            return {"status": "error", "message": str(e)}
