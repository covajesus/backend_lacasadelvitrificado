from app.backend.db.models import SaleModel, CustomerModel, SettingModel, RegionModel, CommuneModel, SaleProductModel, ProductModel, InventoryModel, UnitMeasureModel, SupplierModel, CategoryModel, LotItemModel, LotModel, InventoryMovementModel, InventoryLotItemModel
from datetime import datetime, timedelta
from app.backend.classes.setting_class import SettingClass
from sqlalchemy import func
import requests
import json
import os
from app.backend.classes.file_class import FileClass

class DteClass:
    def __init__(self, db):
        self.db = db

    def generate_pdf(self, folio, dte_type_id, ambiente=0):
        validate_token = SettingClass(self.db).validate_token()

        setting_data = SettingClass(self.db).get(1)

        if validate_token == 0:
            SettingClass(self.db).get_simplefactura_token()
            token = setting_data["setting_data"]["simplefactura_token"]
        else:
            token = setting_data["setting_data"]["simplefactura_token"]
            
        try:
            # Determinar el código de tipo DTE
            if dte_type_id == 1:  # Boleta
                codigo_tipo_dte = 39
            else:  # Factura
                codigo_tipo_dte = 33
            
            # Payload para la API de SimpleFactura
            payload = {
                "credenciales": {
                    "rutEmisor": "78181331-1"
                },
                "dteReferenciadoExterno": {
                    "folio": folio,
                    "codigoTipoDte": codigo_tipo_dte,
                    "ambiente": ambiente
                }
            }
            
            headers = {
                'Authorization': f'Bearer {token}',
                "Content-Type": "application/json"
            }
            
            # Llamar a la API de SimpleFactura
            print(f"[DEBUG PDF] Llamando a SimpleFactura con folio: {folio}")
            print(f"[DEBUG PDF] Payload: {json.dumps(payload, indent=2)}")
            
            response = requests.post(
                "https://api.simplefactura.cl/getPdf",
                json=payload,
                headers=headers
            )
            
            print(f"[DEBUG PDF] Response status: {response.status_code}")
            print(f"[DEBUG PDF] Response headers: {dict(response.headers)}")
            
            if response.status_code == 200:
                # Usar FileClass para guardar el PDF
                file_class = FileClass(self.db)
                remote_path = f"{folio}.pdf"
                
                # Guardar el PDF usando temporal_upload
                result = file_class.temporal_upload(response.content, remote_path)
                
                print(f"PDF generado exitosamente: {result}")
                return remote_path
            else:
                print(f"Error generando PDF: {response.status_code} - {response.text}")
                return None
                
        except Exception as e:
            print(f"Error en generate_pdf: {str(e)}")
            return None

    def generate_dte(self, id):
        sale = self.db.query(SaleModel).filter(SaleModel.id == id).first()

        customer = self.db.query(CustomerModel).filter(CustomerModel.id == sale.customer_id).first()

        commune = self.db.query(CommuneModel).filter(CommuneModel.id == customer.commune_id).first()

        region = self.db.query(RegionModel).filter(RegionModel.id == customer.region_id).first()

        validate_token = SettingClass(self.db).validate_token()

        setting_data = SettingClass(self.db).get(1)

        if validate_token == 0:
            SettingClass(self.db).get_simplefactura_token()
            token = setting_data["setting_data"]["simplefactura_token"]
        else:
            token = setting_data["setting_data"]["simplefactura_token"]

        sales_products = self.db.query(
            SaleProductModel,
            ProductModel
        ).join(
            ProductModel, SaleProductModel.product_id == ProductModel.id
        ).filter(SaleProductModel.sale_id == id).all()

        added_date_str = sale.added_date.strftime("%Y-%m-%d")
        due_date = (sale.added_date + timedelta(days=30)).strftime('%Y-%m-%d')

        # Construir el detalle con todos los productos
        items = []
        for idx, (sp, product) in enumerate(sales_products, start=1):
            items.append({
                "NroLinDet": idx,
                "NmbItem": product.product,  # o product.product si ese es el campo correcto
                "QtyItem": sp.quantity,
                "UnmdItem": "un",  # puedes cambiar la unidad si es necesario
                "PrcItem": int(sp.price),  # precio unitario sin IVA
                "MontoItem": int(int(sp.price) * int(sp.quantity))  # monto total línea
            })

        if sale.dte_type_id == 1:
            # Armar el payload
            payload = {
                "Documento": {
                    "Encabezado": {
                        "IdDoc": {
                            "TipoDTE": 39,
                            "FchEmis": added_date_str,
                            "FchVenc": due_date,
                        },
                        "Emisor": {
                            "RUTEmisor": "77176777-K",
                            "RznSocEmisor": "Vitrificados Chile Compaaañia Limitada",
                            "GiroEmisor": "VENTA AL POR MENOR DE ARTICULOS DE FERRETERIA Y MATERIALES DE CONSTRUCCION",
                            "DirOrigen": "Santiago",
                            "CmnaOrigen": "Santiago"
                        },
                        "Receptor": {
                            "RUTRecep": customer.identification_number,
                            "RznSocRecep": customer.social_reason
                        },
                        "Totales": {
                            "MntNeto": round(sale.subtotal),
                            "IVA": round(sale.tax),
                            "MntTotal": round(sale.total)
                        }
                    },
                    "Detalle": items
                }
            }

            headers = {
                'Authorization': f'Bearer {token}',
                'Content-Type': 'application/json'
            }
         
            response = requests.post(
                'https://api.simplefactura.cl/invoiceV2/Casa_Matriz',
                data=json.dumps(payload),
                headers=headers
            )

            print(f"[DEBUG BOLETA] Response status: {response.status_code}")
            print(f"[DEBUG BOLETA] Response text: {response.text}")

            if response.status_code == 200:
                # Obtener el folio de la respuesta
                response_data = response.json()
                # El folio está dentro del campo 'data'
                data_section = response_data.get('data', {})
                folio = data_section.get('folio', None)
                print(f"[DEBUG BOLETA] Folio obtenido: {folio}")
                
                if folio:
                    print(f"[DEBUG BOLETA] Iniciando generación de PDF para folio: {folio}")
                    # Generar y descargar el PDF
                    pdf_path = self.generate_pdf(folio, sale.dte_type_id)
                    if pdf_path:
                        print(f"[DEBUG BOLETA] PDF generado exitosamente: {pdf_path}")
                    else:
                        print("[DEBUG BOLETA] Error generando PDF")
                else:
                    print("[DEBUG BOLETA] No se pudo obtener el folio de la respuesta")
                
                return 1
            else:
                print(f"[DEBUG BOLETA] Error en la respuesta: {response.status_code}")
                return 0
        else:
            payload = {
                "Documento": {
                    "Encabezado": {
                        "IdDoc": {
                            "TipoDTE": 33,
                            "FchEmis": added_date_str,
                            "FchVenc": due_date,
                        },
                        "Emisor": {
                            "RUTEmisor": "77176777-K",
                            "RznSoc": "Vitrificados Chile Compaaañia Limitada",
                            "GiroEmis": "VENTA AL POR MENOR DE ARTICULOS DE FERRETERIA Y MATERIALES DE CONSTRUCCION",
                            "DirOrigen": "Santiago",
                            "CmnaOrigen": "Santiago"
                        },
                        "Receptor": {
                            "RUTRecep": customer.identification_number,
                            "RznSocRecep": customer.social_reason,
                            "CorreoRecep": customer.email,
                            "DirRecep": customer.address,
                            "GiroRecep": customer.activity,
                            "CmnaRecep": commune.commune,
                            "CiudadRecep": region.region
                        },
                        "Totales": {
                            "MntNeto": round(sale.subtotal),
                            "IVA": round(sale.tax),
                            "MntTotal": round(sale.total)
                        }
                    },
                    "Detalle": items
                }
            }

            headers = {
                'Authorization': f'Bearer {token}',
                'Content-Type': 'application/json'
            }
         
            response = requests.post(
                'https://api.simplefactura.cl/invoiceV2/Casa_Matriz',
                data=json.dumps(payload),
                headers=headers
            )

            print(f"[DEBUG FACTURA] Response status: {response.status_code}")
            print(f"[DEBUG FACTURA] Response text: {response.text}")

            if response.status_code == 200:
                # Obtener el folio de la respuesta
                response_data = response.json()
                # El folio está dentro del campo 'data'
                data_section = response_data.get('data', {})
                folio = data_section.get('folio', None)
                print(f"[DEBUG FACTURA] Folio obtenido: {folio}")
                
                if folio:
                    print(f"[DEBUG FACTURA] Iniciando generación de PDF para folio: {folio}")
                    # Generar y descargar el PDF
                    pdf_path = self.generate_pdf(folio, sale.dte_type_id)
                    if pdf_path:
                        print(f"[DEBUG FACTURA] PDF generado exitosamente: {pdf_path}")
                    else:
                        print("[DEBUG FACTURA] Error generando PDF")
                else:
                    print("[DEBUG FACTURA] No se pudo obtener el folio de la respuesta")
                
                return 1
            else:
                print(f"[DEBUG FACTURA] Error en la respuesta: {response.status_code}")
                return 0