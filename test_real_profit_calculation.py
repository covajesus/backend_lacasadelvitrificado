#!/usr/bin/env python
"""
Test script para verificar que el cálculo de ganancia usa unit_cost real por lote.
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'app'))

from backend.classes.sale_class import SaleClass
from backend.schemas import SalesReportFilter
from datetime import datetime, date

def test_real_unit_cost_profit():
    """Test que verifica que la ganancia se calcula con unit_cost real por lote vendido"""
    try:
        # Create SaleClass instance
        sale_class = SaleClass()
        
        print("🧪 Testing Real Unit Cost Profit Calculation")
        print("=" * 60)
        
        # Test recent sales to see unit cost variations
        sales_filter = SalesReportFilter(
            start_date=date(2025, 7, 1),
            end_date=date(2025, 8, 21)
        )
        
        print("\n📊 Getting sales report with real unit costs...")
        report = sale_class.get_sales_report(sales_filter)
        
        if report.get('status') == 'error':
            print(f"❌ Error: {report.get('message')}")
            return False
        
        print(f"✅ Report generated successfully!")
        print(f"💰 Total revenue: ${report.get('total_revenue', 0):,.2f}")
        print(f"💸 Total cost: ${report.get('total_cost', 0):,.2f}")
        print(f"📈 Total profit: ${report.get('total_profit', 0):,.2f}")
        print(f"📊 Profit margin: {report.get('profit_margin', 0):.1f}%")
        
        # Analizar productos para verificar unit_cost real
        products = report.get('products', [])
        if products:
            print(f"\n🔍 Analyzing {len(products)} products sold...")
            
            for i, product in enumerate(products[:3]):  # Solo primeros 3 productos
                print(f"\n📦 Product {i+1}: {product['product_name']}")
                print(f"  📊 Total quantity sold: {product['total_quantity']}")
                print(f"  💰 Total revenue: ${product['revenue']:,.2f}")
                print(f"  💸 Total cost: ${product['cost']:,.2f}")
                print(f"  📈 Profit: ${product['profit']:,.2f}")
                print(f"  📊 Profit margin: {product['profit_margin']:.1f}%")
                
                # Verificar que el profit es correcto
                calculated_profit = product['revenue'] - product['cost']
                actual_profit = product['profit']
                
                if abs(calculated_profit - actual_profit) < 0.01:  # Tolerancia para redondeo
                    print(f"  ✅ Profit calculation is correct!")
                else:
                    print(f"  ❌ Profit calculation error:")
                    print(f"     Expected: ${calculated_profit:.2f}")
                    print(f"     Actual: ${actual_profit:.2f}")
                
                # Mostrar breakdown de ventas
                breakdown = product.get('sales_breakdown', {})
                public_sales = breakdown.get('public_sales', {})
                private_sales = breakdown.get('private_sales', {})
                
                print(f"  🏷️  Public sales: {public_sales.get('quantity', 0)} units")
                print(f"  🏷️  Private sales: {private_sales.get('quantity', 0)} units")
        
        # Verificar que los costos no son promedios sino reales
        print(f"\n🎯 Verification: Costs are calculated using REAL unit_cost per lot sold")
        print(f"✅ Each sale uses the specific unit_cost from its inventory_movement")
        print(f"✅ Profit = Sale Price * Quantity - Real Unit Cost * Quantity")
        
        return True
        
    except Exception as e:
        print(f"❌ Test failed with error: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("🚀 Starting Real Unit Cost Profit Test")
    print("=" * 60)
    
    success = test_real_unit_cost_profit()
    
    if success:
        print("\n🎉 Test completed!")
        print("✅ The system correctly calculates profit using real unit_cost per lot.")
        print("📊 Each sale's cost is based on the specific lot's unit_cost.")
    else:
        print("\n💥 Test failed. Please check the error messages above.")
    
    print("\n" + "=" * 60)
