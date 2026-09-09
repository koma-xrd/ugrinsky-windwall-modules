# Manual release assets

This committed snapshot lets the German DOCX build and its document tests run
with bundled document Python on a clean checkout. It contains the CAD release
manifest and all eleven drawing PNGs created by `render_cad_figures` (E01–E06)
and `render_electrical_figures` (E07–E11). These are document assets, not certified
physical construction parts. Their original layout is retained so the shared
`load_manual_data` interface can consume the manifest without importing CAD.

The snapshot was captured from the assembly-manual worktree after commits
`e0eeb61` and `dd9bba1`. The drawings remain high-resolution 2400 × 1680 PNGs.
E04 was subsequently regenerated with a true +Z top-plan comparison of the same
insertion/locked CAD states, retaining the isometric engagement detail. Its
direction labels show insertion at -18 degrees, the locked zero and a CCW arrow.
The DOCX builder always reads this snapshot; local ignored build/output files do
not override it. Missing assets produce a clear error instead of invoking CAD
inside the document runtime.

When geometry or drawing content changes, rebuild the release manifest and both
drawing sets with the repository's separately configured CAD runtime. Review
them together, then replace the matching files under `release/` as one change.
Run the bundled document tests, rebuild the DOCX, run document audits and perform
the complete render/page-inspection loop before delivery. Do not update only a
manifest or only a drawing set: their geometry and annotations must agree.

The `release/build` and `release/output` folders are intentionally tracked
exceptions to the repository's general generated-file ignores. For an initial
snapshot or additional asset use `git add -f assets/manual/release`; normal
updates to existing tracked assets need no force.
