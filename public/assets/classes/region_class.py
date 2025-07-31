from app.backend.db.models import RegionModel


class RegionClass:
    def __init__(self, db):
        self.db = db

    def get_all_no_paginations(self):
        try:
            data = self.db.query(
                RegionModel.id,
                RegionModel.region,
                RegionModel.added_date
            ).all()

            serialized_data = [{
                "id": region.id,
                "region": region.region,
                "added_date": region.added_date.strftime("%Y-%m-%d %H:%M:%S") if region.added_date else None
            } for region in data]

            return {
                "data": serialized_data
            }

        except Exception as e:
            error_message = str(e)
            return f"Error: {error_message}"
