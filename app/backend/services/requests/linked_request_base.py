"""Base para módulos solicitud ↔ pedido ↔ inventario."""

from typing import Union

from app.backend.core.constants import RequestReasonPrefix
from app.backend.services.crud.base_domain_service import BaseDomainService
from app.backend.services.inventory.inventory_sale_bridge import InventorySaleBridge
from app.backend.services.requests.sale_linkage_service import SaleLinkageService


class LinkedRequestService(BaseDomainService):
    """
    Servicio base para Muestras, Ventas unitarias y Uso interno.
    Provee bridge de inventario y vinculación de pedidos.
    """

    reason_prefix: RequestReasonPrefix

    def __init__(self, db):
        super().__init__(db)
        self._inventory = InventorySaleBridge(db, self.reason_prefix.value)
        self._sale_linkage = SaleLinkageService(db, self._inventory)

    def _delete_linked_request(
        self,
        request,
        *,
        sale_unlink_mode: str = "hard_delete",
        check_folio: bool = True,
    ) -> Union[str, dict]:
        """Flujo estándar de eliminación con reversa de inventario."""
        sale_id = getattr(request, "sale_id", None)
        if sale_id:
            if check_folio:
                block = self._inventory.sale_delete_block_reason(sale_id)
                if block:
                    return {"status": "error", "message": block}
            self._inventory.reverse_sale_inventory(sale_id)

        self.db.delete(request)
        self.db.flush()

        if sale_id:
            self._inventory.unlink_sale(
                sale_id,
                mode=sale_unlink_mode,
                check_folio=False,
            )
        return "success"
