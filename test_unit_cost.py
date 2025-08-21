#!/usr/bin/env python3
"""
Script de prueba para calcular unit_cost basado en costos de envío y peso de productos
"""

import sys
import os

# Agregar el directorio raíz al path para importar módulos
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.backend.db.database import get_db
from app.backend.classes.shopping_class import ShoppingClass

def test_unit_cost_calculation():
    """
    Prueba el cálculo de unit_cost para un shopping específico
    """
    # Obtener la sesión de base de datos
    db = next(get_db())
    
    try:
        shopping_class = ShoppingClass(db)
        
        # Cambiar este ID por un shopping que exista en tu base de datos
        shopping_id = 9  # Ajusta este valor según tus datos
        
        print("Iniciando prueba de cálculo de unit_cost...")
        print(f"Shopping ID: {shopping_id}")
        
        # Ejecutar la prueba
        shopping_class.test_calculate_unit_costs(shopping_id)
        
        print("Prueba completada.")
        
    except Exception as e:
        print(f"Error en la prueba: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    test_unit_cost_calculation()
