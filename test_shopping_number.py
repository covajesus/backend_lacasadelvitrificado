# Test script para verificar que el campo shopping_number funciona correctamente

from app.backend.schemas import ShoppingCreateInput, UpdateShopping, ShoppingProductInput
from typing import List

# Ejemplo de datos de prueba con shopping_number
sample_product = ShoppingProductInput(
    product_id=1,
    unit_measure_id=1,
    quantity=10,
    quantity_per_package=25.5,
    original_unit_cost=100.0,
    discount_percentage=5.0,
    final_unit_cost=95.0,
    amount=950.0,
    category_id=1
)

# Test para ShoppingCreateInput
create_shopping_data = ShoppingCreateInput(
    shopping_number="SP-2025-001",
    products=[sample_product],
    total=950.0,
    email="test@example.com",
    supplier_id=1,
    prepaid_status_id=1,
    second_email="second@example.com",
    third_email="third@example.com"
)

# Test para UpdateShopping
update_shopping_data = UpdateShopping(
    shopping_number="SP-2025-001-UPDATED",
    products=[sample_product],
    total=950.0,
    email="test@example.com",
    supplier_id=1,
    prepaid_status_id=1,
    second_email="second@example.com",
    third_email="third@example.com"
)

print("✅ ShoppingCreateInput con shopping_number:", create_shopping_data.shopping_number)
print("✅ UpdateShopping con shopping_number:", update_shopping_data.shopping_number)
print("✅ Schemas actualizados correctamente!")

# Verificar que shopping_number es opcional
create_shopping_without_number = ShoppingCreateInput(
    products=[sample_product],
    total=950.0,
    email="test@example.com",
    supplier_id=1
)

print("✅ ShoppingCreateInput sin shopping_number (opcional):", create_shopping_without_number.shopping_number)
print("✅ Todos los tests pasaron correctamente!")
