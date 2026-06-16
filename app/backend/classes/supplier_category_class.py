from app.backend.db.models import SupplierCategoryModel, SupplierModel, CategoryModel
from datetime import datetime

from app.backend.services.crud.base_domain_service import BaseDomainService


class SupplierCategoryClass(BaseDomainService):
    
    @staticmethod
    def _serialize_row(supplier_category):
        return {
            "id": supplier_category.id,
            "supplier_id": supplier_category.supplier_id,
            "category_id": supplier_category.category_id,
            "added_date": supplier_category.added_date.strftime("%Y-%m-%d %H:%M:%S")
            if supplier_category.added_date
            else None,
            "updated_date": supplier_category.updated_date.strftime("%Y-%m-%d %H:%M:%S")
            if getattr(supplier_category, "updated_date", None)
            else None,
        }

    def get_all(self, page=0, items_per_page=10):
        query = (
            self.db.query(
                SupplierCategoryModel.id,
                SupplierCategoryModel.supplier_id,
                SupplierCategoryModel.category_id,
                SupplierCategoryModel.added_date,
                SupplierCategoryModel.updated_date,
            )
            .order_by(SupplierCategoryModel.id)
        )
        return self.list_query(
            query, page=page, items_per_page=items_per_page, serialize_row=self._serialize_row
        )

    def get_list(self):
        query = (
            self.db.query(
                SupplierCategoryModel.id,
                SupplierCategoryModel.supplier_id,
                SupplierCategoryModel.category_id,
                SupplierCategoryModel.added_date,
            )
            .order_by(SupplierCategoryModel.id)
        )
        return self.list_wrapped(query, lambda row: self._serialize_row(row))

    def get_by_supplier(self, supplier_id):
        try:
            data = (
                self.db.query(
                    SupplierCategoryModel.id, 
                    SupplierCategoryModel.supplier_id,
                    SupplierCategoryModel.category_id,
                    SupplierCategoryModel.added_date,
                    SupplierModel.supplier.label('supplier_name'),
                    CategoryModel.category.label('category_name')
                )
                .join(SupplierModel, SupplierCategoryModel.supplier_id == SupplierModel.id)
                .join(CategoryModel, SupplierCategoryModel.category_id == CategoryModel.id)
                .filter(SupplierCategoryModel.supplier_id == supplier_id)
                .order_by(SupplierCategoryModel.id)
            )

            serialized_data = [{
                    "id": supplier_category.id,
                    "supplier_id": supplier_category.supplier_id,
                    "supplier_name": supplier_category.supplier_name,
                    "category_id": supplier_category.category_id,
                    "category_name": supplier_category.category_name,
                    "added_date": supplier_category.added_date.strftime("%Y-%m-%d %H:%M:%S") if supplier_category.added_date else None
                } for supplier_category in data]

            return {
                "data": serialized_data
            }

        except Exception as e:
            error_message = str(e)
            return {"status": "error", "message": error_message}
    
    def get_by_category(self, category_id):
        try:
            data = (
                self.db.query(
                    SupplierCategoryModel.id, 
                    SupplierCategoryModel.supplier_id,
                    SupplierCategoryModel.category_id,
                    SupplierCategoryModel.added_date,
                    SupplierModel.supplier.label('supplier_name'),
                    CategoryModel.category.label('category_name')
                )
                .join(SupplierModel, SupplierCategoryModel.supplier_id == SupplierModel.id)
                .join(CategoryModel, SupplierCategoryModel.category_id == CategoryModel.id)
                .filter(SupplierCategoryModel.category_id == category_id)
                .order_by(SupplierCategoryModel.id)
            )

            serialized_data = [{
                    "id": supplier_category.id,
                    "supplier_id": supplier_category.supplier_id,
                    "supplier_name": supplier_category.supplier_name,
                    "category_id": supplier_category.category_id,
                    "category_name": supplier_category.category_name,
                    "added_date": supplier_category.added_date.strftime("%Y-%m-%d %H:%M:%S") if supplier_category.added_date else None
                } for supplier_category in data]

            return {
                "data": serialized_data
            }

        except Exception as e:
            error_message = str(e)
            return {"status": "error", "message": error_message}
    
    def update(self, id, form_data):
        existing_supplier_category = self.db.query(SupplierCategoryModel).filter(SupplierCategoryModel.id == id).one_or_none()

        if not existing_supplier_category:
            return "No data found"

        try:
            # Verificar que el supplier existe si se proporciona
            if hasattr(form_data, 'supplier_id') and form_data.supplier_id is not None:
                supplier = self.db.query(SupplierModel).filter(SupplierModel.id == form_data.supplier_id).first()
                if not supplier:
                    return {"status": "error", "message": "Supplier no encontrado"}
                existing_supplier_category.supplier_id = form_data.supplier_id
            
            # Verificar que la category existe si se proporciona
            if hasattr(form_data, 'category_id') and form_data.category_id is not None:
                category = self.db.query(CategoryModel).filter(CategoryModel.id == form_data.category_id).first()
                if not category:
                    return {"status": "error", "message": "Category no encontrada"}
                existing_supplier_category.category_id = form_data.category_id

            existing_supplier_category.updated_date = datetime.utcnow()

            self.db.commit()
            self.db.refresh(existing_supplier_category)
            return "Supplier Category updated successfully"
        except Exception as e:
            self.db.rollback()
            error_message = str(e)
            return {"status": "error", "message": error_message}
        
    def store(self, supplier_category_inputs):
        try:
            # Verificar que el supplier existe
            supplier = self.db.query(SupplierModel).filter(SupplierModel.id == supplier_category_inputs.supplier_id).first()
            if not supplier:
                return {"status": "error", "message": "Supplier no encontrado"}
            
            # Verificar que la category existe
            category = self.db.query(CategoryModel).filter(CategoryModel.id == supplier_category_inputs.category_id).first()
            if not category:
                return {"status": "error", "message": "Category no encontrada"}
            
            # Verificar que la relación no existe ya
            existing_relation = self.db.query(SupplierCategoryModel).filter(
                SupplierCategoryModel.supplier_id == supplier_category_inputs.supplier_id,
                SupplierCategoryModel.category_id == supplier_category_inputs.category_id
            ).first()
            if existing_relation:
                return {"status": "error", "message": "La relación ya existe"}

            new_supplier_category = SupplierCategoryModel(
                supplier_id=supplier_category_inputs.supplier_id,
                category_id=supplier_category_inputs.category_id,
                added_date=datetime.utcnow()
            )

            self.db.add(new_supplier_category)
            self.db.commit()
            self.db.refresh(new_supplier_category)

            return {
                "status": "Relación Supplier-Category registrada exitosamente.",
                "supplier_category_id": new_supplier_category.id
            }

        except Exception as e:
            self.db.rollback()
            return {"status": "error", "message": str(e)}

    def get(self, id):
        try:
            data_query = self.db.query(
                SupplierCategoryModel.id,
                SupplierCategoryModel.supplier_id,
                SupplierCategoryModel.category_id,
                SupplierCategoryModel.added_date,
                SupplierCategoryModel.updated_date
            ).filter(SupplierCategoryModel.id == id).first()

            if data_query:
                supplier_category_data = {
                    "id": data_query.id,
                    "supplier_id": data_query.supplier_id,
                    "category_id": data_query.category_id,
                    "added_date": data_query.added_date.strftime("%Y-%m-%d %H:%M:%S") if data_query.added_date else None,
                    "updated_date": data_query.updated_date.strftime("%Y-%m-%d %H:%M:%S") if data_query.updated_date else None
                }

                return {"supplier_category_data": supplier_category_data}

            else:
                return {"error": "No se encontraron datos para el campo especificado."}
            
        except Exception as e:
            return {"error": str(e)}
        
    def delete(self, id):
        return self.delete_entity(SupplierCategoryModel, id)

    def delete_by_supplier(self, supplier_id):
        try:
            deleted_count = self.db.query(SupplierCategoryModel).filter(SupplierCategoryModel.supplier_id == supplier_id).delete()
            self.db.commit()
            return f"Se eliminaron {deleted_count} categorías del supplier {supplier_id}"
        except Exception as e:
            self.db.rollback()
            error_message = str(e)
            return f"Error: {error_message}"
    
    def delete_by_category(self, category_id):
        try:
            deleted_count = self.db.query(SupplierCategoryModel).filter(SupplierCategoryModel.category_id == category_id).delete()
            self.db.commit()
            return f"Se eliminaron {deleted_count} suppliers de la categoría {category_id}"
        except Exception as e:
            self.db.rollback()
            error_message = str(e)
            return f"Error: {error_message}"
