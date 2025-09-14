from app.backend.schemas import ShoppingCreateInput
import pdfkit
from io import BytesIO
from app.backend.db.models import SupplierModel, ProductModel, CategoryModel, UnitFeatureModel, ShoppingProductModel, SettingModel, ShoppingModel
from datetime import datetime
import math

class TemplateClass:
    def __init__(self, db):
        self.db = db
    
    def truncate_text(self, text, max_length=20):
        """Trunca el texto a la longitud mÃ¡xima especificada y agrega '...'"""
        if len(text) <= max_length:
            return text
        return text[:max_length] + "..."
    
    def format_number(self, value):
        """Formatea nÃºmeros para mostrar enteros sin decimales cuando es necesario"""
        if value == int(value):
            return str(int(value))
        else:
            return f"{value:.2f}"
    
    def format_currency(self, value):
        """Formatea números como moneda con separador de miles (punto)"""
        try:
            # Convertir a float si no lo es
            num = float(value)
            # Si es entero, mostrar sin decimales
            if num == int(num):
                return f"{int(num):,}".replace(',', '.')
            else:
                # Si tiene decimales, mostrar con 2 decimales
                return f"{num:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.')
        except (ValueError, TypeError):
            return "0"

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

        # Obtener porcentaje de descuento desde settings
        settings = self.db.query(SettingModel).first()
        prepaid_discount_percentage = float(settings.prepaid_discount) if settings and settings.prepaid_discount and has_prepaid else 0.0

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

            # Calcular totales por unidad de medida usando los mismos datos que el template
            # Usar item.quantity_per_package del request
            if item.unit_measure_id == 1:  # Kilogramos
                total_kg += float(item.quantity_per_package)
            elif item.unit_measure_id == 2:  # Litros
                total_lts += float(item.quantity_per_package)
            elif item.unit_measure_id == 3:  # Unidades
                total_und += float(item.quantity_per_package)

            # Calcular peso total para envío usando los datos del request
            if unit_feature:
                weight_per_unit = float(unit_feature.weight_per_unit) if unit_feature.weight_per_unit else 0.0
                product_total_weight = weight_per_unit * float(item.quantity)
                total_shipping_kg += product_total_weight
                
                # Para cï¿½lculo de pallets
                weight_per_pallet = float(unit_feature.weight_per_pallet) if unit_feature.weight_per_pallet else 1000.0
                products_info.append({
                    'name': product_data.product if product_data else 'Unknown',
                    'total_weight': product_total_weight,
                    'weight_per_pallet': weight_per_pallet
                })

            # Calcular total sin descuento usando los mismos datos que el template
            # Usar item.final_unit_cost e item.quantity_per_package del request
            if item.final_unit_cost and item.quantity_per_package:
                product_amount = float(item.quantity_per_package) * float(item.final_unit_cost)
                total_without_discount += product_amount

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
            
            # Capacidad del pallet = Mï¿½XIMA de productos activos (sincronizado con frontend)
            pallet_capacity = max(p["capacity"] for p in active)
            pallet_weight = 0
            pallet_contents = []
            
            # Llenar pallet con productos disponibles
            for product in remaining:
                if product["weight"] > 0 and pallet_weight < pallet_capacity:
                    # Cuï¿½nto puede agregar de este producto
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
        shopping_data = self.db.query(ShoppingModel).filter(ShoppingModel.id == id).first()
        shopping_number = str(shopping_data.shopping_number) if shopping_data and shopping_data.shopping_number else str(id)
        date = datetime.utcnow().strftime("%Y-%m-%d")

        html = f"""
        <html>
        <head>
        <meta charset="utf-8">
        <style>@page {{ margin: 2cm 1.5cm; size: A4 portrait; }}
            body {{ font-family: Arial, sans-serif; font-size: 14px; line-height: 1.4; margin: 0; padding: 0; }}
            table {{ border-collapse: collapse; width: 100%; margin-top: 20px; page-break-inside: auto; }}
            th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; word-wrap: break-word; max-width: 150px; }}
            th {{ background-color: #f2f2f2; }} tr {{ page-break-inside: avoid; page-break-after: auto; }}
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
            &ensp;&ensp;&ensp;&ensp;&ensp;&ensp;&ensp;&ensp;&ensp;&ensp;            <img src="{logo_url}" class="logo float-right" />
        </div>

        <div class="title">
            <h2>Purchase Order #{shopping_number}</h2>
        </div>

        <div style="margin-bottom: 20px;">
        <div style="display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 20px;">
            <div>
                <strong>Vitrificadoschile Compañia Limitada</strong><br>
                Av. Pres. Kennedy 7440 of.901<br>
                7650618 Santiago - Chile
            </div>
            <div style="text-align: right;">
                Date: {date}
            </div>
        </div>

        <table>
            <thead>
            <tr>
                <th>Pos Item no.</th>
                <th>Description</th>
                <th>Kg/Lts/Un</th>
                <th>Cont</th>
                <th>Price</th>
                <th>Amount</th>
            </tr>
            </thead>
            <tbody>
        """

        # Ordenar productos por category_id
        sorted_products = sorted(data.products, key=lambda p: p.category_id)
        
        # Calcular todos los totales adicionales AL PRINCIPIO
        totals = self.calculate_shopping_totals(data, id)
        
        # Crear función para generar HTML de totales
        def get_totals_html():
            totals_html = f"""
        <div style="margin-top: 20px; font-size: 12px; text-align: right; border-top: 1px solid #ddd; padding-top: 15px;">
            <div style="margin-bottom: 8px;">
                <strong>Total Kilograms:</strong> {self.format_number(totals['total_kg'])} Kg
            </div>
            <div style="margin-bottom: 8px;">
                <strong>Total Liters:</strong> {self.format_number(totals['total_lts'])} Lts
            </div>
            <div style="margin-bottom: 8px;">
                <strong>Total Units:</strong> {self.format_number(totals['total_und'])} Units
            </div>
            <div style="margin-bottom: 8px;">
                <strong>Total Shipping (Kg):</strong> {self.format_number(totals['total_shipping_kg'])} Kg
            </div>
            <div style="margin-bottom: 8px;">
                <strong>Total Pallets (Units):</strong> {self.format_number(totals['total_pallets'])} Units
            </div>"""
            
            # Mostrar descuento si hay prepago
            if totals['has_prepaid'] and totals['total_with_discount'] is not None:
                discount_amount = totals['total_without_discount'] - totals['total_with_discount']
                totals_html += f"""
            <div style="margin-bottom: 8px;">
                <strong>Discount:</strong> €. {self.format_currency(discount_amount)}
            </div>"""

            totals_html += f"""
            <div style="margin-bottom: 8px;">
                <strong>Total without Discount:</strong> €. {self.format_currency(totals['total_without_discount'])}
            </div>"""

            # Mostrar total con descuento solo si hay prepago
            if totals['has_prepaid'] and totals['total_with_discount'] is not None:
                totals_html += f"""
            <div style="margin-bottom: 8px;">
                <strong>Total with Discount ({self.format_number(totals['prepaid_discount_percentage'])}%):</strong> €. {self.format_currency(totals['total_with_discount'])}
            </div>"""

            totals_html += "</div>"
            return totals_html
        
        # Calcular total de filas (productos + headers de categoría)
        total_rows = len(sorted_products)
        categories = set(item.category_id for item in sorted_products)
        total_rows += len(categories)  # Agregar filas de categorías
        
        # Decidir si usar paginación
        use_pagination = total_rows > 16
        items_per_page = 16
        current_category_id = None
        row_count = 0
        page_count = 1
        
        # Comenzar primera tabla
        for i, item in enumerate(sorted_products):
            product_data = self.db.query(ProductModel).filter(ProductModel.id == item.product_id).first()
            unit = {1: "Kg", 2: "Lts", 3: "Units"}.get(item.unit_measure_id, "")
            
            # Si es el primer elemento o cambiamos de categoría, agregamos header de categoría
            category_changed = item.category_id != current_category_id
            
            # Si usamos paginación y llegamos al límite de filas, cerrar tabla actual, agregar totales y abrir nueva página
            if use_pagination and row_count >= items_per_page:
                html += """
            </tbody>
        </table>
        """ + get_totals_html() + """
        <div style="page-break-before: always;"></div>
        <table>
            <thead>
                <tr>
                    <th>Code</th>
                    <th>Product</th>
                    <th>Kg/Lts/Un</th>
                    <th>Cont</th>
                    <th>Unit Cost</th>
                    <th>Amount</th>
                </tr>
            </thead>
            <tbody>
                """
                row_count = 0
                page_count += 1
                current_category_id = None  # Reset para mostrar categoría en nueva página
                category_changed = True  # Forzar mostrar categoría
            
            # Mostrar header de categoría si cambió
            if category_changed:
                category_data = self.db.query(CategoryModel).filter(CategoryModel.id == item.category_id).first()
                html += f"""
                <tr>
                    <td colspan="6" style="background-color: {category_data.color}; font-weight: bold; text-align: center; font-size:20px;">{category_data.category}</td>
                </tr>
                """
                current_category_id = item.category_id
                row_count += 1
            
            # Agregar producto
            html += f"""
            <tr>
                <td>{product_data.code}</td>
                <td>{self.truncate_text(product_data.product)}</td>
                <td>{self.format_number(item.quantity_per_package)} {unit}</td>
                <td>{self.format_number(item.quantity)}</td>
                <td>€. {self.format_number(item.final_unit_cost)}</td>
                <td>€. {self.format_currency(item.quantity_per_package * item.final_unit_cost)}</td>
            </tr>
            """
            row_count += 1

        # Cerrar tabla final
        html += f"""
            </tbody>
        </table>
        """

        html += """
        </body>
        </html>
        """

        return html

    def generate_shopping_html_for_customs_company(self, data: ShoppingCreateInput, id) -> str:
        logo_url = "file:/var/www/api.lacasadelvitrificado.com/public/assets/logo.png"
        vitrificado_logo_url = "file:/var/www/api.lacasadelvitrificado.com/public/assets/vitrificado-logo.png"
        shopping_data = self.db.query(ShoppingModel).filter(ShoppingModel.id == id).first()
        shopping_number = str(shopping_data.shopping_number) if shopping_data and shopping_data.shopping_number else str(id)
        date = datetime.utcnow().strftime("%Y-%m-%d")

        html = f"""
        <html>
            <head>
            <meta charset="utf-8">
            <style>@page {{ margin: 2cm 1.5cm; size: A4 portrait; }}
                body {{ font-family: Arial, sans-serif; font-size: 14px; line-height: 1.4; margin: 0; padding: 0; }}
                table {{ border-collapse: collapse; width: 100%; margin-top: 20px; page-break-inside: auto; }}
                th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; word-wrap: break-word; max-width: 150px; }}
                th {{ background-color: #f2f2f2; }} tr {{ page-break-inside: avoid; page-break-after: auto; }}
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
                &ensp;&ensp;&ensp;&ensp;&ensp;&ensp;&ensp;&ensp;&ensp;&ensp;            <img src="{logo_url}" class="logo float-right" />
        </div>

        <div class="title">
            <h2>Purchase Order #{shopping_number}</h2>
        </div>

        <div style="display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 20px;">
            <div>
                <strong>Vitrificadoschile Compañia Limitada</strong><br>
                Av. Pres. Kennedy 7440 of.901<br>
                7650618 Santiago - Chile
            </div>
            <div style="text-align: right;">
                Date: {date}
            </div>
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
        
        # Calcular total de filas (productos + headers de categoría)
        total_rows = len(sorted_products)
        categories = set(item.category_id for item in sorted_products)
        total_rows += len(categories)  # Agregar filas de categorías
        
        # Decidir si usar paginación
        use_pagination = total_rows > 16
        items_per_page = 16
        current_category_id = None
        row_count = 0
        page_count = 1
        
        # Comenzar primera tabla
        for i, item in enumerate(sorted_products):
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

            unit = {1: "Kg", 2: "Lts", 3: "Units"}.get(item.unit_measure_id, "")
            
            # Si es el primer elemento o cambiamos de categoría, agregamos header de categoría
            category_changed = item.category_id != current_category_id
            
            # Si usamos paginación y llegamos al límite de filas, cerrar tabla actual y abrir nueva página
            if use_pagination and row_count >= items_per_page:
                html += """
            </tbody>
        </table>
        <div style="page-break-before: always;"></div>
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
                row_count = 0
                page_count += 1
                current_category_id = None  # Reset para mostrar categoría en nueva página
                category_changed = True  # Forzar mostrar categoría
            
            # Mostrar header de categoría si cambió
            if category_changed:
                category_data = self.db.query(CategoryModel).filter(CategoryModel.id == item.category_id).first()
                html += f"""
                <tr>
                    <td colspan="6" style="background-color: {category_data.color}; font-weight: bold; text-align: center; font-size:20px;">{category_data.category}</td>
                </tr>
                """
                current_category_id = item.category_id
                row_count += 1
            
            # Agregar producto
            html += f"""
            <tr>
                <td>{product_data.code}</td>
                <td>{self.truncate_text(product_data.product)}</td>
                <td>{self.format_number(item.quantity_per_package)} {unit}</td>
                <td>{self.format_number(item.quantity)}</td>
                <td>€. {self.format_number(item.final_unit_cost)}</td>
                <td>€. {self.format_currency(item.quantity_per_package * item.final_unit_cost)}</td>
            </tr>
            """
            row_count += 1

        html += f"""
            </tbody>
        </table>
        """

        # Calcular todos los totales adicionales
        totals = self.calculate_shopping_totals(data, id)

        html += """
        <!-- Salto de página -->
        <div class="page-break"></div>

        <!-- Segunda pï¿½gina -->
        <div class="page-break">
            <div class="header">
                <img src="{vitrificado_logo_url}" class="vitrificado_logo float-left" />
                &ensp;&ensp;&ensp;&ensp;&ensp;&ensp;&ensp;&ensp;&ensp;&ensp;&ensp;&ensp;&ensp;&ensp;&ensp;&ensp;
                &ensp;&ensp;&ensp;&ensp;&ensp;&ensp;&ensp;&ensp;&ensp;&ensp;&ensp;&ensp;&ensp;&ensp;&ensp;&ensp;&ensp;
                &ensp;&ensp;&ensp;&ensp;&ensp;&ensp;&ensp;&ensp;&ensp;&ensp;&ensp;&ensp;&ensp;&ensp;&ensp;&ensp;
                &ensp;&ensp;&ensp;&ensp;&ensp;&ensp;&ensp;&ensp;&ensp;&ensp;&ensp;&ensp;&ensp;&ensp;&ensp;&ensp;&ensp;
                &ensp;&ensp;&ensp;&ensp;&ensp;&ensp;&ensp;&ensp;&ensp;&ensp;            <img src="{logo_url}" class="logo float-right" />

        </div>

        <div class="title">
            <h2>Purchase Order #{shopping_number}</h2>
        </div>

        <div style="display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 20px;">
            <div>
                <strong>Vitrificadoschile Compañia Limitada</strong><br>
                Av. Pres. Kennedy 7440 of.901<br>
                7650618 Santiago - Chile
            </div>
            <div style="text-align: right;">
                Date: {date}
            </div>
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
                
                # Acumular informaciï¿½n de productos para cï¿½lculo correcto de pallets
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
        shopping_data = self.db.query(ShoppingModel).filter(ShoppingModel.id == id).first()
        shopping_number = str(shopping_data.shopping_number) if shopping_data and shopping_data.shopping_number else str(id)
        date = datetime.utcnow().strftime("%Y-%m-%d")

        html = f"""
        <html>
        <head>
        <meta charset="utf-8">
        <style>@page {{ margin: 2cm 1.5cm; size: A4 portrait; }}
            body {{ font-family: Arial, sans-serif; font-size: 14px; line-height: 1.4; margin: 0; padding: 0; }}
            table {{ border-collapse: collapse; width: 100%; margin-top: 20px; page-break-inside: auto; }}
            th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; word-wrap: break-word; max-width: 150px; }}
            th {{ background-color: #f2f2f2; }} tr {{ page-break-inside: avoid; page-break-after: auto; }}
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
            &ensp;&ensp;&ensp;&ensp;&ensp;&ensp;&ensp;&ensp;&ensp;&ensp;            <img src="{logo_url}" class="logo float-right" />
        </div>

        <div class="title">
            <h2>Purchase Order #{shopping_number}</h2>
        </div>

        <div style="display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 20px;">
            <div>
                <strong>Vitrificadoschile Compañia Limitada</strong><br>
                Av. Pres. Kennedy 7440 of.901<br>
                7650618 Santiago - Chile
            </div>
            <div style="text-align: right;">
                Date: {date}
            </div>
        </div>

        <table>
            <thead>
            <tr>
                <th>Pos Item no.</th>
                <th>Description</th>
                <th>Kg/Lts/Un</th>
                <th>Cont</th>
            </tr>
            </thead>
            <tbody>
        """

        # Ordenar productos por category_id
        sorted_products = sorted(data.products, key=lambda p: p.category_id)
        
        # Calcular total de filas (productos + headers de categoría)
        total_rows = len(sorted_products)
        categories = set(item.category_id for item in sorted_products)
        total_rows += len(categories)  # Agregar filas de categorías
        
        # Decidir si usar paginación
        use_pagination = total_rows > 16
        items_per_page = 16
        current_category_id = None
        row_count = 0
        page_count = 1
        
        # Comenzar primera tabla
        for i, item in enumerate(sorted_products):
            product_data = self.db.query(ProductModel).filter(ProductModel.id == item.product_id).first()
            unit = {1: "Kg", 2: "Lts", 3: "Units"}.get(item.unit_measure_id, "")
            
            # Si es el primer elemento o cambiamos de categoría, agregamos header de categoría
            category_changed = item.category_id != current_category_id
            
            # Si usamos paginación y llegamos al límite de filas, cerrar tabla actual y abrir nueva página
            if use_pagination and row_count >= items_per_page:
                html += """
            </tbody>
        </table>
        <div style="page-break-before: always;"></div>
        <table>
            <thead>
                <tr>
                    <th>Code</th>
                    <th>Product</th>
                    <th>Kg/Lts/Un</th>
                    <th>Cont</th>
                </tr>
            </thead>
            <tbody>
                """
                row_count = 0
                page_count += 1
                current_category_id = None  # Reset para mostrar categoría en nueva página
                category_changed = True  # Forzar mostrar categoría
            
            # Mostrar header de categoría si cambió
            if category_changed:
                category_data = self.db.query(CategoryModel).filter(CategoryModel.id == item.category_id).first()
                html += f"""
                <tr>
                    <td colspan="4" style="background-color: {category_data.color}; font-weight: bold; text-align: center; font-size:20px;">{category_data.category}</td>
                </tr>
                """
                current_category_id = item.category_id
                row_count += 1
            
            # Agregar producto
            html += f"""
            <tr>
                <td>{product_data.code}</td>
                <td>{self.truncate_text(product_data.product)}</td>
                <td>{self.format_number(item.quantity_per_package)} {unit}</td>
                <td>{self.format_number(item.quantity)}</td>
            </tr>
            """
            row_count += 1

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
        <style>@page {{ margin: 2cm 1.5cm; size: A4 portrait; }}
            body {{ font-family: Arial, sans-serif; font-size: 14px; line-height: 1.4; margin: 0; padding: 0; }}
            table {{ border-collapse: collapse; width: 100%; margin-top: 20px; page-break-inside: auto; }}
            th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; word-wrap: break-word; max-width: 150px; }}
            th {{ background-color: #f2f2f2; }} tr {{ page-break-inside: avoid; page-break-after: auto; }}
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
        <style>@page {{ margin: 2cm 1.5cm; size: A4 portrait; }}
            body {{ font-family: Arial, sans-serif; font-size: 14px; line-height: 1.4; margin: 0; padding: 0; }}
            table {{ border-collapse: collapse; width: 100%; margin-top: 20px; page-break-inside: auto; }}
            th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; word-wrap: break-word; max-width: 150px; }}
            th {{ background-color: #f2f2f2; }} tr {{ page-break-inside: avoid; page-break-after: auto; }}
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



