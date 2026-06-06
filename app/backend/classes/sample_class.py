import re
from datetime import datetime
from decimal import Decimal
from sqlalchemy import func

from app.backend.db.models import (
    SampleRequestModel,
    SampleRequestItemModel,
    ProductModel,
    UnitFeatureModel,
    UnitMeasureModel,
    CustomerModel,
)


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

    def _serialize_request(self, request, items_count=0):
        return {
            "id": request.id,
            "customer_id": request.customer_id,
            "customer_rut": request.customer_rut,
            "customer_name": request.customer_name,
            "notes": request.notes or "",
            "items_count": items_count,
            "added_date": request.added_date.strftime("%Y-%m-%d %H:%M:%S") if request.added_date else None,
            "updated_date": request.updated_date.strftime("%Y-%m-%d %H:%M:%S") if request.updated_date else None,
        }

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
                    items_count = (
                        self.db.query(SampleRequestItemModel)
                        .filter(SampleRequestItemModel.sample_request_id == row.id)
                        .count()
                    )
                    serialized.append(self._serialize_request(row, items_count))

                return {
                    "total_items": total_items,
                    "total_pages": total_pages,
                    "current_page": page,
                    "items_per_page": items_per_page,
                    "data": serialized,
                }

            rows = query.all()
            return [self._serialize_request(row) for row in rows]
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

            payload = self._serialize_request(request, len(items))
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

            self.db.query(SampleRequestItemModel).filter(
                SampleRequestItemModel.sample_request_id == sample_id
            ).delete()
            self.db.delete(request)
            self.db.commit()
            return "success"
        except Exception as e:
            self.db.rollback()
            return {"status": "error", "message": str(e)}
