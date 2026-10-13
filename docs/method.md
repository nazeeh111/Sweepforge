# Calculation and replay

Sweepforge fits one planar crank-rocker mechanism to ordered target positions over one uniformly timed crank revolution. It returns one bounded-search candidate. It does not synthesize arbitrary mechanism topologies, establish uniqueness, or prove that a target is impossible when fitting fails.

All lengths and coordinates are in millimetres; phase, yaw, and crank angles are in radians. The nominal ground length is fixed at 80 mm in this implementation. A design stores `groundMm` and `z = [r, p, q, u, v, phase, yaw, ox, oy]`. Here r is crank AB, p is coupler BC, and q is rocker CD. A = (0, 0), D = (groundMm, 0), and B = (r cos(theta + phase), r sin(theta + phase)). C is the positive intersection of the circle centered at B with radius p and the circle centered at D with radius q. The tool point is P = B + u e + v n, where e is the unit vector from B to C and n is its perpendicular pointing to the positive side. Rotate every point by yaw, then translate by (ox, oy).

This fixes one assembly branch. A branch touching a singular configuration is not an admissible full-cycle mechanism. The declared dimension tolerance independently widens the ground length, r, p, q, u, v, link body radius, and tool disk radius; radii are clipped at zero. Phase, yaw, and translation are exact coordinate conventions rather than alignment uncertainty. Obstacles remain the fixed circular objects supplied by the user.

The full-body model checks capsule-shaped AB, BC, CD, BP, CP, and AD, plus the circular tool. A capsule is the shape swept by a disk along a line segment. Its radius is `linkRadiusMm`; the tool uses `toolRadiusMm`. Required clearance expands each obstacle radius. Selecting `components="tool"` checks only the tool disk and explicitly excludes the bars. This is useful for a sampling counterexample, but it is not a full-body verdict.

Playback samples and numerical fit errors describe nominal motion. They do not establish continuous clearance between sampled frames. The clearance report distinguishes `clear_under_model`, a nominal `collision` witness, and `unresolved` when the declared enclosure cannot prove clearance within its calculation budget. An empty obstacle set is `no_obstacles`, not demonstrated obstacle avoidance. A witness identifies its component, obstacle, and crank angle so it can be inspected in the studio.

## Interval clearance

The production checker uses mpmath interval arithmetic at 30 decimal digits. An interval encloses every admitted value instead of treating its midpoint as representative. Basic interval operations round outward. The report retains that mpmath interval support is experimental; a finite set of tests does not establish universal correctness of the arithmetic library.

Before proving nonempty-obstacle clearance, the checker requires strict full-rotation closure throughout the independent dimension box. With the ground longer than the crank, the admitted circle intersections must satisfy p + q > ground + r and ground - r > |p - q| with margins covering dimensional tolerance. It then starts with an angular cover of the complete revolution and keeps the whole dimensional box intact while subdividing angular cells.

For a cell, it encloses A, B, C, D, and P using circle-intersection operations. For each capsule and obstacle, it encloses the closest point on the segment by projecting the obstacle center onto the segment and clamping that parameter to [0, 1]. If the segment's squared length cannot be proved positive, it conservatively uses the segment's full coordinate hull instead. A cell is accepted only when the lower bound on squared separation strictly exceeds the upper bound on squared expanded radius for every admitted component and obstacle. Otherwise it subdivides the angle, or retains uncertainty.

A `collision` result requires a nominal angular interval whose upper separation bound is strictly below the obstacle's lower expanded-radius bound. It is a nominal overlap witness, not evidence that every tolerance combination collides. Mere tolerance overlap, touching, a failed enclosure, or reaching the declared total interval-work budget cannot produce a clear result. Cells reaching a small angular width without separation remain unresolved. The report records its consumed work and declared budget.

The fitting search uses ten deterministic starts and `max_nfev=500` per start, with additional numerical-Jacobian calls performed by SciPy. Its reported maximum and root-mean-square errors compare the candidate tool point with the requested ordered phase samples. Matching those samples within the declared path tolerance does not establish a continuous bound between target samples or a best possible mechanism.

Recheck after changing any request input or design dimension. The report binds a canonical input identity for exactly the normalized request and design. An earlier report does not transfer to an edited mechanism, a different tolerance, altered obstacles, or excluded components.

## Portable evidence

The ZIP exporter calls the production calculation again using the submitted request and design. It discards client-supplied reports, paths, and poses. It freezes normalized inputs and recomputed evidence, includes the actual package source and assets with the MIT license, and records a SHA-256 digest for each included file. SHA-256 is a file digest for detecting changes against a retained manifest; the included manifest is not a signature or proof of authenticity.

Install the exact versions in `requirements.lock`, then run `python verifier.py` with Python 3.12 or later. The verifier reads its own bundle directory regardless of the working directory, checks file digests and dependency versions, imports the included calculation source, and recomputes the report from `request.json` and `design.json`. It fails if the report differs. Dependency installation needs a package source or a local wheel cache; recalculation itself uses no network.

`offline.html` is self-contained original JavaScript. It independently evaluates the frozen nominal dimensions with the circle-intersection construction above, with a phase slider and playback. The displayed report is explicitly the exported evidence. Opening or playing the HTML does not recompute the interval clearance calculation. Run the Python verifier to do that.

No report certifies material suitability, loads, fabrication, stiffness, own-link contact, friction, joint layering, compliance, assembly play, or physical safety. Review the declared input scope and report limits before applying a result. Conceptual drawings and their separate restrictions are documented in [fabrication.md](fabrication.md).
