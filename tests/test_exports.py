from __future__ import annotations

import hashlib
import io
import json
import math
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
import xml.etree.ElementTree as ET
import zipfile

from sweepforge import exports


def fixture():
    # Independently compute circle intersection controls for a strict crank-rocker.
    z = [22, 72, 66, 85, 30, .7, -.3, 5, -8]
    r, p, q, u, v, phase, yaw, ox, oy = z
    target = []
    for i in range(16):
        theta = i * 2 * math.pi / 16 + phase
        bx, by = r * math.cos(theta), r * math.sin(theta)
        dx, dy = 80 - bx, -by
        d = math.hypot(dx, dy)
        along = (p*p - q*q + d*d) / (2*d)
        height = math.sqrt(p*p - along*along)
        cx, cy = bx + (along*dx-height*dy)/d, by + (along*dy+height*dx)/d
        px, py = bx + u*(cx-bx)/p - v*(cy-by)/p, by + u*(cy-by)/p + v*(cx-bx)/p
        target.append([ox + math.cos(yaw)*px-math.sin(yaw)*py,
                       oy + math.sin(yaw)*px+math.cos(yaw)*py])
    request = {"schema": "sweepforge/1", "target": target, "groundMm": 80,
               "pathToleranceMm": 2, "obstacles": [], "clearanceMm": .5,
               "linkRadiusMm": 2, "toolRadiusMm": 1, "dimensionToleranceMm": .05,
               "components": "all", "budget": 8000}
    return {"request": request, "design": {"groundMm": 80, "z": z}}


def unzip(data):
    with zipfile.ZipFile(io.BytesIO(data)) as archive:
        return {name: archive.read(name) for name in archive.namelist()}


class DrawingContract(unittest.TestCase):
    def test_svg_hole_centers_lengths_and_capsule_radii_match_design(self):
        payload = fixture()
        drawn = exports.flat_patterns(**payload)
        svg = ET.fromstring(drawn["svg"])
        self.assertTrue(svg.attrib["width"].endswith("mm"))
        self.assertTrue(svg.attrib["height"].endswith("mm"))
        r, p, q, u, v, *_ = payload["design"]["z"]
        expected = {"AD": 80, "AB": r, "CD": q, "BC": p,
                    "BP": math.hypot(u, v), "CP": math.hypot(u-p, v)}
        groups = svg.findall("{*}g")
        self.assertEqual({g.attrib["id"] for g in groups}, set(expected))
        for group in groups:
            name = group.attrib["id"]
            holes = group.findall("{*}circle")
            self.assertEqual([h.attrib["data-joint"] for h in holes], list(name))
            x1, y1 = float(holes[0].attrib["cx"]), float(holes[0].attrib["cy"])
            x2, y2 = float(holes[1].attrib["cx"]), float(holes[1].attrib["cy"])
            self.assertAlmostEqual(math.hypot(x2-x1, y2-y1), expected[name], places=8)
            self.assertEqual(float(group.attrib["data-body-radius-mm"]), 2)
            outline = group.find("{*}path").attrib["d"]
            self.assertIn("A 2 2", outline)
            self.assertTrue(outline.endswith("Z"))
            self.assertLess(float(holes[0].attrib["r"]), 2)
        assembly = drawn["metadata"]["assembly"]
        self.assertEqual(assembly["B"], [0, 0])
        self.assertEqual(assembly["C"], [p, 0])
        self.assertEqual(assembly["P"], [u, v])

    def test_dxf_mm_units_pin_centers_and_arc_radii_match_svg(self):
        drawn = exports.flat_patterns(**fixture())
        lines = drawn["dxf"].decode().splitlines()
        pairs = list(zip(lines[0::2], lines[1::2]))
        self.assertIn(("9", "$INSUNITS"), pairs)
        idx = pairs.index(("9", "$INSUNITS"))
        self.assertEqual(pairs[idx+1], ("70", "4"))
        entities = []
        current = None
        for code, value in pairs:
            if code == "0":
                if current:
                    entities.append(current)
                current = {"kind": value}
            elif current is not None:
                current[code] = value
        circles = [e for e in entities if e["kind"] == "CIRCLE"]
        arcs = [e for e in entities if e["kind"] == "ARC"]
        self.assertEqual(len(circles), 12)
        self.assertEqual(len(arcs), 12)
        for piece in drawn["metadata"]["pieces"]:
            found = [e for e in circles if e["8"] == "CUT_HOLES_" + piece["name"]]
            self.assertEqual(len(found), 2)
            for circle, center in zip(found, piece["holeCentersMm"]):
                self.assertAlmostEqual(float(circle["10"]), center[0], places=8)
                self.assertAlmostEqual(float(circle["20"]), center[1], places=8)
                self.assertAlmostEqual(float(circle["40"]), piece["holeRadiusMm"], places=8)
        self.assertTrue(all(float(e["40"]) == 2 for e in arcs))
        self.assertEqual(sum(e["kind"] == "LINE" and e.get("8", "").startswith("REFERENCE_") for e in entities), 6)

    def test_degenerate_triangle_and_zero_radius_refuse_only_drawing(self):
        payload = fixture()
        for z, radius in [([22, 72, 66, 0, 0, .7, -.3, 5, -8], 2),
                          ([22, 72, 66, 20, 0, .7, -.3, 5, -8], 2),
                          (payload["design"]["z"], 0)]:
            payload["design"]["z"] = z
            payload["request"]["linkRadiusMm"] = radius
            drawn = exports.flat_patterns(**payload)
            self.assertFalse(drawn["metadata"]["supported"])
            self.assertNotIn("svg", drawn)
            self.assertNotIn("dxf", drawn)


class PortableBundleContract(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.payload = fixture()
        cls.files = unzip(exports.build_bundle(cls.payload))

    def test_bundle_complete_safe_names_checksums_and_exact_dependencies(self):
        files = self.files
        required = {"request.json", "design.json", "evidence.json", "fabrication.json",
                    "offline.html", "verifier.py", "requirements.lock", "SHA256SUMS.json",
                    "source/LICENSE", "source/sweepforge/core.py", "source/sweepforge/exports.py",
                    "flat-patterns.svg", "flat-patterns.dxf"}
        self.assertTrue(required.issubset(files))
        for name in files:
            self.assertFalse(Path(name).is_absolute())
            self.assertNotIn("..", Path(name).parts)
            self.assertNotIn("\\", name)
        self.assertEqual(files["requirements.lock"].decode(), "numpy==2.3.5\nscipy==1.18.1\nmpmath==1.3.0\n")
        manifest = json.loads(files["SHA256SUMS.json"])
        self.assertEqual(set(manifest), set(files) - {"SHA256SUMS.json"})
        for name, checksum in manifest.items():
            self.assertEqual(hashlib.sha256(files[name]).hexdigest(), checksum)
        package = Path(exports.__file__).parent
        for source in package.glob("*.py"):
            self.assertEqual(files["source/sweepforge/"+source.name], source.read_bytes())
        for asset in (package / "assets").glob("*"):
            if asset.is_file():
                self.assertEqual(files["source/sweepforge/assets/"+asset.name], asset.read_bytes())

    def test_forged_client_report_path_and_poses_are_ignored(self):
        payload = fixture()
        payload["request"]["components"] = "tool"
        payload.update(report={"state": "FORGED", "inputSha256": "fake"},
                       path="/etc/passwd", poses=[{"P": [999, 999]}])
        files = unzip(exports.build_bundle(payload))
        evidence = json.loads(files["evidence.json"])
        self.assertEqual(evidence["report"]["state"], "no_obstacles")
        self.assertNotEqual(evidence.get("path"), "/etc/passwd")
        self.assertNotEqual(evidence.get("poses"), payload["poses"])
        self.assertEqual(json.loads(files["design.json"]), payload["design"])
        self.assertNotIn(b"FORGED", files["offline.html"])
        self.assertIn(b"Tool disk only; bars are drawn for context and excluded", files["offline.html"])

    def test_unsupported_drawings_keep_recomputed_evidence_and_replay(self):
        payload = fixture()
        payload["request"]["linkRadiusMm"] = 0
        files = unzip(exports.build_bundle(payload))
        self.assertFalse(json.loads(files["fabrication.json"])["supported"])
        self.assertIn("fabrication.txt", files)
        self.assertIn("evidence.json", files)
        self.assertIn("verifier.py", files)
        self.assertNotIn("flat-patterns.svg", files)

    def _run_verifier(self, files):
        with tempfile.TemporaryDirectory(prefix="sweepforge-export-") as directory:
            base = Path(directory)
            bundle, elsewhere = base / "bundle", base / "elsewhere"
            elsewhere.mkdir()
            for name, data in files.items():
                target = bundle / name
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(data)
            # Retain any installed mpmath staging path but remove original package.
            env = os.environ.copy()
            original = str(Path(exports.__file__).resolve().parent.parent)
            env["PYTHONPATH"] = os.pathsep.join(str(Path(p).resolve()) for p in env.get("PYTHONPATH", "").split(os.pathsep)
                                               if p and str(Path(p).resolve()) != original)
            return subprocess.run([sys.executable, str(bundle / "verifier.py")],
                                  cwd=elsewhere, env=env, capture_output=True,
                                  text=True, timeout=120)

    def test_outside_directory_recomputation_uses_bundled_source(self):
        result = self._run_verifier(self.files)
        self.assertEqual(result.returncode, 0, result.stderr)
        actual = json.loads(result.stdout)
        self.assertEqual(actual["report"], json.loads(self.files["evidence.json"])["report"])
        self.assertIn("Recomputed report matches", result.stderr)

    def test_changed_inputs_fail_integrity_check_before_execution(self):
        files = dict(self.files)
        files["design.json"] = b'{"groundMm":80,"z":[20,72,66,85,30,0.7,-0.3,5,-8]}'
        result = self._run_verifier(files)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("Checksum mismatch: design.json", result.stderr)

    def test_modified_evidence_with_updated_checksum_still_requires_recomputation(self):
        files = dict(self.files)
        evidence = json.loads(files["evidence.json"])
        evidence["report"]["state"] = "FORGED"
        files["evidence.json"] = json.dumps(evidence).encode()
        manifest = json.loads(files["SHA256SUMS.json"])
        manifest["evidence.json"] = hashlib.sha256(files["evidence.json"]).hexdigest()
        files["SHA256SUMS.json"] = json.dumps(manifest).encode()
        result = self._run_verifier(files)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("Recomputed report differs", result.stderr)
        self.assertEqual(json.loads(result.stdout)["report"]["state"], "no_obstacles")

    def test_package_symlink_source_is_refused(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            package = root / "sweepforge"
            package.mkdir()
            (root / "LICENSE").write_text("MIT License\nPermission is hereby granted")
            outside = root / "external.py"
            outside.write_text("# must not be copied")
            (package / "core.py").symlink_to(outside)
            with patch.object(exports, "__file__", str(package / "exports.py")):
                with self.assertRaises(ValueError):
                    exports._package_files()

    def test_offline_playback_is_self_contained_and_derives_frozen_geometry(self):
        page = self.files["offline.html"].decode()
        self.assertNotIn("<script src=", page)
        self.assertNotIn("fetch(", page)
        self.assertNotIn("https://", page)
        self.assertIn("function pose(angle)", page)
        self.assertIn("const a=(p*p-q*q+d*d)/(2*d)", page)
        self.assertIn("Exported report", page)
        self.assertIn("python verifier.py", page)
        self.assertIn("not an authenticity signature", page)


if __name__ == "__main__":
    unittest.main()
