# Implementación de Descuento por Prepago en Templates

## Cambios realizados:

### 1. Modelo de base de datos
✅ **SettingModel**: Agregado campo `prepaid_discount = Column(Numeric(5, 2))`
✅ **Migración**: Creado `migration_add_prepaid_discount.sql`

### 2. Template Class
✅ **Imports**: Agregado `SettingModel` y `ShoppingModel` a los imports
✅ **Función helper**: Actualizada `calculate_shopping_totals()` con lógica de descuento
✅ **Templates**: Actualizados ambos métodos de generación de PDF

### 3. Lógica implementada

#### Detección de prepago:
```python
shopping = self.db.query(ShoppingModel).filter(ShoppingModel.id == shopping_id).first()
has_prepaid = shopping and shopping.prepaid_status_id is not None
```

#### Obtención del descuento:
```python
if has_prepaid:
    settings = self.db.query(SettingModel).first()
    if settings and hasattr(settings, 'prepaid_discount') and settings.prepaid_discount:
        prepaid_discount_percentage = float(settings.prepaid_discount)
```

#### Cálculo del total con descuento:
```python
if has_prepaid and prepaid_discount_percentage > 0:
    total_with_discount = total_without_discount * (1 - prepaid_discount_percentage / 100)
```

### 4. Templates actualizados

#### Sin prepago (comportamiento normal):
```
Total sin Descuento:
€. 1252
```

#### Con prepago (muestra ambos totales):
```
Total sin Descuento:
€. 1252

Total con Descuento (5%):
€. 1189,40
```

### 5. Archivos modificados:
- ✅ `app/backend/db/models.py` - Agregado campo prepaid_discount
- ✅ `app/backend/classes/template_class.py` - Lógica completa implementada

### 6. Archivos creados:
- ✅ `migration_add_prepaid_discount.sql` - Migración de base de datos
- ✅ `test_prepaid_discount.py` - Tests de verificación
- ✅ `verify_prepaid_discount.py` - Script de verificación

## Funcionalidades:

### ✅ Detección automática
- Verifica si `prepaid_status_id` existe en el shopping
- Solo muestra descuento cuando hay prepago

### ✅ Configuración flexible
- Descuento configurable desde settings
- Soporte para decimales (ej: 5.5%)
- Valor por defecto: 0.00%

### ✅ Presentación condicional
- Muestra "Total sin Descuento" siempre
- Muestra "Total con Descuento (X%)" solo si hay prepago
- Formato limpio sin decimales innecesarios

### ✅ Compatibilidad
- No afecta compras existentes sin prepago
- Retrocompatible con datos actuales
- Manejo seguro de valores nulos

## Pasos de implementación:

### 1. Migración de base de datos
```sql
ALTER TABLE settings ADD COLUMN prepaid_discount DECIMAL(5,2) DEFAULT 0.00;
```

### 2. Configurar descuento
- Ir a settings en el sistema
- Establecer valor de `prepaid_discount` (ej: 5.00 para 5%)

### 3. Crear compras con prepago
- Al crear shopping, asignar `prepaid_status_id`
- Los PDFs mostrarán automáticamente ambos totales

## Ejemplos de uso:

### Compra sin prepago:
```json
{
  "prepaid_status_id": null,
  "total": 1250.00
}
```
**Resultado**: Solo muestra "Total sin Descuento: €. 1250"

### Compra con prepago (descuento 5%):
```json
{
  "prepaid_status_id": 1,
  "total": 1250.00
}
```
**Resultado**: 
```
Total sin Descuento: €. 1250
Total con Descuento (5%): €. 1187,50
```

## Testing:

✅ **Lógica verificada**: Tests confirman cálculos correctos
✅ **Sintaxis validada**: Código sin errores
✅ **Compatibilidad**: Funciona con y sin prepago

## Beneficios:

- 🎯 **Automatización**: Calcula descuentos automáticamente
- 💰 **Transparencia**: Muestra ambos totales claramente  
- ⚙️ **Flexibilidad**: Descuento configurable
- 🔄 **Compatibilidad**: No rompe funcionalidad existente
