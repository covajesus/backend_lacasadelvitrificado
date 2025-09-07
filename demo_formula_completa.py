#!/usr/bin/env python3
"""
Demostración detallada de la fórmula correcta de pallets con ejemplos paso a paso
"""

def mostrar_formula_con_ejemplos():
    """Muestra la fórmula implementada con ejemplos detallados"""
    print("=== FÓRMULA CORRECTA DE PALLETS MIXTOS ===")
    print("Implementada en template_class.py")
    print()
    
    # EJEMPLO 1: Caso simple
    print("📦 EJEMPLO 1: Caso básico")
    print("-" * 40)
    
    productos_ejemplo1 = [
        {"nombre": "Cerámica A", "peso_total": 300, "max_por_pallet": 1000},
        {"nombre": "Cerámica B", "peso_total": 400, "max_por_pallet": 800},
        {"nombre": "Adhesivo", "peso_total": 200, "max_por_pallet": 600}
    ]
    
    print("Productos en la orden:")
    for p in productos_ejemplo1:
        print(f"  • {p['nombre']}: {p['peso_total']}kg (máximo {p['max_por_pallet']}kg por pallet)")
    
    print(f"\nPeso total: {sum(p['peso_total'] for p in productos_ejemplo1)}kg")
    
    # Simular algoritmo paso a paso
    print(f"\n🔄 PROCESO DE LLENADO DE PALLETS:")
    
    # Estado inicial
    remaining = [{"name": p["nombre"], "weight": p["peso_total"], "capacity": p["max_por_pallet"]} for p in productos_ejemplo1]
    pallets = []
    
    paso = 1
    while any(p["weight"] > 0 for p in remaining):
        print(f"\n--- PASO {paso}: Nuevo Pallet ---")
        
        # Productos activos (que aún tienen peso)
        active = [p for p in remaining if p["weight"] > 0]
        print("Productos restantes:")
        for p in active:
            print(f"  • {p['name']}: {p['weight']}kg restante (máx {p['capacity']}kg/pallet)")
        
        # Capacidad del pallet = la más restrictiva
        pallet_capacity = min(p["capacity"] for p in active)
        print(f"\n🏗️ Capacidad del pallet: {pallet_capacity}kg (limitada por el producto más restrictivo)")
        
        pallet_weight = 0
        pallet_contents = []
        
        print(f"\n📥 Llenando el pallet:")
        
        # Llenar pallet
        for product in remaining:
            if product["weight"] > 0 and pallet_weight < pallet_capacity:
                space_available = pallet_capacity - pallet_weight
                can_add = min(product["weight"], space_available)
                
                if can_add > 0:
                    print(f"  + Agregando {can_add}kg de {product['name']}")
                    print(f"    (espacio disponible: {space_available}kg, producto restante: {product['weight']}kg)")
                    
                    pallet_weight += can_add
                    product["weight"] -= can_add
                    pallet_contents.append(f"{product['name']}: {can_add}kg")
        
        pallets.append({
            "peso": pallet_weight,
            "capacidad": pallet_capacity,
            "contenido": pallet_contents
        })
        
        print(f"\n✅ Pallet {paso} completado: {pallet_weight}kg / {pallet_capacity}kg")
        paso += 1
    
    print(f"\n🎯 RESULTADO FINAL:")
    print(f"Total de pallets necesarios: {len(pallets)}")
    for i, pallet in enumerate(pallets, 1):
        print(f"  Pallet {i}: {pallet['peso']}kg / {pallet['capacidad']}kg")
        for contenido in pallet['contenido']:
            print(f"    - {contenido}")

def ejemplo_extremo():
    """Ejemplo extremo que muestra las ventajas de la fórmula"""
    print(f"\n\n📦 EJEMPLO 2: Caso extremo (productos muy diferentes)")
    print("-" * 60)
    
    productos_extremo = [
        {"nombre": "Material Frágil", "peso_total": 1000, "max_por_pallet": 300},    # Muy restrictivo
        {"nombre": "Material Resistente", "peso_total": 500, "max_por_pallet": 2000}, # Muy flexible
        {"nombre": "Material Medio", "peso_total": 400, "max_por_pallet": 800}       # Medio
    ]
    
    print("Productos en la orden:")
    for p in productos_extremo:
        print(f"  • {p['nombre']}: {p['peso_total']}kg (máximo {p['max_por_pallet']}kg por pallet)")
    
    print(f"\nPeso total: {sum(p['peso_total'] for p in productos_extremo)}kg")
    
    # Comparación de fórmulas
    import math
    
    print(f"\n📊 COMPARACIÓN DE FÓRMULAS:")
    
    # Fórmula original (muy incorrecta)
    peso_total = sum(p['peso_total'] for p in productos_extremo)
    suma_capacidades = sum(p['max_por_pallet'] for p in productos_extremo)
    formula_original = math.ceil(peso_total / suma_capacidades)
    
    print(f"1️⃣ Fórmula original (incorrecta):")
    print(f"   ceil({peso_total} / {suma_capacidades}) = {formula_original} pallet")
    print(f"   ❌ Muy optimista, no considera restricciones")
    
    # Fórmula individual (conservadora)
    formula_individual = sum(math.ceil(p['peso_total'] / p['max_por_pallet']) for p in productos_extremo)
    print(f"\n2️⃣ Fórmula individual (conservadora):")
    for p in productos_extremo:
        pallets_producto = math.ceil(p['peso_total'] / p['max_por_pallet'])
        print(f"   {p['nombre']}: ceil({p['peso_total']} / {p['max_por_pallet']}) = {pallets_producto} pallets")
    print(f"   Total: {formula_individual} pallets")
    print(f"   ⚠️ Muy conservadora, no optimiza espacios")
    
    # Nueva fórmula (optimizada)
    print(f"\n3️⃣ Nueva fórmula (optimizada y realista):")
    
    remaining = [{"name": p["nombre"], "weight": p["peso_total"], "capacity": p["max_por_pallet"]} for p in productos_extremo]
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
            "peso": pallet_weight,
            "capacidad": pallet_capacity,
            "contenido": pallet_contents
        })
    
    for i, pallet in enumerate(pallets, 1):
        print(f"   Pallet {i}: {pallet['peso']}kg / {pallet['capacidad']}kg")
        for contenido in pallet['contenido']:
            print(f"     - {contenido}")
    
    print(f"   Total: {len(pallets)} pallets")
    print(f"   ✅ Optimiza espacios respetando restricciones")
    
    print(f"\n📈 COMPARACIÓN FINAL:")
    print(f"   Fórmula original: {formula_original} pallets (muy optimista)")
    print(f"   Fórmula individual: {formula_individual} pallets (conservadora)")
    print(f"   Nueva fórmula: {len(pallets)} pallets (optimizada)")
    
    ahorro = formula_individual - len(pallets)
    if ahorro > 0:
        print(f"   💰 Ahorro: {ahorro} pallets vs fórmula conservadora")
    
    diferencia_original = len(pallets) - formula_original
    print(f"   ⚖️ Diferencia vs original: +{diferencia_original} pallets (más realista)")

def mostrar_codigo_implementado():
    """Muestra el código exacto implementado en template_class.py"""
    print(f"\n\n💻 CÓDIGO IMPLEMENTADO EN TEMPLATE_CLASS.PY:")
    print("=" * 50)
    
    codigo = '''
def calculate_real_mixed_pallets(products_info):
    """Algoritmo correcto para pallets mixtos - permite compartir pallets"""
    remaining = [
        {
            "name": p["name"], 
            "weight": p["total_weight"], 
            "capacity": p["weight_per_pallet"]
        } 
        for p in products_info
    ]
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

# Uso en el template:
calculated_pallets = calculate_real_mixed_pallets(products_info)
how_many_pallets = len(calculated_pallets)
'''
    
    print(codigo)
    
    print("🔑 PUNTOS CLAVE DE LA FÓRMULA:")
    print("1️⃣ Simula llenado real de pallets")
    print("2️⃣ Respeta restricciones por producto")
    print("3️⃣ Optimiza uso de espacio disponible")
    print("4️⃣ Maneja productos con capacidades muy diferentes")
    print("5️⃣ Más precisa que fórmulas anteriores")

if __name__ == "__main__":
    mostrar_formula_con_ejemplos()
    ejemplo_extremo()
    mostrar_codigo_implementado()
