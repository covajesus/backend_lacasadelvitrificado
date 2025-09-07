# Script para verificar si existe el campo prepaid_discount en settings
# Si no existe, se debe agregar a la base de datos

print("Verificando estructura de la tabla settings...")

# Verificar el modelo actual
from app.backend.db.models import SettingModel

print("Campos actuales en SettingModel:")
for attr in dir(SettingModel):
    if not attr.startswith('_') and not callable(getattr(SettingModel, attr)):
        print(f"  - {attr}")

print("\nBuscando campo prepaid_discount...")
if hasattr(SettingModel, 'prepaid_discount'):
    print("✅ Campo prepaid_discount existe en el modelo")
else:
    print("❌ Campo prepaid_discount NO existe en el modelo")
    print("\n📝 Acción requerida:")
    print("   1. Agregar campo prepaid_discount a la tabla settings en la base de datos")
    print("   2. Agregar campo prepaid_discount al modelo SettingModel")
    print("\nSQL sugerido:")
    print("ALTER TABLE settings ADD COLUMN prepaid_discount DECIMAL(5,2) DEFAULT 0.00;")

print("\n✅ Verificación completada")
