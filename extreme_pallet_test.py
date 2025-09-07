#!/usr/bin/env python3
"""
Casos extremos que demuestran el problema con pallets mixtos
"""
import math

def extreme_case_test():
    """Caso extremo que demuestra claramente el problema"""
    print("=== CASO EXTREMO - PRODUCTOS CON DIFERENCIAS GRANDES ===")
    
    # Caso extremo: productos muy diferentes
    products = [
        {"name": "Material Frágil", "weight_per_unit": 100, "quantity": 5, "weight_per_pallet": 200},    # 500kg, solo 200kg por pallet
        {"name": "Material Resistente", "weight_per_unit": 50, "quantity": 10, "weight_per_pallet": 3000}, # 500kg, hasta 3000kg por pallet
        {"name": "Material Medio", "weight_per_unit": 25, "quantity": 20, "weight_per_pallet": 1000},   # 500kg, 1000kg por pallet
    ]
    
    total_weight_per_shopping = 0.0
    maximum_total_weight = 0.0
    
    print("Productos en la orden:")
    for product in products:
        product_total_weight = product["weight_per_unit"] * product["quantity"]
        total_weight_per_shopping += product_total_weight
        maximum_total_weight += product["weight_per_pallet"]
        
        print(f"- {product['name']}: {product['quantity']} unidades × {product['weight_per_unit']}kg = {product_total_weight}kg")
        print(f"  Capacidad máxima por pallet: {product['weight_per_pallet']}kg")
    
    print(f"\nPeso total de la orden: {total_weight_per_shopping}kg")
    print(f"Suma de capacidades máximas: {maximum_total_weight}kg")
    
    # Fórmula actual (incorrecta)
    how_many_pallets_current = math.ceil(total_weight_per_shopping / maximum_total_weight)
    print(f"Pallets calculados (fórmula actual): {how_many_pallets_current}")
    
    # Cálculo real necesario
    print(f"\nCálculo real de pallets necesarios:")
    
    # Material Frágil: 500kg ÷ 200kg/pallet = 3 pallets mínimo
    pallets_fragil = math.ceil(500 / 200)
    print(f"- Material Frágil: {pallets_fragil} pallets (500kg ÷ 200kg/pallet)")
    
    # En la realidad, estos 3 pallets de material frágil solo ocupan 500kg
    # Los otros materiales deben ir en pallets separados o combinados según capacidad restante
    
    # Pallet 1 de frágil: 200kg de frágil + ¿cuánto más?
    # Capacidad restante en pallet frágil: 0kg (ya que el límite es 200kg por pallet de frágil)
    
    # Los otros 1000kg de material resistente y medio necesitan pallets adicionales
    remaining_weight = 1000  # 500kg resistente + 500kg medio
    standard_pallet_capacity = 1000  # Capacidad estándar para otros materiales
    additional_pallets = math.ceil(remaining_weight / standard_pallet_capacity)
    
    print(f"- Materiales Resistente + Medio: {additional_pallets} pallets adicionales")
    
    total_real_pallets = pallets_fragil + additional_pallets
    print(f"Total pallets reales necesarios: {total_real_pallets}")
    
    print(f"\n⚠️  DIFERENCIA CRÍTICA:")
    print(f"Fórmula actual: {how_many_pallets_current} pallets")
    print(f"Realidad: {total_real_pallets} pallets")
    print(f"Error: {total_real_pallets - how_many_pallets_current} pallets de diferencia ({((total_real_pallets - how_many_pallets_current) / total_real_pallets * 100):.1f}% de error)")

def correct_formula_proposal():
    """Propuesta de fórmula correcta"""
    print(f"\n=== PROPUESTA DE FÓRMULA CORRECTA ===")
    
    print("""
PROBLEMA IDENTIFICADO:
La fórmula actual suma todas las capacidades máximas de pallets de diferentes productos,
pero en la realidad los productos con restricciones de peso menores limitan la capacidad
total del envío.

FÓRMULA ACTUAL (INCORRECTA):
total_pallets = ceil(peso_total / suma_capacidades_maximas)

FÓRMULAS PROPUESTAS (CORRECTAS):

1. CONSERVADORA (más segura):
   total_pallets = ceil(peso_total / min_capacidad_pallet)

2. OPTIMIZADA (más realista):
   Para cada producto:
     pallets_producto = ceil(peso_producto / capacidad_pallet_producto)
   total_pallets = sum(pallets_producto)

3. MIXTA INTELIGENTE (recomendada):
   - Calcular pallets necesarios por producto individualmente
   - Intentar optimizar combinando productos compatibles
   - Respetar límites de capacidad por tipo de producto
""")

if __name__ == "__main__":
    extreme_case_test()
    correct_formula_proposal()
