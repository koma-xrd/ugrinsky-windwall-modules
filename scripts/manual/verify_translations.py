"""Run the bundled accessibility audit and renderer once per translated manual.

This does not author DOCX files. PATH is restricted to the dependency bundle so
the Windows renderer cannot silently launch desktop LibreOffice. Logs and any
rendered pages are local QA output, not distributable release artifacts.
"""

import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.manual.localize_manual import LOCALES, audit_translation


def verify(root, output_directory, document_skill_directory=None):
    runtime = next((p for p in Path(sys.executable).parents if p.name == "codex-primary-runtime"), None)
    if runtime is None:
        raise RuntimeError("Use the bundled document Python for document QA")
    skill = document_skill_directory or runtime / "plugins/openai-primary-runtime/plugins/documents/skills/documents"
    output_directory.mkdir(parents=True, exist_ok=True)
    temporary_directory = output_directory / "tmp"
    temporary_directory.mkdir(exist_ok=True)
    environment = dict(os.environ, PATH=str(runtime / "dependencies/bin/override"), PYTHONIOENCODING="utf-8",
                       TEMP=str(temporary_directory), TMP=str(temporary_directory))
    for locale, (name, _) in LOCALES.items():
        document = root / f"release/v5/docs/Ugrinsky-Wind-Wall-V5-Manual-{name}.docx"
        audit_translation(root, document, locale)
        a11y = subprocess.run([sys.executable, "-X", "utf8", str(skill / "scripts/a11y_audit.py"),
                               str(document), "--out_json", str(output_directory / f"{locale}-a11y.json")],
                              capture_output=True, text=True, encoding="utf-8", env=environment, check=False)
        print(f"{locale} accessibility exit {a11y.returncode}: {a11y.stdout.strip()}", flush=True)
        if a11y.returncode:
            raise RuntimeError(a11y.stderr or a11y.stdout)
        render = subprocess.run([sys.executable, "-X", "utf8", str(skill / "render_docx.py"), str(document),
                                 "--output_dir", str(output_directory / locale), "--emit_pdf", "--verbose"],
                                capture_output=True, text=True, encoding="utf-8", env=environment,
                                check=False, timeout=60)
        (output_directory / f"{locale}-render.log").write_text(render.stdout + render.stderr,
                                                                encoding="utf-8", newline="\n")
        output = render.stdout + render.stderr
        diagnosis = next((line for line in output.splitlines() if line.startswith("FileNotFoundError:")),
                         output.strip().splitlines()[-1] if output.strip() else "No renderer output")
        # Keep the cleanup diagnosis, but omit the random temporary profile path.
        cleanup_error = next((line.split(": '", 1)[0] for line in output.splitlines()
                              if line.startswith("PermissionError:")), None)
        evidence = {"artifact_sha256": hashlib.sha256(document.read_bytes()).hexdigest(),
                    "render_exit_code": render.returncode,
                    "render_error": diagnosis,
                    "render_cleanup_error": cleanup_error,
                    "page_png_count": len(list((output_directory / locale).glob("page-*.png")))}
        (output_directory / f"{locale}-evidence.json").write_text(json.dumps(evidence, indent=2) + "\n",
                                                                encoding="utf-8", newline="\n")
        print(f"{locale} packaged render exit {render.returncode}: {diagnosis}", flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project-root", type=Path, default=ROOT)
    parser.add_argument("--output-directory", type=Path, default=ROOT / "build/manual-i18n-qa")
    parser.add_argument("--document-skill-directory", type=Path,
                        help="Installed bundled document skill directory returned for this session")
    args = parser.parse_args()
    verify(args.project_root, args.output_directory, args.document_skill_directory)
