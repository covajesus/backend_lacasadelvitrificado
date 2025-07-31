from pydantic import BaseModel, Field, EmailStr
from fastapi import UploadFile, File
from typing import Union, List, Dict, Optional
from datetime import datetime, date
from decimal import Decimal
from fastapi import Form
from typing import List
from typing import Optional

class UserLogin(BaseModel):
    rol_id: Union[int, None]
    rut: Union[int, None]
    branch_office_id: Union[int, None]
    full_name: Union[str, None]
    email: Union[str, None]
    phone: Union[str, None]
    hashed_password: Union[str, None]

class User(BaseModel):
    rol_id: int
    branch_office_id: Union[int, None]
    rut: str
    full_name: str
    email: str
    password: str
    phone: str

class UpdateUser(BaseModel):
    rol_id: int = None
    rut: str = None
    full_name: str = None
    email: str = None
    phone: str = None

class UpdateCustomer(BaseModel):
    social_reason: str
    identification_number: str
    activity: str
    address: str
    phone: str
    email: str
    region_id: int
    commune_id: int

class StoreCustomer(BaseModel):
    social_reason: str
    identification_number: str
    activity: str
    address: str
    phone: str
    email: str
    region_id: int
    commune_id: int

class LocationList(BaseModel):
    page: int

class CustomerList(BaseModel):
    page: int

class CategoryList(BaseModel):
    page: int

class InventoryList(BaseModel):
    page: int

class StoreLocation(BaseModel):
    location: Union[str, None]

class ProductList(BaseModel):
    page: int

class SaleList(BaseModel):
    page: int
    rol_id: int
    rut: str

class UnitMeasureList(BaseModel):
    page: int

class StoreSupplier(BaseModel):
    identification_number: str
    supplier: str
    address: str

class StoreUnitMeasure(BaseModel):
    unit_measure: str

class StoreCategory(BaseModel):
    category: str
    public_name: str
    color: str

class UpdateCategory(BaseModel):
    category: str
    public_name: str
    color: str

class UpdateSupplier(BaseModel):
    identification_number: str
    supplier: str
    address: str

class AddAdjustmentInput(BaseModel):
    user_id: int
    inventory_id: int
    product_id: int
    location_id: int
    stock: int
    public_sale_price: int
    private_sale_price: int
    unit_cost: int
    minimum_stock: int
    maximum_stock: int

class RemoveAdjustmentInput(BaseModel):
    user_id: int
    inventory_id: int
    product_id: int
    location_id: int
    stock: int
    public_sale_price: int
    private_sale_price: int
    unit_cost: int
    minimum_stock: int
    maximum_stock: int

class CartItem(BaseModel):
    id: int
    quantity: int
    lot_numbers: Optional[str] = ""
    public_sale_price: Optional[int] = 0
    private_sale_price: Optional[int] = 0

class StoreSale(BaseModel):
    rol_id: int
    customer_rut: str
    document_type_id: int
    delivery_address: Optional[str]
    subtotal: float
    tax: float
    total: float
    cart: List[CartItem]
    shipping_method_id: int

    @classmethod
    def as_form(
        cls,
        rol_id: int = Form(...),
        customer_rut: str = Form(...),
        document_type_id: int = Form(...),
        delivery_address: Optional[str] = Form(None),
        subtotal: float = Form(...),
        tax: float = Form(...),
        total: float = Form(...),
        cart: str = Form(...),
        shipping_method_id: int = Form(...)
    ):
        import json
        return cls(
            rol_id=rol_id,
            customer_rut=customer_rut,
            document_type_id=document_type_id,
            delivery_address=delivery_address,
            subtotal=subtotal,
            tax=tax,
            total=total,
            cart=json.loads(cart),
            shipping_method_id=shipping_method_id
        )

class StoreProduct(BaseModel):
    supplier_id: int
    category_id: int
    unit_measure_id: int
    code: str
    product: str
    original_unit_cost: str
    discount_percentage: str
    final_unit_cost: str
    short_description: str
    description: str
    quantity_per_package: Union[str, None]
    quantity_per_pallet: Union[str, None]
    weight_per_pallet: Union[str, None]
    weight_per_unit: Union[str, None]

    @classmethod
    def as_form(cls,
                    supplier_id: int = Form(...),
                    category_id: int = Form(...),
                    unit_measure_id: int = Form(...),
                    code: str = Form(...),
                    product: str = Form(...),
                    original_unit_cost: str = Form(...),
                    discount_percentage: str = Form(...),
                    final_unit_cost: str = Form(...),
                    description: str = Form(...),
                    quantity_per_package: Optional[str] = Form(None),
                    quantity_per_pallet: Optional[str] = Form(None),
                    weight_per_pallet: Optional[str] = Form(None),
                    weight_per_unit: Optional[str] = Form(None),
                    short_description: str = Form(...)
                ):
        return cls(
            supplier_id=supplier_id,
            category_id=category_id,
            unit_measure_id=unit_measure_id,
            code=code,
            product=product,
            original_unit_cost=original_unit_cost,
            discount_percentage=discount_percentage,
            final_unit_cost=final_unit_cost,
            description=description,
            quantity_per_package=quantity_per_package,
            quantity_per_pallet=quantity_per_pallet,
            weight_per_pallet=weight_per_pallet,
            weight_per_unit=weight_per_unit,
            short_description=short_description
        )
    
class ShoppingProductInput(BaseModel):
    category_id: int
    product_id: int
    quantity: int
    quantity_per_package: float
    discount_percentage: int
    original_unit_cost: float
    final_unit_cost: float
    amount: float
    unit_measure_id: int

class ShoppingList(BaseModel):
    page: int

class SendCustomsCompanyInput(BaseModel):
    customs_company_email: str

class StoreCustomsCompanyDocuments(BaseModel):
    maritime_freight: str
    merchandise_insurance: str
    manifest_opening: str
    deconsolidation: str
    land_freight: str
    port_charges: str
    honoraries: str
    physical_assessment_expenses: str
    administrative_expenses: str
    dollar_value: str
    folder_processing: str
    valija_expenses: str

    @classmethod
    def as_form(cls,
                    maritime_freight: str = Form(...),
                    merchandise_insurance: str = Form(...),
                    manifest_opening: str = Form(...),
                    deconsolidation: str = Form(...),
                    land_freight: str = Form(...),
                    port_charges: str = Form(...),
                    honoraries: str = Form(...),
                    physical_assessment_expenses: str = Form(...),
                    administrative_expenses: str = Form(...),
                    dollar_value: str = Form(...),
                    folder_processing: str = Form(...),
                    valija_expenses: str = Form(...)
                ):
        return cls(
            maritime_freight=maritime_freight,
            merchandise_insurance=merchandise_insurance,
            manifest_opening=manifest_opening,
            deconsolidation=deconsolidation,
            land_freight=land_freight,
            port_charges=port_charges,
            honoraries=honoraries,
            physical_assessment_expenses=physical_assessment_expenses,
            administrative_expenses=administrative_expenses,
            dollar_value=dollar_value,
            folder_processing=folder_processing,
            valija_expenses=valija_expenses
        )

class PreInventoryItems(BaseModel):
    product_id: int = Field(..., description="ID del producto")
    stock: int = Field(..., ge=0, description="Cantidad real que ingresa al inventario")

class PreInventoryStocks(BaseModel):
    items: List[PreInventoryItems]

class StorePaymentDocuments(BaseModel):
    wire_transfer_amount: str
    wire_transfer_date: str
    commission: str
    exchange_rate: str
    extra_expenses: Optional[str] = None

    @classmethod
    def as_form(cls,
                    wire_transfer_amount: str = Form(...),
                    wire_transfer_date: str = Form(...),
                    commission: str = Form(...),
                    exchange_rate: str = Form(...),
                    extra_expenses: Optional[str] = Form(None)
                ):
        return cls(
            wire_transfer_amount=wire_transfer_amount,
            wire_transfer_date=wire_transfer_date,
            commission=commission,
            exchange_rate=exchange_rate,
            extra_expenses=extra_expenses
        )
    
class ShoppingCreateInput(BaseModel):
    products: List[ShoppingProductInput]
    total: float
    email: str
    prepaid_status_id: Optional[int] = None
    second_email: Optional[str] = None
    third_email: Optional[str] = None
    supplier_id: int
    
class SupplierList(BaseModel):
    page: int

class StoreInventory(BaseModel):
    user_id: int
    product_id: int
    location_id: int
    stock: int
    unit_cost: int
    public_sale_price: int
    private_sale_price: int
    minimum_stock: int
    maximum_stock: int
    lot_number: str
    arrival_date: date

class UpdateSettings(BaseModel):
    tax_value: int
    identification_number: str
    account_type: str
    account_number: str
    account_name: str
    account_email: str
    bank: str
    delivery_cost: int
    shop_address: str