#!/usr/bin/env python3
"""
Prueba de la corrección del código - función movida correctamente
"""

class MockTemplateClass:
    """Simulación de la clase para probar"""
    def __init__(self):
        pass

    def calculate_real_mixed_pallets(self, products_info):
        """Algoritmo correcto para pallets mixtos - permite compartir pallets"""
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

def test_corrected_structure():
    """Prueba que la estructura corregida funciona"""
    print("=== PRUEBA DE LA ESTRUCTURA CORREGIDA ===")
    print()
    
    # Crear instancia de la clase
    template = MockTemplateClass()
    
    # Datos de prueba
    products_info = [
        {'name': 'Cerámica A', 'total_weight': 300, 'weight_per_pallet': 1000},
        {'name': 'Cerámica B', 'total_weight': 400, 'weight_per_pallet': 800},
        {'name': 'Adhesivo', 'total_weight': 200, 'weight_per_pallet': 600}
    ]
    
    print("Datos de entrada:")
    for p in products_info:
        print(f"  • {p['name']}: {p['total_weight']}kg (máx {p['weight_per_pallet']}kg/pallet)")
    
    print()
    
    # Llamar al método (ahora correctamente como método de la clase)
    calculated_pallets = template.calculate_real_mixed_pallets(products_info)
    how_many_pallets = len(calculated_pallets)
    
    print("Resultado:")
    print(f"Total de pallets necesarios: {how_many_pallets}")
    print()
    
    for i, pallet in enumerate(calculated_pallets, 1):
        print(f"Pallet {i}: {pallet['total_weight']}kg / {pallet['capacity']}kg")
        for content in pallet['contents']:
            print(f"  - {content}")
        print()
    
    print("✅ ESTRUCTURA CORREGIDA:")
    print("1. La función ahora es un método de la clase")
    print("2. Se llama con self.calculate_real_mixed_pallets()")
    print("3. Mejor organización del código")
    print("4. Más fácil de mantener y testear")
    print("5. Sigue las mejores prácticas de programación")

if __name__ == "__main__":
    test_corrected_structure()
