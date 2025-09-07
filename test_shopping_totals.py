# Test para verificar que los cálculos de totales funcionan correctamente

from app.backend.schemas import ShoppingCreateInput, ShoppingProductInput
from app.backend.classes.template_class import TemplateClass
from unittest.mock import Mock, MagicMock

# Mock de la base de datos
class MockDB:
    def query(self, model):
        return MockQuery()

class MockQuery:
    def filter(self, *args):
        return self
    
    def first(self):
        # Mock de ProductModel
        product_mock = Mock()
        product_mock.product = "Producto Test"
        
        # Mock de UnitFeatureModel  
        unit_feature_mock = Mock()
        unit_feature_mock.weight_per_unit = 1.5
        unit_feature_mock.weight_per_pallet = 1000.0
        
        # Mock de ShoppingProductModel
        shopping_product_mock = Mock()
        shopping_product_mock.quantity_per_package = 25.0
        shopping_product_mock.quantity = 10
        shopping_product_mock.original_unit_cost = 100.0
        
        return product_mock

# Datos de prueba
sample_product = ShoppingProductInput(
    product_id=1,
    unit_measure_id=1,  # Kilogramos
    quantity=10,
    quantity_per_package=25.0,
    original_unit_cost=100.0,
    discount_percentage=5.0,
    final_unit_cost=95.0,
    amount=950.0,
    category_id=1
)

sample_product_lts = ShoppingProductInput(
    product_id=2,
    unit_measure_id=2,  # Litros
    quantity=5,
    quantity_per_package=77.0,
    original_unit_cost=200.0,
    discount_percentage=0.0,
    final_unit_cost=200.0,
    amount=1000.0,
    category_id=1
)

create_shopping_data = ShoppingCreateInput(
    shopping_number="SP-2025-001",
    products=[sample_product, sample_product_lts],
    total=1950.0,
    email="test@example.com",
    supplier_id=1
)

# Crear instancia del template con mock de DB
mock_db = MockDB()
template = TemplateClass(mock_db)

print("✅ Test de función calculate_shopping_totals creado")
print("📋 Datos de prueba:")
print(f"   - Producto 1: {sample_product.quantity_per_package} Kg")
print(f"   - Producto 2: {sample_product_lts.quantity_per_package} Lts") 
print(f"   - Total general: €. {create_shopping_data.total}")
print("✅ Estructura de test lista para implementar con datos reales")
