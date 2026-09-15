# V5 manual translation catalogues

Each UTF-8 JSON catalogue supplies all 310 unique source text runs and alternative
image descriptions from the reviewed German V5 DOCX. Keys are assigned in source
document order, followed by image descriptions. Repeated text shares a key. Pure
measurements, units and technical filenames remain in the source structure; figure
IDs and shared international labels may remain unchanged.

Run `scripts/manual/localize_manual.py --list-source` with the bundled document
Python to see the exact German text for every key. `source_sha256` binds the
catalogue to that immutable German package. The `locale` field selects language
metadata and script fonts. `translations` is an exact key-to-text mapping; missing
or additional keys, changed numeric tokens, filenames, missing required safety
phrases and untranslated German instructions fail validation before authoring.

The shared builder preserves all paragraphs and run formatting, 13 chapters,
11 tables, 16 inline images, page breaks, A4 pages and 18 mm margins. Captions and
complete alt descriptions are translated. The canonical English E01-E15 raster
drawings and shared hero image are reused unchanged and identified by their release
hashes. The two Word style parts
use the same explicit language, fonts and black heading styles. ZIP ordering,
timestamps and source metadata dates are deterministic.

For a source revision, review the whole translated content and update the source
binding deliberately; never bypass coverage or numeric checks to make a build pass.
Rebuild with the bundled document Python, run the manual and translation tests,
run packaged accessibility and rendering QA, and then update the multilingual audit
and release index as described in the root README. Catalogue files have `-text`
Git attributes so checksum bindings survive checkouts with automatic line endings.

Current limits: no independent native-speaker review is recorded. Packaged
LibreOffice is absent, so page layout and glyph rendering remain unverified.
The QA writer binds audit evidence to document bytes and refuses to treat an
unexpected rendering result as a successful page review.
