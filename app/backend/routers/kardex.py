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
    Listado tipo inventario/kardex (usado en frontend /inventarios).

    Cantidad = suma de ``inventories_movements`` por producto; costo medio derivado de movimientos.
    Precios máximos público/privado desde ``lot_items``. ``inventory_id`` = inventario con mayor ``id`` por SKU.
    ``kardex_values_id`` en la respuesta coincide con ``product_id`` (compatibilidad con el cliente).

    - **page**: 0 = sin paginar (todos); >=1 pagina con offset.
    - **items_per_page**: tamaño de página cuando ``page`` >= 1.
    """
    data = KardexClass(db).get_all(page, items_per_page)
    return {"message": data}

@kardex.get("/product/{product_id}")
def get_by_product(product_id: int, session_user: UserLogin = Depends(get_current_active_user), db: Session = Depends(get_db)):
    """
    Kardex por producto: saldos y costo desde ``inventories_movements``, mismo criterio que el listado.

    - **product_id**: ID del producto
    """
    data = KardexClass(db).get_by_product_id(product_id)
    return {"message": data}

@kardex.get("/summary")
def get_summary(session_user: UserLogin = Depends(get_current_active_user), db: Session = Depends(get_db)):
    """
    Resumen: productos con inventario, cantidad total en movimientos, valor y costo medio global.
    """
    data = KardexClass(db).get_summary()
    return {"message": data}
