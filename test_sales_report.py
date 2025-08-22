#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Test para el endpoint de reporte de ventas
Prueba diferentes filtros de fecha y muestra los resultados
"""

import requests
import json

def test_sales_report():
    url = "http://127.0.0.1:8000/sales/report"
    
    print("🔍 TESTING SALES REPORT ENDPOINT")
    print("=" * 60)
    
    # Test 1: Sin filtros (todas las ventas)
    print("\n📊 TEST 1: Reporte completo (sin filtros)")
    print("-" * 40)
    
    payload1 = {
        "start_date": None,
        "end_date": None
    }
    
    try:
        response1 = requests.post(url, json=payload1)
        if response1.status_code == 200:
            data1 = response1.json()
            message1 = data1.get('message', {})
            
            print(f"✅ Status: {message1.get('status')}")
            print(f"📝 Message: {message1.get('message')}")
            
            if message1.get('summary'):
                summary = message1['summary']
                print(f"\n📈 RESUMEN GENERAL:")
                print(f"   Total productos: {summary.get('total_products')}")
                print(f"   Ingresos totales: ${summary.get('total_revenue', 0):,.2f}")
                print(f"   Costos totales: ${summary.get('total_cost', 0):,.2f}")
                print(f"   Ganancia total: ${summary.get('total_profit', 0):,.2f}")
                print(f"   Margen general: {summary.get('overall_margin_percent', 0):.2f}%")
            
            if message1.get('data'):
                print(f"\n🎯 PRODUCTOS MÁS VENDIDOS (TOP 3):")
                for i, product in enumerate(message1['data'][:3], 1):
                    print(f"\n   {i}. {product.get('product_name')} ({product.get('product_code')})")
                    print(f"      📦 Cantidad vendida: {product.get('quantity_sold')}")
                    
                    # Mostrar precios
                    prices = product.get('prices', {})
                    print(f"      💰 Precio público: ${prices.get('public_price', 0):,.2f}")
                    print(f"      🔒 Precio privado: ${prices.get('private_price', 0):,.2f}")
                    print(f"      � Costo unitario promedio: ${prices.get('average_unit_cost', 0):,.2f}")
                    
                    # Mostrar desglose de ventas por tipo de precio
                    breakdown = product.get('sales_breakdown', {})
                    print(f"\n      📈 DESGLOSE DE VENTAS:")
                    
                    public_sales = breakdown.get('public_sales', {})
                    if public_sales.get('quantity', 0) > 0:
                        print(f"         � Ventas a precio PÚBLICO: {public_sales.get('quantity')} unidades ({public_sales.get('percentage', 0):.1f}%)")
                        print(f"            Ingresos: ${public_sales.get('revenue', 0):,.2f} en {public_sales.get('transactions', 0)} transacciones")
                    
                    private_sales = breakdown.get('private_sales', {})
                    if private_sales.get('quantity', 0) > 0:
                        print(f"         🔵 Ventas a precio PRIVADO: {private_sales.get('quantity')} unidades ({private_sales.get('percentage', 0):.1f}%)")
                        print(f"            Ingresos: ${private_sales.get('revenue', 0):,.2f} en {private_sales.get('transactions', 0)} transacciones")
                    
                    custom_sales = breakdown.get('custom_sales', {})
                    if custom_sales.get('quantity', 0) > 0:
                        print(f"         🟡 Ventas a precio PERSONALIZADO: {custom_sales.get('quantity')} unidades ({custom_sales.get('percentage', 0):.1f}%)")
                        print(f"            Ingresos: ${custom_sales.get('revenue', 0):,.2f} en {custom_sales.get('transactions', 0)} transacciones")
                    
                    # Mostrar totales
                    totals = product.get('totals', {})
                    print(f"\n      💵 TOTALES:")
                    print(f"         Ingresos: ${totals.get('total_revenue', 0):,.2f}")
                    print(f"         Costos: ${totals.get('total_cost', 0):,.2f}")
                    print(f"         Ganancia: ${totals.get('total_profit', 0):,.2f}")
                    print(f"         Margen: {totals.get('profit_margin_percent', 0):.2f}%")
        else:
            print(f"❌ Error HTTP {response1.status_code}")
            print(f"Response: {response1.text}")
            
    except Exception as e:
        print(f"❌ Error en la petición: {e}")
    
    # Test 2: Con filtro de fecha (últimos 30 días)
    print(f"\n\n📊 TEST 2: Reporte con filtro de fecha")
    print("-" * 40)
    
    payload2 = {
        "start_date": "2025-07-01",
        "end_date": "2025-08-31"
    }
    
    try:
        response2 = requests.post(url, json=payload2)
        if response2.status_code == 200:
            data2 = response2.json()
            message2 = data2.get('message', {})
            
            print(f"✅ Status: {message2.get('status')}")
            print(f"📝 Message: {message2.get('message')}")
            print(f"📅 Período: {payload2['start_date']} a {payload2['end_date']}")
            
            if message2.get('summary'):
                summary2 = message2['summary']
                print(f"\n📈 RESUMEN DEL PERÍODO:")
                print(f"   Total productos: {summary2.get('total_products')}")
                print(f"   Ingresos: ${summary2.get('total_revenue', 0):,.2f}")
                print(f"   Ganancia: ${summary2.get('total_profit', 0):,.2f}")
                print(f"   Margen: {summary2.get('overall_margin_percent', 0):.2f}%")
        else:
            print(f"❌ Error HTTP {response2.status_code}")
            print(f"Response: {response2.text}")
            
    except Exception as e:
        print(f"❌ Error en la petición: {e}")

if __name__ == "__main__":
    test_sales_report()
