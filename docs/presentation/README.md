# A fitted path, a missed frame, a retained witness

This is a real local workflow executed from current main `4925ccafeddf92682fe40f87dbae1aa4f40c5ecf`. The input is a bundled synthetic timed path, not a measured machine. The one-motor topology, fixed 80 mm ground span and positive circle-intersection branch stay unchanged.

## Make the edit and fit it

Install the exact declared dependencies in an isolated environment, then launch:

```sh
python -m pip install -r requirements.lock .
sweepforge studio --port 6381
```

1. Select **Between 64 frames**. This preset explicitly checks the tool only; bars are excluded.
2. Open **Bring your own timed path**. Paste [ui-request.json](ui-request.json), then **Use pasted input**. It changes only target point 0's y coordinate by +0.2 mm relative to [source-request.json](source-request.json). Ordered points are equal motor-phase steps, not an arbitrary clock time.
3. Choose **Fit mechanism**. The actual candidate's maximum target-sample error is **0.1777396264259595 mm**, within the declared 2 mm tolerance. This finite fit is not an optimum or uniqueness proof.
4. **Jump to collision witness**, then **Save request JSON** and **Export design & replay**. The actual [edited native export](ui-design.zip) contains the frozen request, dimensions, recomputed evidence, conceptual patterns and complete calculation source.

A malformed pasted input retains the current result and export. Dimension edits invalidate it; restoring the input still requires a fresh check. The phase slider works by keyboard. Actual desktop and 390-pixel workbench routes were exercised with reduced motion. [Browser record](browser.json) · [actual fitted response](ui-fitted.json).

## Inspect the distinction

All **64 nominal samples** miss the 1 mm obstacle. Their minimum gap is **+0.751081933720299 mm**. That is a sampled observation, not a clearance certificate.

The interval checker reports **collision**, with a nominal tool witness near **302.4802878499031°**. Its stored upper bound on squared distance is strictly below the stored lower bound on expanded radius squared. [Full geometry and bounds](geometry.json) retain every exact report field and original source limits.

The explanatory detail includes the two neighboring frames, zero-based indices 53 and 54 at 298.125° and 303.75°. Its separate diamond probe is halfway between them at 300.9375°; independent scalar circle closure places that nominal tool point 0.9958478037487493 mm inside the disk. The red circle is the actual stored interval witness, not that midpoint probe. No sampled curve or picture substitutes for the interval calculation.

The full mechanism and detail each use equal horizontal/vertical millimetre scales, with separate labeled magnifications. All 48 target points, 64 samples and 512 nominal display positions are retained. The 129-position detail curve is a nominal visual sampling, not an interval enclosure. The six bars are shown as centerlines for context and are not checked by this diagnostic. Zero dimension tolerance and a point tool are deliberate limits, not hardware safety evidence.

## Reopen the actual portable result

Extract [ui-design.zip](ui-design.zip) into a new directory and read its producer README.txt. Its playback filename is lowercase `offline.html`. The native archive has 27 members and includes every source/asset named by its verifier.

```sh
python -m venv /tmp/sweepforge-replay-env
/tmp/sweepforge-replay-env/bin/python -m pip install -r /path/to/extracted/requirements.lock
/tmp/sweepforge-replay-env/bin/python /path/to/extracted/verifier.py
```

Python 3.12+, NumPy 2.3.5, SciPy 1.18.1 and mpmath 1.3.0 are required. Dependency installation can require a free package source; the actual check and playback make no network calls. The unchanged native verifier checks all member hashes and exact dependency versions, then recomputes the stored report using the included source, even from another working directory. Do not alter a saved verdict to make it pass. Hashes identify bytes, not their author.

Open `offline.html` in a fresh browser. Its frozen dimensions equal the actual exported design. Its phase slider and actual 390-pixel mobile context work without page overflow. Playback remains a visualization of stored evidence, not a new interval check. The native archive's README and all calculation files remain unmodified producer bytes. The explanatory figure/generator are separate repository files, not additions to its integrity manifest.

The native DXF reopens in the existing CAD reader with millimetre units and all six reference lengths matching fabrication.json to export precision. Its 42 entities describe nominal capsule pieces, holes and reference centerlines. BC/BP/CP form one rigid triangle, not three free joints. These are conceptual patterns, not validated fabrication instructions. Retain the included MIT notice and exact dependency lock.

## CLI controls and other model states

The [original unedited CLI fit](fitted.json), [check](checked.json), [native export](design.zip) and [exact commands](cli-journey.json) are separate controls. They do not overwrite or relabel the edited workbench artifact. Existing output paths are refused without replacement.

A [one-work-unit control](budget-control.json) returns **unresolved**, not clear. A separate [ordinary full-body control](full-body-control.json) checks all six bar capsules plus the tool with ±0.05 mm dimension tolerance and returns clear_under_model for its own distant obstacle. That result is not transferred to the tool-only collision example.

No measured hardware, loads, flex, bearing play, own-link contact, manufacturing safety, general optimality or arbitrary topology is established. The interval operations use experimental mpmath support under the source's narrower declared method. [Method](../method.md) · [Fabrication limits](../fabrication.md).
