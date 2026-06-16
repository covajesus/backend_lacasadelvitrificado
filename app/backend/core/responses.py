from typing import Any, Optional, Union


def success_payload(data: Any = "success") -> Any:
    """Respuesta estándar de éxito para capa router → ``{"message": data}``."""
    return data


def error_payload(message: str, *, status: str = "error") -> dict:
    """Respuesta estándar de error para servicios."""
    return {"status": status, "message": message}


def service_result(
    value: Any,
    *,
    error: Optional[Exception] = None,
) -> Union[str, dict]:
    """
    Normaliza retorno de servicios legacy.
    - Éxito: ``"success"`` o dict de datos.
    - ``DomainError`` / ``ValueError``: ``{"status": "error", "message": ...}``.
    """
    if error is not None:
        if isinstance(error, ValueError):
            return error_payload(str(error))
        if hasattr(error, "message"):
            return error_payload(error.message)
        return error_payload(str(error))
    return value
