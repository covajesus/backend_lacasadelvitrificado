# Guía del backend — La Casa del Vitrificado

> **OBLIGATORIO:** Lee este archivo **antes** de modificar cualquier código en `backend/`.
> La regla Cursor `.cursor/rules/backend-enterprise.mdc` se activa al editar `backend/**/*.py`.

## Arquitectura por capas

```
Router (delgado)  →  *Class (orquestador)  →  services/  →  db / sale_class (infra)
```

| Capa | Ubicación | Responsabilidad |
|------|-----------|-----------------|
| **API** | `routers/` | HTTP, auth, `return {"message": ...}` |
| **Dominio** | `classes/*_class.py` | Casos de uso por módulo; **sin lógica duplicada** |
| **Servicios** | `services/` | Lógica reutilizable entre módulos |
| **Core** | `core/` | Constantes, paginación, roles, excepciones |
| **Infra** | `db/`, `sale_class.py`, `inventory_stock.py` | ORM, FIFO, SQL complejo |

Documentación: [`docs/architecture.md`](docs/architecture.md).

## Servicios disponibles (reutilizar siempre)

| Servicio | Ruta | Uso |
|----------|------|-----|
| `BaseDomainService` | `services/crud/base_domain_service.py` | `list_query`, `safe`, `delete_entity`, `get_or_error` |
| `LinkedRequestService` | `services/requests/linked_request_base.py` | Muestras, ventas unitarias, uso interno |
| `InventorySaleBridge` | `services/inventory/inventory_sale_bridge.py` | Stock, reversa, descuento inventario |
| `SaleLinkageService` | `services/requests/sale_linkage_service.py` | Crear/actualizar pedido vinculado |
| `summarize_items_by_unit` | `services/requests/item_summary.py` | Resumen cantidades en listados |
| `paginate_query` / `fetch_all_or_paginated` | `core/pagination.py` | Listados paginados |
| `apply_customer_rut_scope` | `core/role_access.py` | Filtro por RUT según rol |
| `SimpleFacturaClient` | `services/integrations/simplefactura_client.py` | API facturación |

## Patrones de diseño

| Patrón | Implementación |
|--------|----------------|
| **Thin Controller** | Routers solo delegan |
| **Facade** | `InventorySaleBridge` |
| **Template Method** | `SaleLinkageService.create_or_refresh` |
| **Value Object** | `SaleDeductionLine` |
| **Strategy** | Resolvers en `validate_stock`, serializers |
| **Repository-lite** | `BaseDomainService.list_query` |

## Cómo crear o refactorizar un módulo

### CRUD simple (categorías, ubicaciones, proveedores…)

```python
from app.backend.services.crud.base_domain_service import BaseDomainService

class FooClass(BaseDomainService):
    @staticmethod
    def _serialize_row(row): ...

    def get_all(self, page=0, items_per_page=10):
        query = self.db.query(...).order_by(...)
        return self.list_query(query, page=page, items_per_page=items_per_page, serialize_row=self._serialize_row)
```

### Solicitud → pedido → inventario

```python
class FooClass(LinkedRequestService):
    reason_prefix = RequestReasonPrefix.XXX
    # self._inventory y self._sale_linkage ya inicializados
```

### Errores

- Negocio: `ValidationError` o `ValueError`
- Captura en class: `except (ValueError, ValidationError)`
- Respuesta API: `{"status": "error", "message": "..."}`

## Estado del refactor

| Estado | Módulos |
|--------|---------|
| **Completo** | category, location, unit_measure, supplier, region, commune, movement_type, rol, setting, user, supplier_category, customer (listado), sample, unit_sale, internal_use |
| **Paginación corregida** | sale, product, inventory, kardex, budget, shopping, employee |
| **Pendiente descomposición** | sale_class, whatsapp_class, shopping_class, product_class, template_class, budget_class, inventory_class, dte_class, authentication_class |

Los módulos pendientes mantienen contrato API; la migración es incremental hacia `services/`.

## Convenciones API (no romper frontend)

```python
return {"message": SomeClass(db).method(...)}
# Éxito: "success" o dict
# Error: {"status": "error", "message": "..."}
```

## Checklist antes de commit

- [ ] ¿Leíste esta guía?
- [ ] ¿Reutilizaste `services/` / `core/`?
- [ ] ¿Router delgado?
- [ ] ¿Paginación con `list_query` o `paginate_query`?
- [ ] ¿Sin copiar bloques de inventario/pedido?

## No editar

- `public/assets/classes/` (copia obsoleta)
- Migraciones ya aplicadas en producción
