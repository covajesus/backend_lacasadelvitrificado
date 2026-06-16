from datetime import datetime
from decimal import Decimal, ROUND_HALF_UP

from sqlalchemy import func

from app.backend.classes.inventory_stock import sale_acceptance_unit_cost_from_movements
from app.backend.core.constants import RequestReasonPrefix, TaxPolicy
from app.backend.core.exceptions import ValidationError
from app.backend.db.models import (
    UnitSaleRequestModel,
    UnitSaleRequestItemModel,
    ProductModel,
    UnitMeasureModel,
    UnitFeatureModel,
    LotItemModel,
    CustomerModel,
    CustomerProductDiscountModel,
)
from app.backend.services.inventory.inventory_sale_bridge import InventorySaleBridge, SaleDeductionLine
from app.backend.core.pagination import paginate_query
from app.backend.core.role_access import apply_customer_rut_scope
from app.backend.services.requests.item_summary import summarize_items_by_unit
from app.backend.services.requests.linked_request_base import LinkedRequestService


class UnitSaleClass(LinkedRequestService):
    reason_prefix = RequestReasonPrefix.UNIT_SALE

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

    def _items_quantity_summary(self, items):
        return summarize_items_by_unit(
            items,
            quantity_resolver=lambda i: float(i.unit_quantity or 0),
        )

    def _request_items(self, unit_sale_request_id):
        return (
            self.db.query(UnitSaleRequestItemModel)
            .filter(UnitSaleRequestItemModel.unit_sale_request_id == unit_sale_request_id)
            .order_by(UnitSaleRequestItemModel.id)
            .all()
        )

    def _serialize_request(self, request, items=None, items_summary=None):
        items = items if items is not None else self._request_items(request.id)
        summary = items_summary or self._items_quantity_summary(items)
        if items:
            subtotal, tax, total = self._calculate_totals(items)
        else:
            subtotal = Decimal(str(request.subtotal or 0))
            tax = Decimal(str(request.tax or 0))
            total = Decimal(str(request.total or 0))

        return {
            "id": request.id,
            "customer_id": request.customer_id,
            "customer_rut": request.customer_rut,
            "customer_name": request.customer_name,
            "notes": request.notes or "",
            "sale_id": request.sale_id,
            "subtotal": float(subtotal),
            "tax": float(tax),
            "total": float(total),
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
        tax = (subtotal * TaxPolicy.UNIT_SALE_RATE).quantize(Decimal("1"), rounding=ROUND_HALF_UP)
        total = subtotal + tax
        return subtotal, tax, total

    def _inventory_units(self, unit_quantity) -> int:
        return InventorySaleBridge.inventory_units(unit_quantity)

    def _validate_stock(self, items):
        self._inventory.validate_stock(
            items,
            base_units_resolver=lambda i: self._inventory_units(i.unit_quantity),
        )

    def _to_deduction_lines(self, items):
        lines = []
        for item in items:
            effective_qty = self._inventory_units(item.unit_quantity)
            if effective_qty <= 0:
                continue
            line_price = int(
                Decimal(str(item.line_total or 0)).quantize(Decimal("1"), rounding=ROUND_HALF_UP)
            )
            lines.append(
                SaleDeductionLine(
                    product_id=item.product_id,
                    inventory_base_units=effective_qty,
                    line_price=line_price,
                )
            )
        return lines

    def _create_or_refresh_sale(self, unit_sale_request, items):
        if not unit_sale_request.customer_id:
            raise ValueError("Cliente inválido para generar el pedido de venta unitaria.")

        subtotal, tax, total = self._calculate_totals(items)
        delivery = self._delivery_address(
            unit_sale_request.id,
            unit_sale_request.customer_name,
            unit_sale_request.customer_rut,
        )
        self._validate_stock(items)
        return self._sale_linkage.create_or_refresh(
            unit_sale_request,
            customer_id=unit_sale_request.customer_id,
            delivery_address=delivery,
            subtotal=subtotal,
            tax=tax,
            total=total,
            deduction_lines=self._to_deduction_lines(items),
            persist_totals=lambda req, s, t, tot: self._persist_request_totals(req, s, t, tot),
        )

    @staticmethod
    def _persist_request_totals(request, subtotal, tax, total):
        request.subtotal = subtotal
        request.tax = tax
        request.total = total

    def get_all(self, page=0, items_per_page=10, rut=None, customer_name=None, rol_id=None, user_rut=None):
        return self.safe(lambda: self._get_all(page, items_per_page, rut, customer_name, rol_id, user_rut))

    def _get_all(self, page, items_per_page, rut, customer_name, rol_id, user_rut):
        query = self.db.query(UnitSaleRequestModel).order_by(UnitSaleRequestModel.added_date.desc())
        if rut and rut.strip():
            query = query.filter(UnitSaleRequestModel.customer_rut == rut.strip())
        if customer_name and customer_name.strip():
            query = query.filter(UnitSaleRequestModel.customer_name.ilike(f"%{customer_name.strip()}%"))
        query = apply_customer_rut_scope(
            query, UnitSaleRequestModel, rol_id=rol_id, user_rut=user_rut
        )

        def serialize_row(row):
            items = self._request_items(row.id)
            return self._serialize_request(row, items, self._items_quantity_summary(items))

        if page > 0:
            return paginate_query(
                query, page=page, items_per_page=items_per_page, serialize_row=serialize_row
            )
        return [serialize_row(row) for row in query.all()]

    def get(self, unit_sale_id):
        try:
            request = (
                self.db.query(UnitSaleRequestModel)
                .filter(UnitSaleRequestModel.id == unit_sale_id)
                .first()
            )
            if not request:
                return {"status": "error", "message": "Unit sale request not found"}

            items = self._request_items(unit_sale_id)

            payload = self._serialize_request(
                request,
                items,
                self._items_quantity_summary(items),
            )
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

            unit_price = Decimal(str(item_input.unit_price))
            if unit_price <= 0:
                raise ValueError(
                    f"Debe indicar un precio unitario válido para {product_info['product_name']}."
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
        except (ValueError, ValidationError) as e:
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
        except (ValueError, ValidationError) as e:
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

            sale_id = request.sale_id
            if sale_id:
                block = self._inventory.sale_delete_block_reason(sale_id)
                if block:
                    return {"status": "error", "message": block}
                self._inventory.reverse_sale_inventory(sale_id)

            self.db.query(UnitSaleRequestItemModel).filter(
                UnitSaleRequestItemModel.unit_sale_request_id == unit_sale_id
            ).delete()
            self.db.delete(request)
            self.db.flush()

            if sale_id:
                self._inventory.unlink_sale(sale_id, mode="hard_delete", check_folio=False)

            self.db.commit()
            return "success"
        except Exception as e:
            self.db.rollback()
            return {"status": "error", "message": str(e)}
