"""
Saldos de inventario solo desde ``inventories_movements`` (suma de ``quantity`` por clave).
"""
from sqlalchemy import func

from app.backend.db.models import (
    InventoryModel,
    InventoryMovementModel,
    LotItemModel,
    LotModel,
)

# Salidas: no entran en la media aritmética de ``unit_cost`` (venta, salida por ajuste).
AVERAGE_UNIT_COST_EXCLUDED_MOVEMENT_TYPE_IDS = (2, 3)


def stock_sum_for_product(db, product_id):
    q = (
        db.query(func.coalesce(func.sum(InventoryMovementModel.quantity), 0))
        .join(InventoryModel, InventoryModel.id == InventoryMovementModel.inventory_id)
        .filter(InventoryModel.product_id == product_id)
    )
    return int(q.scalar() or 0)


def stock_sum_for_inventory(db, inventory_id):
    q = (
        db.query(func.coalesce(func.sum(InventoryMovementModel.quantity), 0))
        .filter(InventoryMovementModel.inventory_id == inventory_id)
    )
    return int(q.scalar() or 0)


def lot_balance_subquery(db):
    return (
        db.query(
            InventoryMovementModel.inventory_id.label("inv_id"),
            InventoryMovementModel.lot_item_id.label("lot_item_id"),
            func.coalesce(func.sum(InventoryMovementModel.quantity), 0).label("balance"),
        )
        .group_by(
            InventoryMovementModel.inventory_id,
            InventoryMovementModel.lot_item_id,
        )
        .subquery()
    )


def fifo_lots_available(db, product_id):
    """Líneas (lote) con saldo > 0 orden FIFO por ``lots.arrival_date``."""
    bal_sq = lot_balance_subquery(db)
    return (
        db.query(
            LotItemModel,
            LotModel,
            bal_sq.c.inv_id.label("inventory_id"),
            bal_sq.c.balance,
        )
        .join(LotModel, LotModel.id == LotItemModel.lot_id)
        .join(InventoryModel, InventoryModel.product_id == LotItemModel.product_id)
        .join(
            bal_sq,
            (bal_sq.c.inv_id == InventoryModel.id)
            & (bal_sq.c.lot_item_id == LotItemModel.id),
        )
        .filter(LotItemModel.product_id == product_id)
        .filter(bal_sq.c.balance > 0)
        .order_by(LotModel.arrival_date.asc())
        .all()
    )


def average_unit_cost_for_product(db, product_id):
    """
    Promedio aritmético de ``unit_cost`` en ``inventories_movements`` para el producto:
    ``SUM(unit_cost) / COUNT(*)`` entre movimientos de ese producto que **no** son salidas
    (tipos en ``AVERAGE_UNIT_COST_EXCLUDED_MOVEMENT_TYPE_IDS``: venta, salida).
    No pondera por ``quantity`` (cada fila cuenta una vez). Filas con ``unit_cost`` NULL se excluyen.
    Sin filas válidas → ``0``.
    """
    row = (
        db.query(
            func.coalesce(func.sum(InventoryMovementModel.unit_cost), 0),
            func.count(InventoryMovementModel.id),
        )
        .join(InventoryModel, InventoryModel.id == InventoryMovementModel.inventory_id)
        .filter(InventoryModel.product_id == product_id)
        .filter(InventoryMovementModel.unit_cost.isnot(None))
        .filter(
            ~InventoryMovementModel.movement_type_id.in_(
                AVERAGE_UNIT_COST_EXCLUDED_MOVEMENT_TYPE_IDS
            )
        )
        .first()
    )
    if not row:
        return 0
    total_uc, cnt = int(row[0] or 0), int(row[1] or 0)
    if cnt == 0:
        return 0
    return int(round(float(total_uc) / float(cnt)))


def sale_acceptance_unit_cost_from_movements(db, product_id) -> int:
    """
    Costo unitario de movimientos ligados a ventas, **solo** desde ``inventories_movements``:

    - **Aceptar pago** (``SaleClass.change_status``, ``status_id == 2``): salida de inventario.
    - **Reversa / devolución** (``SaleClass.reverse``): entrada que repone stock.

    En ambos casos usa ``average_unit_cost_for_product`` (media de ``unit_cost`` en entradas/ajustes,
    sin filas de salida tipo venta/salida);
    no se usa ``sales_products.price`` ni precio de lista del pedido para este valor.
    """
    return int(average_unit_cost_for_product(db, product_id))
