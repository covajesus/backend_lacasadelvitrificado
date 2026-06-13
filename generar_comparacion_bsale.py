"""Genera PDF con comparación de costos: Sistema propio vs Bsale Omnicanal."""

from fpdf import FPDF
from datetime import date

OUTPUT = r"c:\Users\jesus\Desktop\proyecto_lacasadelvitrificado\Comparacion_Bsale_vs_Sistema_Propio.pdf"

# Costos infraestructura sistema propio (CLP/año)
HOSTING_ANUAL = 86_000
DOMINIO_ANUAL = 11_000
INFRA_ANUAL = HOSTING_ANUAL + DOMINIO_ANUAL  # $97.000
INFRA_MENSUAL = round(INFRA_ANUAL / 12)  # ~$8.083

# Costos desarrollo y mantenimiento
DEV_PAGADO = 1_100_000
DEV_TOTAL = 1_600_000
MANT_MENSUAL = 50_000
BSALE_MENSUAL = 141_000  # promedio con IVA
BSALE_HASTA_HOY = 1_196_000

MESES_HOSTING_HASTA_HOY = 9  # oct 2025 - jun 2026
HOSTING_HASTA_HOY = round(MESES_HOSTING_HASTA_HOY / 12 * INFRA_ANUAL)  # $72.750


def fmt(n):
    return f"${n:,.0f}".replace(",", ".")


class PDF(FPDF):
    def header(self):
        self.set_font("Helvetica", "B", 11)
        self.set_text_color(80, 80, 80)
        self.cell(0, 8, "La Casa del Vitrificado - Analisis de costos", align="L")
        self.ln(10)

    def footer(self):
        self.set_y(-15)
        self.set_font("Helvetica", "I", 8)
        self.set_text_color(120, 120, 120)
        self.cell(0, 10, f"Pagina {self.page_no()}/{{nb}} | Generado el {date.today().strftime('%d/%m/%Y')}", align="C")

    def section_title(self, title):
        self.ln(4)
        self.set_font("Helvetica", "B", 13)
        self.set_text_color(30, 60, 120)
        self.cell(0, 10, title, new_x="LMARGIN", new_y="NEXT")
        self.set_draw_color(30, 60, 120)
        self.line(10, self.get_y(), 200, self.get_y())
        self.ln(4)

    def sub_title(self, title):
        self.ln(2)
        self.set_font("Helvetica", "B", 11)
        self.set_text_color(50, 50, 50)
        self.cell(0, 8, title, new_x="LMARGIN", new_y="NEXT")
        self.ln(2)

    def body_text(self, text):
        self.set_font("Helvetica", "", 10)
        self.set_text_color(40, 40, 40)
        self.multi_cell(0, 6, text)
        self.ln(2)

    def bullet(self, text):
        self.set_font("Helvetica", "", 10)
        self.set_text_color(40, 40, 40)
        self.multi_cell(0, 6, f"  -  {text}")
        self.ln(1)

    def table_row(self, cols, widths, bold=False, fill=False):
        style = "B" if bold else ""
        self.set_font("Helvetica", style, 9)
        if fill:
            self.set_fill_color(240, 245, 250)
        else:
            self.set_fill_color(255, 255, 255)
        self.set_text_color(40, 40, 40)
        for col, w in zip(cols, widths):
            self.cell(w, 8, col, border=1, fill=fill)
        self.ln()


def build_pdf():
    # Calculos acumulados
    hoy_pagado = DEV_PAGADO + HOSTING_HASTA_HOY
    hoy_contratado = DEV_TOTAL + HOSTING_HASTA_HOY

    ano_adicional = 500_000 + (MANT_MENSUAL * 12) + INFRA_ANUAL  # $1.197.000
    acum_jun_2027 = DEV_TOTAL + HOSTING_HASTA_HOY + INFRA_ANUAL + (MANT_MENSUAL * 12)
    acum_jun_2028 = DEV_TOTAL + round(33 / 12 * INFRA_ANUAL) + (MANT_MENSUAL * 24)
    bsale_jun_2027 = BSALE_HASTA_HOY + (BSALE_MENSUAL * 12)
    bsale_jun_2028 = BSALE_HASTA_HOY + (BSALE_MENSUAL * 32)

    costo_mensual_propio = MANT_MENSUAL + INFRA_MENSUAL

    pdf = PDF()
    pdf.alias_nb_pages()
    pdf.set_auto_page_break(auto=True, margin=20)
    pdf.add_page()

    page_w = pdf.w - pdf.l_margin - pdf.r_margin
    pdf.ln(30)
    pdf.set_font("Helvetica", "B", 22)
    pdf.set_text_color(30, 60, 120)
    pdf.cell(page_w, 12, "Comparacion de Costos", align="C", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(6)
    pdf.set_font("Helvetica", "B", 16)
    pdf.cell(page_w, 10, "Sistema Propio vs Bsale Omnicanal", align="C", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(16)
    pdf.set_font("Helvetica", "", 11)
    pdf.set_text_color(80, 80, 80)
    for line in [
        "La Casa del Vitrificado",
        "Fecha del analisis: 13 de junio de 2026",
        "Inicio del sistema propio: octubre 2025",
        "Actualizado con costos de hosting y dominio",
    ]:
        pdf.cell(page_w, 8, line, align="C", new_x="LMARGIN", new_y="NEXT")

    pdf.add_page()

    pdf.section_title("1. Bsale Plan Omnicanal (Full)")
    pdf.body_text(
        "Plataforma todo-en-uno para venta multicanal. Referencia: bsale.cl/sheet/plan-omnicanal"
    )
    pdf.sub_title("Precio Bsale")
    pdf.body_text(
        f"2,9 UF + IVA al mes (~{fmt(BSALE_MENSUAL)}/mes). "
        "Hosting, dominio y soporte incluidos. 30 dias de prueba gratis."
    )

    pdf.section_title("2. Sistema Propio (ERP a medida)")
    pdf.sub_title("Costos del sistema propio")
    w = [55, 35, 35, 35, 30]
    pdf.table_row(["Concepto", "Monto", "Periodo", "Estado", "Tipo"], w, bold=True, fill=True)
    pdf.table_row(["Desarrollo inicial", "$800.000", "-", "Pagado", "Unico"], w)
    pdf.table_row(["Segundo pago", "$300.000", "-", "Pagado", "Unico"], w, fill=True)
    pdf.table_row(["Tercer pago", "$500.000", "-", "Pendiente", "Unico"], w)
    pdf.table_row(["Mensualidad mant.", "$50.000", "mes", "No iniciada", "Recurrente"], w, fill=True)
    pdf.table_row(["Hosting Azure", "$86.000", "ano", "Activo", "Recurrente"], w)
    pdf.table_row(["Dominio", "$11.000", "ano", "Activo", "Recurrente"], w, fill=True)
    pdf.ln(2)
    pdf.body_text(
        f"Desarrollo total contratado: {fmt(DEV_TOTAL)} | Pagado: {fmt(DEV_PAGADO)}\n"
        f"Infraestructura anual: {fmt(INFRA_ANUAL)} ({fmt(HOSTING_ANUAL)} hosting + "
        f"{fmt(DOMINIO_ANUAL)} dominio) = ~{fmt(INFRA_MENSUAL)}/mes\n"
        f"Costo mensual recurrente total (mant. + infra): ~{fmt(costo_mensual_propio)}/mes"
    )

    pdf.section_title("3. Supuestos del calculo")
    for item in [
        "Fecha de referencia: 13 de junio de 2026 (~9 meses desde octubre 2025)",
        "Bsale: prueba octubre 2025, cobro desde noviembre 2025 (8 meses)",
        "Hosting y dominio activos desde octubre 2025",
        "Mensualidad de mantenimiento ($50.000) inicia en julio 2026",
        "Bsale incluye hosting/dominio; el sistema propio los paga aparte",
    ]:
        pdf.bullet(item)

    pdf.section_title("4. Costos hasta hoy (oct 2025 - 13 jun 2026)")
    w2 = [65, 55, 55]
    pdf.table_row(["Escenario", "Sistema propio", "Bsale"], w2, bold=True, fill=True)
    pdf.table_row(["Desarrollo (pagado)", fmt(DEV_PAGADO), "-"], w2)
    pdf.table_row([f"Hosting+dominio ({MESES_HOSTING_HASTA_HOY} meses)", fmt(HOSTING_HASTA_HOY), "Incluido"], w2, fill=True)
    pdf.table_row(["TOTAL (solo pagado)", fmt(hoy_pagado), fmt(BSALE_HASTA_HOY)], w2, bold=True)
    pdf.table_row(["TOTAL (todo contratado)", fmt(hoy_contratado), fmt(BSALE_HASTA_HOY)], w2, fill=True)
    pdf.ln(2)
    pdf.body_text(
        f"Hasta hoy Bsale sigue siendo mas economico: ~{fmt(BSALE_HASTA_HOY - hoy_pagado)} "
        f"menos que lo pagado, o ~{fmt(BSALE_HASTA_HOY - hoy_contratado)} menos incluyendo "
        f"el pago pendiente de desarrollo."
    )

    pdf.section_title("5. Proximo ano (jul 2026 - jun 2027)")
    pdf.table_row(["Concepto", "Sistema propio", "Bsale"], w2, bold=True, fill=True)
    pdf.table_row(["Pago desarrollo pendiente", fmt(500_000), "$0"], w2)
    pdf.table_row(["Mantenimiento (12 meses)", fmt(MANT_MENSUAL * 12), fmt(BSALE_MENSUAL * 12)], w2, fill=True)
    pdf.table_row(["Hosting + dominio (12 meses)", fmt(INFRA_ANUAL), "Incluido"], w2)
    pdf.table_row(["Costo adicional del ano", fmt(ano_adicional), fmt(BSALE_MENSUAL * 12)], w2, fill=True)
    pdf.table_row(["ACUMULADO TOTAL", fmt(acum_jun_2027), fmt(bsale_jun_2027)], w2, bold=True, fill=True)
    pdf.ln(2)
    pdf.body_text(
        f"Ganador: Sistema propio (~{fmt(bsale_jun_2027 - acum_jun_2027)} de ahorro acumulado).\n"
        f"Punto de equilibrio acumulado: ~enero 2027 (~6 meses tras iniciar la mensualidad)."
    )

    pdf.section_title("6. Dentro de 2 anos (oct 2025 - jun 2028)")
    pdf.table_row(["Concepto", "Sistema propio", "Bsale"], w2, bold=True, fill=True)
    pdf.table_row(["Desarrollo (total)", fmt(DEV_TOTAL), "$0"], w2)
    pdf.table_row(["Hosting + dominio (33 meses)", fmt(round(33 / 12 * INFRA_ANUAL)), "Incluido"], w2, fill=True)
    pdf.table_row(["Mantenimiento (24 meses)", fmt(MANT_MENSUAL * 24), "-"], w2)
    pdf.table_row(["Suscripcion Bsale (32 meses)", "-", fmt(BSALE_MENSUAL * 32)], w2, fill=True)
    pdf.table_row(["TOTAL ACUMULADO", fmt(acum_jun_2028), fmt(bsale_jun_2028)], w2, bold=True, fill=True)
    pdf.ln(2)
    pdf.body_text(
        f"Ganador: Sistema propio (~{fmt(bsale_jun_2028 - acum_jun_2028)} de ahorro vs Bsale)."
    )

    pdf.section_title("7. Costo mensual en operacion")
    w3 = [60, 60, 60]
    pdf.table_row(["Concepto", "Sistema propio", "Bsale"], w3, bold=True, fill=True)
    pdf.table_row(["Mantenimiento / licencia", fmt(MANT_MENSUAL), fmt(BSALE_MENSUAL)], w3)
    pdf.table_row(["Hosting + dominio", fmt(INFRA_MENSUAL), "Incluido"], w3, fill=True)
    pdf.table_row(["TOTAL MENSUAL", fmt(costo_mensual_propio), fmt(BSALE_MENSUAL)], w3, bold=True, fill=True)
    pdf.ln(2)
    pdf.body_text(
        f"En operacion continua, el sistema propio cuesta ~{fmt(costo_mensual_propio)}/mes "
        f"vs ~{fmt(BSALE_MENSUAL)}/mes de Bsale (ahorro de ~{fmt(BSALE_MENSUAL - costo_mensual_propio)}/mes)."
    )

    pdf.section_title("8. Resumen comparativo")
    w4 = [42, 43, 48, 48]
    pdf.table_row(["Plazo", "Mas economico", "Sistema propio", "Bsale"], w4, bold=True, fill=True)
    pdf.table_row(["Hasta hoy", "Bsale", fmt(hoy_contratado), fmt(BSALE_HASTA_HOY)], w4)
    pdf.table_row(["Jun 2027", "Sistema propio", fmt(acum_jun_2027), fmt(bsale_jun_2027)], w4, fill=True)
    pdf.table_row(["Jun 2028", "Sistema propio", fmt(acum_jun_2028), fmt(bsale_jun_2028)], w4)

    pdf.section_title("9. Conclusion")
    pdf.body_text(
        f"Incluyendo hosting ({fmt(HOSTING_ANUAL)}/ano) y dominio ({fmt(DOMINIO_ANUAL)}/ano), "
        f"el sistema propio sigue siendo mas barato a mediano plazo. El costo recurrente real "
        f"es ~{fmt(costo_mensual_propio)}/mes frente a ~{fmt(BSALE_MENSUAL)}/mes de Bsale."
    )
    pdf.body_text(
        "A corto plazo (hasta hoy) Bsale resulta mas economico por la alta inversion inicial "
        "del desarrollo. A partir de ~enero 2027 el acumulado favorece al sistema propio."
    )
    pdf.sub_title("Recomendacion")
    pdf.bullet(
        "Continuar con el sistema propio tiene sentido economico: ahorro de ~$1,5M en 2 anos "
        "incluso contando hosting y dominio."
    )
    pdf.bullet(
        "Bsale conviene si se necesita e-commerce + POS + integraciones de inmediato, "
        "sin seguir desarrollando."
    )
    pdf.bullet(
        "La mensualidad de $50.000 debe cubrir mantenimiento; hosting y dominio son costos "
        f"adicionales fijos de {fmt(INFRA_ANUAL)}/ano."
    )

    pdf.output(OUTPUT)
    return OUTPUT


if __name__ == "__main__":
    path = build_pdf()
    print(f"PDF generado: {path}")
