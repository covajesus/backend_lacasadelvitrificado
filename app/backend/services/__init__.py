"""Capa de servicios de dominio (lógica reutilizable entre módulos)."""

from app.backend.services.inventory.inventory_sale_bridge import InventorySaleBridge, SaleDeductionLine
from app.backend.services.requests.sale_linkage_service import SaleLinkageService
from app.backend.services.requests.item_summary import summarize_items_by_unit

__all__ = [
    "InventorySaleBridge",
    "SaleDeductionLine",
    "SaleLinkageService",
    "summarize_items_by_unit",
]
