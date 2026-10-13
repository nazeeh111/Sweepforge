import test from 'node:test';
import assert from 'node:assert/strict';
import {pose,resample} from '../sweepforge/assets/geometry.js';
const z=[22,72,66,85,30,.7,-.3,5,-8];
test('display geometry closes independent rigid circles over 509 phases',()=>{
  const distance=(a,b)=>Math.hypot(a[0]-b[0],a[1]-b[1]);
  for(let i=0;i<509;i++){
    const p=pose(z,(i+.37)*2*Math.PI/509);
    assert.ok(p);
    for(const [a,b,length]of [['A','B',22],['B','C',72],['C','D',66],['A','D',80],['B','P',Math.hypot(85,30)],['C','P',Math.hypot(85-72,30)]])assert.ok(Math.abs(distance(p[a],p[b])-length)<1e-10);
  }
});
test('drawing resampling closes the loop and refuses degenerate strokes',()=>{
  assert.deepEqual(resample([[0,0],[20,0],[20,20],[0,20]],8),[[0,0],[10,0],[20,0],[20,10],[20,20],[10,20],[0,20],[0,10]]);
  assert.throws(()=>resample([[0,0],[0,0],[0,0]]));
  assert.throws(()=>resample([[0,0],[1,0]]));
});
test('invalid circle geometry is visibly unavailable, not clamped into a fake pose',()=>{
  assert.equal(pose([45,40,35,85,30,0,0,0,0],Math.PI),null);
});
