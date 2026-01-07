from app.backend.db.models import KardexValuesModel, ProductModel, InventoryModel, InventoryMovementModel
from datetime import datetime
from sqlalchemy import func

class KardexClass:
    def __init__(self, db):
        self.db = db

    def get_all(self, page=0, items_per_page=10):
        try:
            # Subconsulta para obtener el inventory_id más reciente por producto
            subquery = (
                self.db.query(
                    InventoryModel.product_id,
                    func.max(InventoryModel.id).label("latest_inventory_id")
                )
                .group_by(InventoryModel.product_id)
                .subquery()
            )
            
            # Subconsulta de stock por inventario desde movimientos
            stock_subq = (
                self.db.query(
                    InventoryMovementModel.inventory_id.label("inventory_id"),
                    func.sum(InventoryMovementModel.quantity).label("stock_sum"),
                )
                .group_by(InventoryMovementModel.inventory_id)
                .subquery()
            )
            
            query = (
                self.db.query(
                    KardexValuesModel.id,
                    KardexValuesModel.product_id,
                    KardexValuesModel.average_cost,
                    KardexValuesModel.added_date,
                    KardexValuesModel.updated_date,
                    ProductModel.product.label("product_name"),
                    ProductModel.code.label("product_code"),
                    subquery.c.latest_inventory_id.label("inventory_id"),
                    func.coalesce(stock_subq.c.stock_sum, 0).label("quantity")
                )
                .join(ProductModel, ProductModel.id == KardexValuesModel.product_id, isouter=True)
                .join(subquery, subquery.c.product_id == KardexValuesModel.product_id, isouter=True)
                .outerjoin(stock_subq, stock_subq.c.inventory_id == subquery.c.latest_inventory_id)
                .order_by(KardexValuesModel.updated_date.desc())
            )

            if page > 0:
                total_items = query.count()
                total_pages = (total_items + items_per_page - 1) // items_per_page

                if page < 1 or page > total_pages:
                    return {"status": "error", "message": "Invalid page number"}

                data = query.offset((page - 1) * items_per_page).limit(items_per_page).all()

                if not data:
                    return {"status": "error", "message": "No data found"}

                serialized_data = [{
                    "id": kardex.id,
                    "product_id": kardex.product_id,
                    "inventory_id": kardex.inventory_id,
                    "product_name": kardex.product_name,
                    "product_code": kardex.product_code,
                    "quantity": kardex.quantity,
                    "average_cost": kardex.average_cost,
                    "total_value": kardex.quantity * kardex.average_cost,
                    "added_date": kardex.added_date.strftime("%Y-%m-%d %H:%M:%S") if kardex.added_date else None,
                    "updated_date": kardex.updated_date.strftime("%Y-%m-%d %H:%M:%S") if kardex.updated_date else None
                } for kardex in data]

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
                    "id": kardex.id,
                    "product_id": kardex.product_id,
                    "inventory_id": kardex.inventory_id,
                    "product_name": kardex.product_name,
                    "product_code": kardex.product_code,
                    "quantity": kardex.quantity,
                    "average_cost": kardex.average_cost,
                    "total_value": kardex.quantity * kardex.average_cost,
                    "added_date": kardex.added_date.strftime("%Y-%m-%d %H:%M:%S") if kardex.added_date else None,
                    "updated_date": kardex.updated_date.strftime("%Y-%m-%d %H:%M:%S") if kardex.updated_date else None
                } for kardex in data]

                return serialized_data

        except Exception as e:
            error_message = str(e)
            return {"status": "error", "message": error_message}

    def get_by_product_id(self, product_id):
        try:
            kardex_record = (
                self.db.query(
                    KardexValuesModel.id,
                    KardexValuesModel.product_id,
                    KardexValuesModel.quantity,
                    KardexValuesModel.average_cost,
                    KardexValuesModel.added_date,
                    KardexValuesModel.updated_date,
                    ProductModel.product.label("product_name"),
                    ProductModel.code.label("product_code"),
                    InventoryModel.id.label("inventory_id")
                )
                .join(ProductModel, ProductModel.id == KardexValuesModel.product_id, isouter=True)
                .join(InventoryModel, InventoryModel.product_id == KardexValuesModel.product_id, isouter=True)
                .filter(KardexValuesModel.product_id == product_id)
                .first()
            )

            if kardex_record:
                return {
                    "id": kardex_record.id,
                    "product_id": kardex_record.product_id,
                    "inventory_id": kardex_record.inventory_id,
                    "product_name": kardex_record.product_name,
                    "product_code": kardex_record.product_code,
                    "quantity": kardex_record.quantity,
                    "average_cost": kardex_record.average_cost,
                    "total_value": kardex_record.quantity * kardex_record.average_cost,
                    "added_date": kardex_record.added_date.strftime("%Y-%m-%d %H:%M:%S") if kardex_record.added_date else None,
                    "updated_date": kardex_record.updated_date.strftime("%Y-%m-%d %H:%M:%S") if kardex_record.updated_date else None
                }
            else:
                return {"status": "error", "message": "No kardex record found for this product"}

        except Exception as e:
            return {"status": "error", "message": str(e)}

    def get_summary(self):
        try:
            # Obtener resumen general del kardex
            total_products = self.db.query(KardexValuesModel).count()
            total_quantity = self.db.query(func.sum(KardexValuesModel.quantity)).scalar() or 0
            total_value = self.db.query(
                func.sum(KardexValuesModel.quantity * KardexValuesModel.average_cost)
            ).scalar() or 0
            average_cost_overall = total_value / total_quantity if total_quantity > 0 else 0

            return {
                "total_products": total_products,
                "total_quantity": total_quantity,
                "total_value": total_value,
                "average_cost_overall": round(average_cost_overall, 2)
            }

        except Exception as e:
            return {"status": "error", "message": str(e)}
