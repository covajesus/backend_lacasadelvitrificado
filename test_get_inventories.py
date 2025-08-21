#!/usr/bin/env python3
"""
Test para el endpoint GET /shoppings/get_inventories/{shopping_id}
"""

import sys
import os

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.backend.db.database import get_db

def test_get_inventories_endpoint():
    """
    Prueba el endpoint para obtener inventarios por shopping_id
    """
    try:
        # Usar el shopping_id que sabemos tiene inventarios
        shopping_id = 9
        
        # Simular la llamada al endpoint (sin hacer HTTP real, sino llamando directamente a la función)
        from app.backend.routers.shoppings import get_inventories_by_shopping_id
        from app.backend.schemas import UserLogin
        
        # Crear un usuario mock para la sesión
        class MockUser:
            def __init__(self):
                self.id = 1
                self.username = "test"
                self.email = "test@test.com"
        
        db = next(get_db())
        
        try:
            result = get_inventories_by_shopping_id(
                shopping_id=shopping_id,
                session_user=MockUser(),
                db=db
            )
            
            print(f"=== INVENTARIOS PARA SHOPPING {shopping_id} ===")
            print(f"Status: {result.get('status')}")
            print(f"Message: {result.get('message')}")
            
            if result.get('data'):
                print(f"\\nCantidad de inventarios encontrados: {len(result['data'])}")
                
                for i, inventory in enumerate(result['data'][:3]):  # Mostrar solo los primeros 3
                    print(f"\\n--- Inventario {i+1} ---")
                    print(f"Inventory ID: {inventory['inventory_id']}")
                    print(f"Producto: {inventory['product_name']} ({inventory['product_code']})")
                    print(f"Unidad de medida: {inventory['unit_measure']}")
                    print(f"Cantidad: {inventory['quantity']}")
                    print(f"Unit Cost (Movement): {inventory['movement_unit_cost']}")
                    print(f"Unit Cost (Lot): {inventory['lot_unit_cost']}")
                    print(f"Precio público: {inventory['public_sale_price']}")
                    print(f"Lote número: {inventory['lot_number']}")
                    print(f"Fecha de creación: {inventory['inventory_added_date']}")
            else:
                print("No se encontraron inventarios")
                
        finally:
            db.close()
            
    except Exception as e:
        print(f"Error en el test: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_get_inventories_endpoint()
