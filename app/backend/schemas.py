from pydantic import BaseModel, Field, EmailStr, validator
from fastapi import UploadFile, File
from typing import Union, List, Dict, Optional
from datetime import datetime, date
from decimal import Decimal
from fastapi import Form
from typing import List
from typing import Optional
import json

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
    product_discounts: Optional[Dict[int, float]] = {}

class UpdateCustomerProfile(BaseModel):
    social_reason: Optional[str] = None
    activity: Optional[str] = None
    address: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    region_id: Optional[int] = None
    commune_id: Optional[int] = None

class StoreCustomer(BaseModel):
    social_reason: str
    identification_number: str
    activity: str
    address: str
    phone: str
    email: str
    region_id: int
    commune_id: int
    product_discounts: Optional[Dict[int, float]] = {}

class LocationList(BaseModel):
    page: int

class CustomerList(BaseModel):
    page: int
    name: Optional[str] = None
    rut: Optional[str] = None

class CategoryList(BaseModel):
    page: int

class InventoryList(BaseModel):
    page: int

class StoreLocation(BaseModel):
    location: Union[str, None]

class ProductList(BaseModel):
    page: int
    supplier_id: Optional[int] = None
    product_id: Optional[int] = None

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
    product_id: Optional[int] = None  # Opcional, se puede obtener del inventario
    location_id: int
    stock: int
    public_sale_price: int
    private_sale_price: int
    unit_cost: int
    lot_number: str  # Número de lote requerido

class RemoveAdjustmentInput(BaseModel):
    user_id: int
    inventory_id: int
    product_id: Optional[int] = None  # Opcional, se puede obtener del inventario
    stock: int  # Solo cantidad

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
        try:
            # Parse the cart JSON string
            cart_data = json.loads(cart)
            
            # Validate that cart_data is a list
            if not isinstance(cart_data, list):
                raise ValueError("Cart must be a list of items")
            
            # Filter out None values and validate each cart item
            validated_cart = []
            for item in cart_data:
                if item is None:
                    continue  # Skip None items
                
                # Validate required fields for each cart item
                if not isinstance(item, dict):
                    continue  # Skip non-dict items
                
                if 'id' not in item or 'quantity' not in item:
                    continue  # Skip items without required fields
                
                # Ensure id and quantity are valid
                try:
                    item_id = int(item['id'])
                    item_quantity = int(item['quantity'])
                    if item_id <= 0 or item_quantity <= 0:
                        continue  # Skip invalid values
                except (ValueError, TypeError):
                    continue  # Skip items with invalid id or quantity
                
                # Create a valid CartItem with defaults for optional fields
                validated_item = {
                    'id': item_id,
                    'quantity': item_quantity,
                    'lot_numbers': item.get('lot_numbers', ''),
                    'public_sale_price': item.get('public_sale_price', 0),
                    'private_sale_price': item.get('private_sale_price', 0)
                }
                validated_cart.append(validated_item)
            
            # Ensure we have at least one valid cart item
            if not validated_cart:
                raise ValueError("Cart must contain at least one valid item")
            
            return cls(
                rol_id=rol_id,
                customer_rut=customer_rut,
                document_type_id=document_type_id,
                delivery_address=delivery_address,
                subtotal=subtotal,
                tax=tax,
                total=total,
                cart=validated_cart,
                shipping_method_id=shipping_method_id
            )
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON in cart field: {str(e)}")
        except Exception as e:
            raise ValueError(f"Error processing cart data: {str(e)}")

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
    is_compound: int
    compound_product_id: Union[int, None]

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
                    short_description: str = Form(...),
                    is_compound: int = Form(...),
                    compound_product_id: Union[int, None] = Form(None)
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
            short_description=short_description,
            is_compound=is_compound,
            compound_product_id=compound_product_id
        )
    
class ShoppingProductInput(BaseModel):
    category_id: int
    product_id: int
    quantity: float
    quantity_per_package: float
    discount_percentage: float
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
    shopping_number: Optional[str] = None
    products: List[ShoppingProductInput]
    total: float
    email: str
    prepaid_status_id: Optional[int] = None
    second_email: Optional[str] = None
    third_email: Optional[str] = None
    supplier_id: int

    @validator('shopping_number', pre=True)
    def convert_shopping_number(cls, v):
        if v is not None and not isinstance(v, str):
            return str(v)
        return v

class UpdateShopping(BaseModel):
    shopping_number: Optional[str] = None
    products: List[ShoppingProductInput]
    total: float
    email: str
    prepaid_status_id: Optional[int] = None
    second_email: Optional[str] = None
    third_email: Optional[str] = None
    supplier_id: int

    @validator('shopping_number', pre=True)
    def convert_shopping_number(cls, v):
        if v is not None and not isinstance(v, str):
            return str(v)
        return v
    
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
    shopping_id: Optional[int] = None  # Para cálculo automático de unit_cost

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
    payment_card_url: str
    prepaid_discount: Optional[int] = 0

class SalesReportFilter(BaseModel):
    date_from: Optional[str] = None
    date_to: Optional[str] = None

class SupplierCategoryCreate(BaseModel):
    supplier_id: int
    category_id: int

class SupplierCategoryUpdate(BaseModel):
    supplier_id: Optional[int] = None
    category_id: Optional[int] = None

class SupplierCategoryList(BaseModel):
    page: int = 1

class SupplierCategoryResponse(BaseModel):
    id: int
    supplier_id: int
    category_id: int
    added_date: Optional[datetime] = None
    updated_date: Optional[datetime] = None
    
    class Config:
        from_attributes = True