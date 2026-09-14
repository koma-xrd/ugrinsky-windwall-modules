"""Translate the reviewed V5 DOCX without changing its German builder or images.

Catalogues translate unique text runs and image descriptions. Exact source and
input hashes reject stale catalogues; numeric tokens and full coverage fail
closed before authoring. OOXML layout is retained, with explicit language and
script fonts. Package audits are read-only and do not certify page rendering.
"""

from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import re
import sys
from zipfile import ZIP_DEFLATED, ZipFile, ZipInfo

from lxml import etree

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
SOURCE_MANUAL = "release/v5/docs/Ugrinsky-Wind-Wall-V5-Bauanleitung.docx"
SOURCE_SHA256 = "2101928cae0575febea5a57d2e791b4c62127ed155ffefd378134cb5dfe9d0a0"
LOCALES = {
    "en-GB": ("English", "Arial"),
    "zh-CN": ("Chinese-Simplified", "Microsoft YaHei"),
    "hi-IN": ("Hindi", "Nirmala UI"),
    "es-ES": ("Spanish", "Arial"),
    "fr-FR": ("French", "Arial"),
}
NS = {
    "w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main",
    "wp": "http://schemas.openxmlformats.org/drawingml/2006/wordprocessingDrawing",
    "a": "http://schemas.openxmlformats.org/drawingml/2006/main",
    "r": "http://schemas.openxmlformats.org/officeDocument/2006/relationships",
    "dc": "http://purl.org/dc/elements/1.1/",
    "cp": "http://schemas.openxmlformats.org/package/2006/metadata/core-properties",
}
TECHNICAL = {"PLA", "ASA", "M8", "M4", "51105", "608", "ID", "STL", "STEP", "N S N S"}
SHARED_LABELS = {"Base", "Generator"} | {f"E{i:02d}" for i in range(1, 16)}
LANGUAGE_CHECKS = {
    "en-GB": {"s008": "Do not connect", "s006": "not waterproof", "s130": "no final turn count",
              "s157": "active winding face", "s168": "strain relief"},
    "zh-CN": {"s008": "不得", "s006": "不防水", "s130": "没有最终匝数",
              "s157": "有效绕组表面", "s168": "应力释放"},
    "hi-IN": {"s008": "न जोड़ें", "s006": "जलरोधी नहीं", "s130": "कोई अंतिम टर्न संख्या",
              "s157": "सक्रिय वाइंडिंग सतह", "s168": "खिंचाव राहत"},
    "es-ES": {"s008": "No conecte", "s006": "no son impermeables", "s130": "No existe un número final",
              "s157": "superficie activa del bobinado", "s168": "alivio real de tracción"},
    "fr-FR": {"s008": "Ne raccordez pas", "s006": "ne sont pas étanches", "s130": "ni nombre définitif",
              "s157": "surface active du bobinage", "s168": "décharge de traction"},
}
HERO_QUALIFIERS = {
    "en-GB": "Unvalidated concept",
    "zh-CN": "未经验证的概念图",
    "hi-IN": "अप्रमाणित अवधारणा",
    "es-ES": "Concepto no validado",
    "fr-FR": "Concept non validé",
}


def digest(payload):
    return hashlib.sha256(payload).hexdigest()


def _is_translatable(text):
    if not text.strip() or text.strip() in TECHNICAL:
        return False
    if re.fullmatch(r"[\d\s.,×/+−–-]+(?: mm)?", text):
        return False
    if re.fullmatch(r"[A-Za-z0-9_./-]+\.(?:stl|step|png)", text):
        return False
    return True


def _source_package(root):
    payload = (Path(root) / SOURCE_MANUAL).read_bytes()
    if digest(payload) != SOURCE_SHA256:
        raise ValueError("German source hash changed; review every translation")
    with ZipFile(Path(root) / SOURCE_MANUAL) as archive:
        return {name: archive.read(name) for name in archive.namelist()}


def _text_nodes(package):
    document = etree.fromstring(package["word/document.xml"])
    nodes = [(node, "text", node.text or "") for node in document.xpath("//w:t", namespaces=NS)]
    nodes += [(node, "descr", node.get("descr", ""))
              for node in document.xpath("//wp:docPr", namespaces=NS)]
    return document, nodes


def _drawing_aliases(root):
    """Map localized German drawing metadata to the canonical English source text."""
    german = json.loads((Path(root) / "scripts/manual/locales/de-DE.json").read_bytes())["drawings"]
    figures = json.loads((Path(root) / "release/v5/drawings/figures.json").read_bytes())["figures"]
    aliases = {}
    for drawing in figures:
        localized = german[drawing["drawing_id"]]
        prefix = drawing["drawing_id"] + "  "
        aliases[prefix + localized["caption"]] = prefix + drawing["caption"]
        aliases[localized["alt_text"]] = drawing["alt_text"]
    return aliases


def source_segments(root):
    """Stable segment IDs are ordered and bound to the exact German package."""
    _, nodes = _text_nodes(_source_package(root))
    aliases = _drawing_aliases(root)
    hero_source = set(json.loads((Path(root) / "scripts/manual/locales/de-DE.json").read_bytes())["hero"].values())
    texts = list(dict.fromkeys(aliases.get(text, text) for _, _, text in nodes
                               if text not in hero_source and _is_translatable(text)))
    return {f"s{index:03d}": text for index, text in enumerate(texts, 1)}


def numeric_tokens(text):
    return Counter(token.replace(",", ".") for token in re.findall(r"\d+(?:[.,]\d+)?", text))


def validate_catalog(source, catalog):
    translations = catalog["translations"]
    if set(source) != set(translations):
        raise ValueError("Translation coverage differs from the complete source")
    for key, original in source.items():
        translated = translations[key]
        if not isinstance(translated, str) or not translated.strip():
            raise ValueError(f"Empty translation: {key}")
        if numeric_tokens(original) != numeric_tokens(translated):
            raise ValueError(f"Translation numeric invariants differ: {key}")
        canonical_english_drawing = bool(re.match(r"^E\d{2}[ .]", original.strip()))
        if (original.strip() == translated.strip() and original not in SHARED_LABELS
                and not (catalog["locale"] == "en-GB" and canonical_english_drawing)):
            raise ValueError(f"Untranslated German instruction: {key}")
        for filename in re.findall(r"[A-Za-z0-9_./-]+\.(?:stl|step|png|json)", original):
            if filename not in translated:
                raise ValueError(f"Technical filename changed: {key}")
    for key, phrase in LANGUAGE_CHECKS[catalog["locale"]].items():
        if phrase not in translations[key]:
            raise ValueError(f"Required safety or technical translation missing: {key}")
    if LANGUAGE_CHECKS[catalog["locale"]]["s008"] not in translations["s233"]:
        raise ValueError("Required battery safety prohibition missing in commissioning")
    prose = "\n".join(translations.values())
    for german in ("Wälzkörper", "Drehzahl", "Wicklung", "Bauanleitung", "Gehäusescheibe", "nicht wasserdicht"):
        if german in prose:
            raise ValueError(f"German instructional leakage: {german}")
    script = {"zh-CN": r"[\u4e00-\u9fff]", "hi-IN": r"[\u0900-\u097f]"}.get(catalog["locale"])
    if script and any(not re.search(script, value) for key, value in translations.items()
                      if source[key] not in SHARED_LABELS):
        raise ValueError("Translation lacks the required writing script")


def load_catalog(root, locale):
    if locale not in LOCALES:
        raise ValueError(f"Unsupported manual locale: {locale}")
    path = Path(root) / f"scripts/manual/locales/{locale}.json"
    catalog = json.loads(path.read_bytes())
    if catalog["locale"] != locale or catalog["source_sha256"] != SOURCE_SHA256:
        raise ValueError("Translation catalogue source or locale is stale")
    if set(catalog.get("hero", {})) != {"caption", "alt_text"}:
        raise ValueError("Localized hero caption and alternative text are required")
    if (not isinstance(catalog["hero"]["caption"], str)
            or not catalog["hero"]["caption"].strip()
            or not isinstance(catalog["hero"]["alt_text"], str)
            or len(catalog["hero"]["alt_text"].strip()) < 40):
        raise ValueError("Localized hero text is incomplete")
    if HERO_QUALIFIERS[locale] not in catalog["hero"]["alt_text"]:
        raise ValueError("Hero alternative text must identify the unvalidated concept")
    validate_catalog(source_segments(root), catalog)
    return catalog


def _xml(element):
    return etree.tostring(element, xml_declaration=True, encoding="UTF-8", standalone=True)


def _translated_package(root, locale):
    package = _source_package(root)
    catalog = load_catalog(root, locale)
    mapping = {text: catalog["translations"][key] for key, text in source_segments(root).items()}
    for localized, canonical in _drawing_aliases(root).items():
        mapping[localized] = mapping[canonical]
    german_hero = json.loads((Path(root) / "scripts/manual/locales/de-DE.json").read_bytes())["hero"]
    mapping[german_hero["caption"]] = catalog["hero"]["caption"]
    mapping[german_hero["alt_text"]] = catalog["hero"]["alt_text"]
    document, nodes = _text_nodes(package)
    for node, attribute, original in nodes:
        if original not in mapping:
            if attribute == "text" and locale in ("en-GB", "zh-CN", "hi-IN"):
                node.text = re.sub(r"(?<=\d),(?=\d)", ".", original)
            continue
        if attribute == "text":
            node.text = mapping[original]
        else:
            node.set(attribute, mapping[original])
    package["word/document.xml"] = _xml(document)
    styles = etree.fromstring(package["word/styles.xml"])
    for lang in styles.xpath("//w:lang", namespaces=NS):
        for attribute in ("val", "eastAsia", "bidi"):
            lang.set(f"{{{NS['w']}}}{attribute}", locale)
    for fonts in styles.xpath("//w:rFonts", namespaces=NS):
        for attribute in ("asciiTheme", "hAnsiTheme", "eastAsiaTheme", "cstheme"):
            fonts.attrib.pop(f"{{{NS['w']}}}{attribute}", None)
        for attribute in ("ascii", "hAnsi", "eastAsia", "cs"):
            fonts.set(f"{{{NS['w']}}}{attribute}", LOCALES[locale][1])
    package["word/styles.xml"] = _xml(styles)
    # Modern Word may select the effects style part. Use the same authoritative
    # styles there so template language, theme colours and fonts cannot return.
    if "word/stylesWithEffects.xml" in package:
        package["word/stylesWithEffects.xml"] = package["word/styles.xml"]
    core = etree.fromstring(package["docProps/core.xml"])
    for tag, text in (("dc:title", catalog["translations"]["s001"]),
                      ("dc:subject", catalog["translations"]["s002"]),
                      ("dc:language", locale), ("dc:creator", "Windwall Project"),
                      ("cp:lastModifiedBy", "Windwall Project")):
        core.find(tag, NS).text = text
    package["docProps/core.xml"] = _xml(core)
    return package


def _input_binding(root):
    root = Path(root)
    german_audit = json.loads((root / "release/v5/audits/manual.json").read_bytes())
    result = {}
    for key, relative in (("geometry_manifest_sha256", "release/v5/manifest.json"),
                          ("figures_manifest_sha256", "release/v5/drawings/figures.json")):
        result[key] = digest((root / relative).read_bytes())
        if result[key] != german_audit[key]:
            raise ValueError("German manual audit input binding is stale")
    figures = json.loads((root / "release/v5/drawings/figures.json").read_bytes())
    drawings = {item["filename"]: digest((root / "release/v5/drawings" / item["filename"]).read_bytes())
                for item in figures["figures"]}
    if drawings != german_audit["drawing_sha256_by_filename"]:
        raise ValueError("German manual drawing binding is stale")
    result["drawing_sha256_by_filename"] = drawings
    result["hero_sha256"] = digest((root / "release/v5/media/windwall-fence-hero.png").read_bytes())
    if result["hero_sha256"] != german_audit.get("hero_sha256"):
        raise ValueError("German manual hero binding is stale")
    result["source_manual_sha256"] = SOURCE_SHA256
    return result


def audit_translation(root, path, locale):
    """Inspect the complete package without writing or launching a renderer."""
    path = Path(path)
    expected = _translated_package(root, locale)
    binding = _input_binding(root)
    with ZipFile(path) as archive:
        if set(archive.namelist()) != set(expected):
            raise ValueError("Translation package members differ")
        for name, payload in expected.items():
            if archive.read(name) != payload:
                raise ValueError(f"Translation package content differs: {name}")
        canonical = (archive.namelist() == sorted(expected) and
                     all(i.date_time == (2026, 9, 9, 0, 0, 0) and i.compress_type == ZIP_DEFLATED
                         for i in archive.infolist()))
        if not canonical:
            raise ValueError("Translation ZIP is not canonical")
    doc = etree.fromstring(expected["word/document.xml"])
    styles = etree.fromstring(expected["word/styles.xml"])
    headings = doc.xpath("//w:p[w:pPr/w:pStyle[@w:val='Heading1']]", namespaces=NS)
    numbers = [int("".join(p.xpath(".//w:t/text()", namespaces=NS)).split()[0]) for p in headings]
    tables = doc.xpath("//w:tbl", namespaces=NS)
    images = doc.xpath("//wp:inline", namespaces=NS)
    captions = doc.xpath("//w:p[w:pPr/w:pStyle[@w:val='Caption']]", namespaces=NS)
    checks = [numbers == list(range(1, 14)), len(tables) == 11, len(images) == 16,
              len(captions) == 16, not doc.xpath("//wp:anchor", namespaces=NS)]
    checks += [bool(t.xpath("./w:tr[1]/w:trPr/w:tblHeader", namespaces=NS)) for t in tables]
    checks += [len(t.xpath("./w:tblPr/w:tblBorders/*[@w:color='D9D9D9']", namespaces=NS)) == 6
               and bool(t.xpath("./w:tblPr/w:tblCellMar", namespaces=NS))
               and not t.xpath(".//w:trHeight[@w:hRule='exact']", namespaces=NS) for t in tables]
    checks += [len(i.xpath("./wp:docPr/@descr", namespaces=NS)[0]) >= 40 for i in images]
    for style in ("Title", "Subtitle", "Heading1", "Heading2", "Heading3"):
        element = styles.xpath(f"//w:style[@w:styleId='{style}']", namespaces=NS)[0]
        checks.append(element.xpath("./w:rPr/w:color/@w:val", namespaces=NS) == ["000000"])
        checks.append(not element.xpath(".//w:pBdr | .//w:color/@w:themeColor", namespaces=NS))
    section = doc.xpath("//w:sectPr", namespaces=NS)[0]
    q = lambda name: f"{{{NS['w']}}}{name}"
    size, margins = section.find(q("pgSz")), section.find(q("pgMar"))
    checks.append([size.get(q("w")), size.get(q("h"))] == ["11906", "16838"])
    checks.append(all(margins.get(q(side)) == "1020" for side in ("top", "right", "bottom", "left")))
    checks.append(all(lang.get(q("val")) == locale for lang in styles.xpath("//w:lang", namespaces=NS)))
    media = {name: digest(payload) for name, payload in expected.items() if name.startswith("word/media/")}
    expected_media = list(binding["drawing_sha256_by_filename"].values()) + [binding["hero_sha256"]]
    if Counter(media.values()) != Counter(expected_media):
        raise ValueError("Translation embedded images do not match release drawings")
    rels = etree.fromstring(expected["word/_rels/document.xml.rels"])
    targets = {r.get("Id"): "word/" + r.get("Target") for r in rels}
    image_bindings = {}
    for inline in images:
        figure_id = inline.xpath("./wp:docPr/@title", namespaces=NS)[0]
        relation = inline.xpath(".//a:blip/@r:embed", namespaces=NS)[0]
        image_bindings[figure_id] = media[targets[relation]]
    if not all(checks):
        raise ValueError("Translation structural checks failed")
    filename = f"Ugrinsky-Wind-Wall-V5-Manual-{LOCALES[locale][0]}.docx"
    catalog_path = f"scripts/manual/locales/{locale}.json"
    return {**binding, "artifact_path": "release/v5/docs/" + filename, "locale": locale,
            "artifact_sha256": digest(path.read_bytes()), "size_bytes": path.stat().st_size,
            "catalog_path": catalog_path, "catalog_sha256": digest((Path(root) / catalog_path).read_bytes()),
            "chapter_count": 13, "figure_count": 16, "table_count": 11, "segment_count": len(source_segments(root)),
            "structural_checks_passed": True, "canonical_zip_verified": True,
            "embedded_images_match_release": 16, "image_binding_sha256_by_id": image_bindings,
            "page_size_mm": [210, 297], "margins_mm": [18, 18, 18, 18],
            "physical_validation_verified": False}


def build_translation(root, locale, output):
    _input_binding(root)
    package = _translated_package(root, locale)
    output = Path(output)
    output.parent.mkdir(parents=True, exist_ok=True)
    with ZipFile(output, "w", ZIP_DEFLATED) as archive:
        for name in sorted(package):
            info = ZipInfo(name, (2026, 9, 9, 0, 0, 0))
            info.compress_type = ZIP_DEFLATED
            archive.writestr(info, package[name])
    return output


def write_audit(root, qa_directory):
    """Record measured structural/a11y evidence and explicit renderer failure."""
    reports = {}
    for locale, (name, _) in LOCALES.items():
        document = Path(root) / f"release/v5/docs/Ugrinsky-Wind-Wall-V5-Manual-{name}.docx"
        report = audit_translation(root, document, locale)
        evidence = json.loads((Path(qa_directory) / f"{locale}-evidence.json").read_bytes())
        if evidence["artifact_sha256"] != report["artifact_sha256"]:
            raise ValueError("Accessibility/render evidence belongs to an older document")
        a11y = json.loads((Path(qa_directory) / f"{locale}-a11y.json").read_bytes())
        report["accessibility_findings"] = a11y["counts"]
        if any(report["accessibility_findings"].values()):
            raise ValueError(f"Accessibility findings require review: {locale}")
        render = (Path(qa_directory) / f"{locale}-render.log").read_text(encoding="utf-8")
        if ("soffice" not in render or "FileNotFoundError" not in render
                or evidence["render_exit_code"] == 0 or evidence["page_png_count"] != 0):
            raise ValueError("Expected missing bundled soffice diagnosis; review actual render result")
        report["page_review"] = "blocked_missing_bundled_soffice"
        report["rendered_page_count"] = 0
        report["render_exit_code"] = evidence["render_exit_code"]
        report["render_attempt"] = "packaged_render_docx_with_emit_pdf_failed_missing_soffice"
        report["render_limitations"] = "Page layout, glyph rendering, pagination and PDF output remain unverified."
        reports[locale] = report
    audit = {"schema_version": 1, "source_manual": SOURCE_MANUAL,
             "inspection_runtime": "bundled_codex_document_python", "documents": reports,
             "translation_method": "Complete source-run and image-description catalogues; shared deterministic OOXML builder",
             "drawing_language_note": "E01-E15 use canonical English raster annotations in every manual; captions and complete alternative descriptions are localized.",
             "translation_review": "Automated structural, coverage, numeric and terminology checks; no independent native-speaker review recorded."}
    path = Path(root) / "release/v5/audits/manual-translations.json"
    path.write_text(json.dumps(audit, ensure_ascii=False, sort_keys=True, indent=2) + "\n", encoding="utf-8", newline="\n")
    return path


def build_translations(root, output_directory):
    return {locale: build_translation(root, locale, Path(output_directory) /
            f"Ugrinsky-Wind-Wall-V5-Manual-{name}.docx")
            for locale, (name, _) in LOCALES.items()}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project-root", type=Path, default=ROOT)
    parser.add_argument("--list-source", action="store_true")
    parser.add_argument("--output-directory", type=Path)
    parser.add_argument("--audit-only", action="store_true")
    parser.add_argument("--qa-directory", type=Path)
    args = parser.parse_args()
    if args.list_source:
        print(json.dumps(source_segments(args.project_root), ensure_ascii=False, indent=2))
        return
    if args.audit_only:
        if args.qa_directory:
            print(write_audit(args.project_root, args.qa_directory))
        else:
            for locale, (name, _) in LOCALES.items():
                path = args.project_root / f"release/v5/docs/Ugrinsky-Wind-Wall-V5-Manual-{name}.docx"
                print(json.dumps(audit_translation(args.project_root, path, locale), ensure_ascii=False))
        return
    for locale, path in build_translations(args.project_root, args.output_directory or
                                           args.project_root / "release/v5/docs").items():
        print(locale, path)


if __name__ == "__main__":
    main()
