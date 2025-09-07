#!/usr/bin/env python3
"""
Demostración de por qué la fórmula individual es correcta para pallets mixtos
"""
import math

def realistic_mixed_pallet_scenario():
    """Escenario realista de pallets mixtos"""
    print("=== ESCENARIO REALISTA: PALLETS MIXTOS ===")
    
    # Productos con restricciones reales
    products = [
        {
            "name": "Cerámica Frágil", 
            "weight_per_unit": 20, 
            "quantity": 50,  # 1000kg total
            "weight_per_pallet": 500,  # Máximo por fragilidad
            "reason": "Limitado por fragilidad - no se puede apilar mucho"
        },
        {
            "name": "Adhesivo Químico", 
            "weight_per_unit": 25, 
            "quantity": 20,  # 500kg total
            "weight_per_pallet": 600,  # Máximo por regulaciones químicas
            "reason": "Limitado por regulaciones de químicos"
        },
        {
            "name": "Herramientas", 
            "weight_per_unit": 5, 
            "quantity": 100,  # 500kg total
            "weight_per_pallet": 2000,  # Sin restricciones especiales
            "reason": "Sin restricciones especiales"
        }
    ]
    
    print("Productos en la orden:")
    for p in products:
        total_weight = p["weight_per_unit"] * p["quantity"]
        print(f"- {p['name']}: {total_weight}kg total")
        print(f"  Limitación: {p['weight_per_pallet']}kg/pallet")
        print(f"  Razón: {p['reason']}")
    
    print(f"\nPeso total: {sum(p['weight_per_unit'] * p['quantity'] for p in products)}kg")
    
    # ¿Qué pasa si intentamos hacer pallets mixtos REALES?
    print(f"\n=== ANÁLISIS DE PALLETS MIXTOS REALES ===")
    
    # Pallet 1: Intentar mezclar frágil + químico
    print("Pallet 1 (Frágil + Químico):")
    print("- Cerámica frágil: máximo 500kg por restricción de fragilidad")
    print("- Adhesivo químico: máximo 600kg por regulación")
    print("- ¿Se pueden mezclar? SÍ, pero el pallet está limitado por el MÁS RESTRICTIVO")
    print("- Capacidad real del pallet mixto: min(500, 600) = 500kg")
    
    fragil_weight = 1000  # Total de cerámica frágil
    quimico_weight = 500  # Total de adhesivo
    
    # Pallet mixto 1: llenar hasta límite de frágil (500kg)
    pallet1_fragil = 500
    pallet1_quimico = 0  # No cabe más por límite de frágil
    remaining_fragil = fragil_weight - pallet1_fragil
    remaining_quimico = quimico_weight - pallet1_quimico
    
    print(f"  Pallet 1: {pallet1_fragil}kg frágil + {pallet1_quimico}kg químico = {pallet1_fragil + pallet1_quimico}kg")
    print(f"  Restante: {remaining_fragil}kg frágil, {remaining_quimico}kg químico")
    
    # Pallet 2: resto de frágil (500kg) - llena el pallet por límite de fragilidad
    pallet2_fragil = remaining_fragil
    pallet2_quimico = 0  # No cabe por límite
    remaining_fragil = 0
    remaining_quimico = remaining_quimico
    
    print(f"  Pallet 2: {pallet2_fragil}kg frágil + {pallet2_quimico}kg químico = {pallet2_fragil + pallet2_quimico}kg")
    print(f"  Restante: {remaining_fragil}kg frágil, {remaining_quimico}kg químico")
    
    # Pallet 3: resto de químico + herramientas
    herramientas_weight = 500
    pallet3_quimico = min(remaining_quimico, 600)  # Máximo por regulación
    pallet3_herramientas = min(herramientas_weight, 600 - pallet3_quimico)  # Lo que quepa
    
    print(f"  Pallet 3: {pallet3_quimico}kg químico + {pallet3_herramientas}kg herramientas = {pallet3_quimico + pallet3_herramientas}kg")
    
    remaining_herramientas = herramientas_weight - pallet3_herramientas
    
    if remaining_herramientas > 0:
        pallet4_herramientas = remaining_herramientas
        print(f"  Pallet 4: {pallet4_herramientas}kg herramientas = {pallet4_herramientas}kg")
        total_pallets_realistic = 4
    else:
        total_pallets_realistic = 3
    
    print(f"\nTotal pallets mixtos reales: {total_pallets_realistic}")
    
    # Comparar con fórmulas
    print(f"\n=== COMPARACIÓN DE FÓRMULAS ===")
    
    # Fórmula individual (la que implementé)
    total_individual = 0
    for p in products:
        total_weight = p["weight_per_unit"] * p["quantity"]
        pallets_needed = math.ceil(total_weight / p["weight_per_pallet"])
        total_individual += pallets_needed
        print(f"- {p['name']}: ceil({total_weight}/{p['weight_per_pallet']}) = {pallets_needed} pallets")
    
    print(f"Fórmula individual: {total_individual} pallets")
    print(f"Realidad mixta optimizada: {total_pallets_realistic} pallets")
    print(f"Diferencia: {total_individual - total_pallets_realistic} pallets")
    
    # La fórmula individual es más conservadora pero más segura
    if total_individual >= total_pallets_realistic:
        print("✅ La fórmula individual es CONSERVADORA - garantiza capacidad suficiente")
        print("📦 Es preferible tener pallets de sobra que quedarse corto")
    else:
        print("⚠️  La fórmula individual subestima - necesita optimización")

def optimized_mixed_pallet_formula():
    """Fórmula optimizada que considera pallets mixtos reales"""
    print(f"\n=== PROPUESTA DE FÓRMULA OPTIMIZADA ===")
    
    print("""
FÓRMULA ACTUAL (Conservadora - la que implementé):
- Calcula pallets por producto individualmente
- Suma todos los pallets necesarios
- VENTAJA: Garantiza capacidad suficiente
- DESVENTAJA: Puede sobreestimar en algunos casos

FÓRMULA OPTIMIZADA (para pallets mixtos reales):
1. Ordenar productos por restricción de peso (más restrictivo primero)
2. Simular llenado de pallets respetando la restricción más limitante
3. Optimizar combinaciones cuando sea posible

CÓDIGO OPTIMIZADO:
```python
def calculate_mixed_pallets_optimized(products):
    pallets = []
    remaining_products = products.copy()
    
    while any(p['remaining_weight'] > 0 for p in remaining_products):
        # Nuevo pallet
        current_pallet_capacity = min(p['weight_per_pallet'] for p in remaining_products if p['remaining_weight'] > 0)
        current_pallet_weight = 0
        
        # Llenar pallet respetando restricciones
        for product in remaining_products:
            if product['remaining_weight'] > 0:
                max_can_add = min(
                    product['remaining_weight'],
                    product['weight_per_pallet'],
                    current_pallet_capacity - current_pallet_weight
                )
                current_pallet_weight += max_can_add
                product['remaining_weight'] -= max_can_add
        
        pallets.append(current_pallet_weight)
    
    return len(pallets)
```

RECOMENDACIÓN:
- Usar fórmula individual (actual) para garantizar capacidad
- Implementar optimización como mejora futura
- Para casos críticos, usar simulación detallada
""")

if __name__ == "__main__":
    realistic_mixed_pallet_scenario()
    optimized_mixed_pallet_formula()
