"""Source-bound nominal mechanism and between-frame detail; equal millimetre scales."""
from pathlib import Path
import json,math,html
P=Path(__file__).resolve().parent;g=json.loads((P/'geometry.json').read_text());COL={'paper':'#edf2ee','ink':'#1d3e32','muted':'#53695d','path':'#16727b','accent':'#a64b24','obstacle':'#a33c32','line':'#71857a'};records=[]
def draw(phone):
 W,H=(420,1300)if phone else(1200,880);a=[f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" role="img" aria-labelledby="sweep-title sweep-desc"><title id="sweep-title">Sixty-four frames miss a collision</title><desc id="sweep-desc">Actual edited timed path fitted to one planar crank-rocker. All 64 nominal tool samples miss the one millimetre obstacle by at least 0.751 millimetres, yet the interval checker finds a nominal tool collision between frames 53 and 54. The full mechanism and a separate detail each use equal horizontal and vertical millimetre scales. This diagnostic checks the tool only, with zero dimension tolerance; bars and physical safety are not checked.</desc><rect width="100%" height="100%" fill="{COL["paper"]}"/>']
 def t(x,y,text,size=18,color='ink',bold=False,anchor=None):a.append(f'<text x="{x}" y="{y}" font-family="Arial,Helvetica,sans-serif" font-size="{size}" fill="{COL[color]}"'+(' font-weight="700"'if bold else'')+(f' text-anchor="{anchor}"'if anchor else'')+'>'+html.escape(str(text))+'</text>')
 def line(points,color,width=1.5,dash=None,id=None):a.append('<polyline'+(f' id="{id}"'if id else'')+' points="'+' '.join(f'{x:.8f},{y:.8f}'for x,y in points)+f'" fill="none" stroke="{COL[color]}" stroke-width="{width}"'+(f' stroke-dasharray="{dash}"'if dash else'')+'/>')
 t(24,35,'Sweepforge / timed motion',14,'path')
 if phone:t(24,81,'64 frames miss',31,bold=True);t(24,121,'a collision.',31,bold=True)
 else:t(24,88,'Sixty-four frames miss a collision.',42,bold=True)
 t(24,164 if phone else 132,'A real fitted mechanism, checked between playback samples.',14 if phone else 20,'muted')
 req=g['request'];ob=req['obstacles'][0];shape=g['midPose'];points=g['path512']+g['targets48']+list(shape.values());lo=[min(q[i]for q in points)-10 for i in(0,1)];hi=[max(q[i]for q in points)+10 for i in(0,1)]
 if phone:box=(24,242,372,320);zoom=(60,711,300,300)
 else:box=(24,250,696,420);zoom=(836,295,310,310)
 def mapping(bounds,box):
  lo,hi=bounds;x,y,w,h=box;scale=min(w/(hi[0]-lo[0]),h/(hi[1]-lo[1]));ox=x+(w-(hi[0]-lo[0])*scale)/2;oy=y+(h-(hi[1]-lo[1])*scale)/2
  return lambda p:(ox+(p[0]-lo[0])*scale,oy+(hi[1]-p[1])*scale),scale,[ox,oy]
 xy,scale,origin=mapping((lo,hi),box);t(24,217 if phone else 216,'Fitted linkage, at a between-frame probe',18,bold=True)
 # Native display samples are connected as a nominal playback curve, not an enclosure.
 line(list(map(xy,g['path512']+[g['path512'][0]])),'path',1.5,id='path512')
 for i,p in enumerate(g['targets48']):
  x,y=xy(p);a.append(f'<circle class="target" data-index="{i}" cx="{x:.8f}" cy="{y:.8f}" r="2.3" fill="{COL["paper"]}" stroke="{COL["path"]}"/>')
 for i,p in enumerate(g['samples64']):
  x,y=xy(p);a.append(f'<circle class="sample" data-index="{i}" cx="{x:.8f}" cy="{y:.8f}" r="1.3" fill="{COL["ink"]}"/>')
 for name,ends in [('AD','AD'),('AB','AB'),('BC','BC'),('CD','CD'),('BP','BP'),('CP','CP')]:line([xy(shape[n])for n in ends],'line',2.5,id='bar-'+name)
 for n,p in shape.items():
  x,y=xy(p);a.append(f'<circle class="joint" data-name="{n}" cx="{x:.8f}" cy="{y:.8f}" r="{4 if n=="P"else 3}" fill="{COL["accent"]if n=="P"else COL["ink"]}"/>');t(x+7,y-7,n,13,'accent'if n=='P'else'ink')
 x,y=xy([ob['x'],ob['y']]);a.append(f'<circle class="overview-obstacle" cx="{x:.8f}" cy="{y:.8f}" r="{ob["radius"]*scale:.8f}" fill="none" stroke="{COL["obstacle"]}" stroke-width="2"/>')
 # Uniform physical scale bar for the overview.
 xx,yy=box[0]+16,box[1]+box[3]-12;line([(xx,yy),(xx+20*scale,yy)],'ink',2);t(xx,yy-10,'20 mm',12,'muted');t(24,598 if phone else 700,'48 timed targets; 512-point nominal display curve.',13,'muted')
 # The detail uses a declared larger, equally scaled millimetre view.
 if phone:t(24,659,'Between frames 53 and 54',22,bold=True);t(24,686,'One millimetre obstacle radius',14,'muted')
 else:t(796,216,'Between frames 53 and 54',23,bold=True);t(796,246,'One millimetre obstacle radius',16,'muted')
 zlo=[ob['x']-3,ob['y']-3];zhi=[ob['x']+3,ob['y']+3];xz,zscale,zorigin=mapping((zlo,zhi),zoom);cx,cy=xz([ob['x'],ob['y']]);a.append(f'<circle id="obstacle-detail" cx="{cx:.8f}" cy="{cy:.8f}" r="{zscale:.8f}" fill="#ead8cf" stroke="{COL["obstacle"]}" stroke-width="2"/>');line(list(map(xz,g['zoom129'])),'path',2,id='zoom129')
 for index in(53,54):
  x,y=xz(g['samples64'][index]);a.append(f'<circle class="neighbor" data-index="{index}" cx="{x:.8f}" cy="{y:.8f}" r="5" fill="{COL["paper"]}" stroke="{COL["ink"]}" stroke-width="2"/>');t(x+10,y+5,str(index),16,bold=True)
 for id,p,color in [('probe',shape['P'],'accent'),('native-witness',g['witnessPose']['P'],'obstacle')]:
  x,y=xz(p)
  if id=='probe':a.append(f'<polygon id="probe" data-cx="{x:.8f}" data-cy="{y:.8f}" points="{x:.8f},{y-6:.8f} {x+6:.8f},{y:.8f} {x:.8f},{y+6:.8f} {x-6:.8f},{y:.8f}" fill="{COL[color]}"/>')
  else:a.append(f'<circle id="{id}" cx="{x:.8f}" cy="{y:.8f}" r="5" fill="{COL[color]}"/>')
 xx,yy=zoom[0],zoom[1]+zoom[3]+15;line([(xx,yy),(xx+zscale,yy)],'ink',2);t(xx,yy+22,'1 mm',12,'muted')
 y=1075 if phone else 720;t(24,y,f'64 frames: +{g["baseline"]["minimumGapMm"]:.3f} mm minimum sampled gap',17 if phone else 22,bold=True);t(24,y+36,'Interval result: collision, nominal tool only.',18 if phone else 22,'obstacle',True)
 t(24,y+76,f'Mid-frame probe: {g["midPhaseDegrees"]:.3f} deg; gap {g["midGapMm"]:.3f} mm.',13,'muted');t(24,y+102,'Bars excluded; zero dimensional tolerance in this diagnostic.',12,'muted');t(24,y+128,'Diamond: midpoint; red circle: stored witness.',12,'muted');
 if phone:t(24,y+151,'Geometric model, not physical linkage safety.',12,'muted')
 a.append('</svg>');records.append({'figure':'phone'if phone else'desktop','overview':{'lo':lo,'hi':hi,'scale':scale,'origin':origin,'box':box},'detail':{'lo':zlo,'hi':zhi,'scale':zscale,'origin':zorigin,'box':zoom},'all512Curve48Targets64SamplesAnd6BarsRetained':True});return '\n'.join(a)+'\n'
for n,m in [('between-frames',False),('between-frames-mobile',True)]:
 svg=draw(m);(P/(n+'.svg')).write_text(svg);(P/(n+'.html')).write_text('<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Sweepforge between frames</title><style>body{margin:0}svg{display:block;max-width:100%;height:auto}</style>'+svg)
(P/'figure-data.json').write_text(json.dumps({'views':records,'encoding':'Nominal geometric samples, not interval enclosures. Exact source interval verdict is separate. Two zooms have separately declared equal physical scales.'},indent=2)+'\n')
