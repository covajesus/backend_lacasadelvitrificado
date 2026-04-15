"""One-off: print average unit_cost detail for a product (run from backend/)."""
from app.backend.db.database import SessionLocal
from app.backend.db.models import InventoryModel, InventoryMovementModel
from app.backend.classes.inventory_stock import (
    AVERAGE_UNIT_COST_EXCLUDED_MOVEMENT_TYPE_IDS,
    average_unit_cost_for_product,
)


def main():
    pid = 5
    db = SessionLocal()
    rows = (
        db.query(
            InventoryMovementModel.id,
            InventoryMovementModel.inventory_id,
            InventoryMovementModel.lot_item_id,
            InventoryMovementModel.movement_type_id,
            InventoryMovementModel.quantity,
            InventoryMovementModel.unit_cost,
            InventoryMovementModel.reason,
        )
        .join(InventoryModel, InventoryModel.id == InventoryMovementModel.inventory_id)
        .filter(InventoryModel.product_id == pid)
        .order_by(InventoryMovementModel.id.asc())
        .all()
    )

    print("=== Producto ID", pid, "===")
    print(
        "Movimientos (orden por id); promedio: unit_cost NOT NULL y tipo NO en salidas",
        AVERAGE_UNIT_COST_EXCLUDED_MOVEMENT_TYPE_IDS,
        "(venta/salida)",
    )
    hdr = f"{'id':>6} {'inv':>4} {'lot':>5} {'tipo':>4} {'qty':>6} {'unit_cost':>10}  motivo"
    print(hdr)
    print("-" * len(hdr))
    total = 0
    n = 0
    for r in rows:
        uc = r.unit_cost
        reason = (r.reason or "")[:55]
        lot = r.lot_item_id if r.lot_item_id is not None else 0
        mtid = r.movement_type_id or 0
        if uc is None:
            print(
                f"{r.id:6d} {r.inventory_id:4d} {lot:5d} {mtid:4d} {r.quantity:6d} {'(NULL)':>10}  {reason}"
            )
            continue
        in_avg = mtid not in AVERAGE_UNIT_COST_EXCLUDED_MOVEMENT_TYPE_IDS
        tag = "" if in_avg else "  [excl. salida]"
        if in_avg:
            total += int(uc)
            n += 1
        print(
            f"{r.id:6d} {r.inventory_id:4d} {lot:5d} {mtid:4d} {r.quantity:6d} {int(uc):10d}  {reason}{tag}"
        )

    print("-" * len(hdr))
    print("Registros con unit_cost (n):", n)
    print("Suma unit_cost:", total)
    manual = int(round(total / n)) if n else 0
    print("Promedio sum/n:", manual)
    avg = average_unit_cost_for_product(db, pid)
    print("average_unit_cost_for_product(db, %d): %s" % (pid, avg))
    db.close()


if __name__ == "__main__":
    main()
