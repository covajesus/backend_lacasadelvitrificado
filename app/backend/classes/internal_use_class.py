from datetime import datetime
from decimal import Decimal, ROUND_HALF_UP

from sqlalchemy import func

from app.backend.classes.inventory_stock import sale_acceptance_unit_cost_from_movements
from app.backend.core.constants import RequestReasonPrefix
from app.backend.core.exceptions import ValidationError
from app.backend.db.models import (
    InternalUseRequestModel,
    InternalUseRequestItemModel,
    LotItemModel,
    ProductModel,
    UnitFeatureModel,
    UnitMeasureModel,
    CustomerModel,
    SettingModel,
)
from app.backend.services.inventory.inventory_sale_bridge import InventorySaleBridge, SaleDeductionLine
from app.backend.core.pagination import paginate_query
from app.backend.core.role_access import is_restricted_customer_role
from app.backend.services.requests.item_summary import summarize_items_by_unit
from app.backend.services.requests.linked_request_base import LinkedRequestService


class InternalUseClass(LinkedRequestService):
    reason_prefix = RequestReasonPrefix.INTERNAL_USE

    def _get_product_info(self, product_id: int):
        row = (
            self.db.query(
                ProductModel.id,
                ProductModel.product,
                UnitMeasureModel.unit_measure,
            )
            .outerjoin(UnitMeasureModel, UnitMeasureModel.id == ProductModel.unit_measure_id)
            .filter(ProductModel.id == product_id)
            .first()
        )
        if not row:
            return None

        unit_cost = sale_acceptance_unit_cost_from_movements(self.db, product_id)
        return {
            "product_id": row.id,
            "product_name": row.product,
            "unit_measure": row.unit_measure or "",
            "purchase_unit_cost": float(unit_cost or 0),
        }

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

    def get_product(self, product_id: int):
        try:
            info = self._get_product_info(product_id)
            if not info:
                return {"status": "error", "message": "Producto no encontrado"}
            return {
                "id": info["product_id"],
                "product": info["product_name"],
                "unit_measure": info["unit_measure"],
                "purchase_unit_cost": info["purchase_unit_cost"],
            }
        except Exception as e:
            return {"status": "error", "message": str(e)}

    def _inventory_units(self, unit_quantity) -> int:
        return InventorySaleBridge.inventory_units(unit_quantity)

    def _get_product_sale_unit_price(self, product_id: int) -> Decimal:
        """Precio unitario de venta al público (sin descuentos de cliente)."""
        row = (
            self.db.query(
                UnitFeatureModel.quantity_per_package,
                func.max(LotItemModel.public_sale_price).label("public_sale_price"),
            )
            .select_from(ProductModel)
            .outerjoin(UnitFeatureModel, UnitFeatureModel.product_id == ProductModel.id)
            .outerjoin(LotItemModel, LotItemModel.product_id == ProductModel.id)
            .filter(ProductModel.id == int(product_id))
            .group_by(UnitFeatureModel.quantity_per_package)
            .first()
        )
        if not row:
            return Decimal("0")

        qpp = Decimal(str(row.quantity_per_package or 1))
        if qpp <= 0:
            qpp = Decimal("1")

        package_price = Decimal(str(row.public_sale_price or 0))
        return (package_price / qpp).quantize(Decimal("1"), rounding=ROUND_HALF_UP)

    def _serialize_item(self, item, *, include_sale_analysis: bool = False):
        payload = {
            "id": item.id,
            "product_id": item.product_id,
            "product_name": item.product_name,
            "unit_quantity": float(item.unit_quantity) if item.unit_quantity is not None else 0,
            "unit_cost": float(item.unit_cost) if item.unit_cost is not None else 0,
            "line_total": float(item.line_total) if item.line_total is not None else 0,
            "unit_measure": item.unit_measure or "",
        }

        if not include_sale_analysis:
            return payload

        qty = Decimal(str(item.unit_quantity or 0))
        line_cost = Decimal(str(item.line_total or 0))
        sale_unit = self._get_product_sale_unit_price(item.product_id)
        line_sale = (qty * sale_unit).quantize(Decimal("1"), rounding=ROUND_HALF_UP)
        line_margin = line_sale - line_cost

        payload.update(
            {
                "unit_sale_price": float(sale_unit),
                "line_sale_total": float(line_sale),
                "line_margin": float(line_margin),
            }
        )
        return payload

    def _serialize_request(
        self,
        request,
        items=None,
        items_summary=None,
        *,
        include_items: bool = False,
        include_sale_analysis: bool = False,
    ):
        items = items if items is not None else self._request_items(request.id)
        summary = items_summary or self._items_quantity_summary(items)
        if items:
            subtotal, tax, total = self._calculate_totals(items)
        else:
            subtotal = Decimal(str(request.subtotal or 0))
            tax = Decimal(str(request.tax or 0))
            total = Decimal(str(request.total or 0))

        payload = {
            "id": request.id,
            "description": request.description or "",
            "notes": request.notes or "",
            "sale_id": request.sale_id,
            "subtotal": float(subtotal),
            "tax": float(tax),
            "total": float(total),
            "cost_total": float(total),
            "items_count": summary.get("items_count", 0),
            "quantity_label": summary.get("quantity_label", "—"),
            "added_date": request.added_date.strftime("%Y-%m-%d %H:%M:%S") if request.added_date else None,
            "updated_date": request.updated_date.strftime("%Y-%m-%d %H:%M:%S") if request.updated_date else None,
        }

        if include_items:
            serialized_items = [
                self._serialize_item(item, include_sale_analysis=include_sale_analysis)
                for item in items
            ]
            payload["items"] = serialized_items

            if include_sale_analysis and serialized_items:
                potential_sale_total = sum(
                    Decimal(str(row.get("line_sale_total") or 0)) for row in serialized_items
                )
                cost_total = Decimal(str(total))
                potential_margin = potential_sale_total - cost_total
                payload["potential_sale_total"] = float(potential_sale_total)
                payload["potential_margin"] = float(potential_margin)

        return payload

    def _items_quantity_summary(self, items):
        return summarize_items_by_unit(
            items,
            quantity_resolver=lambda i: float(i.unit_quantity or 0),
        )

    def _purchase_unit_cost(self, product_id) -> Decimal:
        return Decimal(str(sale_acceptance_unit_cost_from_movements(self.db, product_id) or 0))

    def _request_items(self, internal_use_request_id):
        return (
            self.db.query(InternalUseRequestItemModel)
            .filter(InternalUseRequestItemModel.internal_use_request_id == internal_use_request_id)
            .order_by(InternalUseRequestItemModel.id)
            .all()
        )

    def _delivery_address(self, internal_use_request_id, description):
        desc = (description or "").strip()
        return (
            f"[USO INTERNO #{internal_use_request_id}] {desc} · "
            f"Costo de compra · Descuento inventario automático"
        )

    def _calculate_totals(self, items):
        subtotal = sum(Decimal(str(item.line_total or 0)) for item in items)
        tax = Decimal("0")
        total = subtotal
        return subtotal, tax, total

    def _resolve_internal_customer_id(self):
        settings = self.db.query(SettingModel).first()
        if settings and settings.identification_number:
            customer = (
                self.db.query(CustomerModel)
                .filter(CustomerModel.identification_number == settings.identification_number.strip())
                .first()
            )
            if customer:
                return customer.id

        customer = self.db.query(CustomerModel).order_by(CustomerModel.id).first()
        if not customer:
            raise ValueError("No hay cliente configurado para registrar el uso interno.")
        return customer.id

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

    def _create_or_refresh_sale(self, internal_use_request, items):
        customer_id = self._resolve_internal_customer_id()
        subtotal, tax, total = self._calculate_totals(items)
        delivery = self._delivery_address(internal_use_request.id, internal_use_request.description)
        self._validate_stock(items)
        return self._sale_linkage.create_or_refresh(
            internal_use_request,
            customer_id=customer_id,
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

    def get_all(self, page=0, items_per_page=10, description=None, rol_id=None):
        return self.safe(lambda: self._get_all(page, items_per_page, description, rol_id))

    def get(self, internal_use_id: int):
        return self.safe(lambda: self._get_one(int(internal_use_id)))

    def _get_one(self, internal_use_id: int):
        request = (
            self.db.query(InternalUseRequestModel)
            .filter(InternalUseRequestModel.id == internal_use_id)
            .first()
        )
        if not request:
            return {"status": "error", "message": "Registro de uso interno no encontrado."}

        items = self._request_items(internal_use_id)
        return self._serialize_request(
            request,
            items,
            self._items_quantity_summary(items),
            include_items=True,
            include_sale_analysis=True,
        )

    def _get_all(self, page, items_per_page, description, rol_id):
        if is_restricted_customer_role(rol_id):
            return {"status": "error", "message": "No data found"}

        query = self.db.query(InternalUseRequestModel).order_by(
            InternalUseRequestModel.added_date.desc()
        )
        if description and description.strip():
            query = query.filter(
                InternalUseRequestModel.description.ilike(f"%{description.strip()}%")
            )

        def serialize_row(row):
            items = self._request_items(row.id)
            return self._serialize_request(
                row,
                items,
                self._items_quantity_summary(items),
            )

        if page > 0:
            return paginate_query(
                query,
                page=page,
                items_per_page=items_per_page,
                serialize_row=serialize_row,
            )
        return [serialize_row(row) for row in query.all()]

    def _build_items(self, internal_use_request_id, items_input):
        created_items = []
        for item_input in items_input:
            qty = Decimal(str(item_input.unit_quantity))
            if qty <= 0:
                continue

            product_info = self._get_product_info(item_input.product_id)
            if not product_info:
                raise ValueError(f"El producto {item_input.product_id} no existe.")

            unit_cost = self._purchase_unit_cost(item_input.product_id)
            if unit_cost <= 0:
                raise ValueError(
                    f"No hay costo de compra disponible para {product_info['product_name']}."
                )

            line_total = (qty * unit_cost).quantize(Decimal("1"), rounding=ROUND_HALF_UP)
            now = datetime.now()
            created_items.append(
                InternalUseRequestItemModel(
                    internal_use_request_id=internal_use_request_id,
                    product_id=product_info["product_id"],
                    product_name=product_info["product_name"],
                    unit_quantity=qty,
                    unit_cost=unit_cost,
                    line_total=line_total,
                    unit_measure=product_info["unit_measure"],
                    added_date=now,
                    updated_date=now,
                )
            )
        return created_items

    def store(self, internal_use_inputs):
        try:
            description = (internal_use_inputs.description or "").strip()
            if not description:
                return {"status": "error", "message": "Debe indicar una descripción (obra, proyecto o motivo)."}

            if not internal_use_inputs.items:
                return {"status": "error", "message": "Debe agregar al menos un producto."}

            now = datetime.now()
            new_request = InternalUseRequestModel(
                description=description,
                notes=(internal_use_inputs.notes or "").strip() or None,
                added_date=now,
                updated_date=now,
            )
            self.db.add(new_request)
            self.db.flush()

            items = self._build_items(new_request.id, internal_use_inputs.items)
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

    def delete(self, internal_use_id):
        try:
            request = (
                self.db.query(InternalUseRequestModel)
                .filter(InternalUseRequestModel.id == internal_use_id)
                .first()
            )
            if not request:
                return {"status": "error", "message": "Internal use request not found"}

            sale_id = request.sale_id
            if sale_id:
                block = self._inventory.sale_delete_block_reason(sale_id)
                if block:
                    return {"status": "error", "message": block}
                self._inventory.reverse_sale_inventory(sale_id)

            self.db.query(InternalUseRequestItemModel).filter(
                InternalUseRequestItemModel.internal_use_request_id == internal_use_id
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
