import requests
import os
import hashlib
import re
import uuid
import difflib
import unicodedata
from types import SimpleNamespace
from dotenv import load_dotenv
from datetime import datetime
from app.backend.classes.setting_class import SettingClass
from app.backend.db.models import (
    UserModel,
    BudgetModel,
    CustomerModel,
    BudgetProductModel,
    ProductModel,
    WhatsAppMessageModel,
    SettingModel,
    SaleModel,
    CustomerProductDiscountModel,
)
load_dotenv() 

class WhatsappClass:
    _chat_sessions = {}
    _EXIT_WORDS = frozenset(
        {
            "cancelar",
            "salir",
            "reiniciar",
            "terminar",
            "fin",
            "cerrar",
            "chau",
            "adiós",
            "adios",
            "stop",
        }
    )
    _BACK_WORDS = frozenset(
        {
            "volver",
            "atrás",
            "atras",
            "retroceder",
            "regresar",
            "anterior",
            "back",
        }
    )
    # Respuestas que no son dirección (texto normalizado sin tildes, minúsculas)
    _ABSURD_ADDRESS_EXACT = frozenset(
        {
            "no",
            "nose",
            "no se",
            "na",
            "nop",
            "nope",
            "nada",
            "ninguna",
            "ninguno",
            "no hay",
            "sin direccion",
            "no tengo",
            "no tengo direccion",
            "no se la direccion",
            "no me la se",
            "no la conozco",
            "no conozco",
            "no conozco la direccion",
            "no se donde vivo",
            "no se donde es",
            "despues",
            "luego",
            "paso",
            "salto",
            "cualquiera",
            "lo que sea",
            "da igual",
            "no importa",
            "asdf",
            "qwerty",
            "prueba",
            "test",
            "hola",
            "chau",
            "xd",
            "jaja",
            "jeje",
            "aaa",
            "aaaa",
            "aaaaa",
            "xdd",
            "123",
            "1234",
            "12345",
            "123456",
            "abc",
            "abcd",
            "qqqq",
            "wwww",
            "asdasd",
            "qweqwe",
            "zxc",
            "xxx",
            "ningun lado",
            "en ninguna parte",
            "no existe",
            "falsa",
            "inventada",
            "random",
            "no se cual",
            "no se cual es",
            "buscame",
            "googlealo",
            "maps",
            "no recuerdo",
            "olvide",
            "se me olvido",
            "privada",
            "secreto",
            "no digo",
            "no dire",
        }
    )
    _ABSURD_ADDRESS_IN_TEXT = (
        "no se donde",
        "no me la se",
        "no la conozco",
        "no tengo direccion",
        "no tengo la direccion",
        "prefiero no decir",
        "no quiero decir",
        "despues te digo",
        "te digo despues",
        "no puedo decir",
        "me invento",
        "inventa una",
        "pon lo que sea",
        "cualquier direccion",
        "no me acuerdo",
        "no recuerdo la direccion",
        "no se mi direccion",
        "no se la direccion",
        "no conozco mi direccion",
        "vivo en ningun lado",
        "no tengo casa",
        "no vivo aqui",
        "no vivo aca",
    )

    def __init__(self, db):
        self.db = db

    def _normalize_address_input(self, raw: str) -> str:
        s = (raw or "").strip().lower()
        t = unicodedata.normalize("NFKD", s)
        t = "".join(c for c in t if not unicodedata.combining(c))
        t = re.sub(r"\s+", " ", t).strip()
        return t

    def _delivery_address_user_error(self, raw: str) -> str | None:
        """
        None si la dirección parece aceptable.
        Si no, devuelve el texto completo para enviar al usuario.
        """
        t = self._normalize_address_input(raw)
        if not t:
            return (
                "⚠️ Necesitamos una dirección escrita.\n\n"
                "📍 Envía calle, número, comuna y referencias (ej: Los Laureles 890, Temuco, casa azul)."
            )
        if len(t) < 12:
            return (
                "⚠️ La dirección es muy corta o incompleta.\n\n"
                "📍 Escribe calle, número, comuna y si puedes una referencia."
            )
        if t in self._ABSURD_ADDRESS_EXACT:
            return (
                "⚠️ Eso no es una dirección de envío válida.\n\n"
                "📍 Escribe la dirección real donde debemos entregar: calle, número, comuna y referencias."
            )
        padded = f" {t} "
        for phrase in self._ABSURD_ADDRESS_IN_TEXT:
            if f" {phrase} " in padded:
                return (
                    "⚠️ Necesitamos la dirección completa y real, no esa clase de respuesta.\n\n"
                    "📍 Ejemplo: Av. Alemania 1234, Depto 502, Temuco."
                )
        if re.search(r"(.)\1{4,}", t):
            return (
                "⚠️ La dirección no se entiende (muchas letras o números repetidos).\n\n"
                "📍 Escríbela con calle, número, comuna y referencias claras."
            )
        letters = re.findall(r"[a-z]", t)
        digits = re.findall(r"[0-9]", t)
        words = [w for w in t.split() if re.search(r"[a-z0-9]", w)]
        if len(digits) >= 3 and len(letters) == 0:
            return (
                "⚠️ No aceptamos solo números.\n\n"
                "📍 Incluye nombre de calle, número, comuna (ej: O'Higgins 567, Valdivia)."
            )
        if len(letters) == 0:
            return (
                "⚠️ Falta el texto de la dirección (calle, comuna…).\n\n"
                "📍 Escribe la dirección completa con palabras y números."
            )
        has_digit = len(digits) > 0
        if not has_digit:
            if len(words) < 4 or len(t) < 22:
                return (
                    "⚠️ Sin número de calle o casa la dirección queda muy vaga.\n\n"
                    "📍 Incluye calle, número, comuna y referencias (o un texto más detallado con al menos 4 palabras)."
                )
        else:
            if len(words) < 2:
                return (
                    "⚠️ Agrega más detalle: comuna, sector o referencias junto al número.\n\n"
                    "📍 Ejemplo: Los Carrera 340, centro, Temuco."
                )
        return None

    def _is_exit_command(self, text: str) -> bool:
        t = (text or "").strip().lower()
        if not t:
            return False
        first = t.split()[0]
        return first in self._EXIT_WORDS or t in self._EXIT_WORDS

    def _is_back_command(self, text: str) -> bool:
        t = (text or "").strip().lower()
        if not t:
            return False
        first = t.split()[0]
        return first in self._BACK_WORDS or t in self._BACK_WORDS

    def _clean_phone_number(self, phone):
        """
        Limpia y formatea el número de teléfono:
        - Si es internacional (empieza con + y código de país), lo deja como viene
        - Si es chileno, normaliza a formato 56XXXXXXXXX
        """
        if not phone:
            return None
        
        # Convertir a string y quitar espacios al inicio/final
        phone = str(phone).strip()
        # Quitar todos los espacios en blanco
        phone = phone.replace(" ", "")
        
        # Si empieza con + seguido de dígitos (número internacional), dejarlo como viene
        if phone.startswith("+"):
            # Verificar que después del + hay al menos un dígito
            after_plus = phone[1:].replace("-", "").replace(" ", "")
            if after_plus and after_plus.isdigit():
                return phone
        
        # Si ya tiene código de país sin + (ej: 5412345678, 3412345678), dejarlo como viene
        # Detectamos si tiene más de 10 dígitos (probablemente incluye código de país)
        digits_only = re.sub(r"[^\d]", "", phone)
        if len(digits_only) > 10 and not phone.startswith("56"):
            return phone
        
        # Para números chilenos: quitar +56 si existe y agregar 56 si no tiene
        phone = phone.replace("+56", "")
        if not phone.startswith("56"):
            phone = "56" + phone
        
        return phone

    def _clean_text_for_whatsapp(self, text):
        """
        Limpia el texto para WhatsApp:
        - Quita saltos de línea (\n)
        - Quita tabulaciones (\t)
        - Reemplaza múltiples espacios consecutivos por un solo espacio
        - Limita a máximo 4 espacios consecutivos
        """
        if not text:
            return ""
        
        # Convertir a string
        text = str(text)
        
        # Reemplazar saltos de línea y tabulaciones por espacios
        text = text.replace("\n", " ")
        text = text.replace("\r", " ")
        text = text.replace("\t", " ")
        
        # Reemplazar múltiples espacios consecutivos por un solo espacio
        text = re.sub(r' +', ' ', text)
        
        # Limitar a máximo 4 espacios consecutivos (por si acaso)
        text = re.sub(r' {5,}', '    ', text)
        
        return text.strip()

    def _extract_message_text(self, message: dict):
        msg_type = message.get("type")
        if msg_type == "text":
            return (message.get("text", {}).get("body") or "").strip()
        if msg_type == "interactive":
            interactive = message.get("interactive", {})
            interactive_type = interactive.get("type")
            if interactive_type == "button_reply":
                br = interactive.get("button_reply") or {}
                # Preferimos el id del botón (coincide con 1/2/salir/volver en el flujo)
                bid = (br.get("id") or "").strip()
                if bid:
                    return bid
                return (br.get("title") or "").strip()
            if interactive_type == "list_reply":
                lr = interactive.get("list_reply") or {}
                lid = (lr.get("id") or "").strip()
                if lid:
                    return lid
                return (lr.get("title") or "").strip()
        return ""

    # Botones de respuesta rápida (WhatsApp Cloud API: máx. 3 por mensaje, título máx. 20 caracteres)
    _BTN_MAIN_MENU = [
        ("1", "Pedido / compra"),
        ("2", "Presupuesto"),
        ("salir", "Salir"),
    ]
    _BTN_YES_NO_BACK = [
        ("1", "Sí"),
        ("2", "No"),
        ("volver", "Volver"),
    ]
    _BTN_SHIPPING = [
        ("1", "Retiro en tienda"),
        ("2", "Envío domicilio"),
        ("volver", "Volver"),
    ]
    _BTN_DOC_BACK = [
        ("1", "Boleta"),
        ("2", "Factura"),
        ("volver", "Volver"),
    ]
    _BTN_PAY_BACK = [
        ("1", "Efectivo"),
        ("2", "Transferencia"),
        ("volver", "Volver"),
    ]
    _BTN_BUDGET_ACCEPT = [
        ("1", "Sí, acepto"),
        ("2", "No, rechazo"),
    ]
    _BTN_ORDER_REVIEW = [
        ("1", "Confirmar pedido"),
        ("2", "Agregar más"),
        ("volver", "Volver"),
    ]

    def _reply_button_title(self, title: str, max_len: int = 20) -> str:
        t = (title or "").strip()
        if len(t) <= max_len:
            return t
        return t[: max_len - 1].rstrip() + "…"

    def _parse_number(self, value):
        if value is None:
            return 0
        cleaned = re.sub(r"[^\d]", "", str(value))
        return int(cleaned) if cleaned else 0

    def _format_currency(self, amount: int):
        return f"${int(amount):,}".replace(",", ".")

    _RUT_CHILE_INVALID_MSG = (
        "⚠️ RUT no válido.\n\n"
        "📝 Ingresa el número con o sin guión (ej. 7651334-8 o 76513348). "
        "El dígito verificador debe ser correcto. Puedes usar puntos: 7.651.334-8"
    )

    def _rut_chile_compute_dv(self, body: str) -> str:
        """Dígito verificador módulo 11 (Chile). body solo dígitos (8 cifras, con ceros a la izquierda si aplica), sin DV."""
        if not body or not body.isdigit():
            return ""
        s = 0
        m = 2
        for ch in reversed(body):
            s += int(ch) * m
            m = m + 1 if m < 7 else 2
        d = 11 - (s % 11)
        if d == 11:
            return "0"
        if d == 10:
            return "K"
        return str(d)

    def _normalize_rut_chile(self, rut_input: str):
        """
        Normaliza RUT chileno a cuerpo-DV sin puntos (ej. 7651334-8). Acepta con o sin guión.
        El DV se valida sobre el cuerpo rellenado a 8 dígitos (ceros a la izquierda), como en documentos antiguos (ej. 07651334-8 ≡ 76513348).
        Retorna None si no es válido.
        """
        if not rut_input:
            return None
        t = str(rut_input).strip().upper().replace(".", "").replace(" ", "")
        if not t:
            return None
        if "-" in t:
            body, dv = t.split("-", 1)
        else:
            if len(t) < 8:
                return None
            body, dv = t[:-1], t[-1]
        if not body or not dv or len(dv) != 1:
            return None
        if not body.isdigit() or len(body) < 7 or len(body) > 8:
            return None
        dv = dv.upper()
        if dv not in "0123456789K":
            return None
        canonical = body.lstrip("0") or "0"
        if len(canonical) < 7 or len(canonical) > 8:
            return None
        padded = body.zfill(8)
        expected = self._rut_chile_compute_dv(padded)
        if dv != expected:
            return None
        return f"{canonical}-{dv}"

    def _find_customer_by_rut(self, rut_normalized: str):
        if not rut_normalized:
            return None
        body, dv = rut_normalized.split("-", 1)
        no_dash = f"{body}{dv}"
        variants = {rut_normalized, no_dash}
        if len(body) == 8:
            variants.add(f"{body[0:2]}.{body[2:5]}.{body[5:8]}-{dv}")
        if len(body) == 7:
            variants.add(f"{body[0:1]}.{body[1:4]}.{body[4:7]}-{dv}")
        return (
            self.db.query(CustomerModel)
            .filter(CustomerModel.identification_number.in_(list(variants)))
            .first()
        )

    def _sync_customer_whatsapp_phone(self, customer: CustomerModel, wa_phone: str):
        """Actualiza teléfono del cliente con el número de WhatsApp si falta o cambió."""
        clean_phone = self._clean_phone_number(wa_phone)
        if not customer or not clean_phone:
            return
        if (customer.phone or "").replace(" ", "") != clean_phone.replace(" ", ""):
            customer.phone = clean_phone
            customer.updated_date = datetime.now()
            self.db.commit()

    def _create_new_customer_record(self, session: dict, wa_phone: str):
        """Crea cliente nuevo después de tener RUT, nombre, envío y dirección si aplica."""
        clean_phone = self._clean_phone_number(wa_phone)
        social = f"{session.get('first_name', '').strip()} {session.get('last_name', '').strip()}".strip()
        address = (session.get("delivery_address") or "").strip() or "Sin dirección"
        customer = CustomerModel(
            region_id=1,
            commune_id=1,
            identification_number=session["rut"],
            social_reason=social or f"Cliente {session['rut']}",
            activity="Venta WhatsApp",
            address=address,
            phone=clean_phone,
            email=f"whatsapp_{clean_phone}@local",
            added_date=datetime.now(),
            updated_date=datetime.now(),
        )
        self.db.add(customer)
        self.db.commit()
        self.db.refresh(customer)
        session["customer_id"] = customer.id
        session["is_new"] = False

    def _cart_subtotal(self, session: dict):
        return sum(
            item["price"] * item["quantity"]
            for item in session.get("cart", {}).values()
        )

    def _preview_totals_for_session(self, session: dict):
        """
        Totales alineados con SaleClass.store para rol público:
        - sin envío (1): IVA solo subtotal productos
        - con envío (2): IVA sobre (subtotal + shipping_cost)
        """
        from app.backend.classes.sale_class import SaleClass

        subtotal = int(self._cart_subtotal(session))
        shipping_method_id = session.get("shipping_method_id") or 1
        shipping_cost = 0
        if shipping_method_id == 2:
            shipping_cost = int(round(SaleClass(self.db).get_shipping_cost()))

        if shipping_method_id == 2 and shipping_cost > 0:
            tax = int(round((subtotal + shipping_cost) * 0.19))
            total = subtotal + shipping_cost + tax
        else:
            tax = int(round(subtotal * 0.19))
            total = subtotal + tax

        return subtotal, shipping_cost, tax, total

    def _get_public_products(self, customer_id=None):
        """
        Misma lógica que la tienda: precio público = max(public_sale_price) por lote
        (ProductClass.sale_list), más descuento por producto/cliente si existe en la web.
        """
        from app.backend.classes.product_class import ProductClass

        result_pc = ProductClass(self.db).sale_list(0)
        if not isinstance(result_pc, dict) or result_pc.get("status") == "error":
            return []
        data = result_pc.get("data") or []
        if not data:
            return []

        discounts = {}
        if customer_id:
            rows = (
                self.db.query(CustomerProductDiscountModel)
                .filter(CustomerProductDiscountModel.customer_id == customer_id)
                .all()
            )
            discounts = {r.product_id: (r.discount_percentage or 0) for r in rows}

        def _pct_num(v):
            try:
                return float(v or 0)
            except (TypeError, ValueError):
                return 0.0

        result = []
        for p in data:
            pid = p["id"]
            base = int(p.get("public_sale_price") or 0)
            pct = _pct_num(discounts.get(pid, 0))
            if 0 < pct <= 100:
                price = int(round(base * (100 - pct) / 100))
            else:
                price = base
            result.append({
                "id": pid,
                "name": p["product"],
                "price": price,
            })
        return result

    def _build_product_prompt_text(self, products):
        if not products:
            return "No hay productos disponibles en este momento."
        return "Escribe el nombre del producto que buscas (luego te pediremos la cantidad)."

    def _normalize_product_search(self, s: str) -> str:
        if not s:
            return ""
        s = unicodedata.normalize("NFD", str(s))
        s = "".join(c for c in s if unicodedata.category(c) != "Mn")
        return re.sub(r"\s+", " ", s.lower().strip())

    def _score_name_similarity(self, query_norm: str, product_norm: str) -> float:
        """
        Similitud 0..1: tolera errores de tipeo, palabras parciales y orden distinto.
        """
        if not query_norm or not product_norm:
            return 0.0
        if query_norm == product_norm:
            return 1.0
        if query_norm in product_norm:
            return 0.92
        if product_norm in query_norm:
            return 0.84

        ratio_full = difflib.SequenceMatcher(None, query_norm, product_norm).ratio()

        q_tokens = re.findall(r"[a-z0-9]{2,}", query_norm)
        if not q_tokens:
            return ratio_full

        match_sum = 0.0
        p_tokens = re.findall(r"[a-z0-9]{2,}", product_norm)
        for qt in q_tokens:
            if qt in product_norm:
                match_sum += 1.0
                continue
            best_r = 0.0
            for pt in p_tokens:
                r = difflib.SequenceMatcher(None, qt, pt).ratio()
                if r > best_r:
                    best_r = r
            if best_r >= 0.52:
                match_sum += best_r

        token_score = match_sum / len(q_tokens)
        return max(ratio_full, 0.4 * ratio_full + 0.6 * token_score)

    def _resolve_name_to_product_id(self, name_query: str, products: list):
        """
        Devuelve (product_id, candidatos_ambiguos).
        Usa similitud difusa; candidatos si hay varios resultados muy parecidos.
        """
        nq = self._normalize_product_search(name_query)
        if len(nq) < 2:
            return None, []

        scored = []
        for p in products:
            pn = self._normalize_product_search(p["name"])
            score = self._score_name_similarity(nq, pn)
            scored.append((score, p))

        scored.sort(key=lambda x: -x[0])
        if not scored or scored[0][0] <= 0:
            return None, []

        best = scored[0][0]
        second = scored[1][0] if len(scored) > 1 else 0.0

        MIN_SCORE = 0.38
        GAP_CLEAR = 0.085
        AMBIGUOUS_BAND = 0.072

        if best < MIN_SCORE:
            return None, []

        if best - second >= GAP_CLEAR or second < MIN_SCORE:
            return scored[0][1]["id"], []

        close = [p for s, p in scored if s >= best - AMBIGUOUS_BAND and s >= MIN_SCORE]
        if len(close) <= 1:
            return close[0]["id"], []
        return None, close[:10]

    def _resolve_product_pick_one(self, raw_text: str, products: list):
        """Un solo producto por nombre (sin listado ni id)."""
        raw_text = (raw_text or "").strip()
        if not raw_text:
            return None, "Escribe el nombre del producto."

        if re.match(r"^\s*\d+\s+\d+\s*$", raw_text):
            return None, "📝 Envía solo el nombre del producto\n\n🔢 Luego te pediremos la cantidad"

        if re.match(r"^\s*\d+\s*$", raw_text):
            return None, "Indica el nombre del producto, no un número."

        pid, cands = self._resolve_name_to_product_id(raw_text, products)
        if pid:
            return pid, None
        if cands:
            lines = [f"🔍 Hay varias coincidencias para «{raw_text}»\n\n⚠️ Sé más específico con el nombre:"]
            for p in cands[:10]:
                lines.append(
                    f"- {self._clean_text_for_whatsapp(p['name'])} ({self._format_currency(p['price'])})"
                )
            return None, "\n".join(lines)

        return None, (
            f"No encontré «{raw_text}». Prueba con más palabras o un nombre más parecido "
            "(no hace falta que sea exacto)."
        )

    def _build_order_review_text(self, session: dict, subtotal: int, shipping_cost: int, tax: int, total: int):
        lines = ["📋 Resumen de tu pedido:", ""]
        for item in session.get("cart", {}).values():
            line_total = int(item["price"]) * int(item["quantity"])
            lines.append(
                f"📦 {self._clean_text_for_whatsapp(item['name'])} x {item['quantity']} → {self._format_currency(line_total)}"
            )
        lines.append("")
        lines.append(f"📦 Productos: {self._format_currency(subtotal)}")
        if session.get("shipping_method_id") == 2:
            lines.append(f"🚚 Envío: {self._format_currency(shipping_cost)}")
            addr = session.get("delivery_address") or "-"
            lines.append(f"📍 Dirección: {self._clean_text_for_whatsapp(str(addr))}")
        lines.append(f"📊 IVA: {self._format_currency(tax)}")
        lines.append(f"💰 Total: {self._format_currency(total)}")
        return "\n".join(lines)

    def _create_sale_from_session(self, phone: str, session: dict):
        """
        Crea la venta con status_id=1 (pendiente / revisión de pago), igual efectivo o transferencia.
        El inventario se descuenta solo al aceptar pago (status 2) desde el ERP.
        """
        from app.backend.classes.sale_class import SaleClass

        customer = self.db.query(CustomerModel).filter(CustomerModel.id == session.get("customer_id")).first()
        if not customer:
            return {"ok": False, "error": "Cliente no registrado en la sesión"}

        subtotal = int(self._cart_subtotal(session))
        shipping_method_id = session.get("shipping_method_id") or 1
        delivery_address = (session.get("delivery_address") or "Pedido por WhatsApp").strip()

        # Placeholders: SaleClass.store recalcula tax/total según envío
        tax_placeholder = float(int(round(subtotal * 0.19)))
        total_placeholder = float(subtotal + tax_placeholder)

        cart = []
        for item in session["cart"].values():
            cart.append({
                "id": item["id"],
                "quantity": item["quantity"],
                "lot_numbers": "",
                "public_sale_price": item["price"],
                "private_sale_price": item["price"]
            })

        doc_id = session.get("document_type_id")
        if doc_id not in (33, 39):
            doc_id = 39

        sale_input = SimpleNamespace(
            rol_id=5,
            customer_rut=customer.identification_number,
            document_type_id=doc_id,
            delivery_address=delivery_address,
            subtotal=float(subtotal),
            tax=tax_placeholder,
            total=total_placeholder,
            cart=[SimpleNamespace(**x) for x in cart],
            shipping_method_id=shipping_method_id
        )

        sale_result = SaleClass(self.db).store(sale_input)
        if isinstance(sale_result, dict) and sale_result.get("sale_id"):
            sale_id = sale_result["sale_id"]
            sale_row = self.db.query(SaleModel).filter(SaleModel.id == sale_id).first()
            if sale_row and sale_row.status_id != 1:
                sale_row.status_id = 1
                self.db.commit()
                self.db.refresh(sale_row)
            return {
                "ok": True,
                "sale_id": sale_id,
                "subtotal": int(sale_row.subtotal) if sale_row and sale_row.subtotal is not None else subtotal,
                "shipping_cost": int(sale_row.shipping_cost) if sale_row and sale_row.shipping_cost is not None else 0,
                "tax": int(sale_row.tax) if sale_row and sale_row.tax is not None else int(tax_placeholder),
                "total": int(sale_row.total) if sale_row and sale_row.total is not None else int(total_placeholder),
            }
        return {"ok": False, "error": str(sale_result)}

    def _build_payment_info_text(self):
        setting = self.db.query(SettingModel).filter(SettingModel.id == 1).first()
        if not setting:
            return "No se encontró configuración bancaria."

        return (
            "Datos para transferencia:\n"
            f"Banco: {setting.bank or '-'}\n"
            f"Tipo cuenta: {setting.account_type or '-'}\n"
            f"N° cuenta: {setting.account_number or '-'}\n"
            f"Titular: {setting.account_name or '-'}\n"
            f"Correo: {setting.account_email or '-'}"
        )

    def _whatsapp_graph_media_url(self, media_id: str) -> dict | None:
        token = os.getenv("META_TOKEN")
        if not token or not media_id:
            return None
        url = f"https://graph.facebook.com/v22.0/{media_id}"
        r = requests.get(url, headers={"Authorization": f"Bearer {token}"}, timeout=60)
        if r.status_code != 200:
            print(f"[WHATSAPP_MEDIA] media_id error {r.status_code}: {r.text}")
            return None
        return r.json()

    def _download_whatsapp_image_bytes(self, media_id: str) -> tuple[bytes, str] | None:
        meta = self._whatsapp_graph_media_url(media_id)
        if not meta or not meta.get("url"):
            return None
        token = os.getenv("META_TOKEN")
        r = requests.get(meta["url"], headers={"Authorization": f"Bearer {token}"}, timeout=120)
        if r.status_code != 200:
            print(f"[WHATSAPP_MEDIA] download error {r.status_code}")
            return None
        mime = (meta.get("mime_type") or "image/jpeg").lower()
        ext = {"image/jpeg": "jpg", "image/jpg": "jpg", "image/png": "png", "image/webp": "webp"}.get(
            mime, "jpg"
        )
        return (r.content, ext)

    def _save_sale_transfer_proof_file(self, sale_id: int, image_bytes: bytes, ext: str) -> str | None:
        from app.backend.classes.file_class import FileClass

        ts = datetime.now().strftime("%Y_%m_%d_%H_%M_%S")
        uid = uuid.uuid4().hex[:8]
        filename = f"payment_wa_{sale_id}_{ts}_{uid}.{ext}"
        try:
            FileClass(self.db).temporal_upload(image_bytes, filename)
            return filename
        except Exception as e:
            print(f"[WHATSAPP_MEDIA] save error: {e}")
            return None

    def _handle_transfer_proof_image_message(self, message: dict):
        """Recibe imagen del comprobante de transferencia y la guarda en la venta (payment_support)."""
        phone = message.get("from")
        if not phone:
            return
        session = self._chat_sessions.get(phone)
        if not session or session.get("step") not in (
            "order_await_transfer_proof",
            "budget_await_transfer_proof",
        ):
            return
        sale_id = session.get("await_transfer_proof_sale_id")
        if not sale_id:
            self._chat_sessions.pop(phone, None)
            self.send_autoreply(phone, "⚠️ Sesión incompleta. Escribe Hola para comenzar de nuevo.")
            return
        media_id = (message.get("image") or {}).get("id")
        if not media_id:
            self.send_autoreply(phone, "⚠️ No recibí la imagen. Envía una foto del comprobante.")
            return
        got = self._download_whatsapp_image_bytes(media_id)
        if not got:
            self.send_autoreply(
                phone,
                "⚠️ No pude descargar la imagen. Intenta enviarla de nuevo en unos segundos.",
            )
            return
        image_bytes, ext = got
        filename = self._save_sale_transfer_proof_file(int(sale_id), image_bytes, ext)
        if not filename:
            self.send_autoreply(phone, "⚠️ No pude guardar el comprobante. Intenta de nuevo.")
            return
        sale = self.db.query(SaleModel).filter(SaleModel.id == int(sale_id)).first()
        if not sale:
            self._chat_sessions.pop(phone, None)
            self.send_autoreply(phone, "⚠️ No encontré el pedido.")
            return
        sale.payment_support = filename
        sale.updated_date = datetime.now()
        self.db.commit()
        self.send_autoreply(
            phone,
            f"✅ Comprobante recibido para el pedido #{sale_id}.\n\n"
            "Queda registrado en tu pedido para revisión.\n"
            + self._farewell_after_purchase_text(),
        )
        self._chat_sessions.pop(phone, None)

    def _farewell_after_purchase_text(self) -> str:
        return (
            "\n\n🙏 ¡Gracias por tu pedido!\n"
            "👋 Si más adelante quieres comprar de nuevo, escribe Hola.\n"
            "✨ ¡Que tengas un excelente día!"
        )

    def _farewell_after_budget_text(self) -> str:
        return "\n\n👋 Escribe Hola cuando quieras solicitar otro presupuesto."

    def _looks_like_email(self, s: str) -> bool:
        s = (s or "").strip()
        return bool(re.match(r"^[^\s@]+@[^\s@]+\.[^\s@]+$", s))

    def _send_budget_pdf_email(
        self,
        receiver_email: str,
        budget_id: int,
        document_label: str,
        delivery_address: str = None,
    ) -> str:
        from app.backend.classes.template_class import TemplateClass
        from app.backend.classes.email_class import EmailClass

        tpl = TemplateClass(self.db)
        html_pdf = tpl.generate_budget_pdf_html(
            budget_id,
            document_label=document_label or "",
            contact_email=receiver_email.strip(),
            delivery_address=delivery_address,
        )
        if not html_pdf.strip():
            return "no_pdf"

        try:
            pdf_bytes = tpl.html_to_pdf_bytes(html_pdf)
        except Exception:
            return "pdf_error"

        vitrificado_logo_url = "https://api.lacasadelvitrificado.com/public/assets/vitrificado-logo.png"
        body_html = f"""
        <html><head><meta charset="utf-8"></head>
        <body style="font-family: Arial, sans-serif; font-size: 14px;">
        <img src="{vitrificado_logo_url}" style="width:120px;" alt="VitrificadosChile" />
        <p>Adjunto encontrarás el detalle de tu presupuesto en PDF.</p>
        <p>Saludos,<br/>Equipo VitrificadosChile</p>
        </body></html>
        """

        email_client = EmailClass(
            "bergerseidle@vitrificadoschile.com",
            "VitrificadosChile",
            "bhva zicx wfub duxg",
        )
        result = email_client.send_email(
            receiver_email=receiver_email.strip(),
            subject=f"Presupuesto #{budget_id} — VitrificadosChile",
            message=body_html,
            pdf_bytes=pdf_bytes,
            pdf_filename=f"presupuesto_{budget_id}.pdf",
        )
        if "correctamente" in (result or "").lower():
            return "ok"
        return result or "email_error"

    def _finalize_budget_accept_sale(self, phone: str, session: dict, payment_choice: str) -> dict:
        """Vincula cliente al presupuesto, ejecuta accept() y guarda medio de pago en la venta."""
        from app.backend.classes.budget_class import BudgetClass

        bid = session.get("pending_budget_id")
        cid = session.get("customer_id")
        doc_id = session.get("document_type_id")
        if not bid or not cid:
            return {"ok": False, "error": "Datos incompletos"}
        if doc_id not in (33, 39):
            doc_id = 39

        budget = self.db.query(BudgetModel).filter(BudgetModel.id == bid).first()
        if not budget:
            return {"ok": False, "error": "Presupuesto no encontrado"}
        if budget.status_id == 1:
            return {"ok": False, "error": "Presupuesto ya fue aceptado"}
        if budget.status_id == 2:
            return {"ok": False, "error": "Presupuesto rechazado"}

        budget.customer_id = cid
        budget.updated_date = datetime.now()
        self.db.commit()

        delivery = (session.get("delivery_address") or "").strip() or None
        accept_res = BudgetClass(self.db).accept(
            int(bid),
            dte_type_id=doc_id,
            delivery_address_override=delivery,
        )
        if isinstance(accept_res, dict) and accept_res.get("status") == "error":
            return {"ok": False, "error": accept_res.get("message", "Error al aceptar")}

        sale_id = accept_res.get("sale_id") if isinstance(accept_res, dict) else None
        if not sale_id:
            return {"ok": False, "error": "No se obtuvo la venta"}

        pay_label = "Transferencia" if payment_choice == "2" else "Efectivo"
        sale = self.db.query(SaleModel).filter(SaleModel.id == sale_id).first()
        if sale:
            sale.payment_support = pay_label
            if sale.status_id != 1:
                sale.status_id = 1
            self.db.commit()
            self.db.refresh(sale)

        total = int(sale.total) if sale and sale.total is not None else int(budget.total or 0)
        ship_cost = int(sale.shipping_cost) if sale and sale.shipping_cost is not None else int(budget.shipping or 0)

        return {
            "ok": True,
            "sale_id": sale_id,
            "total": total,
            "shipping_cost": ship_cost,
        }

    def _sync_budget_cart_prices(self, session: dict):
        """Recalcula precios del carrito con descuentos del cliente (tras conocer RUT)."""
        cid = session.get("customer_id")
        if not cid or not session.get("cart"):
            return
        pm = {p["id"]: p for p in self._get_public_products(cid)}
        for pid, item in session["cart"].items():
            if pid in pm:
                item["price"] = pm[pid]["price"]

    def _preview_budget_cart_only_totals(self, session: dict):
        """Subtotal productos + IVA (sin envío), para el primer resumen de presupuesto."""
        subtotal = int(self._cart_subtotal(session))
        tax = int(round(subtotal * 0.19))
        total = subtotal + tax
        return subtotal, tax, total

    def _create_budget_from_whatsapp_session(self, phone: str, session: dict):
        from app.backend.classes.budget_class import BudgetClass

        email = (session.get("budget_contact_email") or "").strip()
        if not email or not self._looks_like_email(email):
            return {"ok": False, "error": "Correo no válido"}

        subtotal, shipping_cost, tax, total = self._preview_totals_for_session(session)

        products_ns = []
        for item in session["cart"].values():
            pid = item["id"]
            qty = int(item["quantity"])
            unit = int(item["price"])
            line = unit * qty
            products_ns.append(
                SimpleNamespace(
                    product_id=pid,
                    quantity=qty,
                    sale_price=float(unit),
                    amount=line,
                )
            )

        wa_phone = self._clean_phone_number(phone) or phone
        budget_inputs = SimpleNamespace(
            products=products_ns,
            subtotal=subtotal,
            shipping=shipping_cost,
            tax=tax,
            total=total,
            phone=wa_phone,
            social_reason=email,
            identification_number="",
        )

        res = BudgetClass(self.db).store_without_customer(budget_inputs, skip_whatsapp_notification=True)
        if isinstance(res, dict) and res.get("status") == "success" and res.get("budget_id"):
            return {"ok": True, "budget_id": res["budget_id"], "total": total}
        return {"ok": False, "error": str(res)}

    def _new_session_dict(self):
        return {
            "step": "main_menu",
            "flow": None,
            "cart": {},
            "rut": None,
            "customer_id": None,
            "is_new": False,
            "first_name": "",
            "last_name": "",
            "shipping_method_id": None,
            "delivery_address": None,
            "document_type_id": None,
            "budget_contact_email": None,
            "processing_budget_email": False,
        }

    def _reply_while_processing_budget_email(self, phone: str):
        """Mensaje si el usuario escribe de nuevo mientras se genera/envía el PDF al correo."""
        self.send_autoreply(
            phone,
            "⏳ Todavía estamos procesando tu presupuesto y el envío del correo con el PDF.\n\n"
            "Por favor espera unos segundos y no envíes otro mensaje hasta recibir la confirmación.\n\n"
            "Si volviste a escribir: sigue en proceso; en cuanto termine te respondemos aquí.",
        )

    def _resend_budget_accept_reject_prompt(self, phone: str, session: dict):
        bid = session.get("pending_budget_id")
        contact_email = (session.get("budget_contact_email") or "").strip()
        total = 0
        if bid:
            row = self.db.query(BudgetModel).filter(BudgetModel.id == bid).first()
            if row and row.total is not None:
                total = int(row.total)
        self.send_autoreply(
            phone,
            "📧 Presupuesto enviado a tu correo\n\n"
            f"📄 Revisa tu correo ({contact_email or '—'}); va el PDF adjunto\n"
            f"📋 N° {bid} · 💰 Total: {self._format_currency(total)}\n\n"
            "❓ ¿Aceptas este presupuesto?",
            buttons=list(self._BTN_BUDGET_ACCEPT),
        )

    def _budget_go_back(self, phone: str, session: dict) -> bool:
        """Retrocede un paso en el flujo de presupuesto. Devuelve True si aplicó."""
        step = session.get("step")
        products = self._get_public_products(None)
        if step == "budget_selecting_products":
            session["step"] = "main_menu"
            session["flow"] = None
            session["cart"] = {}
            session.pop("pending_product_id", None)
            session.pop("pending_product_name", None)
            self.send_autoreply(
                phone,
                "⬅️ Volviste al menú principal",
                buttons=list(self._BTN_MAIN_MENU),
            )
            return True

        if step == "budget_ask_quantity":
            session["step"] = "budget_selecting_products"
            session.pop("pending_product_id", None)
            session.pop("pending_product_name", None)
            self.send_autoreply(
                phone,
                "📦 Indica el producto por nombre:\n"
                + self._build_product_prompt_text(products),
            )
            return True

        if step == "budget_ask_more":
            session["step"] = "budget_selecting_products"
            self.send_autoreply(
                phone,
                "📦 Indica el producto por nombre:\n"
                + self._build_product_prompt_text(products),
            )
            return True

        if step == "budget_ask_shipping":
            if not session.get("cart"):
                session["step"] = "budget_selecting_products"
                self.send_autoreply(
                    phone,
                    "📦 Indica el producto por nombre:\n"
                    + self._build_product_prompt_text(products),
                )
            else:
                session["step"] = "budget_ask_more"
                self.send_autoreply(
                    phone,
                    "🛒 ¿Agregar otro producto?",
                    buttons=list(self._BTN_YES_NO_BACK),
                )
            return True

        if step == "budget_collect_address":
            session["step"] = "budget_ask_shipping"
            self.send_autoreply(
                phone,
                "🚚 ¿Envío a domicilio o retiro en tienda?",
                buttons=list(self._BTN_SHIPPING),
            )
            return True

        if step == "budget_collect_email":
            if session.get("shipping_method_id") == 2:
                session["step"] = "budget_collect_address"
                self.send_autoreply(
                    phone,
                    "📍 Indica la dirección completa:\n"
                    "• Calle y número\n"
                    "• Comuna\n"
                    "• Referencias\n\n"
                    "Después te pediremos tu correo.",
                )
            else:
                session["step"] = "budget_ask_shipping"
                self.send_autoreply(
                    phone,
                    "🚚 ¿Envío a domicilio o retiro en tienda?",
                    buttons=list(self._BTN_SHIPPING),
                )
            return True

        if step == "budget_ask_accept_reject":
            self.send_autoreply(
                phone,
                "⚠️ Aquí no se puede volver atrás (el presupuesto ya está registrado).\n\n"
                "Elige una opción:",
                buttons=list(self._BTN_BUDGET_ACCEPT),
            )
            return True

        if step == "budget_accept_collect_rut":
            session["step"] = "budget_ask_accept_reject"
            self._resend_budget_accept_reject_prompt(phone, session)
            return True

        if step == "budget_accept_collect_first_name":
            session["step"] = "budget_accept_collect_rut"
            self.send_autoreply(
                phone,
                "📝 Para crear tu pedido, envíame tu RUT\n"
                "Ejemplo: 12345678-9",
            )
            return True

        if step == "budget_accept_collect_last_name":
            session["step"] = "budget_accept_collect_first_name"
            self.send_autoreply(phone, "Indica tu nombre (solo nombre).")
            return True

        if step == "budget_accept_choose_document":
            if session.get("budget_accept_doc_from") == "new":
                session["step"] = "budget_accept_collect_last_name"
                self.send_autoreply(phone, "Ahora tus apellidos.")
            else:
                session["step"] = "budget_accept_collect_rut"
                self.send_autoreply(
                    phone,
                    "📝 Para crear tu pedido, envíame tu RUT\n"
                    "Ejemplo: 12345678-9",
                )
            return True

        if step == "budget_accept_choose_payment":
            session["step"] = "budget_accept_choose_document"
            self.send_autoreply(
                phone,
                "📄 Tipo de documento para tu pedido",
                buttons=list(self._BTN_DOC_BACK),
            )
            return True

        return False

    def _order_go_back(self, phone: str, session: dict) -> bool:
        """Retrocede un paso en el flujo de pedido. Devuelve True si aplicó."""
        step = session.get("step")
        products = self._get_public_products(session.get("customer_id"))
        if step == "ask_rut":
            session["step"] = "main_menu"
            session["flow"] = None
            session["cart"] = {}
            session["rut"] = None
            session["customer_id"] = None
            session["is_new"] = False
            session["first_name"] = ""
            session["last_name"] = ""
            session["shipping_method_id"] = None
            session["delivery_address"] = None
            session["document_type_id"] = None
            self.send_autoreply(
                phone,
                "⬅️ Volviste al menú principal",
                buttons=list(self._BTN_MAIN_MENU),
            )
            return True

        if step == "collect_first_name":
            session["step"] = "ask_rut"
            self.send_autoreply(
                phone,
                "📝 Envíame tu RUT\n"
                "Ejemplo: 12345678-9",
            )
            return True

        if step == "collect_last_name":
            session["step"] = "collect_first_name"
            self.send_autoreply(phone, "Indica tu nombre (solo nombre).")
            return True

        if step == "ask_shipping":
            if session.get("is_new") and not session.get("customer_id"):
                session["step"] = "collect_last_name"
                self.send_autoreply(phone, "Ahora tus apellidos.")
            else:
                session["step"] = "ask_rut"
                session["customer_id"] = None
                session["rut"] = None
                self.send_autoreply(
                    phone,
                    "📝 Envíame tu RUT\n"
                    "Ejemplo: 12345678-9",
                )
            return True

        if step == "collect_address":
            session["step"] = "ask_shipping"
            session["delivery_address"] = None
            self.send_autoreply(
                phone,
                "🚚 ¿Cómo deseas recibir tu pedido?",
                buttons=list(self._BTN_SHIPPING),
            )
            return True

        if step == "selecting_products":
            if session.get("shipping_method_id") == 2:
                session["step"] = "collect_address"
                self.send_autoreply(
                    phone,
                    "📍 Indica la dirección completa para el envío:\n"
                    "• Calle y número\n"
                    "• Comuna\n"
                    "• Referencias",
                )
            else:
                session["step"] = "ask_shipping"
                self.send_autoreply(
                    phone,
                    "🚚 ¿Cómo deseas recibir tu pedido?",
                    buttons=list(self._BTN_SHIPPING),
                )
            return True

        if step == "ask_quantity":
            session["step"] = "selecting_products"
            session.pop("pending_product_id", None)
            session.pop("pending_product_name", None)
            self.send_autoreply(
                phone,
                "📦 Indica el producto por nombre:\n" + self._build_product_prompt_text(products),
            )
            return True

        if step == "ask_more":
            session["step"] = "selecting_products"
            self.send_autoreply(
                phone,
                "📦 Indica el producto por nombre:\n" + self._build_product_prompt_text(products),
            )
            return True

        if step == "review_order":
            session["step"] = "ask_more"
            self.send_autoreply(
                phone,
                "🛒 ¿Quieres agregar otro producto?",
                buttons=list(self._BTN_YES_NO_BACK),
            )
            return True

        if step == "choose_document":
            subtotal, shipping_cost, tax, total = self._preview_totals_for_session(session)
            session["step"] = "review_order"
            self.send_autoreply(
                phone,
                self._build_order_review_text(session, subtotal, shipping_cost, tax, total),
                buttons=list(self._BTN_ORDER_REVIEW),
            )
            return True

        if step == "choose_payment":
            session["step"] = "choose_document"
            self.send_autoreply(
                phone,
                "📄 Tipo de documento",
                buttons=list(self._BTN_DOC_BACK),
            )
            return True

        return False

    def _handle_budget_flow(self, phone: str, raw_text: str, text: str, session: dict):
        if session.get("processing_budget_email"):
            self._reply_while_processing_budget_email(phone)
            return

        if self._is_back_command(text):
            if self._budget_go_back(phone, session):
                return

        cid = session.get("customer_id")
        products = self._get_public_products(cid)
        products_map = {p["id"]: p for p in products}
        step = session.get("step")

        if step == "budget_selecting_products":
            product_id, err = self._resolve_product_pick_one(raw_text, products)
            if err:
                self.send_autoreply(phone, err)
                return
            p = products_map[product_id]
            session["pending_product_id"] = product_id
            session["pending_product_name"] = p["name"]
            session["step"] = "budget_ask_quantity"
            self.send_autoreply(
                phone,
                f"📦 Producto: {self._clean_text_for_whatsapp(p['name'])}\n"
                f"💰 Precio: {self._format_currency(p['price'])} c/u\n\n"
                "🔢 ¿Cuántas unidades? (envía solo el número)",
            )
            return

        if step == "budget_ask_quantity":
            qty_raw = raw_text.strip()
            if not qty_raw.isdigit():
                self.send_autoreply(phone, "Envía solo la cantidad con un número (ej: 3).")
                return
            quantity = int(qty_raw)
            if quantity <= 0:
                self.send_autoreply(phone, "La cantidad debe ser mayor a cero.")
                return
            product_id = session.get("pending_product_id")
            if not product_id or product_id not in products_map:
                session["step"] = "budget_selecting_products"
                session.pop("pending_product_id", None)
                self.send_autoreply(
                    phone,
                    "Elige el producto de nuevo.\n" + self._build_product_prompt_text(products),
                )
                return
            p = products_map[product_id]
            if product_id not in session["cart"]:
                session["cart"][product_id] = {
                    "id": product_id,
                    "name": p["name"],
                    "price": p["price"],
                    "quantity": 0,
                }
            session["cart"][product_id]["quantity"] += quantity
            session.pop("pending_product_id", None)
            session["step"] = "budget_ask_more"
            self.send_autoreply(
                phone,
                f"✅ Agregado: {self._clean_text_for_whatsapp(p['name'])} x {quantity}\n\n"
                "🛒 ¿Agregar otro producto?",
                buttons=list(self._BTN_YES_NO_BACK),
            )
            return

        if step == "budget_ask_more":
            if text.strip() == "1":
                session["step"] = "budget_selecting_products"
                self.send_autoreply(
                    phone,
                    "Indica otro producto por nombre:\n" + self._build_product_prompt_text(products),
                )
                return
            if text.strip() == "2":
                if not session.get("cart"):
                    session["step"] = "budget_selecting_products"
                    self.send_autoreply(
                        phone,
                        "Tu lista está vacía.\n" + self._build_product_prompt_text(products),
                    )
                    return
                subtotal, tax, total = self._preview_budget_cart_only_totals(session)
                session["step"] = "budget_ask_shipping"
                self.send_autoreply(
                    phone,
                    "📋 Resumen (sin envío aún):\n"
                    f"📦 Productos: {self._format_currency(subtotal)}\n"
                    f"📊 IVA: {self._format_currency(tax)}\n"
                    f"💰 Total estimado: {self._format_currency(total)}\n\n"
                    "🚚 ¿Envío a domicilio o retiro en tienda?",
                    buttons=list(self._BTN_SHIPPING),
                )
                return
            self.send_autoreply(
                phone,
                "⚠️ Elige una opción",
                buttons=list(self._BTN_YES_NO_BACK),
            )
            return

        if step == "budget_ask_shipping":
            choice = text.strip()
            if choice in ["1", "1)", "sin envio", "sin envío", "retiro", "sin envío (retiro en tienda)"]:
                session["shipping_method_id"] = 1
                session["delivery_address"] = "Retiro en tienda / sin envío"
                session["step"] = "budget_collect_email"
                self.send_autoreply(
                    phone,
                    "✅ Perfecto, sin envío (retiro en tienda)\n\n"
                    "📧 Indica tu correo electrónico para el presupuesto\n"
                    "Ejemplo: nombre@correo.cl",
                )
                return
            if choice in ["2", "2)", "con envio", "con envío", "envio", "envío", "domicilio", "delivery"]:
                session["shipping_method_id"] = 2
                session["step"] = "budget_collect_address"
                self.send_autoreply(
                    phone,
                    "🚚 Con envío a domicilio\n\n"
                    "📍 Indica la dirección completa:\n"
                    "• Calle y número\n"
                    "• Comuna\n"
                    "• Referencias\n\n"
                    "Después te pediremos tu correo.",
                )
                return
            self.send_autoreply(
                phone,
                "🚚 ¿Envío a domicilio o retiro en tienda?",
                buttons=list(self._BTN_SHIPPING),
            )
            return

        if step == "budget_collect_address":
            addr_err = self._delivery_address_user_error(raw_text)
            if addr_err:
                self.send_autoreply(phone, addr_err)
                return
            session["delivery_address"] = raw_text.strip()
            session["step"] = "budget_collect_email"
            self.send_autoreply(
                phone,
                "✅ Dirección registrada\n\n"
                "📧 Indica tu correo electrónico para el presupuesto\n"
                "Ejemplo: nombre@correo.cl",
            )
            return

        if step == "budget_collect_email":
            addr = raw_text.strip()
            if not self._looks_like_email(addr):
                self.send_autoreply(
                    phone,
                    "⚠️ No reconozco un correo válido\n\n"
                    "📧 Envíalo así: nombre@dominio.com",
                )
                return
            session["budget_contact_email"] = addr
            session["customer_id"] = None
            session["processing_budget_email"] = True
            try:
                res = self._create_budget_from_whatsapp_session(phone, session)
                if not res.get("ok"):
                    self.send_autoreply(
                        phone,
                        "❌ No pude registrar el presupuesto\n\n"
                        "⏳ Intenta más tarde o escribe Hola",
                    )
                    self._chat_sessions.pop(phone, None)
                    return

                bid = res["budget_id"]
                total = res.get("total", 0)
                contact_email = (session.get("budget_contact_email") or "").strip()
                send_res = (
                    self._send_budget_pdf_email(
                        contact_email,
                        bid,
                        "",
                        session.get("delivery_address"),
                    )
                    if contact_email
                    else "email_error"
                )

                if send_res == "ok":
                    session["pending_budget_id"] = bid
                    session["step"] = "budget_ask_accept_reject"
                    self.send_autoreply(
                        phone,
                        "📧 Presupuesto enviado a tu correo\n\n"
                        f"📄 Revisa tu correo ({contact_email}); va el PDF adjunto\n"
                        f"📋 N° {bid} · 💰 Total: {self._format_currency(total)}\n\n"
                        "❓ ¿Aceptas este presupuesto?",
                        buttons=list(self._BTN_BUDGET_ACCEPT),
                    )
                    return
                elif send_res == "no_pdf":
                    self.send_autoreply(
                        phone,
                        f"✅ Tu presupuesto quedó registrado\n"
                        f"📋 N° {bid} · 💰 Total: {self._format_currency(total)}\n\n"
                        "⚠️ No se pudo generar el PDF; te contactaremos por este chat."
                        + self._farewell_after_budget_text(),
                    )
                elif send_res == "pdf_error":
                    self.send_autoreply(
                        phone,
                        f"✅ Tu presupuesto quedó registrado\n"
                        f"📋 N° {bid} · 💰 Total: {self._format_currency(total)}\n\n"
                        "⚠️ Hubo un error al generar el PDF; te escribimos por WhatsApp."
                        + self._farewell_after_budget_text(),
                    )
                else:
                    self.send_autoreply(
                        phone,
                        f"✅ Tu presupuesto quedó registrado\n"
                        f"📋 N° {bid} · 💰 Total: {self._format_currency(total)}\n\n"
                        f"⚠️ No se pudo enviar el correo con el PDF ({send_res})\n"
                        "Te contactamos por aquí."
                        + self._farewell_after_budget_text(),
                    )
                self._chat_sessions.pop(phone, None)
                return
            finally:
                session["processing_budget_email"] = False

        if step == "budget_accept_choose_payment":
            t = text.strip().lower()
            if t in ("1", "efectivo"):
                pay_choice = "1"
            elif t in ("2", "transferencia"):
                pay_choice = "2"
            else:
                self.send_autoreply(
                    phone,
                    "⚠️ Elige método de pago",
                    buttons=list(self._BTN_PAY_BACK),
                )
                return
            fin = self._finalize_budget_accept_sale(phone, session, pay_choice)
            if not fin.get("ok"):
                self.send_autoreply(
                    phone,
                    f"No pude crear el pedido: {fin.get('error', 'error desconocido')}",
                )
                self._chat_sessions.pop(phone, None)
                return

            sale_id = fin["sale_id"]
            is_transfer = pay_choice == "2"
            doc_label = "Boleta" if session.get("document_type_id") == 39 else "Factura"
            pay_label = "Transferencia" if is_transfer else "Efectivo"
            ship_note = ""
            if fin.get("shipping_cost"):
                ship_note = f"🚚 Envío: {self._format_currency(fin['shipping_cost'])}\n"

            msg = (
                f"🎉 ¡Pedido #{sale_id} creado!\n\n"
                f"📄 Documento: {doc_label}\n"
                f"💳 Método de pago: {pay_label}\n"
                f"{ship_note}"
                f"💰 Total: {self._format_currency(fin['total'])}\n\n"
                "⏳ Queda en revisión de pago hasta confirmarlo en el sistema."
            )
            if is_transfer:
                msg += (
                    "\n\n📸 *Envía una foto* del comprobante de transferencia para registrarlo en tu pedido.\n\n"
                )
                msg += self._build_payment_info_text()
                session["step"] = "budget_await_transfer_proof"
                session["await_transfer_proof_sale_id"] = sale_id
                session["flow"] = "budget"
                self.send_autoreply(phone, msg)
                return

            msg += self._farewell_after_purchase_text()
            self.send_autoreply(phone, msg)
            self._chat_sessions.pop(phone, None)
            return

        if step == "budget_accept_choose_document":
            choice = text.strip().lower()
            if choice in ("1", "boleta"):
                session["document_type_id"] = 39
            elif choice in ("2", "factura"):
                session["document_type_id"] = 33
            else:
                self.send_autoreply(
                    phone,
                    "⚠️ Elige documento",
                    buttons=list(self._BTN_DOC_BACK),
                )
                return

            bid = session.get("pending_budget_id")
            b = self.db.query(BudgetModel).filter(BudgetModel.id == bid).first() if bid else None
            if not b:
                self._chat_sessions.pop(phone, None)
                self.send_autoreply(
                    phone,
                    "⚠️ No encontré el presupuesto\n\n"
                    "👋 Escribe Hola para comenzar de nuevo"
                )
                return

            subtotal = int(b.subtotal or 0)
            ship = int(b.shipping or 0)
            tax = int(b.tax or 0)
            total = int(b.total or 0)
            session["step"] = "budget_accept_choose_payment"
            doc_label = "Boleta" if session["document_type_id"] == 39 else "Factura"
            ship_line = ""
            if ship > 0:
                ship_line = f"🚚 Envío: {self._format_currency(ship)}\n"
            self.send_autoreply(
                phone,
                "Último paso: elige pago y generamos tu pedido.\n\n"
                f"📄 Documento: {doc_label}\n"
                f"📦 Productos: {self._format_currency(subtotal)}\n"
                f"{ship_line}"
                f"📊 IVA: {self._format_currency(tax)}\n"
                f"💰 Total: {self._format_currency(total)}\n\n"
                "💳 Método de pago",
                buttons=list(self._BTN_PAY_BACK),
            )
            return

        if step == "budget_accept_collect_last_name":
            if len(raw_text) < 2:
                self.send_autoreply(phone, "📝 Indica tus apellidos")
                return
            session["last_name"] = raw_text.strip()
            self._create_new_customer_record(session, phone)
            session["budget_accept_doc_from"] = "new"
            session["step"] = "budget_accept_choose_document"
            self.send_autoreply(
                phone,
                "📄 Tipo de documento para tu pedido",
                buttons=list(self._BTN_DOC_BACK),
            )
            return

        if step == "budget_accept_collect_first_name":
            if len(raw_text) < 2:
                self.send_autoreply(phone, "📝 Indica tu nombre")
                return
            session["first_name"] = raw_text.strip()
            session["step"] = "budget_accept_collect_last_name"
            self.send_autoreply(phone, "📝 Ahora tus apellidos")
            return

        if step == "budget_accept_collect_rut":
            rut_norm = self._normalize_rut_chile(raw_text)
            if not rut_norm:
                self.send_autoreply(phone, self._RUT_CHILE_INVALID_MSG)
                return
            session["rut"] = rut_norm
            customer = self._find_customer_by_rut(rut_norm)
            if customer:
                session["customer_id"] = customer.id
                session["is_new"] = False
                self._sync_customer_whatsapp_phone(customer, phone)
                if session.get("shipping_method_id") == 2 and session.get("delivery_address"):
                    cust = self.db.query(CustomerModel).filter(CustomerModel.id == customer.id).first()
                    if cust:
                        cust.address = session["delivery_address"]
                        cust.updated_date = datetime.now()
                        self.db.commit()
                session["budget_accept_doc_from"] = "rut"
                session["step"] = "budget_accept_choose_document"
                self.send_autoreply(
                    phone,
                    "✅ Cliente encontrado.\n\n"
                    "Siguiente: tipo de documento y método de pago. "
                    "Al confirmar el pago se crea tu pedido.\n\n"
                    "📄 Tipo de documento",
                    buttons=list(self._BTN_DOC_BACK),
                )
                return
            session["is_new"] = True
            session["customer_id"] = None
            session["step"] = "budget_accept_collect_first_name"
            self.send_autoreply(
                phone,
                f"📝 No tenemos el RUT {rut_norm} registrado\n\n"
                "Indica tu nombre (solo nombre).",
            )
            return

        if step == "budget_ask_accept_reject":
            choice = text.strip()
            bid = session.get("pending_budget_id")
            if not bid:
                self._chat_sessions.pop(phone, None)
                self.send_autoreply(
                    phone,
                    "⏰ Sesión expirada\n\n"
                    "👋 Escribe Hola para comenzar de nuevo"
                )
                return

            if choice == "1":
                session["step"] = "budget_accept_collect_rut"
                self.send_autoreply(
                    phone,
                    "📝 Para crear tu pedido, envíame tu RUT\n"
                    "Ejemplo: 12345678-9\n\n"
                    "Si no estás registrado, te pediremos nombre y apellidos.\n"
                    "Después: documento → pago → se confirma el pedido.",
                )
                return
            elif choice == "2":
                budget = self.db.query(BudgetModel).filter(BudgetModel.id == bid).first()
                if budget:
                    budget.status_id = 2
                    self.db.commit()
                self.send_autoreply(
                    phone,
                    "❌ Hemos recibido el rechazo del presupuesto\n\n"
                    "🙏 Gracias por tu respuesta."
                    + self._farewell_after_budget_text(),
                )
                self._chat_sessions.pop(phone, None)
                return
            else:
                self.send_autoreply(
                    phone,
                    "⚠️ Elige una opción",
                    buttons=list(self._BTN_BUDGET_ACCEPT),
                )
                return

        self.send_autoreply(phone, "👋 Escribe Hola para comenzar de nuevo.")
        return

    def _handle_text_flow(self, message: dict):
        phone = message.get("from")
        if not phone:
            return

        raw_text = (self._extract_message_text(message) or "").strip()
        text = raw_text.lower()
        session = self._chat_sessions.get(phone)

        if session is not None:
            step = session.get("step")
            if isinstance(step, str) and step.startswith("budget_"):
                # Si el paso es de presupuesto, el flujo debe ser budget (evita que flow=None se fuerce a "order"
                # y se pierdan budget_accept_* sin respuesta).
                session["flow"] = "budget"
            elif session.get("flow") is None and step != "main_menu":
                session["flow"] = "order"

        if self._is_exit_command(text):
            self._chat_sessions.pop(phone, None)
            self.send_autoreply(
                phone,
                "✅ Conversación finalizada.\n\n"
                "👋 ¡Hasta pronto! Escribe Hola cuando quieras volver.",
            )
            return

        if text in [
            "hola",
            "inicio",
            "start",
            "menu",
            "comprar",
            "buenos dias",
            "buenas",
            "hey",
        ]:
            self._chat_sessions[phone] = self._new_session_dict()
            self.send_autoreply(
                phone,
                "👋 ¡Hola! ¿En qué te ayudamos?",
                buttons=list(self._BTN_MAIN_MENU),
            )
            return

        if not session:
            self._chat_sessions[phone] = self._new_session_dict()
            self.send_autoreply(
                phone,
                "👋 Elige una opción",
                buttons=list(self._BTN_MAIN_MENU),
            )
            return

        if session.get("step") in ("order_await_transfer_proof", "budget_await_transfer_proof"):
            self.send_autoreply(
                phone,
                "📸 Envía una *foto* del comprobante de transferencia.\n\n"
                "Para volver al menú, escribe Hola.",
            )
            return

        if session["step"] == "main_menu":
            if self._is_back_command(text):
                self.send_autoreply(
                    phone,
                    "ℹ️ Ya estás en el menú principal",
                    buttons=list(self._BTN_MAIN_MENU),
                )
                return
            choice = text.strip()
            if choice == "1":
                session["flow"] = "order"
                session["step"] = "ask_rut"
                session["cart"] = {}
                session["rut"] = None
                session["customer_id"] = None
                session["is_new"] = False
                session["first_name"] = ""
                session["last_name"] = ""
                session["shipping_method_id"] = None
                session["delivery_address"] = None
                session["document_type_id"] = None
                self.send_autoreply(
                    phone,
                    "📦 Pedido / compra\n\n"
                    "📝 Envíame tu RUT (ej: 12345678-9).\n"
                    "Si no estás registrado, te pediremos tus datos después.",
                )
                return
            if choice == "2":
                session["flow"] = "budget"
                session["step"] = "budget_selecting_products"
                session["cart"] = {}
                session["rut"] = None
                session["customer_id"] = None
                session["is_new"] = False
                session["first_name"] = ""
                session["last_name"] = ""
                session["shipping_method_id"] = None
                session["delivery_address"] = None
                session["document_type_id"] = None
                session["budget_contact_email"] = None
                session["processing_budget_email"] = False
                self.send_autoreply(
                    phone,
                    "💰 Solicitud de presupuesto\n\n" + self._build_product_prompt_text(self._get_public_products(None)),
                )
                return
            self.send_autoreply(
                phone,
                "⚠️ Elige una opción",
                buttons=list(self._BTN_MAIN_MENU),
            )
            return

        if session.get("flow") == "budget":
            self._handle_budget_flow(phone, raw_text, text, session)
            return

        products = self._get_public_products(session.get("customer_id"))
        products_map = {p["id"]: p for p in products}

        if self._is_back_command(text):
            if self._order_go_back(phone, session):
                return

        if session["step"] == "ask_rut":
            rut_norm = self._normalize_rut_chile(raw_text)
            if not rut_norm:
                self.send_autoreply(phone, self._RUT_CHILE_INVALID_MSG)
                return
            session["rut"] = rut_norm
            customer = self._find_customer_by_rut(rut_norm)
            if customer:
                session["customer_id"] = customer.id
                session["is_new"] = False
                self._sync_customer_whatsapp_phone(customer, phone)
                session["step"] = "ask_shipping"
                self.send_autoreply(
                    phone,
                    f"✅ ¡Encontramos tu registro, RUT {rut_norm}!\n\n"
                    "🚚 ¿Cómo deseas recibir tu pedido?",
                    buttons=list(self._BTN_SHIPPING),
                )
                return

            session["is_new"] = True
            session["customer_id"] = None
            session["step"] = "collect_first_name"
            self.send_autoreply(
                phone,
                f"📝 No encontramos el RUT {rut_norm} en nuestro sistema\n\n"
                "Indica tu nombre (solo nombre).",
            )
            return

        if session["step"] == "collect_first_name":
            if len(raw_text) < 2:
                self.send_autoreply(phone, "Por favor indica tu nombre.")
                return
            session["first_name"] = raw_text.strip()
            session["step"] = "collect_last_name"
            self.send_autoreply(phone, "📝 Ahora tus apellidos")
            return

        if session["step"] == "collect_last_name":
            if len(raw_text) < 2:
                self.send_autoreply(phone, "📝 Por favor indica tus apellidos")
                return
            session["last_name"] = raw_text.strip()
            session["step"] = "ask_shipping"
            self.send_autoreply(
                phone,
                "🚚 ¿Cómo deseas recibir tu pedido?",
                buttons=list(self._BTN_SHIPPING),
            )
            return

        if session["step"] == "ask_shipping":
            choice = text.strip()
            if choice in ["1", "1)", "sin envio", "sin envío", "retiro", "sin envío (retiro en tienda)"]:
                session["shipping_method_id"] = 1
                session["delivery_address"] = "Retiro en tienda / sin envío"
                if session.get("is_new") and not session.get("customer_id"):
                    self._create_new_customer_record(session, phone)
                session["step"] = "selecting_products"
                self.send_autoreply(
                    phone,
                    "✅ Perfecto, sin envío (retiro)\n\n"
                    "📦 Ahora dime qué productos quieres:\n" + self._build_product_prompt_text(products)
                )
                return
            if choice in ["2", "2)", "con envio", "con envío", "envio", "envío", "domicilio", "delivery"]:
                session["shipping_method_id"] = 2
                session["step"] = "collect_address"
                self.send_autoreply(
                    phone,
                    "📍 Indica la dirección completa para el envío:\n"
                    "• Calle y número\n"
                    "• Comuna\n"
                    "• Referencias"
                )
                return
            self.send_autoreply(
                phone,
                "⚠️ Elige tipo de entrega",
                buttons=list(self._BTN_SHIPPING),
            )
            return

        if session["step"] == "collect_address":
            addr_err = self._delivery_address_user_error(raw_text)
            if addr_err:
                self.send_autoreply(phone, addr_err)
                return
            session["delivery_address"] = raw_text.strip()
            if session.get("is_new") and not session.get("customer_id"):
                self._create_new_customer_record(session, phone)
            else:
                cust = self.db.query(CustomerModel).filter(CustomerModel.id == session.get("customer_id")).first()
                if cust:
                    cust.address = session["delivery_address"]
                    cust.updated_date = datetime.now()
                    self.db.commit()
            session["step"] = "selecting_products"
            self.send_autoreply(
                phone,
                "✅ Dirección registrada\n\n"
                "📦 Ahora tus productos:\n" + self._build_product_prompt_text(products)
            )
            return

        if session["step"] == "selecting_products":
            product_id, err = self._resolve_product_pick_one(raw_text, products)
            if err:
                self.send_autoreply(phone, err)
                return

            p = products_map[product_id]
            session["pending_product_id"] = product_id
            session["pending_product_name"] = p["name"]
            session["step"] = "ask_quantity"
            self.send_autoreply(
                phone,
                f"📦 Producto: {self._clean_text_for_whatsapp(p['name'])}\n"
                f"💰 Precio: {self._format_currency(p['price'])} c/u\n\n"
                "🔢 ¿Cuántas unidades quieres? (envía solo el número)",
            )
            return

        if session["step"] == "ask_quantity":
            qty_raw = raw_text.strip()
            if not qty_raw.isdigit():
                self.send_autoreply(phone, "Envía solo la cantidad con un número (ej: 3).")
                return
            quantity = int(qty_raw)
            if quantity <= 0:
                self.send_autoreply(phone, "La cantidad debe ser mayor a cero.")
                return

            product_id = session.get("pending_product_id")
            if not product_id or product_id not in products_map:
                session["step"] = "selecting_products"
                session.pop("pending_product_id", None)
                session.pop("pending_product_name", None)
                self.send_autoreply(
                    phone,
                    "⚠️ Hubo un problema con el producto\n\n"
                    "🔄 Elige de nuevo:\n" + self._build_product_prompt_text(products)
                )
                return

            p = products_map[product_id]
            if product_id not in session["cart"]:
                session["cart"][product_id] = {
                    "id": product_id,
                    "name": p["name"],
                    "price": p["price"],
                    "quantity": 0
                }
            session["cart"][product_id]["quantity"] += quantity
            session.pop("pending_product_id", None)
            session.pop("pending_product_name", None)
            session["step"] = "ask_more"
            self.send_autoreply(
                phone,
                f"✅ Listo: {self._clean_text_for_whatsapp(p['name'])} x {quantity}\n\n"
                "🛒 ¿Quieres agregar otro producto?",
                buttons=list(self._BTN_YES_NO_BACK),
            )
            return

        if session["step"] == "ask_more":
            if text.strip() == "1":
                session["step"] = "selecting_products"
                self.send_autoreply(
                    phone,
                    "Indica otro producto por nombre:\n" + self._build_product_prompt_text(products)
                )
                return
            if text.strip() == "2":
                if not session.get("cart"):
                    session["step"] = "selecting_products"
                    self.send_autoreply(
                        phone,
                        "⚠️ Tu carrito está vacío\n\n"
                        "📦 Agrega al menos un producto:\n" + self._build_product_prompt_text(products)
                    )
                    return
                subtotal, shipping_cost, tax, total = self._preview_totals_for_session(session)
                session["step"] = "review_order"
                self.send_autoreply(
                    phone,
                    self._build_order_review_text(session, subtotal, shipping_cost, tax, total),
                    buttons=list(self._BTN_ORDER_REVIEW),
                )
                return
            self.send_autoreply(
                phone,
                "⚠️ Elige una opción",
                buttons=list(self._BTN_YES_NO_BACK),
            )
            return

        if session["step"] == "review_order":
            if text.strip() == "1":
                session["step"] = "choose_document"
                self.send_autoreply(
                    phone,
                    "📄 Tipo de documento",
                    buttons=list(self._BTN_DOC_BACK),
                )
                return
            if text.strip() == "2":
                session["step"] = "selecting_products"
                self.send_autoreply(
                    phone,
                    "📦 Agrega otro producto por nombre:\n" + self._build_product_prompt_text(products)
                )
                return
            self.send_autoreply(
                phone,
                "⚠️ Elige una opción",
                buttons=list(self._BTN_ORDER_REVIEW),
            )
            return

        if session["step"] == "choose_document":
            choice = text.strip().lower()
            if choice in ("1", "boleta"):
                session["document_type_id"] = 39
            elif choice in ("2", "factura"):
                session["document_type_id"] = 33
            else:
                self.send_autoreply(
                    phone,
                    "⚠️ Elige documento",
                    buttons=list(self._BTN_DOC_BACK),
                )
                return

            subtotal, shipping_cost, tax, total = self._preview_totals_for_session(session)
            session["step"] = "choose_payment"
            ship_line = ""
            if session.get("shipping_method_id") == 2 and shipping_cost > 0:
                ship_line = f"🚚 Envío: {self._format_currency(shipping_cost)}\n"
            doc_label = "Boleta" if session["document_type_id"] == 39 else "Factura"
            self.send_autoreply(
                phone,
                f"📄 Documento: {doc_label}\n"
                f"📦 Productos: {self._format_currency(subtotal)}\n"
                f"{ship_line}"
                f"📊 IVA: {self._format_currency(tax)}\n"
                f"💰 Total: {self._format_currency(total)}\n\n"
                "💳 Método de pago",
                buttons=list(self._BTN_PAY_BACK),
            )
            return

        if session["step"] == "choose_payment":
            tp = text.strip().lower()
            if tp in ("1", "efectivo"):
                pass
            elif tp in ("2", "transferencia"):
                pass
            else:
                self.send_autoreply(
                    phone,
                    "⚠️ Elige método de pago",
                    buttons=list(self._BTN_PAY_BACK),
                )
                return

            sale_result = self._create_sale_from_session(phone, session)
            if not sale_result["ok"]:
                self.send_autoreply(
                    phone,
                    "❌ No pude crear el pedido\n\n"
                    "⏳ Intenta nuevamente más tarde"
                )
                self._chat_sessions.pop(phone, None)
                return

            sale_id = sale_result["sale_id"]
            is_transfer = tp in ("2", "transferencia")

            sale_row = self.db.query(SaleModel).filter(SaleModel.id == sale_id).first()
            if sale_row:
                sale_row.payment_support = "Transferencia" if is_transfer else "Efectivo"
                sale_row.updated_date = datetime.now()
                self.db.commit()

            ship_note = ""
            if sale_result.get("shipping_cost"):
                ship_note = f"🚚 Envío: {self._format_currency(sale_result['shipping_cost'])}\n"
            doc_label = "Boleta" if session.get("document_type_id") == 39 else "Factura"
            pay_label = "Transferencia" if is_transfer else "Efectivo"

            msg = (
                f"🎉 Pedido #{sale_id} creado\n\n"
                f"📄 Documento: {doc_label}\n"
                f"💳 Método de pago: {pay_label}\n"
                f"{ship_note}"
                f"💰 Total: {self._format_currency(sale_result['total'])}\n\n"
                "⏳ El pedido queda en revisión de pago hasta confirmarlo en el sistema."
            )
            if is_transfer:
                msg += (
                    "\n\n📸 *Envía una foto* del comprobante de transferencia para registrarlo en tu pedido.\n\n"
                )
                msg += self._build_payment_info_text()
                session["step"] = "order_await_transfer_proof"
                session["await_transfer_proof_sale_id"] = sale_id
                session["flow"] = "order"
                self.send_autoreply(phone, msg)
                return

            msg += self._farewell_after_purchase_text()

            self.send_autoreply(phone, msg)
            self._chat_sessions.pop(phone, None)
            return

    def send_dte(self, customer_phone, dte_type, folio, date, amount, dynamic_value, sale_id: int = None): 
        url = "https://graph.facebook.com/v22.0/790586727468909/messages"
        token = os.getenv('META_TOKEN')

        # Formatear el número de teléfono
        customer_phone_formatted = self._clean_phone_number(customer_phone)

        payload = {
            "messaging_product": "whatsapp",
            "to": customer_phone_formatted,
            "type": "template",
            "template": {
                "name": "envio_dte_cliente_generado_v5",  # nombre EXACTO de tu plantilla
                "language": {"code": "es"},
                "components": [
                    {
                        "type": "body",
                        "parameters": [
                            {"type": "text", "text": dte_type}, 
                            {"type": "text", "text": str(folio)},       # N° Boleta/Factura
                            {"type": "text", "text": date},             # Fecha
                            {"type": "text", "text": str(amount)},      # Monto
                        ]
                    },
                    {
                        "type": "button",
                        "sub_type": "url",
                        "index": "0",
                        "parameters": [
                            {
                                "type": "text",
                                "text": str(dynamic_value)  # valor dinámico para {{1}}
                            }
                        ]
                    }
                ]
            }
        }

        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }

        response = requests.post(url, json=payload, headers=headers)

        print(f"[WHATSAPP] Status: {response.status_code}")
        response_data = response.json()
        print(f"[WHATSAPP] Response: {response_data}")
        
        # Guardar el message_id si el envío fue exitoso
        if response.status_code == 200 and "messages" in response_data:
            message_id = response_data["messages"][0].get("id")
            if message_id:
                self._save_message(
                    message_id=message_id,
                    recipient_phone=customer_phone_formatted,
                    message_type="template",
                    template_name="envio_dte_cliente_generado_v5",
                    status="sent",
                    sale_id=sale_id
                )
        
        return response

    def send_new_order_alert(self, customer_name): 
        url = "https://graph.facebook.com/v22.0/790586727468909/messages"
        token = os.getenv('META_TOKEN')        
        setting_data = SettingClass(self.db).get(1)
        admin_phone = setting_data["setting_data"]["phone"]

        # Formatear el número de teléfono
        admin_phone_formatted = self._clean_phone_number(admin_phone) or str(admin_phone).strip()

        payload = {
            "messaging_product": "whatsapp",
            "to": admin_phone_formatted,
            "type": "template",
            "template": {
                "name": "alerta_nueva_orden",
                "language": {"code": "es"},
                "components": [
                    {
                        "type": "body",
                        "parameters": [
                            {"type": "text", "text": customer_name}
                        ]
                    }
                ]
            }
        }

        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }

        response = requests.post(url, json=payload, headers=headers)

        print(f"[WHATSAPP ALERT] Status: {response.status_code}")
        response_data = response.json()
        print(f"[WHATSAPP ALERT] Response: {response_data}")
        
        # Guardar el message_id si el envío fue exitoso
        if response.status_code == 200 and "messages" in response_data:
            message_id = response_data["messages"][0].get("id")
            if message_id:
                self._save_message(
                    message_id=message_id,
                    recipient_phone=admin_phone_formatted,
                    message_type="template",
                    template_name="alerta_nueva_orden",
                    status="sent"
                )
        
        return response

    def send_order_delivered_alert(self, customer_phone, id): 
        url = "https://graph.facebook.com/v22.0/790586727468909/messages"
        token = os.getenv('META_TOKEN')        

        # Formatear el número de teléfono
        customer_phone_formatted = self._clean_phone_number(customer_phone)

        payload = {
            "messaging_product": "whatsapp",
            "to": customer_phone_formatted,
            "type": "template",
            "template": {
                "name": "alerta_pedido_enviado",
                "language": {"code": "es"},
                "components": [
                    {
                        "type": "body",
                        "parameters": [
                            {"type": "text", "text": id}
                        ]
                    }
                ]
            }
        }

        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }

        response = requests.post(url, json=payload, headers=headers)

        print(f"[WHATSAPP ALERT] Status: {response.status_code}")
        response_data = response.json()
        print(f"[WHATSAPP ALERT] Response: {response_data}")
        
        # Guardar el message_id si el envío fue exitoso
        if response.status_code == 200 and "messages" in response_data:
            message_id = response_data["messages"][0].get("id")
            if message_id:
                self._save_message(
                    message_id=message_id,
                    recipient_phone=customer_phone_formatted,
                    message_type="template",
                    template_name="alerta_pedido_enviado",
                    status="sent"
                )
        
        return response

    def send_rejected_payment_alert(self, customer_phone, id): 
        url = "https://graph.facebook.com/v22.0/790586727468909/messages"
        token = os.getenv('META_TOKEN')        

        # Formatear el número de teléfono
        customer_phone_formatted = self._clean_phone_number(customer_phone)

        payload = {
            "messaging_product": "whatsapp",
            "to": customer_phone_formatted,
            "type": "template",
            "template": {
                "name": "alerta_pago_rechazado",
                "language": {"code": "es"},
                "components": [
                    {
                        "type": "body",
                        "parameters": [
                            {"type": "text", "text": id}
                        ]
                    }
                ]
            }
        }

        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }

        response = requests.post(url, json=payload, headers=headers)

        print(f"[WHATSAPP ALERT] Status: {response.status_code}")
        response_data = response.json()
        print(f"[WHATSAPP ALERT] Response: {response_data}")
        
        # Guardar el message_id si el envío fue exitoso
        if response.status_code == 200 and "messages" in response_data:
            message_id = response_data["messages"][0].get("id")
            if message_id:
                self._save_message(
                    message_id=message_id,
                    recipient_phone=customer_phone_formatted,
                    message_type="template",
                    template_name="alerta_pago_rechazado",
                    status="sent"
                )
        
        return response

    

    # ===============================
    # ENVÍO DEL MENSAJE
    # ===============================
    def review_budget(self, budget_id: int, total: int, customer_phone: str = None, customer_name: str = None):

        url = "https://graph.facebook.com/v22.0/790586727468909/messages"
        token = os.getenv("META_TOKEN")

        # Presupuesto
        budget = self.db.query(BudgetModel).filter_by(id=budget_id).first()
        if not budget:
            return None

        # Cliente - Si se proporcionan customer_phone y customer_name, usarlos directamente
        # Si no, buscar en la base de datos
        if customer_phone and customer_name:
            phone = customer_phone
            customer_name_used = customer_name
        else:
            customer = self.db.query(CustomerModel).filter_by(id=budget.customer_id).first()
            if not customer or not customer.phone:
                return None
            phone = customer.phone
            customer_name_used = customer.social_reason

        # Productos
        products = (
            self.db.query(ProductModel.product, BudgetProductModel.quantity)
            .join(BudgetProductModel, BudgetProductModel.product_id == ProductModel.id)
            .filter(BudgetProductModel.budget_id == budget_id)
            .all()
        )

        # Construir texto de productos sin saltos de línea (WhatsApp no los permite)
        # Usar coma y espacio como separador
        products_list = []
        for p in products:
            product_name = self._clean_text_for_whatsapp(p.product)
            products_list.append(f"{product_name} x {p.quantity}")
        
        products_text = ", ".join(products_list)

        total_formatted = f"{total:,}".replace(",", ".")

        # Limpiar y formatear el número de teléfono
        phone = self._clean_phone_number(phone)

        payload = {
            "messaging_product": "whatsapp",
            "to": phone,
            "type": "template",
            "template": {
                "name": "revision_presupuesto",
                "language": {"code": "es"},
                "components": [
                    {
                        "type": "body",
                        "parameters": [
                            {"type": "text", "text": str(budget_id)},
                            {"type": "text", "text": total_formatted},
                            {"type": "text", "text": products_text}
                        ]
                    },
                    {
                        "type": "button",
                        "sub_type": "quick_reply",
                        "index": "0",
                        "parameters": [
                            {"type": "payload", "payload": f"accept_{budget_id}"}
                        ]
                    },
                    {
                        "type": "button",
                        "sub_type": "quick_reply",
                        "index": "1",
                        "parameters": [
                            {"type": "payload", "payload": f"reject_{budget_id}"}
                        ]
                    }
                ]
            }
        }

        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }

        response = requests.post(url, json=payload, headers=headers)
        response_data = response.json()
        print(f"[WHATSAPP] Response: {response_data}")
        
        # Guardar el message_id si el envío fue exitoso
        if response.status_code == 200 and "messages" in response_data:
            message_id = response_data["messages"][0].get("id")
            if message_id:
                self._save_message(
                    message_id=message_id,
                    recipient_phone=phone,
                    message_type="template",
                    template_name="revision_presupuesto",
                    status="sent",
                    budget_id=budget_id
                )
        
        return response

    def handle_message(self, message):
        print("📩 MENSAJE:", message)
        print(f"[WHATSAPP_HANDLE] Tipo de mensaje: {message.get('type')}")

        if message.get("type") == "button":
            payload = message.get("button", {}).get("payload")  # accept_38
            phone = message.get("from")
            print(f"[WHATSAPP_HANDLE] Payload recibido: {payload}, Phone: {phone}")

            if not payload or "_" not in payload:
                print(f"[WHATSAPP_HANDLE] Payload inválido o sin '_': {payload}")
                return

            action, budget_id = payload.split("_", 1)
            action = action.lower()
            print(f"[WHATSAPP_HANDLE] Action: {action}, Budget ID: {budget_id}")
        elif message.get("type") == "image":
            self._handle_transfer_proof_image_message(message)
            return
        elif message.get("type") in ["text", "interactive"]:
            self._handle_text_flow(message)
            return
        else:
            print(f"[WHATSAPP_HANDLE] Tipo de mensaje no soportado: {message.get('type')}")
            return

        budget = (
            self.db
            .query(BudgetModel)
            .filter(BudgetModel.id == int(budget_id))
            .first()
        )

        if not budget:
            print("⚠️ Presupuesto no existe (reintento ignorado)")
            return {"status": "ignored"}

        # 🔒 Ya procesado - pero si es accept y ya está aceptado, no hacer nada
        # Si es reject y ya está rechazado, tampoco hacer nada
        if action == "accept" and budget.status_id == 1:
            print(f"[WHATSAPP] Presupuesto {budget_id} ya está aceptado, no hacer nada")
            self.send_autoreply(
                phone,
                "⚠️ Este presupuesto ya fue aceptado anteriormente."
            )
            return

        if action == "reject" and budget.status_id == 2:
            print(f"[WHATSAPP] Presupuesto {budget_id} ya está rechazado, no hacer nada")
            self.send_autoreply(
                phone,
                "⚠️ Este presupuesto ya fue rechazado anteriormente."
            )
            return

        if action == "accept":
            print(f"[WHATSAPP] Procesando aceptación de presupuesto {budget_id} desde WhatsApp")
            # Llamar al método accept de BudgetClass para crear el pedido
            from app.backend.classes.budget_class import BudgetClass
            budget_class = BudgetClass(self.db)
            print(f"[WHATSAPP] Llamando a BudgetClass.accept({budget_id})")
            accept_result = budget_class.accept(int(budget_id))
            print(f"[WHATSAPP] Resultado de accept: {accept_result}")
            
            if isinstance(accept_result, dict) and accept_result.get("status") == "error":
                print(f"❌ Error al aceptar presupuesto {budget_id}: {accept_result.get('message')}")
                self.send_autoreply(
                    phone,
                    f"❌ Ocurrió un error al procesar la aceptación del presupuesto:\n{accept_result.get('message')}"
                )
            else:
                sale_id = accept_result.get('sale_id') if isinstance(accept_result, dict) else 'N/A'
                print(f"[WHATSAPP] ✅ Presupuesto {budget_id} aceptado exitosamente. Sale ID: {sale_id}")
                self.send_autoreply(
                    phone,
                    "✅ Gracias por aceptar el presupuesto.\nNos pondremos en contacto contigo a la brevedad."
                )

        elif action == "reject":
            budget.status_id = 2
            self.db.commit()

            self.send_autoreply(
                phone,
                "❌ Hemos recibido el rechazo del presupuesto.\nGracias por tu respuesta."
            )

            print(f"❌ Presupuesto {budget_id} rechazado")

    def handle_status(self, status: dict):
        """
        Maneja estados enviados por WhatsApp:
        sent, delivered, read, failed
        """
        try:
            print("📬 STATUS WHATSAPP RECIBIDO")
            print(f"📬 Status completo: {status}")

            status_type = status.get("status")
            message_id = status.get("id", "").strip()
            recipient = status.get("recipient_id")
            error = status.get("errors", [])
            error_code = error[0].get("code") if error and len(error) > 0 else None
            error_message = error[0].get("message") if error and len(error) > 0 else None

            print(f"➡ Estado: {status_type}")
            print(f"➡ Message ID: '{message_id}' (tipo: {type(message_id)})")
            print(f"➡ Destinatario: {recipient}")
            if error_code:
                print(f"➡ Error Code: {error_code}")
                print(f"➡ Error Message: {error_message}")

            # Validar que tenemos message_id
            if not message_id:
                print("⚠️ ERROR: No se recibió message_id en el status")
                return

            # Buscar el mensaje en la BD por message_id
            print(f"🔍 Buscando mensaje con message_id: '{message_id}'")
            whatsapp_message = (
                self.db.query(WhatsAppMessageModel)
                .filter(WhatsAppMessageModel.message_id == message_id)
                .first()
            )

            if whatsapp_message:
                print(f"✅ Mensaje encontrado en BD (ID: {whatsapp_message.id})")
                print(f"   Estado actual: {whatsapp_message.status}")
                print(f"   Nuevo estado: {status_type}")
                
                # Definir orden de estados (mayor número = estado más avanzado)
                status_order = {
                    "sent": 1,
                    "delivered": 2,
                    "read": 3,
                    "failed": 0  # failed puede ocurrir en cualquier momento
                }
                
                current_order = status_order.get(whatsapp_message.status, 0)
                new_order = status_order.get(status_type, 0)
                
                print(f"   📊 Comparación: Estado actual '{whatsapp_message.status}' (orden: {current_order}) vs nuevo '{status_type}' (orden: {new_order})")
                print(f"   📅 Fechas actuales - sent_date: {whatsapp_message.sent_date}, delivered_date: {whatsapp_message.delivered_date}, read_date: {whatsapp_message.read_date}")
                print(f"   🔍 Debug: new_order > current_order = {new_order > current_order}, new_order == current_order = {new_order == current_order}, new_order < current_order = {new_order < current_order}")
                
                # No permitir que un estado anterior sobrescriba uno posterior
                # Excepto para "failed" que siempre se debe actualizar
                if status_type == "failed":
                    # Siempre actualizar si es failed
                    whatsapp_message.status = status_type
                    whatsapp_message.updated_date = datetime.utcnow()
                    whatsapp_message.error_code = str(error_code) if error_code else None
                    whatsapp_message.error_message = error_message
                    print(f"   ❌ Actualizado a failed (siempre se actualiza)")
                elif new_order > current_order:
                    # Solo actualizar si el nuevo estado es más avanzado
                    print(f"   ✅ Actualizando: nuevo estado es más avanzado")
                    whatsapp_message.status = status_type
                    whatsapp_message.updated_date = datetime.utcnow()

                    if status_type == "sent":
                        if not whatsapp_message.sent_date:
                            whatsapp_message.sent_date = datetime.utcnow()
                            print(f"   📤 Actualizado sent_date")
                        else:
                            print(f"   📤 sent_date ya existía, solo actualizando estado")
                    elif status_type == "delivered":
                        if not whatsapp_message.delivered_date:
                            whatsapp_message.delivered_date = datetime.utcnow()
                            print(f"   📬 Actualizado delivered_date")
                        else:
                            print(f"   📬 delivered_date ya existía, solo actualizando estado")
                    elif status_type == "read":
                        if not whatsapp_message.read_date:
                            whatsapp_message.read_date = datetime.utcnow()
                            print(f"   👁️ Actualizado read_date")
                        else:
                            print(f"   👁️ read_date ya existía, solo actualizando estado")
                elif new_order == current_order:
                    # Mismo estado, verificar si falta alguna fecha y actualizarla
                    print(f"   ⚠️ Mismo estado, verificando fechas...")
                    updated = False
                    
                    if status_type == "sent":
                        if not whatsapp_message.sent_date:
                            whatsapp_message.sent_date = datetime.utcnow()
                            updated = True
                            print(f"   📤 Actualizado sent_date (faltaba)")
                        else:
                            print(f"   📤 sent_date ya existe: {whatsapp_message.sent_date}")
                    elif status_type == "delivered":
                        if not whatsapp_message.delivered_date:
                            whatsapp_message.delivered_date = datetime.utcnow()
                            updated = True
                            print(f"   📬 Actualizado delivered_date (faltaba)")
                        else:
                            print(f"   📬 delivered_date ya existe: {whatsapp_message.delivered_date}")
                    elif status_type == "read":
                        if not whatsapp_message.read_date:
                            whatsapp_message.read_date = datetime.utcnow()
                            updated = True
                            print(f"   👁️ Actualizado read_date (faltaba)")
                        else:
                            print(f"   👁️ read_date ya existe: {whatsapp_message.read_date}")
                    
                    if updated:
                        whatsapp_message.updated_date = datetime.utcnow()
                        print(f"   ✅ Fecha actualizada aunque el estado sea el mismo")
                    else:
                        print(f"   ⚠️ Ignorado: Estado '{status_type}' es el mismo y todas las fechas ya existen")
                        return
                else:
                    print(f"   ⚠️ Ignorado: Estado '{status_type}' no es más avanzado que '{whatsapp_message.status}' (orden actual: {current_order}, nuevo: {new_order})")
                    # No hacer commit si no hay cambios
                    return

                try:
                    self.db.commit()
                    print(f"✅ Estado actualizado en BD: {status_type} para mensaje {message_id}")
                except Exception as commit_error:
                    print(f"❌ ERROR al hacer commit: {str(commit_error)}")
                    self.db.rollback()
                    raise
            else:
                print(f"⚠️ Mensaje NO encontrado en BD con message_id: '{message_id}'")
                print(f"   Buscando todos los message_id en BD para comparar...")
                all_messages = self.db.query(WhatsAppMessageModel.message_id).all()
                print(f"   Total de mensajes en BD: {len(all_messages)}")
                if all_messages:
                    print(f"   Primeros 5 message_id en BD: {[m[0] for m in all_messages[:5]]}")
                
                # Si no existe, crear un nuevo registro (puede pasar si el webhook llega antes de guardar)
                print(f"   Creando nuevo registro...")
                new_message = WhatsAppMessageModel(
                    message_id=message_id,
                    recipient_phone=recipient,
                    status=status_type,
                    error_code=str(error_code) if error_code else None,
                    error_message=error_message,
                    sent_date=datetime.now() if status_type == "sent" else None,
                    delivered_date=datetime.now() if status_type == "delivered" else None,
                    read_date=datetime.now() if status_type == "read" else None
                )
                self.db.add(new_message)
                try:
                    self.db.commit()
                    print(f"✅ Nuevo registro creado para mensaje {message_id} con estado {status_type}")
                except Exception as commit_error:
                    print(f"❌ ERROR al crear nuevo registro: {str(commit_error)}")
                    self.db.rollback()
                    raise
                    
        except Exception as e:
            print(f"❌ ERROR en handle_status: {str(e)}")
            import traceback
            traceback.print_exc()
            self.db.rollback()

    def send_autoreply(self, phone: str, text: str, buttons=None):
        """
        Envía texto plano o mensaje interactivo con botones de respuesta (máx. 3).
        `buttons`: lista de tuplas (id, título_visible); el id es lo que recibimos al pulsar
        (p. ej. "1", "2", "volver", "salir") para no romper la lógica existente.
        """
        url = "https://graph.facebook.com/v22.0/790586727468909/messages"
        token = os.getenv("META_TOKEN")

        # Normalizar número (respeta números internacionales)
        phone = self._clean_phone_number(phone) or phone

        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        }

        response = None
        message_type_saved = "text"

        if buttons:
            btn_payload = []
            for bid, title in buttons[:3]:
                tid = str(bid)[:256]
                ttl = self._reply_button_title(title or tid)
                if not ttl:
                    ttl = str(tid)[:20]
                btn_payload.append(
                    {"type": "reply", "reply": {"id": tid, "title": ttl}}
                )
            body_text = (text or "")[:1024]
            payload = {
                "messaging_product": "whatsapp",
                "to": phone,
                "type": "interactive",
                "interactive": {
                    "type": "button",
                    "body": {"text": body_text},
                    "action": {"buttons": btn_payload},
                },
            }
            response = requests.post(url, json=payload, headers=headers)
            print("📨 AUTORESPONDER (interactive):", response.status_code, response.json())
            message_type_saved = "interactive"
            if response.status_code != 200:
                buttons = None

        if not buttons:
            payload = {
                "messaging_product": "whatsapp",
                "to": phone,
                "type": "text",
                "text": {"body": text},
            }
            response = requests.post(url, json=payload, headers=headers)
            print("📨 AUTORESPONDER:", response.status_code, response.json())
            message_type_saved = "text"

        if response.status_code == 200:
            response_data = response.json()
            if "messages" in response_data:
                message_id = response_data["messages"][0].get("id")
                if message_id:
                    self._save_message(
                        message_id=message_id,
                        recipient_phone=phone,
                        message_type=message_type_saved,
                        status="sent",
                    )

    def _save_message(self, message_id: str, recipient_phone: str, message_type: str, template_name: str = None, status: str = "sent", budget_id: int = None, sale_id: int = None):
        """
        Guarda un mensaje de WhatsApp en la BD
        """
        try:
            # Verificar si ya existe
            existing = (
                self.db.query(WhatsAppMessageModel)
                .filter(WhatsAppMessageModel.message_id == message_id)
                .first()
            )
            
            if existing:
                # Actualizar si ya existe
                existing.status = status
                existing.updated_date = datetime.now()
                if budget_id is not None:
                    existing.budget_id = budget_id
                if sale_id is not None:
                    existing.sale_id = sale_id
                # Si el estado es "sent" y no tiene sent_date, actualizarlo
                if status == "sent" and not existing.sent_date:
                    existing.sent_date = datetime.utcnow()
            else:
                # Crear nuevo registro
                whatsapp_message = WhatsAppMessageModel(
                    message_id=message_id,
                    recipient_phone=recipient_phone,
                    message_type=message_type,
                    template_name=template_name,
                    budget_id=budget_id,
                    sale_id=sale_id,
                    status=status,
                    sent_date=datetime.utcnow() if status == "sent" else None
                )
                self.db.add(whatsapp_message)
            
            self.db.commit()
            print(f"✅ Mensaje guardado/actualizado en BD: {message_id} (budget_id: {budget_id}, sale_id: {sale_id})")
        except Exception as e:
            print(f"❌ Error guardando mensaje en BD: {str(e)}")
            self.db.rollback()

    def get_messages_by_budget(self, budget_id: int):
        """
        Obtiene todos los mensajes de WhatsApp relacionados con un presupuesto
        """
        messages = (
            self.db.query(WhatsAppMessageModel)
            .filter(WhatsAppMessageModel.budget_id == budget_id)
            .order_by(WhatsAppMessageModel.added_date.desc())
            .all()
        )
        return messages

    def get_messages_by_sale(self, sale_id: int):
        """
        Obtiene todos los mensajes de WhatsApp relacionados con una venta
        """
        messages = (
            self.db.query(WhatsAppMessageModel)
            .filter(WhatsAppMessageModel.sale_id == sale_id)
            .order_by(WhatsAppMessageModel.added_date.desc())
            .all()
        )
        return messages

    def get_message_by_id(self, message_id: str):
        """
        Obtiene un mensaje por su message_id de WhatsApp
        """
        message = (
            self.db.query(WhatsAppMessageModel)
            .filter(WhatsAppMessageModel.message_id == message_id)
            .first()
        )
        return message

    def get_all_messages(self, budget_id: int = None, sale_id: int = None, status: str = None, limit: int = 100):
        """
        Obtiene todos los mensajes con filtros opcionales
        """
        query = self.db.query(WhatsAppMessageModel)
        
        if budget_id:
            query = query.filter(WhatsAppMessageModel.budget_id == budget_id)
        if sale_id:
            query = query.filter(WhatsAppMessageModel.sale_id == sale_id)
        if status:
            query = query.filter(WhatsAppMessageModel.status == status)
        
        messages = query.order_by(WhatsAppMessageModel.added_date.desc()).limit(limit).all()
        return messages
