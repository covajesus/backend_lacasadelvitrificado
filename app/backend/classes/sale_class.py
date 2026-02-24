from app.backend.db.models import SaleModel, CustomerModel, SaleProductModel, ProductModel, InventoryModel, UnitMeasureModel, SupplierModel, CategoryModel, LotItemModel, LotModel, InventoryMovementModel, InventoryLotItemModel, UnitFeatureModel, KardexValuesModel, SettingModel, UserModel, BudgetModel, BudgetProductModel
from datetime import datetime
from sqlalchemy import func
from app.backend.classes.whatsapp_class import WhatsappClass

class Product:
    def __init__(self, id, quantity):
        self.id = id
        self.quantity = quantity

class ProductInput:
    def __init__(self, product):
        self.cart = [product]


class SaleClass:
    def __init__(self, db):
        self.db = db

    def check_product_inventory(self, product_id: int, quantity: int):
        product_input = ProductInput(Product(product_id, quantity))
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
                        SaleModel.shipping_cost,
                        SaleModel.total,
                        SaleModel.status_id,
                        SaleModel.added_date,
                        CustomerModel.social_reason.label("customer_name"),
                    )
                    .join(CustomerModel, CustomerModel.id == SaleModel.customer_id, isouter=True)
                    .order_by(SaleModel.added_date.desc())
                )
            else:
                query = (
                    self.db.query(
                        SaleModel.id,
                        SaleModel.subtotal,
                        SaleModel.shipping_cost,
                        SaleModel.tax,
                        SaleModel.total,
                        SaleModel.status_id,
                        SaleModel.added_date,
                        CustomerModel.social_reason.label("customer_name"),
                    )
                    .join(CustomerModel, CustomerModel.id == SaleModel.customer_id, isouter=True)
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
                    "shipping_cost": sale.shipping_cost,
                    "tax": sale.tax,
                    "total": sale.total,
                    "status_id": sale.status_id,
                    "added_date": sale.added_date.strftime("%Y-%m-%d %H:%M:%S"),
                    "customer_name": sale.customer_name
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
                    "shipping_cost": sale.shipping_cost,
                    "tax": sale.tax,
                    "total": sale.total,
                    "status_id": sale.status_id,
                    "added_date": sale.added_date.strftime("%Y-%m-%d %H:%M:%S"),
                    "customer_name": sale.customer_name
                } for sale in data]

                return serialized_data

        except Exception as e:
            error_message = str(e)
            return {"status": "error", "message": error_message}

    def validate_inventory_existence(self, sale_inputs):
        insufficient_products = []

        for item in sale_inputs.cart:
            # Calcular stock total disponible para este producto
            total_stock_query = (
                self.db.query(func.sum(LotItemModel.quantity).label("total_stock"))
                .join(LotModel, LotModel.id == LotItemModel.lot_id)
                .filter(LotItemModel.product_id == item.id)
                .filter(LotItemModel.quantity > 0)
            )
            
            total_stock = total_stock_query.scalar() or 0
            
            # Obtener información del producto y stock mínimo
            product_info = (
                self.db.query(
                    ProductModel.product.label("product_name"),
                    InventoryModel.minimum_stock
                )
                .join(InventoryModel, InventoryModel.product_id == ProductModel.id)
                .filter(ProductModel.id == item.id)
                .first()
            )
            
            if not product_info:
                insufficient_products.append(f"Producto {item.id} no encontrado")
                continue
            
            product_name, minimum_stock = product_info
            
            # Verificar si hay suficiente stock
            if total_stock < item.quantity:
                insufficient_products.append(f"{product_name} (disponible: {total_stock}, solicitado: {item.quantity})")
                continue
            
            # Verificar si después de la venta quedaría por debajo del stock mínimo
            remaining_stock = total_stock - item.quantity
            if remaining_stock < minimum_stock:
                insufficient_products.append(f"{product_name} (quedaría {remaining_stock}, mínimo requerido: {minimum_stock})")
                continue
            
            print(f"[+] Stock validation passed for {product_name}: {total_stock} available, {item.quantity} requested")

        if insufficient_products:
            return 0, insufficient_products  # Hay productos con stock insuficiente

        return 1, []  # Todo OK

    def update_kardex_for_sale(self, product_id, sold_quantity, unit_cost):
        """
        Actualiza el kardex cuando se vende un producto.
        Resta la cantidad vendida del kardex.
        """
        try:
            # Buscar el registro de kardex existente para este producto
            kardex_record = (
                self.db.query(KardexValuesModel)
                .filter(KardexValuesModel.product_id == product_id)
                .first()
            )
            
            if kardex_record:
                # Restar la cantidad vendida
                new_quantity = kardex_record.quantity - sold_quantity
                
                # Asegurar que la cantidad no sea negativa
                if new_quantity < 0:
                    new_quantity = 0
                
                # Actualizar el registro
                kardex_record.quantity = new_quantity
                kardex_record.updated_date = datetime.now()
                
                print(f"[+] Kardex actualizado por venta para producto {product_id}:")
                print(f"    - Cantidad anterior: {kardex_record.quantity + sold_quantity}")
                print(f"    - Cantidad vendida: {sold_quantity}")
                print(f"    - Nueva cantidad: {new_quantity}")
                print(f"    - Costo promedio se mantiene: {kardex_record.average_cost}")
                
                self.db.commit()
            else:
                print(f"[!] No se encontró registro de kardex para producto {product_id}")
            
        except Exception as e:
            print(f"[!] Error actualizando kardex por venta para producto {product_id}: {str(e)}")

    def get_shipping_cost(self):
        """Obtiene el costo de envío desde la tabla settings"""
        try:
            setting = self.db.query(SettingModel).first()
            if setting and setting.delivery_cost:
                return float(setting.delivery_cost)
            return 0.0
        except Exception as e:
            print(f"[!] Error obteniendo shipping_cost desde settings: {str(e)}")
            return 0.0

    def calculate_kardex_based_total(self, cart_items):
        """Calcula el subtotal de la venta basado en los costos del kardex para roles 1 y 2"""
        try:
            subtotal = 0
            
            for item in cart_items:
                # Obtener costo del kardex para este producto
                kardex_record = (
                    self.db.query(KardexValuesModel)
                    .filter(KardexValuesModel.product_id == item.id)
                    .first()
                )
                
                if kardex_record:
                    # Usar costo promedio del kardex
                    unit_cost = kardex_record.average_cost
                else:
                    # Si no hay kardex, usar precio público como fallback
                    unit_cost = item.public_sale_price
                
                # Calcular subtotal para este producto
                item_subtotal = item.quantity * unit_cost
                subtotal += item_subtotal
                
                print(f"[+] Producto {item.id}: {item.quantity} x {unit_cost} = {item_subtotal}")
            
            # Calcular impuestos solo sobre el subtotal (sin shipping)
            tax_rate = 0.19
            tax = subtotal * tax_rate
            total = subtotal + tax
            
            print(f"[+] Subtotal kardex: {subtotal}, Tax: {tax}, Total: {total}")
            
            return subtotal, tax, total
            
        except Exception as e:
            print(f"[!] Error calculando total basado en kardex: {str(e)}")
            # En caso de error, devolver valores por defecto
            return 0, 0, 0

    def store(self, sale_inputs, photo_path = None):
        try:
            # Validate cart items before processing
            if not hasattr(sale_inputs, 'cart') or not sale_inputs.cart:
                return {
                    "status": "error",
                    "message": "Cart is empty or invalid"
                }
            
            # Filter out any None or invalid cart items
            valid_cart_items = []
            for item in sale_inputs.cart:
                if item is None:
                    continue
                if not hasattr(item, 'id') or not hasattr(item, 'quantity'):
                    continue
                if item.id is None or item.quantity is None:
                    continue
                if item.id <= 0 or item.quantity <= 0:
                    continue
                valid_cart_items.append(item)
            
            if not valid_cart_items:
                return {
                    "status": "error",
                    "message": "No valid items in cart"
                }
            
            # Update the cart with only valid items
            sale_inputs.cart = valid_cart_items
            
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

            # Obtener shipping_cost desde settings
            shipping_cost = self.get_shipping_cost()
            
            # Si shipping_method_id == 1, shipping_cost = 0
            if sale_inputs.shipping_method_id == 1:
                shipping_cost = 0
            else:
                # Solo obtener shipping_cost si shipping_method_id == 2
                shipping_cost = self.get_shipping_cost()
            
            # Calcular total basado en costos del kardex si el rol es 1 o 2
            if sale_inputs.rol_id == 1 or sale_inputs.rol_id == 2:
                subtotal, tax, total = self.calculate_kardex_based_total(sale_inputs.cart)
            else:
                subtotal = sale_inputs.subtotal
                tax = sale_inputs.tax
                total = sale_inputs.total
            
            # Recalcular tax sobre (subtotal + shipping_cost) solo si shipping_method_id == 2
            if sale_inputs.shipping_method_id == 2 and shipping_cost > 0:
                tax_rate = 0.19  # 19% de impuesto
                tax = (subtotal + shipping_cost) * tax_rate
                total = subtotal + shipping_cost + tax
            else:
                # Si shipping_method_id == 1, calcular IVA solo sobre subtotal
                if sale_inputs.shipping_method_id == 1:
                    tax_rate = 0.19  # 19% de impuesto
                    tax = subtotal * tax_rate
                    total = subtotal + tax
                else:
                    # Mantener el cálculo original para otros casos
                    total = subtotal + tax
  
            new_sale = SaleModel(
                customer_id=customer_id,
                shipping_method_id=sale_inputs.shipping_method_id,
                dte_type_id=sale_inputs.document_type_id,
                status_id=status_id,
                subtotal=subtotal,
                tax=tax,
                shipping_cost=shipping_cost,
                total=total,
                payment_support=photo_path,
                delivery_address=sale_inputs.delivery_address,
                added_date=datetime.now()
            )
            self.db.add(new_sale)
            self.db.flush()
            self.db.commit()
            self.db.refresh(new_sale)

            # Guardar productos del carrito sin procesar inventario (solo para referencia)
            # El procesamiento de inventario se hará al aceptar el pago
            for item in sale_inputs.cart:
                # Determinar precio según el rol
                if sale_inputs.rol_id == 1 or sale_inputs.rol_id == 2:
                    # Para roles 1 y 2, obtener costo del kardex
                    kardex_record = (
                        self.db.query(KardexValuesModel)
                        .filter(KardexValuesModel.product_id == item.id)
                        .first()
                    )
                    price = kardex_record.average_cost if kardex_record else 0
                else:
                    if sale_inputs.rol_id == 2:
                        price = item.private_sale_price
                    else:
                        price = item.public_sale_price
                
                # Crear registro de producto vendido sin procesar inventario aún
                sale_product = SaleProductModel(
                    sale_id=new_sale.id,
                    product_id=item.id,
                    inventory_movement_id=None,  # Se asignará al aceptar el pago
                    inventory_id=None,  # Se asignará al aceptar el pago
                    lot_item_id=None,  # Se asignará al aceptar el pago
                    quantity=item.quantity,
                    price=price
                )
                self.db.add(sale_product)
            
            self.db.commit()

            # Enviar alerta de nueva orden por WhatsApp
            try:
                # Obtener datos del cliente
                customer = self.db.query(CustomerModel).filter(CustomerModel.id == customer_id).first()
                if customer:
                    customer_name = customer.social_reason or f"Cliente {customer.identification_number}"
                else:
                    customer_name = f"Cliente {sale_inputs.customer_rut}"
                
                # Formatear fecha
                date_formatted = new_sale.added_date.strftime("%d-%m-%Y")
                
                # Enviar alerta
                whatsapp = WhatsappClass(self.db)
                whatsapp.send_new_order_alert(
                    customer_name=customer_name
                )
                print(f"[WHATSAPP ALERT] Alerta enviada para nueva orden {new_sale.id}")
            except Exception as e:
                print(f"[WHATSAPP ALERT] Error enviando alerta: {str(e)}")

            return {"status": "Venta registrada exitosamente.", "sale_id": new_sale.id}

        except Exception as e:
            self.db.rollback()
            raise e

    def reverse(self, sale_id):
        sales_products = self.db.query(SaleProductModel).filter(SaleProductModel.sale_id == sale_id).all()

        try:
            for sales_product in sales_products:
                # Obtener el movimiento de inventario original
                inventory_movement = self.db.query(InventoryMovementModel).filter(
                    InventoryMovementModel.id == sales_product.inventory_movement_id
                ).first()

                if inventory_movement:
                    # Crear movimiento inverso (si quantity es negativo, crear uno positivo igual)
                    # Si quantity es -10, reverse_quantity será 10 (suma para revertir)
                    reverse_quantity = abs(inventory_movement.quantity) if inventory_movement.quantity < 0 else -inventory_movement.quantity
                    
                    # Crear nuevo movimiento de inventario inverso
                    reverse_movement = InventoryMovementModel(
                        inventory_id=inventory_movement.inventory_id,
                        lot_item_id=inventory_movement.lot_item_id,
                        movement_type_id=1,  # Tipo entrada
                        quantity=reverse_quantity,
                        unit_cost=inventory_movement.unit_cost,
                        reason="Reversa de venta",
                        added_date=datetime.now()
                    )
                    self.db.add(reverse_movement)
                    self.db.commit()

                    print(f"[REVERSE] Movimiento reverso creado para producto {sales_product.product_id}: {reverse_quantity}")

            return "Inventory reversed successfully"
        except Exception as e:
            self.db.rollback()
            print(f"[REVERSE] Error: {str(e)}")
            return f"Error trying to reverse inventory: {str(e)}"
        
    def get(self, id):
        try:
            data_query = self.db.query(
                SaleModel.id,
                SaleModel.subtotal,
                SaleModel.tax,
                SaleModel.shipping_cost,
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
                    "shipping_cost": data_query.shipping_cost,
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
                SaleModel.shipping_cost,
                SaleModel.tax,
                SaleModel.total,
                SaleModel.status_id,
                SaleModel.dte_type_id,
                SaleModel.shipping_method_id,
                SaleModel.payment_support,
                SaleModel.delivery_address,
                SaleModel.added_date,
                ProductModel.product,
                CustomerModel.social_reason.label("customer_name")
            ).join(SaleModel, SaleModel.id == SaleProductModel.sale_id, isouter=True).join(ProductModel, ProductModel.id == SaleProductModel.product_id, isouter=True).join(CustomerModel, CustomerModel.id == SaleModel.customer_id, isouter=True).filter(SaleModel.id == id).all()

            if not data_query:
                return {"error": "No se encontraron datos para el campo especificado."}
            
            sale_data = []

            for data in data_query:
                sale_details = {
                    "id": data.id,
                    "quantity": data.quantity,
                    "subtotal": data.subtotal,
                    "tax": data.tax,
                    "shipping_cost": data.shipping_cost,
                    "total": data.total,
                    "status_id": data.status_id,
                    "dte_type_id": data.dte_type_id,
                    "shipping_method_id": data.shipping_method_id,
                    "payment_support": data.payment_support,
                    "delivery_address": data.delivery_address,
                    "added_date": data.added_date.strftime("%d-%m-%Y %H:%M:%S"),
                    "product": data.product,
                    "customer_name": data.customer_name
                }

                sale_data.append(sale_details)

            return {"sale_data": sale_data}
            
        except Exception as e:
            return {"error": str(e)}
        

    def change_status(self, id, status_id):
        try:
            # Bloquear la venta para evitar procesamiento concurrente
            existing_sale = (
                self.db.query(SaleModel)
                .filter(SaleModel.id == id)
                .with_for_update(nowait=True)
                .one_or_none()
            )
        except Exception as lock_error:
            # Si falla el bloqueo, la venta está siendo procesada por otro proceso
            error_msg = str(lock_error).lower()
            if "lock" in error_msg or "wait" in error_msg or "timeout" in error_msg:
                raise Exception("La venta está siendo procesada por otro proceso. Por favor, intente nuevamente en unos segundos.")
            # Re-lanzar el error si no es de bloqueo
            raise

        if not existing_sale:
            return "No data found"

        # Verificar si la venta ya está en el estado deseado
        if existing_sale.status_id == status_id:
            return "Sale already in this status"

        try:
            # Si se acepta el pago (status_id = 2), procesar productos
            if status_id == 2:
                # Primero verificar TODOS los productos de la venta para debugging
                all_sale_products = (
                    self.db.query(SaleProductModel)
                    .filter(SaleProductModel.sale_id == id)
                    .all()
                )
                print(f"[CHANGE_STATUS] Venta ID: {id}, Total de productos en la venta: {len(all_sale_products)}")
                for sp in all_sale_products:
                    print(f"[CHANGE_STATUS] Producto ID: {sp.product_id}, Cantidad: {sp.quantity}, inventory_movement_id: {sp.inventory_movement_id}")
                
                # Ahora verificar si hay productos de la venta que aún no se han procesado
                sale_products_unprocessed = (
                    self.db.query(SaleProductModel)
                    .filter(SaleProductModel.sale_id == id)
                    .filter(SaleProductModel.inventory_movement_id.is_(None))
                    .all()
                )

                print(f"[CHANGE_STATUS] Venta ID: {id}, Productos sin procesar encontrados: {len(sale_products_unprocessed)}")
                for sp in sale_products_unprocessed:
                    print(f"[CHANGE_STATUS] Producto sin procesar - ID: {sp.product_id}, Cantidad: {sp.quantity}, inventory_movement_id: {sp.inventory_movement_id}")

                # Si hay productos sin procesar, validar stock ANTES de procesar
                if sale_products_unprocessed:
                    # Validar que todos los productos tengan stock disponible antes de procesar
                    for sale_product in sale_products_unprocessed:
                        product_id = sale_product.product_id
                        quantity = sale_product.quantity
                        
                        if quantity <= 0:
                            continue
                        
                        # Calcular stock total disponible para este producto
                        total_stock_query = (
                            self.db.query(func.sum(LotItemModel.quantity).label("total_stock"))
                            .join(LotModel, LotModel.id == LotItemModel.lot_id)
                            .filter(LotItemModel.product_id == product_id)
                            .filter(LotItemModel.quantity > 0)
                        )
                        
                        total_stock = total_stock_query.scalar() or 0
                        
                        if total_stock < quantity:
                            error_msg = f"Stock insuficiente para el producto ID {product_id}. Disponible: {total_stock}, Solicitado: {quantity}"
                            print(f"[CHANGE_STATUS] ERROR: {error_msg}")
                            return {"status": "error", "message": error_msg}
                        
                        # Verificar que exista inventario para el producto
                        inventory = (
                            self.db.query(InventoryModel)
                            .filter(InventoryModel.product_id == product_id)
                            .first()
                        )
                        
                        if not inventory:
                            error_msg = f"No se encontró inventario para el producto ID {product_id}"
                            print(f"[CHANGE_STATUS] ERROR: {error_msg}")
                            return {"status": "error", "message": error_msg}
                    
                    # Si todas las validaciones pasan, procesar productos
                    print(f"[CHANGE_STATUS] Procesando {len(sale_products_unprocessed)} productos sin procesar")
                    for sale_product in sale_products_unprocessed:
                        product_id = sale_product.product_id
                        quantity = sale_product.quantity
                        product_price = sale_product.price  # Guardar precio antes de eliminar
                        
                        if quantity <= 0:
                            continue

                        quantity_to_process = quantity
                        total_processed = 0

                        # Buscar lotes disponibles para este producto (FIFO)
                        available_lots = (
                            self.db.query(LotItemModel, LotModel)
                            .join(LotModel, LotModel.id == LotItemModel.lot_id)
                            .filter(LotItemModel.product_id == product_id)
                            .filter(LotItemModel.quantity > 0)
                            .order_by(LotModel.arrival_date.asc())  # FIFO - First In, First Out
                            .all()
                        )

                        if not available_lots:
                            error_msg = f"No hay lotes disponibles para el producto ID {product_id}"
                            print(f"[CHANGE_STATUS] ERROR: {error_msg}")
                            return {"status": "error", "message": error_msg}

                        # Eliminar el sale_product original ya que crearemos uno por cada lote
                        self.db.delete(sale_product)
                        self.db.flush()

                        # Procesar lotes disponibles
                        for lot_item, lot in available_lots:
                            if quantity_to_process <= 0:
                                break

                            # Calcular cantidad a procesar de este lote
                            process_qty = min(quantity_to_process, lot_item.quantity)

                            if process_qty <= 0:
                                continue

                            # Obtener inventario relacionado
                            inventory = (
                                self.db.query(InventoryModel)
                                .filter(InventoryModel.product_id == product_id)
                                .first()
                            )

                            if not inventory:
                                error_msg = f"No se encontró inventario para el producto ID {product_id}"
                                print(f"[CHANGE_STATUS] ERROR: {error_msg}")
                                return {"status": "error", "message": error_msg}

                            # Obtener unit_cost del kardex para el movimiento (si existe)
                            kardex_record = (
                                self.db.query(KardexValuesModel)
                                .filter(KardexValuesModel.product_id == product_id)
                                .first()
                            )

                            movement_unit_cost = kardex_record.average_cost if kardex_record else lot_item.unit_cost

                            # Registrar movimiento de inventario (tipo 2 - Venta)
                            inventory_movement = InventoryMovementModel(
                                inventory_id=inventory.id,
                                lot_item_id=lot_item.id,
                                movement_type_id=2,  # Tipo de movimiento: Venta
                                quantity=(process_qty * -1),  # Cantidad negativa para venta
                                unit_cost=movement_unit_cost,  # Usa costo del kardex si existe
                                reason="Venta",
                                added_date=datetime.utcnow()
                            )
                            self.db.add(inventory_movement)
                            self.db.flush()
                            print(f"[CHANGE_STATUS] Movimiento de inventario creado: inventory_id={inventory.id}, quantity={process_qty * -1}, lot_item_id={lot_item.id}")

                            # Crear registro de producto vendido (uno por cada lote)
                            new_sale_product = SaleProductModel(
                                sale_id=existing_sale.id,
                                product_id=product_id,
                                inventory_movement_id=inventory_movement.id,
                                inventory_id=inventory.id,
                                lot_item_id=lot_item.id,
                                quantity=process_qty,
                                price=product_price
                            )
                            self.db.add(new_sale_product)
                            self.db.flush()

                            # Actualizar cantidad del lote (rebajar stock)
                            lot_item.quantity = max(0, lot_item.quantity - process_qty)
                            lot_item.updated_date = datetime.utcnow()
                            self.db.flush()

                            # Actualizar inventory_lot si existe
                            inventory_lot = (
                                self.db.query(InventoryLotItemModel)
                                .filter(InventoryLotItemModel.lot_item_id == lot_item.id)
                                .filter(InventoryLotItemModel.inventory_id == inventory.id)
                                .first()
                            )
                            
                            if inventory_lot:
                                inventory_lot.quantity = max(0, inventory_lot.quantity - process_qty)
                                inventory_lot.updated_date = datetime.utcnow()
                                self.db.flush()

                            # Actualizar contadores
                            quantity_to_process -= process_qty
                            total_processed += process_qty

                            if quantity_to_process <= 0:
                                break

                        # Actualizar kardex con la cantidad total vendida de este producto
                        if total_processed > 0:
                            self.update_kardex_for_sale(
                                product_id=product_id,
                                sold_quantity=total_processed,
                                unit_cost=0  # No necesitamos el unit_cost para ventas
                            )

                # Si no hay productos sin procesar, buscar presupuesto aceptado del mismo cliente
                if not sale_products_unprocessed:
                    budget = (
                        self.db.query(BudgetModel)
                        .filter(BudgetModel.customer_id == existing_sale.customer_id)
                        .filter(BudgetModel.status_id == 1)
                        .filter(BudgetModel.total == existing_sale.total)
                        .order_by(BudgetModel.updated_date.desc())
                        .first()
                    )

                    if budget:
                        # Obtener productos del presupuesto
                        products = (
                            self.db.query(BudgetProductModel)
                            .filter(BudgetProductModel.budget_id == budget.id)
                            .all()
                        )

                        if products:
                            # Validar stock disponible para todos los productos
                            for product in products:
                                quantity = product.quantity if product.quantity else 0
                                if quantity <= 0:
                                    continue

                                product_id = product.product_id
                                
                                # Calcular stock total disponible para este producto
                                total_stock_query = (
                                    self.db.query(func.sum(LotItemModel.quantity).label("total_stock"))
                                    .join(LotModel, LotModel.id == LotItemModel.lot_id)
                                    .filter(LotItemModel.product_id == product_id)
                                    .filter(LotItemModel.quantity > 0)
                                )
                                
                                total_stock = total_stock_query.scalar() or 0
                                
                                # Verificar si hay suficiente stock
                                if total_stock < quantity:
                                    return {"status": "error", "message": "Uno de los productos solicitados no tiene la cantidad disponible"}

                            # Procesar productos
                            for product in products:
                                quantity = product.quantity if product.quantity else 0
                                if quantity <= 0:
                                    continue

                                product_id = product.product_id
                                quantity_to_process = quantity
                                total_processed = 0

                                # Buscar lotes disponibles para este producto (FIFO)
                                available_lots = (
                                    self.db.query(LotItemModel, LotModel)
                                    .join(LotModel, LotModel.id == LotItemModel.lot_id)
                                    .filter(LotItemModel.product_id == product_id)
                                    .filter(LotItemModel.quantity > 0)
                                    .order_by(LotModel.arrival_date.asc())  # FIFO - First In, First Out
                                    .all()
                                )

                                if not available_lots:
                                    error_msg = f"No hay lotes disponibles para el producto ID {product_id}"
                                    print(f"[CHANGE_STATUS] ERROR: {error_msg}")
                                    return {"status": "error", "message": error_msg}

                                # Procesar lotes disponibles
                                for lot_item, lot in available_lots:
                                    if quantity_to_process <= 0:
                                        break

                                    # Calcular cantidad a procesar de este lote
                                    process_qty = min(quantity_to_process, lot_item.quantity)

                                    if process_qty <= 0:
                                        continue

                                    # Obtener inventario relacionado
                                    inventory = (
                                        self.db.query(InventoryModel)
                                        .filter(InventoryModel.product_id == product_id)
                                        .first()
                                    )

                                    if not inventory:
                                        error_msg = f"No se encontró inventario para el producto ID {product_id}"
                                        print(f"[CHANGE_STATUS] ERROR: {error_msg}")
                                        return {"status": "error", "message": error_msg}

                                    # Obtener unit_cost del kardex para el movimiento (si existe)
                                    kardex_record = (
                                        self.db.query(KardexValuesModel)
                                        .filter(KardexValuesModel.product_id == product_id)
                                        .first()
                                    )

                                    movement_unit_cost = kardex_record.average_cost if kardex_record else lot_item.unit_cost

                                    # Registrar movimiento de inventario (tipo 2 - Venta)
                                    inventory_movement = InventoryMovementModel(
                                        inventory_id=inventory.id,
                                        lot_item_id=lot_item.id,
                                        movement_type_id=2,  # Tipo de movimiento: Venta
                                        quantity=(process_qty * -1),  # Cantidad negativa para venta
                                        unit_cost=movement_unit_cost,  # Usa costo del kardex si existe
                                        reason="Venta desde presupuesto",
                                        added_date=datetime.utcnow()
                                    )
                                    self.db.add(inventory_movement)
                                    self.db.flush()

                                    # Calcular precio unitario
                                    unit_price = product.total // quantity if quantity > 0 else product.total
                                    if quantity > 0 and product.total % quantity != 0:
                                        unit_price = int(round(product.total / quantity))

                                    # Crear registro de producto vendido (sales_products)
                                    sale_product = SaleProductModel(
                                        sale_id=existing_sale.id,
                                        product_id=product_id,
                                        inventory_movement_id=inventory_movement.id,
                                        inventory_id=inventory.id,
                                        lot_item_id=lot_item.id,
                                        quantity=process_qty,  # Cantidad procesada de este lote
                                        price=unit_price
                                    )

                                    self.db.add(sale_product)
                                    self.db.flush()

                                    # Actualizar cantidad del lote (rebajar stock)
                                    lot_item.quantity = max(0, lot_item.quantity - process_qty)
                                    lot_item.updated_date = datetime.utcnow()
                                    self.db.flush()

                                    # Actualizar inventory_lot si existe
                                    inventory_lot = (
                                        self.db.query(InventoryLotItemModel)
                                        .filter(InventoryLotItemModel.lot_item_id == lot_item.id)
                                        .filter(InventoryLotItemModel.inventory_id == inventory.id)
                                        .first()
                                    )
                                    
                                    if inventory_lot:
                                        inventory_lot.quantity = max(0, inventory_lot.quantity - process_qty)
                                        inventory_lot.updated_date = datetime.utcnow()
                                        self.db.flush()

                                    # Actualizar contadores
                                    quantity_to_process -= process_qty
                                    total_processed += process_qty

                                    if quantity_to_process <= 0:
                                        break

                                # Actualizar kardex con la cantidad total vendida de este producto
                                if total_processed > 0:
                                    # Obtener registro de kardex
                                    kardex_record = (
                                        self.db.query(KardexValuesModel)
                                        .filter(KardexValuesModel.product_id == product_id)
                                        .first()
                                    )

                                    if kardex_record:
                                        # Reducir cantidad en kardex
                                        new_quantity = max(0, kardex_record.quantity - total_processed)
                                        kardex_record.quantity = new_quantity
                                        # No actualizar average_cost, solo la cantidad
                                        kardex_record.updated_date = datetime.utcnow()
                                        self.db.flush()

            existing_sale.status_id = status_id
            existing_sale.updated_date = datetime.utcnow()

            self.db.commit()
            self.db.refresh(existing_sale)
            print(f"[CHANGE_STATUS] Venta {id} actualizada exitosamente. Status cambiado a {status_id}")
            return "Sale updated successfully"
        except Exception as e:
            self.db.rollback()
            error_message = str(e)
            # Si es un error de bloqueo, lanzar excepción para que el router lo maneje
            if "could not obtain lock" in error_message.lower() or "lock" in error_message.lower() or "deadlock" in error_message.lower():
                raise Exception(f"La venta está siendo procesada por otro proceso. Error: {error_message}")
            return {"status": "error", "message": error_message}

    def get_sales_report(self, start_date=None, end_date=None):
        try:
            from datetime import datetime, date
            
            # Si no se proporcionan fechas, usar el mes actual por defecto
            if not start_date or not start_date.strip():
                today = date.today()
                start_date = today.replace(day=1).strftime("%Y-%m-%d")  # Primer día del mes actual
            
            if not end_date or not end_date.strip():
                today = date.today()
                end_date = today.strftime("%Y-%m-%d")  # Último día del mes actual (hoy)
            
            # Consulta para obtener ventas individuales con información de lotes y rol del usuario
            # Usar COALESCE para obtener unit_cost del movimiento, kardex o lot_item como fallback
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
                    func.coalesce(
                        InventoryMovementModel.unit_cost,
                        KardexValuesModel.average_cost,
                        LotItemModel.unit_cost,
                        0
                    ).label("unit_cost"),
                    LotItemModel.id.label("lot_item_id"),
                    LotModel.lot_number,
                    LotModel.arrival_date,
                    SaleModel.added_date,
                    UserModel.rol_id.label("user_rol_id")
                )
                .join(SaleProductModel, SaleProductModel.product_id == ProductModel.id)
                .join(SaleModel, SaleModel.id == SaleProductModel.sale_id)
                .join(InventoryMovementModel, InventoryMovementModel.id == SaleProductModel.inventory_movement_id, isouter=True)
                .join(LotItemModel, LotItemModel.id == SaleProductModel.lot_item_id, isouter=True)
                .join(LotModel, LotModel.id == LotItemModel.lot_id, isouter=True)
                .join(UnitMeasureModel, UnitMeasureModel.id == ProductModel.unit_measure_id, isouter=True)
                .join(UnitFeatureModel, UnitFeatureModel.product_id == ProductModel.id, isouter=True)
                .join(CustomerModel, CustomerModel.id == SaleModel.customer_id, isouter=True)
                .join(UserModel, UserModel.rut == CustomerModel.identification_number, isouter=True)
                .join(KardexValuesModel, KardexValuesModel.product_id == ProductModel.id, isouter=True)
                .filter(SaleModel.status_id.in_([2, 4]))  # Incluir ventas aceptadas (2) y entregadas (4)
            )
            
            # Aplicar filtros de fecha
            try:
                start_datetime = datetime.strptime(start_date, "%Y-%m-%d")
                individual_sales_query = individual_sales_query.filter(SaleModel.added_date >= start_datetime)
            except ValueError:
                return {"status": "error", "message": "Formato de fecha inválido para start_date. Use YYYY-MM-DD"}
            
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
                        "prices": {
                            "public_price_per_package": float(sale.public_sale_price) if sale.public_sale_price else 0,
                            "private_price_per_package": float(sale.private_sale_price) if sale.private_sale_price else 0,
                            "public_price_per_unit": public_price_per_unit,
                            "private_price_per_unit": private_price_per_unit,
                            "average_unit_cost_per_unit": 0
                        }
                    }
                
                
                # Calcular valores
                quantity = sale.quantity
                quantity_per_package = products_data[product_id]["quantity_per_package"]
                unit_measure_quantity = quantity * quantity_per_package  # Cantidad en unidad de medida
                
                # IMPORTANTE: El unit_cost en BD está por PAQUETE, lo convertimos a por unidad
                cost_per_package = sale.unit_cost if sale.unit_cost is not None else 0  # Costo por paquete
                cost_per_unit = cost_per_package / quantity_per_package if quantity_per_package > 0 and cost_per_package > 0 else 0  # Costo por unidad
                
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
                
                
                # Determinar tipo de venta basado en el rol_id del usuario
                # rol_id 5 = venta pública, rol_id 1 o 2 = venta privada
                # Si no existe usuario o rol_id es None, por defecto es pública
                if sale.user_rol_id == 5:
                    price_type = 'public'
                elif sale.user_rol_id in [1, 2]:
                    price_type = 'private'
                else:  # rol_id None, 0 u otros = venta pública por defecto
                    price_type = 'public'
                
                # Clasificar por tipo de precio (producto)
                if price_type == 'public':
                    products_data[product_id]["public_sales"]["quantity"] += quantity
                    products_data[product_id]["public_sales"]["unit_measure_quantity"] += unit_measure_quantity
                    products_data[product_id]["public_sales"]["revenue"] += revenue
                    products_data[product_id]["public_sales"]["count"] += 1
                else:  # private o otros
                    products_data[product_id]["private_sales"]["quantity"] += quantity
                    products_data[product_id]["private_sales"]["unit_measure_quantity"] += unit_measure_quantity
                    products_data[product_id]["private_sales"]["revenue"] += revenue
                    products_data[product_id]["private_sales"]["count"] += 1
            
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
    
    def delete(self, sale_id: int):
        try:
            # Buscar la venta
            sale = self.db.query(SaleModel).filter(SaleModel.id == sale_id).first()
            
            if not sale:
                return {"status": "error", "message": "Venta no encontrada"}
            
            # Verificar si la venta tiene un DTE generado (folio)
            if sale.folio:
                return {"status": "error", "message": "No se puede eliminar una venta con DTE generado"}
            
            # Buscar todos los productos de la venta
            sale_products = (
                self.db.query(SaleProductModel)
                .filter(SaleProductModel.sale_id == sale_id)
                .all()
            )
            
            # Eliminar cada producto de la venta
            for sale_product in sale_products:
                self.db.delete(sale_product)
            
            # Eliminar la venta
            self.db.delete(sale)
            
            # Confirmar cambios
            self.db.commit()
            
            return {"status": "success", "message": "Venta eliminada correctamente"}
            
        except Exception as e:
            self.db.rollback()
            return {"status": "error", "message": f"Error al eliminar la venta: {str(e)}"}

    def get_top_customers(self, limit=10):
        """
        Obtiene los clientes que más han comprado, ordenados de mayor a menor.
        
        Args:
            limit: Número de clientes a retornar (default: 10)
        
        Returns:
            Lista de diccionarios con información del cliente y cantidad de compras
        """
        try:
            # Contar ventas por cliente, hacer JOIN con CustomerModel y ordenar por cantidad descendente
            top_customers = (
                self.db.query(
                    CustomerModel.id,
                    CustomerModel.social_reason,
                    CustomerModel.identification_number,
                    CustomerModel.phone,
                    CustomerModel.email,
                    func.count(SaleModel.id).label('total_purchases')
                )
                .join(SaleModel, CustomerModel.id == SaleModel.customer_id)
                .group_by(
                    CustomerModel.id,
                    CustomerModel.social_reason,
                    CustomerModel.identification_number,
                    CustomerModel.phone,
                    CustomerModel.email
                )
                .order_by(func.count(SaleModel.id).desc())
                .limit(limit)
                .all()
            )
            
            # Formatear los resultados
            result = []
            for customer in top_customers:
                result.append({
                    "customer_id": customer.id,
                    "social_reason": customer.social_reason,
                    "identification_number": customer.identification_number,
                    "phone": customer.phone,
                    "email": customer.email,
                    "total_purchases": customer.total_purchases
                })
            
            return result
            
        except Exception as e:
            print(f"[ERROR] Error al obtener top clientes: {str(e)}")
            import traceback
            print(f"[ERROR] Traceback: {traceback.format_exc()}")
            return []

    def get_sales_report(self, desde=None, hasta=None):
        """
        Genera un informe de ventas con:
        - Total vendido por producto (cantidad y monto)
        - Total general (subtotal, tax, total)
        
        Args:
            desde: Fecha de inicio (datetime o string en formato YYYY-MM-DD)
            hasta: Fecha de fin (datetime o string en formato YYYY-MM-DD)
        
        Returns:
            Diccionario con productos, totales y resumen
        """
        try:
            # Construir query base para ventas
            sales_query = self.db.query(SaleModel)
            
            # Aplicar filtros de fecha si se proporcionan
            if desde:
                if isinstance(desde, str):
                    desde = datetime.strptime(desde, "%Y-%m-%d")
                sales_query = sales_query.filter(SaleModel.added_date >= desde)
            
            if hasta:
                if isinstance(hasta, str):
                    hasta = datetime.strptime(hasta, "%Y-%m-%d")
                    # Incluir todo el día hasta las 23:59:59
                    hasta = hasta.replace(hour=23, minute=59, second=59)
                sales_query = sales_query.filter(SaleModel.added_date <= hasta)
            
            # Obtener IDs de ventas filtradas
            sale_ids = [sale.id for sale in sales_query.all()]
            
            if not sale_ids:
                return {
                    "status": "success",
                    "products": [],
                    "totals": {
                        "subtotal": 0,
                        "tax": 0,
                        "total": 0
                    },
                    "summary": {
                        "total_sales": 0,
                        "date_from": desde.strftime("%Y-%m-%d") if desde else None,
                        "date_to": hasta.strftime("%Y-%m-%d") if hasta else None
                    }
                }
            
            # Agrupar productos por producto_id y calcular totales
            products_report = (
                self.db.query(
                    SaleProductModel.product_id,
                    ProductModel.product.label("product_name"),
                    ProductModel.code.label("product_code"),
                    ProductModel.unit_measure_id,
                    UnitMeasureModel.unit_measure.label("unit_measure_name"),
                    func.sum(SaleProductModel.quantity).label("total_quantity"),
                    func.sum(SaleProductModel.quantity * SaleProductModel.price).label("total_amount")
                )
                .join(ProductModel, ProductModel.id == SaleProductModel.product_id)
                .join(UnitMeasureModel, UnitMeasureModel.id == ProductModel.unit_measure_id, isouter=True)
                .filter(SaleProductModel.sale_id.in_(sale_ids))
                .group_by(
                    SaleProductModel.product_id,
                    ProductModel.product,
                    ProductModel.code,
                    ProductModel.unit_measure_id,
                    UnitMeasureModel.unit_measure
                )
                .order_by(func.sum(SaleProductModel.quantity * SaleProductModel.price).desc())
                .all()
            )
            
            # Calcular totales generales de las ventas
            totals_query = (
                self.db.query(
                    func.sum(SaleModel.subtotal).label("total_subtotal"),
                    func.sum(SaleModel.tax).label("total_tax"),
                    func.sum(SaleModel.total).label("total_total")
                )
                .filter(SaleModel.id.in_(sale_ids))
            )
            
            totals_result = totals_query.first()
            
            # Contar total de ventas
            total_sales = len(sale_ids)
            
            # Formatear productos con información de unidad de medida y cantidad por paquete
            products_data = []
            for product in products_report:
                # Obtener quantity_per_package del UnitFeatureModel
                unit_feature = (
                    self.db.query(UnitFeatureModel)
                    .filter(UnitFeatureModel.product_id == product.product_id)
                    .first()
                )
                
                quantity_per_package = 1  # Default si no existe
                if unit_feature and unit_feature.quantity_per_package:
                    quantity_per_package = unit_feature.quantity_per_package
                
                # Calcular cantidad real (paquetes * cantidad por paquete)
                total_quantity_packages = int(product.total_quantity)
                total_quantity_real = total_quantity_packages * quantity_per_package
                
                products_data.append({
                    "product_id": product.product_id,
                    "product_name": product.product_name,
                    "product_code": product.product_code,
                    "unit_measure_id": product.unit_measure_id,
                    "unit_measure_name": product.unit_measure_name or "N/A",
                    "quantity_per_package": quantity_per_package,
                    "total_quantity_packages": total_quantity_packages,
                    "total_quantity_real": total_quantity_real,
                    "total_amount": float(product.total_amount) if product.total_amount else 0
                })
            
            # Preparar respuesta
            result = {
                "status": "success",
                "products": products_data,
                "totals": {
                    "subtotal": float(totals_result.total_subtotal) if totals_result.total_subtotal else 0,
                    "tax": float(totals_result.total_tax) if totals_result.total_tax else 0,
                    "total": float(totals_result.total_total) if totals_result.total_total else 0
                },
                "summary": {
                    "total_sales": total_sales,
                    "date_from": desde.strftime("%Y-%m-%d") if desde else None,
                    "date_to": hasta.strftime("%Y-%m-%d") if hasta else None
                }
            }
            
            return result
            
        except Exception as e:
            print(f"[ERROR] Error al generar informe de ventas: {str(e)}")
            import traceback
            print(f"[ERROR] Traceback: {traceback.format_exc()}")
            return {
                "status": "error",
                "message": str(e),
                "products": [],
                "totals": {
                    "subtotal": 0,
                    "tax": 0,
                    "total": 0
                },
                "summary": {
                    "total_sales": 0,
                    "date_from": None,
                    "date_to": None
                }
            }