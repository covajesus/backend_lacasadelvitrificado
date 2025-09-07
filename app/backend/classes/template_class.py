from app.backend.schemas import ShoppingCreateInput
import pdfkit
from io import BytesIO
from app.backend.db.models import SupplierModel, ProductModel, CategoryModel, UnitFeatureModel, ShoppingProductModel, SettingModel, ShoppingModel
from datetime import datetime
import math

class TemplateClass:
    def __init__(self, db):
        self.db = db
    
    def format_number(self, value):
        """Formatea números para mostrar enteros sin decimales y decimales cuando es necesario"""
        if value == int(value):
            return str(int(value))
        else:
            return f"{value:.2f}"

    def calculate_shopping_totals(self, data: ShoppingCreateInput, shopping_id: int):
        """Calcula todos los totales necesarios para el template"""
        total_kg = 0.0
        total_lts = 0.0
        total_und = 0.0
        total_shipping_kg = 0.0
        total_without_discount = 0.0
        products_info = []

        # Obtener información del shopping para verificar si hay prepago
        shopping = self.db.query(ShoppingModel).filter(ShoppingModel.id == shopping_id).first()
        has_prepaid = shopping and shopping.prepaid_status_id is not None

        # Obtener el descuento de settings si hay prepago
        prepaid_discount_percentage = 0.0
        if has_prepaid:
            settings = self.db.query(SettingModel).first()
            if settings and hasattr(settings, 'prepaid_discount') and settings.prepaid_discount:
                try:
                    prepaid_discount_percentage = float(settings.prepaid_discount)
                except (ValueError, TypeError):
                    prepaid_discount_percentage = 0.0

        for item in data.products:
            # Obtener datos del producto
            product_data = self.db.query(ProductModel).filter(ProductModel.id == item.product_id).first()
            unit_feature = self.db.query(UnitFeatureModel).filter(UnitFeatureModel.product_id == item.product_id).first()
            shopping_product = self.db.query(ShoppingProductModel).filter(
                ShoppingProductModel.shopping_id == shopping_id, 
                ShoppingProductModel.product_id == item.product_id
            ).first()

            if not shopping_product:
                continue

            # Calcular totales por unidad de medida
            if item.unit_measure_id == 1:  # Kilogramos
                total_kg += float(shopping_product.quantity_per_package)
            elif item.unit_measure_id == 2:  # Litros
                total_lts += float(shopping_product.quantity_per_package)
            elif item.unit_measure_id == 3:  # Unidades
                total_und += float(shopping_product.quantity_per_package)

            # Calcular peso total para envío
            if unit_feature:
                weight_per_unit = float(unit_feature.weight_per_unit) if unit_feature.weight_per_unit else 0.0
                product_total_weight = weight_per_unit * float(shopping_product.quantity)
                total_shipping_kg += product_total_weight
                
                # Para cálculo de pallets
                weight_per_pallet = float(unit_feature.weight_per_pallet) if unit_feature.weight_per_pallet else 1000.0
                products_info.append({
                    'name': product_data.product if product_data else 'Unknown',
                    'total_weight': product_total_weight,
                    'weight_per_pallet': weight_per_pallet
                })

            # Calcular total sin descuento
            if shopping_product.original_unit_cost and shopping_product.quantity:
                total_without_discount += float(shopping_product.original_unit_cost) * float(shopping_product.quantity)

        # Calcular pallets usando el algoritmo correcto
        calculated_pallets = self.calculate_real_mixed_pallets(products_info)
        total_pallets = len(calculated_pallets)

        # Calcular total con descuento si hay prepago
        total_with_discount = None
        if has_prepaid and prepaid_discount_percentage > 0:
            total_with_discount = total_without_discount * (1 - prepaid_discount_percentage / 100)

        return {
            'total_kg': total_kg,
            'total_lts': total_lts,
            'total_und': total_und,
            'total_shipping_kg': total_shipping_kg,
            'total_pallets': total_pallets,
            'total_without_discount': total_without_discount,
            'has_prepaid': has_prepaid,
            'prepaid_discount_percentage': prepaid_discount_percentage,
            'total_with_discount': total_with_discount
        }

    def calculate_real_mixed_pallets(self, products_info):
        """Algoritmo correcto para pallets mixtos - permite compartir pallets"""
        remaining = [{"name": p["name"], "weight": p["total_weight"], "capacity": p["weight_per_pallet"]} for p in products_info]
        pallets = []
        
        while any(p["weight"] > 0 for p in remaining):
            # Nuevo pallet
            active = [p for p in remaining if p["weight"] > 0]
            if not active:
                break
            
            # Capacidad del pallet = MÁXIMA de productos activos (sincronizado con frontend)
            pallet_capacity = max(p["capacity"] for p in active)
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

    def generate_shopping_html_for_own_company(self, data: ShoppingCreateInput, id) -> str:
        logo_url = "file:/var/www/api.lacasadelvitrificado.com/public/assets/logo.png"
        vitrificado_logo_url = "file:/var/www/api.lacasadelvitrificado.com/public/assets/vitrificado-logo.png"
        supplier_data = self.db.query(SupplierModel).filter(SupplierModel.id == data.supplier_id).first()
        date = datetime.utcnow().strftime("%Y-%m-%d")

        html = f"""
        <html>
        <head>
        <meta charset="utf-8">
        <style>
            body {{ font-family: Arial, sans-serif; font-size: 14px; }}
            table {{ border-collapse: collapse; width: 100%; margin-top: 20px; }}
            th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
            th {{ background-color: #f2f2f2; }}
            .logo {{ width: 200px; }}
            .vitrificado_logo {{ width: 120px; }}
            .header {{
                display: flex;
                justify-content: space-between;
                align-items: center;
                margin-bottom: 20px;
            }}
            .title {{ text-align: center; margin-top: 20px; margin-bottom: 30px; }}
        </style>
        </head>
        <body>
        <div class="header">
            <img src="{vitrificado_logo_url}" class="vitrificado_logo float-left" />
            &ensp;&ensp;&ensp;&ensp;&ensp;&ensp;&ensp;&ensp;&ensp;&ensp;&ensp;&ensp;&ensp;&ensp;&ensp;&ensp;
            &ensp;&ensp;&ensp;&ensp;&ensp;&ensp;&ensp;&ensp;&ensp;&ensp;&ensp;&ensp;&ensp;&ensp;&ensp;&ensp;&ensp;
            &ensp;&ensp;&ensp;&ensp;&ensp;&ensp;&ensp;&ensp;&ensp;&ensp;&ensp;&ensp;&ensp;&ensp;&ensp;&ensp;
            &ensp;&ensp;&ensp;&ensp;&ensp;&ensp;&ensp;&ensp;&ensp;&ensp;&ensp;&ensp;&ensp;&ensp;&ensp;&ensp;&ensp;
            &ensp;&ensp;&ensp;&ensp;&ensp;&ensp;&ensp;&ensp;&ensp;&ensp;
            <img src="{logo_url}" class="logo float-right" />
        </div>

        <div class="title">
            <h2>Purchase Order #{id}</h2>
        </div>

        <div>
            Date: {date}
        </div>

        <table>
            <thead>
            <tr>
                <th>Pos Item no.</th>
                <th>Description</th>
                <th>Cont</th>
                <th>Kg/Lts/Un</th>
                <th>Price</th>
                <th>Amount</th>
            </tr>
            </thead>
            <tbody>
        """

        # Ordenar productos por category_id
        sorted_products = sorted(data.products, key=lambda p: p.category_id)
        current_category_id = None

        for item in sorted_products:
            product_data = self.db.query(ProductModel).filter(ProductModel.id == item.product_id).first()
            unit = {1: "Kg", 2: "Lts", 3: "Und"}.get(item.unit_measure_id, "")

            if item.category_id != current_category_id:
                category_data = self.db.query(CategoryModel).filter(CategoryModel.id == item.category_id).first()
                html += f"""
                <tr>
                    <td colspan="6" style="background-color: {category_data.color}; font-weight: bold; text-align: center; font-size:20px;">{category_data.category}</td>
                </tr>
                """
                current_category_id = item.category_id

            html += f"""
            <tr>
                <td>{product_data.code}</td>
                <td>{product_data.product}</td>
                <td>{item.quantity}</td>
                <td>{self.format_number(item.quantity_per_package)} {unit}</td>
                <td>€. {self.format_number(item.final_unit_cost)}</td>
                <td>€. {self.format_number(item.amount)}</td>
            </tr>
            """

        html += f"""
            </tbody>
        </table>
        """

        # Calcular todos los totales adicionales
        totals = self.calculate_shopping_totals(data, id)

        html += f"""
        <div style="margin-top: 30px; font-size: 14px;">
            <div style="margin-bottom: 10px;">
                <strong>Total por Kilogramos:</strong><br>
                {self.format_number(totals['total_kg'])} Kg
            </div>
            <div style="margin-bottom: 10px;">
                <strong>Total por Litros:</strong><br>
                {self.format_number(totals['total_lts'])} Lts
            </div>
            <div style="margin-bottom: 10px;">
                <strong>Total por Unidad:</strong><br>
                {self.format_number(totals['total_und'])} Und
            </div>
            <div style="margin-bottom: 10px;">
                <strong>Total Envío (Kg):</strong><br>
                {self.format_number(totals['total_shipping_kg'])} Kg
            </div>
            <div style="margin-bottom: 10px;">
                <strong>Total Pallets (Und):</strong><br>
                {self.format_number(totals['total_pallets'])} Und
            </div>
            <div style="margin-bottom: 10px;">
                <strong>Total sin Descuento:</strong><br>
                €. {self.format_number(totals['total_without_discount'])}
            </div>"""

        # Mostrar total con descuento solo si hay prepago
        if totals['has_prepaid'] and totals['total_with_discount'] is not None:
            html += f"""
            <div style="margin-bottom: 10px;">
                <strong>Total con Descuento2 ({self.format_number(totals['prepaid_discount_percentage'])}%):</strong><br>
                €. {self.format_number(totals['total_with_discount'])}
            </div>"""

        html += f"""
        </div>

        </body>
        </html>
        """

        return html

    def generate_shopping_html_for_customs_company(self, data: ShoppingCreateInput, id) -> str:
        logo_url = "file:/var/www/api.lacasadelvitrificado.com/public/assets/logo.png"
        vitrificado_logo_url = "file:/var/www/api.lacasadelvitrificado.com/public/assets/vitrificado-logo.png"
        date = datetime.utcnow().strftime("%Y-%m-%d")

        html = f"""
        <html>
            <head>
            <meta charset="utf-8">
            <style>
                body {{ font-family: Arial, sans-serif; font-size: 14px; }}
                table {{ border-collapse: collapse; width: 100%; margin-top: 20px; }}
                th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
                th {{ background-color: #f2f2f2; }}
                .logo {{ width: 200px; }}
                .vitrificado_logo {{ width: 120px; }}
                .header {{
                    display: flex;
                    justify-content: space-between;
                    align-items: center;
                    margin-bottom: 20px;
                }}
                .title {{ text-align: center; margin-top: 20px; margin-bottom: 30px; }}
                .page-break {{
                    page-break-before: always;
                    break-before: page;
                }}
            </style>
            </head>
            <body>
            <div class="header">
                <img src="{vitrificado_logo_url}" class="vitrificado_logo float-left" />
                &ensp;&ensp;&ensp;&ensp;&ensp;&ensp;&ensp;&ensp;&ensp;&ensp;&ensp;&ensp;&ensp;&ensp;&ensp;&ensp;
                &ensp;&ensp;&ensp;&ensp;&ensp;&ensp;&ensp;&ensp;&ensp;&ensp;&ensp;&ensp;&ensp;&ensp;&ensp;&ensp;&ensp;
                &ensp;&ensp;&ensp;&ensp;&ensp;&ensp;&ensp;&ensp;&ensp;&ensp;&ensp;&ensp;&ensp;&ensp;&ensp;&ensp;
                &ensp;&ensp;&ensp;&ensp;&ensp;&ensp;&ensp;&ensp;&ensp;&ensp;&ensp;&ensp;&ensp;&ensp;&ensp;&ensp;&ensp;
                &ensp;&ensp;&ensp;&ensp;&ensp;&ensp;&ensp;&ensp;&ensp;&ensp;
                <img src="{logo_url}" class="logo float-right" />
            </div>

            <div class="title">
                <h2>Purchase Order #{id}</h2>
            </div>

            <div>
                Date: {date}
            </div>

            <table>
                <thead>
                    <tr>
                        <th>Pos Item no.</th>
                        <th>Description</th>
                        <th>Cont</th>
                        <th>Kg/Lts/Un</th>
                        <th>Price</th>
                        <th>Amount</th>
                    </tr>
                    </thead>
                    <tbody>
                """

        # Ordenar productos por category_id
        sorted_products = sorted(data.products, key=lambda p: p.category_id)
        current_category_id = None

        for item in sorted_products:
            product_data = self.db.query(ProductModel).filter(ProductModel.id == item.product_id).first()
            if item.unit_measure_id == 1 or item.unit_measure_id == 2 or item.unit_measure_id == 3:
                unit_features = (
                    self.db.query(UnitFeatureModel)
                    .filter(UnitFeatureModel.product_id == item.product_id)
                    .first()
                )

                if not unit_features:
                    raise ValueError(f"Producto con ID {item.product_id} no tiene configuración en UnitFeatureModel")
                try:
                    quantity_per_package = float(unit_features.quantity_per_package)
                    quantity_per_pallet = float(unit_features.quantity_per_pallet)
                    weight_per_pallet = float(unit_features.weight_per_pallet)
                except ValueError:
                    raise ValueError(f"Error al convertir valores de UnitFeatureModel a float (product_id={item.product_id})")

            unit = {1: "Kg", 2: "Lts", 3: "Und"}.get(item.unit_measure_id, "")

            if item.category_id != current_category_id:
                category_data = self.db.query(CategoryModel).filter(CategoryModel.id == item.category_id).first()
                html += f"""
                <tr>
                    <td colspan="8" style="background-color: {category_data.color}; font-weight: bold; text-align: center; font-size:20px;">{category_data.category}</td>
                </tr>
                """
                current_category_id = item.category_id

            html += f"""
            <tr>
                <td>{product_data.code}</td>
                <td>{product_data.product}</td>
                <td>{item.quantity}</td>
                <td>{self.format_number(item.quantity_per_package)} {unit}</td>
                <td>€. {self.format_number(item.final_unit_cost)}</td>
                <td>€. {self.format_number(item.amount)}</td>
            </tr>
            """

        html += f"""
            </tbody>
        </table>

        <div style="text-align: right; margin-top: 20px;">
            <h2>Total: €. {self.format_number(data.total)}</h2>
        </div>
        """

        # Calcular todos los totales adicionales
        totals = self.calculate_shopping_totals(data, id)

        html += f"""
        <div style="margin-top: 30px; font-size: 14px;">
            <div style="margin-bottom: 10px;">
                <strong>Total por Kilogramos:</strong><br>
                {self.format_number(totals['total_kg'])} Kg
            </div>
            <div style="margin-bottom: 10px;">
                <strong>Total por Litros:</strong><br>
                {self.format_number(totals['total_lts'])} Lts
            </div>
            <div style="margin-bottom: 10px;">
                <strong>Total por Unidad:</strong><br>
                {self.format_number(totals['total_und'])} Und
            </div>
            <div style="margin-bottom: 10px;">
                <strong>Total Envío (Kg):</strong><br>
                {self.format_number(totals['total_shipping_kg'])} Kg
            </div>
            <div style="margin-bottom: 10px;">
                <strong>Total Pallets (Und):</strong><br>
                {self.format_number(totals['total_pallets'])} Und
            </div>
            <div style="margin-bottom: 10px;">
                <strong>Total sin Descuento:</strong><br>
                €. {self.format_number(totals['total_without_discount'])}
            </div>"""

        # Mostrar total con descuento solo si hay prepago
        if totals['has_prepaid'] and totals['total_with_discount'] is not None:
            html += f"""
            <div style="margin-bottom: 10px;">
                <strong>Total con Descuento ({self.format_number(totals['prepaid_discount_percentage'])}%):</strong><br>
                €. {self.format_number(totals['total_with_discount'])}
            </div>"""

        html += f"""
        </div>

        <!-- Salto de página -->
        <div class="page-break"></div>

        <!-- Segunda página -->
        <div class="page-break">
            <div class="header">
                <img src="{vitrificado_logo_url}" class="vitrificado_logo float-left" />
                &ensp;&ensp;&ensp;&ensp;&ensp;&ensp;&ensp;&ensp;&ensp;&ensp;&ensp;&ensp;&ensp;&ensp;&ensp;&ensp;
                &ensp;&ensp;&ensp;&ensp;&ensp;&ensp;&ensp;&ensp;&ensp;&ensp;&ensp;&ensp;&ensp;&ensp;&ensp;&ensp;&ensp;
                &ensp;&ensp;&ensp;&ensp;&ensp;&ensp;&ensp;&ensp;&ensp;&ensp;&ensp;&ensp;&ensp;&ensp;&ensp;&ensp;
                &ensp;&ensp;&ensp;&ensp;&ensp;&ensp;&ensp;&ensp;&ensp;&ensp;&ensp;&ensp;&ensp;&ensp;&ensp;&ensp;&ensp;
                &ensp;&ensp;&ensp;&ensp;&ensp;&ensp;&ensp;&ensp;&ensp;&ensp;
                <img src="{logo_url}" class="logo float-right" />
            </div>
            <div class="title">
                <h2>Purchase Order #{id}</h2>
            </div>

            <div>
                Date: {date}
            </div>

            <table>
                <thead>
                    <tr>
                        <th>Total Weight</th>
                        <th>Pallet Number</th>
                    </tr>
                    </thead>
                    <tbody>
                """
        # Ordenar productos por category_id
        sorted_products = sorted(data.products, key=lambda p: p.category_id)
        current_category_id = None
        total_weight_per_shopping = 0.0
        products_info = []


        for item in sorted_products:
            product_data = self.db.query(ProductModel).filter(ProductModel.id == item.product_id).first()

            unit_feature = self.db.query(UnitFeatureModel).filter(UnitFeatureModel.product_id == item.product_id).first()

            shopping_product = self.db.query(ShoppingProductModel).filter(ShoppingProductModel.shopping_id == id, ShoppingProductModel.product_id == item.product_id).first()

            if item.unit_measure_id == 1 or item.unit_measure_id == 2 or item.unit_measure_id == 3:
                unit_features = (
                    self.db.query(UnitFeatureModel)
                    .filter(UnitFeatureModel.product_id == item.product_id)
                    .first()
                )

                weight_per_unit = float(unit_feature.weight_per_unit) if unit_feature else 0.0
                product_total_weight = weight_per_unit * float(shopping_product.quantity)
                weight_per_pallet = float(unit_feature.weight_per_pallet) if unit_feature else 1000.0

                total_weight_per_shopping += product_total_weight
                
                # Acumular información de productos para cálculo correcto de pallets
                products_info.append({
                    'name': product_data.product if product_data else 'Unknown',
                    'total_weight': product_total_weight,
                    'weight_per_pallet': weight_per_pallet
                })

        # Calcular pallets usando el algoritmo correcto
        calculated_pallets = self.calculate_real_mixed_pallets(products_info)
        how_many_pallets = len(calculated_pallets)

        print("Total weight per shopping:", total_weight_per_shopping)
        print("Pallet calculation details:")
        for i, pallet in enumerate(calculated_pallets, 1):
            print(f"  Pallet {i}: {pallet['total_weight']}kg / {pallet['capacity']}kg")
            for content in pallet['contents']:
                print(f"    - {content}")
        print(f"Total pallets needed (correct mixed formula): {how_many_pallets}")

        html += f"""
            <tr>
                <td>{total_weight_per_shopping} Kg</td>
                <td>{how_many_pallets}</td>
            </tr>
            """

        html += f"""
            </tbody>
        </table>
        </div>

        </body>
        </html>
        """

        return html
    
    def generate_shopping_html_for_supplier(self, data: ShoppingCreateInput, id) -> str:
        logo_url = "file:/var/www/api.lacasadelvitrificado.com/public/assets/logo.png"
        vitrificado_logo_url = "file:/var/www/api.lacasadelvitrificado.com/public/assets/vitrificado-logo.png"
        supplier_data = self.db.query(SupplierModel).filter(SupplierModel.id == data.supplier_id).first()
        date = datetime.utcnow().strftime("%Y-%m-%d")

        html = f"""
        <html>
        <head>
        <meta charset="utf-8">
        <style>
            body {{ font-family: Arial, sans-serif; font-size: 14px; }}
            table {{ border-collapse: collapse; width: 100%; margin-top: 20px; }}
            th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
            th {{ background-color: #f2f2f2; }}
            .logo {{ width: 200px; }}
            .vitrificado_logo {{ width: 120px; }}
            .header {{
                display: flex;
                justify-content: space-between;
                align-items: center;
                margin-bottom: 20px;
            }}
            .title {{ text-align: center; margin-top: 20px; margin-bottom: 30px; }}
        </style>
        </head>
        <body>
        <div class="header">
            <img src="{vitrificado_logo_url}" class="vitrificado_logo float-left" />
            &ensp;&ensp;&ensp;&ensp;&ensp;&ensp;&ensp;&ensp;&ensp;&ensp;&ensp;&ensp;&ensp;&ensp;&ensp;&ensp;
            &ensp;&ensp;&ensp;&ensp;&ensp;&ensp;&ensp;&ensp;&ensp;&ensp;&ensp;&ensp;&ensp;&ensp;&ensp;&ensp;&ensp;
            &ensp;&ensp;&ensp;&ensp;&ensp;&ensp;&ensp;&ensp;&ensp;&ensp;&ensp;&ensp;&ensp;&ensp;&ensp;&ensp;
            &ensp;&ensp;&ensp;&ensp;&ensp;&ensp;&ensp;&ensp;&ensp;&ensp;&ensp;&ensp;&ensp;&ensp;&ensp;&ensp;&ensp;
            &ensp;&ensp;&ensp;&ensp;&ensp;&ensp;&ensp;&ensp;&ensp;&ensp;
            <img src="{logo_url}" class="logo float-right" />
        </div>

        <div class="title">
            <h2>Purchase Order #{id}</h2>
        </div>

        <div>
            Date: {date}
        </div>

        <table>
            <thead>
            <tr>
                <th>Pos Item no.</th>
                <th>Description</th>
                <th>Cont</th>
                <th>Kg/Lts/Un</th>
            </tr>
            </thead>
            <tbody>
        """

        # Ordenar productos por category_id
        sorted_products = sorted(data.products, key=lambda p: p.category_id)
        current_category_id = None

        for item in sorted_products:
            product_data = self.db.query(ProductModel).filter(ProductModel.id == item.product_id).first()
            unit = {1: "Kg", 2: "Lts", 3: "Und"}.get(item.unit_measure_id, "")

            if item.category_id != current_category_id:
                category_data = self.db.query(CategoryModel).filter(CategoryModel.id == item.category_id).first()
                html += f"""
                <tr>
                    <td colspan="6" style="background-color: {category_data.color}; font-weight: bold; text-align: center; font-size:20px;">{category_data.category}</td>
                </tr>
                """
                current_category_id = item.category_id

            html += f"""
            <tr>
                <td>{product_data.code}</td>
                <td>{product_data.product}</td>
                <td>{item.quantity}</td>
                <td>{self.format_number(item.quantity_per_package)} {unit}</td>
            </tr>
            """

        html += f"""
            </tbody>
        </table>


        </body>
        </html>
        """

        return html

    def html_to_pdf_bytes(self, html: str) -> bytes:
        path_wkhtmltopdf = '/usr/bin/wkhtmltopdf'
        
        config = pdfkit.configuration(
            wkhtmltopdf=path_wkhtmltopdf
        )

        options = {
            'enable-local-file-access': ''
        }

        pdf_bytes = pdfkit.from_string(html, False, configuration=config, options=options)
        return pdf_bytes


    def spanish_generate_email_content_html(self, data: ShoppingCreateInput) -> str:
        logo_url = "file:/var/www/api.lacasadelvitrificado.com/public/assets/logo.png"
        vitrificado_logo_url = "file:/var/www/api.lacasadelvitrificado.com/public/assets/vitrificado-logo.png"
        supplier_data = self.db.query(SupplierModel).filter(SupplierModel.id == data.supplier_id).first()

        html = f"""
        <html>
        <head>
        <meta charset="utf-8">
        <style>
            body {{ font-family: Arial, sans-serif; font-size: 14px; }}
            table {{ border-collapse: collapse; width: 100%; margin-top: 20px; }}
            th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
            th {{ background-color: #f2f2f2; }}
            .logo {{ width: 200px; }}
            .vitrificado_logo {{ width: 120px; }}
            .header {{
                display: flex;
                justify-content: space-between;
                align-items: center;
                margin-bottom: 20px;
            }}
            .title {{ text-align: center; margin-top: 20px; margin-bottom: 30px; }}
        </style>
        </head>
        <body>
        <div class="header">
            <img src="{vitrificado_logo_url}" class="vitrificado_logo float-left" />
        </div>

        <div style="text-align: justify; font-size: 12px;">
            Estimados,

            Junto con saludarles cordialmente, les informamos que adjunto a este correo encontrarán un nuevo pedido generado desde nuestra plataforma de gestión interna.

            El archivo PDF incluye el detalle completo de los productos requeridos. Agradecemos su confirmación de recepción y quedamos atentos a cualquier comentario o requerimiento adicional.
            <br><br>
            Saludos cordiales,
            <br>
            <h4>Equipo de VitrificadosChile</h4>
        </div>

        </body>
        </html>
        """

        return html
    
    def english_generate_email_content_html(self, data: ShoppingCreateInput) -> str:
        logo_url = "file:/var/www/api.lacasadelvitrificado.com/public/assets/logo.png"
        vitrificado_logo_url = "file:/var/www/api.lacasadelvitrificado.com/public/assets/vitrificado-logo.png"
        supplier_data = self.db.query(SupplierModel).filter(SupplierModel.id == data.supplier_id).first()

        html = f"""
        <html>
        <head>
        <meta charset="utf-8">
        <style>
            body {{ font-family: Arial, sans-serif; font-size: 14px; }}
            table {{ border-collapse: collapse; width: 100%; margin-top: 20px; }}
            th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
            th {{ background-color: #f2f2f2; }}
            .logo {{ width: 200px; }}
            .vitrificado_logo {{ width: 120px; }}
            .header {{
                display: flex;
                justify-content: space-between;
                align-items: center;
                margin-bottom: 20px;
            }}
            .title {{ text-align: center; margin-top: 20px; margin-bottom: 30px; }}
        </style>
        </head>
        <body>
        <div class="header">
            <img src="{vitrificado_logo_url}" class="vitrificado_logo float-left" />
        </div>

        <div style="text-align: justify; font-size: 12px;">
            Dear Berger-Seidle team,

            We warmly greet you and inform you that attached to this email you will find a new order generated from our internal management platform.

            The PDF file includes the complete details of the requested products. We appreciate your confirmation of receipt and remain attentive to any comments or additional requirements.
            <br><br>
            Best regards,
            <br>
            <h4>The VitrificadosChile Team</h4>
        </div>

        </body>
        </html>
        """

        return html