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

# Tipos de movimiento que cuentan como **entrada** de inventario para costo medio (kardex):
# 1 = alta / compra / ingreso típico; 4 = ajuste de entrada (ver ``InventoryClass``).
INBOUND_MOVEMENT_TYPE_IDS = (1, 4)

# Entradas creadas en ``InventoryClass.store`` (texto exacto en ``reason``).
INVENTORY_ADD_ENTRY_REASONS = (
    "Agregado producto al inventario.",
    "Creación de inventario y lote.",
    "Agregado lote a inventario existente.",
)


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


def last_add_entry_unit_cost_for_inventory_lot(db, inventory_id, lot_item_id):
    """
    ``unit_cost`` del **último** movimiento de entrada (tipos 1 o 4) con motivo de alta de
    producto/lote (mismos textos que ``InventoryClass``), para ``inventory_id`` + ``lot_item_id``.
    Orden: ``added_date`` descendente, luego ``id``. Sin fila útil → ``0``.
    """
    try:
        iid = int(inventory_id)
        lid = int(lot_item_id)
    except (TypeError, ValueError):
        return 0
    if iid < 1 or lid < 1:
        return 0
    row = (
        db.query(InventoryMovementModel.unit_cost)
        .filter(InventoryMovementModel.inventory_id == iid)
        .filter(InventoryMovementModel.lot_item_id == lid)
        .filter(InventoryMovementModel.quantity > 0)
        .filter(InventoryMovementModel.movement_type_id.in_(INBOUND_MOVEMENT_TYPE_IDS))
        .filter(InventoryMovementModel.reason.in_(INVENTORY_ADD_ENTRY_REASONS))
        .order_by(InventoryMovementModel.added_date.desc(), InventoryMovementModel.id.desc())
        .first()
    )
    if not row or row[0] is None:
        return 0
    return int(row[0])


def average_unit_cost_for_product(db, product_id):
    """
    Costo medio unitario del saldo actual (CLP), ponderado por capa (inventario + lote).
    Solo considera movimientos de **entrada** (``movement_type_id`` en ``INBOUND_MOVEMENT_TYPE_IDS``)
    con cantidad > 0: de ellos toma el último por capa para fijar el ``unit_cost`` de esa capa
    (criterio tipo kardex, sin mezclar salidas/ventas).
    """
    latest_pos = (
        db.query(
            InventoryMovementModel.inventory_id.label("iid"),
            InventoryMovementModel.lot_item_id.label("lid"),
            func.max(InventoryMovementModel.id).label("max_id"),
        )
        .join(InventoryModel, InventoryModel.id == InventoryMovementModel.inventory_id)
        .filter(InventoryModel.product_id == product_id)
        .filter(InventoryMovementModel.quantity > 0)
        .filter(InventoryMovementModel.movement_type_id.in_(INBOUND_MOVEMENT_TYPE_IDS))
        .group_by(InventoryMovementModel.inventory_id, InventoryMovementModel.lot_item_id)
        .subquery()
    )
    costs = (
        db.query(
            latest_pos.c.iid,
            latest_pos.c.lid,
            InventoryMovementModel.unit_cost,
        )
        .join(InventoryMovementModel, InventoryMovementModel.id == latest_pos.c.max_id)
        .subquery()
    )
    bal = (
        db.query(
            InventoryMovementModel.inventory_id.label("iid"),
            InventoryMovementModel.lot_item_id.label("lid"),
            func.coalesce(func.sum(InventoryMovementModel.quantity), 0).label("balance"),
        )
        .join(InventoryModel, InventoryModel.id == InventoryMovementModel.inventory_id)
        .filter(InventoryModel.product_id == product_id)
        .group_by(InventoryMovementModel.inventory_id, InventoryMovementModel.lot_item_id)
        .subquery()
    )
    row = (
        db.query(
            func.coalesce(func.sum(bal.c.balance * func.coalesce(costs.c.unit_cost, 0)), 0),
            func.coalesce(func.sum(bal.c.balance), 0),
        )
        .select_from(bal)
        .outerjoin(
            costs,
            (costs.c.iid == bal.c.iid) & (costs.c.lid == bal.c.lid),
        )
        .filter(bal.c.balance > 0)
        .first()
    )
    if not row:
        return 0
    val, qty = (row[0] or 0), (row[1] or 0)
    if qty == 0:
        return 0
    return int(round(float(val) / float(qty)))
