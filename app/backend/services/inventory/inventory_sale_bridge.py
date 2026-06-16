from dataclasses import dataclass
from decimal import Decimal, ROUND_HALF_UP
from typing import Any, Callable, Iterable, Optional

from app.backend.classes.sale_class import SaleClass, _inventory_movement_added_at
from app.backend.classes.inventory_stock import (
    stock_sum_for_product,
    sale_acceptance_unit_cost_from_movements,
)
from app.backend.core.constants import SaleStatus
from app.backend.core.exceptions import ValidationError
from app.backend.db.models import (
    SaleModel,
    SaleProductModel,
    InventoryModel,
    InventoryMovementModel,
)


@dataclass(frozen=True)
class SaleDeductionLine:
    """Value Object: una línea a descontar de inventario y reflejar en ``sales_products``."""

    product_id: int
    inventory_base_units: int
    line_price: int
    sale_product_quantity: int = 1


class InventorySaleBridge:
    """
    Servicio compartido (Strategy + Facade) para:
    - validar stock
    - revertir salidas de inventario
    - descontar inventario al vincular un pedido
    - eliminar o rechazar pedidos vinculados

    Usado por Muestras, Ventas Unitarias y Uso Interno.
    """

    def __init__(self, db, reason_prefix: str):
        self.db = db
        self.reason_prefix = reason_prefix
        self._sale_helper = SaleClass(db)

    @staticmethod
    def inventory_units(unit_quantity) -> int:
        d = Decimal(str(unit_quantity))
        if d <= 0:
            return 0
        return int(d.quantize(Decimal("1"), rounding=ROUND_HALF_UP))

    def validate_stock(
        self,
        items: Iterable[Any],
        *,
        base_units_resolver: Callable[[Any], int],
        product_id_resolver: Callable[[Any], int] = lambda i: i.product_id,
        name_resolver: Callable[[Any], str] = lambda i: i.product_name,
        unit_measure_resolver: Callable[[Any], str] = lambda i: getattr(i, "unit_measure", None) or "u.",
    ) -> None:
        for item in items:
            base_units = base_units_resolver(item)
            if base_units <= 0:
                continue
            product_id = product_id_resolver(item)
            available = stock_sum_for_product(self.db, product_id)
            if available < base_units:
                unit = unit_measure_resolver(item)
                name = name_resolver(item)
                raise ValidationError(
                    f"Stock insuficiente para {name}. "
                    f"Disponible: {available} {unit}, solicitado: {base_units} {unit}."
                )

    def reverse_sale_inventory(self, sale_id: int) -> None:
        processed_movement_ids = set()

        sales_products = (
            self.db.query(SaleProductModel).filter(SaleProductModel.sale_id == sale_id).all()
        )
        for sales_product in sales_products:
            if not sales_product.inventory_movement_id:
                continue
            inventory_movement = (
                self.db.query(InventoryMovementModel)
                .filter(InventoryMovementModel.id == sales_product.inventory_movement_id)
                .first()
            )
            if not inventory_movement:
                continue

            processed_movement_ids.add(inventory_movement.id)
            self._reverse_inventory_movement(sale_id, sales_product.product_id, inventory_movement)

        exit_movements = (
            self.db.query(InventoryMovementModel)
            .filter(
                InventoryMovementModel.reason.like(f"{self.reason_prefix}|sale_id={sale_id}|%"),
                InventoryMovementModel.movement_type_id == 2,
            )
            .all()
        )
        for inventory_movement in exit_movements:
            if inventory_movement.id in processed_movement_ids:
                continue
            product_id = self._product_id_from_inventory_movement(inventory_movement)
            if not product_id:
                continue
            self._reverse_inventory_movement(sale_id, product_id, inventory_movement)

        self.db.query(SaleProductModel).filter(SaleProductModel.sale_id == sale_id).delete()
        self.db.flush()

    def deduct_lines(self, sale_id: int, lines: Iterable[SaleDeductionLine]) -> None:
        for line in lines:
            if line.inventory_base_units <= 0:
                continue

            movement_unit_cost = sale_acceptance_unit_cost_from_movements(self.db, line.product_id)
            main_movement, exit_error = self._sale_helper._create_consolidated_sale_inventory_exit(
                sale_id,
                line.product_id,
                line.inventory_base_units,
                movement_unit_cost,
                reason_prefix=self.reason_prefix,
            )
            if exit_error:
                raise ValidationError(exit_error)

            inventory = (
                self.db.query(InventoryModel)
                .filter(InventoryModel.id == main_movement.inventory_id)
                .first()
            )

            self.db.add(
                SaleProductModel(
                    sale_id=sale_id,
                    product_id=line.product_id,
                    inventory_movement_id=main_movement.id,
                    inventory_id=inventory.id if inventory else None,
                    lot_item_id=main_movement.lot_item_id,
                    quantity=line.sale_product_quantity,
                    price=line.line_price,
                )
            )

        self.db.flush()

    def unlink_sale(
        self,
        sale_id: int,
        *,
        mode: str = "hard_delete",
        check_folio: bool = True,
    ) -> Optional[str]:
        """
        Desvincula pedido tras revertir inventario.
        - ``hard_delete``: borra fila en ``sales`` (ventas unitarias, uso interno).
        - ``soft_reject``: ``status_id = 3`` (muestras).
        Retorna mensaje de error o ``None`` si OK. No hace commit.
        Llame ``sale_delete_block_reason`` antes si necesita validar sin borrar.
        """
        block = self.sale_delete_block_reason(sale_id) if check_folio else None
        if block:
            return block

        sale = self.db.query(SaleModel).filter(SaleModel.id == sale_id).first()
        if not sale:
            return None

        if mode == "soft_reject":
            sale.status_id = SaleStatus.REJECTED
            sale.updated_date = _inventory_movement_added_at()
            return None

        self.db.delete(sale)
        return None

    def sale_delete_block_reason(self, sale_id: int) -> Optional[str]:
        """Retorna mensaje si el pedido no puede eliminarse (p. ej. DTE emitido)."""
        sale = self.db.query(SaleModel).filter(SaleModel.id == sale_id).first()
        if sale and sale.folio:
            return "No se puede eliminar: el pedido tiene DTE generado."
        return None

    def _product_id_from_inventory_movement(self, inventory_movement) -> Optional[int]:
        inv = (
            self.db.query(InventoryModel)
            .filter(InventoryModel.id == inventory_movement.inventory_id)
            .first()
        )
        return inv.product_id if inv else None

    def _reverse_inventory_movement(self, sale_id: int, product_id: int, inventory_movement) -> None:
        reverse_marker = (
            f"Reversa {self.reason_prefix}|sale_id={sale_id}|movement_id={inventory_movement.id}"
        )
        already_reversed = (
            self.db.query(InventoryMovementModel.id)
            .filter(InventoryMovementModel.reason == reverse_marker)
            .first()
        )
        if already_reversed:
            return

        reverse_quantity = self._sale_helper._sale_movement_reverse_base_units(
            sale_id,
            SaleProductModel(product_id=product_id),
            inventory_movement,
        )
        if reverse_quantity <= 0:
            reverse_quantity = abs(int(inventory_movement.quantity or 0))
        if reverse_quantity <= 0:
            return

        return_uc = sale_acceptance_unit_cost_from_movements(self.db, product_id)
        self.db.add(
            InventoryMovementModel(
                inventory_id=inventory_movement.inventory_id,
                lot_item_id=inventory_movement.lot_item_id,
                movement_type_id=1,
                quantity=reverse_quantity,
                unit_cost=return_uc,
                reason=reverse_marker,
                added_date=_inventory_movement_added_at(),
            )
        )
        self._sale_helper._reverse_fifo_lot_consumptions(sale_id, product_id)
