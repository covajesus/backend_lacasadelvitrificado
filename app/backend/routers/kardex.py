from fastapi import APIRouter, Depends
from app.backend.db.database import get_db
from sqlalchemy.orm import Session
from app.backend.classes.kardex_class import KardexClass
from app.backend.auth.auth_user import get_current_active_user
from app.backend.schemas import UserLogin

kardex = APIRouter(
    prefix="/kardex",
    tags=["Kardex"]
)

@kardex.get("/")
def index(page: int = 0, items_per_page: int = 10, session_user: UserLogin = Depends(get_current_active_user), db: Session = Depends(get_db)):
    """
    Obtener todos los registros de kardex con paginación.
    
    - **page**: Número de página (0 para obtener todos)
    - **items_per_page**: Elementos por página (por defecto 10)
    """
    data = KardexClass(db).get_all(page, items_per_page)
    return {"message": data}

@kardex.get("/product/{product_id}")
def get_by_product(product_id: int, session_user: UserLogin = Depends(get_current_active_user), db: Session = Depends(get_db)):
    """
    Obtener registro de kardex por ID de producto.
    
    - **product_id**: ID del producto
    """
    data = KardexClass(db).get_by_product_id(product_id)
    return {"message": data}

@kardex.get("/summary")
def get_summary(session_user: UserLogin = Depends(get_current_active_user), db: Session = Depends(get_db)):
    """
    Obtener resumen general del kardex.
    
    Incluye:
    - Total de productos en kardex
    - Cantidad total en inventario
    - Valor total del inventario
    - Costo promedio general
    """
    data = KardexClass(db).get_summary()
    return {"message": data}
