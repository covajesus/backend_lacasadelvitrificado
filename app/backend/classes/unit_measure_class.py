from datetime import datetime

from app.backend.db.models import UnitMeasureModel
from app.backend.services.crud.base_domain_service import BaseDomainService


class UnitMeasureClass(BaseDomainService):
    @staticmethod
    def _serialize_row(unit_measure):
        return {"id": unit_measure.id, "unit_measure": unit_measure.unit_measure}

    def get_all(self, page=0, items_per_page=10):
        query = self.db.query(
            UnitMeasureModel.id, UnitMeasureModel.unit_measure
        ).order_by(UnitMeasureModel.id)
        return self.list_query(
            query, page=page, items_per_page=items_per_page, serialize_row=self._serialize_row
        )

    def get_list(self):
        query = self.db.query(
            UnitMeasureModel.id, UnitMeasureModel.unit_measure
        ).order_by(UnitMeasureModel.unit_measure)
        return self.list_wrapped(query, self._serialize_row)

    def store(self, unit_measure_inputs):
        return self.safe(lambda: self._store(unit_measure_inputs), rollback=True)

    def _store(self, unit_measure_inputs):
        new_unit_measure = UnitMeasureModel(
            unit_measure=unit_measure_inputs.unit_measure,
            added_date=datetime.utcnow(),
        )
        self.db.add(new_unit_measure)
        self.db.commit()
        self.db.refresh(new_unit_measure)
        return {
            "status": "Ubicación registrada exitosamente.",
            "unit_measure_id": new_unit_measure.id,
        }

    def get(self, id):
        return self.safe(
            lambda: self.get_or_error(
                self.db.query(UnitMeasureModel.id, UnitMeasureModel.unit_measure)
                .filter(UnitMeasureModel.id == id)
                .first(),
                data_key="unit_measure_data",
                serialize=lambda row: {"id": row.id, "unit_measure": row.unit_measure},
            )
        )

    def delete(self, id):
        return self.delete_entity(UnitMeasureModel, id)

    def update(self, id, unit_measure_inputs):
        return self.safe(lambda: self._update(id, unit_measure_inputs), rollback=True)

    def _update(self, id, unit_measure_inputs):
        existing = self.db.query(UnitMeasureModel).filter(UnitMeasureModel.id == id).first()
        if not existing:
            return {"status": "error", "message": "Unidad de medida no encontrada."}
        existing.unit_measure = unit_measure_inputs.unit_measure
        existing.updated_date = datetime.utcnow()
        self.db.commit()
        self.db.refresh(existing)
        return {
            "status": "success",
            "message": "Unidad de medida actualizada exitosamente.",
            "unit_measure_id": existing.id,
        }
