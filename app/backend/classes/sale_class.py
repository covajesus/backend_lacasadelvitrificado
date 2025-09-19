from app.backend.db.models import SaleModel, CustomerModel, SaleProductModel, ProductModel, InventoryModel, UnitMeasureModel, SupplierModel, CategoryModel, LotItemModel, LotModel, InventoryMovementModel, InventoryLotItemModel, UnitFeatureModel
from datetime import datetime
from sqlalchemy import func

class SaleClass:
    def __init__(self, db):
        self.db = db

    class Product:
        def __init__(self, id, quantity):
            self.id = id
            self.quantity = quantity

    class ProductInput:
        def __init__(self, product):
            self.cart = [product]

    def check_product_inventory(self, product_id: int, quantity: int):
        product_input = SaleClass.ProductInput(SaleClass.Product(product_id, quantity))
        status, insufficient = SaleClass(self.db).validate_inventory_existence(product_input)
        if status == 1:
            return {"status": "ok", "message": "Stock suficiente"}
        else:
            return {"status": "error", "message": f"Stock insuficiente para: {insufficient}"}

    def get_all(self, rol_id = None, rut = None, page=0, items_per_page=10):
        customer = self.db.query(CustomerModel).filter(CustomerModel.identification_number == rut).first()
        
        try:
            if rol_id == 1 or rol_id == 2:
                query = (
                    self.db.query(
                        SaleModel.id,
                        SaleModel.subtotal,
                        SaleModel.tax,
                        SaleModel.total,
                        SaleModel.status_id,
                        SaleModel.added_date,                
                    )
                    .order_by(SaleModel.added_date.desc())
                )
            else:
                query = (
                    self.db.query(
                        SaleModel.id,
                        SaleModel.subtotal,
                        SaleModel.tax,
                        SaleModel.total,
                        SaleModel.status_id,
                        SaleModel.added_date,                
                    )
                    .filter(SaleModel.customer_id == customer.id if customer else None)
                    .order_by(SaleModel.added_date.desc())
                )

            if page > 0:
                total_items = query.count()
                total_pages = (total_items + items_per_page - 1)

                if page < 1 or page > total_pages:
                    return {"status": "error", "message": "Invalid page number"}

                data = query.offset((page - 1) * items_per_page).limit(items_per_page).all()

                if not data:
                    return {"status": "error", "message": "No data found"}

                serialized_data = [{
                    "id": sale.id,
                    "subtotal": sale.subtotal,
                    "tax": sale.tax,
                    "total": sale.total,
                    "status_id": sale.status_id,
                    "added_date": sale.added_date.strftime("%Y-%m-%d %H:%M:%S")
                } for sale in data]

                return {
                    "total_items": total_items,
                    "total_pages": total_pages,
                    "current_page": page,
                    "items_per_page": items_per_page,
                    "data": serialized_data
                }

            else:
                data = query.all()

                serialized_data = [{  
                    "id": sale.id,
                    "subtotal": sale.subtotal,
                    "tax": sale.tax,
                    "total": sale.total,
                    "status_id": sale.status_id,
                    "added_date": sale.added_date.strftime("%Y-%m-%d %H:%M:%S")
                } for sale in data]

                return serialized_data

        except Exception as e:
            error_message = str(e)
            return {"status": "error", "message": error_message}

    def validate_inventory_existence(self, sale_inputs):
        insufficient_products = []

        for item in sale_inputs.cart:
            query = (
                self.db.query(
                    func.sum(LotItemModel.quantity).label("total_stock"),
                    InventoryModel.minimum_stock,
                    ProductModel.product.label("product_name")
                )
                .select_from(ProductModel)
                .join(UnitMeasureModel, UnitMeasureModel.id == ProductModel.unit_measure_id, isouter=True)
                .join(SupplierModel, SupplierModel.id == ProductModel.supplier_id, isouter=True)
                .join(CategoryModel, CategoryModel.id == ProductModel.category_id, isouter=True)
                .join(LotItemModel, LotItemModel.product_id == ProductModel.id)
                .join(LotModel, LotModel.id == LotItemModel.lot_id)
                .join(InventoryModel, InventoryModel.product_id == ProductModel.id)
                .filter(ProductModel.id == item.id)
                .group_by(ProductModel.id, InventoryModel.minimum_stock, ProductModel.product)
            )
            print("[SQL QUERY]", str(query.statement.compile(compile_kwargs={"literal_binds": True})))
            result = query.first()

            if result:
                total_stock, minimum_stock, product_name = result
                if (total_stock - item.quantity) < minimum_stock:
                    insufficient_products.append(product_name)
            else:
                # Producto no encontrado o sin stock
                product = self.db.query(ProductModel.product).filter(ProductModel.id == item.id).scalar()
                insufficient_products.append(product or f"Producto {item.id}")

        if insufficient_products:
            return 0, insufficient_products  # Hay productos con stock insuficiente

        return 1, []  # Todo OK

    def store_inventory_movement(self, sale_id, sale_inputs):
        for item in sale_inputs.cart:
            print(item.lot_numbers)
            lot_ids = item.lot_numbers.split(',')
            quantity_to_deduct = item.quantity  # Total por descontar

            for lot_id in lot_ids:
                print(2323232323)
                print(lot_id)
                lot_id = lot_id.strip()
                if not lot_id or quantity_to_deduct <= 0:
                    continue

                # Obtener el lote individual por número de lote y producto
                print(55555555555555888)
                lot_item, lot = (
                    self.db.query(LotItemModel, LotModel)
                    .join(LotModel, LotModel.id == LotItemModel.lot_id)
                    .filter(LotModel.lot_number == lot_id)
                    .filter(LotItemModel.product_id == item.id)
                    .first()
                )

                print(f"[+] Processing lot {lot_id} for product {item.id}")

                if not lot_item or lot_item.quantity <= 0:
                    continue

                print(8888)

                deduct_qty = min(quantity_to_deduct, lot_item.quantity)

                # Obtener inventario relacionado
                inventory = (
                    self.db.query(InventoryModel)
                    .join(LotModel, LotModel.id == lot.id)
                    .filter(InventoryModel.product_id == item.id)
                    .first()
                )

                if not inventory:
                    continue

                # Descontar cantidad del lote
                lot_item.quantity = lot_item.quantity - deduct_qty
                lot_item.updated_date = datetime.now()
                self.db.commit()

                # Descontar cantidad del inventario_lote
                inventory_lot = self.db.query(InventoryLotItemModel).filter(
                    InventoryLotItemModel.lot_item_id == lot_item.id
                ).first()
                
                if not inventory_lot:
                    print(f"[!] No se encontró inventario_lote para inventory_id={inventory.id}, lot_item_id={lot_item.id}")

                if inventory_lot:
                    inventory_lot.quantity -= deduct_qty
                    inventory_lot.updated_date = datetime.now()
                    self.db.commit()

              

                # Registrar movimiento
                inventory_movement = InventoryMovementModel(
                    inventory_id=inventory.id,
                    lot_item_id=lot_item.id,
                    movement_type_id=2,
                    quantity=(deduct_qty * -1),
                    unit_cost=lot_item.unit_cost,
                    public_sale_price=lot_item.public_sale_price,
                    private_sale_price=lot_item.private_sale_price,
                    reason="Venta",
                    added_date=datetime.now()
                )
                self.db.add(inventory_movement)
                self.db.commit()

                if sale_inputs.rol_id == 1 or sale_inputs.rol_id == 2:
                    price = item.private_sale_price
                else:
                    price = item.public_sale_price

                sale_product = SaleProductModel(
                    sale_id=sale_id,
                    product_id=item.id,
                    inventory_movement_id=inventory_movement.id,
                    inventory_id=inventory.id,
                    lot_item_id=lot_item.id,
                    quantity=item.quantity,
                    price=price
                )

  

                print(f"[+] Deducted {deduct_qty} from lot {lot_id} for product {item.id}")

                self.db.add(sale_product)
                self.db.commit()

                quantity_to_deduct -= deduct_qty

                if quantity_to_deduct <= 0:
                    break

    def store(self, sale_inputs, photo_path):
        try:
            status, failed_products = self.validate_inventory_existence(sale_inputs)

            if status == 0:
                return {
                    "status": "error",
                    "message": f"Stock insuficiente para los productos: {', '.join(failed_products)}"
                }

            if sale_inputs.rol_id == 1 or sale_inputs.rol_id == 2:
                customer_id = 1
                status_id = 4
            else:
                customer_data = self.db.query(CustomerModel).filter(CustomerModel.identification_number == sale_inputs.customer_rut).first()
                if not customer_data:
                    customer_id = 0
                customer_id = customer_data.id
                status_id = 1

            new_sale = SaleModel(
                customer_id=customer_id,
                shipping_method_id=sale_inputs.shipping_method_id,
                dte_type_id=sale_inputs.document_type_id,
                status_id=status_id,
                subtotal=sale_inputs.subtotal,
                tax=sale_inputs.tax,
                total=sale_inputs.total,
                payment_support=photo_path,
                delivery_address=sale_inputs.delivery_address,
                added_date=datetime.now()
            )
            self.db.add(new_sale)
            self.db.flush()
            self.db.commit()
            self.db.refresh(new_sale)

            self.store_inventory_movement(new_sale.id, sale_inputs)

            return {"status": "Venta registrada exitosamente.", "sale_id": new_sale.id}

        except Exception as e:
            self.db.rollback()
            raise e

    def reverse(self, sale_id):
        sales_products = self.db.query(SaleProductModel).filter(SaleProductModel.sale_id == sale_id).all()

        try:
            for sales_product in sales_products:
                inventory_movement = self.db.query(InventoryMovementModel).filter(
                    InventoryMovementModel.id == sales_product.inventory_movement_id
                ).first()

                inventory_lot_item = self.db.query(InventoryLotItemModel).filter(InventoryLotItemModel.inventory_id == sales_product.inventory_id).filter(InventoryLotItemModel.lot_item_id == inventory_movement.lot_item_id).first()
                new_quantity = inventory_lot_item.quantity + (inventory_movement.quantity * -1)
                inventory_lot_item.quantity = new_quantity
                inventory_lot_item.updated_date = datetime.now()
                self.db.commit()

                lot_items = self.db.query(LotItemModel).filter(LotItemModel.id == sales_product.lot_item_id).first()
                lot_items.quantity = int(lot_items.quantity) + int(sales_product.quantity)
                lot_items.updated_date = datetime.now()
                self.db.commit()

                self.db.delete(inventory_movement)
                self.db.commit()

            return "Inventory reject successfully"
        except Exception as e:
            self.db.rollback()
            return "Error trying to reject inventory"
        
    def get(self, id):
        try:
            data_query = self.db.query(
                SaleModel.id,
                SaleModel.subtotal,
                SaleModel.tax,
                SaleModel.total,
                SaleModel.status_id,
                SaleModel.dte_type_id,
                SaleModel.shipping_method_id,
                SaleModel.payment_support,
                SaleModel.delivery_address,
                SaleModel.added_date,
                CustomerModel.social_reason
            ).join(CustomerModel, CustomerModel.id == SaleModel.customer_id, isouter=True).filter(SaleModel.id == id).first()

            if data_query:
                sale_data = {
                    "id": data_query.id,
                    "subtotal": data_query.subtotal,
                    "tax": data_query.tax,
                    "total": data_query.total,
                    "status_id": data_query.status_id,
                    "dte_type_id": data_query.dte_type_id,
                    "shipping_method_id": data_query.shipping_method_id,
                    "payment_support": data_query.payment_support,
                    "delivery_address": data_query.delivery_address,
                    "added_date": data_query.added_date.strftime("%d-%m-%Y %H:%M:%S"),
                    "social_reason": data_query.social_reason
                }

                return {"sale_data": sale_data}

            else:
                return {"error": "No se encontraron datos para el campo especificado."}
            
        except Exception as e:
            return {"error": str(e)}
        
    
    def details(self, id):
        try:
            data_query = self.db.query(
                SaleProductModel.id,
                SaleProductModel.quantity,
                SaleModel.subtotal,
                SaleModel.tax,
                SaleModel.total,
                SaleModel.status_id,
                SaleModel.dte_type_id,
                SaleModel.shipping_method_id,
                SaleModel.payment_support,
                SaleModel.delivery_address,
                SaleModel.added_date,
                ProductModel.product
            ).join(SaleModel, SaleModel.id == SaleProductModel.sale_id, isouter=True).join(ProductModel, ProductModel.id == SaleProductModel.product_id, isouter=True).filter(SaleModel.id == id).all()

            if not data_query:
                return {"error": "No se encontraron datos para el campo especificado."}
            
            sale_data = []

            for data in data_query:
                sale_details = {
                    "id": data.id,
                    "quantity": data.quantity,
                    "subtotal": data.subtotal,
                    "tax": data.tax,
                    "total": data.total,
                    "status_id": data.status_id,
                    "dte_type_id": data.dte_type_id,
                    "shipping_method_id": data.shipping_method_id,
                    "payment_support": data.payment_support,
                    "delivery_address": data.delivery_address,
                    "added_date": data.added_date.strftime("%d-%m-%Y %H:%M:%S"),
                    "product": data.product
                }

                sale_data.append(sale_details)

            return {"sale_data": sale_data}
            
        except Exception as e:
            return {"error": str(e)}
        

    def change_status(self, id, status_id):
        existing_sale = self.db.query(SaleModel).filter(SaleModel.id == id).one_or_none()

        if not existing_sale:
            return "No data found"

        try:
            existing_sale.status_id = status_id
            existing_sale.updated_date = datetime.utcnow()

            self.db.commit()
            self.db.refresh(existing_sale)
            return "Sale updated successfully"
        except Exception as e:
            self.db.rollback()
            error_message = str(e)
            return {"status": "error", "message": error_message}

    def get_sales_report(self, start_date=None, end_date=None):
        try:
            from datetime import datetime
            
            # Consulta para obtener ventas individuales con información de lotes
            individual_sales_query = (
                self.db.query(
                    ProductModel.id.label("product_id"),
                    ProductModel.product.label("product_name"),
                    ProductModel.code.label("product_code"),
                    ProductModel.unit_measure_id,
                    UnitMeasureModel.unit_measure,
                    UnitFeatureModel.quantity_per_package,
                    SaleProductModel.quantity,
                    SaleProductModel.price.label("sale_price"),
                    LotItemModel.public_sale_price,
                    LotItemModel.private_sale_price,
                    InventoryMovementModel.unit_cost,
                    LotItemModel.id.label("lot_item_id"),
                    LotModel.lot_number,
                    LotModel.arrival_date,
                    SaleModel.added_date
                )
                .join(SaleProductModel, SaleProductModel.product_id == ProductModel.id)
                .join(SaleModel, SaleModel.id == SaleProductModel.sale_id)
                .join(InventoryMovementModel, InventoryMovementModel.id == SaleProductModel.inventory_movement_id)
                .join(LotItemModel, LotItemModel.id == SaleProductModel.lot_item_id)
                .join(LotModel, LotModel.id == LotItemModel.lot_id)
                .join(UnitMeasureModel, UnitMeasureModel.id == ProductModel.unit_measure_id, isouter=True)
                .join(UnitFeatureModel, UnitFeatureModel.product_id == ProductModel.id, isouter=True)
            )
            
            # Aplicar filtros de fecha si se proporcionan
            if start_date and start_date.strip():
                try:
                    start_datetime = datetime.strptime(start_date, "%Y-%m-%d")
                    individual_sales_query = individual_sales_query.filter(SaleModel.added_date >= start_datetime)
                except ValueError:
                    return {"status": "error", "message": "Formato de fecha inválido para start_date. Use YYYY-MM-DD"}
            
            if end_date and end_date.strip():
                try:
                    end_datetime = datetime.strptime(end_date, "%Y-%m-%d")
                    end_datetime = end_datetime.replace(hour=23, minute=59, second=59)
                    individual_sales_query = individual_sales_query.filter(SaleModel.added_date <= end_datetime)
                except ValueError:
                    return {"status": "error", "message": "Formato de fecha inválido para end_date. Use YYYY-MM-DD"}
            
            individual_sales = individual_sales_query.all()
            
            # Incluir información de filtro en el mensaje de respuesta
            filter_info = ""
            if start_date and end_date:
                filter_info = f" (período: {start_date} a {end_date})"
            elif start_date:
                filter_info = f" (desde: {start_date})"
            elif end_date:
                filter_info = f" (hasta: {end_date})"
            
            if not individual_sales:
                return {
                    "status": "success",
                    "message": f"No se encontraron ventas{filter_info}",
                    "period": {"start_date": start_date, "end_date": end_date},
                    "data": []
                }
            
            # Agrupar por producto y lote
            products_data = {}
            
            for sale in individual_sales:
                product_id = sale.product_id
                lot_item_id = sale.lot_item_id
                
                if product_id not in products_data:
                    # Calcular la cantidad total representada en la unidad de medida
                    quantity_per_package = float(sale.quantity_per_package) if sale.quantity_per_package else 1.0
                    unit_measure_name = sale.unit_measure if sale.unit_measure else "unidades"
                    
                    # Calcular precios por unidad de medida (no por paquete)
                    # Los precios en BD están por paquete, los convertimos a por unidad de medida
                    public_price_per_unit = float(sale.public_sale_price) / quantity_per_package if sale.public_sale_price and quantity_per_package > 0 else 0
                    private_price_per_unit = float(sale.private_sale_price) / quantity_per_package if sale.private_sale_price and quantity_per_package > 0 else 0
                    
                    products_data[product_id] = {
                        "product_id": product_id,
                        "product_name": sale.product_name,
                        "product_code": sale.product_code,
                        "unit_measure": unit_measure_name,
                        "quantity_per_package": quantity_per_package,
                        "total_quantity": 0,
                        "total_unit_measure_quantity": 0,  # Nueva: cantidad total en unidad de medida
                        "public_sales": {"quantity": 0, "revenue": 0, "count": 0, "unit_measure_quantity": 0},
                        "private_sales": {"quantity": 0, "revenue": 0, "count": 0, "unit_measure_quantity": 0},
                        "total_revenue": 0,
                        "total_cost": 0,
                        "lots_breakdown": {},  # Nuevo: desglose por lotes
                        "prices": {
                            "public_price_per_package": float(sale.public_sale_price) if sale.public_sale_price else 0,
                            "private_price_per_package": float(sale.private_sale_price) if sale.private_sale_price else 0,
                            "public_price_per_unit": public_price_per_unit,
                            "private_price_per_unit": private_price_per_unit,
                            "average_unit_cost_per_unit": 0
                        }
                    }
                
                # Inicializar datos del lote si no existe
                if lot_item_id not in products_data[product_id]["lots_breakdown"]:
                    quantity_per_package = products_data[product_id]["quantity_per_package"]
                    # El unit_cost en BD está por UNIDAD (litro), lo convertimos a por paquete
                    cost_per_unit = float(sale.unit_cost)  # Costo por unidad (litro)
                    cost_per_package = cost_per_unit * quantity_per_package  # Costo por paquete
                    
                    products_data[product_id]["lots_breakdown"][lot_item_id] = {
                        "lot_number": sale.lot_number,
                        "arrival_date": sale.arrival_date.strftime("%Y-%m-%d") if sale.arrival_date else None,
                        "cost_per_package": cost_per_package,
                        "cost_per_unit": cost_per_unit,
                        "quantity_sold": 0,
                        "unit_measure_quantity_sold": 0,  # Nueva: cantidad en unidad de medida
                        "revenue": 0,
                        "cost": 0,
                        "public_sales": {"quantity": 0, "revenue": 0, "unit_measure_quantity": 0},
                        "private_sales": {"quantity": 0, "revenue": 0, "unit_measure_quantity": 0}
                    }
                
                # Calcular valores
                quantity = sale.quantity
                quantity_per_package = products_data[product_id]["quantity_per_package"]
                unit_measure_quantity = quantity * quantity_per_package  # Cantidad en unidad de medida
                
                # IMPORTANTE: El unit_cost en BD está por UNIDAD (litro), lo convertimos a por paquete
                cost_per_unit = sale.unit_cost  # Costo por unidad (litro)
                cost_per_package = cost_per_unit * quantity_per_package  # Costo por paquete
                
                # Los precios de venta están por paquete, los convertimos a por unidad de medida
                unit_measure_sale_price = sale.sale_price / quantity_per_package if quantity_per_package > 0 else sale.sale_price
                
                # Calcular revenue y cost basado en la cantidad real en unidad de medida
                revenue = unit_measure_quantity * unit_measure_sale_price  # Revenue por cantidad real
                cost = unit_measure_quantity * cost_per_unit         # Cost por cantidad real
                
                # Actualizar totales del producto
                products_data[product_id]["total_quantity"] += quantity
                products_data[product_id]["total_unit_measure_quantity"] += unit_measure_quantity
                products_data[product_id]["total_revenue"] += revenue
                products_data[product_id]["total_cost"] += cost
                
                # Actualizar datos del lote específico
                lot_data = products_data[product_id]["lots_breakdown"][lot_item_id]
                lot_data["quantity_sold"] += quantity
                lot_data["unit_measure_quantity_sold"] += unit_measure_quantity
                lot_data["revenue"] += revenue
                lot_data["cost"] += cost
                
                # Determinar tipo de precio
                if sale.sale_price == sale.public_sale_price:
                    price_type = 'public'
                elif sale.sale_price == sale.private_sale_price:
                    price_type = 'private'
                else:
                    price_type = 'private'  # Por defecto
                
                # Clasificar por tipo de precio (producto)
                if price_type == 'public':
                    products_data[product_id]["public_sales"]["quantity"] += quantity
                    products_data[product_id]["public_sales"]["unit_measure_quantity"] += unit_measure_quantity
                    products_data[product_id]["public_sales"]["revenue"] += revenue
                    products_data[product_id]["public_sales"]["count"] += 1
                    # También para el lote
                    lot_data["public_sales"]["quantity"] += quantity
                    lot_data["public_sales"]["unit_measure_quantity"] += unit_measure_quantity
                    lot_data["public_sales"]["revenue"] += revenue
                else:  # private o otros
                    products_data[product_id]["private_sales"]["quantity"] += quantity
                    products_data[product_id]["private_sales"]["unit_measure_quantity"] += unit_measure_quantity
                    products_data[product_id]["private_sales"]["revenue"] += revenue
                    products_data[product_id]["private_sales"]["count"] += 1
                    # También para el lote
                    lot_data["private_sales"]["quantity"] += quantity
                    lot_data["private_sales"]["unit_measure_quantity"] += unit_measure_quantity
                    lot_data["private_sales"]["revenue"] += revenue
            
            # Formatear datos para respuesta
            formatted_data = []
            total_revenue = 0
            total_cost = 0
            total_profit = 0
            
            for product_data in products_data.values():
                # Calcular costo unitario promedio POR UNIDAD DE MEDIDA
                avg_unit_cost_per_unit = product_data["total_cost"] / product_data["total_unit_measure_quantity"] if product_data["total_unit_measure_quantity"] > 0 else 0
                product_data["prices"]["average_unit_cost_per_unit"] = round(avg_unit_cost_per_unit, 2)
                
                # Calcular ganancias
                actual_profit = product_data["total_revenue"] - product_data["total_cost"]
                
                # Calcular porcentajes de ventas por tipo
                total_qty = product_data["total_quantity"]
                public_percent = (product_data["public_sales"]["quantity"] / total_qty * 100) if total_qty > 0 else 0
                private_percent = (product_data["private_sales"]["quantity"] / total_qty * 100) if total_qty > 0 else 0
                
                # Formatear desglose por lotes
                lots_breakdown_formatted = []
                for lot_item_id, lot_data in product_data["lots_breakdown"].items():
                    lot_profit = lot_data["revenue"] - lot_data["cost"]
                    lot_margin = (lot_profit / lot_data["revenue"] * 100) if lot_data["revenue"] > 0 else 0
                    
                    lots_breakdown_formatted.append({
                        "lot_number": lot_data["lot_number"],
                        "arrival_date": lot_data["arrival_date"],
                        "cost_per_package": round(lot_data["cost_per_package"], 2),
                        "cost_per_unit": round(lot_data["cost_per_unit"], 2),
                        "quantity_sold": lot_data["quantity_sold"],
                        "unit_measure_quantity_sold": round(lot_data["unit_measure_quantity_sold"], 2),
                        "unit_measure": product_data["unit_measure"],
                        "revenue": round(lot_data["revenue"], 2),
                        "cost": round(lot_data["cost"], 2),
                        "profit": round(lot_profit, 2),
                        "profit_margin_percent": round(lot_margin, 2),
                        "sales_by_type": {
                            "public_sales": {
                                "quantity": lot_data["public_sales"]["quantity"],
                                "unit_measure_quantity": round(lot_data["public_sales"]["unit_measure_quantity"], 2),
                                "revenue": round(lot_data["public_sales"]["revenue"], 2)
                            },
                            "private_sales": {
                                "quantity": lot_data["private_sales"]["quantity"],
                                "unit_measure_quantity": round(lot_data["private_sales"]["unit_measure_quantity"], 2),
                                "revenue": round(lot_data["private_sales"]["revenue"], 2)
                            }
                        }
                    })
                
                # Ordenar lotes por fecha de llegada
                lots_breakdown_formatted.sort(key=lambda x: x["arrival_date"] or "1900-01-01")
                
                product_summary = {
                    "product_id": product_data["product_id"],
                    "product_name": product_data["product_name"],
                    "product_code": product_data["product_code"],
                    "unit_measure": product_data["unit_measure"],
                    "quantity_per_package": product_data["quantity_per_package"],
                    "quantity_sold": product_data["total_quantity"],
                    "unit_measure_quantity_sold": round(product_data["total_unit_measure_quantity"], 2),
                    "prices": product_data["prices"],
                    "sales_breakdown": {
                        "public_sales": {
                            "quantity": product_data["public_sales"]["quantity"],
                            "unit_measure_quantity": round(product_data["public_sales"]["unit_measure_quantity"], 2),
                            "percentage": round(public_percent, 1),
                            "revenue": round(product_data["public_sales"]["revenue"], 2),
                            "transactions": product_data["public_sales"]["count"]
                        },
                        "private_sales": {
                            "quantity": product_data["private_sales"]["quantity"],
                            "unit_measure_quantity": round(product_data["private_sales"]["unit_measure_quantity"], 2),
                            "percentage": round(private_percent, 1),
                            "revenue": round(product_data["private_sales"]["revenue"], 2),
                            "transactions": product_data["private_sales"]["count"]
                        }
                    },
                    "lots_breakdown": lots_breakdown_formatted,  # Nuevo: desglose por lotes
                    "totals": {
                        "total_revenue": round(product_data["total_revenue"], 2),
                        "total_cost": round(product_data["total_cost"], 2),
                        "total_profit": round(actual_profit, 2),
                        "profit_margin_percent": round((actual_profit / product_data["total_revenue"] * 100), 2) if product_data["total_revenue"] > 0 else 0
                    }
                }
                
                formatted_data.append(product_summary)
                
                # Sumar totales generales
                total_revenue += product_data["total_revenue"]
                total_cost += product_data["total_cost"]
                total_profit += actual_profit
            
            # Ordenar por cantidad vendida
            formatted_data.sort(key=lambda x: x["quantity_sold"], reverse=True)
            
            # Resumen general
            summary = {
                "total_products": len(formatted_data),
                "total_revenue": round(total_revenue, 2),
                "total_cost": round(total_cost, 2),
                "total_profit": round(total_profit, 2),
                "overall_margin_percent": round((total_profit / total_revenue * 100), 2) if total_revenue > 0 else 0
            }
            
            return {
                "status": "success",
                "message": f"Reporte generado para {len(formatted_data)} productos",
                "period": {"start_date": start_date, "end_date": end_date},
                "summary": summary,
                "data": formatted_data
            }
            
        except Exception as e:
            return {"status": "error", "message": f"Error al generar reporte: {str(e)}"}