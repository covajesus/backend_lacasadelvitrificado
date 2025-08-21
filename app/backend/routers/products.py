from fastapi import APIRouter, Depends
from app.backend.db.database import get_db
from sqlalchemy.orm import Session
from app.backend.schemas import UserLogin, ProductList, StoreProduct
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
    data = ProductClass(db).get_all(product_input.page)

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
        file_extension = photo.filename.split('.')[-1] if '.' in photo.filename else ''
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
            file_extension = photo.filename.split('.')[-1] if '.' in photo.filename else ''
            file_category_name = 'photo'
            unique_filename = f"{timestamp}_{unique_id}.{file_extension}" if file_extension else f"{timestamp}_{unique_id}"
            photo_remote_path = f"{file_category_name}_{unique_filename}"

            FileClass(db).upload(photo, photo_remote_path)

        if catalog:
            timestamp = datetime.now().strftime("%Y_%m_%d_%H_%M_%S")
            unique_id = uuid.uuid4().hex[:8]
            file_extension = catalog.filename.split('.')[-1] if '.' in catalog.filename else ''
            file_category_name = 'catalog'
            unique_filename = f"{timestamp}_{unique_id}.{file_extension}" if file_extension else f"{timestamp}_{unique_id}"
            catalog_remote_path = f"{file_category_name}_{unique_filename}"

            FileClass(db).upload(catalog, catalog_remote_path)

        response = ProductClass(db).update(id, form_data, photo_remote_path, catalog_remote_path)

        return {"message": response}

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al procesar: {str(e)}") 