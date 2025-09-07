#!/usr/bin/env python3
"""
Prueba para demostrar el problema con el cálculo de pallets mixtos
"""
import math

def current_pallet_calculation():
    """Fórmula actual (incorrecta para pallets mixtos)"""
    print("=== FÓRMULA ACTUAL (PROBLEMÁTICA) ===")
    
    # Ejemplo: Orden con productos mixtos (caso problemático)
    products = [
        {"name": "Cerámica Pesada", "weight_per_unit": 50, "quantity": 10, "weight_per_pallet": 500},   # 500kg total, pallet pequeño
        {"name": "Cerámica Ligera", "weight_per_unit": 10, "quantity": 50, "weight_per_pallet": 2000},  # 500kg total, pallet grande
        {"name": "Adhesivo Especial", "weight_per_unit": 25, "quantity": 20, "weight_per_pallet": 800}, # 500kg total, pallet medio
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
    
    # Fórmula actual
    how_many_pallets_current = math.ceil(total_weight_per_shopping / maximum_total_weight)
    print(f"Pallets calculados (fórmula actual): {how_many_pallets_current}")
    
    return how_many_pallets_current

def correct_pallet_calculation():
    """Fórmula correcta para pallets mixtos"""
    print("\n=== FÓRMULA CORRECTA (PARA PALLETS MIXTOS) ===")
    
    # Los mismos productos
    products = [
        {"name": "Cerámica Pesada", "weight_per_unit": 50, "quantity": 10, "weight_per_pallet": 500},   # 500kg total, pallet pequeño
        {"name": "Cerámica Ligera", "weight_per_unit": 10, "quantity": 50, "weight_per_pallet": 2000},  # 500kg total, pallet grande
        {"name": "Adhesivo Especial", "weight_per_unit": 25, "quantity": 20, "weight_per_pallet": 800}, # 500kg total, pallet medio
    ]
    
    # Método 1: Asumir capacidad mínima de pallet (más conservador)
    min_pallet_capacity = min(product["weight_per_pallet"] for product in products)
    total_weight = sum(product["weight_per_unit"] * product["quantity"] for product in products)
    
    pallets_method1 = math.ceil(total_weight / min_pallet_capacity)
    print(f"Método 1 - Capacidad mínima ({min_pallet_capacity}kg): {pallets_method1} pallets")
    
    # Método 2: Capacidad promedio ponderada
    total_capacity = sum(product["weight_per_pallet"] for product in products)
    avg_pallet_capacity = total_capacity / len(products)
    pallets_method2 = math.ceil(total_weight / avg_pallet_capacity)
    print(f"Método 2 - Capacidad promedio ({avg_pallet_capacity:.1f}kg): {pallets_method2} pallets")
    
    # Método 3: Simulación de empaquetado real (más preciso)
    print(f"\nMétodo 3 - Simulación de empaquetado real:")
    pallets_used = []
    remaining_products = [(p["weight_per_unit"] * p["quantity"], p["name"]) for p in products]
    remaining_products.sort(reverse=True)  # Ordenar por peso descendente
    
    pallet_number = 1
    
    while remaining_products:
        current_pallet_weight = 0
        current_pallet_capacity = 1200  # Capacidad estándar de pallet mixto
        products_in_pallet = []
        
        # Intentar llenar el pallet actual
        i = 0
        while i < len(remaining_products):
            weight, name = remaining_products[i]
            if current_pallet_weight + weight <= current_pallet_capacity:
                current_pallet_weight += weight
                products_in_pallet.append((weight, name))
                remaining_products.pop(i)
            else:
                i += 1
        
        print(f"  Pallet {pallet_number}: {current_pallet_weight}kg")
        for weight, name in products_in_pallet:
            print(f"    - {name}: {weight}kg")
        
        pallets_used.append(current_pallet_weight)
        pallet_number += 1
    
    print(f"Total pallets necesarios (simulación real): {len(pallets_used)}")
    
    return len(pallets_used)

def demonstrate_problem():
    """Demuestra el problema con la fórmula actual"""
    print("DEMOSTRACIÓN DEL PROBLEMA CON PALLETS MIXTOS")
    print("=" * 50)
    
    current_result = current_pallet_calculation()
    correct_result = correct_pallet_calculation()
    
    print(f"\n=== COMPARACIÓN DE RESULTADOS ===")
    print(f"Fórmula actual: {current_result} pallets")
    print(f"Fórmula correcta: {correct_result} pallets")
    print(f"Diferencia: {abs(current_result - correct_result)} pallets")
    
    if current_result != correct_result:
        print("\n⚠️  PROBLEMA DETECTADO:")
        if current_result < correct_result:
            print("La fórmula actual SUBESTIMA la cantidad de pallets necesarios")
            print("Esto puede causar problemas de capacidad en el transporte")
        else:
            print("La fórmula actual SOBREESTIMA la cantidad de pallets necesarios")
            print("Esto puede causar costos innecesarios de transporte")
    else:
        print("\n✅ Las fórmulas coinciden para este caso")

if __name__ == "__main__":
    demonstrate_problem()
