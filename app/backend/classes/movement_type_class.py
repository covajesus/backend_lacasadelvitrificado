from app.backend.db.models import MovementTypeModel
from app.backend.services.crud.base_domain_service import BaseDomainService


class MovementTypeClass(BaseDomainService):
    @staticmethod
    def _serialize_row(movement_type):
        return {"id": movement_type.id, "movement_type": movement_type.movement_type}

    def get_list(self):
        query = self.db.query(MovementTypeModel.id, MovementTypeModel.movement_type).order_by(
            MovementTypeModel.location
        )
        return self.list_wrapped(query, self._serialize_row)
