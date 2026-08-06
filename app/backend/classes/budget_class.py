from datetime import datetime
from sqlalchemy import func
from app.backend.db.models import (
    BudgetModel,
    BudgetProductModel,
    CustomerModel,
    ProductModel,
    SaleModel,
    SaleProductModel,
    InventoryModel,
    LotItemModel,
    LotModel,
    InventoryMovementModel,
    CustomerProductDiscountModel,
    SettingModel,
)
from app.backend.classes.whatsapp_class import WhatsappClass
from app.backend.services.promotions.promotion_pricing_service import PromotionPricingService

class BudgetClass:
    def __init__(self, db):
        self.db = db

    def _get_tax_percent(self) -> float:
        setting = self.db.query(SettingModel).filter(SettingModel.id == 1).first()
        if not setting or setting.tax_value is None:
            return 19.0
        try:
            return float(setting.tax_value)
        except (TypeError, ValueError):
            return 19.0

    def _customer_product_discount_percent(self, customer_id, product_id) -> float:
        if not customer_id or int(customer_id) <= 0:
            return 0.0
        row = (
            self.db.query(CustomerProductDiscountModel)
            .filter(CustomerProductDiscountModel.customer_id == int(customer_id))
            .filter(CustomerProductDiscountModel.product_id == int(product_id))
            .first()
        )
        if not row:
            return 0.0
        return float(row.discount_percentage or 0)

    def _resolve_budget_unit_price(self, product_id, customer_id=None, pricing_service=None, discounts_map=None):
        """
        Precio unitario para presupuesto: precio público con promoción activa (si hay),
        y luego descuento de cliente si aplica. El presupuesto al cliente siempre usa
        precio público/promo, nunca monto privado.
        """
        pricing = pricing_service or PromotionPricingService(self.db)
        active = discounts_map if discounts_map is not None else pricing.get_active_product_discounts_map()
        public_price = pricing.get_product_public_price(int(product_id))
        unit_price = float(public_price or 0)
        has_promotion = False
        promotion_discount_percent = 0.0
        original_price = unit_price

        promo = active.get(int(product_id))
        if promo and unit_price > 0:
            package_cost = pricing.get_product_package_cost(int(product_id))
            calculated = pricing.calculate_promotional_price(
                unit_price,
                promo.get('discount_percent') or 0,
                package_cost,
            )
            unit_price = float(calculated['promotional_price'])
            original_price = float(calculated['original_price'])
            has_promotion = True
            promotion_discount_percent = float(calculated['discount_percent'])

        customer_discount = self._customer_product_discount_percent(customer_id, product_id)
        if customer_discount > 0:
            unit_price = unit_price * (1 - customer_discount / 100)

        return {
            'unit_price': round(unit_price, 2),
            'original_price': original_price,
            'has_promotion': has_promotion,
            'promotion_discount_percent': promotion_discount_percent,
            'customer_discount_percent': customer_discount,
        }

    def _build_priced_budget_products(self, products, customer_id=None):
        pricing = PromotionPricingService(self.db)
        discounts_map = pricing.get_active_product_discounts_map()
        products_payload = []
        calculated_subtotal = 0

        for product in products:
            product_id = int(getattr(product, 'product_id', 0) or 0)
            quantity = int(getattr(product, 'quantity', 0) or 0)
            if product_id <= 0 or quantity <= 0:
                continue

            priced = self._resolve_budget_unit_price(
                product_id,
                customer_id=customer_id,
                pricing_service=pricing,
                discounts_map=discounts_map,
            )
            amount = int(round(priced['unit_price'] * quantity))
            products_payload.append({
                'product_id': product_id,
                'quantity': quantity,
                'total': amount,
                'unit_price': priced['unit_price'],
                'has_promotion': priced['has_promotion'],
            })
            calculated_subtotal += amount

        return products_payload, calculated_subtotal

    def _attach_promotion_to_budget_products(self, product_data):
        pricing_service = PromotionPricingService(self.db)
        discounts_map = pricing_service.get_active_product_discounts_map()
        enriched = []
        for item in product_data:
            row = dict(item)
            product_id = row.get("product_id")
            quantity = row.get("quantity") or 0
            stored_unit = None
            if quantity > 0 and row.get("total") is not None:
                stored_unit = int(row["total"] // quantity)
                row["sale_price"] = stored_unit
            if product_id:
                promo = discounts_map.get(int(product_id))
                if promo:
                    promo_price = int(round(float(promo["promotional_price"])))
                    original = int(round(float(promo["original_price"])))
                    # Solo marcar promoción si el precio guardado coincide con el promo
                    if stored_unit is not None and abs(stored_unit - promo_price) <= 1:
                        row["has_product_promotion"] = True
                        row["promotion_discount_percent"] = promo["discount_percent"]
                        row["public_sale_price_original"] = original
                        row["public_sale_price"] = promo_price
            enriched.append(row)
        return enriched

    def serialize_budget(self, budget_row):
        return {
            "id": budget_row.id,
            "customer_id": budget_row.customer_id,
            "customer_name": budget_row.customer_name,
            "status_id": budget_row.status_id if hasattr(budget_row, "status_id") else None,
            "subtotal": budget_row.subtotal,
            "shipping": budget_row.shipping if budget_row.shipping is not None else 0,
            "tax": budget_row.tax,
            "total": budget_row.total,
            "added_date": budget_row.added_date.strftime("%Y-%m-%d %H:%M:%S") if budget_row.added_date else None,
            "updated_date": budget_row.updated_date.strftime("%Y-%m-%d %H:%M:%S") if budget_row.updated_date else None
        }

    def get_all(self, rol_id=None, rut=None, page=0, items_per_page=10, identification_number=None, social_reason=None):
        try:
            # Obtener customer_id desde rut si no es rol 1 o 2
            customer = None
            if rut and (rol_id != 1 and rol_id != 2):
                # Convertir rut a string si es necesario
                rut_str = str(rut) if rut else None
                customer = (
                    self.db.query(CustomerModel)
                    .filter(CustomerModel.identification_number == rut_str)
                    .first()
                )

            query = (
                self.db.query(
                    BudgetModel.id,
                    BudgetModel.customer_id,
                    CustomerModel.social_reason.label("customer_name"),
                    BudgetModel.status_id,
                    BudgetModel.subtotal,
                    BudgetModel.shipping,
                    BudgetModel.tax,
                    BudgetModel.total,
                    BudgetModel.added_date,
                    BudgetModel.updated_date
                )
                .join(CustomerModel, CustomerModel.id == BudgetModel.customer_id, isouter=True)
                .order_by(BudgetModel.added_date.desc())
            )

            # Si rol_id es 1 o 2, mostrar todo. Si no, filtrar por customer_id
            if rol_id != 1 and rol_id != 2:
                if customer:
                    query = query.filter(BudgetModel.customer_id == customer.id)
                else:
                    # Si no se encuentra el cliente, retornar lista vacía
                    query = query.filter(BudgetModel.customer_id == -1)

            # Aplicar filtros de búsqueda si se proporcionan
            if identification_number and identification_number.strip():
                query = query.filter(CustomerModel.identification_number == identification_number.strip())

            if social_reason and social_reason.strip():
                query = query.filter(CustomerModel.social_reason.ilike(f"%{social_reason.strip()}%"))

            if page > 0:
                total_items = query.count()
                total_pages = max((total_items + items_per_page - 1) // items_per_page, 1) // items_per_page

                if page < 1 or (total_pages > 0 and page > total_pages):
                    return {"status": "error", "message": "Invalid page number"}

                data = query.offset((page - 1) * items_per_page).limit(items_per_page).all()

                if not data:
                    return {"status": "error", "message": "No data found"}

                serialized_data = [self.serialize_budget(item) for item in data]

                return {
                    "total_items": total_items,
                    "total_pages": total_pages,
                    "current_page": page,
                    "items_per_page": items_per_page,
                    "data": serialized_data
                }

            data = query.all()
            return [self.serialize_budget(item) for item in data]

        except Exception as e:
            return {"status": "error", "message": str(e)}

    def get(self, budget_id):
        try:
            budget = (
                self.db.query(
                    BudgetModel.id,
                    BudgetModel.customer_id,
                    CustomerModel.social_reason.label("customer_name"),
                    BudgetModel.status_id,
                    BudgetModel.subtotal,
                    BudgetModel.shipping,
                    BudgetModel.tax,
                    BudgetModel.total,
                    BudgetModel.added_date,
                    BudgetModel.updated_date
                )
                .join(CustomerModel, CustomerModel.id == BudgetModel.customer_id, isouter=True)
                .filter(BudgetModel.id == budget_id)
                .first()
            )

            if not budget:
                return {"status": "error", "message": "Budget not found"}

            products = (
                self.db.query(
                    BudgetProductModel.id,
                    BudgetProductModel.product_id,
                    ProductModel.product.label("product_name"),
                    BudgetProductModel.quantity,
                    BudgetProductModel.total
                )
                .join(ProductModel, ProductModel.id == BudgetProductModel.product_id, isouter=True)
                .filter(BudgetProductModel.budget_id == budget_id)
                .all()
            )

            product_data = [{
                "id": item.id,
                "product_id": item.product_id,
                "product_name": item.product_name,
                "quantity": item.quantity,
                "total": item.total
            } for item in products]

            return {
                "budget": self.serialize_budget(budget),
                "products": self._attach_promotion_to_budget_products(product_data)
            }

        except Exception as e:
            return {"status": "error", "message": str(e)}

    def store(self, budget_inputs):
        try:
            customer = self.db.query(CustomerModel).filter(CustomerModel.id == budget_inputs.customer_id).first()
            if not customer:
                return {"status": "error", "message": "Customer not found"}

            products_payload, calculated_subtotal = self._build_priced_budget_products(
                budget_inputs.products,
                customer_id=budget_inputs.customer_id,
            )
            if not products_payload:
                return {"status": "error", "message": "Debe agregar al menos un producto al presupuesto."}

            shipping = int(budget_inputs.shipping) if budget_inputs.shipping else 0
            tax_percent = self._get_tax_percent()
            tax = int(round((calculated_subtotal + shipping) * tax_percent / 100)) if tax_percent > 0 else 0
            total = calculated_subtotal + shipping + tax
            subtotal = calculated_subtotal

            new_budget = BudgetModel(
                customer_id=budget_inputs.customer_id,
                status_id=0,
                subtotal=subtotal,
                shipping=shipping,
                tax=tax,
                total=total,
                added_date=datetime.now(),
                updated_date=datetime.now()
            )

            self.db.add(new_budget)
            self.db.flush()

            for product in products_payload:
                new_product = BudgetProductModel(
                    budget_id=new_budget.id,
                    product_id=product["product_id"],
                    quantity=product["quantity"],
                    total=product["total"],
                    added_date=datetime.now(),
                    updated_date=datetime.now()
                )
                self.db.add(new_product)

            PromotionPricingService(self.db).record_product_discount_usages(
                [p for p in products_payload if p.get('has_promotion')],
                budget_id=new_budget.id,
            )

            self.db.commit()
            self.db.refresh(new_budget)

            # Enviar notificación de WhatsApp para revisar el presupuesto
            try:
                WhatsappClass(self.db).review_budget(
                    budget_id=new_budget.id,
                    total=total
                )
            except Exception as whatsapp_error:
                print(f"Error al enviar WhatsApp de review_budget: {str(whatsapp_error)}")
                # No fallar el proceso si falla el WhatsApp

            return {"status": "success", "budget_id": new_budget.id}

        except Exception as e:
            self.db.rollback()
            return {"status": "error", "message": str(e)}

    def store_without_customer(self, budget_inputs, skip_whatsapp_notification=False):
        """
        Crea un presupuesto sin guardar el cliente en la tabla customers.
        Los datos del cliente se guardan temporalmente en el presupuesto.
        skip_whatsapp_notification: Si es True, no envía el mensaje de revisión por WhatsApp.
        """
        try:
            products_payload, calculated_subtotal = self._build_priced_budget_products(
                budget_inputs.products,
                customer_id=None,
            )
            if not products_payload:
                return {"status": "error", "message": "Debe agregar al menos un producto al presupuesto."}

            shipping = int(budget_inputs.shipping) if budget_inputs.shipping else 0
            tax_percent = self._get_tax_percent()
            tax = int(round((calculated_subtotal + shipping) * tax_percent / 100)) if tax_percent > 0 else 0
            total = calculated_subtotal + shipping + tax
            subtotal = calculated_subtotal

            # Crear presupuesto con customer_id = -1 para indicar que no hay cliente guardado
            # Los datos del cliente se proporcionan en el request pero no se guardan en customers
            new_budget = BudgetModel(
                customer_id=-1,  # Valor especial para indicar que no hay cliente guardado
                status_id=0,
                subtotal=subtotal,
                shipping=shipping,
                tax=tax,
                total=total,
                added_date=datetime.now(),
                updated_date=datetime.now()
            )

            self.db.add(new_budget)
            self.db.flush()

            for product in products_payload:
                new_product = BudgetProductModel(
                    budget_id=new_budget.id,
                    product_id=product["product_id"],
                    quantity=product["quantity"],
                    total=product["total"],
                    added_date=datetime.now(),
                    updated_date=datetime.now()
                )
                self.db.add(new_product)

            PromotionPricingService(self.db).record_product_discount_usages(
                [p for p in products_payload if p.get('has_promotion')],
                budget_id=new_budget.id,
            )

            self.db.commit()
            self.db.refresh(new_budget)

            # Enviar notificación de WhatsApp para revisar el presupuesto
            # Solo si no se indica que se omita (ej: cuando viene de WhatsApp y se pregunta directamente)
            if not skip_whatsapp_notification:
                try:
                    # Obtener el teléfono del cliente desde budget_inputs
                    customer_phone = budget_inputs.phone if budget_inputs.phone else None
                    
                    if customer_phone:
                        # Enviar WhatsApp con los datos del cliente temporal
                        WhatsappClass(self.db).review_budget(
                            budget_id=new_budget.id,
                            total=total,
                            customer_phone=customer_phone,
                            customer_name=budget_inputs.social_reason
                        )
                    else:
                        print(f"[BUDGET_WITHOUT_CUSTOMER] No se envió WhatsApp porque no hay teléfono para presupuesto {new_budget.id}")
                except Exception as whatsapp_error:
                    print(f"Error al enviar WhatsApp de review_budget: {str(whatsapp_error)}")
                    # No fallar el proceso si falla el WhatsApp

            return {
                "status": "success",
                "budget_id": new_budget.id,
                "customer_data": {
                    "identification_number": budget_inputs.identification_number,
                    "social_reason": budget_inputs.social_reason,
                    "phone": budget_inputs.phone
                }
            }

        except Exception as e:
            self.db.rollback()
            return {"status": "error", "message": str(e)}

    def accept(self, budget_id, dte_type_id=None, dte_status_id=None, delivery_address_override=None):
        print(f"[BUDGET_ACCEPT] Iniciando aceptación de presupuesto {budget_id}, dte_type_id={dte_type_id}, dte_status_id={dte_status_id}")
        try:
            # Usar with_for_update() para bloquear la fila y prevenir race conditions
            budget = (
                self.db.query(BudgetModel)
                .filter(BudgetModel.id == budget_id)
                .with_for_update()  # Bloquea la fila hasta que se complete la transacción
                .first()
            )

            if not budget:
                print(f"[BUDGET_ACCEPT] Presupuesto {budget_id} no encontrado")
                return {"status": "error", "message": "Budget not found"}

            print(f"[BUDGET_ACCEPT] Presupuesto encontrado: customer_id={budget.customer_id}, status_id={budget.status_id}, total={budget.total}")

            # Verificar estado después de bloquear la fila
            if budget.status_id == 1:
                print(f"[BUDGET_ACCEPT] Presupuesto {budget_id} ya está aceptado")
                return {"status": "error", "message": "Budget already accepted"}

            # Obtener el cliente para obtener su dirección
            customer = (
                self.db.query(CustomerModel)
                .filter(CustomerModel.id == budget.customer_id)
                .first()
            )

            if not customer:
                return {"status": "error", "message": "Customer not found"}

            # Determinar shipping_method_id y delivery_address según shipping del presupuesto
            shipping_method_id = 1
            delivery_address = None
            has_shipping_cost = bool(budget.shipping and int(budget.shipping or 0) > 0)

            if delivery_address_override and str(delivery_address_override).strip():
                delivery_address = str(delivery_address_override).strip()
                shipping_method_id = 2 if has_shipping_cost else 1
            elif has_shipping_cost:
                shipping_method_id = 2
                delivery_address = customer.address if customer.address else None
            else:
                shipping_method_id = 1
                delivery_address = "Retiro en tienda / sin envío"

            # Determinar dte_type_id y dte_status_id
            # Si se pasan por parámetro, usar esos valores
            # Si no, intentar obtener del presupuesto
            final_dte_type_id = dte_type_id
            final_dte_status_id = dte_status_id
            
            if final_dte_type_id is None:
                budget_dte_type_id = getattr(budget, 'dte_type_id', None) if hasattr(budget, 'dte_type_id') else None
                final_dte_type_id = budget_dte_type_id
            
            # Si dte_status_id no se proporciona, usar None (no generar DTE)
            if final_dte_status_id is None:
                final_dte_status_id = None
            
            print(f"[BUDGET_ACCEPT] Valores DTE finales: dte_type_id={final_dte_type_id}, dte_status_id={final_dte_status_id}")
            
            new_sale = SaleModel(
                customer_id=budget.customer_id,
                shipping_method_id=shipping_method_id,
                dte_type_id=final_dte_type_id,
                dte_status_id=final_dte_status_id,
                status_id=1,
                subtotal=budget.subtotal,
                tax=budget.tax,
                shipping_cost=budget.shipping,
                total=budget.total,
                payment_support=None,
                delivery_address=delivery_address,
                added_date=datetime.now(),
                updated_date=datetime.now()
            )

            self.db.add(new_sale)
            self.db.flush()
            print(f"[BUDGET_ACCEPT] SaleModel creado con ID: {new_sale.id}")

            # Obtener productos del presupuesto
            budget_products = (
                self.db.query(BudgetProductModel)
                .filter(BudgetProductModel.budget_id == budget_id)
                .all()
            )

            print(f"[BUDGET_ACCEPT] Productos del presupuesto encontrados: {len(budget_products)}")

            # Crear productos de la venta desde el presupuesto
            for budget_product in budget_products:
                # Calcular precio unitario
                quantity = budget_product.quantity if budget_product.quantity > 0 else 1
                unit_price = int(budget_product.total // quantity) if quantity > 0 else budget_product.total

                print(f"[BUDGET_ACCEPT] Creando SaleProduct: product_id={budget_product.product_id}, quantity={budget_product.quantity}, price={unit_price}")

                # Crear SaleProductModel sin procesar inventario aún (inventory_movement_id=None)
                sale_product = SaleProductModel(
                    sale_id=new_sale.id,
                    product_id=budget_product.product_id,
                    inventory_movement_id=None,  # Se asignará al aceptar el pago
                    inventory_id=None,  # Se asignará al aceptar el pago
                    lot_item_id=None,  # Se asignará al aceptar el pago
                    quantity=budget_product.quantity,
                    price=unit_price
                )
                self.db.add(sale_product)

            # Cambiar status del presupuesto
            budget.status_id = 1
            budget.updated_date = datetime.now()

            self.db.commit()
            self.db.refresh(new_sale)

            print(f"[BUDGET_ACCEPT] Presupuesto aceptado exitosamente. Sale ID: {new_sale.id}")
            return {"status": "success", "sale_id": new_sale.id}

        except Exception as e:
            self.db.rollback()
            print(f"[BUDGET_ACCEPT] Error al aceptar presupuesto {budget_id}: {str(e)}")
            import traceback
            print(f"[BUDGET_ACCEPT] Traceback: {traceback.format_exc()}")
            return {"status": "error", "message": str(e)}

    def reject(self, budget_id):
        try:
            budget = (
                self.db.query(BudgetModel)
                .filter(BudgetModel.id == budget_id)
                .first()
            )

            if not budget:
                return {"status": "error", "message": "Budget not found"}

            budget.status_id = 2
            budget.updated_date = datetime.now()

            self.db.commit()

            return {"status": "success", "message": "Budget rejected"}

        except Exception as e:
            self.db.rollback()
            return {"status": "error", "message": str(e)}

    def delete(self, budget_id):
        try:
            # Buscar el budget
            budget = (
                self.db.query(BudgetModel)
                .filter(BudgetModel.id == budget_id)
                .first()
            )

            if not budget:
                return {"status": "error", "message": "Presupuesto no encontrado"}

            # Buscar y eliminar todos los productos relacionados
            budget_products = (
                self.db.query(BudgetProductModel)
                .filter(BudgetProductModel.budget_id == budget_id)
                .all()
            )

            # Eliminar cada producto relacionado
            for product in budget_products:
                self.db.delete(product)

            # Eliminar el budget
            self.db.delete(budget)

            # Confirmar cambios
            self.db.commit()

            return {"status": "success", "message": "Presupuesto y productos relacionados eliminados correctamente"}

        except Exception as e:
            self.db.rollback()
            error_message = str(e)
            return {"status": "error", "message": f"Error al eliminar el presupuesto: {error_message}"}

    def product_detail(self, product_id, customer_id=None):
        """
        Obtiene el detalle del producto para presupuesto.
        Devuelve nombre, precio público y descuento del cliente si se proporciona customer_id.
        """
        print(f"[BUDGET_PRODUCT_DETAIL] Llamado con product_id={product_id}, customer_id={customer_id}")
        try:
            # Verificar que el producto existe
            product = self.db.query(ProductModel).filter(ProductModel.id == product_id).first()
            if not product:
                return {"status": "error", "message": "Product not found"}
            
            # Verificar si hay lot_items para este producto
            lot_items_count = (
                self.db.query(LotItemModel)
                .filter(LotItemModel.product_id == product_id)
                .count()
            )
            print(f"[BUDGET_PRODUCT_DETAIL] Cantidad de lot_items para producto {product_id}: {lot_items_count}")
            
            # Obtener precio público del producto desde lot_items (máximo de todos los lot_items)
            price_query = (
                self.db.query(func.max(LotItemModel.public_sale_price).label("public_sale_price"))
                .filter(LotItemModel.product_id == product_id)
                .scalar()
            )
            
            print(f"[BUDGET_PRODUCT_DETAIL] Resultado de query de precio: {price_query} (tipo: {type(price_query)})")
            
            public_sale_price = int(price_query) if price_query is not None and price_query > 0 else 0
            print(f"[BUDGET_PRODUCT_DETAIL] Precio público final: {public_sale_price}")
            
            # Si no hay precio, intentar obtener directamente de lot_items
            if public_sale_price == 0:
                lot_item = (
                    self.db.query(LotItemModel)
                    .filter(LotItemModel.product_id == product_id)
                    .filter(LotItemModel.public_sale_price.isnot(None))
                    .filter(LotItemModel.public_sale_price > 0)
                    .first()
                )
                if lot_item:
                    public_sale_price = int(lot_item.public_sale_price)
                    print(f"[BUDGET_PRODUCT_DETAIL] Precio encontrado directamente en lot_item: {public_sale_price}")

            # Obtener descuento del cliente para este producto si se proporciona customer_id
            customer_discount = 0
            if customer_id:
                print(f"[BUDGET_PRODUCT_DETAIL] Buscando descuento para customer_id={customer_id}, product_id={product_id}")
                customer_discount_record = (
                    self.db.query(CustomerProductDiscountModel)
                    .filter(CustomerProductDiscountModel.customer_id == customer_id)
                    .filter(CustomerProductDiscountModel.product_id == product_id)
                    .first()
                )
                print(f"[BUDGET_PRODUCT_DETAIL] Descuento encontrado: {customer_discount_record is not None}")
                if customer_discount_record:
                    customer_discount = customer_discount_record.discount_percentage or 0
                    print(f"[BUDGET_PRODUCT_DETAIL] Descuento porcentaje: {customer_discount}")
                else:
                    print(f"[BUDGET_PRODUCT_DETAIL] No se encontró descuento para customer_id={customer_id}, product_id={product_id}")

            product_data = {
                "id": product.id,
                "product": product.product,
                "public_sale_price": public_sale_price,
                "customer_discount_percentage": customer_discount
            }

            print(f"[BUDGET_PRODUCT_DETAIL] Datos finales: {product_data}")
            return PromotionPricingService(self.db).enrich_product_dict(product_data)

        except Exception as e:
            return {"status": "error", "message": str(e)}