class DomainError(Exception):
    """Error de negocio esperado (stock, validación, reglas de dominio)."""

    def __init__(self, message: str):
        self.message = message
        super().__init__(message)


class ValidationError(DomainError):
    """Entrada inválida o datos incompletos."""
