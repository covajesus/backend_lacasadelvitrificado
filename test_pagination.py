import sys
sys.path.append('.')

from app.backend.db.database import get_db
from app.backend.classes.template_class import TemplateClass
from app.backend.schemas import ShoppingCreateInput, ShoppingProductInput
from typing import List

# Crear datos de prueba mínimos
class TestData:
    def __init__(self):
        self.products = [
            ShoppingProductInput(
                product_id=1,
                category_id=1, 
                unit_measure_id=1,
                quantity_per_package=100,
                quantity=5,
                discount_percentage=0.0,
                original_unit_cost=10.50,
                final_unit_cost=10.50,
                amount=525.0
            )
        ]
        self.supplier_id = 1
        self.email = "test@test.com"
        self.second_email = None
        self.third_email = None

# Obtener una conexión a la base de datos
db = next(get_db())

try:
    # Crear instancia del template
    template = TemplateClass(db)
    
    # Datos de prueba
    data = TestData()
    shopping_id = 1  # Usar un ID existente en tu DB
    
    # Generar HTML
    html_content = template.generate_shopping_html_for_own_company(data, shopping_id)
    
    # Contar cuántos page-break hay en el HTML generado
    page_breaks = html_content.count('page-break-before: always')
    
    print(f"Número de saltos de página en el HTML: {page_breaks}")
    
    # Mostrar las líneas que contienen page-break
    lines = html_content.split('\n')
    for i, line in enumerate(lines):
        if 'page-break-before: always' in line:
            print(f"Línea {i+1}: {line.strip()}")
            
except Exception as e:
    print(f"Error: {e}")
finally:
    db.close()
