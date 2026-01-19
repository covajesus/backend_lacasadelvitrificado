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
        
        if not sale:
            print(f"[ERROR DTE] Venta {id} no encontrada")
            return 0

        customer = self.db.query(CustomerModel).filter(CustomerModel.id == sale.customer_id).first()
        
        if not customer:
            print(f"[ERROR DTE] Cliente no encontrado para la venta {id}")
            return 0

        commune = self.db.query(CommuneModel).filter(CommuneModel.id == customer.commune_id).first()
        region = self.db.query(RegionModel).filter(RegionModel.id == customer.region_id).first()
        
        # Validar que commune y region existan (necesarios para facturas)
        if not commune and sale.dte_type_id != 1:
            print(f"[ERROR DTE] Comuna no encontrada para el cliente {customer.id}")
            return 0
        
        if not region and sale.dte_type_id != 1:
            print(f"[ERROR DTE] Región no encontrada para el cliente {customer.id}")
            return 0

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

        if not sales_products or len(sales_products) == 0:
            print(f"[ERROR DTE] No se encontraron productos para la venta {id}")
            print(f"[ERROR DTE] Verificando productos sin join...")
            # Verificar si hay productos sin join para debug
            products_check = self.db.query(SaleProductModel).filter(SaleProductModel.sale_id == id).all()
            print(f"[ERROR DTE] Productos encontrados sin join: {len(products_check) if products_check else 0}")
            if products_check:
                for p in products_check:
                    print(f"[ERROR DTE] - Producto ID: {p.product_id}, Quantity: {p.quantity}, Price: {p.price}, Inventory Movement ID: {p.inventory_movement_id}")
            return 0
        
        print(f"[DEBUG DTE] Se encontraron {len(sales_products)} productos para la venta {id}")

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

        print(f"[DEBUG DTE] Generando DTE para venta {id}")
        print(f"[DEBUG DTE] dte_type_id en venta: {sale.dte_type_id}")
        if sale.dte_type_id == 1:
            print(f"[DEBUG DTE] Generando BOLETA (dte_type_id = 1)")
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
                try:
                    # Obtener el folio de la respuesta
                    response_data = response.json()
                    print(f"[DEBUG BOLETA] Response data completa: {response_data}")
                    # El folio está dentro del campo 'data'
                    data_section = response_data.get('data', {})
                    folio = data_section.get('folio', None)
                    print(f"[DEBUG BOLETA] Folio obtenido: {folio}")
                    
                    if folio:
                        print(f"[DEBUG BOLETA] DTE generado exitosamente con folio: {folio}")
                        return folio
                    else:
                        print("[DEBUG BOLETA] No se pudo obtener el folio de la respuesta")
                        print(f"[DEBUG BOLETA] Estructura de data: {data_section}")
                        return 0
                except Exception as e:
                    print(f"[ERROR BOLETA] Error parseando respuesta JSON: {str(e)}")
                    print(f"[ERROR BOLETA] Response text: {response.text}")
                    return 0
            else:
                print(f"[DEBUG BOLETA] Error en la respuesta: {response.status_code}")
                print(f"[DEBUG BOLETA] Response text: {response.text}")
                try:
                    error_data = response.json()
                    print(f"[DEBUG BOLETA] Error data: {error_data}")
                except:
                    pass
                return 0
        else:
            print(f"[DEBUG DTE] Generando FACTURA (dte_type_id != 1, valor: {sale.dte_type_id})")
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
                            "CorreoRecep": customer.email if customer.email else "",
                            "DirRecep": customer.address if customer.address else "",
                            "GiroRecep": customer.activity if customer.activity else "",
                            "CmnaRecep": commune.commune if commune else "",
                            "CiudadRecep": region.region if region else ""
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
                try:
                    # Obtener el folio de la respuesta
                    response_data = response.json()
                    print(f"[DEBUG FACTURA] Response data completa: {response_data}")
                    # El folio está dentro del campo 'data'
                    data_section = response_data.get('data', {})
                    folio = data_section.get('folio', None)
                    print(f"[DEBUG FACTURA] Folio obtenido: {folio}")
                    
                    if folio:
                        print(f"[DEBUG FACTURA] DTE generado exitosamente con folio: {folio}")
                        return folio
                    else:
                        print("[DEBUG FACTURA] No se pudo obtener el folio de la respuesta")
                        print(f"[DEBUG FACTURA] Estructura de data: {data_section}")
                        return 0
                except Exception as e:
                    print(f"[ERROR FACTURA] Error parseando respuesta JSON: {str(e)}")
                    print(f"[ERROR FACTURA] Response text: {response.text}")
                    return 0
            else:
                print(f"[DEBUG FACTURA] Error en la respuesta: {response.status_code}")
                print(f"[DEBUG FACTURA] Response text: {response.text}")
                try:
                    error_data = response.json()
                    print(f"[DEBUG FACTURA] Error data: {error_data}")
                except:
                    pass
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