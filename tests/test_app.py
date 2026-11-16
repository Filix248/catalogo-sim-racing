"""Exercise real Streamlit interactions with an isolated, mocked catalogue.

Run with ``python -m unittest discover -s tests -v``. No network or local
Supabase credentials are used: every test supplies synthetic environment values
and patches the client's creation for all reruns.
"""

import copy
from html import unescape
import logging
import os
from pathlib import Path
import re
import unittest
from unittest.mock import MagicMock, patch

import streamlit as st
from streamlit.testing.v1 import AppTest

from catalogo import DEMO_PRODUCTS


ROOT = Path(__file__).resolve().parents[1]
logging.getLogger("streamlit.runtime.scriptrunner_utils.script_run_context").setLevel(logging.ERROR)


class AppInteractionTests(unittest.TestCase):
    def setUp(self):
        st.cache_data.clear()
        st.cache_resource.clear()
        self.environ = patch.dict(os.environ, {
            "SUPABASE_URL": "https://catalogue-test.invalid",
            "SUPABASE_KEY": "TEST-KEY-DO-NOT-RENDER",
        })
        self.environ.start()
        self.addCleanup(self.environ.stop)
        self.client_patch = patch("supabase.create_client")
        self.create_client = self.client_patch.start()
        self.addCleanup(self.client_patch.stop)
        self.client = MagicMock()
        self.create_client.return_value = self.client
        self.response = self.client.table.return_value.select.return_value.limit.return_value.execute.return_value
        self.response.data = copy.deepcopy(DEMO_PRODUCTS)
        self.addCleanup(st.cache_data.clear)
        self.addCleanup(st.cache_resource.clear)

    def app(self):
        app = AppTest.from_file(str(ROOT / "app.py"), default_timeout=20).run()
        self.assertHealthy(app)
        return app

    def assertHealthy(self, app):
        self.assertEqual(list(app.exception), [], [exception.value for exception in app.exception])

    def navigate(self, app, page):
        app.get("button_group")[0].set_value(page).run()
        self.assertHealthy(app)
        self.assertEqual(app.session_state["navigation"], page)

    def visible_ids(self, app, context="catalogue"):
        prefix = f"detail_{context}_"
        return [button.key.removeprefix(prefix) for button in app.button if button.key and button.key.startswith(prefix)]

    def test_combined_filters_and_reset_restore_catalogue(self):
        app = self.app()
        app.text_input(key="catalogue_query").set_value("nvidia").run()
        app.selectbox(key="catalogue_category").select("GPU").run()
        app.selectbox(key="catalogue_budget").select("Mid-range").run()
        self.assertHealthy(app)
        self.assertEqual(self.visible_ids(app), ["demo-4060"])
        app.toggle(key="only_saved").set_value(True).run()
        self.assertEqual(self.visible_ids(app), [])
        next(button for button in app.button if button.label == "Limpiar filtros").click().run()
        self.assertHealthy(app)
        self.assertEqual(app.session_state["catalogue_query"], "")
        self.assertEqual(app.session_state["catalogue_category"], "Todas")
        self.assertEqual(app.session_state["catalogue_budget"], "Todos")
        self.assertFalse(app.session_state["only_saved"])
        self.assertEqual(len(self.visible_ids(app)), len(DEMO_PRODUCTS))

    def test_saved_toggle_tracks_saving_and_removing_last_product(self):
        app = self.app()
        app.button(key="save_catalogue_demo-g923").click().run()
        self.assertEqual(app.session_state["saved"], ["demo-g923"])
        app.toggle(key="only_saved").set_value(True).run()
        self.assertEqual(self.visible_ids(app), ["demo-g923"])
        app.button(key="save_catalogue_demo-g923").click().run()
        self.assertHealthy(app)
        self.assertEqual(app.session_state["saved"], [])
        self.assertEqual(self.visible_ids(app), [])

    def test_card_comparison_remove_stays_removed_after_navigation(self):
        app = self.app()
        app.button(key="compare_catalogue_demo-g923").click().run()
        self.assertEqual(app.session_state["comparison"], ["demo-g923"])
        self.navigate(app, "Comparar")
        self.assertEqual(app.multiselect(key="compare_picker").value, ["demo-g923"])
        app.button(key="compare_comparison_demo-g923").click().run()
        self.assertHealthy(app)
        self.assertEqual(app.session_state["comparison"], [])
        self.assertEqual(app.multiselect(key="compare_picker").value, [])
        self.navigate(app, "Explorar")
        self.navigate(app, "Comparar")
        self.assertEqual(app.multiselect(key="compare_picker").value, [])
        self.assertEqual(app.session_state["comparison"], [])

    def test_picker_changes_sync_cards_and_survive_page_changes(self):
        app = self.app()
        self.navigate(app, "Comparar")
        app.multiselect(key="compare_picker").set_value(["demo-g923", "demo-t300"]).run()
        self.assertHealthy(app)
        self.assertEqual(app.session_state["comparison"], ["demo-g923", "demo-t300"])
        self.assertEqual(len(app.dataframe), 1)
        self.assertEqual(len(app.dataframe[0].value.columns), 3)
        app.multiselect(key="compare_picker").set_value(["demo-t300"]).run()
        self.navigate(app, "Explorar")
        self.assertEqual(app.button(key="compare_catalogue_demo-t300").label, "✓ Añadido")
        self.assertEqual(app.button(key="compare_catalogue_demo-g923").label, "+ Comparar")
        self.navigate(app, "Comparar")
        self.assertEqual(app.multiselect(key="compare_picker").value, ["demo-t300"])

    def test_comparison_limit_does_not_silently_replace_selection(self):
        app = self.app()
        for pid in ("demo-g923", "demo-t300", "demo-4060", "demo-4070"):
            app.button(key=f"compare_catalogue_{pid}").click().run()
        self.assertHealthy(app)
        self.assertEqual(app.session_state["comparison"], ["demo-g923", "demo-t300", "demo-4060"])
        self.navigate(app, "Comparar")
        self.assertEqual(len(app.multiselect(key="compare_picker").value), 3)

    def test_product_presentation_keeps_selection_and_shows_exact_purchase_details(self):
        affiliate_url = "https://www.amazon.com/dp/B0ABC12345/ref=nosim?tag=demo-20&th=1"
        requirement = "Necesita una base compatible con la plataforma y el juego elegido; el conjunto no funciona por sí solo en consola."
        warning = "No incluye volante ni pedales. Comprueba conexiones, firmware y anclaje antes de comprar; no conectes dos cables de datos simultáneamente."
        product = {
            "id": "test-shifter", "nombre": "Palanca de prueba", "categoria": "Palanca de cambios",
            "nivel_presupuesto": "Entry", "url_afiliado": affiliate_url,
            "specs_tecnicas": {
                "tipo": "Manual en H", "descripcion_editorial": "Palanca independiente para ampliar un equipo existente.",
                "requiere": requirement, "advertencia": warning,
                "incluye": ["Palanca", "Cable USB", "Fijación a mesa"],
                "fuentes_fabricante": ["https://www.thrustmaster.com/testing/shifter"],
            },
        }
        self.response.data = [product, copy.deepcopy(DEMO_PRODUCTS[0])]
        app = self.app()
        app.button(key="save_catalogue_demo-g923").click().run()
        app.button(key="compare_catalogue_demo-g923").click().run()
        app.text_input(key="catalogue_query").set_value("palanca").run()
        app.button(key="detail_catalogue_test-shifter").click().run()
        self.assertHealthy(app)
        self.assertEqual(app.session_state["saved"], ["demo-g923"])
        self.assertEqual(app.session_state["comparison"], ["demo-g923"])

        dialogs = app.get("dialog")
        self.assertEqual(len(dialogs), 1)
        self.assertTrue(dialogs[0].proto.dialog.is_open)
        rendered = unescape("\n".join(item.value for item in dialogs[0].get("markdown")))
        self.assertIn(product["nombre"], rendered)
        self.assertNotIn("Logitech G923", rendered)
        notices = [unescape(item.value) for item in dialogs[0].get("markdown") if "product-requirement" in item.value]
        self.assertTrue(any(requirement in notice for notice in notices))
        self.assertTrue(any(warning in notice for notice in notices))
        for included in product["specs_tecnicas"]["incluye"]:
            self.assertIn(included, rendered)
        purchase_links = [link for link in dialogs[0].get("link_button") if link.proto.label == "Consultar producto en Amazon ↗"]
        self.assertEqual([link.proto.url for link in purchase_links], [affiliate_url])

        app.button(key="close_detail_test-shifter").click().run()
        self.assertHealthy(app)
        self.assertEqual(list(app.get("dialog")), [])
        self.assertEqual(self.visible_ids(app), ["test-shifter"])
        self.assertEqual(app.session_state["catalogue_query"], "palanca")
        self.assertEqual(app.session_state["saved"], ["demo-g923"])
        self.assertEqual(app.session_state["comparison"], ["demo-g923"])

    def test_untrusted_manufacturer_urls_never_become_official_links_or_remote_images(self):
        affiliate_url = "https://www.amazon.com/dp/B0ABC12345?tag=demo-20"
        untrusted_sources = [
            "https://www.thrustmaster.com.evil.test/photos/product.jpg",
            "https://www.thrustmaster.com@evil.test/photos/product.jpg",
            "http://www.thrustmaster.com/photos/product.jpg",
            "https://evil.test/?redirect=https://www.thrustmaster.com",
            "https://www.thrustmaster.com:8443/photos/product.jpg",
        ]
        self.response.data = [{
            "id": "test-source", "nombre": "Accesorio con fuente sin verificar", "categoria": "Pedales",
            "nivel_presupuesto": "Entry", "url_afiliado": affiliate_url,
            "specs_tecnicas": {
                "fuentes_fabricante": untrusted_sources,
                "imagen_url": untrusted_sources[0], "imagenes": untrusted_sources,
            },
        }]
        app = self.app()
        app.button(key="detail_catalogue_test-source").click().run()
        self.assertHealthy(app)
        dialog = app.get("dialog")[0]
        self.assertEqual([link.proto.url for link in dialog.get("link_button")], [affiliate_url])
        rendered = "\n".join(item.value for item in dialog.get("markdown"))
        for untrusted in untrusted_sources:
            self.assertNotIn(untrusted, rendered)
        image_sources = re.findall(r'<img\b[^>]*\bsrc=["\x27]([^"\x27]+)', rendered)
        self.assertTrue(image_sources)
        self.assertTrue(all(not source.startswith(("https:", "http:", "//")) for source in image_sources))

    def test_xbox_setup_excludes_gpu_and_guides_still_navigate(self):
        app = self.app()
        self.navigate(app, "Mi setup")
        app.selectbox(key="setup_budget").select("Mid-range").run()
        app.selectbox(key="setup_platform").select("Xbox").run()
        self.assertHealthy(app)
        self.assertEqual(set(self.visible_ids(app, "setup")), {"demo-t300", "demo-monitor"})
        self.assertTrue(any("excluyeron 1" in expander.label for expander in app.expander))
        self.navigate(app, "Guías")
        self.assertTrue(any("variante exacta" in markdown.value for markdown in app.markdown))
        next(button for button in app.button if button.label == "Armar mi selección →").click().run()
        self.assertHealthy(app)
        self.assertEqual(app.session_state["navigation"], "Mi setup")

    def test_connection_failure_falls_back_without_exposing_error_or_key(self):
        self.create_client.side_effect = RuntimeError("TEST-KEY-DO-NOT-RENDER internal connection details")
        app = self.app()
        self.assertEqual(len(self.visible_ids(app)), len(DEMO_PRODUCTS))
        self.assertTrue(any("No pudimos cargar" in item.value for item in app.info))
        rendered = "\n".join(str(item.value) for kind in (app.markdown, app.caption, app.info, app.error) for item in kind)
        self.assertNotIn("TEST-KEY-DO-NOT-RENDER", rendered)
        self.assertNotIn("internal connection details", rendered)
        self.create_client.side_effect = None
        next(button for button in app.button if button.label == "Reintentar conexión").click().run()
        self.assertHealthy(app)
        self.assertFalse(any("No pudimos cargar" in item.value for item in app.info))
        self.assertTrue(any("Catálogo conectado" in item.value for item in app.markdown))


if __name__ == "__main__":
    unittest.main()
