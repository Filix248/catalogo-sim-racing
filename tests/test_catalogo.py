"""Run with: python -m unittest discover -s tests -v."""

import copy
import unittest

from catalogo import (
    DEMO_PRODUCTS, assess_product, filter_products, normalize_products,
    recommend_products, safe_amazon_url,
)


class AmazonLinkTests(unittest.TestCase):
    def test_real_formats_and_short_links(self):
        for link in (
            "https://www.amazon.com/dp/B0ABC12345?tag=mi-tag-20",
            "https://amazon.es/nombre-producto/dp/B0ABC12345/",
            "https://amazon.com.mx/gp/product/B0ABC12345",
            "https://amazon.co.uk/gp/aw/d/B0ABC12345",
            "https://amzn.to/3abcDEF",
        ):
            with self.subTest(link=link):
                self.assertEqual(safe_amazon_url(link), link)

    def test_placeholders_and_untrusted_urls_do_not_become_buy_links(self):
        for link in (
            None, "", "https://amazon.com/dp/ejemplo1", "javascript:alert(1)",
            "https://amazon.com.evil.test/dp/B0ABC12345",
            "https://evil.test/amazon.com/dp/B0ABC12345",
            "https://amazon.com@evil.test/dp/B0ABC12345",
            "https://user:secret@amazon.com/dp/B0ABC12345",
            "https://amazon.com:9000/dp/B0ABC12345",
            "http://amazon.com/dp/B0ABC12345",
            "https://amazon.com/dp/B0ABC123456",
            "https://amzn.to/not/a/link", "https://amzn.to/abcd",
            "https://amazon.com\\@evil.test/dp/B0ABC12345",
            "https://amazon.com/dp/B0ABC12345\n?tag=bad",
        ):
            with self.subTest(link=link):
                self.assertIsNone(safe_amazon_url(link))


class NormalizationTests(unittest.TestCase):
    def test_bad_fields_are_safe_and_do_not_mutate_input(self):
        records = [
            {"id": "same", "nombre": " RTX ", "categoria": "gpu", "nivel_presupuesto": "mid range", "specs_tecnicas": '{"vram_gb": 8}', "precio_aprox": "NaN"},
            {"id": "same", "nombre": None, "specs_tecnicas": "broken", "precio_aprox": -1},
            None,
        ]
        original = copy.deepcopy(records)
        normalized = normalize_products(records)
        self.assertEqual(records, original)
        self.assertEqual(len(normalized), 2)
        self.assertEqual(normalized[0]["categoria"], "GPU")
        self.assertEqual(normalized[0]["nivel_presupuesto"], "Mid-range")
        self.assertEqual(normalized[0]["specs_tecnicas"], {"vram_gb": 8})
        self.assertIsNone(normalized[0]["precio_aprox"])
        self.assertIsNone(normalized[1]["precio_aprox"])
        self.assertEqual(normalized[1]["nombre"], "Producto sin nombre")
        self.assertNotEqual(normalized[0]["id"], normalized[1]["id"])

    def test_empty_input_and_demo_links(self):
        for records in (None, "text", {}, []):
            self.assertEqual(normalize_products(records), [])
        self.assertTrue(all(product["amazon_url"] is None for product in normalize_products(DEMO_PRODUCTS)))


class FilterTests(unittest.TestCase):
    def setUp(self):
        self.products = normalize_products(DEMO_PRODUCTS)

    def test_every_selected_filter_applies(self):
        found = filter_products(self.products, query="nvidia 4060", budget="Mid-range", category="gpu")
        self.assertEqual([p["nombre"] for p in found], ["NVIDIA RTX 4060"])
        self.assertEqual(filter_products(self.products, query="4060", budget="Entry"), [])

    def test_search_ignores_accents_case_and_word_order(self):
        products = normalize_products([{"nombre": "Pedalera hidráulica ÉLITE", "categoria": "Pedales"}])
        self.assertEqual(len(filter_products(products, query="ELITE hidraulica")), 1)


class CompatibilityTests(unittest.TestCase):
    def test_missing_metadata_does_not_confirm_named_variant(self):
        product = normalize_products(DEMO_PRODUCTS)[0]
        result = assess_product(product, "PlayStation", "Assetto Corsa", "1080p")
        self.assertEqual(result["status"], "unknown")
        self.assertEqual(len(result["reasons"]), 2)
        self.assertTrue(any("variante exacta" in note for note in result["notes"]))

    def test_gpu_is_excluded_from_console_even_if_metadata_claims_it(self):
        product = {"categoria": "GPU", "specs_tecnicas": {"plataformas": ["Xbox"]}}
        self.assertEqual(assess_product(product, "Xbox")["status"], "incompatible")

    def test_pc_support_does_not_establish_egpu_support(self):
        product = {"categoria": "GPU", "specs_tecnicas": {"plataformas": ["PC"]}}
        result = assess_product(product, "Laptop con eGPU")
        self.assertEqual(result["status"], "incompatible")
        self.assertTrue(any("conector" in note for note in result["notes"]))

    def test_all_requested_metadata_must_be_declared(self):
        product = {"categoria": "Volante", "specs_tecnicas": {"plataformas": ["PC"], "simuladores": ["Assetto Corsa"]}}
        self.assertEqual(assess_product(product, "PC de Escritorio", "Assetto Corsa")["status"], "compatible")
        self.assertEqual(assess_product(product, "PC", "iRacing")["status"], "incompatible")
        del product["specs_tecnicas"]["simuladores"]
        self.assertEqual(assess_product(product, "PC", "iRacing")["status"], "unknown")

    def test_resolution_does_not_claim_hardware_incompatibility(self):
        product = {"categoria": "GPU", "specs_tecnicas": {"plataformas": ["PC"], "resolucion_ideal": "1080p"}}
        result = assess_product(product, "PC", resolution="4K")
        self.assertEqual(result["status"], "compatible")
        self.assertFalse(result["resolution_match"])
        self.assertTrue(any("pruebas a 4K" in note for note in result["notes"]))

    def test_empty_platform_lists_are_unknown(self):
        self.assertEqual(assess_product({"specs_tecnicas": {"plataformas": []}}, "PC")["status"], "unknown")

    def test_generation_specific_support_is_not_broadened(self):
        product = {"categoria": "Volante", "specs_tecnicas": {"plataformas": ["PS4"]}}
        self.assertNotEqual(assess_product(product, "PlayStation")["status"], "compatible")


class RecommendationTests(unittest.TestCase):
    def test_shortlist_does_not_add_two_alternatives_of_same_type(self):
        products = normalize_products([
            {"id": "1", "nombre": "GPU A", "categoria": "GPU", "nivel_presupuesto": "Entry", "specs_tecnicas": {"resolucion_ideal": "1080p"}},
            {"id": "2", "nombre": "GPU B", "categoria": "GPU", "nivel_presupuesto": "Entry", "specs_tecnicas": {"resolucion_ideal": "1440p"}},
            {"id": "3", "nombre": "Monitor", "categoria": "Monitor", "nivel_presupuesto": "Entry"},
        ])
        found = recommend_products(products, "Entry", resolution="1440p")
        self.assertEqual(len(found), 2)
        self.assertEqual(found[0]["product"]["nombre"], "GPU B")

    def test_exact_budget_empty_and_incompatible_cases(self):
        products = normalize_products(DEMO_PRODUCTS)
        found = recommend_products(products, "Enthusiast", platform="Xbox")
        self.assertEqual(found, [])
        self.assertEqual(recommend_products([], "Entry"), [])
        entry = recommend_products(products, "Entry")
        self.assertEqual([p["product"]["nombre"] for p in entry], ["Logitech G923"])


if __name__ == "__main__":
    unittest.main()
