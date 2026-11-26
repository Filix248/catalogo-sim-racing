"""Create a shareable comparison without accessing accounts, files or the network.

Only catalogue content is exported. Prices, stock, reviews, internal record IDs
and connection configuration are deliberately outside this document's scope.
"""

from __future__ import annotations

from collections.abc import Mapping
from datetime import date, datetime, timezone
from html import escape
from io import BytesIO
from pathlib import Path
import re
from urllib.parse import urlsplit

import reportlab
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import ParagraphStyle
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (
    KeepTogether, PageBreak, Paragraph, SimpleDocTemplate, Spacer,
    Table, TableStyle,
)

from catalogo import normalize_products, safe_amazon_url


INK = colors.HexColor("#10232d")
LIME = colors.HexColor("#d4f56a")
TEXT = colors.HexColor("#1e3541")
MUTED = colors.HexColor("#546873")
PALE = colors.HexColor("#f1f5f5")
LINE = colors.HexColor("#d8e2e4")
WHITE = colors.white
CATALOGUE_URL = "https://apex-lab-sim-racing.streamlit.app/"
LEVELS = {"Entry": "Primera parrilla", "Mid-range": "Siguiente nivel", "Enthusiast": "Máxima inmersión"}
MANUFACTURERS = ("logitechg.com", "logitech.com", "thrustmaster.com", "nextlevelracing.com", "lg.com", "asus.com", "msi.com")
SPEC_LABELS = {
    "tipo": "Tipo", "fuerza_feedback": "Force feedback", "vram_gb": "Memoria GPU (GB)",
    "hz": "Frecuencia (Hz)", "resolucion": "Resolución del panel",
    "conexion": "Conexión", "resolucion_ideal": "Objetivo editorial de resolución",
    "plataformas": "Plataformas declaradas", "simuladores": "Simuladores declarados",
    "estado": "Estado de la oferta", "asin": "ASIN", "fecha_revision": "Fecha de revisión",
}
CONTENT_KEYS = {"descripcion_editorial", "incluye", "requiere", "advertencia", "fuentes_fabricante", "fuentes", "fuente"}
PRIVATE_KEY = re.compile(r"(^_|password|contrase|secret|token|credential|credencial|supabase|api.?key|service.?role)", re.I)
COMMERCE_KEY = re.compile(r"(^|_)(precio|price|stock|rating|ratings|review|reviews|reseña|resena|puntuacion|disponibilidad)(_|$)", re.I)
IMAGE_KEY = re.compile(r"(^|_)(imagen|image|foto|photo|thumbnail)(_|$)", re.I)


def _fonts() -> None:
    """Vera is shipped and licensed with ReportLab on Windows and Linux."""
    if "ApexVera" not in pdfmetrics.getRegisteredFontNames():
        directory = Path(reportlab.__file__).resolve().parent / "fonts"
        pdfmetrics.registerFont(TTFont("ApexVera", str(directory / "Vera.ttf")))
        pdfmetrics.registerFont(TTFont("ApexVera-Bold", str(directory / "VeraBd.ttf")))
        pdfmetrics.registerFontFamily("ApexVera", normal="ApexVera", bold="ApexVera-Bold", italic="ApexVera", boldItalic="ApexVera-Bold")


def _public_key(key: object) -> bool:
    text = str(key)
    return not (PRIVATE_KEY.search(text) or COMMERCE_KEY.search(text) or IMAGE_KEY.search(text))


def _text(value: object, *, depth: int = 0) -> str:
    """Flatten JSON-like values readably; never interpret supplied markup."""
    if depth > 12:
        return "Detalle anidado no representable"
    if value is None:
        return "No indicado"
    if isinstance(value, bool):
        return "Sí" if value else "No"
    if isinstance(value, Mapping):
        entries = [f"{str(key).replace('_', ' ')}: {_text(item, depth=depth + 1)}" for key, item in value.items() if _public_key(key)]
        return "; ".join(entries) or "No indicado"
    if isinstance(value, (list, tuple)):
        return "; ".join(_text(item, depth=depth + 1) for item in value) or "No indicado"
    if isinstance(value, (str, int, float)):
        text = str(value).strip()
        # PDF copy uses ordinary hyphens and removes control characters.
        return "".join(char for char in text.replace("\u2011", "-").replace("\u2013", "-").replace("\u2014", "-") if char in "\n\t" or ord(char) >= 32) or "No indicado"
    return "No indicado"


def _paragraph(value: object, style: ParagraphStyle) -> Paragraph:
    return Paragraph(escape(_text(value)).replace("\n", "<br/>"), style)


def format_value(value: object) -> str:
    """Return plain comparison text; callers must escape it for HTML or XML."""
    return _text(value)


def comparison_rows(products: list[dict]) -> list[tuple[str, list[str]]]:
    """Shared UI/PDF facts, with unknown support and full warnings preserved."""
    fields = [
        ("categoria", "Categoría"), ("nivel_presupuesto", "Nivel de setup"),
        ("estado", "Estado de la oferta"), ("plataformas", "Plataformas declaradas"),
        ("tipo", "Tipo"), ("fuerza_feedback", "Force feedback"),
        ("vram_gb", "Memoria GPU (GB)"), ("hz", "Frecuencia (Hz)"),
        ("resolucion", "Resolución del panel"), ("conexion", "Conexión"),
        ("resolucion_ideal", "Objetivo editorial de resolución"),
        ("incluye", "Lo que incluye"), ("requiere", "Requisitos"),
        ("advertencia", "Antes de comprar"),
    ]
    rows = []
    for key, label in fields:
        if key not in {"categoria", "nivel_presupuesto", "plataformas"} and not any(key in product.get("specs_tecnicas", {}) for product in products):
            continue
        values = []
        for product in products:
            value = product.get(key) if key in {"categoria", "nivel_presupuesto"} else product.get("specs_tecnicas", {}).get(key)
            if key == "nivel_presupuesto" and isinstance(value, str):
                value = LEVELS.get(value, value)
            text = _text(value)
            if key == "plataformas" and text == "No indicado":
                text = "Por confirmar"
            values.append(text)
        rows.append((label, values))
    return rows


def _source_urls(specs: Mapping) -> list[str]:
    values = specs.get("fuentes_fabricante") or specs.get("fuentes") or specs.get("fuente") or []
    values = [values] if isinstance(values, str) else values if isinstance(values, (list, tuple)) else []
    result = []
    for value in values:
        if not isinstance(value, str) or any(char.isspace() or ord(char) < 32 for char in value) or "\\" in value:
            continue
        try:
            parsed = urlsplit(value)
            host = (parsed.hostname or "").casefold()
            if parsed.scheme != "https" or parsed.username is not None or parsed.password is not None or parsed.port not in {None, 443}:
                continue
            if any(host == domain or host.endswith("." + domain) for domain in MANUFACTURERS):
                result.append(value)
        except ValueError:
            continue
    return list(dict.fromkeys(result))


def _styles() -> dict[str, ParagraphStyle]:
    common = dict(fontName="ApexVera", textColor=TEXT, splitLongWords=1, allowWidows=0, allowOrphans=0)
    return {
        "title": ParagraphStyle("ApexTitle", fontSize=25, leading=30, fontName="ApexVera-Bold", textColor=INK, spaceAfter=9, splitLongWords=1),
        "subtitle": ParagraphStyle("ApexSubtitle", fontSize=10, leading=15, spaceAfter=15, **common),
        "body": ParagraphStyle("ApexBody", fontSize=9.4, leading=14, spaceAfter=7, **common),
        "fact": ParagraphStyle("ApexFact", fontSize=9.4, leading=14, spaceAfter=4, **common),
        "small": ParagraphStyle("ApexSmall", fontSize=8, leading=11.5, spaceAfter=5, **common),
        "table": ParagraphStyle("ApexTable", fontSize=9, leading=13, **common),
        "label": ParagraphStyle("ApexLabel", fontSize=9, leading=13, fontName="ApexVera-Bold", textColor=MUTED, splitLongWords=1),
        "table_header": ParagraphStyle("ApexTableHeader", fontSize=10, leading=14, fontName="ApexVera-Bold", textColor=WHITE, splitLongWords=1),
        "section": ParagraphStyle("ApexSection", fontSize=11, leading=15, fontName="ApexVera-Bold", textColor=INK, spaceBefore=8, spaceAfter=5, keepWithNext=True, splitLongWords=1),
        "product": ParagraphStyle("ApexProduct", fontSize=20, leading=25, fontName="ApexVera-Bold", textColor=INK, spaceAfter=8, splitLongWords=1),
        "eyebrow": ParagraphStyle("ApexEyebrow", fontSize=8.2, leading=12, fontName="ApexVera-Bold", textColor=MUTED, spaceAfter=5, splitLongWords=1),
        "cta": ParagraphStyle("ApexCTA", fontSize=10, leading=15, fontName="ApexVera-Bold", textColor=INK, spaceAfter=6, splitLongWords=1),
    }


def _field_block(label: str, value: object, styles: dict) -> list:
    """Separate flowables let long warnings and nested values cross page breaks."""
    content = escape(_text(value)).replace("\n", "<br/>")
    return [Paragraph(f"<b>{escape(label)}:</b> {content}", styles["body"])]


def _summary(products: list[dict], styles: dict, width: float) -> list:
    count = len(products)
    cells = [[Paragraph("TU SELECCIÓN", styles["table_header"])]]
    cells[0] += [Paragraph(f"{index:02d}<br/>{escape(_text(product['nombre'])[:180])}", styles["table_header"]) for index, product in enumerate(products, 1)]
    for label, values in comparison_rows(products):
        if label in {"Lo que incluye", "Requisitos", "Antes de comprar"}:
            continue
        row = [Paragraph(escape(label), styles["label"])]
        for text in values:
            if len(text) > 310:
                text = text[:310].rstrip() + "... (ver ficha completa)"
            row.append(_paragraph(text, styles["table"]))
        cells.append(row)
    table = Table(cells, colWidths=[114] + [(width - 114) / count] * count, repeatRows=1, hAlign="LEFT")
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), INK), ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 11), ("RIGHTPADDING", (0, 0), (-1, -1), 11),
        ("TOPPADDING", (0, 0), (-1, -1), 8), ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [WHITE, PALE]),
        ("LINEBELOW", (0, 0), (-1, 0), 3, LIME),
        ("LINEBELOW", (0, 1), (-1, -1), 0.4, LINE),
    ]))
    return [table, Spacer(1, 11), _paragraph("No indicado o Por confirmar significa que la ficha no declara ese dato. La comparación no verifica que los productos formen un conjunto compatible. Consulta los requisitos completos en las siguientes fichas. Comprueba la plataforma, el juego, las conexiones y el anclaje de la variante exacta. Un objetivo de resolución no garantiza rendimiento ni FPS. Esta selección no es una compra ni una reserva.", styles["small"])]


def _product_story(product: dict, number: int, count: int, styles: dict, width: float) -> list:
    specs = product["specs_tecnicas"]
    story = [PageBreak(), _paragraph(f"FICHA {number:02d} / {count:02d}  ·  {product['categoria']}  ·  {LEVELS.get(product['nivel_presupuesto'], product['nivel_presupuesto'])}", styles["eyebrow"]), _paragraph(product["nombre"], styles["product"])]
    if specs.get("estado"):
        story.extend(_field_block("Estado de la oferta", specs["estado"], styles))
    if specs.get("descripcion_editorial"):
        story.append(_paragraph(specs["descripcion_editorial"], styles["body"]))
    for key, label in [("incluye", "Lo que incluye"), ("requiere", "Requisitos"), ("advertencia", "Antes de comprar")]:
        if specs.get(key):
            story.extend(_field_block(label, specs[key], styles))
    story.append(Paragraph("Características registradas", styles["section"]))
    technical_fields = [(key, value) for key, value in specs.items() if key not in CONTENT_KEYS | {"estado"} and _public_key(key)]
    if not technical_fields:
        story.append(_paragraph("Esta ficha no incluye más especificaciones. Confirma los detalles de la variante en Amazon y en el fabricante.", styles["body"]))
    for key, value in technical_fields:
        # Separate paragraphs rather than fixed table rows: long values can split.
        label = SPEC_LABELS.get(key, str(key).replace("_", " ").capitalize())
        content = escape(_text(value)).replace("\n", "<br/>")
        story.append(Paragraph(f"<b>{escape(label)}:</b> {content}", styles["fact"]))
    story.append(Spacer(1, 10))
    url = safe_amazon_url(product.get("url_afiliado"))
    if url:
        story.append(KeepTogether([
            Paragraph(f'<a href="{CATALOGUE_URL}" color="#10232d">Consultar en el catálogo</a>', styles["cta"]),
            _paragraph("Abre el catálogo de APEX / LAB para consultar sus enlaces de compra. Comprueba precio, variante, condición y disponibilidad en Amazon.", styles["small"]),
        ]))
    else:
        story.append(_paragraph("Esta ficha no tiene un enlace de compra habilitado.", styles["small"]))
    sources = _source_urls(specs)
    if sources:
        story.append(Spacer(1, 5))
        for index, source in enumerate(sources, 1):
            host = urlsplit(source).hostname
            story.append(Paragraph(f'<b>Fuente del fabricante {index:02d}:</b> <a href="{escape(source, quote=True)}" color="#10232d">{escape(host or "Fabricante")} - Abrir documentación</a>', styles["small"]))
    return story


def build_comparison_pdf(products: list[dict], *, generated_at: date | datetime | None = None) -> bytes:
    """Return an A4 landscape PDF for one to three records, without mutations.

    ``generated_at`` is injectable for deterministic previews/tests. The date is
    the export date, not a claim that Amazon prices or availability were checked.
    """
    if not isinstance(products, (list, tuple)) or not 1 <= len(products) <= 3 or not all(isinstance(item, Mapping) for item in products):
        raise ValueError("Selecciona entre uno y tres productos para exportar.")
    products = normalize_products(products)
    generated_at = generated_at or datetime.now(timezone.utc)
    if not isinstance(generated_at, (date, datetime)):
        raise ValueError("La fecha de generación debe ser una fecha válida.")
    date_label = generated_at.strftime("%d/%m/%Y")
    _fonts()
    styles = _styles()
    output = BytesIO()
    page_width, page_height = landscape(A4)
    doc = SimpleDocTemplate(output, pagesize=(page_width, page_height), rightMargin=36, leftMargin=36, topMargin=104, bottomMargin=52, title="Mi comparativa de sim racing | APEX / LAB", author="APEX / LAB", subject="Comparativa editorial de productos seleccionados", creator="APEX / LAB", pageCompression=1)

    def page_chrome(canvas, document):
        canvas.saveState()
        canvas.setFillColor(INK)
        canvas.rect(0, page_height - 82, page_width, 82, fill=1, stroke=0)
        canvas.setFillColor(LIME)
        canvas.rect(36, page_height - 51, 27, 27, fill=1, stroke=0)
        canvas.setFillColor(INK)
        canvas.setFont("ApexVera-Bold", 17)
        canvas.drawString(42, page_height - 44, "A")
        canvas.setFillColor(WHITE)
        canvas.setFont("ApexVera-Bold", 16)
        canvas.drawString(76, page_height - 43, "APEX / LAB")
        canvas.setFillColor(LIME)
        canvas.setFont("ApexVera", 8)
        canvas.drawRightString(page_width - 36, page_height - 36, "EL GARAGE / COMPARATIVA")
        canvas.setFillColor(colors.HexColor("#bdcdd3"))
        canvas.drawRightString(page_width - 36, page_height - 53, f"Generada el {date_label}")
        canvas.setStrokeColor(LINE)
        canvas.line(36, 39, page_width - 36, 39)
        canvas.setFillColor(MUTED)
        canvas.setFont("ApexVera", 7)
        canvas.drawString(36, 25, "APEX / LAB · Catálogo independiente de sim racing · Compra y disponibilidad en Amazon")
        canvas.drawRightString(page_width - 36, 25, f"Página {document.page}")
        canvas.restoreState()

    story = [Paragraph("Tu próxima mejora,<br/>frente a frente.", styles["title"]), _paragraph(f"{len(products):02d} productos en tu selección. Compara los datos registrados y conserva las fichas completas para revisar requisitos y fuentes.", styles["subtitle"])]
    categories = {product["categoria"] for product in products}
    if len(categories) > 1:
        story.append(_paragraph("Tu selección combina categorías diferentes: sirve para revisar piezas de un setup, no para tratarlas como alternativas equivalentes.", styles["small"]))
    story.extend(_summary(products, styles, doc.width))
    story.append(Spacer(1, 5))
    story.append(_paragraph("Como Afiliado de Amazon, obtengo ingresos por las compras que cumplen los requisitos aplicables. As an Amazon Associate I earn from qualifying purchases.", styles["small"]))
    for number, product in enumerate(products, 1):
        story.extend(_product_story(product, number, len(products), styles, doc.width))
    doc.build(story, onFirstPage=page_chrome, onLaterPages=page_chrome)
    return output.getvalue()
