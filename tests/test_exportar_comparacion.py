"""Check PDF content, safe links and pagination without network or credentials."""

import copy
from datetime import date
from io import BytesIO
import unittest

from pypdf import PdfReader

from catalogo import normalize_products
from exportar_comparacion import CATALOGUE_URL, build_comparison_pdf, comparison_rows, format_value


def fixture_products():
    return normalize_products([
        {
            "id": "INTERNAL-ID-DO-NOT-EXPORT", "nombre": "Logitech G923 + palanca (Xbox/PC, reacondicionado)",
            "categoria": "Volante", "nivel_presupuesto": "Entry", "precio_aprox": 98765,
            "secret": "ROOT-SECRET-DO-NOT-EXPORT",
            "url_afiliado": "https://www.amazon.com/dp/B0CXRN9K6P?tag=apexlabsimrac-20&linkCode=ll1",
            "specs_tecnicas": {
                "estado": "Reacondicionado", "plataformas": ["PC", "Xbox"],
                "tipo": "Engranaje", "fuerza_feedback": True,
                "incluye": ["Volante", "Pedales", "Palanca de cambios"],
                "requiere": "Mesa estable y juego compatible.",
                "advertencia": "Comprueba el contenido y el estado de la oferta reacondicionada.",
                "fuentes_fabricante": ["https://www.logitechg.com/es-cl/products/driving/g923-trueforce-sim-racing-wheel.html"],
                "fecha_revision": "2026-11-16",
            },
        },
        {
            "id": "monitor", "nombre": "LG UltraGear 27GS75Q-B · 27 pulgadas QHD",
            "categoria": "Monitor", "nivel_presupuesto": "Mid-range",
            "url_afiliado": "https://www.amazon.com/dp/B0DFZZHK6X?tag=apexlabsimrac-20",
            "specs_tecnicas": {
                "hz": 180, "resolucion": "2560 × 1440", "fuerza_feedback": False,
                "incluye": ["Pantalla", "Soporte"], "conexion": ["HDMI", "DisplayPort"],
                "advertencia": "La frecuencia depende de la conexión y la fuente de vídeo.",
                "ajustes": {"altura": "Sí", "inclinacion": "Sí"},
                "fuentes_fabricante": ["https://www.lg.com/us/monitors/lg-27gs75q-b-gaming-monitor"],
            },
        },
        {
            "id": "gpu", "nombre": "ASUS Dual RTX 5060 Ti OC 8GB",
            "categoria": "GPU", "nivel_presupuesto": "Enthusiast",
            "url_afiliado": "https://www.amazon.com/dp/B0F7W1KVT3?tag=apexlabsimrac-20",
            "specs_tecnicas": {"vram_gb": 8, "plataformas": ["PC"], "resolucion_ideal": "1440p", "requiere": "Fuente y espacio adecuados en el equipo."},
        },
    ])


def pdf_text(reader):
    return "\n".join(page.extract_text() or "" for page in reader.pages)


def pdf_links(reader):
    return [annotation.get_object()["/A"].get("/URI") for page in reader.pages for annotation in page.get("/Annots", []) if annotation.get_object().get("/A", {}).get("/S") == "/URI"]


class ComparisonPdfTests(unittest.TestCase):
    def test_pdf_retains_selection_facts_warnings_and_returns_to_catalogue(self):
        products = fixture_products()
        original = copy.deepcopy(products)
        data = build_comparison_pdf(products, generated_at=date(2026, 11, 16))
        self.assertTrue(data.startswith(b"%PDF-"))
        reader = PdfReader(BytesIO(data))
        text = pdf_text(reader)
        self.assertGreaterEqual(len(reader.pages), 4)
        for product in products:
            self.assertIn(product["nombre"], text)
            self.assertNotIn(product["url_afiliado"], pdf_links(reader))
            for field in ["requiere", "advertencia"]:
                if field in product["specs_tecnicas"]:
                    self.assertIn(product["specs_tecnicas"][field], text)
        self.assertIn("Reacondicionado", text)
        self.assertIn("2560 × 1440", text)
        self.assertIn("Por confirmar", text)
        self.assertIn("As an Amazon Associate I earn from qualifying purchases.", text)
        self.assertIn("16/11/2026", text)
        self.assertIn("APEX / LAB", reader.metadata.title)
        self.assertEqual(pdf_links(reader).count(CATALOGUE_URL), len(products))
        self.assertTrue(all("amazon." not in url and "amzn.to" not in url for url in pdf_links(reader)))
        self.assertNotIn("apexlabsimrac-20", text)
        self.assertEqual(products, original)
        for sensitive in ["INTERNAL-ID-DO-NOT-EXPORT", "ROOT-SECRET-DO-NOT-EXPORT", "98765"]:
            self.assertNotIn(sensitive, text)

    def test_unsafe_links_markup_private_fields_and_commerce_are_not_active(self):
        product = fixture_products()[0]
        product["nombre"] = 'Modelo <b>literal & seguro</b>'
        product["url_afiliado"] = "https://amazon.com.attacker.invalid/dp/B0CXRN9K6P?token=LEAK-URI"
        product["specs_tecnicas"].update({
            "requiere": '<img src="https://attacker.invalid/private.png"/> & <a href="javascript:alert(1)">texto</a>',
            "fuentes_fabricante": [
                "https://www.logitechg.com/productos/g923",
                "http://www.logitechg.com/insecure",
                "https://logitechg.com.attacker.invalid/fake",
                "https://user:LEAK-SOURCE@www.logitechg.com/private",
                "https://www.logitechg.com:444/wrong-port",
                "javascript:alert(1)",
            ],
            "supabase_key": "LEAK-KEY", "precio": "LEAK-PRICE", "stock": "LEAK-STOCK",
            "extras": {"secret_token": "LEAK-NESTED", "puerto": "USB-C"},
        })
        reader = PdfReader(BytesIO(build_comparison_pdf([product])))
        text = pdf_text(reader)
        self.assertIn("Modelo <b>literal & seguro</b>", text)
        self.assertIn("https://attacker.invalid/private.png", text)
        self.assertIn("puerto: USB-C", text)
        self.assertEqual(pdf_links(reader), ["https://www.logitechg.com/productos/g923"])
        for sensitive in ["LEAK-URI", "LEAK-SOURCE", "LEAK-KEY", "LEAK-PRICE", "LEAK-STOCK", "LEAK-NESTED"]:
            self.assertNotIn(sensitive, text)

    def test_long_detail_paginates_and_preserves_final_warning_and_nested_values(self):
        product = fixture_products()[0]
        product["nombre"] = "Volante de prueba con nombre completo " + "extendido " * 35
        product["specs_tecnicas"]["advertencia"] = "Precaución de montaje. " * 450 + "FIN DE ADVERTENCIA COMPLETA"
        product["specs_tecnicas"]["datos_adicionales"] = {"conectores": ["USB", {"adaptador": "No incluido"}], "ejes": 0}
        reader = PdfReader(BytesIO(build_comparison_pdf([product])))
        text = pdf_text(reader)
        self.assertGreater(len(reader.pages), 2)
        self.assertIn("FIN DE ADVERTENCIA COMPLETA", text)
        self.assertIn("adaptador: No incluido", text)
        self.assertIn("ejes: 0", text)
        self.assertIn("Consultar en el catálogo", text)
        self.assertEqual(len(pdf_links(reader)), 2)
        self.assertTrue(all(float(page.mediabox.width) > float(page.mediabox.height) for page in reader.pages))

    def test_three_regular_wheel_fiches_do_not_orphan_purchase_links(self):
        products = [copy.deepcopy(fixture_products()[0]) for _ in range(3)]
        for index, product in enumerate(products):
            product["id"] = f"wheel-{index}"
            product["nombre"] = f"Volante {index + 1} + pedales (plataforma y variante declaradas)"
            product["specs_tecnicas"].update({
                "plataformas_detalle": ["Windows PC", "Xbox Series X|S", "Xbox One"],
                "nota_variante": "Comprueba el estilo seleccionado en la oferta y los accesorios incluidos.",
            })
        reader = PdfReader(BytesIO(build_comparison_pdf(products)))
        self.assertEqual(len(reader.pages), 4)
        for page in reader.pages[1:]:
            text = page.extract_text()
            self.assertIn("Características registradas", text)
            self.assertIn("Consultar en el catálogo", text)
            self.assertIn("Fuente del fabricante", text)

    def test_pdf_replaces_direct_and_short_amazon_links_with_catalogue(self):
        for url in [
            "https://www.amazon.com/dp/B0CXRN9K6P?tag=apexlabsimrac-20",
            "https://www.amazon.es/dp/B0CXRN9K6P?tag=private-tracking-21",
            "https://amzn.to/abc1234",
        ]:
            with self.subTest(url=url):
                product = fixture_products()[0]
                product["url_afiliado"] = url
                reader = PdfReader(BytesIO(build_comparison_pdf([product])))
                self.assertIn(CATALOGUE_URL, pdf_links(reader))
                self.assertNotIn(url, pdf_links(reader))
                self.assertIn(product["specs_tecnicas"]["fuentes_fabricante"][0], pdf_links(reader))
                self.assertTrue(all("amazon." not in link and "amzn.to" not in link for link in pdf_links(reader)))

    def test_shared_matrix_preserves_explicit_unknown_zero_and_full_requirements(self):
        products = fixture_products()[:2]
        products[1]["specs_tecnicas"]["hz"] = 0
        products[0]["specs_tecnicas"]["advertencia"] += " Advertencia final intacta."
        rows = dict(comparison_rows(products))
        self.assertEqual(rows["Plataformas declaradas"], ["PC; Xbox", "Por confirmar"])
        self.assertEqual(rows["Force feedback"], ["Sí", "No"])
        self.assertEqual(rows["Frecuencia (Hz)"], ["No indicado", "0"])
        self.assertEqual(rows["Antes de comprar"][0], products[0]["specs_tecnicas"]["advertencia"])
        self.assertEqual(format_value({"salida": [False, 0, "2560 × 1440"]}), "salida: No; 0; 2560 × 1440")

    def test_rejects_empty_or_overfull_selection_and_invalid_date(self):
        for value in [[], fixture_products() + [fixture_products()[0]], None, [{}, "invalid"]]:
            with self.subTest(value=value), self.assertRaises(ValueError):
                build_comparison_pdf(value)
        with self.assertRaises(ValueError):
            build_comparison_pdf(fixture_products()[:1], generated_at="not-a-date")


if __name__ == "__main__":
    unittest.main()
