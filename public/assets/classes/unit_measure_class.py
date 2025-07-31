from app.backend.db.models import UnitMeasureModel
from datetime import datetime

class UnitMeasureClass:
    def __init__(self, db):
        self.db = db

    def get_all(self, page=0, items_per_page=10):
        try:
            query = (
                self.db.query(
                    UnitMeasureModel.id, 
                    UnitMeasureModel.unit_measure
                )
                .order_by(UnitMeasureModel.id)
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
                    "id": unit_measure.id,
                    "unit_measure": unit_measure.unit_measure
                } for unit_measure in data]

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
                    "id": unit_measure.id,
                    "unit_measure": unit_measure.unit_measure
                } for unit_measure in data]

                return serialized_data

        except Exception as e:
            error_message = str(e)
            return {"status": "error", "message": error_message}
    
    def get_list(self):
        try:
            data = (
                self.db.query(
                    UnitMeasureModel.id, 
                    UnitMeasureModel.unit_measure
                )
                .order_by(UnitMeasureModel.unit_measure)
            )

            serialized_data = [{
                    "id": unit_measure.id,
                    "unit_measure": unit_measure.unit_measure
                } for unit_measure in data]

            return {
                "data": serialized_data
            }

        except Exception as e:
            error_message = str(e)
            return {"status": "error", "message": error_message}
        
    def store(self, unit_measure_inputs):
        try:
            new_unit_measure = UnitMeasureModel(
                unit_measure=unit_measure_inputs.unit_measure,
                added_date=datetime.utcnow()
            )

            self.db.add(new_unit_measure)
            self.db.commit()
            self.db.refresh(new_unit_measure)

            return {
                "status": "Ubicación registrada exitosamente.",
                "unit_measure_id": new_unit_measure.id
            }

        except Exception as e:
            self.db.rollback()
            return {"status": "error", "message": str(e)}

    def get(self, id):
        try:
            data_query = self.db.query(
                UnitMeasureModel.id,
                UnitMeasureModel.unit_measure
            ).filter(UnitMeasureModel.id == id).first()

            if data_query:
                unit_measure_data = {
                    "id": data_query.id,
                    "unit_measure": data_query.unit_measure
                }

                return {"unit_measure_data": unit_measure_data}

            else:
                return {"error": "No se encontraron datos para el campo especificado."}
            
        except Exception as e:
            return {"error": str(e)}
        
    def delete(self, id):
        try:
            data = self.db.query(UnitMeasureModel).filter(UnitMeasureModel.id == id).first()
            if data:
                self.db.delete(data)
                self.db.commit()
                return 'success'
            else:
                return "No data found"
        except Exception as e:
            error_message = str(e)
            return f"Error: {error_message}"