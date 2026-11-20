"""Genera el PDF de una revisión guardada, para que el estudiante trabaje sus correcciones."""

from io import BytesIO
from xml.sax.saxutils import escape

from django.utils import timezone
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.platypus import KeepTogether, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

COLOR_SEVERIDAD = {"CRITICA": "#b3261e", "MAYOR": "#e08a00", "MENOR": "#1f4e8c"}


def _texto(valor):
    """Escapa el texto para ReportLab y cambia símbolos que la fuente no tiene."""
    if isinstance(valor, list):
        valor = "; ".join(str(v) for v in valor)
    return escape(str(valor or "")).replace("→", "->")


def generar_pdf(revision):
    """Devuelve el contenido (bytes) del PDF con los datos generales y las observaciones."""
    estilos = getSampleStyleSheet()
    normal = ParagraphStyle("normal", parent=estilos["Normal"], fontSize=10, leading=13)
    nota = ParagraphStyle("nota", parent=normal, fontSize=9, textColor=colors.HexColor("#5b6475"))
    cita = ParagraphStyle("cita", parent=normal, fontName="Helvetica-Oblique", leftIndent=12,
                          backColor=colors.HexColor("#f5f6f8"), borderPadding=4, spaceBefore=4, spaceAfter=4)

    elementos = [
        Paragraph("Observaciones del agente", estilos["Title"]),
        Paragraph(f"<b>{_texto(revision.nombre_documento)}</b>", normal),
        Paragraph(f"{revision.get_etapa_display()} · {revision.get_modalidad_display()} · "
                  f"Revisado el {timezone.localtime(revision.creada):%d/%m/%Y %H:%M}", nota),
        Paragraph(f"Modelo: {_texto(revision.modelo)} · {revision.cantidad_observaciones} observaciones: "
                  f"{revision.conteo['CRITICA']} críticas, {revision.conteo['MAYOR']} mayores, "
                  f"{revision.conteo['MENOR']} menores", nota),
    ]
    if revision.simulado:
        elementos.append(Paragraph("<b>Modo simulado:</b> estas observaciones son de ejemplo, no las generó Claude.",
                                   ParagraphStyle("aviso", parent=normal, textColor=colors.HexColor("#b3261e"))))

    elementos += [Spacer(1, 12), Paragraph("Datos generales", estilos["Heading2"])]
    datos = revision.datos_generales
    filas = [
        ("Tipo de documento", datos.get("tipo_documento")),
        ("Objeto de estudio", datos.get("objeto_estudio")),
        ("Campo de acción", datos.get("campo_accion")),
        ("Causas", datos.get("causas")),
        ("Término de relación", datos.get("termino_relacion")),
        ("Efectos", datos.get("efectos")),
    ]
    tabla = Table([[Paragraph(f"<b>{a}</b>", normal), Paragraph(_texto(b), normal)] for a, b in filas],
                  colWidths=[4.5 * cm, 12 * cm])
    tabla.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LINEBELOW", (0, 0), (-1, -1), 0.5, colors.HexColor("#d9dde5")),
    ]))
    elementos += [tabla, Spacer(1, 12), Paragraph("Observaciones", estilos["Heading2"])]

    for numero, o in enumerate(revision.observaciones.all(), start=1):
        color = COLOR_SEVERIDAD.get(o.severidad, "#5b6475")
        bloque = [Paragraph(f'{numero}. <font color="{color}"><b>{o.get_severidad_display()}</b></font> · '
                            f"<b>{_texto(o.regla)}</b> · {_texto(o.seccion)}", normal)]
        if o.fragmento:
            bloque.append(Paragraph(f"\"{_texto(o.fragmento)}\"", cita))
            if not o.fragmento_encontrado:
                bloque.append(Paragraph("El fragmento citado no se encontró de forma literal en el documento.", nota))
        bloque += [Paragraph(_texto(o.descripcion), normal), Spacer(1, 10)]
        elementos.append(KeepTogether(bloque))

    if not revision.cantidad_observaciones:
        elementos.append(Paragraph("El agente no encontró incumplimientos.", normal))

    elementos += [Spacer(1, 12), Paragraph(
        "Observaciones generadas por el Agente de IA para la revisión de trabajos de grado (UCB Cochabamba). "
        "Apoyan la revisión del docente; no la reemplazan.", nota)]

    buffer = BytesIO()
    SimpleDocTemplate(buffer, pagesize=letter, leftMargin=2 * cm, rightMargin=2 * cm,
                      topMargin=2 * cm, bottomMargin=2 * cm,
                      title=f"Observaciones - {revision.nombre_documento}").build(elementos)
    return buffer.getvalue()