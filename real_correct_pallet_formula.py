#!/usr/bin/env python3
"""
Fórmula REALMENTE correcta para pallets mixtos
"""
import math

def demonstrate_the_real_problem():
    """Demuestra el problema real de mi fórmula anterior"""
    print("=== PROBLEMA EN MI FÓRMULA ANTERIOR ===")
    
    products = [
        {"name": "Producto A", "weight": 500, "pallet_capacity": 3000},  # Solo 500kg, cabe en 3000kg
        {"name": "Producto B", "weight": 400, "pallet_capacity": 2000},  # Solo 400kg, cabe en 2000kg  
        {"name": "Producto C", "weight": 300, "pallet_capacity": 1000},  # Solo 300kg, cabe en 1000kg
    ]
    
    print("Productos:")
    for p in products:
        print(f"- {p['name']}: {p['weight']}kg (pallet máx: {p['pallet_capacity']}kg)")
    
    # MI FÓRMULA ANTERIOR (INCORRECTA)
    print(f"\n--- MI FÓRMULA ANTERIOR (INCORRECTA) ---")
    total_pallets_wrong = 0
    for p in products:
        pallets = math.ceil(p['weight'] / p['pallet_capacity'])
        print(f"- {p['name']}: ceil({p['weight']} / {p['pallet_capacity']}) = {pallets} pallet")
        total_pallets_wrong += pallets
    
    print(f"Total (fórmula incorrecta): {total_pallets_wrong} pallets")
    print("❌ PROBLEMA: ¡Cada producto 'ocupa' 1 pallet completo aunque solo use una fracción!")
    
    # FÓRMULA REALMENTE CORRECTA
    print(f"\n--- FÓRMULA REALMENTE CORRECTA ---")
    print("Los productos pueden compartir pallets respetando límites:")
    
    # Pallet 1: Intentar meter todos los productos
    remaining_products = products.copy()
    pallets_used = []
    
    while any(p['weight'] > 0 for p in remaining_products):
        # Nuevo pallet
        pallet_contents = []
        pallet_weight = 0
        
        # Buscar qué producto tiene la restricción más fuerte de los que quedan
        active_products = [p for p in remaining_products if p['weight'] > 0]
        if not active_products:
            break
            
        # La capacidad del pallet está limitada por el producto más restrictivo
        min_capacity = min(p['pallet_capacity'] for p in active_products)
        
        print(f"\nPallet {len(pallets_used) + 1} (capacidad limitada a {min_capacity}kg):")
        
        # Intentar llenar el pallet
        for product in remaining_products:
            if product['weight'] > 0:
                # Cuánto puede agregar de este producto
                space_left = min_capacity - pallet_weight
                max_from_product = min(product['weight'], product['pallet_capacity'])
                can_add = min(max_from_product, space_left)
                
                if can_add > 0:
                    pallet_weight += can_add
                    product['weight'] -= can_add
                    pallet_contents.append(f"{product['name']}: {can_add}kg")
                    print(f"  + {product['name']}: {can_add}kg")
        
        pallets_used.append({
            'weight': pallet_weight,
            'capacity': min_capacity,
            'contents': pallet_contents
        })
        
        print(f"  Total pallet: {pallet_weight}kg / {min_capacity}kg")
    
    print(f"\nTotal pallets (correcto): {len(pallets_used)}")
    print(f"Diferencia: {total_pallets_wrong - len(pallets_used)} pallets de diferencia!")

def correct_mixed_pallet_algorithm():
    """Algoritmo correcto para pallets mixtos"""
    print(f"\n=== ALGORITMO CORRECTO ===")
    
    products_info = [
        {"name": "Cerámica Pesada", "total_weight": 800, "weight_per_pallet": 500},   # Necesita 2 pallets mínimo
        {"name": "Cerámica Ligera", "total_weight": 400, "weight_per_pallet": 2000},  # Cabe en cualquier pallet
        {"name": "Adhesivo", "total_weight": 300, "weight_per_pallet": 1000},         # Cabe en pallet medio
    ]
    
    def calculate_real_mixed_pallets(products_info):
        """Algoritmo que realmente simula llenado de pallets mixtos"""
        remaining = [{"name": p["name"], "weight": p["total_weight"], "capacity": p["weight_per_pallet"]} for p in products_info]
        pallets = []
        
        while any(p["weight"] > 0 for p in remaining):
            # Nuevo pallet
            active = [p for p in remaining if p["weight"] > 0]
            if not active:
                break
            
            # Capacidad del pallet = mínima de productos activos
            pallet_capacity = min(p["capacity"] for p in active)
            pallet_weight = 0
            pallet_info = {"capacity": pallet_capacity, "contents": []}
            
            # Llenar pallet con productos disponibles
            for product in remaining:
                if product["weight"] > 0 and pallet_weight < pallet_capacity:
                    # Cuánto puede agregar
                    space_available = pallet_capacity - pallet_weight
                    can_add = min(product["weight"], space_available)
                    
                    if can_add > 0:
                        pallet_weight += can_add
                        product["weight"] -= can_add
                        pallet_info["contents"].append(f"{product['name']}: {can_add}kg")
            
            pallet_info["total_weight"] = pallet_weight
            pallets.append(pallet_info)
        
        return pallets
    
    result = calculate_real_mixed_pallets(products_info)
    
    print("Productos:")
    for p in products_info:
        print(f"- {p['name']}: {p['total_weight']}kg (máx {p['weight_per_pallet']}kg/pallet)")
    
    print(f"\nResultado del algoritmo correcto:")
    for i, pallet in enumerate(result, 1):
        print(f"Pallet {i}: {pallet['total_weight']}kg / {pallet['capacity']}kg")
        for content in pallet['contents']:
            print(f"  - {content}")
    
    print(f"\nTotal pallets necesarios: {len(result)}")
    
    return len(result)

if __name__ == "__main__":
    demonstrate_the_real_problem()
    correct_mixed_pallet_algorithm()
