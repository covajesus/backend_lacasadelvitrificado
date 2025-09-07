#!/usr/bin/env python3
"""
Prueba de la fórmula realmente correcta implementada en template_class.py
"""

def test_new_formula():
    """Simula la nueva fórmula implementada"""
    print("=== PRUEBA DE LA NUEVA FÓRMULA IMPLEMENTADA ===")
    
    # Datos de ejemplo como vendrían de la base de datos
    products_info = [
        {'name': 'Cerámica Resistente', 'total_weight': 500, 'weight_per_pallet': 3000},  # 500kg, pallet de 3000kg
        {'name': 'Cerámica Frágil', 'total_weight': 400, 'weight_per_pallet': 500},      # 400kg, pallet de 500kg  
        {'name': 'Adhesivo', 'total_weight': 300, 'weight_per_pallet': 1000},            # 300kg, pallet de 1000kg
    ]
    
    def calculate_real_mixed_pallets(products_info):
        """Algoritmo correcto implementado en template_class.py"""
        remaining = [{"name": p["name"], "weight": p["total_weight"], "capacity": p["weight_per_pallet"]} for p in products_info]
        pallets = []
        
        while any(p["weight"] > 0 for p in remaining):
            # Nuevo pallet
            active = [p for p in remaining if p["weight"] > 0]
            if not active:
                break
            
            # Capacidad del pallet = mínima de productos activos (más restrictivo)
            pallet_capacity = min(p["capacity"] for p in active)
            pallet_weight = 0
            pallet_contents = []
            
            # Llenar pallet con productos disponibles
            for product in remaining:
                if product["weight"] > 0 and pallet_weight < pallet_capacity:
                    # Cuánto puede agregar de este producto
                    space_available = pallet_capacity - pallet_weight
                    can_add = min(product["weight"], space_available)
                    
                    if can_add > 0:
                        pallet_weight += can_add
                        product["weight"] -= can_add
                        pallet_contents.append(f"{product['name']}: {can_add}kg")
            
            pallets.append({
                "total_weight": pallet_weight,
                "capacity": pallet_capacity,
                "contents": pallet_contents
            })
        
        return pallets
    
    print("Productos en la orden:")
    total_weight = 0
    for p in products_info:
        print(f"- {p['name']}: {p['total_weight']}kg (máx {p['weight_per_pallet']}kg/pallet)")
        total_weight += p['total_weight']
    
    print(f"\nPeso total de la orden: {total_weight}kg")
    
    # Calcular con la nueva fórmula
    calculated_pallets = calculate_real_mixed_pallets(products_info)
    how_many_pallets = len(calculated_pallets)
    
    print(f"\n--- RESULTADO DE LA NUEVA FÓRMULA ---")
    print("Distribución de pallets:")
    for i, pallet in enumerate(calculated_pallets, 1):
        print(f"  Pallet {i}: {pallet['total_weight']}kg / {pallet['capacity']}kg")
        for content in pallet['contents']:
            print(f"    - {content}")
    
    print(f"\nTotal pallets necesarios: {how_many_pallets}")
    
    # Comparar con fórmulas anteriores
    print(f"\n--- COMPARACIÓN CON FÓRMULAS ANTERIORES ---")
    
    # Fórmula original (muy incorrecta)
    import math
    total_weight_shopping = sum(p['total_weight'] for p in products_info)
    total_capacity = sum(p['weight_per_pallet'] for p in products_info)
    original_formula = math.ceil(total_weight_shopping / total_capacity)
    
    # Mi fórmula anterior (incorrecta)
    individual_formula = sum(math.ceil(p['total_weight'] / p['weight_per_pallet']) for p in products_info)
    
    print(f"Fórmula original (suma capacidades): {original_formula} pallets")
    print(f"Mi fórmula anterior (individual): {individual_formula} pallets") 
    print(f"Nueva fórmula (mixtos reales): {how_many_pallets} pallets")
    
    print(f"\n--- ANÁLISIS ---")
    if how_many_pallets < individual_formula:
        print(f"✅ Mejora: {individual_formula - how_many_pallets} pallets menos que fórmula individual")
        print("✅ La nueva fórmula optimiza el uso de pallets mixtos")
    elif how_many_pallets == individual_formula:
        print("ℹ️  Mismo resultado que fórmula individual para este caso")
    else:
        print("⚠️  Usa más pallets que fórmula individual - revisar algoritmo")
    
    if how_many_pallets > original_formula:
        print("✅ Más realista que fórmula original (que era muy optimista)")
    
    return how_many_pallets

def extreme_case_test():
    """Caso extremo para probar la fórmula"""
    print(f"\n=== CASO EXTREMO ===")
    
    products_extreme = [
        {'name': 'Producto Pesado', 'total_weight': 1500, 'weight_per_pallet': 500},    # Necesita 3 pallets mínimo
        {'name': 'Producto Ligero', 'total_weight': 100, 'weight_per_pallet': 2000},    # Cabe en cualquier lado
        {'name': 'Producto Medio', 'total_weight': 200, 'weight_per_pallet': 1000},     # Flexible
    ]
    
    def calculate_real_mixed_pallets(products_info):
        remaining = [{"name": p["name"], "weight": p["total_weight"], "capacity": p["weight_per_pallet"]} for p in products_info]
        pallets = []
        
        while any(p["weight"] > 0 for p in remaining):
            active = [p for p in remaining if p["weight"] > 0]
            if not active:
                break
            
            pallet_capacity = min(p["capacity"] for p in active)
            pallet_weight = 0
            pallet_contents = []
            
            for product in remaining:
                if product["weight"] > 0 and pallet_weight < pallet_capacity:
                    space_available = pallet_capacity - pallet_weight
                    can_add = min(product["weight"], space_available)
                    
                    if can_add > 0:
                        pallet_weight += can_add
                        product["weight"] -= can_add
                        pallet_contents.append(f"{product['name']}: {can_add}kg")
            
            pallets.append({
                "total_weight": pallet_weight,
                "capacity": pallet_capacity,
                "contents": pallet_contents
            })
        
        return pallets
    
    result = calculate_real_mixed_pallets(products_extreme)
    
    print("Caso extremo:")
    for p in products_extreme:
        print(f"- {p['name']}: {p['total_weight']}kg (máx {p['weight_per_pallet']}kg/pallet)")
    
    print(f"\nResultado:")
    for i, pallet in enumerate(result, 1):
        print(f"  Pallet {i}: {pallet['total_weight']}kg / {pallet['capacity']}kg")
        for content in pallet['contents']:
            print(f"    - {content}")
    
    print(f"Total: {len(result)} pallets")

if __name__ == "__main__":
    test_new_formula()
    extreme_case_test()
