from decimal import Decimal
from enum import Enum


class SaleStatus:
    """IDs de estado en tabla ``sales``."""

    PAYMENT_REVIEW = 1
    IN_PROCESS = 2
    REJECTED = 3
    DELIVERED = 4


class RequestReasonPrefix(str, Enum):
    """Prefijo en ``inventories_movements.reason`` y dirección de pedido."""

    SAMPLE = "Muestra"
    UNIT_SALE = "Venta unitaria"
    INTERNAL_USE = "Uso interno"


class TaxPolicy:
    """Política de IVA para pedidos vinculados a solicitudes."""

    UNIT_SALE_RATE = Decimal("0.19")
    ZERO = Decimal("0")
