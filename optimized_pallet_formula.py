#!/usr/bin/env python3
"""
Fórmula optimizada para pallets mixtos - más precisa
"""
import math

def optimized_pallet_calculation_for_template():
    """Fórmula optimizada que simula pallets mixtos reales"""
    print("=== FÓRMULA OPTIMIZADA PARA TEMPLATE_CLASS ===")
    
    # Simulación de productos como vienen de la DB
    products_data = [
        {"weight": 1000, "pallet_capacity": 500, "name": "Cerámica Frágil"},
        {"weight": 500, "pallet_capacity": 600, "name": "Adhesivo Químico"}, 
        {"weight": 500, "pallet_capacity": 2000, "name": "Herramientas"}
    ]
    
    def calculate_optimized_pallets(products_data):
        """Algoritmo optimizado para pallets mixtos"""
        pallets_used = []
        remaining_products = [{"weight": p["weight"], "capacity": p["pallet_capacity"], "name": p["name"]} for p in products_data]
        
        while any(p["weight"] > 0 for p in remaining_products):
            # Nuevo pallet - capacidad limitada por el producto más restrictivo restante
            active_products = [p for p in remaining_products if p["weight"] > 0]
            if not active_products:
                break
                
            pallet_capacity = min(p["capacity"] for p in active_products)
            current_pallet_weight = 0
            pallet_contents = []
            
            # Llenar pallet optimizando espacio
            for product in remaining_products:
                if product["weight"] > 0:
                    # Cuánto puede agregar de este producto
                    max_can_add = min(
                        product["weight"],  # Lo que queda del producto
                        product["capacity"],  # Límite del producto
                        pallet_capacity - current_pallet_weight  # Espacio restante en pallet
                    )
                    
                    if max_can_add > 0:
                        current_pallet_weight += max_can_add
                        product["weight"] -= max_can_add
                        pallet_contents.append(f"{product['name']}: {max_can_add}kg")
            
            pallets_used.append({
                "weight": current_pallet_weight,
                "capacity": pallet_capacity,
                "contents": pallet_contents
            })
        
        return pallets_used
    
    # Calcular con fórmula optimizada
    optimized_pallets = calculate_optimized_pallets(products_data)
    
    print("Pallets calculados (optimizada):")
    for i, pallet in enumerate(optimized_pallets, 1):
        print(f"Pallet {i}: {pallet['weight']}kg (capacidad: {pallet['capacity']}kg)")
        for content in pallet['contents']:
            print(f"  - {content}")
    
    print(f"\nTotal pallets (optimizada): {len(optimized_pallets)}")
    
    # Comparar con fórmula individual
    individual_total = sum(math.ceil(p["weight"] / p["pallet_capacity"]) for p in products_data)
    print(f"Total pallets (individual): {individual_total}")
    
    print(f"\n=== CONCLUSIÓN ===")
    if len(optimized_pallets) <= individual_total:
        print("✅ La fórmula optimizada es más eficiente")
        print(f"📦 Ahorro: {individual_total - len(optimized_pallets)} pallets")
    else:
        print("⚠️  La fórmula individual ya era óptima")
    
    return len(optimized_pallets)

def implementation_for_template_class():
    """Código para implementar en template_class.py"""
    print(f"\n=== CÓDIGO PARA TEMPLATE_CLASS.PY ===")
    print("""
def calculate_optimized_mixed_pallets(products_info):
    '''Calcula pallets mixtos optimizados'''
    pallets_used = []
    remaining_products = [{"weight": p["total_weight"], "capacity": p["pallet_capacity"], "name": p["name"]} for p in products_info]
    
    while any(p["weight"] > 0 for p in remaining_products):
        active_products = [p for p in remaining_products if p["weight"] > 0]
        if not active_products:
            break
            
        pallet_capacity = min(p["capacity"] for p in active_products)
        current_pallet_weight = 0
        
        for product in remaining_products:
            if product["weight"] > 0:
                max_can_add = min(
                    product["weight"],
                    product["capacity"], 
                    pallet_capacity - current_pallet_weight
                )
                
                if max_can_add > 0:
                    current_pallet_weight += max_can_add
                    product["weight"] -= max_can_add
        
        pallets_used.append(current_pallet_weight)
    
    return len(pallets_used)

# En el loop de productos, acumular info:
products_info = []
for item in sorted_products:
    # ... código existente ...
    products_info.append({
        "total_weight": product_total_weight,
        "pallet_capacity": weight_per_pallet,
        "name": product_data.product
    })

# Calcular pallets optimizados
how_many_pallets = calculate_optimized_mixed_pallets(products_info)
""")

if __name__ == "__main__":
    optimized_pallet_calculation_for_template()
    implementation_for_template_class()
