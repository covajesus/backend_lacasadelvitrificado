from app.backend.db.models import CommuneModel
from app.backend.services.crud.base_domain_service import BaseDomainService


class CommuneClass(BaseDomainService):
    @staticmethod
    def _serialize_row(commune):
        return {
            "id": commune.id,
            "commune": commune.commune,
            "added_date": commune.added_date.strftime("%Y-%m-%d %H:%M:%S") if commune.added_date else None,
        }

    def get_all_no_paginations(self, region_id: int = None):
        query = self.db.query(CommuneModel.id, CommuneModel.commune, CommuneModel.added_date).filter(
            CommuneModel.region_id == region_id
        )
        return self.list_wrapped(query, self._serialize_row)
