#!/usr/bin/env python3
"""
Test para verificar que el shopping_id se actualiza a status_id = 7
"""

import sys
import os
from datetime import date

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.backend.db.database import get_db
from app.backend.classes.inventory_class import InventoryClass
from app.backend.schemas import StoreInventory
from app.backend.db.models import ShoppingModel

def test_shopping_status_update():
    """
    Prueba que el shopping se actualice a status_id = 7 cuando se crea inventario
    """
    db = next(get_db())
    
    try:
        # Verificar el status actual del shopping
        shopping = db.query(ShoppingModel).filter(ShoppingModel.id == 9).first()
        print(f"Status actual del shopping 9: {shopping.status_id}")
        
        inventory_class = InventoryClass(db)
        
        # Crear inventario con shopping_id
        store_inventory = StoreInventory(
            user_id=1,
            product_id=12,  # Producto diferente para evitar duplicados
            location_id=1,
            stock=2,
            unit_cost=0,  # Será calculado automáticamente
            public_sale_price=10000,
            private_sale_price=9000,
            minimum_stock=5,
            maximum_stock=100,
            lot_number="1004",
            arrival_date=date.today(),
            shopping_id=9  # Esto activará el cálculo y actualizará status
        )
        
        print("\\nCreando inventario con shopping_id = 9...")
        result = inventory_class.store(store_inventory)
        
        # Verificar que el status se actualizó
        shopping_updated = db.query(ShoppingModel).filter(ShoppingModel.id == 9).first()
        print(f"\\nStatus del shopping después de crear inventario: {shopping_updated.status_id}")
        print(f"Resultado: {result}")
        
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()

if __name__ == "__main__":
    test_shopping_status_update()
