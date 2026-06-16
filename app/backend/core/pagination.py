"""Utilidades de paginación para listados del ERP."""

from typing import Any, Callable, TypeVar, Union

T = TypeVar("T")


def paginate_query(
    query,
    *,
    page: int,
    items_per_page: int,
    serialize_row: Callable[[T], dict],
    empty_message: str = "No data found",
) -> dict:
    """Pagina un query SQLAlchemy y serializa cada fila."""
    total_items = query.count()
    total_pages = max((total_items + items_per_page - 1) // items_per_page, 1)

    if page < 1 or page > total_pages:
        return {"status": "error", "message": "Invalid page number"}

    rows = query.offset((page - 1) * items_per_page).limit(items_per_page).all()
    if not rows:
        return {"status": "error", "message": empty_message}

    return {
        "total_items": total_items,
        "total_pages": total_pages,
        "current_page": page,
        "items_per_page": items_per_page,
        "data": [serialize_row(row) for row in rows],
    }


def fetch_all_or_paginated(
    query,
    *,
    page: int = 0,
    items_per_page: int = 10,
    serialize_row: Callable[[T], Any],
    empty_message: str = "No data found",
) -> Union[list, dict]:
    """
    Si ``page > 0`` devuelve dict paginado; si no, lista serializada completa.
    Usado por casi todos los ``get_all`` legacy del ERP.
    """
    if page > 0:
        return paginate_query(
            query,
            page=page,
            items_per_page=items_per_page,
            serialize_row=serialize_row,
            empty_message=empty_message,
        )
    return [serialize_row(row) for row in query.all()]
