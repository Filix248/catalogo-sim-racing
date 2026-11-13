"""APEX / LAB: catálogo editorial y configurador prudente de sim racing."""

from __future__ import annotations

import base64
import json
import os
from html import escape
from pathlib import Path

import streamlit as st

from catalogo import (
    DEMO_PRODUCTS, assess_product, filter_products, normalize_products,
    recommend_products, safe_amazon_url,
)

ROOT = Path(__file__).resolve().parent
BUDGETS = {"Todos": "Todos los niveles", "Entry": "Primera parrilla", "Mid-range": "Siguiente nivel", "Enthusiast": "Máxima inmersión"}
PLATFORMS = ["PC", "PlayStation", "Xbox", "Laptop con eGPU"]
SIMULATORS = ["Assetto Corsa", "Forza Horizon", "iRacing"]
RESOLUTIONS = ["1080p", "1440p", "4K", "Ultrawide"]

st.set_page_config(page_title="APEX / LAB · Tu próximo setup", page_icon="🏁", layout="wide")
st.markdown(f"<style>{(ROOT / 'styles.css').read_text(encoding='utf-8')}</style>", unsafe_allow_html=True)


def html(markup: str) -> None:
    st.markdown(markup, unsafe_allow_html=True)


def asset(name: str) -> str:
    path = ROOT / "assets" / name
    if not path.is_file():
        return ""
    return "data:image/svg+xml;base64," + base64.b64encode(path.read_bytes()).decode("ascii")


def secret(name: str) -> str:
    value = os.getenv(name)
    if value:
        return value
    try:
        return str(st.secrets.get(name, ""))
    except (FileNotFoundError, KeyError, st.errors.StreamlitSecretNotFoundError):
        return ""


@st.cache_resource(show_spinner=False)
def connection(url: str, key: str):
    from supabase import ClientOptions, create_client
    return create_client(url, key, options=ClientOptions(postgrest_client_timeout=10))


@st.cache_data(ttl=300, show_spinner=False)
def load_catalogue() -> tuple[list[dict], str]:
    url, key = secret("SUPABASE_URL"), secret("SUPABASE_KEY")
    if not url or not key:
        return normalize_products(DEMO_PRODUCTS), "demo"
    try:
        response = connection(url, key).table("catalogo_amazon").select("*").limit(500).execute()
        if not isinstance(response.data, list):
            raise ValueError("Respuesta inesperada del catálogo")
        return normalize_products(response.data), "supabase"
    except Exception:
        # No exponer errores del cliente: pueden incluir datos de conexión.
        return normalize_products(DEMO_PRODUCTS), "offline"


def go_to(page: str) -> None:
    st.session_state["navigation"] = page


def sync_comparison() -> None:
    st.session_state["comparison"] = list(st.session_state["compare_picker"])


def set_collection(budget: str) -> None:
    st.session_state["catalogue_budget"] = budget
    st.session_state["catalogue_category"] = "Todas"
    st.session_state["catalogue_query"] = ""
    st.session_state["only_saved"] = False


def reset_filters() -> None:
    set_collection("Todos")


def spec_summary(product: dict) -> list[tuple[str, str]]:
    specs = product.get("specs_tecnicas", {})
    result = []
    for field, label, suffix in [("tipo", "Transmisión", ""), ("vram_gb", "Memoria", " GB VRAM"), ("hz", "Frecuencia", " Hz"), ("resolucion_ideal", "Objetivo registrado", "")]:
        value = specs.get(field)
        if value is not None and value != "":
            result.append((label, f"{value}{suffix}"))
    if isinstance(specs.get("fuerza_feedback"), bool):
        result.append(("Force feedback", "Sí" if specs["fuerza_feedback"] else "No"))
    return result


def category_asset(product: dict) -> str:
    category = product.get("categoria", "").casefold()
    if "gpu" in category or "gráfica" in category:
        return "gpu.svg"
    if "monitor" in category or "pantalla" in category:
        return "monitor.svg"
    return "wheel.svg"


def editorial_copy(product: dict) -> str:
    category = product.get("categoria", "").casefold()
    if "volante" in category:
        return "Siente la pista. Revisa la variante y su plataforma antes de elegir."
    if "gpu" in category:
        return "El apartado gráfico de tu PC. Equilíbralo con tu CPU y tu pantalla."
    if "monitor" in category:
        return "Tu ventana al circuito. Resolución y fluidez deben ir de la mano."
    return "Una pieza para tu setup. Revisa sus conexiones y especificaciones."


def product_card(product: dict, context: str, *, assessment: dict | None = None) -> None:
    pid = str(product["id"])
    with st.container(border=True, key=f"card_{context}_{pid}"):
        html(f'<div class="product-art"><span class="category-label">{escape(product["categoria"])}</span><img src="{asset(category_asset(product))}" alt="Ilustración de categoría {escape(product["categoria"])}"><span class="art-caption">ILUSTRACIÓN DE CATEGORÍA</span></div>')
        html(f'<div class="product-level">{escape(BUDGETS.get(product["nivel_presupuesto"], product["nivel_presupuesto"]))}</div><h3 class="product-title">{escape(product["nombre"])}</h3><p class="product-description">{escape(editorial_copy(product))}</p>')
        specs = spec_summary(product)
        html('<div class="spec-pills">' + "".join(f'<span>{escape(("Force feedback" if value == "Sí" else "Sin force feedback") if label == "Force feedback" else value)}</span>' for label, value in specs[:3]) + '</div>')
        if assessment:
            html(f'<div class="compatibility {escape(assessment["status"])}">● {escape(assessment["label"])}</div>')
            for reason in assessment.get("reasons", [])[:2]:
                st.caption(reason)
        else:
            html('<div class="compatibility unknown">◌ Compatibilidad por verificar</div>')
        url = safe_amazon_url(product.get("url_afiliado"))
        if url:
            st.link_button("Consultar en Amazon ↗", url, type="primary", width="stretch")
            html('<p class="affiliate-link-disclosure"><strong>Enlace de afiliado.</strong> Puedo recibir una comisión por las compras que cumplen los requisitos aplicables. Consulta precio, variante y disponibilidad en Amazon.</p>')
        else:
            st.button("Enlace pendiente", disabled=True, key=f"pending_{context}_{pid}", width="stretch")
            st.caption("Este producto aún no tiene un enlace de compra válido.")
        actions = st.columns(2)
        saved = pid in st.session_state["saved"]
        if actions[0].button("♥ Guardado" if saved else "♡ Guardar", key=f"save_{context}_{pid}", width="stretch"):
            if saved:
                st.session_state["saved"].remove(pid)
            else:
                st.session_state["saved"].append(pid)
            st.rerun()
        selected = pid in st.session_state["comparison"]
        if actions[1].button("✓ Añadido" if selected else "+ Comparar", key=f"compare_{context}_{pid}", width="stretch"):
            if selected:
                st.session_state["comparison"].remove(pid)
            elif len(st.session_state["comparison"]) < 3:
                st.session_state["comparison"].append(pid)
            else:
                st.toast("Puedes comparar hasta 3 productos. Retira uno en Comparar.", icon="ℹ️")
            st.rerun()
        with st.expander("Ver ficha y comprobaciones"):
            st.write(f'**Categoría:** {product["categoria"]}')
            for label, value in specs:
                st.write(f"**{label}:** {value}")
            platforms = product.get("specs_tecnicas", {}).get("plataformas")
            if platforms:
                st.write("**Plataformas registradas:** " + (", ".join(str(p) for p in platforms) if isinstance(platforms, list) else str(platforms)))
            st.caption("Datos del catálogo del editor; no equivalen a una prueba física ni a una certificación del fabricante.")
            if assessment:
                for note in assessment.get("notes", []):
                    st.caption(note)
            st.caption("Comprueba conectores, medidas, variante exacta y soporte del fabricante antes de comprar.")


def card_grid(items: list[dict], context: str, assessments: dict | None = None) -> None:
    for start in range(0, len(items), 3):
        columns = st.columns(3, gap="medium")
        for col, product in zip(columns, items[start:start + 3]):
            with col:
                product_card(product, context, assessment=(assessments or {}).get(str(product["id"])))


def section_heading(kicker: str, title: str, description: str = "") -> None:
    html(f'<div class="section-heading"><span class="eyebrow">{escape(kicker)}</span><h2>{escape(title)}</h2><p>{escape(description)}</p></div>')


products, source = load_catalogue()
for key, value in {"navigation": "Explorar", "saved": [], "comparison": [], "catalogue_budget": "Todos", "catalogue_category": "Todas", "catalogue_query": "", "only_saved": False}.items():
    if key not in st.session_state:
        st.session_state[key] = value
available_ids = {str(p["id"]) for p in products}
st.session_state["saved"] = [pid for pid in st.session_state["saved"] if pid in available_ids]
st.session_state["comparison"] = [pid for pid in st.session_state["comparison"] if pid in available_ids]

html('<header class="brandbar"><a class="brand" href="#inicio" aria-label="APEX LAB inicio"><span class="brand-icon">A</span> APEX<span class="brand-slash">/</span>LAB <span class="brand-tag">SIM RACING SELECT</span></a><span class="brand-note"><i></i> EL SIGUIENTE NIVEL ESTÁ EN LOS DETALLES</span></header>')

if st.session_state["navigation"] == "Explorar":
    html('<section id="inicio" class="hero"><div class="hero-copy"><div class="eyebrow"><span class="blue-line"></span> MENOS DUDAS. MÁS VUELTAS.</div><h1>Tu próxima vuelta<br><span class="hero-accent">empieza aquí.</span></h1><p>Encuentra las piezas para tu setup de sim racing.<br>Explora, compara y elige con más criterio.</p><div class="hero-tags"><span>01 &nbsp; EXPLORA</span><span>02 &nbsp; COMPARA</span><span>03 &nbsp; ARMA TU SETUP</span></div></div>' + f'<div class="hero-visual"><img src="{asset("hero-rig.svg")}" alt="Ilustración de un cockpit de sim racing con volante, asiento y monitor"><span class="visual-tag"><i></i> TU LUGAR EN LA PARRILLA</span></div></section>')
    with st.container(key="hero_actions"):
        cta, second, _ = st.columns([1.4, 1.4, 3.5])
        cta.button("Armar mi setup  →", type="primary", width="stretch", on_click=go_to, args=("Mi setup",))
        second.button("Cómo elegir  ↗", width="stretch", on_click=go_to, args=("Guías",))
    html('<div class="trust-strip"><span><b>01</b> Hardware por nivel</span><span><b>02</b> Comparaciones claras</span><span><b>03</b> Compra en Amazon</span><span class="trust-small">Elige aquí. Confirma los detalles allá.</span></div>')

comparison_count = len(st.session_state["comparison"])
navigation = st.segmented_control("Navegación principal", ["Explorar", "Mi setup", "Comparar", "Guías"], key="navigation", required=True, label_visibility="collapsed", format_func=lambda page: f"{page} ({comparison_count})" if page == "Comparar" and comparison_count else page)
html('<aside class="affiliate-notice" aria-label="Información de afiliación"><p><strong>Enlaces de afiliado:</strong> puedo recibir una comisión por las compras que cumplen los requisitos aplicables.</p><p lang="en">As an Amazon Associate I earn from qualifying purchases.</p></aside>')
if source != "supabase":
    st.info("Estás viendo datos de muestra. " + ("No pudimos cargar el catálogo conectado. Puedes seguir explorando y volver a intentarlo." if source == "offline" else "Conecta tu catálogo para mostrar tus productos reales."), icon="ℹ️")
    if source == "offline" and st.button("Reintentar conexión"):
        load_catalogue.clear()
        connection.clear()
        st.rerun()

if navigation == "Explorar":
    section_heading("ENCUENTRA TU PUNTO DE PARTIDA", "Un setup a tu ritmo.", "Desde tu primer volante hasta una experiencia más inmersiva.")
    collection_columns = st.columns(3, gap="medium")
    collections = [
        ("Entry", "01 / START", "Primera parrilla", "Tu entrada al sim racing. Empieza por el control.", "→ Ver nivel inicial"),
        ("Mid-range", "02 / UPGRADE", "Siguiente nivel", "Pantalla, control y gráficos. Encuentra tu próxima mejora.", "→ Explorar mejoras"),
        ("Enthusiast", "03 / IMMERSION", "Máxima inmersión", "Explora las piezas del nivel entusiasta.", "→ Ver selección"),
    ]
    for column, (budget, number, title, text, button) in zip(collection_columns, collections):
        with column, st.container(border=True, key=f"collection_{budget}"):
            html(f'<span class="collection-number">{number}</span><h3 class="collection-title">{title}</h3><p class="collection-copy">{text}</p>')
            st.button(button, key=f"pick_{budget}", on_click=set_collection, args=(budget,), width="stretch", type="tertiary")
    section_heading("EL GARAGE", "Explora el catálogo.", "Compara lo que importa. Guarda lo que te interesa.")
    with st.container(border=True, key="catalogue_filters"):
        search_col, category_col, budget_col = st.columns([1.6, 1, 1.1])
        search_col.text_input("Buscar producto", placeholder="Volante, RTX, Logitech…", key="catalogue_query")
        categories = ["Todas"] + sorted({p["categoria"] for p in products})
        if st.session_state["catalogue_category"] not in categories:
            st.session_state["catalogue_category"] = "Todas"
        category_col.selectbox("Categoría", categories, key="catalogue_category")
        budget_col.selectbox("Nivel de setup", list(BUDGETS), format_func=BUDGETS.get, key="catalogue_budget")
        left, right = st.columns([4, 1])
        left.toggle("Solo mis guardados", key="only_saved")
        right.button("Limpiar filtros", on_click=reset_filters, type="tertiary", width="stretch")
    filtered = filter_products(products, query=st.session_state["catalogue_query"], budget=st.session_state["catalogue_budget"], category=st.session_state["catalogue_category"])
    if st.session_state["only_saved"]:
        filtered = [p for p in filtered if str(p["id"]) in st.session_state["saved"]]
    html(f'<div class="results-meta"><span><b>{len(filtered):02d}</b> productos en tu selección</span><span>{len(st.session_state["saved"])} guardados · {"Catálogo conectado" if source == "supabase" else "Catálogo de muestra"}</span></div>')
    if filtered:
        card_grid(filtered, "catalogue")
    else:
        st.info("No hay productos con estos filtros." + (" Guarda un producto para encontrarlo aquí." if st.session_state["only_saved"] else " Prueba otra categoría o nivel."))
        st.button("Ver todo el catálogo", on_click=reset_filters)
    html('<div class="editorial-banner"><span class="eyebrow">ANTES DE CAMBIAR UNA PIEZA</span><h3>Un buen setup se construye en conjunto.</h3><p>La plataforma, el espacio y las conexiones importan tanto como el hardware.</p></div>')
    st.button("Encontrar mi punto de partida →", on_click=go_to, args=("Mi setup",), key="bottom_setup")

elif navigation == "Mi setup":
    section_heading("TU PUNTO DE PARTIDA", "Cada piloto tiene su setup.", "Cuéntanos dónde corres. Te mostramos candidatos y lo que falta comprobar.")
    with st.container(border=True, key="setup_form"):
        a, b = st.columns(2)
        with a:
            platform = st.selectbox("¿Dónde vas a correr?", PLATFORMS, key="setup_platform")
            simulator = st.selectbox("Simulador principal", SIMULATORS, key="setup_simulator")
        with b:
            budget = st.selectbox("Nivel de setup", ["Entry", "Mid-range", "Enthusiast"], format_func=BUDGETS.get, key="setup_budget")
            resolution = st.selectbox("Resolución objetivo", RESOLUTIONS, key="setup_resolution")
    st.caption("El nivel clasifica el catálogo; no es un límite de gasto. La resolución es una orientación y no garantiza FPS.")
    recommendations = recommend_products(products, budget=budget, platform=platform, simulator=simulator, resolution=resolution)
    incompatible = [p for p in filter_products(products, budget=budget) if assess_product(p, platform=platform, simulator=simulator, resolution=resolution)["status"] == "incompatible"]
    if platform == "Laptop con eGPU":
        st.info("Una GPU externa requiere un portátil y una caja eGPU compatibles. Revisa la conexión y el soporte del equipo; no basta con tener un puerto USB-C.")
    if platform in ["PlayStation", "Xbox"]:
        st.caption("Las GPU de PC se excluyen en consola. Los volantes requieren la variante compatible con tu consola.")
    if recommendations:
        section_heading("CANDIDATOS PARA REVISAR", "Tu selección inicial.", f"{platform} · {simulator} · {resolution} · {BUDGETS[budget]}")
        assessment_map = {str(item["product"]["id"]): item["assessment"] for item in recommendations}
        card_grid([item["product"] for item in recommendations], "setup", assessment_map)
        st.info("Es una selección parcial, con una opción por categoría. Los elementos sin compatibilidad documentada quedan por verificar; no es una garantía de un sistema completo.")
    else:
        st.info("No tenemos candidatos para esta combinación. Prueba otro nivel o explora el catálogo; no sustituimos una pieza incompatible por una recomendación automática.")
    if incompatible:
        with st.expander(f"¿Por qué se excluyeron {len(incompatible)} productos?"):
            for product in incompatible:
                assessment = assess_product(product, platform=platform, simulator=simulator, resolution=resolution)
                st.write(f'**{product["nombre"]}**')
                for reason in assessment["reasons"]:
                    st.caption(reason)
    st.caption("Antes de cerrar el setup: comprueba CPU, placa base, RAM, fuente, conexiones de vídeo, espacio y anclajes. El catálogo actual no cubre todas esas piezas.")

elif navigation == "Comparar":
    section_heading("DECIDE CON CRITERIO", "Las diferencias, frente a frente.", "Elige hasta tres productos. Para comparar alternativas, empieza por la misma categoría.")
    by_id = {str(p["id"]): p for p in products}
    st.session_state["compare_picker"] = list(st.session_state["comparison"])
    selected = st.multiselect("Productos a comparar", options=list(by_id), format_func=lambda pid: by_id[pid]["nombre"], max_selections=3, key="compare_picker", on_change=sync_comparison)
    if selected:
        chosen = [by_id[pid] for pid in selected]
        if len({p["categoria"] for p in chosen}) > 1:
            st.info("Seleccionaste categorías diferentes. Puedes revisar sus fichas, pero sus características no son equivalentes.")
        columns = st.columns(len(chosen), gap="medium")
        for column, product in zip(columns, chosen):
            with column:
                product_card(product, "comparison")
        rows = []
        field_labels = [("tipo", "Transmisión"), ("fuerza_feedback", "Force feedback"), ("vram_gb", "VRAM (GB)"), ("hz", "Frecuencia (Hz)"), ("resolucion_ideal", "Objetivo registrado"), ("plataformas", "Plataformas registradas")]
        def comparison_value(value):
            if value is None or value == "":
                return "Sin datos"
            if isinstance(value, bool):
                return "Sí" if value else "No"
            if isinstance(value, list):
                return ", ".join(str(v) for v in value)
            return str(value)
        for field, label in [("categoria", "Categoría"), ("nivel_presupuesto", "Nivel")] + field_labels:
            row = {"Característica": label}
            for index, product in enumerate(chosen, 1):
                value = product.get(field) if field in ["categoria", "nivel_presupuesto"] else product["specs_tecnicas"].get(field)
                row[f'{index}. {product["nombre"]}'] = comparison_value(value)
            rows.append(row)
        st.dataframe(rows, hide_index=True, width="stretch")
        payload = [{"nombre": p["nombre"], "categoria": p["categoria"], "nivel": p["nivel_presupuesto"], "specs_tecnicas": p["specs_tecnicas"], "url_amazon": safe_amazon_url(p.get("url_afiliado"))} for p in chosen]
        st.download_button("Descargar mi comparación ↓", data=json.dumps(payload, ensure_ascii=False, indent=2), file_name="mi-comparacion-apex.json", mime="application/json")
    else:
        st.info("Tu comparador está listo. Selecciona productos arriba o usa «+ Comparar» en una tarjeta.")
        st.button("Explorar productos →", on_click=go_to, args=("Explorar",))

elif navigation == "Guías":
    section_heading("LA VUELTA DE RECONOCIMIENTO", "Antes de comprar, entiende tu setup.", "Cuatro decisiones que conviene tomar antes de elegir modelos.")
    guide_columns = st.columns(2, gap="medium")
    guides = [
        ("01", "Empieza por tu plataforma.", "PC, PlayStation y Xbox necesitan comprobaciones distintas. Un mismo nombre de volante puede tener variantes diferentes.", "Revisa la ficha de la variante exacta y la lista oficial de juegos y sistemas compatibles."),
        ("02", "Haz espacio para conducir.", "Mide la mesa, el asiento y la zona de pedales. Una buena postura y un anclaje firme también son parte de la experiencia.", "Comprueba medidas, grosor de mesa admitido y puntos de fijación antes de comprar un soporte o cockpit."),
        ("03", "Equilibra imagen y rendimiento.", "Una resolución objetivo no define por sí sola el rendimiento. También intervienen CPU, ajustes del simulador y número de pantallas.", "Busca pruebas de tu combinación de juego, GPU, CPU y resolución; el catálogo no estima FPS."),
        ("04", "Mejora una cosa con intención.", "Identifica primero qué te limita: control, postura, espacio o imagen. Después compara alternativas de esa categoría.", "Guarda dos o tres candidatos y revisa sus diferencias en el comparador antes de cambiar una pieza."),
    ]
    for index, (number, title, description, tip) in enumerate(guides):
        with guide_columns[index % 2], st.container(border=True, key=f"guide_{number}"):
            html(f'<span class="guide-number">{number}</span><h3 class="guide-title">{title}</h3><p class="guide-copy">{description}</p><p class="guide-tip">{tip}</p>')
    with st.expander("Cómo leer esta selección", expanded=True):
        st.write("Organizamos los productos por categoría y nivel. Solo mostramos las características registradas en el catálogo; cuando falta un dato, lo indicamos. Las ilustraciones representan categorías y no el aspecto exacto del modelo.")
        st.write("La compatibilidad se evalúa con los metadatos disponibles. Un dato desconocido no se interpreta como compatible y una resolución diferente no implica incompatibilidad.")
        st.write("Los guardados y la comparación duran durante esta sesión. No se crea una cuenta ni se envían esas selecciones a la base de datos.")
    st.button("Armar mi selección →", type="primary", on_click=go_to, args=("Mi setup",))

html('<footer class="footer"><div class="footer-brand">APEX<span>/</span>LAB <small>ELIGE CON CRITERIO. CORRE A TU RITMO.</small></div><p>Catálogo independiente de sim racing. Las compras se realizan en Amazon.</p><p class="footer-affiliation">Como Afiliado de Amazon, obtengo ingresos por las compras que cumplen los requisitos aplicables.</p><p class="footer-note">Consulta precio y disponibilidad en Amazon. La ficha del fabricante y la variante exacta determinan la compatibilidad.</p></footer>')
