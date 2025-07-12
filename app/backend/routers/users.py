from fastapi import APIRouter, Depends, HTTPException
from app.backend.db.database import get_db
from sqlalchemy.orm import Session
from app.backend.schemas import User, UpdateUser, UserLogin, RecoverUser, ConfirmEmail, UserList
from app.backend.classes.user_class import UserClass
from app.backend.auth.auth_user import get_current_active_user

users = APIRouter(
    prefix="/users",
    tags=["User"]
)

@users.post("/")
def index(user: UserList, session_user: UserLogin = Depends(get_current_active_user), db: Session = Depends(get_db)):
    data = UserClass(db).get_all(user.rut, user.page)

    return {"message": data}

@users.post("/store")
def store(user:User, session_user: UserLogin = Depends(get_current_active_user), db: Session = Depends(get_db)):
    user_inputs = user.dict()
    data = UserClass(db).store(user_inputs)

    return {"message": data}

@users.get("/refresh_password/{rut}")
def resfresh_password(rut:int, session_user: UserLogin = Depends(get_current_active_user), db: Session = Depends(get_db)):
    data = UserClass(db).refresh_password(rut)

    return {"message": data}

@users.get("/edit/{id}")
def edit(id:int, session_user: UserLogin = Depends(get_current_active_user), db: Session = Depends(get_db)):
    try:
        user_data = UserClass(db).get('id', id)
        
        if not user_data:
            raise HTTPException(status_code=404, detail="Usuario no encontrado")

        return {"message": user_data}

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al obtener el usuario: {str(e)}")

@users.delete("/delete/{id}")
def delete(id:int, session_user: UserLogin = Depends(get_current_active_user), db: Session = Depends(get_db)):
    data = UserClass(db).delete(id)

    return {"message": data}

@users.put("/update/{id}")
def update(id: int, user: UpdateUser, session_user: UserLogin = Depends(get_current_active_user), db: Session = Depends(get_db)):
    user_inputs = user.dict()
    data = UserClass(db).update(id, user_inputs)

    return {"message": data}

@users.post("/recover")
def recover(user:RecoverUser, session_user: UserLogin = Depends(get_current_active_user), db: Session = Depends(get_db)):
    user_inputs = user.dict()
    data = UserClass(db).recover(user_inputs)

    return {"message": data}

@users.patch("/confirm_email")
def confirm_email(user_inputs:ConfirmEmail, session_user: UserLogin = Depends(get_current_active_user), db: Session = Depends(get_db)):
    data = UserClass(db).confirm_email(user_inputs)

    return {"message": data}