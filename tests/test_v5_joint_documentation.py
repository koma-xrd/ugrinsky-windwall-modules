"""Keep active assembly instructions aligned with the plain blade end release."""

import json
from pathlib import Path
import re
import unittest

ROOT = Path(__file__).resolve().parents[1]


class V5JointDocumentationTests(unittest.TestCase):
    def test_active_sources_have_no_obsolete_blade_interface_claims(self):
        paths = [ROOT / "README.md", ROOT / "release/v5/drawings/README.md", ROOT / "scripts/manual/build_manual.py",
                 ROOT / "scripts/manual/manual_data.py", ROOT / "scripts/manual/v5_figures.py",
                 *sorted((ROOT / "scripts/manual/locales").glob("*.json"))]
        forbidden = r"tongue|tongues|Nut[- ](?:und[- ])?Feder|obere Feder|untere Nut|blade[- ]seam load sharing|lower groove"
        for path in paths:
            with self.subTest(path=path.relative_to(ROOT)):
                self.assertIsNone(re.search(forbidden, path.read_text(encoding="utf-8"), re.I))

    def test_readme_explains_current_geometry_and_assembly(self):
        text = " ".join((ROOT / "README.md").read_text(encoding="utf-8").split()).lower()
        for phrase in ("flat 5 mm", "bottom-open m8 nut pocket", "plain flush blade ends",
                       "sole keyed torque interface", "insertion windows", "counterclockwise",
                       "flush blade contact", "inspect every latch", "stiffness", "bridge printability",
                       "dimensional fit", "powered operation", "unvalidated"):
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, text)

    def test_german_source_and_all_catalogues_explain_flat_carrier_and_joint(self):
        source = (ROOT / "scripts/manual/build_manual.py").read_text(encoding="utf-8")
        required = {
            "de-DE": ("plane 5 mm", "nach unten offene M8", "glatte bündige Blattenden", "einzige formschlüssige Drehmomentschnittstelle", "Einführfenster", "gegen den Uhrzeigersinn", "bündigen Blattkontakt", "Rastung", "Steifigkeit", "Brückendruck", "Maßpassung"),
            "en-GB": ("flat 5 mm", "bottom-open M8", "plain flush blade ends", "sole keyed torque interface", "insertion windows", "counterclockwise", "flush blade contact", "latch", "stiffness", "bridge printability", "dimensional fit"),
            "es-ES": ("plana de 5 mm", "M8 abierta por abajo", "extremos de pala lisos y enrasados", "única interfaz", "ventanas de inserción", "antihorario", "contacto enrasado", "pestillo", "rigidez", "puentes", "ajuste dimensional"),
            "fr-FR": ("plane de 5 mm", "M8 ouverte vers le bas", "extrémités de pales lisses et affleurantes", "seule interface", "fenêtres d’insertion", "antihoraire", "contact affleurant", "cliquet", "rigidité", "ponts", "ajustement dimensionnel"),
            "zh-CN": ("5 mm 平面", "底部开口的 M8", "平整齐平的叶片端部", "唯一的形锁合扭矩接口", "插入窗口", "逆时针", "齐平接触", "锁扣", "刚度", "桥接打印", "尺寸配合"),
            "hi-IN": ("5 mm समतल", "नीचे से खुला M8", "सादे समतल ब्लेड सिरे", "एकमात्र आकारबद्ध टॉर्क इंटरफ़ेस", "प्रवेश खिड़कियों", "वामावर्त", "समतल संपर्क", "लैच", "कठोरता", "ब्रिज प्रिंटिंग", "आयामी फिट"),
        }
        for locale, phrases in required.items():
            text = source if locale == "de-DE" else json.dumps(json.loads(
                (ROOT / f"scripts/manual/locales/{locale}.json").read_bytes())["translations"], ensure_ascii=False)
            for phrase in phrases:
                with self.subTest(locale=locale, phrase=phrase):
                    self.assertIn(phrase, text)

    def test_released_drawings_describe_plain_ends_and_flat_print_surface(self):
        inventory = json.loads((ROOT / "release/v5/drawings/figures.json").read_bytes())
        self.assertNotIn("blade_seam", inventory["render_parameters"])
        figures = {f["drawing_id"]: f for f in inventory["figures"]}
        for identifier in ("E02", "E03"):
            text = json.dumps(figures[identifier]).lower()
            self.assertIn("plain flush blade ends", text)
            self.assertIn("sole keyed torque interface", text)
        text = json.dumps(figures["E05"]).lower()
        for phrase in ("flat 5 mm", "bottom-open m8", "upper integral sleeve", "raised"):
            self.assertIn(phrase, text)

    def test_all_six_manual_audits_record_renderer_failure_without_page_approval(self):
        german = json.loads((ROOT / "release/v5/audits/manual.json").read_bytes())
        translated = json.loads((ROOT / "release/v5/audits/manual-translations.json").read_bytes())["documents"]
        for locale, audit in {"de-DE": german, **translated}.items():
            with self.subTest(locale=locale):
                self.assertEqual(audit["render_error"],
                                 "FileNotFoundError: LibreOffice soffice.exe was not found on PATH")
                self.assertEqual(audit.get("render_cleanup_error"), "PermissionError: [WinError 5] Zugriff verweigert")
                self.assertEqual(audit["rendered_page_count"], 0)
                self.assertEqual(audit["page_review"], "blocked_missing_bundled_soffice")
