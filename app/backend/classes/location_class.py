from app.backend.db.models import LocationModel
from datetime import datetime

class LocationClass:
    def __init__(self, db):
        self.db = db

    def get_all(self, page=0, items_per_page=10):
        try:
            query = (
                self.db.query(
                    LocationModel.id, 
                    LocationModel.location
                )
                .order_by(LocationModel.id)
            )

            if page > 0:
                total_items = query.count()
                total_pages = (total_items + items_per_page - 1)

                if page < 1 or page > total_pages:
                    return {"status": "error", "message": "Invalid page number"}

                data = query.offset((page - 1) * items_per_page).limit(items_per_page).all()

                if not data:
                    return {"status": "error", "message": "No data found"}

                serialized_data = [{
                    "id": location.id,
                    "location": location.location
                } for location in data]

                return {
                    "total_items": total_items,
                    "total_pages": total_pages,
                    "current_page": page,
                    "items_per_page": items_per_page,
                    "data": serialized_data
                }

            else:
                data = query.all()

                serialized_data = [{
                    "id": location.id,
                    "location": location.location
                } for location in data]

                return serialized_data

        except Exception as e:
            error_message = str(e)
            return {"status": "error", "message": error_message}
    
    def get_list(self):
        try:
            data = (
                self.db.query(
                    LocationModel.id, 
                    LocationModel.location
                )
                .order_by(LocationModel.location)
            )

            serialized_data = [{
                    "id": location.id,
                    "location": location.location
                } for location in data]

            return {
                "data": serialized_data
            }

        except Exception as e:
            error_message = str(e)
            return {"status": "error", "message": error_message}
        
    def store(self, location_inputs):
        try:
            new_location = LocationModel(
                location=location_inputs.location,
                added_date=datetime.utcnow()
            )

            self.db.add(new_location)
            self.db.commit()
            self.db.refresh(new_location)

            return {
                "status": "Ubicación registrada exitosamente.",
                "location_id": new_location.id
            }

        except Exception as e:
            self.db.rollback()
            return {"status": "error", "message": str(e)}

    def get(self, id):
        try:
            data_query = self.db.query(
                LocationModel.id,
                LocationModel.location
            ).filter(LocationModel.id == id).first()

            if data_query:
                location_data = {
                    "id": data_query.id,
                    "location": data_query.location
                }

                return {"location_data": location_data}

            else:
                return {"error": "No se encontraron datos para el campo especificado."}
            
        except Exception as e:
            return {"error": str(e)}
        
    def delete(self, id):
        try:
            data = self.db.query(LocationModel).filter(LocationModel.id == id).first()
            if data:
                self.db.delete(data)
                self.db.commit()
                return 'success'
            else:
                return "No data found"
        except Exception as e:
            error_message = str(e)
            return f"Error: {error_message}"