import re
from datetime import datetime
from decimal import Decimal, ROUND_HALF_UP
from sqlalchemy import func

from app.backend.classes.inventory_stock import sale_acceptance_unit_cost_from_movements
from app.backend.core.constants import RequestReasonPrefix, TaxPolicy
from app.backend.core.exceptions import ValidationError
from app.backend.db.models import (
    SampleRequestModel,
    SampleRequestItemModel,
    ProductModel,
    UnitFeatureModel,
    UnitMeasureModel,
    CustomerModel,
)
from app.backend.services.inventory.inventory_sale_bridge import InventorySaleBridge, SaleDeductionLine
from app.backend.core.pagination import paginate_query
from app.backend.core.role_access import apply_customer_rut_scope
from app.backend.services.requests.item_summary import summarize_items_by_unit
from app.backend.services.requests.linked_request_base import LinkedRequestService


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


class SampleClass(LinkedRequestService):
    reason_prefix = RequestReasonPrefix.SAMPLE

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
        return summarize_items_by_unit(
            items,
            quantity_resolver=lambda i: float(i.total_amount or 0),
        )

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
        self._inventory.validate_stock(
            items,
            base_units_resolver=lambda i: int(Decimal(i.total_amount or 0)),
        )

    def _purchase_line_total(self, product_id, base_units):
        unit_cost = Decimal(str(sale_acceptance_unit_cost_from_movements(self.db, product_id) or 0))
        return (unit_cost * Decimal(str(base_units or 0))).quantize(Decimal("1"), rounding=ROUND_HALF_UP)

    def _calculate_sample_totals(self, items):
        subtotal = sum(self._purchase_line_total(item.product_id, item.total_amount) for item in items)
        tax = TaxPolicy.ZERO
        total = subtotal
        return subtotal, tax, total

    def _to_deduction_lines(self, items):
        lines = []
        for item in items:
            effective_qty = int(Decimal(item.total_amount or 0))
            if effective_qty <= 0:
                continue
            line_price = int(self._purchase_line_total(item.product_id, item.total_amount))
            lines.append(
                SaleDeductionLine(
                    product_id=item.product_id,
                    inventory_base_units=effective_qty,
                    line_price=line_price,
                )
            )
        return lines

    def _create_or_refresh_sample_sale(self, sample_request, items):
        if not sample_request.customer_id:
            raise ValueError("Cliente inválido para generar el pedido de muestra.")

        subtotal, tax, total = self._calculate_sample_totals(items)
        delivery = self._sample_delivery_address(
            sample_request.id,
            sample_request.customer_name,
            sample_request.customer_rut,
        )
        self._validate_sample_stock(items)
        return self._sale_linkage.create_or_refresh(
            sample_request,
            customer_id=sample_request.customer_id,
            delivery_address=delivery,
            subtotal=subtotal,
            tax=tax,
            total=total,
            deduction_lines=self._to_deduction_lines(items),
        )

    def get_all(self, page=0, items_per_page=10, rut=None, customer_name=None, rol_id=None, user_rut=None):
        return self.safe(lambda: self._get_all(page, items_per_page, rut, customer_name, rol_id, user_rut))

    def _get_all(self, page, items_per_page, rut, customer_name, rol_id, user_rut):
        query = self.db.query(SampleRequestModel).order_by(SampleRequestModel.added_date.desc())
        if rut and rut.strip():
            query = query.filter(SampleRequestModel.customer_rut == rut.strip())
        if customer_name and customer_name.strip():
            query = query.filter(SampleRequestModel.customer_name.ilike(f"%{customer_name.strip()}%"))
        query = apply_customer_rut_scope(
            query, SampleRequestModel, rol_id=rol_id, user_rut=user_rut
        )

        def serialize_row(row):
            return self._serialize_request(row, self._items_quantity_summary(row.id))

        if page > 0:
            return paginate_query(
                query, page=page, items_per_page=items_per_page, serialize_row=serialize_row
            )
        return [serialize_row(row) for row in query.all()]

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
        except (ValueError, ValidationError) as e:
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
        except (ValueError, ValidationError) as e:
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
                self._inventory.reverse_sale_inventory(request.sale_id)
                self._inventory.unlink_sale(request.sale_id, mode="soft_reject", check_folio=False)

            self.db.query(SampleRequestItemModel).filter(
                SampleRequestItemModel.sample_request_id == sample_id
            ).delete()
            self.db.delete(request)
            self.db.commit()
            return "success"
        except Exception as e:
            self.db.rollback()
            return {"status": "error", "message": str(e)}
