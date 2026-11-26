"""Exercise real Streamlit interactions with an isolated, mocked catalogue.

Run with ``python -m unittest discover -s tests -v``. No network or local
Supabase credentials are used: every test supplies synthetic environment values
and patches the client's creation for all reruns.
"""

import copy
from html import unescape
from io import BytesIO
import logging
import os
from pathlib import Path
import re
import unittest
from unittest.mock import MagicMock, patch

import streamlit as st
from streamlit.testing.v1 import AppTest
from pypdf import PdfReader

from catalogo import DEMO_PRODUCTS, load_public_catalogue


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
        app = AppTest.from_file(str(ROOT / "app.py"), default_timeout=20)
        # AppTest installs its own Secrets object for every run. Keep it
        # populated with synthetic empty values so no local file is consulted.
        app.secrets = {"SUPABASE_URL": "", "SUPABASE_KEY": ""}
        app.run()
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

    def test_quick_category_keeps_other_filters_and_collections(self):
        app = self.app()
        app.button(key="save_catalogue_demo-4060").click().run()
        app.button(key="compare_catalogue_demo-g923").click().run()
        app.text_input(key="catalogue_query").set_value("nvidia").run()
        app.selectbox(key="catalogue_budget").select("Mid-range").run()
        app.selectbox(key="catalogue_category").select("Volante").run()
        app.toggle(key="only_saved").set_value(True).run()
        self.assertEqual(self.visible_ids(app), [])

        app.button(key="browse_GPU").click().run()

        self.assertHealthy(app)
        self.assertEqual(app.selectbox(key="catalogue_category").value, "GPU")
        self.assertEqual(app.session_state["catalogue_query"], "nvidia")
        self.assertEqual(app.session_state["catalogue_budget"], "Mid-range")
        self.assertTrue(app.session_state["only_saved"])
        self.assertEqual(self.visible_ids(app), ["demo-4060"])
        self.assertEqual(app.session_state["saved"], ["demo-4060"])
        self.assertEqual(app.session_state["comparison"], ["demo-g923"])

    def test_browse_all_restores_filters_and_quick_filtered_presentation(self):
        app = self.app()
        app.button(key="save_catalogue_demo-g923").click().run()
        app.button(key="compare_catalogue_demo-4060").click().run()
        app.text_input(key="catalogue_query").set_value("nvidia").run()
        app.selectbox(key="catalogue_budget").select("Mid-range").run()
        app.button(key="browse_GPU").click().run()
        app.toggle(key="only_saved").set_value(True).run()
        self.assertEqual(self.visible_ids(app), [])

        app.button(key="browse_all").click().run()

        self.assertHealthy(app)
        self.assertEqual(app.session_state["catalogue_query"], "")
        self.assertEqual(app.selectbox(key="catalogue_category").value, "Todas")
        self.assertEqual(app.selectbox(key="catalogue_budget").value, "Todos")
        self.assertFalse(app.toggle(key="only_saved").value)
        self.assertEqual(set(self.visible_ids(app)), {product["id"] for product in DEMO_PRODUCTS})
        self.assertEqual(app.session_state["saved"], ["demo-g923"])
        self.assertEqual(app.session_state["comparison"], ["demo-4060"])

        app.button(key="browse_GPU").click().run()
        app.button(key="detail_catalogue_demo-4060").click().run()
        self.assertHealthy(app)
        dialog = app.get("dialog")[0]
        self.assertTrue(dialog.proto.dialog.is_open)
        rendered = unescape("\n".join(item.value for item in dialog.get("markdown")))
        self.assertIn("NVIDIA RTX 4060", rendered)
        self.assertNotIn("Logitech G923", rendered)
        app.button(key="close_detail_demo-4060").click().run()
        self.assertHealthy(app)
        self.assertEqual(list(app.get("dialog")), [])
        self.assertEqual(app.selectbox(key="catalogue_category").value, "GPU")
        self.assertEqual(set(self.visible_ids(app)), {"demo-4060", "demo-4070"})
        self.assertEqual(app.session_state["saved"], ["demo-g923"])
        self.assertEqual(app.session_state["comparison"], ["demo-4060"])

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
        preview = [item.value for item in app.markdown if 'class="comparison-preview"' in item.value]
        self.assertEqual(len(preview), 1)
        self.assertLess(preview[0].index("Logitech G923"), preview[0].index("Thrustmaster T300 RS"))
        app.multiselect(key="compare_picker").set_value(["demo-t300"]).run()
        self.navigate(app, "Explorar")
        self.assertEqual(app.button(key="compare_catalogue_demo-t300").label, "✓ Añadido")
        self.assertEqual(app.button(key="compare_catalogue_demo-g923").label, "+ Comparar")
        self.navigate(app, "Comparar")
        self.assertEqual(app.multiselect(key="compare_picker").value, ["demo-t300"])

    def test_comparison_download_is_pdf_of_current_selection_and_keeps_state(self):
        app = self.app()
        self.navigate(app, "Comparar")
        self.assertEqual(len(app.get("download_button")), 0)
        selected_ids = ["demo-t300", "demo-g923", "demo-4060"]
        by_id = {product["id"]: product for product in DEMO_PRODUCTS}
        with patch("streamlit.download_button", wraps=st.download_button) as download:
            for count in (1, 2, 3):
                with self.subTest(product_count=count):
                    current = selected_ids[:count]
                    app.multiselect(key="compare_picker").set_value(current).run()
                    self.assertHealthy(app)
                    kwargs = download.call_args.kwargs
                    self.assertEqual(kwargs["mime"], "application/pdf")
                    self.assertEqual(kwargs["file_name"], "mi-comparacion-apex.pdf")
                    self.assertTrue(kwargs["data"].startswith(b"%PDF-"))
                    text = "\n".join(page.extract_text() or "" for page in PdfReader(BytesIO(kwargs["data"])).pages)
                    for pid in current:
                        self.assertIn(by_id[pid]["nombre"], text)
                    for pid in selected_ids[count:]:
                        self.assertNotIn(by_id[pid]["nombre"], text)
                    buttons = app.get("download_button")
                    self.assertEqual(len(buttons), 1)
                    self.assertEqual(buttons[0].key, "download_comparison_pdf")
                    self.assertTrue(buttons[0].proto.ignore_rerun)
                    self.assertTrue(buttons[0].proto.url.endswith(".pdf"))
                    self.assertEqual(app.session_state["comparison"], current)
            self.navigate(app, "Explorar")
            self.navigate(app, "Comparar")
            self.assertEqual(app.multiselect(key="compare_picker").value, selected_ids)
            self.assertEqual(app.session_state["comparison"], selected_ids)
            self.assertEqual(app.get("download_button")[0].key, "download_comparison_pdf")

    def test_comparison_preview_escapes_catalogue_text_and_matches_selection(self):
        product = copy.deepcopy(DEMO_PRODUCTS[0])
        product.update({"id": "test-markup", "nombre": 'Volante <script>prueba</script> & "control"'})
        product["specs_tecnicas"] = {"tipo": '<b>Correa & engranaje</b>', "fuerza_feedback": False}
        self.response.data = [product, copy.deepcopy(DEMO_PRODUCTS[1])]
        app = self.app()
        self.navigate(app, "Comparar")
        app.multiselect(key="compare_picker").set_value(["test-markup"]).run()
        self.assertHealthy(app)
        previews = [item.value for item in app.markdown if 'class="comparison-preview"' in item.value]
        self.assertEqual(len(previews), 1)
        preview = previews[0]
        self.assertIn('Volante &lt;script&gt;prueba&lt;/script&gt; &amp; &quot;control&quot;', preview)
        self.assertIn('&lt;b&gt;Correa &amp; engranaje&lt;/b&gt;', preview)
        self.assertNotIn("<script>", preview)
        self.assertNotIn("Thrustmaster T300 RS", preview)
        self.assertIn("Force feedback", preview)
        self.assertIn("<td>No</td>", preview)

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
        backup, _ = load_public_catalogue(ROOT / "catalogo_publico.json")
        self.assertEqual(set(self.visible_ids(app)), {product["id"] for product in backup})
        self.assertTrue(any("Catálogo de respaldo · revisión 16/11/2026" in item.value for item in app.info))
        self.assertTrue(any("Catálogo de respaldo · revisión 16/11/2026" in item.value for item in app.markdown))
        self.assertFalse(any("datos de muestra" in item.value for item in app.info))
        rendered = "\n".join(str(item.value) for kind in (app.markdown, app.caption, app.info, app.error) for item in kind)
        self.assertNotIn("TEST-KEY-DO-NOT-RENDER", rendered)
        self.assertNotIn("internal connection details", rendered)
        self.create_client.side_effect = None
        next(button for button in app.button if button.label == "Reintentar conexión").click().run()
        self.assertHealthy(app)
        self.assertEqual(len(app.info), 0)
        self.assertTrue(any("Catálogo conectado" in item.value for item in app.markdown))

    def test_missing_configuration_uses_real_backup_without_reading_local_secrets(self):
        with patch.dict(os.environ, {"SUPABASE_URL": "", "SUPABASE_KEY": ""}):
            app = self.app()
        self.create_client.assert_not_called()
        self.assertEqual(len(self.visible_ids(app)), 16)
        self.assertTrue(any("Catálogo de respaldo" in item.value for item in app.info))
        first_id = self.visible_ids(app)[0]
        with patch.dict(os.environ, {"SUPABASE_URL": "", "SUPABASE_KEY": ""}):
            app.button(key=f"detail_catalogue_{first_id}").click().run()
        self.assertHealthy(app)
        purchase = [link for link in app.get("dialog")[0].get("link_button") if link.proto.label == "Consultar producto en Amazon ↗"]
        self.assertEqual(len(purchase), 1)
        self.assertIn("tag=apexlabsimrac-20", purchase[0].proto.url)

    def test_connected_empty_table_stays_empty_instead_of_restoring_backup(self):
        self.response.data = []
        with patch("catalogo.load_public_catalogue") as backup:
            app = self.app()
        backup.assert_not_called()
        self.assertEqual(self.visible_ids(app), [])
        self.assertFalse(any("Catálogo de respaldo" in item.value or "datos de muestra" in item.value for item in app.info))
        self.assertTrue(any("Catálogo conectado" in item.value for item in app.markdown))

    def test_connection_failure_and_corrupt_backup_use_labelled_demo_with_no_purchase_links(self):
        self.create_client.side_effect = RuntimeError("TEST-KEY-DO-NOT-RENDER")
        with patch("catalogo.load_public_catalogue", side_effect=ValueError("corrupt backup")):
            app = self.app()
            self.assertEqual(len(self.visible_ids(app)), len(DEMO_PRODUCTS))
            self.assertTrue(any("datos de muestra" in item.value for item in app.info))
            self.assertTrue(any("Catálogo de muestra" in item.value for item in app.markdown))
            app.button(key="detail_catalogue_demo-g923").click().run()
            self.assertHealthy(app)
            self.assertFalse(any(link.proto.label == "Consultar producto en Amazon ↗" for link in app.get("dialog")[0].get("link_button")))

    def test_comparison_and_saved_selection_survive_switch_from_live_to_backup(self):
        backup, _ = load_public_catalogue(ROOT / "catalogo_publico.json")
        self.response.data = copy.deepcopy(backup)
        self.response.data[0]["id"] = "different-database-id"
        app = self.app()
        product_id = backup[0]["id"]
        app.button(key=f"save_catalogue_{product_id}").click().run()
        app.button(key=f"compare_catalogue_{product_id}").click().run()
        self.client.table.return_value.select.return_value.limit.return_value.execute.side_effect = RuntimeError("connection interrupted")
        st.cache_data.clear()
        app.run()
        self.assertHealthy(app)
        self.assertEqual(app.session_state["saved"], [product_id])
        self.assertEqual(app.session_state["comparison"], [product_id])
        self.assertTrue(any("Catálogo de respaldo" in item.value for item in app.info))


if __name__ == "__main__":
    unittest.main()
