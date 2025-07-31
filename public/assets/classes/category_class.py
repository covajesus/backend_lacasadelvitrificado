from app.backend.db.models import CategoryModel
from datetime import datetime

class CategoryClass:
    def __init__(self, db):
        self.db = db

    def get_all(self, page=0, items_per_page=10):
        try:
            query = (
                self.db.query(
                    CategoryModel.id, 
                    CategoryModel.category,
                    CategoryModel.public_name,
                    CategoryModel.color
                )
                .order_by(CategoryModel.id)
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
                    "id": category.id,
                    "category": category.category,
                    "public_name": category.public_name,
                    "color": category.color
                } for category in data]

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
                    "id": category.id,
                    "category": category.category,
                    "public_name": category.public_name,
                    "color": category.color
                } for category in data]

                return serialized_data

        except Exception as e:
            error_message = str(e)
            return {"status": "error", "message": error_message}
    
    def get_list(self):
        try:
            data = (
                self.db.query(
                    CategoryModel.id, 
                    CategoryModel.category,
                    CategoryModel.public_name,
                    CategoryModel.color
                )
                .order_by(CategoryModel.category)
            )

            serialized_data = [{
                    "id": category.id,
                    "category": category.category,
                    "public_name": category.public_name,
                    "color": category.color
                } for category in data]

            return {
                "data": serialized_data
            }

        except Exception as e:
            error_message = str(e)
            return {"status": "error", "message": error_message}
    
    def update(self, id, form_data):
        existing_category = self.db.query(CategoryModel).filter(CategoryModel.id == id).one_or_none()

        if not existing_category:
            return "No data found"

        try:
            existing_category.category = form_data.category
            existing_category.public_name = form_data.public_name
            existing_category.color = form_data.color
            existing_category.updated_date = datetime.utcnow()

            self.db.commit()
            self.db.refresh(existing_category)
            return "Category updated successfully"
        except Exception as e:
            self.db.rollback()
            error_message = str(e)
            return {"status": "error", "message": error_message}
        
    def store(self, category_inputs):
        try:
            new_category = CategoryModel(
                category=category_inputs.category,
                public_name=category_inputs.public_name,
                color=category_inputs.color,
                added_date=datetime.utcnow()
            )

            self.db.add(new_category)
            self.db.commit()
            self.db.refresh(new_category)

            return {
                "status": "Categoría registrada exitosamente.",
                "category_id": new_category.id
            }

        except Exception as e:
            self.db.rollback()
            return {"status": "error", "message": str(e)}

    def get(self, id):
        try:
            data_query = self.db.query(
                CategoryModel.id,
                CategoryModel.category,
                CategoryModel.public_name,
                CategoryModel.color,
                CategoryModel.added_date
            ).filter(CategoryModel.id == id).first()

            if data_query:
                category_data = {
                    "id": data_query.id,
                    "category": data_query.category,
                    "public_name": data_query.public_name,
                    "color": data_query.color,
                    "added_date": data_query.added_date.strftime("%Y-%m-%d %H:%M:%S")
                }

                return {"category_data": category_data}

            else:
                return {"error": "No se encontraron datos para el campo especificado."}
            
        except Exception as e:
            return {"error": str(e)}
        
    def delete(self, id):
        try:
            data = self.db.query(CategoryModel).filter(CategoryModel.id == id).first()
            if data:
                self.db.delete(data)
                self.db.commit()
                return 'success'
            else:
                return "No data found"
        except Exception as e:
            error_message = str(e)
            return f"Error: {error_message}"