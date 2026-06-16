"""Filtros de acceso por rol reutilizables en listados."""

from typing import Any, Optional


def is_restricted_customer_role(rol_id: Optional[int]) -> bool:
    """Rol 5 (cliente) no debe ver listados internos de solicitudes."""
    return rol_id == 5


def apply_customer_rut_scope(
    query,
    model,
    *,
    rol_id: Optional[int],
    user_rut: Optional[str],
    admin_roles: tuple = (1, 2, 6),
    rut_field: str = "customer_rut",
):
    """Restringe query al RUT del usuario si no es rol administrador."""
    if rol_id not in admin_roles and user_rut:
        return query.filter(getattr(model, rut_field) == str(user_rut).strip())
    return query
