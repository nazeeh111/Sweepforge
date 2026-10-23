import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import vm from 'node:vm';

// Execute actual handlers, substituting only DOM and HTTP. The separate native
// browser acceptance pass checks layout and real downloads.
function studio({reducedMotion=false}={}) {
  const nodes=new Map();
  function node(tag='div') {
    return {tag,children:[],value:'0',dataset:{},style:{},disabled:false,hidden:false,textContent:'',
      classList:{toggle(){}},setAttribute(name,value){this[name]=value;},hasAttribute(){return false;},
      addEventListener(){},getContext(){return {};},append(...items){this.children.push(...items);},
      replaceChildren(...items){this.children=items;},querySelectorAll(){return [];},
      click(){},scrollIntoView(){},focus(){}};
  }
  const document={getElementById(id){if(!nodes.has(id))nodes.set(id,node());return nodes.get(id);},
    createElement:node,createTextNode:text=>({textContent:text})};
  const context=vm.createContext({document,structuredClone,Blob,matchMedia:()=>({matches:reducedMotion}),
    setTimeout:()=>0,clearTimeout(){},requestAnimationFrame(){},
    URL:{createObjectURL:()=> 'blob:export',revokeObjectURL(){}},fetch:()=>{throw Error('Unexpected HTTP');}});
  const source=fs.readFileSync(new URL('../sweepforge/assets/app.js',import.meta.url),'utf8')
    .replace(/^import .*\n/,'').replace("if(typeof document!=='undefined')start();",'');
  vm.runInContext(source+'\nthis.studio={state,operation,exportDesign,invalidate,start};',context);
  const api=context.studio;
  api.state.request={target:[[0,0]],obstacles:[],components:'tool',pathToleranceMm:2,
    linkRadiusMm:2,toolRadiusMm:0,clearanceMm:0,dimensionToleranceMm:0};
  api.state.design={groundMm:80,z:[22,72,66,85,30,.7,-.3,5,-8]};
  for(const k of ['pathToleranceMm','linkRadiusMm','toolRadiusMm','clearanceMm','dimensionToleranceMm'])document.getElementById(k).value=String(api.state.request[k]);
  document.getElementById('components').value='tool';
  ['r','p','q','u','v','phase','yaw','ox','oy'].forEach((k,i)=>document.getElementById('dim-'+k).value=String(api.state.design.z[i]));
  const result={request:api.state.request,design:api.state.design,
    report:{state:'collision',inputSha256:'saved-result',cells:6,witness:{angleRad:5}}};
  api.state.result=result;api.state.current=true;
  return {...api,nodes,context,result,$:id=>document.getElementById(id)};
}
function deferred(){let resolve,reject;const promise=new Promise((a,b)=>{resolve=a;reject=b;});return {promise,resolve,reject};}

test('new calculation replaces previous verdict and witness with pending feedback',async()=>{
  const s=studio(),reply=deferred();s.context.fetch=()=>reply.promise;
  s.$('witness').hidden=false;s.$('resultTitle').textContent='A collision is confirmed.';
  s.$('metrics').append({textContent:'old evidence'});
  const running=s.operation('check');
  assert.equal(s.state.current,false);assert.equal(s.$('witness').hidden,true);
  assert.match(s.$('resultTitle').textContent,/Checking the full revolution/);
  assert.equal(s.$('metrics').children.length,0);assert.equal(s.$('export').disabled,true);
  reply.resolve({ok:true,json:async()=>s.result});await running;
  assert.equal(s.state.current,true);assert.equal(s.$('witness').hidden,false);
  assert.match(s.$('resultTitle').textContent,/collision is confirmed/);
});

test('failed export keeps draft and current check, shows retry, releases controls',async()=>{
  const s=studio(),request=structuredClone(s.state.request);
  s.context.fetch=async()=>({ok:false,json:async()=>({error:'Worker deadline exceeded.'})});
  await s.exportDesign();
  assert.match(s.$('identity').textContent,/EXPORT FAILED/);
  assert.match(s.$('notice').textContent,/draft is retained.*Retry Export/);
  assert.equal(s.$('notice').hidden,false);assert.equal(s.$('export').disabled,false);
  assert.equal(s.state.busy,false);assert.equal(s.state.current,true);
  assert.deepEqual(s.state.request,request);
});

test('late calculation failure cannot replace feedback for edited inputs',async()=>{
  const s=studio(),reply=deferred();s.context.fetch=()=>reply.promise;
  const running=s.operation('check');s.invalidate();reply.reject(Error('old request failed'));await running;
  assert.equal(s.$('identity').textContent,'EDITED · RECALCULATE');
  assert.match(s.$('resultLabel').textContent,/INPUT CHANGED/);assert.equal(s.$('export').disabled,true);
});

test('late export failure cannot overwrite feedback for edited inputs',async()=>{
  const s=studio(),reply=deferred();s.context.fetch=()=>reply.promise;
  const running=s.exportDesign();s.invalidate();reply.reject(Error('old export failed'));await running;
  assert.equal(s.$('identity').textContent,'EDITED · RECALCULATE');assert.equal(s.$('notice').hidden,true);
  assert.equal(s.$('export').disabled,true);
});

test('reduced motion starts paused and startup failure gives a recovery action',async()=>{
  const s=studio({reducedMotion:true});assert.equal(s.state.playing,false);
  s.context.fetch=async()=>({ok:false});await s.start();
  assert.equal(s.$('play')['aria-label'],'Play animation');
  assert.equal(s.$('identity').textContent,'WORKSHOP NOT LOADED');
  assert.match(s.$('resultText').textContent,/server running, then reload/);
});
