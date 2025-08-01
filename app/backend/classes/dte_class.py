from app.backend.db.models import SaleModel, CustomerModel, SettingModel, RegionModel, CommuneModel, SaleProductModel, ProductModel, InventoryModel, UnitMeasureModel, SupplierModel, CategoryModel, LotItemModel, LotModel, InventoryMovementModel, InventoryLotItemModel
from datetime import datetime, timedelta
from app.backend.classes.setting_class import SettingClass
from sqlalchemy import func
import requests
import json

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

        print(validate_token)

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

            print(response.text)

            if response.status_code == 200:
                return 1
            else:
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

            print(response.text)

            if response.status_code == 200:
                return 1
            else:
                return 0