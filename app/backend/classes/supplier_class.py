from datetime import datetime

from fastapi import HTTPException

from app.backend.db.models import SupplierModel
from app.backend.services.crud.base_domain_service import BaseDomainService


class SupplierClass(BaseDomainService):
    @staticmethod
    def _serialize_row(supplier):
        return {
            "id": supplier.id,
            "identification_number": supplier.identification_number,
            "supplier": supplier.supplier,
            "address": supplier.address,
            "added_date": supplier.added_date.strftime("%Y-%m-%d %H:%M:%S"),
        }

    def get_all(self, page=0, items_per_page=10):
        query = (
            self.db.query(
                SupplierModel.id,
                SupplierModel.identification_number,
                SupplierModel.supplier,
                SupplierModel.address,
                SupplierModel.added_date,
            )
            .order_by(SupplierModel.id)
        )
        return self.list_query(
            query, page=page, items_per_page=items_per_page, serialize_row=self._serialize_row
        )

    def get_list(self, page=0, items_per_page=10):
        query = (
            self.db.query(
                SupplierModel.id,
                SupplierModel.identification_number,
                SupplierModel.supplier,
                SupplierModel.address,
                SupplierModel.added_date,
            )
            .order_by(SupplierModel.id)
        )
        result = self.list_wrapped(query, self._serialize_row)
        if isinstance(result, dict) and result.get("data") == []:
            return {"status": "error", "message": "No data found"}
        return result

    def store(self, supplier_inputs):
        try:
            return self._store(supplier_inputs)
        except Exception as e:
            self.db.rollback()
            raise HTTPException(status_code=500, detail=f"Error: {str(e)}") from e

    def _store(self, supplier_inputs):
        new_supplier = SupplierModel(
            identification_number=supplier_inputs.identification_number,
            supplier=supplier_inputs.supplier,
            address=supplier_inputs.address,
            added_date=datetime.now(),
            updated_date=datetime.now(),
        )
        self.db.add(new_supplier)
        self.db.commit()
        self.db.refresh(new_supplier)
        return {"status": "Proveedor registrado exitosamente.", "supplier_id": new_supplier.id}

    def update(self, id, supplier_inputs):
        existing_supplier = self.db.query(SupplierModel).filter(SupplierModel.id == id).one_or_none()
        if not existing_supplier:
            return "No data found"
        return self.safe(lambda: self._update(existing_supplier, supplier_inputs), rollback=True)

    def _update(self, existing_supplier, supplier_inputs):
        existing_supplier.identification_number = supplier_inputs.identification_number
        existing_supplier.supplier = supplier_inputs.supplier
        existing_supplier.address = supplier_inputs.address
        existing_supplier.updated_date = datetime.utcnow()
        self.db.commit()
        self.db.refresh(existing_supplier)
        return "Supplier updated successfully"

    def get(self, id):
        return self.safe(
            lambda: self.get_or_error(
                self.db.query(
                    SupplierModel.id,
                    SupplierModel.supplier,
                    SupplierModel.identification_number,
                    SupplierModel.address,
                    SupplierModel.added_date,
                )
                .filter(SupplierModel.id == id)
                .first(),
                data_key="supplier_data",
                serialize=lambda row: {
                    "id": row.id,
                    "supplier": row.supplier,
                    "identification_number": row.identification_number,
                    "address": row.address,
                    "added_date": row.added_date.strftime("%Y-%m-%d %H:%M:%S")
                    if row.added_date
                    else None,
                },
            )
        )

    def delete(self, id):
        return self.delete_entity(SupplierModel, id)
