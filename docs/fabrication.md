# Conceptual flat patterns

Exporting a candidate creates replayable evidence and, when the geometry supports it, SVG and DXF patterns in millimetres. These are nominal outlines of the geometry checked by Sweepforge. They are not a validated cutting plan, bearing specification, material choice, or physical safety assessment.

The six separate pieces are ground AD, crank AB, rocker CD, and the rigid coupler frame's BC, BP, and CP bars. Each piece has the exact nominal capsule silhouette used in the model: straight parallel sides separated by twice `linkRadiusMm`, with semicircular ends of that radius. Do not enlarge an end for a bearing and assume the old clearance report still covers it.

The distance between each piece's two pin-hole centers is its design length. For the coupler, the local assembly coordinates are B = (0, 0), C = (p, 0), and P = (u, v). BC, BP, and CP must be joined as one rigid triangle. They are not three independently rotating links. Retain the sign of v when assembling the triangle; reflecting it changes the tool path. The exported `fabrication.json` records all center coordinates, lengths, radii, and these assembly coordinates.

The illustrative hole radius is the smallest of 1 mm, one third of the body radius, and one sixth of the pin spacing. This ensures the holes fit inside each nominal silhouette and do not overlap one another. It does not select pins, bearings, fastening hardware, joint clearance, or useful stock thickness. Holes remove material from the modeled outer envelope; the calculation does not assess the remaining material's strength.

SVG marks each outline as `data-role="cut-outline"` and each hole as `cut-hole`. Labels and dashed centerlines are reference marks. DXF separates `CUT_OUTLINE_*`, `CUT_HOLES_*`, and `REFERENCE_CENTERLINE_*` layers and declares millimetres through `$INSUNITS = 4`. Exclude reference marks from cutting. The files contain no kerf compensation. Validate dimensions, units, joining, fixtures, process settings, and scale in your own CAD/CAM workflow before making anything.

The bars' capsules form the modeled rigid frame's union. Replacing that frame with a filled triangle or a wider plate changes the occupied geometry and can invalidate obstacle clearance, even with identical pin locations. Ground supports, joint stacks, motors, fasteners, spacers, bearings, and a tool mounting disk are not fabricated by these files. Physical assembly may need layered links, which the two-dimensional model does not check.

A zero body radius, a zero-length member, or a collinear BCP triangle refuses drawing export. The ZIP still contains the recomputed evidence, frozen inputs, source, verifier, and `fabrication.txt` explaining the refusal. A positive drawing status means the specified nominal shapes can be drawn; it does not mean the mechanism has a clear report or is suitable for construction.

The model's dimension tolerance is a calculation input, not a manufacturing specification. Reports describe only the admitted planar bars and tool disk relative to fixed circular obstacles. Own-link contacts, bending, fatigue, friction, play, layer conflicts, loads, strength, and physical safety are outside the check.
