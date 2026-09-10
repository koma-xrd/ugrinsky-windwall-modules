# Generator reference measurements

These are STL measurements, not physical magnet or bearing measurements.
The original downloaded files remain external to the repository. Binary STL
triangles were sliced with `slice_triangles`/`join_segments` from the existing
measurement script; circular contours were fitted with a 0.05 mm maximum RMS.
No reference mesh enters production CadQuery geometry.

| External file | Measured features, mm | Reconstruction decision |
| --- | --- | --- |
| `3 magnet_ring (2).stl` | Envelope 103.994 x 103.994 x 10; disc z=0..3, floor z=0.998; 18 pockets approximately 11.004 diameter on radius 44.5; shaft hole 8.205; rear boss about 20 diameter | Regularize pockets to 11 x 2. Increase OD to 106 and floor to 3 for loaded walls. Use common 8.8 shaft bore, 34 hub and ribs; total height 10. |
| `2 Coil_Former.stl` | Envelope 118 x 118 x 12; floor 2; cavity diameter 114.005; center bore 12.405; upper center opening 42.505, center boss OD60; 18 rounded guide contours at mid-height | Reconstruct the functional 18-island open serpentine guide in the removable cassette while retaining the V5 housing interface. |
| `4 Stator_Cover_PLate.stl` | 112 OD, 62.005 ID, thickness 2 | Separate 112/62 x 2 annulus above former, conservative 14 total. |
| `1 Base.stl` | 120 OD, cavity 114.006, height 27, floor 3 | Keep cup envelope, add parameterized through-bore/boss for shaft bearing reference. |
| `5 Top_Bearing.stl` | Central bore 12.305, upper boss OD20, overall height14; outer fitting is noncircular | Does not identify an 8 mm bearing product. Reserve provisional 12 OD, 8 ID, 6 long sleeve in 12.3 seat; axial retention remains open. |

Pocket fits at source z=1 mm yield radii 5.5018..5.5027 mm with RMS below
0.00034 mm; these are mesh-fit residuals, not manufacturing accuracy. Slices
at z=0.5 have only the outer contour and shaft hole, while z=1.5 and 2.5 also
have all 18 pockets. Unique ring Z planes are 0, 0.998, 3 and 10 mm, establishing
the blind pocket depth. Polygon interpolation reduces the fitted outer radius
slightly; the envelope dimensions are used for nominal OD. The source rear
boss center is offset approximately (0.097,-0.203) mm from its shaft axis;
the reconstruction explicitly centers every rotating/stationary interface.

The CAD coupon provides 10.8, 11.0 and 11.2 mm diameters with the same 2 mm
depth and a 3 mm floor. Actual magnet diameter, thickness, protrusion and
retention need physical verification. The nominal 1.5 mm gaps are measured
from carrier pocket planes and only bound magnets that are flush or recessed.

Source SHA-256 fingerprints:

| File | SHA-256 |
| --- | --- |
| Magnet ring | `f838e07b7d8b0bba026da2a16ac24db00db2e2a82593bac2e12a3e302d5315f2` |
| Coil former | `118014450fdb95d35e3b54a70433b43965bff0429117a6b3ead8034dfc92dd15` |
| Cover | `4595dd91982b0b855eb9213f087ba8558134e393ad1d67a340f122bf599af6e1` |
| Base | `31c3883c701b0496af80390d83a7dd05ace5eba325551d031f61dc94d46ef3c2` |
| Top bearing feature | `7820a23cad35b0c7bda16438d50e9a4688b4403797a426ecf0330a12e895906b` |

Detailed local evidence: `build/generator-reference-measurements.json`,
`build/generator-reference-sections.png`, and `build/measure_generator.py`.
These derived reports and scripts are local ignored artifacts, not source meshes.
