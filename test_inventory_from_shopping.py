#!/usr/bin/env python3
"""
Test para verificar que el unit_cost se calcule automáticamente al crear inventario desde shopping
"""

import sys
import os
from datetime import date

# Agregar el directorio raíz al path para importar módulos
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.backend.db.database import get_db
from app.backend.classes.inventory_class import InventoryClass
from app.backend.schemas import StoreInventory

def test_inventory_with_shopping():
    """
    Prueba crear inventario con shopping_id para verificar cálculo automático de unit_cost
    """
    db = next(get_db())
    
    try:
        inventory_class = InventoryClass(db)
        
        # Crear un StoreInventory con shopping_id
        store_inventory = StoreInventory(
            user_id=1,
            product_id=18,  # Producto que sabemos existe en shopping 9
            location_id=1,
            stock=2,
            unit_cost=0,  # Este será sobrescrito por el cálculo automático
            public_sale_price=10000,
            private_sale_price=9000,
            minimum_stock=5,
            maximum_stock=100,
            lot_number="999",  # Número como string
            arrival_date=date.today(),
            shopping_id=9  # Este activará el cálculo automático
        )
        
        print("Creando inventario con cálculo automático de unit_cost...")
        print(f"Shopping ID: {store_inventory.shopping_id}")
        print(f"Product ID: {store_inventory.product_id}")
        print(f"Stock: {store_inventory.stock}")
        
        # Crear el inventario
        result = inventory_class.store(store_inventory)
        
        print(f"Resultado: {result}")
        
    except Exception as e:
        print(f"Error en la prueba: {e}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()

if __name__ == "__main__":
    test_inventory_with_shopping()
