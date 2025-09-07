#!/usr/bin/env python3
"""
Análisis del problema real con los datos específicos del usuario
"""

def analizar_datos_reales():
    """Analiza los datos reales del problema"""
    print("=" * 60)
    print("ANÁLISIS DE LOS DATOS REALES DEL PROBLEMA")
    print("=" * 60)
    
    # Datos exactos del log del usuario
    productos_reales = [
        {
            'name': 'AquaSeal® CeramicStar (Mate)',
            'total_weight': 24.04,
            'weight_per_pallet': 378.63
        },
        {
            'name': 'AquaSeal® CeramicStar Harter',
            'total_weight': 2.24,
            'weight_per_pallet': 70.56
        },
        {
            'name': 'AquaSeal® EcoGold (Mate)',
            'total_weight': 1140.0,
            'weight_per_pallet': 547.2
        }
    ]
    
    print("📦 DATOS DE LOS PRODUCTOS:")
    peso_total = 0
    for i, p in enumerate(productos_reales, 1):
        print(f"{i}. {p['name']}")
        print(f"   • Peso total: {p['total_weight']}kg")
        print(f"   • Capacidad por pallet: {p['weight_per_pallet']}kg")
        peso_total += p['total_weight']
        print()
    
    print(f"PESO TOTAL DE LA ORDEN: {peso_total}kg")
    print()
    
    # Aplicar nuestra fórmula actual
    def calculate_real_mixed_pallets(products_info):
        """Fórmula actual implementada"""
        remaining = [{"name": p["name"], "weight": p["total_weight"], "capacity": p["weight_per_pallet"]} for p in products_info]
        pallets = []
        
        while any(p["weight"] > 0 for p in remaining):
            # Nuevo pallet
            active = [p for p in remaining if p["weight"] > 0]
            if not active:
                break
            
            # AQUÍ ESTÁ EL PROBLEMA: Capacidad = mínima de productos activos
            pallet_capacity = min(p["capacity"] for p in active)
            pallet_weight = 0
            pallet_contents = []
            
            print(f"Nuevo pallet - Capacidad limitada a: {pallet_capacity}kg")
            
            # Llenar pallet con productos disponibles
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
        
        return pallets
    
    print("🔄 APLICANDO NUESTRA FÓRMULA ACTUAL:")
    print("-" * 40)
    
    calculated_pallets = calculate_real_mixed_pallets(productos_reales)
    
    print(f"🎯 RESULTADO:")
    print(f"Total de pallets: {len(calculated_pallets)}")
    print()
    
    for i, pallet in enumerate(calculated_pallets, 1):
        print(f"Pallet {i}: {pallet['total_weight']}kg / {pallet['capacity']}kg")
        for content in pallet['contents']:
            print(f"  - {content}")
        print()
    
    return len(calculated_pallets)

def identificar_problema():
    """Identifica exactamente cuál es el problema"""
    print("=" * 60)
    print("IDENTIFICACIÓN DEL PROBLEMA")
    print("=" * 60)
    
    productos = [
        {'name': 'CeramicStar (Mate)', 'weight': 24.04, 'capacity': 378.63},
        {'name': 'CeramicStar Harter', 'weight': 2.24, 'capacity': 70.56},
        {'name': 'EcoGold (Mate)', 'weight': 1140.0, 'capacity': 547.2}
    ]
    
    print("🔍 ANÁLISIS DEL PROBLEMA:")
    print()
    
    print("1. CAPACIDADES POR PALLET:")
    for p in productos:
        print(f"   • {p['name']}: {p['capacity']}kg")
    
    min_capacity = min(p['capacity'] for p in productos)
    print(f"\n2. CAPACIDAD MÍNIMA: {min_capacity}kg")
    print(f"   (Producto más restrictivo: CeramicStar Harter)")
    
    peso_total = sum(p['weight'] for p in productos)
    print(f"\n3. PESO TOTAL: {peso_total}kg")
    
    pallets_con_minima = peso_total / min_capacity
    print(f"\n4. PALLETS NECESARIOS CON CAPACIDAD MÍNIMA:")
    print(f"   {peso_total}kg ÷ {min_capacity}kg = {pallets_con_minima:.2f}")
    print(f"   Redondeando hacia arriba: {int(pallets_con_minima) + 1} pallets")
    
    print(f"\n❌ PROBLEMA IDENTIFICADO:")
    print(f"   La fórmula usa la capacidad MÁS RESTRICTIVA para TODOS los pallets")
    print(f"   Esto desperdicia mucho espacio en los pallets")
    print(f"   El producto EcoGold (1140kg) podría ir en 3 pallets de 547.2kg")
    print(f"   Pero el algoritmo lo limita a pallets de solo 70.56kg")

def proponer_solucion():
    """Propone una solución mejorada"""
    print("=" * 60)
    print("SOLUCIÓN PROPUESTA")
    print("=" * 60)
    
    productos = [
        {'name': 'CeramicStar (Mate)', 'weight': 24.04, 'capacity': 378.63},
        {'name': 'CeramicStar Harter', 'weight': 2.24, 'capacity': 70.56},
        {'name': 'EcoGold (Mate)', 'weight': 1140.0, 'capacity': 547.2}
    ]
    
    print("✅ SOLUCIÓN MEJORADA:")
    print("Calcular pallets por producto individualmente, luego optimizar")
    print()
    
    import math
    
    total_pallets = 0
    for p in productos:
        pallets_individuales = math.ceil(p['weight'] / p['capacity'])
        print(f"• {p['name']}: ceil({p['weight']} / {p['capacity']}) = {pallets_individuales} pallets")
        total_pallets += pallets_individuales
    
    print(f"\nTotal (fórmula individual): {total_pallets} pallets")
    print()
    
    print("🎯 COMPARACIÓN:")
    print(f"   Fórmula actual (problemática): ~17 pallets")
    print(f"   Fórmula individual (conservadora): {total_pallets} pallets")
    print(f"   Diferencia: {17 - total_pallets} pallets menos con fórmula individual")

if __name__ == "__main__":
    pallets_calculados = analizar_datos_reales()
    identificar_problema()
    proponer_solucion()
