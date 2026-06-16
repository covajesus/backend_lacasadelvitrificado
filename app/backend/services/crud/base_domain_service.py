"""Servicio base para clases de dominio (*Class)."""

from typing import Any, Callable, Optional, TypeVar, Union

from app.backend.core.exceptions import DomainError, ValidationError
from app.backend.core.pagination import fetch_all_or_paginated

T = TypeVar("T")


class BaseDomainService:
    """
    Clase base (Mixin) para orquestadores de dominio.
    Centraliza manejo de errores y listados paginados.
    """

    def __init__(self, db):
        self.db = db

    def safe(
        self,
        fn: Callable[[], Any],
        *,
        rollback: bool = False,
    ) -> Any:
        """Ejecuta lógica capturando errores en formato legacy del API."""
        try:
            return fn()
        except (ValueError, ValidationError, DomainError) as exc:
            if rollback:
                self.db.rollback()
            return {"status": "error", "message": getattr(exc, "message", str(exc))}
        except Exception as exc:
            if rollback:
                self.db.rollback()
            return {"status": "error", "message": str(exc)}

    def list_query(
        self,
        query,
        *,
        page: int = 0,
        items_per_page: int = 10,
        serialize_row: Callable[[T], Any],
        empty_message: str = "No data found",
    ) -> Union[list, dict]:
        """Wrapper de ``fetch_all_or_paginated`` con manejo de errores."""
        return self.safe(
            lambda: fetch_all_or_paginated(
                query,
                page=page,
                items_per_page=items_per_page,
                serialize_row=serialize_row,
                empty_message=empty_message,
            )
        )

    def list_wrapped(
        self,
        query,
        serialize_row: Callable[[T], dict],
    ) -> dict:
        """Patrón ``get_list`` → ``{"data": [...]}``."""
        return self.safe(lambda: {"data": [serialize_row(row) for row in query.all()]})

    def delete_entity(self, model, entity_id: int) -> Union[str, dict]:
        """Elimina por ID; mantiene contratos legacy (``success`` / ``No data found``)."""
        return self.safe(
            lambda: self._delete_entity(model, entity_id),
            rollback=True,
        )

    def _delete_entity(self, model, entity_id: int) -> str:
        row = self.db.query(model).filter(model.id == entity_id).first()
        if not row:
            return "No data found"
        self.db.delete(row)
        self.db.commit()
        return "success"

    def get_or_error(
        self,
        query_result,
        *,
        data_key: str,
        serialize: Callable[[Any], dict],
        not_found: str = "No se encontraron datos para el campo especificado.",
    ) -> dict:
        """Patrón ``get(id)`` con clave ``{data_key: {...}}`` o ``{"error": ...}``."""
        if query_result:
            return {data_key: serialize(query_result)}
        return {"error": not_found}
