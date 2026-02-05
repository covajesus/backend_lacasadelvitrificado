from fastapi import APIRouter, Depends
from app.backend.db.database import get_db
from sqlalchemy.orm import Session
from app.backend.schemas import UserLogin, ProductList, StoreProduct, ProductSearch
from app.backend.classes.product_class import ProductClass
from app.backend.auth.auth_user import get_current_active_user
from app.backend.classes.file_class import FileClass
from fastapi import File, UploadFile, HTTPException
from datetime import datetime
import uuid

products = APIRouter(
    prefix="/products",
    tags=["Products"]
)

@products.post("/")
def index(product_input: ProductList, session_user: UserLogin = Depends(get_current_active_user), db: Session = Depends(get_db)):
    data = ProductClass(db).get_all(
        page=product_input.page,
        supplier_id=product_input.supplier_id,
        product_id=product_input.product_id
    )

    return {"message": data}

@products.post("/store")
def store(
    form_data: StoreProduct = Depends(StoreProduct.as_form),
    photo: UploadFile = File(None),
    catalog: UploadFile = File(None),
    db: Session = Depends(get_db)
):
    try:
        timestamp = datetime.now().strftime("%Y_%m_%d_%H_%M_%S")
        unique_id = uuid.uuid4().hex[:8]  # 8 caracteres únicos
        # Manejar archivos con múltiples puntos (ej: imagen.android.jpg)
        file_extension = photo.filename.rsplit('.', 1)[-1].lower() if '.' in photo.filename else ''
        file_category_name = 'photo'
        unique_filename = f"{timestamp}_{unique_id}.{file_extension}" if file_extension else f"{timestamp}_{unique_id}"

        photo_remote_path = f"{file_category_name}_{unique_filename}"

        FileClass(db).upload(photo, photo_remote_path)

        timestamp = datetime.now().strftime("%Y_%m_%d_%H_%M_%S")
        unique_id = uuid.uuid4().hex[:8]  # 8 caracteres únicos
        file_extension = catalog.filename.split('.')[-1] if '.' in catalog.filename else ''
        file_category_name = 'catalog'
        unique_filename = f"{timestamp}_{unique_id}.{file_extension}" if file_extension else f"{timestamp}_{unique_id}"

        catalog_remote_path = f"{file_category_name}_{unique_filename}"

        FileClass(db).upload(catalog, catalog_remote_path)

        response = ProductClass(db).store(form_data, photo_remote_path, catalog_remote_path)

        return {"message": response}

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al procesar: {str(e)}")

@products.delete("/delete/{id}")
def delete(id: int, session_user: UserLogin = Depends(get_current_active_user), db: Session = Depends(get_db)):
    data = ProductClass(db).delete(id)

    return {"message": data}

@products.get("/edit/{id}")
def edit(id: int, session_user: UserLogin = Depends(get_current_active_user), db: Session = Depends(get_db)):
    print(f"Fetching product with ID: {id}")
    data = ProductClass(db).get(id)

    return {"message": data}

@products.get("/budget/{id}")
def budget(id: int, customer_id: int = None, session_user: UserLogin = Depends(get_current_active_user), db: Session = Depends(get_db)):
    """
    Endpoint para obtener datos del producto para presupuesto.
    Devuelve lo mismo que /edit/{id} pero con public_sale_price y discount_percentage del cliente.
    """
    data = ProductClass(db).budget(id, customer_id=customer_id)

    return {"message": data}

@products.get("/sale/data/{id}")
def sale(id: int, session_user: UserLogin = Depends(get_current_active_user), db: Session = Depends(get_db)):
    data = ProductClass(db).sale_data(id)

    return {"message": data}

@products.get("/sale_list/{category_id}")
def sale_list(category_id: int, session_user: UserLogin = Depends(get_current_active_user), db: Session = Depends(get_db)):
    data = ProductClass(db).sale_list(category_id)

    return {"message": data}

@products.get("/sale_list_by_category/{category_id}")
def sale_list(category_id: int, session_user: UserLogin = Depends(get_current_active_user), db: Session = Depends(get_db)):
    data = ProductClass(db).sale_list_by_category(category_id)

    return {"message": data}

@products.get("/list")
def list(session_user: UserLogin = Depends(get_current_active_user), db: Session = Depends(get_db)):
    data = ProductClass(db).get_list()

    return {"message": data}

@products.get("/supplier/{supplier_identifier}")
def products_by_supplier(supplier_identifier: str, session_user: UserLogin = Depends(get_current_active_user), db: Session = Depends(get_db)):
    """
    Endpoint para obtener productos filtrados por proveedor.
    
    Args:
        supplier_identifier: RUT del proveedor (ej: "12345678-9") o ID del proveedor (ej: "123")
    
    Returns:
        Lista de productos del proveedor especificado
    """
    data = ProductClass(db).get_products_by_supplier(supplier_identifier)

    return {"message": data}

@products.post("/search")
def search(search_input: ProductSearch, session_user: UserLogin = Depends(get_current_active_user), db: Session = Depends(get_db)):
    """
    Endpoint para buscar productos por código o nombre usando LIKE.
    
    Args:
        search_input: Objeto con el término de búsqueda (q) que se buscará en el código y nombre del producto
    
    Returns:
        Lista de productos que coinciden con el término de búsqueda
    """
    data = ProductClass(db).search(search_input.q)
    
    return {"message": data}

@products.post("/update/{id}")
def update(
    id: int,
    form_data: StoreProduct = Depends(StoreProduct.as_form),
    photo: UploadFile = File(None),
    catalog: UploadFile = File(None),
    db: Session = Depends(get_db)
):
    try:
        photo_remote_path = None
        catalog_remote_path = None

        if photo:
            timestamp = datetime.now().strftime("%Y_%m_%d_%H_%M_%S")
            unique_id = uuid.uuid4().hex[:8]
            # Manejar archivos con múltiples puntos (ej: imagen.android.jpg)
            file_extension = photo.filename.rsplit('.', 1)[-1].lower() if '.' in photo.filename else ''
            file_category_name = 'photo'
            unique_filename = f"{timestamp}_{unique_id}.{file_extension}" if file_extension else f"{timestamp}_{unique_id}"
            photo_remote_path = f"{file_category_name}_{unique_filename}"

            FileClass(db).upload(photo, photo_remote_path)

        if catalog:
            timestamp = datetime.now().strftime("%Y_%m_%d_%H_%M_%S")
            unique_id = uuid.uuid4().hex[:8]
            # Manejar archivos con múltiples puntos (ej: imagen.android.jpg)
            file_extension = catalog.filename.rsplit('.', 1)[-1].lower() if '.' in catalog.filename else ''
            file_category_name = 'catalog'
            unique_filename = f"{timestamp}_{unique_id}.{file_extension}" if file_extension else f"{timestamp}_{unique_id}"
            catalog_remote_path = f"{file_category_name}_{unique_filename}"

            FileClass(db).upload(catalog, catalog_remote_path)

        response = ProductClass(db).update(id, form_data, photo_remote_path, catalog_remote_path)

        return {"message": response}

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al procesar: {str(e)}") 