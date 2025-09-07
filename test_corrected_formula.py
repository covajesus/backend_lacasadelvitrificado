#!/usr/bin/env python3
"""
Test de la fórmula corregida de pallets
"""
import math

def test_corrected_formula():
    """Simula la nueva fórmula corregida"""
    print("=== PRUEBA DE LA FÓRMULA CORREGIDA ===")
    
    # Simulando datos como vendrían de la base de datos
    shopping_products = [
        {
            "product_name": "Cerámica Frágil",
            "weight_per_unit": 100,
            "quantity": 5,
            "weight_per_pallet": 200
        },
        {
            "product_name": "Cerámica Resistente", 
            "weight_per_unit": 50,
            "quantity": 10,
            "weight_per_pallet": 3000
        },
        {
            "product_name": "Adhesivo",
            "weight_per_unit": 25,
            "quantity": 20,
            "weight_per_pallet": 1000
        }
    ]
    
    print("Datos de productos:")
    for product in shopping_products:
        print(f"- {product['product_name']}: {product['quantity']} units × {product['weight_per_unit']}kg = {product['quantity'] * product['weight_per_unit']}kg")
        print(f"  Max per pallet: {product['weight_per_pallet']}kg")
    
    # FÓRMULA ANTERIOR (INCORRECTA)
    total_weight_per_shopping = 0.0
    maximum_total_weight = 0.0
    
    for product in shopping_products:
        product_total_weight = product['weight_per_unit'] * product['quantity']
        total_weight_per_shopping += product_total_weight
        maximum_total_weight += product['weight_per_pallet']
    
    old_formula_result = math.ceil(total_weight_per_shopping / maximum_total_weight)
    
    print(f"\n--- FÓRMULA ANTERIOR (INCORRECTA) ---")
    print(f"Peso total: {total_weight_per_shopping}kg")
    print(f"Suma capacidades: {maximum_total_weight}kg")
    print(f"Resultado: {old_formula_result} pallets")
    
    # FÓRMULA NUEVA (CORREGIDA) 
    total_weight_per_shopping = 0.0
    total_pallets_needed = 0.0
    product_details = []
    
    for product in shopping_products:
        weight_per_unit = product['weight_per_unit']
        product_total_weight = weight_per_unit * product['quantity']
        weight_per_pallet = product['weight_per_pallet']
        
        # Calcular pallets necesarios por producto individual (fórmula correcta)
        pallets_for_this_product = math.ceil(product_total_weight / weight_per_pallet)
        
        total_weight_per_shopping += product_total_weight
        total_pallets_needed += pallets_for_this_product
        
        # Guardar detalles para debugging
        product_details.append({
            'product': product['product_name'],
            'weight': product_total_weight,
            'pallet_capacity': weight_per_pallet,
            'pallets_needed': pallets_for_this_product
        })
    
    print(f"\n--- FÓRMULA NUEVA (CORREGIDA) ---")
    print(f"Peso total: {total_weight_per_shopping}kg")
    print("Detalles por producto:")
    for detail in product_details:
        print(f"  - {detail['product']}: {detail['weight']}kg, capacity: {detail['pallet_capacity']}kg/pallet, needs: {detail['pallets_needed']} pallets")
    
    how_many_pallets = int(total_pallets_needed)
    print(f"Total pallets needed (corrected formula): {how_many_pallets}")
    
    print(f"\n--- COMPARACIÓN ---")
    print(f"Fórmula anterior: {old_formula_result} pallets")
    print(f"Fórmula corregida: {how_many_pallets} pallets")
    print(f"Diferencia: {how_many_pallets - old_formula_result} pallets")
    
    if how_many_pallets > old_formula_result:
        print("⚠️  La fórmula anterior SUBESTIMABA los pallets necesarios")
        print("✅ La nueva fórmula es más precisa y evita problemas de capacidad")
    elif how_many_pallets < old_formula_result:
        print("⚠️  La fórmula anterior SOBREESTIMABA los pallets necesarios")
        print("✅ La nueva fórmula es más eficiente")
    else:
        print("✅ Ambas fórmulas coinciden en este caso")

if __name__ == "__main__":
    test_corrected_formula()
