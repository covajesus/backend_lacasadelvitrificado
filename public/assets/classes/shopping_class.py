from fastapi import HTTPException
from app.backend.db.models import ShoppingModel, ShoppingProductModel, KilogramFeatureModel, LiterFeatureModel
from datetime import datetime

class ShoppingClass:
    def __init__(self, db):
        self.db = db

    def store(self, data):
        try:
            new_shopping = ShoppingModel(
                    supplier_id=data.supplier_id,
                    email=data.email,
                    total=data.total,
                    added_date=datetime.utcnow(),
                    updated_date=datetime.utcnow()
                )

            self.db.add(new_shopping)
            self.db.commit()
            self.db.refresh(new_shopping)

            for product in data.products:
                if product.unit_measure_id == 1:
                    kilogram_features = self.db.query(KilogramFeatureModel).filter(KilogramFeatureModel.product_id == product.product_id).first()

                    quantity_per_package = kilogram_features.quantity_per_package * product.quantity
                elif product.unit_measure_id == 2:
                    liter_features = self.db.query(LiterFeatureModel).filter(LiterFeatureModel.product_id == product.product_id).first()
                
                    quantity_per_package = liter_features.quantity_per_package * product.quantity
                else:
                    quantity_per_package = product.quantity 
                
                new_shopping_product = ShoppingProductModel(
                    shopping_id=new_shopping.id,
                    product_id=product.product_id,
                    unit_measure_id=product.unit_measure_id,
                    quantity=product.quantity,
                    quantity_per_package=quantity_per_package,
                    added_date=datetime.utcnow(),
                    updated_date=datetime.utcnow()
                )
                self.db.add(new_shopping_product)
                self.db.commit()
                self.db.refresh(new_shopping_product)

            return {"detail": "Shopping stored successfully", "shopping_id": new_shopping.id}
        except Exception as e:
            print("Error:", e)
            raise HTTPException(status_code=500, detail="Error to store shopping")