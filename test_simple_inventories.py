#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Test para verificar el endpoint get_inventories_by_shopping_id
Devuelve precios públicos, privados y fecha de llegada
"""

import requests

def test_get_inventories_endpoint():
    # Shopping ID de ejemplo
    shopping_id = 139
    
    # URL del endpoint
    url = f"http://127.0.0.1:8000/shoppings/get_inventories/{shopping_id}"
    
    print(f"Testing URL: {url}")
    print("=" * 60)
    
    try:
        response = requests.get(url)
        
        if response.status_code == 200:
            data = response.json()
            message = data.get('message', {})
            
            print(f"✅ Status: {message.get('status')}")
            print(f"📝 Message: {message.get('message')}")
            print(f"🛒 Shopping ID: {message.get('shopping_id')}")
            print(f"📦 Total inventarios: {len(message.get('data', []))}")
            print("\n" + "=" * 60)
            
            # Mostrar los datos principales que se necesitan
            for i, item in enumerate(message.get('data', [])[:3], 1):
                print(f"\n📋 INVENTARIO {i}:")
                print(f"   Producto: {item.get('product_name')} ({item.get('product_code')})")
                print(f"   💰 Precio Público: ${item.get('public_sale_price', 0):,.2f}")
                print(f"   🔒 Precio Privado: ${item.get('private_sale_price', 0):,.2f}")
                print(f"   📅 Fecha Llegada: {item.get('arrival_date', 'No especificada')}")
                print(f"   📦 Cantidad: {item.get('quantity', 0)}")
                print(f"   💵 Costo Unitario: ${item.get('unit_cost', 0):,.2f}")
            
            if len(message.get('data', [])) > 3:
                print(f"\n... y {len(message.get('data', [])) - 3} inventarios más")
                
        else:
            print(f"❌ Error HTTP {response.status_code}")
            print(f"Response: {response.text}")
            
    except Exception as e:
        print(f"❌ Error en la petición: {e}")

if __name__ == "__main__":
    test_get_inventories_endpoint()
