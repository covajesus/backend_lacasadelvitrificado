from datetime import datetime
import uuid

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy.orm import Session

from app.backend.auth.auth_user import get_current_active_user
from app.backend.classes.advertising_class import AdvertisingClass
from app.backend.classes.file_class import FileClass
from app.backend.db.database import get_db
from app.backend.schemas import AdvertisingList, StoreAdvertising, UpdateAdvertising, UserLogin

advertising = APIRouter(
    prefix="/advertising",
    tags=["Advertising"],
)


def _save_campaign_image(db: Session, image: UploadFile | None) -> str | None:
    if not image or not image.filename:
        return None
    timestamp = datetime.now().strftime("%Y_%m_%d_%H_%M_%S")
    unique_id = uuid.uuid4().hex[:8]
    file_extension = image.filename.rsplit('.', 1)[-1].lower() if '.' in image.filename else 'jpg'
    remote_path = f"campaign_{timestamp}_{unique_id}.{file_extension}"
    FileClass(db).upload(image, remote_path)
    return remote_path


@advertising.post("/")
def index(
    campaign_inputs: AdvertisingList,
    session_user: UserLogin = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    data = AdvertisingClass(db).get_all(
        page=campaign_inputs.page,
        q=campaign_inputs.q,
        status_id=campaign_inputs.status_id,
    )
    return {"message": data}


@advertising.post("/store")
def store(
    form_data: StoreAdvertising = Depends(StoreAdvertising.as_form),
    image: UploadFile = File(None),
    session_user: UserLogin = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    try:
        image_path = _save_campaign_image(db, image)
        data = AdvertisingClass(db).store(form_data, image_path=image_path)
        return {"message": data}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Error al crear campaña: {exc}") from exc


@advertising.post("/update/{id}")
def update(
    id: int,
    form_data: UpdateAdvertising = Depends(UpdateAdvertising.as_form),
    image: UploadFile = File(None),
    session_user: UserLogin = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    try:
        image_path = _save_campaign_image(db, image)
        data = AdvertisingClass(db).update(
            id,
            form_data,
            image_path=image_path,
            remove_image=bool(form_data.remove_image),
        )
        return {"message": data}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Error al actualizar campaña: {exc}") from exc


@advertising.get("/edit/{id}")
def edit(
    id: int,
    session_user: UserLogin = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    data = AdvertisingClass(db).get(id)
    return {"message": data}


@advertising.delete("/delete/{id}")
def delete(
    id: int,
    session_user: UserLogin = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    data = AdvertisingClass(db).delete(id)
    return {"message": data}


@advertising.post("/send/{id}")
def send(
    id: int,
    session_user: UserLogin = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    data = AdvertisingClass(db).start_send(id)
    return {"message": data}


@advertising.get("/send_progress/{id}")
def send_progress(
    id: int,
    session_user: UserLogin = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    data = AdvertisingClass(db).get_send_progress(id)
    return {"message": data}


@advertising.get("/promotion_preview/{promotion_id}")
def promotion_preview(
    promotion_id: int,
    extra_message: str = '',
    session_user: UserLogin = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    data = AdvertisingClass(db).get_promotion_preview(promotion_id, extra_message=extra_message)
    return {"message": data}


@advertising.get("/message_preview")
def message_preview(
    message: str = '',
    session_user: UserLogin = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    data = AdvertisingClass(db).get_message_preview(message)
    return {"message": data}
