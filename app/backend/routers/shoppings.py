from fastapi import APIRouter, Depends
from app.backend.db.database import get_db
from sqlalchemy.orm import Session
from app.backend.schemas import UserLogin, PreInventoryStocks, ShoppingCreateInput, UpdateShopping, ShoppingList, StorePaymentDocuments, SendCustomsCompanyInput, StoreCustomsCompanyDocuments
from app.backend.db.models import ShoppingModel
from app.backend.classes.shopping_class import ShoppingClass
from app.backend.classes.template_class import TemplateClass
from app.backend.classes.file_class import FileClass
from app.backend.classes.email_class import EmailClass
from app.backend.auth.auth_user import get_current_active_user
from fastapi import File, UploadFile, HTTPException
from datetime import datetime
import uuid

shoppings = APIRouter(
    prefix="/shoppings",
    tags=["Shoppings"]
)

@shoppings.post("/")
def index(shopping_inputs: ShoppingList, db: Session = Depends(get_db)):
    data = ShoppingClass(db).get_all(shopping_inputs.page)

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
    payment_support: UploadFile = File(None),
    db: Session = Depends(get_db)
):
    try:
        timestamp = datetime.now().strftime("%Y_%m_%d_%H_%M_%S")
        unique_id = uuid.uuid4().hex[:8]  # 8 caracteres únicos
        file_extension = payment_support.filename.split('.')[-1] if '.' in payment_support.filename else ''
        file_category_name = 'payment_support'
        unique_filename = f"{timestamp}_{unique_id}.{file_extension}" if file_extension else f"{timestamp}_{unique_id}"

        support_remote_path = f"{file_category_name}_{unique_filename}"

        FileClass(db).upload(payment_support, support_remote_path)

        response = ShoppingClass(db).store_payment_documents(id, form_data, support_remote_path)

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
    customs_company_support: UploadFile = File(None),
    db: Session = Depends(get_db)
):
    try:
        timestamp = datetime.now().strftime("%Y_%m_%d_%H_%M_%S")
        unique_id = uuid.uuid4().hex[:8]  # 8 caracteres únicos
        file_extension = customs_company_support.filename.split('.')[-1] if '.' in customs_company_support.filename else ''
        file_category_name = 'customs_company_support'
        unique_filename = f"{timestamp}_{unique_id}.{file_extension}" if file_extension else f"{timestamp}_{unique_id}"

        support_remote_path = f"{file_category_name}_{unique_filename}"

        FileClass(db).upload(customs_company_support, support_remote_path)

        response = ShoppingClass(db).store_customs_company_documents(id, form_data, support_remote_path)

        return {"message": response}

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al procesar: {str(e)}")

@shoppings.post("/send_customs_company_email/{id}")
def send_customs_company_email(id:int, send_customs_company_inputs:SendCustomsCompanyInput, db: Session = Depends(get_db)):
    data = ShoppingClass(db).get_shopping_data(id)

    html_content = TemplateClass(db).generate_shopping_html_for_customs_company(data, id)
    email_html_content = TemplateClass(db).spanish_generate_email_content_html(data)
    pdf_bytes = TemplateClass(db).html_to_pdf_bytes(html_content)

    email_client = EmailClass("bergerseidle@vitrificadoschile.com", "VitrificadosChile", "uhwy oflr siuu faoo")

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
    email_client = EmailClass("bergerseidle@vitrificadoschile.com", "VitrificadosChile", "uhwy oflr siuu faoo")

    # Construir lista de destinatarios
    to_email = data.email
    cc_emails = [email for email in [data.second_email, data.third_email] if email]

    shopping_data = ShoppingClass(db).store(data)
    
    # Obtener shopping_number para el subject del correo
    shopping_record = db.query(ShoppingModel).filter(ShoppingModel.id == shopping_data["shopping_id"]).first()
    shopping_number = str(shopping_record.shopping_number) if shopping_record and shopping_record.shopping_number else str(shopping_data["shopping_id"])

    html_content_for_own_company = TemplateClass(db).generate_shopping_html_for_own_company(data, shopping_data["shopping_id"])
    html_content_for_supplier = TemplateClass(db).generate_shopping_html_for_supplier(data, shopping_data["shopping_id"])
    spanish_email_html_content = TemplateClass(db).spanish_generate_email_content_html(data)
    english_email_html_content = TemplateClass(db).english_generate_email_content_html(data)
    pdf_bytes_own = TemplateClass(db).html_to_pdf_bytes(html_content_for_own_company)
    pdf_bytes_supplier = TemplateClass(db).html_to_pdf_bytes(html_content_for_supplier)

    result = email_client.send_email(
        receiver_email=to_email,
        subject="Nueva Orden de Compra - N° " + shopping_number,
        message=spanish_email_html_content,
        pdf_bytes=pdf_bytes_own,
        pdf_filename="purcharse_order.pdf",
    )

    result = email_client.send_email(
        receiver_email=to_email,
        subject="Purchase Order - N° " + shopping_number,
        message=english_email_html_content,
        pdf_bytes=pdf_bytes_supplier,
        pdf_filename="purcharse_order.pdf",
        cc=cc_emails  # <-- nuevo parámetro para copia
    )

    return {"message": result}

@shoppings.post("/update/{id}")
def update_shopping(id: int, data: UpdateShopping, session_user: UserLogin = Depends(get_current_active_user), db: Session = Depends(get_db)):
    # Actualizar la compra
    result = ShoppingClass(db).update(id, data)
    
    if result.get("status") == "success":
        # Envío de correos igual que en store
        email_client = EmailClass("bergerseidle@vitrificadoschile.com", "VitrificadosChile", "uhwy oflr siuu faoo")

        # Construir lista de destinatarios
        to_email = data.email
        cc_emails = [email for email in [data.second_email, data.third_email] if email]

        # Generar contenido HTML y PDF
        # Obtener shopping_number para el subject del correo
        shopping_record = db.query(ShoppingModel).filter(ShoppingModel.id == id).first()
        shopping_number = str(shopping_record.shopping_number) if shopping_record and shopping_record.shopping_number else str(id)
        
        html_content_for_own_company = TemplateClass(db).generate_shopping_html_for_own_company(data, id)
        html_content_for_supplier = TemplateClass(db).generate_shopping_html_for_supplier(data, id)
        spanish_email_html_content = TemplateClass(db).spanish_generate_email_content_html(data)
        english_email_html_content = TemplateClass(db).english_generate_email_content_html(data)
        pdf_bytes_own = TemplateClass(db).html_to_pdf_bytes(html_content_for_own_company)
        pdf_bytes_supplier = TemplateClass(db).html_to_pdf_bytes(html_content_for_supplier)

        # Enviar correo a la empresa propia
        email_result = email_client.send_email(
            receiver_email=to_email,
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
