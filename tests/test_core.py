import copy, importlib, math, unittest
from pathlib import Path
import numpy as np
D={'groundMm':80,'z':[22,72,66,85,30,.7,-.3,5,-8]}
def scalar(d,t):
 r,p,q,u,v,phase,yaw,ox,oy=d['z'];g=d['groundMm'];b=[r*math.cos(t+phase),r*math.sin(t+phase)];dx,dy=g-b[0],-b[1];dist=math.hypot(dx,dy)
 a=math.atan2(dy,dx)+math.acos((p*p+dist*dist-q*q)/(2*p*dist));c=[b[0]+p*math.cos(a),b[1]+p*math.sin(a)];point=[b[0]+u*math.cos(a)-v*math.sin(a),b[1]+u*math.sin(a)+v*math.cos(a)]
 def world(x):return [x[0]*math.cos(yaw)-x[1]*math.sin(yaw)+ox,x[0]*math.sin(yaw)+x[1]*math.cos(yaw)+oy]
 return {k:world(x) for k,x in {'A':[0,0],'B':b,'C':c,'D':[g,0],'P':point}.items()}
def req(**edits):
 v={'schema':'sweepforge/1','target':[scalar(D,i*2*math.pi/48)['P'] for i in range(48)],'groundMm':80,'pathToleranceMm':2,'obstacles':[],'clearanceMm':.5,'linkRadiusMm':2,'toolRadiusMm':1,'dimensionToleranceMm':.05,'components':'all','budget':8000};v.update(edits);return v
class CoreControls(unittest.TestCase):
 def setUp(self):
  self.assertTrue((Path(__file__).parents[1]/'sweepforge/core.py').is_file(),'Production core is not implemented');self.c=importlib.import_module('sweepforge.core')
 def test_strict_schema(self):
  self.assertEqual(self.c.validate_request(req())['schema'],'sweepforge/1')
  for e in [{'groundMm':81},{'budget':True},{'budget':8001},{'dimensionToleranceMm':-1},{'components':'body'},{'extra':1},{'clearanceMm':'0.5'},{'pathToleranceMm':float('nan')},{'target':[[0,0]]*7},{'obstacles':[{'x':0,'y':0,'radius':-1}]},{'obstacles':[{'x':0,'y':0,'radius':1}]*9}]:
   with self.subTest(e=e),self.assertRaises(ValueError):self.c.validate_request(req(**e))
  r=req();r['target'][0][0]=True
  with self.assertRaises(ValueError):self.c.validate_request(r)
 def test_geometry(self):
  angles=(np.arange(509)+.37)*2*np.pi/509;actual=self.c.poses(D,angles)
  for i,t in enumerate(angles):
   for k,x in scalar(D,float(t)).items():np.testing.assert_allclose(actual[k][i],x,atol=1e-10,rtol=0)
  for a,b,n in [('A','B',22),('B','C',72),('C','D',66),('A','D',80)]:np.testing.assert_allclose(np.linalg.norm(actual[a]-actual[b],axis=1),n,atol=1e-10,rtol=0)
  with self.assertRaises(ValueError):self.c.poses({'groundMm':80,'z':[22,40,35,85,30,.7,-.3,5,-8]},[0])
 def test_pose_angle_input_rejections(self):
  for angles in [np.array(0),[],[[0,1]],[True],[True,0],[np.bool_(True),0],np.array([-2**63],dtype=np.int64),['1'],[10**1000]]:
   with self.subTest(angles_type=type(angles).__name__),self.assertRaises(ValueError):self.c.poses(D,angles)
 def test_inverse(self):
  design=self.c.synthesize(req());a=(np.arange(509)+.37)*2*np.pi/509;expected=np.array([scalar(D,float(t))['P'] for t in a]);self.assertLess(float(np.max(np.linalg.norm(self.c.poses(design,a)['P']-expected,axis=1))),1e-5)
 def test_empty_identity(self):
  r=self.c.check(req(),D);self.assertEqual(r['state'],'no_obstacles');self.assertEqual(len(r['inputSha256']),64);self.assertNotEqual(r['inputSha256'],self.c.check(req(clearanceMm=.7),D)['inputSha256'])
 def test_tool_missed_frames(self):
  coarse=np.array([scalar(D,i*2*math.pi/64)['P'] for i in range(64)]);half=np.array([scalar(D,(i+.5)*2*math.pi/64)['P'] for i in range(64)]);gaps=np.min(np.linalg.norm(half[:,None,:]-coarse[None,:,:],axis=2),axis=1);point=half[int(np.argmax(gaps))];self.assertGreater(float(np.min(np.linalg.norm(coarse-point,axis=1))),1)
  r=self.c.check(req(components='tool',clearanceMm=0,toolRadiusMm=0,dimensionToleranceMm=0,obstacles=[{'x':float(point[0]),'y':float(point[1]),'radius':1}]),D);self.assertEqual(r['state'],'collision',r);w=r['witness'];self.assertEqual(w['component'],'tool');self.assertLess(math.dist(scalar(D,w['angleRad'])['P'],point),1);self.assertLess(w['distanceSquaredUpperMm2'],w['expandedRadiusSquaredLowerMm2'])
 def test_body(self):
  p=scalar(D,0)
  for a,b,name in [('A','D','AD'),('A','B','AB')]:
   mid=np.mean([p[a],p[b]],axis=0);r=self.c.check(req(obstacles=[{'x':float(mid[0]),'y':float(mid[1]),'radius':.1}]),D);self.assertEqual(r['state'],'collision');self.assertEqual(r['witness']['component'],name)
   witness=scalar(D,r['witness']['angleRad']);start=np.array(witness[a]);delta=np.array(witness[b])-start;t=np.clip(np.dot(mid-start,delta)/np.dot(delta,delta),0,1);self.assertLess(float(np.linalg.norm(start+t*delta-mid)),2.6)
 def test_tolerance_clear(self):
  r=self.c.check(req(obstacles=[{'x':-150,'y':180,'radius':1}],dimensionToleranceMm=.1),D);self.assertEqual(r['state'],'clear_under_model',r);self.assertEqual(r['bounds']['dimensionIntervalsMm']['groundMm'],[79.9,80.1]);self.assertGreater(r['cells'],0)
 def test_refusals(self):
  self.assertEqual(self.c.check(req(obstacles=[{'x':-150,'y':180,'radius':1}],budget=1),D)['state'],'unresolved')
  d=copy.deepcopy(D);d['z'][1]=40;d['z'][2]=63;self.assertEqual(self.c.check(req(obstacles=[{'x':-150,'y':180,'radius':1}],dimensionToleranceMm=1),d)['state'],'unresolved')
  flat={'groundMm':80,'z':[22,72,66,85,30,0,0,0,0]};self.assertEqual(self.c.check(req(clearanceMm=0,linkRadiusMm=0,toolRadiusMm=0,dimensionToleranceMm=0,obstacles=[{'x':40,'y':1,'radius':1}],budget=200),flat)['state'],'unresolved')
 def test_sampled_baseline(self):
  coarse=np.array([scalar(D,i*2*math.pi/64)['P'] for i in range(64)]);point=scalar(D,53.5*2*math.pi/64)['P']
  r=self.c.analyze({'request':req(components='tool',clearanceMm=0,toolRadiusMm=0,dimensionToleranceMm=0,obstacles=[{'x':point[0],'y':point[1],'radius':1}]),'design':D},fit=False)
  self.assertTrue('baseline' in r);self.assertEqual(r['baseline']['frames'],64);self.assertFalse(r['baseline']['intersects']);self.assertAlmostEqual(r['baseline']['minimumGapMm'],float(np.min(np.linalg.norm(coarse-point,axis=1)))-1,places=10);self.assertEqual(r['report']['state'],'collision')
  empty=self.c.analyze({'request':req(),'design':D},fit=False);self.assertIsNone(empty['baseline']['minimumGapMm']);self.assertIsNone(empty['baseline']['intersects'])
 def test_tolerance_enclosure_and_capsule_projection(self):
  from mpmath import iv
  rng=np.random.default_rng(51);base=self.c._design(D);parameters=self.c._parameters(base,.2)
  for _ in range(12):
   low=float(rng.uniform(0,6.25));high=low+.02;box=self.c._interval_poses(parameters,iv.mpf(str(low)),iv.mpf(str(high)));self.assertIsNotNone(box)
   center=[iv.mpf('125'),iv.mpf('-65')]
   for __ in range(8):
    d=copy.deepcopy(D);d['groundMm']+=float(rng.uniform(-.2,.2));d['z'][:5]=[x+float(rng.uniform(-.2,.2)) for x in d['z'][:5]];pose=scalar(d,float(rng.uniform(low,high)))
    for name,point in pose.items():
     for i,v in enumerate(point):self.assertLessEqual(float(box[name][i].a),v);self.assertGreaterEqual(float(box[name][i].b),v)
    for _,a,b in self.c.BARS:
     distance=self.c._segment_distance2(box[a],box[b],center);av=np.array(pose[a]);bv=np.array(pose[b]);delta=bv-av;t=np.clip(np.dot(np.array([125,-65])-av,delta)/np.dot(delta,delta),0,1);actual=float(np.sum((av+t*delta-np.array([125,-65]))**2));self.assertLessEqual(float(distance.a),actual);self.assertGreaterEqual(float(distance.b),actual)
 def test_degenerate_tool_arm_and_tolerance_only_overlap(self):
  flat={'groundMm':80,'z':[22,72,66,0,0,0,0,0,0]};r=self.c.check(req(obstacles=[{'x':-150,'y':180,'radius':1}],dimensionToleranceMm=0),flat);self.assertEqual(r['state'],'clear_under_model',r)
  flat['z'][3]=85;flat['z'][4]=30
  r=self.c.check(req(clearanceMm=0,linkRadiusMm=0,toolRadiusMm=0,dimensionToleranceMm=.2,obstacles=[{'x':40,'y':-.2,'radius':.1}],budget=300),flat);self.assertEqual(r['state'],'unresolved',r);self.assertIsNone(r['witness'])
 def test_analyze(self):
  r=self.c.analyze({'request':req(),'design':D},fit=False);self.assertEqual(len(r['path']),512);self.assertEqual(len(r['poses']),181);self.assertEqual(set(r['poses'][0]),{'angleRad','A','B','C','D','P'});self.assertIn(r['fit']['status'],('within_tolerance','approximate'))
  with self.assertRaises(ValueError):self.c.analyze({'request':req(),'design':D,'result':'fake'},fit=False)
if __name__=='__main__':unittest.main()
