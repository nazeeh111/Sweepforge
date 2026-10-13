"""Portable calculations and conceptual millimetre drawings for Sweepforge."""
from __future__ import annotations

import hashlib
import html
import io
import json
import math
from pathlib import Path
import zipfile

from .core import analyze

LOCKED_REQUIREMENTS = "numpy==2.3.5\nscipy==1.18.1\nmpmath==1.3.0\n"


def _json(value) -> bytes:
    return (json.dumps(value, sort_keys=True, indent=2, allow_nan=False) + "\n").encode()


def flat_patterns(request: dict, design: dict) -> dict:
    """Draw six separate capsule bars, matching the nominal checked body radii.

    BCP must be assembled as a rigid triangle; these are not three free joints.
    Unsupported geometry returns a refusal record without discarding evidence.
    """
    r, p, q, u, v, *_ = design["z"]
    radius = request["linkRadiusMm"]
    lengths = [("AD", design["groundMm"]), ("AB", r), ("CD", q),
               ("BC", p), ("BP", math.hypot(u, v)),
               ("CP", math.hypot(u - p, v))]
    note = ("Conceptual nominal capsule bars in millimetres. Assemble BC/BP/CP "
            "as one rigid BCP triangle, retaining the sign of v. Hole sizes are "
            "illustrative, not a bearing or fastener specification. No kerf "
            "compensation, material, load or physical safety validation.")
    if (not math.isfinite(radius) or radius <= 0 or
            any(not math.isfinite(length) or length <= 1e-9 for _, length in lengths) or
            abs(v) <= 1e-9):
        return {"metadata": {"supported": False, "units": "mm", "reason":
                "Flat patterns require a positive body radius, nonzero bars, and a noncollinear BCP triangle.",
                "limits": note}}
    # Separate pieces have exactly the checked capsule silhouettes. Do not
    # widen an end for a bearing, since that would invalidate body clearance.
    margin = max(5.0, 3 * radius)
    pitch = 2 * radius + margin
    x = margin + radius
    pieces = []
    for i, (name, length) in enumerate(lengths):
        y = margin + radius + i * pitch
        hole_radius = min(1.0, radius / 3, length / 6)
        pieces.append({"name": name, "lengthMm": length,
                       "bodyRadiusMm": radius, "holeRadiusMm": hole_radius,
                       "holeCentersMm": [[x, y], [x + length, y]],
                       "jointLabels": list(name)})
    width = max(length for _, length in lengths) + 2 * (margin + radius)
    height = 2 * (margin + radius) + (len(pieces) - 1) * pitch
    metadata = {"supported": True, "units": "mm", "pieces": pieces,
                "assembly": {"B": [0, 0], "C": [p, 0], "P": [u, v],
                             "rigidPieces": ["BC", "BP", "CP"]}, "limits": note}
    svg = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{width:.12g}mm" height="{height:.12g}mm" viewBox="0 0 {width:.12g} {height:.12g}">',
           '<title>Sweepforge conceptual capsule bars, millimetres</title>',
           f'<desc>{html.escape(note)}</desc>',
           '<metadata>' + html.escape(json.dumps(metadata, sort_keys=True, allow_nan=False)) + '</metadata>']
    dxf = ["0", "SECTION", "2", "HEADER", "9", "$ACADVER", "1", "AC1015",
           "9", "$INSUNITS", "70", "4", "9", "$MEASUREMENT", "70", "1",
           "9", "$HANDSEED", "5", "100",
           "0", "ENDSEC", "0", "SECTION", "2", "TABLES", "0", "TABLE", "2", "LAYER",
           "5", "1", "100", "AcDbSymbolTable", "70", "19"]
    layers = [("0", 7)] + [(prefix + piece["name"], color) for piece in pieces
                           for prefix, color in [("CUT_OUTLINE_", 7), ("CUT_HOLES_", 7),
                                                 ("REFERENCE_CENTERLINE_", 4)]]
    for handle, (layer, color) in enumerate(layers, start=2):
        dxf.extend(["0", "LAYER", "5", f"{handle:X}", "100", "AcDbSymbolTableRecord", "100", "AcDbLayerTableRecord",
                    "2", layer, "70", "0", "62", str(color), "6", "CONTINUOUS"])
    dxf.extend(["0", "ENDTAB", "0", "ENDSEC", "0", "SECTION", "2", "ENTITIES"])
    next_handle = 32

    def entity(kind, layer, pairs):
        nonlocal next_handle
        dxf.extend(["0", kind, "5", f"{next_handle:X}", "100", "AcDbEntity", "8", layer,
                    "100", "AcDbLine" if kind == "LINE" else "AcDbCircle"])
        next_handle += 1
        for code, value in pairs:
            if kind == "ARC" and code == 50:
                dxf.extend(["100", "AcDbArc"])
            dxf.extend([str(code), f"{value:.12g}" if isinstance(value, (int, float)) else str(value)])

    for piece in pieces:
        name, length = piece["name"], piece["lengthMm"]
        (sx, sy), (ex, ey) = piece["holeCentersMm"]
        rad = piece["holeRadiusMm"]
        # Two straight sides and two semicircles are the exact capsule outline.
        path = (f"M {sx:.12g} {sy-radius:.12g} H {ex:.12g} "
                f"A {radius:.12g} {radius:.12g} 0 0 1 {ex:.12g} {sy+radius:.12g} "
                f"H {sx:.12g} A {radius:.12g} {radius:.12g} 0 0 1 {sx:.12g} {sy-radius:.12g} Z")
        svg.append(f'<g id="{name}" data-length-mm="{length:.12g}" data-body-radius-mm="{radius:.12g}">')
        svg.append(f'<path data-role="cut-outline" d="{path}" fill="none" stroke="black" stroke-width="0.1"/>')
        for label, (hx, hy) in zip(piece["jointLabels"], piece["holeCentersMm"]):
            svg.append(f'<circle data-role="cut-hole" data-joint="{label}" cx="{hx:.12g}" cy="{hy:.12g}" r="{rad:.12g}" fill="none" stroke="black" stroke-width="0.1"/>')
            # Labels and centerlines are reference only, on distinct roles/layers.
            svg.append(f'<text data-role="reference" x="{hx:.12g}" y="{hy+radius+2:.12g}" font-size="2">{label}</text>')
            entity("CIRCLE", f"CUT_HOLES_{name}", [(10, hx), (20, hy), (30, 0), (40, rad)])
        svg.append(f'<line data-role="reference-centerline" x1="{sx:.12g}" y1="{sy:.12g}" x2="{ex:.12g}" y2="{ey:.12g}" stroke="#467b91" stroke-width="0.1" stroke-dasharray="1 1"/>')
        svg.append('</g>')
        entity("LINE", f"CUT_OUTLINE_{name}", [(10, sx), (20, sy-radius), (30, 0), (11, ex), (21, sy-radius), (31, 0)])
        entity("ARC", f"CUT_OUTLINE_{name}", [(10, ex), (20, sy), (30, 0), (40, radius), (50, 270), (51, 90)])
        entity("LINE", f"CUT_OUTLINE_{name}", [(10, ex), (20, sy+radius), (30, 0), (11, sx), (21, sy+radius), (31, 0)])
        entity("ARC", f"CUT_OUTLINE_{name}", [(10, sx), (20, sy), (30, 0), (40, radius), (50, 90), (51, 270)])
        entity("LINE", f"REFERENCE_CENTERLINE_{name}", [(10, sx), (20, sy), (30, 0), (11, ex), (21, ey), (31, 0)])
    svg.append('</svg>')
    dxf.extend(["0", "ENDSEC", "0", "EOF"])
    return {"metadata": metadata, "svg": ("\n".join(svg) + "\n").encode(),
            "dxf": ("\n".join(dxf) + "\n").encode()}


_PLAYBACK_JS = r"""
const frozen=JSON.parse(document.getElementById('frozen').textContent);
const req=frozen.request, design=frozen.design;
const [r,p,q,u,v,phase,yaw,ox,oy]=design.z, g=design.groundMm;
const cv=document.getElementById('scene'), cx=cv.getContext('2d');
function pose(angle){
 const theta=angle+phase, A=[0,0], D=[g,0], B=[r*Math.cos(theta),r*Math.sin(theta)];
 const dx=D[0]-B[0],dy=D[1]-B[1],d=Math.hypot(dx,dy);
 if(!(d>0))throw Error('Degenerate pose');
 const a=(p*p-q*q+d*d)/(2*d),h2=p*p-a*a;
 if(!(h2>0))throw Error('Assembly branch is not strictly closed');
 const h=Math.sqrt(h2),ex=dx/d,ey=dy/d,C=[B[0]+a*ex-h*ey,B[1]+a*ey+h*ex];
 const tx=(C[0]-B[0])/p,ty=(C[1]-B[1])/p,P=[B[0]+u*tx-v*ty,B[1]+u*ty+v*tx];
 const cs=Math.cos(yaw),sn=Math.sin(yaw);
 return Object.fromEntries(Object.entries({A,B,C,D,P}).map(([k,[x,y]])=>[k,[ox+cs*x-sn*y,oy+sn*x+cs*y]]));
}
const controls=['AB','BC','CD','BP','CP','AD'];
let cloud=[...req.target], path=[];
try{for(let i=0;i<=720;i++){let f=pose(i*Math.PI/360);path.push(f.P);cloud.push(...Object.values(f));}}
catch(err){document.getElementById('playback-message').textContent='Playback unavailable: '+err.message;}
for(const o of req.obstacles){cloud.push([o.x-o.radius,o.y-o.radius],[o.x+o.radius,o.y+o.radius]);}
const margin=5+Math.max(req.linkRadiusMm,req.toolRadiusMm);
const xs=cloud.map(x=>x[0]),ys=cloud.map(x=>x[1]);
const minx=Math.min(...xs)-margin,maxx=Math.max(...xs)+margin,miny=Math.min(...ys)-margin,maxy=Math.max(...ys)+margin;
const scale=Math.min((cv.width-40)/(maxx-minx),(cv.height-40)/(maxy-miny));
function drawLine(points,color,width=1){cx.strokeStyle=color;cx.lineWidth=width;cx.beginPath();points.forEach(([x,y],i)=>i?cx.lineTo(x,y):cx.moveTo(x,y));cx.stroke();}
function draw(){
 cx.setTransform(1,0,0,1,0,0);cx.clearRect(0,0,cv.width,cv.height);
 cx.setTransform(scale,0,0,-scale,20-minx*scale,cv.height-20+miny*scale);
 drawLine(req.target.concat([req.target[0]]),'#557e91',1/scale);drawLine(path,'#e6b365',1/scale);
 for(const o of req.obstacles){cx.fillStyle='#da6f7777';cx.beginPath();cx.arc(o.x,o.y,o.radius,0,Math.PI*2);cx.fill();}
 const angle=Number(document.getElementById('phase').value)*Math.PI/180;
 try{const f=pose(angle);
  for(const name of controls){cx.lineCap='round';drawLine([f[name[0]],f[name[1]]],name==='AD'?'#6c7682':'#eae1cb',2*req.linkRadiusMm);}
  for(const key of ['A','B','C','D']){cx.fillStyle='#111b27';cx.beginPath();cx.arc(...f[key],1.5/scale,0,Math.PI*2);cx.fill();}
  cx.fillStyle='#7febc5';cx.beginPath();cx.arc(...f.P,req.toolRadiusMm,0,Math.PI*2);cx.fill();
 }catch(err){document.getElementById('playback-message').textContent='Playback unavailable: '+err.message;}
 document.getElementById('phase-value').textContent=(angle*180/Math.PI).toFixed(1)+' degrees';
}
let playing=false,last=0;
document.getElementById('play').onclick=()=>{playing=!playing;document.getElementById('play').textContent=playing?'Pause':'Play';last=0;};
document.getElementById('phase').oninput=draw;
function animate(now){if(playing){if(last){const slider=document.getElementById('phase');slider.value=(Number(slider.value)+(now-last)*0.03)%360;draw();}last=now;}requestAnimationFrame(animate);}
draw();requestAnimationFrame(animate);
"""


def offline_html(result: dict) -> bytes:
    """Standalone playback independently derives poses from frozen dimensions.

    Playback is nominal illustration. Only Python replay recomputes bounds.
    """
    frozen = json.dumps({"request": result["request"], "design": result["design"]},
                        sort_keys=True, allow_nan=False).replace("<", "\\u003c").replace(">", "\\u003e").replace("&", "\\u0026")
    report = html.escape(json.dumps(result["report"], sort_keys=True, indent=2, allow_nan=False))
    checked = ("All six capsule bars and the tool disk" if result["request"]["components"] == "all"
               else "Tool disk only; bars are drawn for context and excluded from the check")
    return f'''<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Sweepforge frozen mechanism playback</title>
<style>body{{background:#111b27;color:#eae1cb;font:16px system-ui;max-width:1100px;margin:30px auto;padding:0 20px}}canvas{{width:100%;background:#182637;border-radius:12px}}button{{padding:8px 22px}}input{{width:65%}}pre{{white-space:pre-wrap;overflow-wrap:anywhere;background:#182637;padding:20px}}.note{{color:#afd4de}}</style>
<h1>Sweepforge frozen mechanism</h1><p class="note">Offline nominal playback. Exported evidence below is a saved result, not a new clearance check. Recompute with the included verifier.py.</p><p>Checked scope: {checked}.</p>
<canvas id="scene" width="1100" height="580" aria-label="Frozen planar mechanism"></canvas>
<p><button id="play">Play</button> <input id="phase" type="range" min="0" max="360" step="0.1" value="0" aria-label="Crank phase"> <span id="phase-value"></span></p><p id="playback-message">One uniformly timed revolution; target points are ordered phase samples. Gold: nominal tool path. Blue: requested path. Pink: fixed obstacles.</p>
<h2>Exported report</h2><pre>{report}</pre><h2>Recompute</h2><pre>python -m pip install -r requirements.lock
python verifier.py</pre><p>Python 3.12 or later. Dependency installation requires access to a package source or a local wheel cache. Recalculation and playback use no network. SHA256SUMS.json detects changes against its included manifest; it is not an authenticity signature.</p>
<p>Only the declared planar capsule/disk geometry and tolerance model are covered. Loads, materials, joint layering, own-link contact, compliance, fabrication, and physical safety are not checked. See fabrication.json before using any drawing.</p>
<script id="frozen" type="application/json">{frozen}</script><script>{_PLAYBACK_JS}</script></html>'''.encode()


_VERIFIER = r'''#!/usr/bin/env python3
"""Recompute Sweepforge evidence using the included source; no network calls."""
from pathlib import Path
import hashlib
import importlib.metadata
import json
import sys

def main():
    if sys.version_info < (3, 12):
        raise SystemExit("Python 3.12 or later is required")
    base = Path(__file__).resolve().parent
    manifest = json.loads((base / "SHA256SUMS.json").read_text())
    for name, expected in manifest.items():
        relative = Path(name)
        if relative.is_absolute() or ".." in relative.parts or "\\" in name:
            raise SystemExit("Unsafe manifest path")
        target = base / relative
        if target.is_symlink() or not target.resolve().is_relative_to(base):
            raise SystemExit("Manifest path escapes bundle")
        if hashlib.sha256(target.read_bytes()).hexdigest() != expected:
            raise SystemExit("Checksum mismatch: " + name)
    for name, version in {"numpy": "2.3.5", "scipy": "1.18.1", "mpmath": "1.3.0"}.items():
        try:
            found = importlib.metadata.version(name)
        except importlib.metadata.PackageNotFoundError:
            raise SystemExit("Missing dependency: " + name + "; install requirements.lock")
        if found != version:
            raise SystemExit("Dependency version mismatch: " + name + "=" + found + "; expected " + version)
    sys.path.insert(0, str(base / "source"))
    from sweepforge.core import analyze
    request = json.loads((base / "request.json").read_text())
    design = json.loads((base / "design.json").read_text())
    claimed = json.loads((base / "evidence.json").read_text())
    actual = analyze({"request": request, "design": design}, fit=False)
    print(json.dumps(actual, sort_keys=True, indent=2, allow_nan=False))
    if actual["report"] != claimed["report"]:
        raise SystemExit("Recomputed report differs from exported evidence")
    print("Recomputed report matches. Checksums do not establish authenticity.", file=sys.stderr)

if __name__ == "__main__":
    main()
'''


def _package_files() -> dict[str, bytes]:
    package = Path(__file__).resolve().parent
    license_path = package.parent / "LICENSE"
    if not license_path.is_file():
        license_path = package / "assets" / "LICENSE.txt"
    license_bytes = license_path.read_bytes()
    if b"Permission is hereby granted" not in license_bytes:
        raise ValueError("Portable bundle requires the package's MIT license")
    files = {"source/LICENSE": license_bytes}
    candidates = list(package.rglob("*.py"))
    assets = package / "assets"
    if assets.exists():
        candidates.extend(path for path in assets.rglob("*") if not path.is_dir())
    for path in sorted(set(candidates)):
        relative = path.relative_to(package)
        if any(part.startswith(".") or part == "__pycache__" for part in relative.parts):
            continue
        if path.is_symlink() or not path.resolve().is_relative_to(package):
            raise ValueError("Portable bundle does not include symlinks or external sources")
        files["source/sweepforge/" + relative.as_posix()] = path.read_bytes()
    if "source/sweepforge/core.py" not in files:
        raise ValueError("Portable bundle requires its actual calculation source")
    return files


def build_bundle(payload: dict) -> bytes:
    """Freeze inputs and freshly recomputed evidence into a portable ZIP.

    Client reports, paths and poses are intentionally excluded from the input.
    """
    if not isinstance(payload, dict) or "request" not in payload or "design" not in payload:
        raise ValueError("Export requires request and design")
    result = analyze({"request": payload["request"], "design": payload["design"]}, fit=False)
    # Deep-freeze plain JSON before deriving any exported views.
    result = json.loads(_json(result))
    drawings = flat_patterns(result["request"], result["design"])
    files = _package_files()
    files.update({"request.json": _json(result["request"]), "design.json": _json(result["design"]),
                  "evidence.json": _json(result), "fabrication.json": _json(drawings["metadata"]),
                  "offline.html": offline_html(result), "verifier.py": _VERIFIER.encode(),
                  "requirements.lock": LOCKED_REQUIREMENTS.encode(),
                  "README.txt": ("Sweepforge frozen calculation bundle\n\n"
                      "Python 3.12+. Install exact requirements.lock, then run python verifier.py.\n"
                      "The verifier imports included source/sweepforge, not your original workspace.\n"
                      "Offline.html independently calculates nominal playback from frozen dimensions.\n"
                      "Evidence is recomputed when exporting. Review fabrication.json for drawing status.\n"
                      "Patterns are conceptual mm outlines, not validated hardware or a cutting prescription.\n"
                      "SHA256SUMS.json is an integrity manifest, not proof of authenticity.\n"
                      "Source code is original MIT-licensed software; see source/LICENSE.\n").encode()})
    if drawings["metadata"]["supported"]:
        files["flat-patterns.svg"] = drawings["svg"]
        files["flat-patterns.dxf"] = drawings["dxf"]
    else:
        files["fabrication.txt"] = ("Drawing refused: " + drawings["metadata"]["reason"] +
                                    "\n" + drawings["metadata"]["limits"] + "\n").encode()
    files["SHA256SUMS.json"] = _json({name: hashlib.sha256(data).hexdigest() for name, data in sorted(files.items())})
    output = io.BytesIO()
    with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for name, data in sorted(files.items()):
            item = zipfile.ZipInfo(name, date_time=(1980, 1, 1, 0, 0, 0))
            item.external_attr = 0o100644 << 16
            item.compress_type = zipfile.ZIP_DEFLATED
            archive.writestr(item, data)
    return output.getvalue()
