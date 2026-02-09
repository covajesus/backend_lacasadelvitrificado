from fastapi import APIRouter, Depends
from app.backend.db.database import get_db
from sqlalchemy.orm import Session
from app.backend.schemas import UserLogin, PreInventoryStocks, ShoppingCreateInput, UpdateShopping, ShoppingList, StorePaymentDocuments, SendCustomsCompanyInput, StoreCustomsCompanyDocuments
from app.backend.db.models import ShoppingModel, SettingModel, ShoppingProductModel, PreInventoryStockModel, ProductModel, LotItemModel, UnitFeatureModel, LotModel
from app.backend.classes.shopping_class import ShoppingClass
from app.backend.classes.template_class import TemplateClass
from app.backend.classes.email_class import EmailClass
from app.backend.auth.auth_user import get_current_active_user
from fastapi import HTTPException
from datetime import datetime

shoppings = APIRouter(
    prefix="/shoppings",
    tags=["Shoppings"]
)

@shoppings.post("/")
def index(shopping_inputs: ShoppingList, db: Session = Depends(get_db)):
    data = ShoppingClass(db).get_all(shopping_inputs.page)

    return {"message": data}

@shoppings.get("/list")
def list_all(db: Session = Depends(get_db)):
    data = ShoppingClass(db).get_list()

    return {"message": data}

@shoppings.get("/products/{shopping_id}")
def get_shopping_products(shopping_id: int, db: Session = Depends(get_db)):
    data = ShoppingClass(db).get_shopping_products_detail(shopping_id)

    return {"message": data}

@shoppings.get("/edit/{id}")
def edit(id: int, session_user: UserLogin = Depends(get_current_active_user), db: Session = Depends(get_db)):
    data = ShoppingClass(db).get(id)

    return {"message": data}

@shoppings.get("/confirm/{id}")
def confirm(id: int, session_user: UserLogin = Depends(get_current_active_user), db: Session = Depends(get_db)):
    data = ShoppingClass(db).confirm(id)

    return {"message": data}

@shoppings.post("/get_pre_inventory_products/{id}")
def get_products(id: int, shopping_inputs: ShoppingList, session_user: UserLogin = Depends(get_current_active_user), db: Session = Depends(get_db)):
    data = ShoppingClass(db).get_pre_inventory_products(id)

    return {"message": data}

@shoppings.post("/get_products/{id}")
def get_products(id: int, shopping_inputs: ShoppingList, session_user: UserLogin = Depends(get_current_active_user), db: Session = Depends(get_db)):
    data = ShoppingClass(db).get_products(id)

    return {"message": data}

@shoppings.post("/upload_payment_documents/{id}")
def store(
    id: int,
    form_data: StorePaymentDocuments = Depends(StorePaymentDocuments.as_form),
    db: Session = Depends(get_db)
):
    try:
        response = ShoppingClass(db).store_payment_documents(id, form_data)

        return {"message": response}

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al procesar: {str(e)}")

@shoppings.post("/save_inventory_quantities/{shopping_id}")
async def save_inventory_quantities(
    shopping_id: int,
    pre_inventory_stocks: PreInventoryStocks,
    db: Session = Depends(get_db)
):
    ShoppingClass(db).save_pre_inventory_quantities(shopping_id, pre_inventory_stocks.items)
    return {"message": "Quantities saved successfully"}
    
@shoppings.post("/upload_customs_company_documents/{id}")
def store(
    id: int,
    form_data: StoreCustomsCompanyDocuments = Depends(StoreCustomsCompanyDocuments.as_form),
    db: Session = Depends(get_db)
):
    try:
        response = ShoppingClass(db).store_customs_company_documents(id, form_data)

        return {"message": response}

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al procesar: {str(e)}")

@shoppings.post("/send_customs_company_email/{id}")
def send_customs_company_email(id:int, send_customs_company_inputs:SendCustomsCompanyInput, db: Session = Depends(get_db)):
    data = ShoppingClass(db).get_shopping_data(id)

    html_content = TemplateClass(db).generate_shopping_html_for_customs_company(data, id)
    email_html_content = TemplateClass(db).spanish_generate_email_content_html(data)
    pdf_bytes = TemplateClass(db).html_to_pdf_bytes(html_content)

    email_client = EmailClass("bergerseidle@vitrificadoschile.com", "VitrificadosChile", "bhva zicx wfub duxg")

    result = email_client.send_email(
        receiver_email=send_customs_company_inputs.customs_company_email,
        subject="Purchase Order",
        message=email_html_content,
        pdf_bytes=pdf_bytes,
        pdf_filename="purcharse_order.pdf"
    )

    ShoppingClass(db).send_customs_company_email(id, send_customs_company_inputs.customs_company_email)

    return {"message": 'Email sent successfully'}

@shoppings.post("/store")
def store_shopping(data: ShoppingCreateInput, db: Session = Depends(get_db)):
    email_client = EmailClass("bergerseidle@vitrificadoschile.com", "VitrificadosChile", "bhva zicx wfub duxg")

    # Obtener el email de configuración para correos internos
    settings = db.query(SettingModel).first()
    internal_email = settings.account_email if settings and settings.account_email else data.email

    # Construir lista de destinatarios para proveedor
    to_email = data.email
    cc_emails = [email for email in [data.second_email, data.third_email] if email]

    shopping_data = ShoppingClass(db).store(data)
    
    # Usar shopping_number directamente del objeto data
    shopping_number = str(data.shopping_number)

    html_content_for_own_company = TemplateClass(db).generate_shopping_html_for_own_company(data, shopping_data["shopping_id"])
    html_content_for_supplier = TemplateClass(db).generate_shopping_html_for_supplier(data, shopping_data["shopping_id"])
    spanish_email_html_content = TemplateClass(db).spanish_generate_email_content_html(data)
    english_email_html_content = TemplateClass(db).english_generate_email_content_html(data)
    pdf_bytes_own = TemplateClass(db).html_to_pdf_bytes(html_content_for_own_company)
    pdf_bytes_supplier = TemplateClass(db).html_to_pdf_bytes(html_content_for_supplier)

    # Enviar correo interno a account_email
    result = email_client.send_email(
        receiver_email=internal_email,
        subject="Nueva Orden de Compra - N° " + shopping_number,
        message=spanish_email_html_content,
        pdf_bytes=pdf_bytes_own,
        pdf_filename="purcharse_order.pdf",
    )

    # Enviar correo al proveedor
    result = email_client.send_email(
        receiver_email=to_email,
        subject="Purchase Order - N° " + shopping_number,
        message=english_email_html_content,
        pdf_bytes=pdf_bytes_supplier,
        pdf_filename="purcharse_order.pdf",
        cc=cc_emails  # <-- nuevo parámetro para copia
    )

    return {"message": result}

@shoppings.get("/test")
def test(db: Session = Depends(get_db)):
    shopping_class = ShoppingClass(db)
    result = []
    
    # Obtener todos los productos
    all_products = db.query(ProductModel).all()
    total_products = len(all_products)
    
    products_with_lot_items = 0
    lot_items_processed = 0
    lot_items_skipped_no_lot = 0
    lot_items_skipped_no_pre_stock = 0
    
    for product in all_products:
        try:
            # Obtener todos los lot_items de este producto
            lot_items = db.query(LotItemModel).filter(
                LotItemModel.product_id == product.id
            ).all()
            
            if not lot_items:
                continue
            
            products_with_lot_items += 1
            
            # Obtener quantity_per_package de unit_features
            unit_feature = db.query(UnitFeatureModel).filter(
                UnitFeatureModel.product_id == product.id
            ).first()
            
            quantity_per_package = unit_feature.quantity_per_package if unit_feature and unit_feature.quantity_per_package else 1
            
            # Procesar cada lot_item
            for lot_item in lot_items:
                # Obtener el lot para encontrar el lot_number
                lot = db.query(LotModel).filter(LotModel.id == lot_item.lot_id).first()
                
                if not lot:
                    lot_items_skipped_no_lot += 1
                    continue
                
                # Buscar el shopping_id desde PreInventoryStockModel usando product_id y lot_number
                pre_stock = db.query(PreInventoryStockModel).filter(
                    PreInventoryStockModel.product_id == product.id,
                    PreInventoryStockModel.lot_number == lot.lot_number
                ).first()
                
                if not pre_stock:
                    # Si no encuentra por lot_number, buscar solo por product_id
                    pre_stock = db.query(PreInventoryStockModel).filter(
                        PreInventoryStockModel.product_id == product.id
                    ).first()
                
                if not pre_stock:
                    lot_items_skipped_no_pre_stock += 1
                    continue
                
                shopping_id = pre_stock.shopping_id
                quantity = pre_stock.stock if pre_stock else 0
                
                # Llamar a calculate_unit_cost_for_product para obtener precio_x_litro
                result_calc = shopping_class.calculate_unit_cost_for_product(
                    shopping_id=shopping_id,
                    product_id=product.id,
                    quantity=quantity
                )
                
                precio_x_litro = result_calc.get("precio_x_litro", 0)
                
                # Calcular private_sale_price (precio_x_litro * quantity_per_package) y redondear
                private_sale_price = round(precio_x_litro * quantity_per_package)
                
                # Actualizar el lot_item
                lot_item.private_sale_price = private_sale_price
                lot_item.updated_date = datetime.now()
                
                lot_items_processed += 1
                
                result.append({
                    "product_id": product.id,
                    "product_name": result_calc.get("product_name", product.product),
                    "lot_item_id": lot_item.id,
                    "precio_x_litro": precio_x_litro,
                    "quantity_per_package": quantity_per_package,
                    "private_sale_price": private_sale_price,
                    "status": "updated"
                })
            
            db.commit()
            
        except Exception as e:
            result.append({
                "product_id": product.id,
                "product_name": product.product if hasattr(product, 'product') else "N/A",
                "status": "error",
                "error": str(e)
            })
    
    return {
        "message": result, 
        "total_processed": len(result),
        "summary": {
            "total_products": total_products,
            "products_with_lot_items": products_with_lot_items,
            "lot_items_processed": lot_items_processed,
            "lot_items_skipped_no_lot": lot_items_skipped_no_lot,
            "lot_items_skipped_no_pre_stock": lot_items_skipped_no_pre_stock
        }
    }

@shoppings.post("/update/{id}")
def update_shopping(id: int, data: UpdateShopping, session_user: UserLogin = Depends(get_current_active_user), db: Session = Depends(get_db)):
    # Actualizar la compra
    result = ShoppingClass(db).update(id, data)
    
    if result.get("status") == "success":
        # Envío de correos igual que en store
        email_client = EmailClass("bergerseidle@vitrificadoschile.com", "VitrificadosChile", "bhva zicx wfub duxg")

        # Obtener el email de configuración para correos internos
        settings = db.query(SettingModel).first()
        internal_email = settings.account_email if settings and settings.account_email else data.email

        # Construir lista de destinatarios para proveedor
        to_email = data.email
        cc_emails = [email for email in [data.second_email, data.third_email] if email]

        # Generar contenido HTML y PDF
        # Usar shopping_number directamente del objeto data
        shopping_number = str(data.shopping_number)
        
        html_content_for_own_company = TemplateClass(db).generate_shopping_html_for_own_company(data, id)
        html_content_for_supplier = TemplateClass(db).generate_shopping_html_for_supplier(data, id)
        spanish_email_html_content = TemplateClass(db).spanish_generate_email_content_html(data)
        english_email_html_content = TemplateClass(db).english_generate_email_content_html(data)
        pdf_bytes_own = TemplateClass(db).html_to_pdf_bytes(html_content_for_own_company)
        pdf_bytes_supplier = TemplateClass(db).html_to_pdf_bytes(html_content_for_supplier)

        # Enviar correo interno a account_email
        email_result = email_client.send_email(
            receiver_email=internal_email,
            subject="Orden de Compra Actualizada - N° " + shopping_number,
            message=spanish_email_html_content,
            pdf_bytes=pdf_bytes_own,
            pdf_filename="purcharse_order.pdf",
        )

        # Enviar correo al proveedor
        email_result = email_client.send_email(
            receiver_email=to_email,
            subject="Updated Purchase Order - N° " + shopping_number,
            message=english_email_html_content,
            pdf_bytes=pdf_bytes_supplier,
            pdf_filename="purcharse_order.pdf",
            cc=cc_emails
        )

        return {"message": {"update": result, "email": email_result}}
    else:
        return {"message": result}

@shoppings.get("/get_inventories/{shopping_id}")
def get_inventories_by_shopping_id(
    shopping_id: int,
    session_user: UserLogin = Depends(get_current_active_user), 
    db: Session = Depends(get_db)
):
    data = ShoppingClass(db).get_inventories_by_shopping_id(shopping_id)

    return {"message": data}

@shoppings.delete("/delete/{id}")
def delete_shopping(id: int, session_user: UserLogin = Depends(get_current_active_user), db: Session = Depends(get_db)):
    """
    Elimina un shopping y todos sus registros relacionados:
    - Productos del shopping (ShoppingProductModel)
    - Stocks pre-inventario (PreInventoryStockModel)
    - El shopping mismo (ShoppingModel)
    """
    data = ShoppingClass(db).delete(id)
    
    if isinstance(data, dict) and data.get("status") == "error":
        raise HTTPException(status_code=400, detail=data["message"])
    
    return {"message": data}