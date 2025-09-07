#!/usr/bin/env python3
"""
Comparación entre algoritmo del frontend y backend
"""

def algoritmo_frontend():
    """Simula el algoritmo del frontend basado en el log"""
    print("=" * 60)
    print("ALGORITMO DEL FRONTEND (3 pallets)")
    print("=" * 60)
    
    productos = [
        {'name': 'AquaSeal® CeramicStar (Mate)', 'total_weight': 24.04, 'weight_per_pallet': 378.63},
        {'name': 'AquaSeal® CeramicStar Harter', 'total_weight': 2.24, 'weight_per_pallet': 70.56},
        {'name': 'AquaSeal® EcoGold (Mate)', 'total_weight': 1140.0, 'weight_per_pallet': 547.2}
    ]
    
    print("📦 Datos de entrada:")
    for p in productos:
        print(f"  • {p['name']}: {p['total_weight']}kg (máx {p['weight_per_pallet']}kg/pallet)")
    print()
    
    print("🔍 El log del frontend muestra:")
    print("  Comment: 'Mixed pallets calculation (FIXED - using max capacity)'")
    print("  Esto sugiere que usa la CAPACIDAD MÁXIMA, no la mínima")
    print()
    
    # Simular algoritmo con capacidad máxima
    remaining = [{"name": p["name"], "weight": p["total_weight"], "capacity": p["weight_per_pallet"]} for p in productos]
    pallets = []
    
    while any(p["weight"] > 0 for p in remaining):
        active = [p for p in remaining if p["weight"] > 0]
        if not active:
            break
        
        # DIFERENCIA CLAVE: USA LA CAPACIDAD MÁXIMA
        pallet_capacity = max(p["capacity"] for p in active)  # MAX en lugar de MIN
        pallet_weight = 0
        pallet_contents = []
        
        print(f"Nuevo pallet - Capacidad: {pallet_capacity}kg (MÁXIMA de productos activos)")
        
        for product in remaining:
            if product["weight"] > 0 and pallet_weight < pallet_capacity:
                space_available = pallet_capacity - pallet_weight
                can_add = min(product["weight"], space_available)
                
                if can_add > 0:
                    print(f"  - Agregando {can_add}kg de {product['name']}")
                    pallet_weight += can_add
                    product["weight"] -= can_add
                    pallet_contents.append(f"{product['name']}: {can_add}kg")
        
        pallets.append({
            "total_weight": pallet_weight,
            "capacity": pallet_capacity,
            "contents": pallet_contents
        })
        
        print(f"  Pallet completado: {pallet_weight}kg / {pallet_capacity}kg")
        print()
    
    print(f"🎯 RESULTADO FRONTEND: {len(pallets)} pallets")
    for i, pallet in enumerate(pallets, 1):
        print(f"Pallet {i}: {pallet['total_weight']}kg / {pallet['capacity']}kg")
        for content in pallet['contents']:
            print(f"  - {content}")
        print()
    
    return len(pallets)

def algoritmo_backend():
    """Algoritmo actual del backend"""
    print("=" * 60)
    print("ALGORITMO DEL BACKEND (4 pallets)")
    print("=" * 60)
    
    productos = [
        {'name': 'AquaSeal® CeramicStar (Mate)', 'total_weight': 24.04, 'weight_per_pallet': 378.63},
        {'name': 'AquaSeal® CeramicStar Harter', 'total_weight': 2.24, 'weight_per_pallet': 70.56},
        {'name': 'AquaSeal® EcoGold (Mate)', 'total_weight': 1140.0, 'weight_per_pallet': 547.2}
    ]
    
    remaining = [{"name": p["name"], "weight": p["total_weight"], "capacity": p["weight_per_pallet"]} for p in productos]
    pallets = []
    
    while any(p["weight"] > 0 for p in remaining):
        active = [p for p in remaining if p["weight"] > 0]
        if not active:
            break
        
        # USA LA CAPACIDAD MÍNIMA
        pallet_capacity = min(p["capacity"] for p in active)  # MIN
        pallet_weight = 0
        pallet_contents = []
        
        print(f"Nuevo pallet - Capacidad: {pallet_capacity}kg (MÍNIMA de productos activos)")
        
        for product in remaining:
            if product["weight"] > 0 and pallet_weight < pallet_capacity:
                space_available = pallet_capacity - pallet_weight
                can_add = min(product["weight"], space_available)
                
                if can_add > 0:
                    print(f"  - Agregando {can_add}kg de {product['name']}")
                    pallet_weight += can_add
                    product["weight"] -= can_add
                    pallet_contents.append(f"{product['name']}: {can_add}kg")
        
        pallets.append({
            "total_weight": pallet_weight,
            "capacity": pallet_capacity,
            "contents": pallet_contents
        })
        
        print(f"  Pallet completado: {pallet_weight}kg / {pallet_capacity}kg")
        print()
    
    print(f"🎯 RESULTADO BACKEND: {len(pallets)} pallets")
    for i, pallet in enumerate(pallets, 1):
        print(f"Pallet {i}: {pallet['total_weight']}kg / {pallet['capacity']}kg")
        for content in pallet['contents']:
            print(f"  - {content}")
        print()
    
    return len(pallets)

def comparacion_y_solucion():
    """Compara ambos algoritmos y propone solución"""
    print("=" * 60)
    print("COMPARACIÓN Y SOLUCIÓN")
    print("=" * 60)
    
    print("🔍 DIFERENCIA IDENTIFICADA:")
    print("  Frontend: usa MAX capacity (547.2kg) - MÁS OPTIMISTA")
    print("  Backend: usa MIN capacity (70.56kg) - MÁS CONSERVADOR")
    print()
    
    print("❓ ¿CUÁL ES CORRECTO?")
    print("  Depende de la lógica de negocio:")
    print()
    print("  📦 FRONTEND (MAX capacity):")
    print("    • Asume que se puede usar la capacidad máxima disponible")
    print("    • Más eficiente en uso de pallets")
    print("    • Riesgo: puede no respetar restricciones de productos específicos")
    print()
    print("  📦 BACKEND (MIN capacity):")
    print("    • Más conservador, respeta la restricción más estricta")
    print("    • Garantiza que todos los productos caben")
    print("    • Puede desperdiciar espacio")
    print()
    
    print("✅ RECOMENDACIÓN:")
    print("  Sincronizar ambos algoritmos para usar la misma lógica")
    print("  Opción 1: Cambiar backend para usar MAX capacity")
    print("  Opción 2: Cambiar frontend para usar MIN capacity")
    print("  Opción 3: Implementar lógica intermedia más inteligente")

if __name__ == "__main__":
    pallets_frontend = algoritmo_frontend()
    pallets_backend = algoritmo_backend()
    comparacion_y_solucion()
    
    print(f"\n📊 RESUMEN:")
    print(f"  Frontend: {pallets_frontend} pallets")
    print(f"  Backend: {pallets_backend} pallets")
    print(f"  Diferencia: {pallets_backend - pallets_frontend} pallets")
