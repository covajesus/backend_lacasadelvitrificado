from fastapi import APIRouter, Depends
from app.backend.db.database import get_db
from sqlalchemy.orm import Session
from app.backend.schemas import UserLogin, StoreInventory, InventoryList, AddAdjustmentInput, RemoveAdjustmentInput, PreInventoryStocks
from app.backend.classes.inventory_class import InventoryClass
from app.backend.classes.shopping_class import ShoppingClass
from app.backend.auth.auth_user import get_current_active_user
from datetime import datetime

inventories = APIRouter(
    prefix="/inventories",
    tags=["Inventories"]
)

@inventories.post("/")
def index(inventory_inputs: InventoryList, session_user: UserLogin = Depends(get_current_active_user), db: Session = Depends(get_db)):
    data = InventoryClass(db).get_all(inventory_inputs.page)

    return {"message": data}

@inventories.post("/store")
def store(inventory_inputs: StoreInventory, session_user: UserLogin = Depends(get_current_active_user), db: Session = Depends(get_db)):
    data = InventoryClass(db).store(inventory_inputs)

    return {"message": data}

@inventories.post("/pre_save_inventory_quantities/{shopping_id}")
def pre_save_inventory_quantities(
    shopping_id: int,
    data: PreInventoryStocks,
    db: Session = Depends(get_db)
):
    InventoryClass(db).pre_save_inventory_quantities(shopping_id, data)

    return {"message": "Cantidades de inventario actualizadas correctamente"}

@inventories.delete("/delete/{id}")
def delete(id: int, session_user: UserLogin = Depends(get_current_active_user), db: Session = Depends(get_db)):
    data = InventoryClass(db).delete(id)

    return {"message": data}

@inventories.get("/edit/{id}")
def edit(id: int, session_user: UserLogin = Depends(get_current_active_user), db: Session = Depends(get_db)):
    data = InventoryClass(db).get(id)

    return {"message": data}

@inventories.post("/add_adjustment")
def add_adjustment(inventory_inputs: AddAdjustmentInput, session_user: UserLogin = Depends(get_current_active_user), db: Session = Depends(get_db)):
    data = InventoryClass(db).add_adjustment(inventory_inputs)

    return {"message": data}

@inventories.post("/remove_adjustment")
def remove_adjustment(inventory_inputs: RemoveAdjustmentInput, session_user: UserLogin = Depends(get_current_active_user), db: Session = Depends(get_db)):
    data = InventoryClass(db).remove_adjustment(inventory_inputs)

    return {"message": data}

@inventories.post("/create_from_shopping/{shopping_id}")
def create_inventory_from_shopping(
    shopping_id: int, 
    session_user: UserLogin = Depends(get_current_active_user), 
    db: Session = Depends(get_db)
):
    """
    Crea inventario automáticamente desde un shopping, calculando el unit_cost 
    basado en el precio del producto + distribución de costos de envío por peso
    """
    try:
        shopping_class = ShoppingClass(db)
        inventory_class = InventoryClass(db)
        
        # Obtener productos del pre-inventario
        pre_inventory_products = shopping_class.get_pre_inventory_products(shopping_id)
        
        if isinstance(pre_inventory_products, dict) and pre_inventory_products.get("status") == "error":
            return {"status": "error", "message": "No se encontraron productos en el pre-inventario"}
        
        # Si es una respuesta paginada, obtener todos los datos
        if isinstance(pre_inventory_products, dict) and "data" in pre_inventory_products:
            products_data = pre_inventory_products["data"]
        else:
            products_data = pre_inventory_products
        
        created_inventories = []
        errors = []
        
        for product_data in products_data:
            try:
                # Calcular el unit_cost automáticamente
                result_calc = shopping_class.calculate_unit_cost_for_product(
                    shopping_id, 
                    product_data["product_id"], 
                    product_data["stock"]
                )
                
                # Obtener el precio_x_litro del resultado (ahora devuelve un diccionario)
                calculated_unit_cost = result_calc.get("precio_x_litro", 0)
                
                # Crear el objeto StoreInventory
                store_inventory = StoreInventory(
                    user_id=session_user.id,
                    product_id=product_data["product_id"],
                    location_id=1,  # Default location, puede ser parametrizable
                    stock=product_data["stock"],
                    unit_cost=int(calculated_unit_cost),  # Convertir a int según el schema
                    public_sale_price=int(product_data.get("final_unit_cost", 0) * 1.3),  # Margen del 30%
                    private_sale_price=int(product_data.get("final_unit_cost", 0) * 1.2),  # Margen del 20%
                    minimum_stock=5,  # Default, puede ser parametrizable
                    maximum_stock=100,  # Default, puede ser parametrizable
                    lot_number=str(product_data["lot_number"]),
                    arrival_date=datetime.now().date()
                )
                
                # Crear el inventario
                result = inventory_class.store(store_inventory)
                created_inventories.append({
                    "product_id": product_data["product_id"],
                    "product_name": product_data["product"],
                    "calculated_unit_cost": calculated_unit_cost,
                    "result": result
                })
                
            except Exception as e:
                errors.append({
                    "product_id": product_data["product_id"],
                    "error": str(e)
                })
        
        return {
            "status": "success",
            "message": f"Inventarios creados: {len(created_inventories)}, Errores: {len(errors)}",
            "created_inventories": created_inventories,
            "errors": errors
        }
        
    except Exception as e:
        return {"status": "error", "message": f"Error general: {str(e)}"}