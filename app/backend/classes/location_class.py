from datetime import datetime

from app.backend.db.models import LocationModel
from app.backend.services.crud.base_domain_service import BaseDomainService


class LocationClass(BaseDomainService):
    @staticmethod
    def _serialize_row(location):
        return {"id": location.id, "location": location.location}

    def get_all(self, page=0, items_per_page=10):
        query = self.db.query(LocationModel.id, LocationModel.location).order_by(LocationModel.id)
        return self.list_query(
            query, page=page, items_per_page=items_per_page, serialize_row=self._serialize_row
        )

    def get_list(self):
        query = self.db.query(LocationModel.id, LocationModel.location).order_by(LocationModel.location)
        return self.list_wrapped(query, self._serialize_row)

    def store(self, location_inputs):
        return self.safe(lambda: self._store_location(location_inputs), rollback=True)

    def _store_location(self, location_inputs):
        new_location = LocationModel(
            location=location_inputs.location,
            added_date=datetime.utcnow(),
        )
        self.db.add(new_location)
        self.db.commit()
        self.db.refresh(new_location)
        return {"status": "Ubicación registrada exitosamente.", "location_id": new_location.id}

    def get(self, id):
        return self.safe(
            lambda: self.get_or_error(
                self.db.query(LocationModel.id, LocationModel.location)
                .filter(LocationModel.id == id)
                .first(),
                data_key="location_data",
                serialize=lambda row: {"id": row.id, "location": row.location},
            )
        )

    def delete(self, id):
        return self.delete_entity(LocationModel, id)
