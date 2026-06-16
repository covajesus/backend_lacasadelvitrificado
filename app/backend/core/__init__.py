"""Núcleo transversal: constantes, excepciones y utilidades compartidas."""

from app.backend.core.constants import SaleStatus, RequestReasonPrefix
from app.backend.core.exceptions import DomainError, ValidationError
from app.backend.core.responses import error_payload, success_payload

__all__ = [
    "SaleStatus",
    "RequestReasonPrefix",
    "DomainError",
    "ValidationError",
    "error_payload",
    "success_payload",
]
