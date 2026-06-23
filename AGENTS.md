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

## Convenciones de nombres (código en inglés)

| Ámbito | Idioma | Ejemplos |
|--------|--------|----------|
| **Funciones y métodos** | Inglés | `get_all`, `validate_stock`, `create_or_refresh` |
| **Variables y parámetros** | Inglés | `customer_id`, `shipping_method_id`, `movement_type` |
| **Rutas HTTP** (`routers/`) | Inglés, kebab o snake en path | `/internal-uses/store`, `/inventories/movements/{id}` |
| **Clases, módulos, archivos** | Inglés | `inventory_class.py`, `SaleLinkageService` |
| **Constantes / enums** | Inglés | `SaleStatus.DELIVERED`, `RequestReasonPrefix` |
| **Comentarios y docstrings** | Español o inglés (claridad) | — |
| **Mensajes al usuario / `reason` de negocio** | Español | `"Ajuste de inventario realizado."` |

**Prohibido en código nuevo:** identificadores en español (`obtenerCliente`, `metodo_envio`, `crearPresupuesto`).

**Legacy:** módulos antiguos pueden tener nombres mixtos; al tocarlos, renombrar solo si no rompe el contrato API ni el frontend.

## Checklist antes de commit

- [ ] ¿Leíste esta guía?
- [ ] ¿Reutilizaste `services/` / `core/`?
- [ ] ¿Router delgado?
- [ ] ¿Paginación con `list_query` o `paginate_query`?
- [ ] ¿Sin copiar bloques de inventario/pedido?
- [ ] ¿Funciones, variables y rutas nuevas en inglés?

## Migraciones de base de datos

Al agregar tablas o columnas nuevas, crear un script idempotente en `migrations/` y ejecutarlo **en local y en producción** antes de desplegar el backend.

```bash
cd backend

# Todas las migraciones pendientes
python migrations/run_all_migrations.py

# Solo módulo publicidad (campañas WhatsApp)
python migrations/run_advertising_migrations.py
```

| Script | Qué crea / actualiza |
|--------|----------------------|
| `run_add_promotion_audience.py` | `promotions.audience_type`, tabla `promotion_customers` |
| `run_add_sales_coupon_code.py` | `sales.coupon_code` |
| `run_add_advertising_campaigns.py` | `advertising_campaigns`, `advertising_campaign_customers` |
| `run_add_advertising_promotion_id.py` | `advertising_campaigns.promotion_id` |

Los scripts leen la conexión desde `.env` vía `SQLALCHEMY_DATABASE_URI`. Son idempotentes: si la tabla/columna ya existe, hacen `SKIP`.

**Producción:** conectar al servidor, activar el entorno del backend y ejecutar los mismos comandos contra la BD de producción antes de reiniciar la API.

## Campañas WhatsApp (plantillas Meta)

Fuera de la ventana de 24 h, Meta **no permite** mensajes interactivos libres (error `131047`). Las campañas de publicidad deben usar **plantillas MARKETING** aprobadas.

Crear en [Meta Business Manager](https://business.facebook.com/) → WhatsApp → Plantillas de mensajes:

### `product_discount_promotion` (promoción por producto)

| Campo | Valor |
|-------|--------|
| Categoría | Marketing |
| Idioma | Español |
| Nombre exacto en Meta | `product_discount_promotion` |
| Cuerpo | Ver texto fijo abajo con `{{1}}` `{{2}}` `{{3}}` |
| Botón | Ir a la promoción → URL `https://lacasadelvitrificado.com/{{1}}` |

Texto del cuerpo (3 variables):

```
🥳 ¡Nueva promoción! 🎉
📦 *Producto:* {{1}}
💰 *Descuento:* {{2}}
🗓️ *Vigencia:* {{3}}

Toca el botón *Ir a la promoción*.
```

El API envía: `{{1}}` = nombre producto, `{{2}}` = descuento (ej. `15%`), `{{3}}` = vigencia (ej. `01-06-2026 al 30-06-2026`).

### `campana_publicidad_v1` (cupón o mensaje libre, sin imagen)

| Campo | Valor |
|-------|--------|
| Categoría | Marketing |
| Idioma | Español |
| Cuerpo | `{{1}}` |
| Botón | Ir a la promoción → URL `https://lacasadelvitrificado.com/{{1}}` |

### `campana_publicidad_imagen_v1` (con imagen)

| Campo | Valor |
|-------|--------|
| Categoría | Marketing |
| Idioma | Español |
| Encabezado | Imagen |
| Cuerpo | `{{1}}` |
| Botón | Ir a la promoción → URL `https://lacasadelvitrificado.com/{{1}}` |

Variables de entorno opcionales:

```env
WHATSAPP_CAMPAIGN_TEMPLATE_PRODUCT_NAME=product_discount_promotion
WHATSAPP_CAMPAIGN_TEMPLATE_PRODUCT_IMAGE_NAME=product_discount_promotion
WHATSAPP_CAMPAIGN_TEMPLATE_NAME=campana_publicidad_v1
WHATSAPP_CAMPAIGN_TEMPLATE_IMAGE_NAME=campana_publicidad_imagen_v1
WHATSAPP_CAMPAIGN_TEMPLATE_LANG=es
WHATSAPP_CAMPAIGN_SITE_URL=https://lacasadelvitrificado.com
```

El botón recibe el sufijo dinámico generado por el backend, por ejemplo:

`shoppings/login?phone=56976357193&customer_id=12&token=...&product_id=45`

- **No** pegues la URL completa en Meta: solo `https://lacasadelvitrificado.com/{{1}}`.
- Si la campaña usa promoción **por producto**, se agrega `product_id` y el cliente entra directo a `/sales/product/detail/{id}`.
- Si es **cupón** o mensaje libre, va al listado de ventas (`/sales`).

Tras aprobar las plantillas en Meta, desplegar el backend y reiniciar `fastapi.service`.

## No editar

- `public/assets/classes/` (copia obsoleta)
- Migraciones ya aplicadas en producción
