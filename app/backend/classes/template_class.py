from app.backend.schemas import ShoppingCreateInput
import pdfkit
from io import BytesIO
from app.backend.db.models import SupplierModel, ProductModel, CategoryModel, UnitFeatureModel, ShoppingProductModel
from datetime import datetime
import math

class TemplateClass:
    def __init__(self, db):
        self.db = db

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
                <td>{item.quantity_per_package:.2f} {unit}</td>
                <td>€. {item.final_unit_cost:.2f}</td>
                <td>€. {item.amount:.2f}</td>
            </tr>
            """

        html += f"""
            </tbody>
        </table>

        <div style="text-align: right; margin-top: 20px;">
            <h2>Total: €. {data.total:.2f}</h2>
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
                <td>{item.quantity_per_package:.2f} {unit}</td>
                <td>€. {item.final_unit_cost:.2f}</td>
                <td>€. {item.amount:.2f}</td>
            </tr>
            """

        html += f"""
            </tbody>
        </table>

        <div style="text-align: right; margin-top: 20px;">
            <h2>Total: €. {data.total:.2f}</h2>
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
        maximum_total_weight = 0.0


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

                total_weight_per_shopping = total_weight_per_shopping + (weight_per_unit * float(shopping_product.quantity))

                maximum_total_weight = float(maximum_total_weight) + float(unit_feature.weight_per_pallet)

        print("Total weight per shopping:", total_weight_per_shopping)
        print("Maximum total weight:", maximum_total_weight)
        how_many_pallets = math.ceil(total_weight_per_shopping / maximum_total_weight)

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
                <td>{item.quantity_per_package:.2f} {unit}</td>
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