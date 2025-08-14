import os
import pdfkit
from io import BytesIO
from app.backend.schemas import ShoppingCreateInput
from app.backend.db.models import SupplierModel, ProductModel, CategoryModel


class TemplateClass:
    def __init__(self, db):
        self.db = db

    def generate_shopping_html(self, data: ShoppingCreateInput) -> str:
        # Rutas locales en el servidor (ajusta según dónde estén tus imágenes)
        logo_url = "file:///var/www/api.lacasadelvitrificado.com/public/assets/logo.png"
        vitrificado_logo_url = "file:///var/www/api.lacasadelvitrificado.com/public/assets/vitrificado-logo.png"

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
            <img src="{vitrificado_logo_url}" class="vitrificado_logo" />
            <img src="{logo_url}" class="logo" />
        </div>

        <div class="title">
            <h2>Purchase Order</h2>
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
                    <td colspan="4" style="background-color: {category_data.color}; font-weight: bold; text-align: center; font-size:20px;">{category_data.category}</td>
                </tr>
                """
                current_category_id = item.category_id

            html += f"""
            <tr>
                <td>{product_data.code}</td>
                <td>{product_data.product}</td>
                <td>{item.quantity}</td>
                <td>{item.price:.2f} {unit}</td>
            </tr>
            """

        html += f"""
            </tbody>
        </table>

        <div style="text-align: right; margin-top: 20px;">
            <h2>Total: ${data.total:.2f}</h2>
        </div>
        </body>
        </html>
        """

        return html

    def html_to_pdf_bytes(self, html: str) -> bytes:
        # Detectar si es Windows o Linux
        if os.name == 'nt':  # Windows
            path_wkhtmltopdf = r"C:\Program Files\wkhtmltopdf\bin\wkhtmltopdf.exe"
        else:  # Linux
            path_wkhtmltopdf = '/usr/bin/wkhtmltopdf'

        config = pdfkit.configuration(wkhtmltopdf=path_wkhtmltopdf)

        options = {
            'enable-local-file-access': ''  # Necesario para que las imágenes locales funcionen
        }

        pdf_bytes = pdfkit.from_string(html, False, configuration=config, options=options)
        return pdf_bytes
