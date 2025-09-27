from app.backend.db.database import Base
from sqlalchemy import Column, Integer, String, DateTime, Date, ForeignKey, Float, Boolean, Text, Numeric
from datetime import datetime

class AccountTypeModel(Base):
    __tablename__ = 'account_types'

    id = Column(Integer, primary_key=True)
    account_type = Column(String(255))
    added_date = Column(DateTime())
    updated_date = Column(DateTime())

class SettingModel(Base):
    __tablename__ = 'settings'

    id = Column(Integer, primary_key=True)
    tax_value = Column(String(255))
    identification_number = Column(String(255))
    account_type = Column(String(255))
    account_number = Column(String(255))
    account_name = Column(String(255))
    account_email = Column(String(255))
    bank = Column(String(255))
    delivery_cost = Column(Integer)
    simplefactura_token = Column(Text())
    shop_address = Column(String(255))
    payment_card_url = Column(String(255))
    prepaid_discount = Column(Integer)
    updated_date = Column(DateTime())

class ShoppingModel(Base):
    __tablename__ = 'shoppings'

    id = Column(Integer, primary_key=True)
    shopping_number = Column(String(100))
    supplier_id = Column(Integer)
    status_id = Column(Integer)
    email = Column(String(255))
    total = Column(Numeric(10, 2)) 
    maritime_freight = Column(Numeric(10, 2))
    merchandise_insurance = Column(Numeric(10, 2))
    manifest_opening = Column(Numeric(10, 2))
    deconsolidation = Column(Numeric(10, 2))
    land_freight = Column(Numeric(10, 2))
    port_charges = Column(Numeric(10, 2))
    honoraries = Column(Numeric(10, 2))
    physical_assessment_expenses = Column(Numeric(10, 2))
    administrative_expenses = Column(Numeric(10, 2))
    dollar_value = Column(Numeric(10, 2))
    folder_processing = Column(Numeric(10, 2))
    valija_expenses = Column(Numeric(10, 2))
    customs_company_support = Column(Text())
    wire_transfer_amount = Column(Numeric(10, 2))
    wire_transfer_date = Column(Date)
    commission = Column(Numeric(10, 2))
    exchange_rate = Column(Integer)
    extra_expenses = Column(Numeric(10, 2))
    payment_support = Column(Text())
    added_date = Column(DateTime())
    updated_date = Column(DateTime())

    # Nuevos campos agregados sin modificar los anteriores
    prepaid_status_id = Column(Integer)

class ShoppingProductModel(Base):
    __tablename__ = 'shoppings_products'

    id = Column(Integer, primary_key=True)
    shopping_id = Column(Integer)
    product_id = Column(Integer)
    unit_measure_id = Column(Integer)
    quantity = Column(Integer)
    quantity_per_package = Column(Numeric(10, 2))
    original_unit_cost = Column(Numeric(10, 2))
    discount_percentage = Column(Integer)
    final_unit_cost = Column(Numeric(10, 2))
    amount = Column(Numeric(10, 2))
    added_date = Column(DateTime())
    updated_date = Column(DateTime())

class SupplierModel(Base):
    __tablename__ = 'suppliers'

    id = Column(Integer, primary_key=True)
    identification_number = Column(String(255))
    supplier = Column(String(255))
    address = Column(Text())
    added_date = Column(DateTime())
    updated_date = Column(DateTime())

class UnitMeasureModel(Base):
    __tablename__ = 'unit_measures'

    id = Column(Integer, primary_key=True)
    unit_measure = Column(String(255))
    added_date = Column(DateTime())
    updated_date = Column(DateTime())

class SaleModel(Base):
    __tablename__ = 'sales'

    id = Column(Integer, primary_key=True)
    customer_id = Column(Integer)
    shipping_method_id = Column(Integer)
    dte_type_id = Column(Integer)
    status_id = Column(Integer)
    folio = Column(Integer, default=0)
    subtotal = Column(Float)
    tax = Column(Float)
    shipping_cost = Column(Float, default=0)
    total = Column(Float)
    payment_support = Column(Text())
    delivery_address = Column(Text())
    added_date = Column(DateTime(), default=datetime.now)
    updated_date = Column(DateTime(), default=datetime.now)

class SaleProductModel(Base):
    __tablename__ = 'sales_products'

    id = Column(Integer, primary_key=True)
    sale_id = Column(Integer)
    product_id = Column(Integer)
    inventory_movement_id = Column(Integer)
    inventory_id = Column(Integer)
    lot_item_id = Column(Integer)
    quantity = Column(Integer)
    price = Column(Integer)

class CustomerModel(Base):
    __tablename__ = 'customers'

    id = Column(Integer, primary_key=True)
    region_id = Column(Integer)
    commune_id = Column(Integer)
    identification_number = Column(String(255))
    social_reason = Column(String(255))
    activity = Column(String(255))
    address = Column(String(255))
    phone = Column(String(255))
    email = Column(String(255))
    added_date = Column(DateTime())
    updated_date = Column(DateTime())

class LocationModel(Base):
    __tablename__ = 'locations'

    id = Column(Integer, primary_key=True)
    location = Column(String(255))
    added_date = Column(DateTime())
    updated_date = Column(DateTime())

class CategoryModel(Base):
    __tablename__ = 'categories'

    id = Column(Integer, primary_key=True)
    category = Column(String(255))
    public_name = Column(String(255))
    color = Column(String(255))
    added_date = Column(DateTime())
    updated_date = Column(DateTime())

class LiterFeatureModel(Base):
    __tablename__ = 'liter_features'

    id = Column(Integer, primary_key=True)
    product_id = Column(Integer)
    quantity_per_package = Column(Integer)
    quantity_per_pallet = Column(Integer)
    weight_per_liter = Column(String(255))
    weight_per_pallet = Column(String(255))
    added_date = Column(DateTime())
    updated_date = Column(DateTime())

class PreInventoryStockModel(Base):
    __tablename__ = 'pre_inventory_stocks'

    id = Column(Integer, primary_key=True)
    product_id = Column(Integer)
    shopping_id = Column(Integer)
    lot_number = Column(Integer)
    stock = Column(Integer)
    added_date = Column(DateTime())
    updated_date = Column(DateTime())

class UnitFeatureModel(Base):
    __tablename__ = 'unit_features'

    id = Column(Integer, primary_key=True)
    product_id = Column(Integer)
    quantity_per_package = Column(Integer)
    quantity_per_pallet = Column(Integer)
    weight_per_unit = Column(String(255))
    weight_per_pallet = Column(String(255))
    added_date = Column(DateTime())
    updated_date = Column(DateTime())

class RegionModel(Base):
    __tablename__ = 'regions'

    id = Column(Integer, primary_key=True)
    region = Column(String(255))    
    region_remuneration_code = Column(Integer) 
    added_date = Column(DateTime())
    updated_date = Column(DateTime())

class ProductModel(Base):
    __tablename__ = 'products'

    id = Column(Integer, primary_key=True)
    supplier_id = Column(Integer)
    category_id = Column(Integer)
    unit_measure_id = Column(Integer)
    code = Column(String(255))
    product = Column(String(255))
    original_unit_cost = Column(Text())
    discount_percentage = Column(Text())
    final_unit_cost = Column(Text())
    short_description = Column(Text())
    description = Column(Text())
    photo = Column(Text())
    catalog = Column(Text())
    is_compound = Column(Integer)
    compound_product_id = Column(Integer)
    added_date = Column(DateTime())
    updated_date = Column(DateTime())

class UserModel(Base):
    __tablename__ = 'users'

    id = Column(Integer, primary_key=True)
    rol_id = Column(Integer, ForeignKey('rols.id'))
    rut = Column(String(255))
    full_name = Column(String(255))
    email = Column(String(255))
    phone = Column(Text())
    hashed_password = Column(Text())
    added_date = Column(DateTime())
    updated_date = Column(DateTime())

class RolModel(Base):
    __tablename__ = 'rols'

    id = Column(Integer, primary_key=True)
    rol = Column(String(255))
    added_date = Column(DateTime())
    updated_date = Column(DateTime())

class CommuneModel(Base):
    __tablename__ = 'communes'

    id = Column(Integer, primary_key=True)
    region_id = Column(Integer)
    commune = Column(String(255))
    added_date = Column(DateTime())
    updated_date = Column(DateTime())

class CustomerProductDiscountModel(Base):
    __tablename__ = 'customers_products_discounts'

    id = Column(Integer, primary_key=True)
    customer_id = Column(Integer)
    product_id = Column(Integer)
    discount_percentage = Column(Integer)

class InventoryModel(Base):
    __tablename__ = 'inventories'  # Cambia el nombre si es otro

    id = Column(Integer, primary_key=True, autoincrement=True)
    product_id = Column(Integer)
    location_id = Column(Integer)
    minimum_stock = Column(Integer)
    maximum_stock = Column(Integer)
    last_update = Column(DateTime())
    added_date = Column(DateTime())

class LotModel(Base):
    __tablename__ = 'lots'

    id = Column(Integer, primary_key=True, autoincrement=True)
    supplier_id = Column(Integer)
    lot_number = Column(String(255))
    arrival_date = Column(Date())
    added_date = Column(DateTime())
    updated_date = Column(DateTime())

class LotItemModel(Base):
    __tablename__ = 'lot_items'

    id = Column(Integer, primary_key=True, autoincrement=True)
    lot_id = Column(Integer)
    product_id = Column(Integer)
    quantity = Column(Integer)
    unit_cost = Column(Integer)
    public_sale_price = Column(Integer)
    private_sale_price = Column(Integer)
    added_date = Column(DateTime())
    updated_date = Column(DateTime())

class InventoryLotItemModel(Base):
    __tablename__ = 'inventories_lots'

    id = Column(Integer, primary_key=True, autoincrement=True)
    inventory_id = Column(Integer, ForeignKey('inventories.id'))
    lot_item_id = Column(Integer, ForeignKey('lots.id'))
    quantity = Column(Integer)
    added_date = Column(DateTime())
    updated_date = Column(DateTime())

class MovementTypeModel(Base):
    __tablename__ = 'movement_types'

    id = Column(Integer, primary_key=True, autoincrement=True)
    movement_type = Column(String(255))
    added_date = Column(DateTime())
    updated_date = Column(DateTime())

class InventoryMovementModel(Base):
    __tablename__ = 'inventories_movements'

    id = Column(Integer, primary_key=True, autoincrement=True)
    inventory_id = Column(Integer, ForeignKey('inventories.id'))
    lot_item_id = Column(Integer, ForeignKey('lot_items.id'))
    movement_type_id = Column(Integer, ForeignKey('movement_types.id'))
    quantity = Column(Integer)
    unit_cost = Column(Integer)
    reason = Column(Text())
    added_date = Column(DateTime())
    
class InventoryAuditModel(Base):
    __tablename__ = 'inventories_audits'

    id = Column(Integer, primary_key=True, autoincrement=True) 
    user_id = Column(Integer, ForeignKey('users.id'))
    inventory_id = Column(Integer, ForeignKey('inventories.id'))
    previous_stock = Column(Integer)
    new_stock = Column(Integer)
    reason = Column(Text())
    added_date = Column(DateTime(), default=datetime.now)

class SupplierCategoryModel(Base):
    __tablename__ = 'suppliers_categories'

    id = Column(Integer, primary_key=True, autoincrement=True)
    supplier_id = Column(Integer, ForeignKey('suppliers.id'))
    category_id = Column(Integer, ForeignKey('categories.id'))
    added_date = Column(DateTime(), default=datetime.now)
    updated_date = Column(DateTime())

class KardexValuesModel(Base):
    __tablename__ = 'kardex_values'

    id = Column(Integer, primary_key=True, autoincrement=True)
    product_id = Column(Integer, ForeignKey('products.id'))
    quantity = Column(Integer, default=0)
    average_cost = Column(Integer, default=0)
    added_date = Column(DateTime(), default=datetime.now)
    updated_date = Column(DateTime(), default=datetime.now)