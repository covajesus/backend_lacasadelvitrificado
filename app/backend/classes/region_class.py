from app.backend.db.models import RegionModel
from app.backend.services.crud.base_domain_service import BaseDomainService


class RegionClass(BaseDomainService):
    @staticmethod
    def _serialize_row(region):
        return {
            "id": region.id,
            "region": region.region,
            "added_date": region.added_date.strftime("%Y-%m-%d %H:%M:%S") if region.added_date else None,
        }

    def get_all_no_paginations(self):
        query = self.db.query(RegionModel.id, RegionModel.region, RegionModel.added_date)
        return self.list_wrapped(query, self._serialize_row)
