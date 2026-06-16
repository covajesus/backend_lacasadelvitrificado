"""Utilidades compartidas para solicitudes con líneas (muestras, ventas, uso interno)."""

from typing import Any, Callable, Iterable


def summarize_items_by_unit(
    items: Iterable[Any],
    *,
    quantity_resolver: Callable[[Any], float],
    unit_measure_resolver: Callable[[Any], str] = lambda i: getattr(i, "unit_measure", None) or "u.",
) -> dict:
    """Agrega cantidades por unidad de medida para listados."""
    items = list(items)
    if not items:
        return {
            "items_count": 0,
            "total_quantity": 0,
            "quantity_label": "—",
        }

    by_unit = {}
    for item in items:
        unit = (unit_measure_resolver(item) or "").strip() or "u."
        amount = float(quantity_resolver(item) or 0)
        by_unit[unit] = by_unit.get(unit, 0) + amount

    parts = []
    for unit, total in by_unit.items():
        if total == int(total):
            parts.append(f"{int(total)} {unit}")
        else:
            parts.append(f"{total:g} {unit}")

    return {
        "items_count": len(items),
        "total_quantity": sum(by_unit.values()),
        "quantity_label": ", ".join(parts),
    }
