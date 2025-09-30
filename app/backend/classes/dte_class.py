from app.backend.db.models import SaleModel, CustomerModel, SettingModel, RegionModel, CommuneModel, SaleProductModel, ProductModel, InventoryModel, UnitMeasureModel, SupplierModel, CategoryModel, LotItemModel, LotModel, InventoryMovementModel, InventoryLotItemModel
from datetime import datetime, timedelta
from app.backend.classes.setting_class import SettingClass
from sqlalchemy import func
import requests
import json
import os
from fastapi import HTTPException
from fastapi.responses import Response

class DteClass:
    def __init__(self, db):
        self.db = db


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

        if sale.shipping_method_id == 2:
            subtotal = sale.subtotal + sale.shipping_cost
        else:
            subtotal = sale.subtotal

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
                            "MntNeto": round(subtotal),
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
                    print(f"[DEBUG BOLETA] DTE generado exitosamente con folio: {folio}")
                else:
                    print("[DEBUG BOLETA] No se pudo obtener el folio de la respuesta")
                
                return folio  # Retornar el folio en lugar de 1
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
                            "RznSoc": "Vitrificados Chile Compañia Limitada",
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
                            "MntNeto": round(subtotal),
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
                    print(f"[DEBUG FACTURA] DTE generado exitosamente con folio: {folio}")
                else:
                    print("[DEBUG FACTURA] No se pudo obtener el folio de la respuesta")
                
                return folio  # Retornar el folio en lugar de 1
            else:
                print(f"[DEBUG FACTURA] Error en la respuesta: {response.status_code}")
                return 0

    def download(self, folio):
        """
        Descarga el PDF del DTE por folio
        """
        try:
            # Verificar que la venta existe y tiene el folio
            sale = self.db.query(SaleModel).filter(SaleModel.folio == folio).first()
            if not sale:
                raise HTTPException(status_code=404, detail="DTE no encontrado")
            
            # Obtener token de SimpleFactura
            validate_token = SettingClass(self.db).validate_token()
            setting_data = SettingClass(self.db).get(1)
            
            if validate_token == 0:
                SettingClass(self.db).get_simplefactura_token()
                token = setting_data["setting_data"]["simplefactura_token"]
            else:
                token = setting_data["setting_data"]["simplefactura_token"]
            
            # Determinar el código de tipo DTE
            if sale.dte_type_id == 1:  # Boleta
                dte_type_id = 39
            else:  # Factura
                dte_type_id = 33
            
            # Payload para la API de SimpleFactura
            payload = {
                "credenciales": {
                    "rutEmisor": "77176777-K",
                    "nombreSucursal": "Casa Matriz"
                },
                "dteReferenciadoExterno": {
                    "folio": folio,
                    "codigoTipoDte": dte_type_id,
                    "ambiente": 1
                }
            }
            
            headers = {
                'Authorization': f'Bearer {token}',
                "Content-Type": "application/json"
            }
            
            # Llamar a la API de SimpleFactura para obtener el PDF
            response = requests.post(
                "https://api.simplefactura.cl/getPdf",
                json=payload,
                headers=headers
            )
            
            if response.status_code == 200:
                # Retornar el PDF como respuesta forzando descarga
                return Response(
                    content=response.content,
                    media_type="application/pdf",
                    headers={
                        "Content-Disposition": f"attachment; filename=dte_{folio}.pdf",
                        "Content-Type": "application/pdf",
                        "Cache-Control": "no-cache, no-store, must-revalidate",
                        "Pragma": "no-cache",
                        "Expires": "0"
                    }
                )
            else:
                raise HTTPException(
                    status_code=response.status_code, 
                    detail=f"Error generando PDF: {response.text}"
                )
                
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Error al procesar: {str(e)}")