from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.backend.db.database import get_db
from app.backend.classes.dte_class import DteClass
from app.backend.auth.auth_user import get_current_active_user
from app.backend.schemas import UserLogin

dtes = APIRouter(
    prefix="/dtes",
    tags=["DTEs"]
)

@dtes.get("/download/{folio}")
def download_dte(folio: int, db: Session = Depends(get_db)):
    """
    Descarga el PDF del DTE por folio
    """
    return DteClass(db).download(folio)
