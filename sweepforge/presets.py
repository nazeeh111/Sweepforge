"""Original synthetic requests. No measured hardware evidence."""
import math

def point(z, theta):
    r,p,q,u,v,phase,yaw,ox,oy=z
    b=(r*math.cos(theta+phase),r*math.sin(theta+phase))
    dx,dy=80-b[0],-b[1]
    d=math.hypot(dx,dy)
    along=(p*p-q*q+d*d)/(2*d)
    h=math.sqrt(p*p-along*along)
    cx,cy=b[0]+along*dx/d-h*dy/d,b[1]+along*dy/d+h*dx/d
    ax,ay=(cx-b[0])/p,(cy-b[1])/p
    x,y=b[0]+u*ax-v*ay,b[1]+u*ay+v*ax
    return [x*math.cos(yaw)-y*math.sin(yaw)+ox,x*math.sin(yaw)+y*math.cos(yaw)+oy]

def request(z):
    return {'schema':'sweepforge/1','target':[point(z, i*2*math.pi/48) for i in range(48)],'groundMm':80,'pathToleranceMm':2,'obstacles':[{'x':-90,'y':120,'radius':14}],'clearanceMm':0.5,'linkRadiusMm':2,'toolRadiusMm':1,'dimensionToleranceMm':0.05,'components':'all','budget':8000}

def examples():
    z=[22,72,66,85,30,0.7,-0.3,5,-8]
    base=request(z)
    blind=request(z)
    center=point(z, (53.5)*2*math.pi/64)
    blind.update(obstacles=[{'x':center[0],'y':center[1],'radius':1}],components='tool',toolRadiusMm=0,clearanceMm=0,dimensionToleranceMm=0)
    second=[18,88,75,112,-22,-0.55,0.4,-15,-20]
    return [{'name':'Sculpted loop','description':'Synthetic timed path. Check all six capsule bars and the tool, including ±0.05 mm dimension tolerance.','request':base,'design':{'groundMm':80,'z':z}}, {'name':'Between 64 frames','description':'Diagnostic tool-point model: every one of 64 frames misses a 1 mm obstacle. The continuous check finds the collision. Bars are explicitly excluded.','request':blind,'design':{'groundMm':80,'z':z}}, {'name':'Offset sweep','description':'A second original timed loop with different geometry. Edit its path or solve from positions.','request':request(second),'design':{'groundMm':80,'z':second}}]
