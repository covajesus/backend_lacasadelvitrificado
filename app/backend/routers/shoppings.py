from fastapi import APIRouter, Depends, Query
from app.backend.db.database import get_db
from sqlalchemy.orm import Session
from app.backend.schemas import UserLogin, PreInventoryStocks, ShoppingCreateInput, UpdateShopping, ShoppingList, StorePaymentDocuments, SendCustomsCompanyInput, StoreCustomsCompanyDocuments, ResendShoppingEmailsInput
from app.backend.db.models import ShoppingProductModel, PreInventoryStockModel, ProductModel, LotItemModel, UnitFeatureModel, LotModel
from app.backend.classes.shopping_class import ShoppingClass
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


@shoppings.get("/landed_unit_costs/{shopping_id}")
def get_landed_unit_costs(
    shopping_id: int,
    basis: str = Query(
        "simulator",
        description="simulator = misma lógica que Simulator.vue (líneas OC + quantity_to_buy); "
        "inventory = pre-inventario + calculate_unit_cost_for_product (crear inventario).",
    ),
    session_user: UserLogin = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """
    Costo unitario final en CLP (mercancía + gastos prorrateados por participación en CLP).

    Por defecto ``basis=simulator`` alinea con el Simulador de Precios del front.
    Use ``basis=inventory`` para el costo usado al crear inventario desde pre-inventario.
    """
    result = ShoppingClass(db).get_landed_unit_costs_for_shopping(shopping_id, basis=basis)
    if result.get("status") == "error":
        if result.get("message") == "Shopping not found":
            raise HTTPException(status_code=404, detail=result.get("message"))
        raise HTTPException(status_code=400, detail=result.get("message", "Error"))
    return {"message": result}


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
def send_customs_company_email(
    id: int,
    send_customs_company_inputs: SendCustomsCompanyInput,
    db: Session = Depends(get_db),
):
    result = ShoppingClass(db).send_customs_email(
        id,
        send_customs_company_inputs.customs_company_email,
        trigger_source="customs",
        advance_status=True,
    )
    if result.get("status") == "error":
        raise HTTPException(status_code=400, detail=result.get("message") or "Error al enviar correo")
    return {"message": result}

@shoppings.get("/email_recipients/{id}")
def email_recipients(
    id: int,
    session_user: UserLogin = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    data = ShoppingClass(db).get_email_recipients(id)
    if data.get("status") == "error":
        raise HTTPException(status_code=404, detail=data.get("message") or "Not found")
    return {"message": data}

@shoppings.post("/resend_emails/{id}")
def resend_emails(
    id: int,
    payload: ResendShoppingEmailsInput,
    session_user: UserLogin = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    data = ShoppingClass(db).resend_emails(id, payload.emails)
    if data.get("status") == "error":
        raise HTTPException(status_code=400, detail=data.get("message") or "Error al reenviar correos")
    return {"message": data}

@shoppings.post("/store")
def store_shopping(data: ShoppingCreateInput, db: Session = Depends(get_db)):
    shopping_data = ShoppingClass(db).store(data)
    shopping_id = shopping_data["shopping_id"]
    email_result = ShoppingClass(db).send_order_emails(shopping_id, trigger_source="store")
    return {"message": {"shopping": shopping_data, "email": email_result}}

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
    result = ShoppingClass(db).update(id, data)

    if result.get("status") == "success":
        email_result = ShoppingClass(db).send_order_emails(id, trigger_source="update")
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