from app.backend.db.models import VisitModel, CustomerModel, ConstructionSiteModel
from app.backend.classes.customer_class import CustomerClass
from datetime import datetime

class BudgetClass:
    def __init__(self, db):
        self.db = db
        self.customer = CustomerClass(db)

    def get_all(self, page=0, items_per_page=10):
        try:
            query = (
                self.db.query(
                    ConstructionSiteModel.id,
                    ConstructionSiteModel.customer_id,
                    ConstructionSiteModel.closet_id,
                    ConstructionSiteModel.glazed_type_id,
                    ConstructionSiteModel.transit_type_id,
                    ConstructionSiteModel.stair_id,
                    ConstructionSiteModel.wood_retaping_id,
                    ConstructionSiteModel.furniture_move_id,
                    ConstructionSiteModel.wood_type_id,
                    ConstructionSiteModel.status_id,
                    ConstructionSiteModel.square_meters,
                    ConstructionSiteModel.wood_tiles,
                    ConstructionSiteModel.wood_tile_size,
                    ConstructionSiteModel.observations,
                    ConstructionSiteModel.added_date,
                    ConstructionSiteModel.updated_date
                ).filter(ConstructionSiteModel == 5).order_by(ConstructionSiteModel.added_date.desc())
            )

            if page > 0:
                total_items = query.count()
                total_pages = (total_items + items_per_page - 1) // items_per_page

                if page < 1 or page > total_pages:
                    return {"status": "error", "message": "Invalid page number"}

                data = query.offset((page - 1) * items_per_page).limit(items_per_page).all()

                if not data:
                    return {"status": "error", "message": "No data found"}

                serialized_data = [self.serialize_site(site) for site in data]

                return {
                    "total_items": total_items,
                    "total_pages": total_pages,
                    "current_page": page,
                    "items_per_page": items_per_page,
                    "data": serialized_data
                }

            else:
                data = query.all()
                return [self.serialize_site(site) for site in data]

        except Exception as e:
            return {"status": "error", "message": str(e)}

    def search(self, search_inputs, page=0, items_per_page=10):
        try:
            print(search_inputs)
            filters = []
            if search_inputs.full_name:
                filters.append(CustomerModel.full_name.ilike(f"%{search_inputs.full_name.lower()}%"))
            if search_inputs.phone:
                filters.append(CustomerModel.phone == search_inputs.phone)
            if search_inputs.address:
                filters.append(CustomerModel.email.ilike(f"%{search_inputs.address}%"))
            
            query = (
                self.db.query(
                    VisitModel.id, 
                    VisitModel.since_visit_date_time, 
                    VisitModel.until_visit_date_time, 
                    VisitModel.added_date,
                    CustomerModel.full_name,
                    CustomerModel.phone,
                    VisitModel.status_id
                )
                .join(CustomerModel, VisitModel.customer_id == CustomerModel.id, isouter=True)
                .filter(*filters)
                .order_by(VisitModel.id)
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
                    "id": visit.id,
                    "since_visit_date_time": visit.since_visit_date_time,
                    "until_visit_date_time": visit.until_visit_date_time,
                    "added_date": visit.added_date.strftime("%Y-%m-%d %H:%M:%S") if visit.added_date else None,
                    "full_name": visit.full_name,
                    "phone": visit.phone,
                    "status_id": visit.status_id
                } for visit in data]

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
                    "id": visit.id,
                    "since_visit_date_time": visit.since_visit_date_time,
                    "until_visit_date_time": visit.until_visit_date_time,
                    "added_date": visit.added_date.strftime("%Y-%m-%d %H:%M:%S") if visit.added_date else None,
                    "full_name": visit.full_name,
                    "phone": visit.phone,
                    "status_id": visit.status_id
                } for visit in data]

                return serialized_data

        except Exception as e:
            error_message = str(e)
            return {"status": "error", "message": error_message}
        
    def store(self, visit_inputs):
        try:
            customer_update_result = self.customer.update(visit_inputs.id, visit_inputs)

            if customer_update_result.get("status") != "Cliente actualizado exitosamente.":
                return customer_update_result

            customer_id = customer_update_result["customer_id"]

            new_visit = VisitModel(
                customer_id=customer_id,
                since_visit_date_time=visit_inputs.since_visit_date_time,
                until_visit_date_time=visit_inputs.until_visit_date_time,
                status_id=8,
                added_date=datetime.utcnow()
            )

            self.db.add(new_visit)
            self.db.commit()
            self.db.refresh(new_visit)

            return {
                "status": "Visita registrada y cliente actualizado exitosamente.",
                "visit_id": new_visit.id
            }

        except Exception as e:
            self.db.rollback()
            return {"status": "error", "message": str(e)}

    def accept(self, id):
        try:
            visit = self.db.query(VisitModel).filter(VisitModel.id == id).first()

            if not visit:
                return {
                    "status": "error",
                    "message": "Visita no encontrada."
                }

            visit.status_id = 4
            visit.updated_date = datetime.utcnow()

            self.db.commit()
            self.db.refresh(visit)

            new_construction_site = ConstructionSiteModel(
                customer_id=visit.customer_id,
                status_id=5
            )

            self.db.add(new_construction_site)
            self.db.commit()
            self.db.refresh(new_construction_site)

            return {
                "status": "Visita aceptada exitosamente.",
                "visit_id": new_construction_site.id
            }

        except Exception as e:
            self.db.rollback()
            return {"status": "error", "message": str(e)}


    def delete(self, id):
        try:
            data = self.db.query(VisitModel).filter(VisitModel.id == id).first()
            if data:
                self.db.delete(data)
                self.db.commit()
                return 'success'
            else:
                return "No data found"
        except Exception as e:
            error_message = str(e)
            return f"Error: {error_message}"