#!/usr/bin/env python3
"""
Test para simular el endpoint POST /inventories/store con y sin shopping_id
"""

import sys
import os
from datetime import date

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.backend.db.database import get_db
from app.backend.classes.inventory_class import InventoryClass
from app.backend.schemas import StoreInventory

def test_store_without_shopping_id():
    """
    Simula POST /inventories/store SIN shopping_id (comportamiento actual)
    """
    db = next(get_db())
    
    try:
        inventory_class = InventoryClass(db)
        
        # Simular el JSON que envías normalmente (SIN shopping_id)
        store_inventory = StoreInventory(
            user_id=1,
            product_id=12,
            location_id=1,
            stock=3,
            unit_cost=5000,  # Este se usará directamente
            public_sale_price=10000,
            private_sale_price=9000,
            minimum_stock=5,
            maximum_stock=100,
            lot_number="1001",
            arrival_date=date.today()
            # shopping_id NO está incluido
        )
        
        print("=== TEST SIN shopping_id ===")
        print(f"Unit cost enviado: {store_inventory.unit_cost}")
        print(f"Shopping ID: {getattr(store_inventory, 'shopping_id', 'No definido')}")
        
        result = inventory_class.store(store_inventory)
        print(f"Resultado: {result}")
        
    except Exception as e:
        print(f"Error: {e}")
    finally:
        db.close()

def test_store_with_shopping_id():
    """
    Simula POST /inventories/store CON shopping_id (cálculo automático)
    """
    db = next(get_db())
    
    try:
        inventory_class = InventoryClass(db)
        
        # Simular el JSON con shopping_id incluido
        store_inventory = StoreInventory(
            user_id=1,
            product_id=12,
            location_id=1,
            stock=3,
            unit_cost=5000,  # Este será sobrescrito
            public_sale_price=10000,
            private_sale_price=9000,
            minimum_stock=5,
            maximum_stock=100,
            lot_number="1002",
            arrival_date=date.today(),
            shopping_id=9  # Esto activa el cálculo automático
        )
        
        print("\n=== TEST CON shopping_id ===")
        print(f"Unit cost enviado: {store_inventory.unit_cost}")
        print(f"Shopping ID: {store_inventory.shopping_id}")
        
        result = inventory_class.store(store_inventory)
        print(f"Resultado: {result}")
        
    except Exception as e:
        print(f"Error: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    test_store_without_shopping_id()
    test_store_with_shopping_id()
