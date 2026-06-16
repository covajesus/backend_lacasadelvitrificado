from app.backend.db.models import RolModel
from app.backend.services.crud.base_domain_service import BaseDomainService


class RolClass(BaseDomainService):
    def get_all(self):
        return self.safe(lambda: self._get_all())

    def _get_all(self):
        data = self.db.query(RolModel).order_by(RolModel.id).all()
        if not data:
            return "No data found"
        return data

    def get(self, field, value):
        return self.safe(
            lambda: self.db.query(RolModel).filter(getattr(RolModel, field) == value).first()
        )

    def store(self, Rol_inputs):
        return self.safe(lambda: self._store(Rol_inputs), rollback=True)

    def _store(self, Rol_inputs):
        data = RolModel(**Rol_inputs)
        self.db.add(data)
        self.db.commit()
        return 1

    def delete(self, id):
        return self.safe(lambda: self._delete(id), rollback=True)

    def _delete(self, id):
        data = self.db.query(RolModel).filter(RolModel.id == id).first()
        if not data:
            return "No data found"
        self.db.delete(data)
        self.db.commit()
        return 1

    def update(self, id, rol):
        existing_rol = self.db.query(RolModel).filter(RolModel.id == id).one_or_none()
        if not existing_rol:
            return "No data found"
        return self.safe(lambda: self._update(existing_rol, rol), rollback=True)

    def _update(self, existing_rol, rol):
        existing_rol_data = rol.dict(exclude_unset=True)
        for key, value in existing_rol_data.items():
            setattr(existing_rol, key, value)
        self.db.commit()
        return 1
