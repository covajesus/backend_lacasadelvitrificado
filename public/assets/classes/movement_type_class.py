from app.backend.db.models import MovementTypeModel
from datetime import datetime

class MovementTypeClass:
    def __init__(self, db):
        self.db = db
    
    def get_list(self):
        try:
            data = (
                self.db.query(
                    MovementTypeModel.id, 
                    MovementTypeModel.movement_type
                )
                .order_by(MovementTypeModel.location)
            )

            serialized_data = [{
                    "id": movement_type.id,
                    "movement_type": movement_type.movement_type
                } for movement_type in data]

            return {
                "data": serialized_data
            }

        except Exception as e:
            error_message = str(e)
            return {"status": "error", "message": error_message}