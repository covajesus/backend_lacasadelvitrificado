"""Servicios de vinculación solicitud ↔ pedido."""

from datetime import datetime
from decimal import Decimal
from typing import Any, Callable, Iterable, Optional, Union

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
        dte_type_id: int = 2,
        dte_status_id: int = 2,
        status_id: int = SaleStatus.DELIVERED,
        shipping_method_id: int = 1,
        shipping_cost: Union[Decimal, int] = 0,
    ) -> int:
        if not customer_id:
            raise ValidationError("Cliente inválido para generar el pedido.")

        now = datetime.now()
        if persist_totals:
            persist_totals(request, subtotal, tax, total)

        sale_status = int(status_id or SaleStatus.DELIVERED)
        method_id = int(shipping_method_id or 1)
        cost = int(Decimal(str(shipping_cost or 0)))
        sale_id = getattr(request, "sale_id", None)
        if sale_id:
            sale = self.db.query(SaleModel).filter(SaleModel.id == sale_id).first()
            if sale:
                self.inventory_bridge.reverse_sale_inventory(sale.id)
                self._apply_sale_fields(
                    sale,
                    customer_id,
                    delivery_address,
                    subtotal,
                    tax,
                    total,
                    now,
                    dte_type_id=dte_type_id,
                    dte_status_id=dte_status_id,
                    status_id=sale_status,
                    shipping_method_id=method_id,
                    shipping_cost=cost,
                )
                self.inventory_bridge.deduct_lines(sale.id, deduction_lines)
                return sale.id

        new_sale = SaleModel(
            customer_id=customer_id,
            shipping_method_id=method_id,
            dte_type_id=int(dte_type_id),
            dte_status_id=int(dte_status_id),
            status_id=sale_status,
            subtotal=int(subtotal),
            tax=int(tax),
            shipping_cost=cost,
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
    def _apply_sale_fields(
        sale,
        customer_id,
        delivery_address,
        subtotal,
        tax,
        total,
        now,
        *,
        dte_type_id: int = 2,
        dte_status_id: int = 2,
        status_id: int = SaleStatus.DELIVERED,
        shipping_method_id: int = 1,
        shipping_cost: int = 0,
    ):
        sale.customer_id = customer_id
        sale.delivery_address = delivery_address
        sale.subtotal = int(subtotal)
        sale.tax = int(tax)
        sale.shipping_method_id = int(shipping_method_id or 1)
        sale.shipping_cost = int(shipping_cost or 0)
        sale.total = int(total)
        sale.dte_type_id = int(dte_type_id)
        sale.dte_status_id = int(dte_status_id)
        sale.status_id = int(status_id)
        sale.updated_date = now
