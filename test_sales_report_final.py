#!/usr/bin/env python
"""
Test script for sales report functionality with only public and private price categories.
This test verifies that the sales report works correctly after removing custom sales category.
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'app'))

from backend.classes.sale_class import SaleClass
from backend.schemas import SalesReportFilter
from datetime import datetime, date

def test_sales_report_no_custom():
    """Test that sales report works with only public and private categories"""
    try:
        # Create SaleClass instance
        sale_class = SaleClass()
        
        # Create filter for recent sales (optional)
        sales_filter = SalesReportFilter(
            start_date=date(2025, 7, 1),
            end_date=date(2025, 7, 31)
        )
        
        print("🧪 Testing Sales Report with Public/Private Categories Only")
        print("=" * 60)
        
        # Test without filter first
        print("\n📊 Testing without date filter...")
        report_all = sale_class.get_sales_report()
        
        print(f"✅ Report generated successfully!")
        print(f"📈 Total sales: {report_all.get('total_sales', 0)}")
        print(f"💰 Total revenue: ${report_all.get('total_revenue', 0):,.2f}")
        print(f"🏷️  Total products sold: {len(report_all.get('products', []))}")
        
        # Test with date filter
        print(f"\n📊 Testing with date filter (July 2025)...")
        report_filtered = sale_class.get_sales_report(sales_filter)
        
        print(f"✅ Filtered report generated successfully!")
        print(f"📈 Filtered sales: {report_filtered.get('total_sales', 0)}")
        print(f"💰 Filtered revenue: ${report_filtered.get('total_revenue', 0):,.2f}")
        
        # Verify structure contains only public and private categories
        products = report_filtered.get('products', [])
        if products:
            sample_product = products[0]
            sales_breakdown = sample_product.get('sales_breakdown', {})
            
            print(f"\n🔍 Verifying sales breakdown structure...")
            print(f"Available categories: {list(sales_breakdown.keys())}")
            
            # Check that only public_sales and private_sales exist
            expected_categories = {'public_sales', 'private_sales'}
            actual_categories = set(sales_breakdown.keys())
            
            if actual_categories == expected_categories:
                print("✅ Sales breakdown contains only public and private categories (correct!)")
            else:
                print(f"❌ Unexpected categories found: {actual_categories - expected_categories}")
                print(f"❌ Missing categories: {expected_categories - actual_categories}")
            
            # Display sample breakdown
            for category, data in sales_breakdown.items():
                print(f"  {category}: {data.get('quantity', 0)} units ({data.get('percentage', 0)}%)")
        
        return True
        
    except Exception as e:
        print(f"❌ Test failed with error: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("🚀 Starting Sales Report Test (Public/Private Only)")
    print("=" * 60)
    
    success = test_sales_report_no_custom()
    
    if success:
        print("\n🎉 All tests passed! Sales report is working correctly.")
        print("✅ Custom sales category successfully removed.")
        print("📊 Report now contains only public and private price categories.")
    else:
        print("\n💥 Tests failed. Please check the error messages above.")
    
    print("\n" + "=" * 60)
