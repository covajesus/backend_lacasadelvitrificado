"""Helpers para routers FastAPI (capa API delgada)."""

from functools import wraps
from typing import Callable

from app.backend.core.exceptions import DomainError, ValidationError


def map_service_errors(func: Callable) -> Callable:
    """
    Decorador opcional para routers que llaman servicios con ``DomainError``.
    Mantiene compatibilidad con el contrato ``{"message": ...}`` existente.
    """

    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except (ValidationError, DomainError, ValueError) as exc:
            message = getattr(exc, "message", str(exc))
            return {"message": {"status": "error", "message": message}}

    return wrapper
