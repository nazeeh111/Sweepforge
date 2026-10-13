# SPDX-License-Identifier: MIT
"""Bounded crank-rocker fitting and outward interval capsule clearance.

Only a fixed 80 mm ground and positive circle-intersection assembly are supported.
Clearance concerns declared planar capsules/disks, not manufactured safety.
"""
import hashlib
import json
import math
import numpy as np
from scipy.optimize import least_squares
from mpmath import iv

iv.dps = 30
FIELDS = {'schema', 'target', 'groundMm', 'pathToleranceMm', 'obstacles',
          'clearanceMm', 'linkRadiusMm', 'toolRadiusMm', 'dimensionToleranceMm',
          'components', 'budget'}
DESIGN_BOUNDS = [(10,45),(40,140),(35,130),(-50,160),(-80,80),
                 (-math.pi,math.pi),(-math.pi,math.pi),(-150,150),(-150,150)]
BARS = [('AD','A','D'),('AB','A','B'),('BC','B','C'),('CD','C','D'),
        ('BP','B','P'),('CP','C','P')]
LIMITS = ['One uniformly timed revolution, one fixed-topology positive assembly branch.',
          'Nominal collisions; clear covers every declared independent dimension/radius interval.',
          'Ground/r/p/q/u/v and nonnegative body radii vary; phase/yaw/translation are exact.',
          'Only fixed circular obstacles versus declared capsules/tool disk; no own-link collisions.',
          'No loads, flex, joint play, manufacturing/process or physical-safety guarantee.',
          'Outward mpmath interval basic operations at 30 decimal digits; interval support is experimental.']


def _number(v, label, low, high, integer=False):
    if type(v) not in (int, float) or not low <= v <= high or not math.isfinite(v):
        raise ValueError(f'{label} requires a finite number in {low}..{high}; bool/text forbidden')
    if integer and type(v) is not int:
        raise ValueError(label+' requires an integer')
    return int(v) if integer else float(v)


def _exact(value, keys, label):
    if type(value) is not dict or set(value) != set(keys):
        raise ValueError(label+' requires exactly the documented fields')


def validate_request(payload):
    """Strict bounded JSON contract. No coercion, optional hidden fields or truth."""
    _exact(payload, FIELDS, 'Request')
    if payload['schema'] != 'sweepforge/1':
        raise ValueError('Unsupported request schema')
    target = payload['target']
    if type(target) is not list or not 8 <= len(target) <= 128:
        raise ValueError('target requires 8..128 ordered [x,y] points')
    points = []
    for row in target:
        if type(row) is not list or len(row) != 2:
            raise ValueError('Each target point requires two numeric coordinates')
        points.append([_number(x, 'target coordinate', -250, 250) for x in row])
    obstacles = payload['obstacles']
    if type(obstacles) is not list or len(obstacles) > 8:
        raise ValueError('At most eight circular obstacles are supported')
    circles = []
    for circle in obstacles:
        _exact(circle, {'x','y','radius'}, 'Obstacle')
        circles.append({'x':_number(circle['x'],'obstacle x',-500,500),
                        'y':_number(circle['y'],'obstacle y',-500,500),
                        'radius':_number(circle['radius'],'obstacle radius',.01,200)})
    if type(payload['components']) is not str or payload['components'] not in ('all','tool'):
        raise ValueError('components must be all or tool')
    return {'schema':'sweepforge/1','target':points,'groundMm':_number(payload['groundMm'],'groundMm',80,80),
            'pathToleranceMm':_number(payload['pathToleranceMm'],'pathToleranceMm',.001,100),
            'obstacles':circles,'clearanceMm':_number(payload['clearanceMm'],'clearanceMm',0,20),
            'linkRadiusMm':_number(payload['linkRadiusMm'],'linkRadiusMm',0,20),
            'toolRadiusMm':_number(payload['toolRadiusMm'],'toolRadiusMm',0,20),
            'dimensionToleranceMm':_number(payload['dimensionToleranceMm'],'dimensionToleranceMm',0,2),
            'components':payload['components'],'budget':_number(payload['budget'],'budget',1,8000,True)}


def _design(value):
    _exact(value, {'groundMm','z'}, 'Design')
    g = _number(value['groundMm'],'design groundMm',80,80)
    z = value['z']
    if type(z) is not list or len(z) != 9:
        raise ValueError('Design z requires exactly nine numeric parameters')
    return {'groundMm':g, 'z':[_number(x,'design z',lo,hi) for x,(lo,hi) in zip(z,DESIGN_BOUNDS)]}


def _rotation_ok(d, tolerance=0):
    r,p,q,*_ = d['z'];g = d['groundMm'];t=tolerance
    return r-t>0 and p-t>0 and q-t>0 and g-t>r+t and p+q-g-r>4*t+1e-9 and g-r-abs(p-q)>4*t+1e-9


def _local(d, a):
    r,p,q,u,v,phase,yaw,ox,oy=d['z'];g=d['groundMm']
    b=np.stack((r*np.cos(a+phase),r*np.sin(a+phase)),axis=-1)
    delta=np.array([g,0])-b;distance=np.linalg.norm(delta,axis=-1)
    along=(p*p-q*q+distance*distance)/(2*distance)
    height2=p*p-along*along
    c=b+along[:,None]*delta/distance[:,None]+np.sqrt(np.maximum(0,height2))[:,None]*np.stack((-delta[:,1],delta[:,0]),axis=-1)/distance[:,None]
    relative=(c-b)/p
    point=b+u*relative+v*np.stack((-relative[:,1],relative[:,0]),axis=-1)
    rotation=np.array([[math.cos(yaw),-math.sin(yaw)],[math.sin(yaw),math.cos(yaw)]])
    positions={'A':np.zeros_like(b),'B':b,'C':c,'D':np.tile([g,0],(len(a),1)),'P':point}
    return {name:xy@rotation.T+np.array([ox,oy]) for name,xy in positions.items()}


def poses(design, angles):
    d=_design(design)
    if not _rotation_ok(d):
        raise ValueError('Design has no strictly nonsingular full-rotation closure')
    if isinstance(angles,np.ndarray):
        if angles.ndim!=1 or not 1<=angles.size<=8192 or angles.dtype.kind not in 'ifu':
            raise ValueError('angles requires 1..8192 numeric values')
        a=angles
    elif isinstance(angles,(list,tuple)) and 1<=len(angles)<=8192:
        for angle in angles:
            if isinstance(angle,(bool,np.bool_)) or not isinstance(angle,(int,float,np.integer,np.floating)) or not -1e6<=angle<=1e6 or not math.isfinite(angle):
                raise ValueError('angles requires bounded numeric values, not bool/text')
        a=np.array(angles,dtype=float)
    else:
        raise ValueError('angles requires 1..8192 finite values')
    if not np.isfinite(a).all() or np.any(a < -1e6) or np.any(a > 1e6):
        raise ValueError('angles requires bounded finite values')
    return _local(d,a.astype(float))


def synthesize(request):
    req=validate_request(request);target=np.array(req['target']);angles=np.arange(len(target))*2*np.pi/len(target)
    lower,upper=np.array(DESIGN_BOUNDS).T
    rng=np.random.default_rng(417);candidates=[];margin=2+4*req['dimensionToleranceMm']
    def residual(z):
        d={'groundMm':80.,'z':z.tolist()};actual=_local(d,angles)['P'];r,p,q,*_=z
        penalties=[max(0,margin-(p+q-80-r))*20,max(0,margin-(80-r-abs(p-q)))*20]
        return np.r_[(actual-target).ravel(),penalties]
    for _ in range(10):
        seed=[rng.uniform(15,35),rng.uniform(65,95),rng.uniform(60,90),rng.uniform(40,100),rng.uniform(-45,45),rng.uniform(-2,2),rng.uniform(-1,1),rng.uniform(-20,20),rng.uniform(-20,20)]
        result=least_squares(residual,seed,bounds=(lower,upper),max_nfev=500,ftol=1e-10,xtol=1e-10,gtol=1e-10)
        d={'groundMm':80.,'z':result.x.tolist()}
        if _rotation_ok(d,req['dimensionToleranceMm']):
            error=float(np.max(np.linalg.norm(_local(d,angles)['P']-target,axis=1)))
            candidates.append((error,d))
    if not candidates:
        raise ValueError('Finite fitting search found no strictly closed design across the dimension box; this is not an impossibility proof')
    return min(candidates,key=lambda pair:pair[0])[1]


def _iv(value):
    return iv.mpf(str(value))


def _parameters(d,t):
    width=_iv(t);params=[_iv(x) for x in d['z']]
    for i in range(5):
        params[i]=iv.mpf([params[i].a-width.b,params[i].b+width.b])
    g=_iv(d['groundMm']);g=iv.mpf([g.a-width.b,g.b+width.b])
    return g,params


def _interval_poses(params,lo,hi):
    g,z=params;r,p,q,u,v,phase,yaw,ox,oy=z
    theta=iv.mpf([lo.a,hi.b])+phase
    bx,by=r*iv.cos(theta),r*iv.sin(theta);dx,dy=g-bx,-by
    length=iv.sqrt(dx**2+dy**2)
    if not length.a>0:return None
    along=(p*p-q*q+length*length)/(2*length);h2=p*p-along*along
    if not h2.a>0:return None
    h=iv.sqrt(h2);cx=bx+along*dx/length-h*dy/length;cy=by+along*dy/length+h*dx/length
    ux,uy=(cx-bx)/p,(cy-by)/p;px,py=bx+u*ux-v*uy,by+u*uy+v*ux
    cyaw,syaw=iv.cos(yaw),iv.sin(yaw)
    return {key:(x*cyaw-y*syaw+ox,x*syaw+y*cyaw+oy) for key,(x,y) in {'A':(_iv(0),_iv(0)),'B':(bx,by),'C':(cx,cy),'D':(g,_iv(0)),'P':(px,py)}.items()}


def _segment_distance2(a,b,center):
    delta=[b[i]-a[i] for i in range(2)];norm=sum(x**2 for x in delta)
    if norm.a>0:
        projection=sum((center[i]-a[i])*delta[i] for i in range(2))/norm
        low=max(_iv(0).a,min(_iv(1).a,projection.a))
        high=max(_iv(0).b,min(_iv(1).b,projection.b))
        t=iv.mpf([low,high]);closest=[a[i]+t*delta[i] for i in range(2)]
    else:
        # The true closest point remains in the complete segment hull, including
        # zero-length rigid tool arms. This is conservative, not sampled.
        closest=[iv.mpf([min(a[i].a,b[i].a),max(a[i].b,b[i].b)]) for i in range(2)]
    return sum((closest[i]-center[i])**2 for i in range(2))


class _BudgetReached(Exception):
    pass


def check(request, design):
    req=validate_request(request);d=_design(design)
    digest=hashlib.sha256(json.dumps({'request':req,'design':d},sort_keys=True,separators=(',',':'),allow_nan=False).encode()).hexdigest()
    tolerance=req['dimensionToleranceMm'];names=['r','p','q','u','v']
    dimensional={name:[value-tolerance,value+tolerance] for name,value in zip(names,d['z'])}
    dimensional['groundMm']=[80-tolerance,80+tolerance]
    radius_bounds={key:[max(0,req[key]-tolerance),req[key]+tolerance] for key in ('linkRadiusMm','toolRadiusMm')}
    report={'state':'unresolved','cells':0,'work':0,'budget':req['budget'],'inputSha256':digest,
            'bounds':{'dimensionIntervalsMm':dimensional,'radiusIntervalsMm':radius_bounds,'angleRad':[0,2*math.pi],'components':req['components'],'clearanceMm':req['clearanceMm']},
            'method':'Outward interval circle closure and clamped closest-point capsule projection; conservative degenerate segment hull. Entire angular cover, independent dimensional intervals; nominal interior collision witnesses only.',
            'limits':LIMITS,'witness':None}
    if not req['obstacles']:
        return {**report,'state':'no_obstacles','reason':'No obstacle was supplied; clearance has not been demonstrated'}
    if not _rotation_ok(d,tolerance):
        return {**report,'reason':'Declared dimension box does not preserve strictly nonsingular full-rotation closure'}
    uncertain=_parameters(d,tolerance);nominal=_parameters(d,0)
    components=[('tool','P','P','toolRadiusMm')]
    if req['components']=='all':components=[(name,a,b,'linkRadiusMm') for name,a,b in BARS]+components
    obstacles=[((_iv(o['x']),_iv(o['y'])),_iv(o['radius'])) for o in req['obstacles']]
    queue=[(_iv(0),2*iv.pi)];unresolved=0;accepted=0
    def spend():
        if report['work']>=req['budget']:raise _BudgetReached
        report['work']+=1
    try:
        while queue:
            spend();lo,hi=queue.pop();report['cells']+=1
            current=_interval_poses(uncertain,lo,hi);all_clear=current is not None;exact=None
            if current is not None:
                for index,(center,obstacle_radius) in enumerate(obstacles):
                    for component,a,b,radius_key in components:
                        spend();distance=_segment_distance2(current[a],current[b],center)
                        radius=obstacle_radius+_iv(req['clearanceMm'])+_iv(req[radius_key])+_iv(tolerance)
                        if distance.a>(radius**2).b:continue
                        all_clear=False
                        if exact is None:
                            spend();exact=_interval_poses(nominal,lo,hi)
                        if exact is not None:
                            spend();nominal_distance=_segment_distance2(exact[a],exact[b],center)
                            nominal_radius2=(obstacle_radius+_iv(req['clearanceMm'])+_iv(req[radius_key]))**2
                            if nominal_distance.b<nominal_radius2.a:
                                upper=math.nextafter(float(nominal_distance.b),math.inf)
                                lower=math.nextafter(float(nominal_radius2.a),-math.inf)
                                angle_lo=math.nextafter(float(lo.b),math.inf);angle_hi=math.nextafter(float(hi.a),-math.inf)
                                if upper<lower and angle_lo<=angle_hi:
                                    witness={'component':component,'obstacle':index,'angleRad':(angle_lo+angle_hi)/2,'angleInterval':[angle_lo,angle_hi],'distanceSquaredUpperMm2':upper,'expandedRadiusSquaredLowerMm2':lower,'nominalOnly':True}
                                    return {**report,'state':'collision','witness':witness,'reason':'A nominal interval is strictly inside the expanded obstacle; not a tolerance-only overlap'}
            if all_clear:
                accepted+=1;continue
            if float((hi-lo).b)<=1e-7:
                unresolved+=1;continue
            mid=(lo+hi)/2;queue.extend([(lo,mid),(mid,hi)])
    except (_BudgetReached,ValueError,ZeroDivisionError,OverflowError) as exc:
        reason='Finite total interval-work budget exhausted' if isinstance(exc,_BudgetReached) else 'Interval enclosure could not be evaluated safely'
        return {**report,'reason':reason,'acceptedCells':accepted,'unresolvedCells':unresolved,'remainingCells':len(queue)}
    return {**report,'state':'unresolved' if unresolved else 'clear_under_model','acceptedCells':accepted,'unresolvedCells':unresolved,'reason':'Tangency, tolerance overlap or unresolved enclosure retained' if unresolved else 'Every declared component/obstacle pair is outside its expanded obstacle for the entire angle and dimension box'}


def _sampled_baseline(req, design):
    result={'frames':64,'minimumGapMm':None,'intersects':None,
            'scope':'Nominal samples only; no clearance proof'}
    if not req['obstacles']:return result
    sampled=poses(design,np.arange(64)*2*np.pi/64)
    components=[('P','P','toolRadiusMm')]
    if req['components']=='all':components=[(a,b,'linkRadiusMm') for _,a,b in BARS]+components
    minimum=math.inf
    for obstacle in req['obstacles']:
        center=np.array([obstacle['x'],obstacle['y']])
        for a,b,key in components:
            start=sampled[a];delta=sampled[b]-start;denominator=np.sum(delta*delta,axis=1)
            projection=np.divide(np.sum((center-start)*delta,axis=1),denominator,
                                 out=np.zeros(len(start)),where=denominator>0)
            closest=start+np.clip(projection,0,1)[:,None]*delta
            gap=np.linalg.norm(closest-center,axis=1)-obstacle['radius']-req['clearanceMm']-req[key]
            minimum=min(minimum,float(gap.min()))
    return {**result,'minimumGapMm':minimum,'intersects':minimum<=0}


def analyze(payload, fit=True):
    if type(fit) is not bool:raise ValueError('fit must be boolean')
    if fit:
        req=validate_request(payload);d=synthesize(req)
    else:
        _exact(payload,{'request','design'},'Check payload');req=validate_request(payload['request']);d=_design(payload['design'])
    n=len(req['target']);actual=poses(d,np.arange(n)*2*np.pi/n)['P'];errors=np.linalg.norm(actual-np.array(req['target']),axis=1)
    metrics={'maxErrorMm':float(errors.max()),'rmsErrorMm':float(np.sqrt(np.mean(errors**2))),'status':'within_tolerance' if errors.max()<=req['pathToleranceMm'] else 'approximate','method':'10 deterministic starts; SciPy max_nfev=500 per start, with additional numerical Jacobian calls. One finite found candidate, no uniqueness or arbitrary-path guarantee.'}
    angles=np.linspace(0,2*np.pi,181);samples=poses(d,angles)
    records=[{'angleRad':float(angle),**{key:xy[i].tolist() for key,xy in samples.items()}} for i,angle in enumerate(angles)]
    return {'request':req,'design':d,'fit':metrics,'path':poses(d,np.arange(512)*2*np.pi/512)['P'].tolist(),'poses':records,'baseline':_sampled_baseline(req,d),'report':check(req,d)}
