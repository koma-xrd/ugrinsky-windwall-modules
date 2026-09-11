# Release packages

Printable and editable deliverables are grouped by release version. Use the
highest version unless a build note explicitly asks for an earlier prototype.

## Available releases

- [`v5/`](v5/) — current V5.2 prototype release

## Folder layout

Each version uses the same predictable structure:

| Folder or file | Contents |
| --- | --- |
| `stl/` | Ready-to-slice printable parts |
| `step/` | Editable CAD exchange files |
| `coupons/` | Small fit and joint test prints |
| `assembly/` | Complete reference assemblies |
| `docs/` | Assembly manuals and translations |
| `drawings/` | Exploded views and technical figures |
| `media/` | README and presentation images or animations |
| `audits/` | Generated review and translation evidence |
| `manifest.json` | Part dimensions, roles, and build metadata |
| `release-index.json` | File inventory and integrity hashes |

Start with the fit coupons before printing the complete rotor or generator.
The generated files remain prototype parts until their documented physical-fit
checks have been completed on the intended printer and material.
