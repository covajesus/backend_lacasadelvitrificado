"""Servicios de vinculación solicitud ↔ pedido."""

from datetime import datetime
from decimal import Decimal
from typing import Any, Callable, Iterable, Optional

from app.backend.core.constants import SaleStatus
from app.backend.core.exceptions import ValidationError
from app.backend.db.models import SaleModel
from app.backend.services.inventory.inventory_sale_bridge import InventorySaleBridge, SaleDeductionLine


class SaleLinkageService:
    """
    Template Method para crear o actualizar un ``SaleModel`` vinculado a una solicitud.
    La validación de stock debe ejecutarse antes de llamar a este servicio.
    """

    def __init__(self, db, inventory_bridge: InventorySaleBridge):
        self.db = db
        self.inventory_bridge = inventory_bridge

    def create_or_refresh(
        self,
        request: Any,
        *,
        customer_id: int,
        delivery_address: str,
        subtotal: Decimal,
        tax: Decimal,
        total: Decimal,
        deduction_lines: Iterable[SaleDeductionLine],
        persist_totals: Optional[Callable[[Any, Decimal, Decimal, Decimal], None]] = None,
    ) -> int:
        if not customer_id:
            raise ValidationError("Cliente inválido para generar el pedido.")

        now = datetime.now()
        if persist_totals:
            persist_totals(request, subtotal, tax, total)

        sale_id = getattr(request, "sale_id", None)
        if sale_id:
            sale = self.db.query(SaleModel).filter(SaleModel.id == sale_id).first()
            if sale:
                self.inventory_bridge.reverse_sale_inventory(sale.id)
                self._apply_sale_fields(
                    sale, customer_id, delivery_address, subtotal, tax, total, now
                )
                self.inventory_bridge.deduct_lines(sale.id, deduction_lines)
                return sale.id

        new_sale = SaleModel(
            customer_id=customer_id,
            shipping_method_id=1,
            dte_type_id=2,
            dte_status_id=2,
            status_id=SaleStatus.DELIVERED,
            subtotal=int(subtotal),
            tax=int(tax),
            shipping_cost=0,
            total=int(total),
            payment_support=None,
            delivery_address=delivery_address,
            added_date=now,
            updated_date=now,
        )
        self.db.add(new_sale)
        self.db.flush()

        self.inventory_bridge.deduct_lines(new_sale.id, deduction_lines)
        request.sale_id = new_sale.id
        return new_sale.id

    @staticmethod
    def _apply_sale_fields(sale, customer_id, delivery_address, subtotal, tax, total, now):
        sale.customer_id = customer_id
        sale.delivery_address = delivery_address
        sale.subtotal = int(subtotal)
        sale.tax = int(tax)
        sale.shipping_cost = 0
        sale.total = int(total)
        sale.status_id = SaleStatus.DELIVERED
        sale.updated_date = now
