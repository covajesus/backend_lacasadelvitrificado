from datetime import datetime

from app.backend.db.models import CategoryModel
from app.backend.services.crud.base_domain_service import BaseDomainService


class CategoryClass(BaseDomainService):
    @staticmethod
    def _serialize_row(category):
        return {
            "id": category.id,
            "category": category.category,
            "public_name": category.public_name,
            "color": category.color,
        }

    def get_all(self, page=0, items_per_page=10):
        query = (
            self.db.query(
                CategoryModel.id,
                CategoryModel.category,
                CategoryModel.public_name,
                CategoryModel.color,
            )
            .order_by(CategoryModel.id)
        )
        return self.list_query(
            query, page=page, items_per_page=items_per_page, serialize_row=self._serialize_row
        )

    def get_list(self):
        query = (
            self.db.query(
                CategoryModel.id,
                CategoryModel.category,
                CategoryModel.public_name,
                CategoryModel.color,
            )
            .order_by(CategoryModel.category)
        )
        return self.list_wrapped(query, self._serialize_row)

    def update(self, id, form_data):
        existing_category = self.db.query(CategoryModel).filter(CategoryModel.id == id).one_or_none()
        if not existing_category:
            return "No data found"

        return self.safe(
            lambda: self._update_category(existing_category, form_data),
            rollback=True,
        )

    def _update_category(self, existing_category, form_data):
        existing_category.category = form_data.category
        existing_category.public_name = form_data.public_name
        existing_category.color = form_data.color
        existing_category.updated_date = datetime.utcnow()
        self.db.commit()
        self.db.refresh(existing_category)
        return "Category updated successfully"

    def store(self, category_inputs):
        return self.safe(
            lambda: self._store_category(category_inputs),
            rollback=True,
        )

    def _store_category(self, category_inputs):
        new_category = CategoryModel(
            category=category_inputs.category,
            public_name=category_inputs.public_name,
            color=category_inputs.color,
            added_date=datetime.utcnow(),
        )
        self.db.add(new_category)
        self.db.commit()
        self.db.refresh(new_category)
        return {"status": "Categoría registrada exitosamente.", "category_id": new_category.id}

    def get(self, id):
        return self.safe(
            lambda: self.get_or_error(
                self.db.query(
                    CategoryModel.id,
                    CategoryModel.category,
                    CategoryModel.public_name,
                    CategoryModel.color,
                    CategoryModel.added_date,
                )
                .filter(CategoryModel.id == id)
                .first(),
                data_key="category_data",
                serialize=lambda row: {
                    "id": row.id,
                    "category": row.category,
                    "public_name": row.public_name,
                    "color": row.color,
                    "added_date": row.added_date.strftime("%Y-%m-%d %H:%M:%S"),
                },
            )
        )

    def delete(self, id):
        return self.delete_entity(CategoryModel, id)
