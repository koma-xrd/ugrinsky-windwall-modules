"""Resolve the manual's inventory and dimensions from the current V5 release.

The loader has no CAD dependency and never regenerates assets. It requires the
drawing index to match the manifest hash. German names are editorial labels;
quantities, files, component ownership and dimensions come from the release.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path


PART_LABELS = {
    "base_rotor_module": "Base mit oberem Magnetträger",
    "standard_rotor_module": "Standardmodul",
    "top_rotor_module": "Topmodul",
    "lower_magnet_rotor": "Unterer Magnetrotor",
    "generator_housing": "Generatorgehäuse",
    "coil_cassette": "Spulenkassette",
    "generator_cover": "Stationärer Deckel",
    "top_support": "Oberer Lagerhalter",
}


def mm(value: float) -> str:
    """Format a measured or nominal length without spurious CAD decimals."""
    return f"{value:.2f}".rstrip("0").rstrip(".").replace(".", ",")


def dimensions(values) -> str:
    return " × ".join(mm(value) for value in values) + " mm"


def _release_path(project_root: Path, relative: str) -> Path:
    path = (project_root / relative).resolve()
    if not path.is_relative_to(project_root / "release/v5"):
        raise ValueError(f"Asset path must stay within release/v5: {relative}")
    if not path.is_file():
        raise FileNotFoundError(f"V5 release asset missing: {relative}")
    return path


def load_manual_data(project_root: Path) -> dict:
    """Read and validate V5 inputs before any DOCX is authored."""
    root = Path(project_root).resolve()
    manifest_path = root / "release/v5/manifest.json"
    raw_manifest = manifest_path.read_bytes()
    manifest = json.loads(raw_manifest)
    figures = json.loads((root / "release/v5/drawings/figures.json").read_text(encoding="utf-8"))
    german = json.loads((root / "scripts/manual/locales/de-DE.json").read_text(encoding="utf-8"))
    if manifest["release"] != "v5" or figures["release"] != "v5":
        raise ValueError("Manual requires the V5 release")
    if figures["source_manifest_sha256"] != hashlib.sha256(raw_manifest).hexdigest():
        raise ValueError("Drawing source manifest hash differs from release/v5/manifest.json")
    drawing_ids = [drawing["drawing_id"] for drawing in figures["figures"]]
    if drawing_ids != [f"E{index:02d}" for index in range(1, 16)]:
        raise ValueError("Manual requires E01 through E15 exactly once and in order")
    if set(german["drawings"]) != set(drawing_ids):
        raise ValueError("German drawing catalogue must cover E01 through E15 exactly")
    parts = manifest["production_parts"]
    if {part["name"] for part in parts} != set(PART_LABELS):
        raise ValueError("V5 production inventory has changed; review manual instructions")
    if sum(part["quantity"] for part in parts) != manifest["production_quantity"]:
        raise ValueError("V5 production quantities do not match the manifest total")
    for part in parts + manifest["coupons"]:
        _release_path(root, part["stl_path"])
        _release_path(root, part["step_path"])
    for assembly in manifest["assemblies"]:
        _release_path(root, assembly["step_path"])
    drawings = {}
    for drawing in figures["figures"]:
        if not drawing["caption"].strip() or len(drawing["alt_text"].strip()) < 40:
            raise ValueError(f"Meaningful caption and alt text required: {drawing['drawing_id']}")
        path = _release_path(root, "release/v5/drawings/" + drawing["filename"])
        localized = german["drawings"][drawing["drawing_id"]]
        if not localized["caption"].strip() or len(localized["alt_text"].strip()) < 40:
            raise ValueError(f"German drawing text is incomplete: {drawing['drawing_id']}")
        drawings[drawing["drawing_id"]] = {**drawing, **localized, "path": path}
    hero = {**german["hero"],
            "path": _release_path(root, "release/v5/media/windwall-fence-hero.png")}
    assemblies = {assembly["name"]: assembly for assembly in manifest["assemblies"]}
    components = {part["name"]: part for part in assemblies["fence_assembly"]["components"]}
    frame_parts = {part["name"]: part for part in drawings["E14"]["parts"]}
    bearings = manifest["parameters"]["bearings"]
    hardware = [
        (components["shaft"]["quantity"], "M8 Gewindestange", "Verlängerte Welle für oberen 608; erst nach Trockenmontage ablängen"),
        (sum(components[name]["quantity"] for name in ("upper_nut", "lower_nut", "top_nut")), "M8 Muttern", "Zwei formschlüssige Drehmomentmuttern und eine obere Klemmmutter"),
        (components["top_washer"]["quantity"], "Obere M8 Scheibe", dimensions((manifest["assembly_audit"]["hardware_envelopes"]["washer_diameter_mm"], manifest["assembly_audit"]["hardware_envelopes"]["washer_thickness_mm"])) + "; Außenmaß und Dicke"),
        (sum(components[name]["quantity"] for name in ("upper_magnets", "lower_magnets")), "Magnete", "Zwei Ringe mit je " + str(components["upper_magnets"]["quantity"]) + " Magneten; Projektziel 10 × 2 mm, reale Maße und Halterung prüfen"),
        (components["51105_shaft_washer"]["quantity"], "Axiallager 51105 komplett", dimensions((bearings["thrust_bore_diameter_mm"], bearings["thrust_outer_diameter_mm"], bearings["thrust_height_mm"]))),
        (components["bearing_608"]["quantity"], "Radiallager 608", dimensions((bearings["radial_bore_diameter_mm"], bearings["radial_outer_diameter_mm"], bearings["radial_height_mm"]))),
        (sum(part["quantity"] for name, part in components.items() if name.startswith("cover_screw_")), "M4 Deckelschrauben", "Länge und Kopfform am realen Stapel prüfen; keine freigegebene Kataloglänge"),
        (sum(part["quantity"] for name, part in components.items() if name.startswith("cover_nut_")), "Gefangene M4 Muttern", "Sechskant; vollständig in Gehäusetaschen einsetzen"),
        (sum(name.startswith("lower_wood_screw_") for name in frame_parts), "Holzschrauben unten", frame_parts["lower_wood_screw_1_reference"]["reference_note"]),
        (sum(name.startswith("wood_screw_") for name in frame_parts), "Holzschrauben oben", frame_parts["wood_screw_1_reference"]["reference_note"]),
    ]
    return {"manifest": manifest, "parts": parts, "drawings": drawings, "hero": hero,
            "components": components, "hardware": hardware,
            "coupons": {part["name"]: part for part in manifest["coupons"]}}
