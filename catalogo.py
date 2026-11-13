"""Pure catalogue logic shared by the Streamlit interface and its tests.

Compatibility comes only from explicit ``specs_tecnicas`` metadata. Supported
optional keys are ``plataformas`` and ``simuladores`` (lists of exact supported
values); ``resolucion_ideal`` is an editorial target, never an FPS guarantee.
An absent list means unknown, not universal compatibility. For a laptop with an
external GPU, write ``Laptop con eGPU`` explicitly: PC support does not prove the
laptop, enclosure, connector or power supply will work together.
"""

from __future__ import annotations

import json
import math
import re
import unicodedata
from collections.abc import Iterable, Mapping
from typing import Any
from urllib.parse import urlsplit


BUDGETS = ("Entry", "Mid-range", "Enthusiast")
PLATFORMS = ("PC", "PlayStation", "Xbox", "Laptop con eGPU")

# Same records as the initial catalogue, with deliberately inactive buy links.
# These are illustrations of the interface, not verified product recommendations.
DEMO_PRODUCTS: list[dict[str, Any]] = [
    {
        "id": "demo-g923", "categoria": "Volante", "nombre": "Logitech G923",
        "nivel_presupuesto": "Entry",
        "specs_tecnicas": {"tipo": "Engranaje", "fuerza_feedback": True},
        "precio_aprox": 350, "url_afiliado": "",
    },
    {
        "id": "demo-t300", "categoria": "Volante", "nombre": "Thrustmaster T300 RS",
        "nivel_presupuesto": "Mid-range",
        "specs_tecnicas": {"tipo": "Correa", "fuerza_feedback": True},
        "precio_aprox": 450, "url_afiliado": "",
    },
    {
        "id": "demo-4060", "categoria": "GPU", "nombre": "NVIDIA RTX 4060",
        "nivel_presupuesto": "Mid-range",
        "specs_tecnicas": {"vram_gb": 8, "resolucion_ideal": "1080p"},
        "precio_aprox": 300, "url_afiliado": "",
    },
    {
        "id": "demo-4070", "categoria": "GPU", "nombre": "NVIDIA RTX 4070 Ti",
        "nivel_presupuesto": "Enthusiast",
        "specs_tecnicas": {"vram_gb": 12, "resolucion_ideal": "1440p"},
        "precio_aprox": 799, "url_afiliado": "",
    },
    {
        "id": "demo-monitor", "categoria": "Monitor", "nombre": 'LG UltraGear 27"',
        "nivel_presupuesto": "Mid-range",
        "specs_tecnicas": {"hz": 144, "resolucion_ideal": "1080p"},
        "precio_aprox": 250, "url_afiliado": "",
    },
]


def _fold(value: Any) -> str:
    text = unicodedata.normalize("NFKD", str(value or "").strip().casefold())
    return "".join(char for char in text if not unicodedata.combining(char))


def _text(value: Any, default: str = "") -> str:
    return str(value).strip() if isinstance(value, (str, int, float)) else default


def _platform(value: Any) -> str:
    folded = _fold(value)
    aliases = {
        "pc": "PC", "pc de escritorio": "PC", "escritorio": "PC",
        "playstation": "PlayStation", "xbox": "Xbox",
        "laptop con egpu": "Laptop con eGPU", "egpu": "Laptop con eGPU",
    }
    return aliases.get(folded, _text(value))


def _budget(value: Any) -> str:
    return {
        "entry": "Entry", "mid-range": "Mid-range", "mid range": "Mid-range",
        "enthusiast": "Enthusiast",
    }.get(_fold(value), _text(value))


def safe_amazon_url(value: Any) -> str | None:
    """Return a syntactically safe Amazon URL; this does not verify the listing.

    Direct links must contain an ASIN-shaped identifier. The allowlist prevents
    lookalike hosts, user-info tricks and arbitrary URLs from becoming buy CTAs.
    Official short links are allowed, without claiming to verify their target.
    """
    if not isinstance(value, str) or not value.strip():
        return None
    value = value.strip()
    if any(char.isspace() or ord(char) < 32 for char in value) or "\\" in value:
        return None
    try:
        parsed = urlsplit(value)
        if (
            parsed.scheme != "https" or parsed.username is not None
            or parsed.password is not None or parsed.port is not None
            or parsed.fragment or not parsed.hostname
        ):
            return None
    except (ValueError, TypeError):
        return None
    host = parsed.hostname.casefold()
    if host == "amzn.to":
        return value if re.fullmatch(r"/[A-Za-z0-9]{5,32}/?", parsed.path) else None
    if host.startswith("www."):
        host = host[4:]
    allowed = {
        "amazon.com", "amazon.es", "amazon.co.uk", "amazon.de", "amazon.fr",
        "amazon.it", "amazon.ca", "amazon.com.mx", "amazon.com.br",
        "amazon.co.jp", "amazon.in", "amazon.com.au", "amazon.nl", "amazon.se",
        "amazon.pl", "amazon.com.be", "amazon.sg", "amazon.ae", "amazon.sa",
        "amazon.eg", "amazon.com.tr", "amazon.ie", "amazon.co.za",
    }
    if host not in allowed:
        return None
    asin_path = re.search(r"/(?:dp|gp/product|gp/aw/d)/([A-Za-z0-9]{10})(?:/|$)", parsed.path)
    return value if asin_path else None


def normalize_products(records: Any) -> list[dict[str, Any]]:
    """Normalize a database result without modifying the supplied records."""
    if not isinstance(records, Iterable) or isinstance(records, (str, bytes, Mapping)):
        return []
    result: list[dict[str, Any]] = []
    seen_ids: set[str] = set()
    for index, record in enumerate(records):
        if not isinstance(record, Mapping):
            continue
        specs = record.get("specs_tecnicas", {})
        if isinstance(specs, str):
            try:
                specs = json.loads(specs)
            except (ValueError, TypeError):
                specs = {}
        specs = dict(specs) if isinstance(specs, Mapping) else {}
        product_id = _text(record.get("id"), f"producto-{index}") or f"producto-{index}"
        if product_id in seen_ids:
            product_id = f"{product_id}-{index}"
            while product_id in seen_ids:
                product_id += "-extra"
        seen_ids.add(product_id)
        category = _text(record.get("categoria"), "Otros") or "Otros"
        category = {
            "gpu": "GPU", "volante": "Volante", "monitor": "Monitor",
            "pedales": "Pedales", "cockpit": "Cockpit",
        }.get(_fold(category), category)
        price = record.get("precio_aprox")
        try:
            price = float(price) if not isinstance(price, bool) else None
            if price is not None and (not math.isfinite(price) or price < 0):
                price = None
        except (ValueError, TypeError):
            price = None
        raw_url = _text(record.get("url_afiliado"))
        result.append({
            **record,
            "id": product_id,
            "nombre": _text(record.get("nombre"), "Producto sin nombre") or "Producto sin nombre",
            "categoria": category,
            "nivel_presupuesto": _budget(record.get("nivel_presupuesto")) or "Sin clasificar",
            "specs_tecnicas": specs,
            "precio_aprox": price,
            "url_afiliado": raw_url,
            "amazon_url": safe_amazon_url(raw_url),
        })
    return result


def filter_products(
    products: Iterable[Mapping[str, Any]], query: str = "", budget: str = "Todos",
    category: str = "Todas",
) -> list[dict[str, Any]]:
    """Apply all supplied filters; accents and case do not affect text search."""
    result = []
    query_words = _fold(query).split()
    for product in products:
        if _fold(budget) not in {"", "todos", "todas"} and _budget(product.get("nivel_presupuesto")) != _budget(budget):
            continue
        if _fold(category) not in {"", "todos", "todas"} and _fold(product.get("categoria")) != _fold(category):
            continue
        searchable = _fold(" ".join([
            _text(product.get("nombre")), _text(product.get("categoria")),
            _text(product.get("nivel_presupuesto")),
            json.dumps(product.get("specs_tecnicas", {}), ensure_ascii=False, default=str),
        ]))
        if all(word in searchable for word in query_words):
            result.append(dict(product))
    return result


def _explicit_list(specs: Mapping[str, Any], key: str) -> list[str] | None:
    value = specs.get(key)
    if not isinstance(value, (list, tuple)):
        return None
    # An empty or malformed list cannot establish either support or exclusion.
    values = [_text(item) for item in value if isinstance(item, str) and item.strip()]
    return values or None


def assess_product(
    product: Mapping[str, Any], platform: str = "PC", simulator: str | None = None,
    resolution: str | None = None,
) -> dict[str, Any]:
    """Evaluate explicit compatibility and retain unknowns as visible warnings.

    ``compatible`` means the requested platform and (if supplied) simulator were
    declared by the catalogue. It is not a complete electrical/system check.
    Resolution is only a ranking hint and never changes compatibility status.
    """
    specs = product.get("specs_tecnicas", {})
    specs = specs if isinstance(specs, Mapping) else {}
    platform = _platform(platform)
    reasons: list[str] = []
    notes: list[str] = []
    excluded = False
    unknown = False
    category = _fold(product.get("categoria"))
    platforms = _explicit_list(specs, "plataformas")
    simulators = _explicit_list(specs, "simuladores")
    if platform in {"PlayStation", "Xbox"} and category == "gpu":
        excluded = True
        reasons.append("Una GPU de escritorio no se instala como ampliación de una consola.")
    elif platforms is None:
        unknown = True
        reasons.append(f"Falta confirmar la compatibilidad de esta variante con {platform}.")
    elif platform not in {_platform(item) for item in platforms}:
        excluded = True
        reasons.append(f"{platform} no figura entre las plataformas declaradas en esta ficha.")
    else:
        reasons.append(f"{platform} figura entre las plataformas declaradas en la ficha.")
    if simulator:
        if simulators is None:
            unknown = True
            reasons.append(f"La ficha aún no confirma soporte o requisitos para {simulator}.")
        elif _fold(simulator) not in {_fold(item) for item in simulators}:
            excluded = True
            reasons.append(f"{simulator} no figura entre los simuladores declarados en esta ficha.")
        else:
            reasons.append(f"{simulator} figura entre los simuladores declarados en la ficha.")
    target = _text(specs.get("resolucion_ideal"))
    resolution_match = _fold(target) == _fold(resolution) if target and resolution else None
    if resolution and target:
        notes.append(
            f"Objetivo registrado: {target}. Coincide con tu selección; no garantiza FPS."
            if resolution_match else
            f"Objetivo registrado: {target}; revisa pruebas a {resolution} antes de elegir."
        )
    elif resolution and category in {"gpu", "monitor"}:
        notes.append(f"No hay un objetivo de resolución registrado; confirma los requisitos a {resolution}.")
    if platform == "Laptop con eGPU":
        notes.append("Comprueba el conector, la caja eGPU, la fuente y el soporte del portátil.")
    if category == "volante":
        notes.append("Confirma la variante exacta, las conexiones y el anclaje antes de comprar.")
    if category == "gpu" and platform not in {"PlayStation", "Xbox"}:
        notes.append("Revisa la fuente, las dimensiones, la placa y los requisitos del equipo completo.")
    status = "incompatible" if excluded else "unknown" if unknown else "compatible"
    return {
        "status": status,
        "label": {"compatible": "Soporte declarado", "unknown": "Por confirmar", "incompatible": "No recomendado para esta selección"}[status],
        "reasons": reasons,
        "notes": notes,
        "resolution_match": resolution_match,
    }


def recommend_products(
    products: Iterable[Mapping[str, Any]], budget: str, platform: str = "PC",
    simulator: str | None = None, resolution: str | None = None,
) -> list[dict[str, Any]]:
    """Select at most one candidate per category for the exact budget level.

    Unknown compatibility remains explicit. This is a shortlist, not a promise
    that the combined products form a complete or fully compatible setup.
    """
    grouped: dict[str, list[tuple[tuple[int, int], dict[str, Any]]]] = {}
    for product in filter_products(products, budget=budget):
        assessment = assess_product(product, platform, simulator, resolution)
        if assessment["status"] == "incompatible":
            continue
        rank = (0 if assessment["status"] == "compatible" else 1,
                0 if assessment["resolution_match"] is True else 1)
        category_key = _fold(product.get("categoria"))
        grouped.setdefault(category_key, []).append((rank, {"product": product, "assessment": assessment}))
    return [sorted(options, key=lambda option: option[0])[0][1] for options in grouped.values()]
