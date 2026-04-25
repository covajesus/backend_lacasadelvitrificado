import argparse
import re
from typing import Optional, Tuple

from app.backend.db.database import SessionLocal
from app.backend.db.models import InventoryModel, InventoryMovementModel, UnitFeatureModel

SALE_REASON_RE = re.compile(r"^(Venta(?: desde presupuesto)?)\|base=(\d+)\|pkgo=([0-9]+(?:\.[0-9]+)?)$")


def _parse_sale_reason(reason: Optional[str]) -> Optional[Tuple[str, int, float]]:
    if not reason:
        return None
    m = SALE_REASON_RE.match(reason.strip())
    if not m:
        return None
    return m.group(1), int(m.group(2)), float(m.group(3))


def _quantity_per_package(db, product_id: int) -> int:
    q = (
        db.query(UnitFeatureModel.quantity_per_package)
        .filter(UnitFeatureModel.product_id == product_id)
        .scalar()
    )
    try:
        n = int(q)
    except (TypeError, ValueError):
        return 1
    return n if n > 0 else 1


def _packages_from_base(base_units: int, qpp: int) -> float:
    if base_units <= 0:
        return 0.0
    if qpp <= 1:
        return float(base_units)
    return float(base_units) / float(qpp)


def _format_packages(value: float) -> str:
    txt = f"{value:.4f}".rstrip("0").rstrip(".")
    return txt if txt else "0"


def _forced_reason_markers(base_units: int, qpp: int) -> tuple[str, str]:
    if base_units <= 0:
        return "0", "0"
    if qpp <= 1:
        return str(base_units), str(base_units)
    if base_units % qpp != 0:
        return str(qpp), "1"
    return str(base_units), _format_packages(_packages_from_base(base_units, qpp))


def _forced_quantity(base_units: int, original_quantity: int, qpp: int) -> int:
    """
    Si el movimiento de salida no es múltiplo del paquete, forzar cantidad al paquete completo
    manteniendo el signo original. Ej.: -6/-4 -> -5 (cuando qpp=5).
    """
    if qpp <= 1:
        return int(original_quantity)
    if base_units <= 0:
        return int(original_quantity)
    if base_units % qpp == 0:
        return int(original_quantity)
    sign = -1 if int(original_quantity) < 0 else 1
    return sign * int(qpp)


def fix_sale_movement_reasons(apply: bool) -> int:
    db = SessionLocal()
    updated = 0
    scanned = 0
    try:
        rows = (
            db.query(
                InventoryMovementModel.id,
                InventoryMovementModel.inventory_id,
                InventoryMovementModel.quantity,
                InventoryMovementModel.reason,
                InventoryModel.product_id,
            )
            .join(InventoryModel, InventoryModel.id == InventoryMovementModel.inventory_id)
            .filter(InventoryMovementModel.movement_type_id == 2)
            .all()
        )

        for row in rows:
            parsed = _parse_sale_reason(row.reason)
            if parsed is None:
                continue
            scanned += 1
            prefix = parsed[0]

            base_units = abs(int(row.quantity or 0))
            if base_units <= 0:
                continue

            qpp = _quantity_per_package(db, int(row.product_id))
            forced_base, forced_pkgo = _forced_reason_markers(base_units, qpp)
            new_reason = f"{prefix}|base={forced_base}|pkgo={forced_pkgo}"
            new_quantity = _forced_quantity(base_units, int(row.quantity or 0), qpp)
            if new_reason == (row.reason or "") and int(new_quantity) == int(row.quantity or 0):
                continue

            updated += 1
            print(
                f"[FIX] movement_id={row.id} product_id={row.product_id} "
                f"old_qty={row.quantity} new_qty={new_quantity} "
                f"old='{row.reason}' new='{new_reason}'"
            )
            if apply:
                (
                    db.query(InventoryMovementModel)
                    .filter(InventoryMovementModel.id == row.id)
                    .update(
                        {"reason": new_reason, "quantity": int(new_quantity)},
                        synchronize_session=False,
                    )
                )

        if apply:
            db.commit()
        else:
            db.rollback()

        mode = "APPLY" if apply else "DRY-RUN"
        print(f"[{mode}] scanned={scanned} updated={updated}")
        return updated
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Fix inventories_movements.reason for sale exits using quantity_per_package and linked sale_products."
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Persist changes. Without this flag, runs in dry-run mode.",
    )
    args = parser.parse_args()
    fix_sale_movement_reasons(apply=args.apply)
