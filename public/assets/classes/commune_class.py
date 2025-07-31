from app.backend.db.models import CommuneModel


class CommuneClass:
    def __init__(self, db):
        self.db = db

    def get_all_no_paginations(self, region_id: int = None):
        try:
            data = self.db.query(
                CommuneModel.id,
                CommuneModel.commune,
                CommuneModel.added_date
            ).filter(CommuneModel.region_id == region_id).all()

            serialized_data = [{
                "id": commune.id,
                "commune": commune.commune,
                "added_date": commune.added_date.strftime("%Y-%m-%d %H:%M:%S") if commune.added_date else None
            } for commune in data]

            return {
                "data": serialized_data
            }

        except Exception as e:
            error_message = str(e)
            return f"Error: {error_message}"
