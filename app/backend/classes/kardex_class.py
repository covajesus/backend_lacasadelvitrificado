from types import SimpleNamespace

from app.backend.db.models import (
    ProductModel,
    InventoryModel,
    InventoryMovementModel,
    LotItemModel,
    UnitMeasureModel,
    UnitFeatureModel,
)
from sqlalchemy import func, and_

from app.backend.classes.inventory_stock import average_unit_cost_for_product, stock_sum_for_product


class KardexClass:
    def __init__(self, db):
        self.db = db

    @staticmethod
    def _kardex_list_row_dict(kardex):
        qty = int(kardex.quantity or 0)
        qpp = kardex.quantity_per_package
        qpp_val = int(qpp) if qpp is not None else 0
        packages_count = round(qty / qpp_val, 2) if qpp_val > 0 else None
        ac = int(kardex.average_cost or 0)
        return {
            "id": int(kardex.product_id or 0),
            "product_id": int(kardex.product_id or 0),
            "kardex_values_id": int(kardex.product_id or 0),
            "inventory_id": kardex.inventory_id,
            "product_name": kardex.product_name,
            "product_code": kardex.product_code,
            "quantity": qty,
            "unit_measure_id": int(kardex.unit_measure_id) if kardex.unit_measure_id is not None else None,
            "unit_measure": (kardex.unit_measure or "").strip(),
            "quantity_per_package": int(qpp) if qpp is not None else None,
            "packages_count": packages_count,
            "average_cost": ac,
            "total_value": qty * ac,
            "max_public_sale_price": int(kardex.max_public_sale_price or 0),
            "max_private_sale_price": int(kardex.max_private_sale_price or 0),
            "added_date": kardex.added_date.strftime("%Y-%m-%d %H:%M:%S") if kardex.added_date else None,
            "updated_date": kardex.updated_date.strftime("%Y-%m-%d %H:%M:%S") if kardex.updated_date else None,
        }

    def get_all(self, page=0, items_per_page=10):
        """
        Listado tipo inventario/kardex. Cantidad = suma de movimientos por producto;
        costo medio desde ``inventories_movements`` (ponderado por capa).
        """
        try:
            lot_prices_sq = (
                self.db.query(
                    LotItemModel.product_id.label("product_id"),
                    func.max(LotItemModel.public_sale_price).label("max_public_sale_price"),
                    func.max(LotItemModel.private_sale_price).label("max_private_sale_price"),
                )
                .group_by(LotItemModel.product_id)
                .subquery()
            )

            subquery = (
                self.db.query(
                    InventoryModel.product_id,
                    func.max(InventoryModel.id).label("latest_inventory_id"),
                )
                .group_by(InventoryModel.product_id)
                .subquery()
            )

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
                    ProductModel.id.label("product_id"),
                    ProductModel.product.label("product_name"),
                    ProductModel.code.label("product_code"),
                    ProductModel.added_date,
                    ProductModel.updated_date,
                    subquery.c.latest_inventory_id.label("inventory_id"),
                    func.coalesce(stock_subq.c.stock_sum, 0).label("quantity"),
                    func.coalesce(lot_prices_sq.c.max_public_sale_price, 0).label("max_public_sale_price"),
                    func.coalesce(lot_prices_sq.c.max_private_sale_price, 0).label("max_private_sale_price"),
                    UnitMeasureModel.unit_measure.label("unit_measure"),
                    ProductModel.unit_measure_id.label("unit_measure_id"),
                    UnitFeatureModel.quantity_per_package.label("quantity_per_package"),
                )
                .join(subquery, subquery.c.product_id == ProductModel.id)
                .outerjoin(stock_subq, stock_subq.c.inventory_id == subquery.c.latest_inventory_id)
                .outerjoin(lot_prices_sq, lot_prices_sq.c.product_id == ProductModel.id)
                .outerjoin(UnitMeasureModel, UnitMeasureModel.id == ProductModel.unit_measure_id)
                .outerjoin(UnitFeatureModel, UnitFeatureModel.product_id == ProductModel.id)
                .filter(
                    and_(
                        ProductModel.code.isnot(None),
                        func.length(func.trim(ProductModel.code)) > 0,
                    )
                )
                .order_by(ProductModel.id.asc())
            )

            if page > 0:
                total_items = query.count()
                total_pages = (total_items + items_per_page - 1) // items_per_page

                if page < 1 or page > total_pages:
                    return {"status": "error", "message": "Invalid page number"}

                data = query.offset((page - 1) * items_per_page).limit(items_per_page).all()

                if not data:
                    return {"status": "error", "message": "No data found"}

                serialized_data = []
                for row in data:
                    pid = row.product_id
                    qty = int(stock_sum_for_product(self.db, pid))
                    ac = average_unit_cost_for_product(self.db, pid)
                    serialized_data.append(
                        self._kardex_list_row_dict(
                            SimpleNamespace(
                                product_id=pid,
                                product_name=row.product_name,
                                product_code=row.product_code,
                                added_date=row.added_date,
                                updated_date=row.updated_date,
                                inventory_id=row.inventory_id,
                                quantity=qty,
                                average_cost=ac,
                                max_public_sale_price=row.max_public_sale_price,
                                max_private_sale_price=row.max_private_sale_price,
                                unit_measure=row.unit_measure,
                                unit_measure_id=row.unit_measure_id,
                                quantity_per_package=row.quantity_per_package,
                            )
                        )
                    )

                return {
                    "total_items": total_items,
                    "total_pages": total_pages,
                    "current_page": page,
                    "items_per_page": items_per_page,
                    "data": serialized_data,
                }

            data = query.all()
            serialized_data = []
            for row in data:
                pid = row.product_id
                qty = int(stock_sum_for_product(self.db, pid))
                ac = average_unit_cost_for_product(self.db, pid)
                serialized_data.append(
                    self._kardex_list_row_dict(
                        SimpleNamespace(
                            product_id=pid,
                            product_name=row.product_name,
                            product_code=row.product_code,
                            added_date=row.added_date,
                            updated_date=row.updated_date,
                            inventory_id=row.inventory_id,
                            quantity=qty,
                            average_cost=ac,
                            max_public_sale_price=row.max_public_sale_price,
                            max_private_sale_price=row.max_private_sale_price,
                            unit_measure=row.unit_measure,
                            unit_measure_id=row.unit_measure_id,
                            quantity_per_package=row.quantity_per_package,
                        )
                    )
                )

            return serialized_data

        except Exception as e:
            error_message = str(e)
            return {"status": "error", "message": error_message}

    def get_by_product_id(self, product_id):
        try:
            row = (
                self.db.query(
                    ProductModel.id.label("product_id"),
                    ProductModel.product.label("product_name"),
                    ProductModel.code.label("product_code"),
                    ProductModel.added_date,
                    ProductModel.updated_date,
                    ProductModel.unit_measure_id.label("unit_measure_id"),
                    UnitMeasureModel.unit_measure.label("unit_measure"),
                    UnitFeatureModel.quantity_per_package.label("quantity_per_package"),
                    InventoryModel.id.label("inventory_id"),
                )
                .outerjoin(UnitMeasureModel, UnitMeasureModel.id == ProductModel.unit_measure_id)
                .outerjoin(UnitFeatureModel, UnitFeatureModel.product_id == ProductModel.id)
                .outerjoin(InventoryModel, InventoryModel.product_id == ProductModel.id)
                .filter(ProductModel.id == product_id)
                .first()
            )

            if row:
                qty = int(stock_sum_for_product(self.db, product_id))
                ac = average_unit_cost_for_product(self.db, product_id)
                qpp = row.quantity_per_package
                qpp_val = int(qpp) if qpp is not None else 0
                packages_count = round(qty / qpp_val, 2) if qpp_val > 0 else None
                return {
                    "id": row.product_id,
                    "product_id": row.product_id,
                    "inventory_id": row.inventory_id,
                    "product_name": row.product_name,
                    "product_code": row.product_code,
                    "quantity": qty,
                    "unit_measure_id": int(row.unit_measure_id) if row.unit_measure_id is not None else None,
                    "unit_measure": (row.unit_measure or "").strip(),
                    "quantity_per_package": int(qpp) if qpp is not None else None,
                    "packages_count": packages_count,
                    "average_cost": ac,
                    "total_value": qty * ac,
                    "added_date": row.added_date.strftime("%Y-%m-%d %H:%M:%S") if row.added_date else None,
                    "updated_date": row.updated_date.strftime("%Y-%m-%d %H:%M:%S") if row.updated_date else None,
                }
            return {"status": "error", "message": "No kardex record found for this product"}

        except Exception as e:
            return {"status": "error", "message": str(e)}

    def get_summary(self):
        try:
            pids = [r[0] for r in self.db.query(InventoryModel.product_id).distinct().all()]
            total_products = len(pids)
            total_quantity = 0
            total_value = 0
            for pid in pids:
                q = int(stock_sum_for_product(self.db, pid))
                c = average_unit_cost_for_product(self.db, pid)
                total_quantity += q
                total_value += q * c
            average_cost_overall = total_value / total_quantity if total_quantity > 0 else 0

            return {
                "total_products": total_products,
                "total_quantity": total_quantity,
                "total_value": total_value,
                "average_cost_overall": round(average_cost_overall, 2),
            }

        except Exception as e:
            return {"status": "error", "message": str(e)}
