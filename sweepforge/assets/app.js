import {pose,resample} from './geometry.js';
const $ = id => document.getElementById(id);
const fields = ['pathToleranceMm','linkRadiusMm','toolRadiusMm','clearanceMm','dimensionToleranceMm'];
const names = ['r','p','q','u','v','phase','yaw','ox','oy'];
const state = {request:null,design:null,result:null,revision:0,current:false,busy:false,mode:'edit',phase:0,playing:true,view:null,drag:null,stroke:[],examples:[]};
const canvas = $('stage'), ctx = canvas.getContext('2d');
let noticeTimer;


function clone(value){return structuredClone(value);}
function notice(message){$('notice').textContent=message;$('notice').hidden=false;clearTimeout(noticeTimer);noticeTimer=setTimeout(()=>$('notice').hidden=true,5000);}
function number(input){
  const raw=input.value.trim(),value=Number(raw);
  const ok=raw!==''&&Number.isFinite(value)&&(!input.hasAttribute('min')||value>=Number(input.min))&&(!input.hasAttribute('max')||value<=Number(input.max));
  input.classList.toggle('invalid',!ok);
  if(!ok)throw new Error('Enter a valid value for '+(input.dataset.name||input.id||'this field')+'.');
  return value;
}
function request(){
  const r=clone(state.request);
  fields.forEach(k=>r[k]=number($(k)));
  r.components=$('components').value;
  r.obstacles=[...$('obstacles').querySelectorAll('.obstaclerow')].map(row=>Object.fromEntries([...row.querySelectorAll('input')].map(i=>[i.dataset.name,number(i)])));
  return r;
}
function design(){return {groundMm:80,z:names.map(k=>number($('dim-'+k)))};}
function invalidate(){
  state.revision++;state.current=false;
  $('export').disabled=true;$('identity').textContent='EDITED · RECALCULATE';
  $('resultLabel').textContent='PREVIOUS RESULT · INPUT CHANGED';
  $('resultTitle').textContent='Recalculate this design.';
  $('resultText').textContent='The previous clearance result no longer describes the current input.';
  $('resultCard').className='resultcard';$('witness').hidden=true;$('metrics').replaceChildren();
}
function setMode(mode){
  state.mode=mode;
  ['edit','draw','obstacle'].forEach(m=>$(m+'Mode').classList.toggle('selected',m===mode));
  $('canvasHelp').textContent={edit:'Drag a cyan point to change the requested motion.',draw:'Draw one closed loop. Release to assign 48 equal phase steps.',obstacle:'Click to place a circular forbidden region.'}[mode];
  canvas.style.cursor=mode==='edit'?'default':'crosshair';
}
function obstacles(){
  $('obstacles').replaceChildren();
  state.request.obstacles.forEach((o,index)=>{
    const row=document.createElement('div');row.className='obstaclerow';
    ['x','y','radius'].forEach(k=>{
      const label=document.createElement('label');label.textContent=k==='radius'?'Radius mm':k.toUpperCase()+' mm';
      const input=document.createElement('input');input.type='number';input.step='0.1';input.dataset.name=k;input.min=k==='radius'?'0.01':'-500';input.max=k==='radius'?'200':'500';input.value=o[k];input.setAttribute('aria-label',`Obstacle ${index+1} ${k}`);
      input.addEventListener('input',()=>{invalidate();try{state.request.obstacles[index][k]=number(input);}catch{}});
      label.append(input);row.append(label);
    });
    const remove=document.createElement('button');remove.textContent='×';remove.title='Remove obstacle '+(index+1);remove.setAttribute('aria-label',remove.title);
    remove.addEventListener('click',()=>{
      // Preserve the current typed values before reindexing; reject invalid drafts.
      try{state.request=request();}catch(e){notice(e.message);return;}
      state.request.obstacles.splice(index,1);obstacles();invalidate();
    });row.append(remove);$('obstacles').append(row);
  });
}
function dimensionInputs(){
  $('dimensions').replaceChildren();
  names.forEach((name,index)=>{
    const label=document.createElement('label');label.textContent=name+(index<5||index>6?' · mm':' · rad');
    const input=document.createElement('input');input.id='dim-'+name;input.dataset.name=name;input.type='number';input.step=index===5||index===6?'0.01':'0.1';input.value=state.design.z[index];
    const bounds=[[10,45],[40,140],[35,130],[-50,160],[-80,80],[-Math.PI,Math.PI],[-Math.PI,Math.PI],[-150,150],[-150,150]][index];input.min=bounds[0];input.max=bounds[1];
    input.addEventListener('input',()=>{invalidate();try{state.design=design();}catch{}});
    label.append(input);$('dimensions').append(label);
  });
}
function controls(){fields.forEach(k=>$(k).value=state.request[k]);$('components').value=state.request.components;obstacles();dimensionInputs();}
function fitView(){
  const points=state.request?.target?.slice()||[];
  if(state.design)for(let i=0;i<181;i++){const p=pose(state.design.z,i*2*Math.PI/181);if(p)points.push(...Object.values(p));}
  for(const o of state.request?.obstacles||[])points.push([o.x-o.radius,o.y-o.radius],[o.x+o.radius,o.y+o.radius]);
  if(!points.length)return;
  const xs=points.map(p=>p[0]),ys=points.map(p=>p[1]);
  const x0=Math.min(...xs),x1=Math.max(...xs),y0=Math.min(...ys),y1=Math.max(...ys);
  state.view={x:(x0+x1)/2,y:(y0+y1)/2,width:Math.max(100,x1-x0+35),height:Math.max(100,y1-y0+35)};
}
function view(){
  if(!state.view)fitView();
  const w=canvas.clientWidth,h=canvas.clientHeight, v=state.view||{x:40,y:40,width:200,height:200};
  const scale=Math.min(w/v.width,h/v.height);
  return {w,h,scale,toScreen:([x,y])=>[w/2+(x-v.x)*scale,h/2-(y-v.y)*scale],toWorld:([x,y])=>[v.x+(x-w/2)/scale,v.y-(y-h/2)/scale]};
}
function draw(){
  const dpr=devicePixelRatio||1,w=canvas.clientWidth,h=canvas.clientHeight;
  if(canvas.width!==Math.round(w*dpr)||canvas.height!==Math.round(h*dpr)){canvas.width=Math.round(w*dpr);canvas.height=Math.round(h*dpr);}
  ctx.setTransform(dpr,0,0,dpr,0,0);ctx.clearRect(0,0,w,h);
  if(!state.request)return;
  const v=view(),s=v.toScreen;
  ctx.strokeStyle='#e9eee6';ctx.lineWidth=1;
  const spacing=v.scale*10,origin=s([0,0]);
  for(let x=origin[0]%spacing;x<w;x+=spacing){ctx.beginPath();ctx.moveTo(x,0);ctx.lineTo(x,h);ctx.stroke();}
  for(let y=origin[1]%spacing;y<h;y+=spacing){ctx.beginPath();ctx.moveTo(0,y);ctx.lineTo(w,y);ctx.stroke();}
  function line(points,color,width=1,dash=[]){if(!points?.length)return;ctx.strokeStyle=color;ctx.lineWidth=width;ctx.setLineDash(dash);ctx.beginPath();points.forEach((p,i)=>{const a=s(p);i?ctx.lineTo(...a):ctx.moveTo(...a)});ctx.stroke();ctx.setLineDash([]);}
  function circle(p,r,fill,stroke){const a=s(p);ctx.beginPath();ctx.arc(...a,r*v.scale,0,Math.PI*2);if(fill){ctx.fillStyle=fill;ctx.fill();}if(stroke){ctx.strokeStyle=stroke;ctx.lineWidth=1.3;ctx.stroke();}}
  const trajectory=[];
  if(state.design){
    for(let i=0;i<=256;i++){const p=pose(state.design.z,i*2*Math.PI/256);if(p)trajectory.push(p.P);}
    if($('sweep').checked){
      for(let i=0;i<64;i++){const p=pose(state.design.z,i*2*Math.PI/64);if(!p)continue;
        const pairs=state.request.components==='all'?[['A','B'],['B','C'],['C','D'],['B','P'],['C','P']]:[];
        for(const [a,b]of pairs)line([p[a],p[b]],'#c3d4c41e',Math.max(1,state.request.linkRadiusMm*2*v.scale));
        circle(p.P,Math.max(state.request.toolRadiusMm,.35),'#dba07924');
      }
    }
    line(trajectory,'#c7774a',1.6);
  }
  for(const o of state.request.obstacles){circle([o.x,o.y],o.radius+state.request.clearanceMm,'#bd625018','#b65c4566');circle([o.x,o.y],o.radius,'#e9b6a154','#a6504055');const p=s([o.x,o.y]);ctx.fillStyle='#a65040';ctx.font='10px ui-monospace,monospace';ctx.fillText('×',p[0]-3,p[1]+3);}
  const target=state.request.target;
  line(target.concat([target[0]]),'#248b94',1.6,[3,4]);
  for(let i=0;i<target.length;i++){const a=s(target[i]);ctx.beginPath();ctx.arc(...a,state.mode==='edit'?2.5:1.4,0,Math.PI*2);ctx.fillStyle='#248b94';ctx.fill();if(i===0){ctx.fillStyle='#248b94';ctx.font='10px ui-monospace,monospace';ctx.fillText('START',a[0]+7,a[1]-8);}}
  if(state.design){
    const p=pose(state.design.z,state.phase*Math.PI/180);
    if(p){
      line([p.A,p.D],'#74877b',4,[4,4]);
      line([p.A,p.B],'#526d65',Math.max(3,2*state.request.linkRadiusMm*v.scale));line([p.C,p.D],'#526d65',Math.max(3,2*state.request.linkRadiusMm*v.scale));
      for(const [a,b]of [['B','C'],['B','P'],['C','P']])line([p[a],p[b]],'#c77549',Math.max(3,2*state.request.linkRadiusMm*v.scale));
      for(const k of ['A','B','C','D']){circle(p[k],2.1,'#fbfcf8','#526d65');const a=s(p[k]);ctx.font='10px ui-monospace,monospace';ctx.fillStyle='#526d65';ctx.fillText(k,a[0]+8,a[1]+4);}
      circle(p.P,Math.max(2,state.request.toolRadiusMm),'#c77549','#9b4b2c');const a=s(p.P);ctx.fillStyle='#a35832';ctx.font='10px ui-monospace,monospace';ctx.fillText('TOOL',a[0]+8,a[1]+4);
    } else {ctx.fillStyle='#ab413b';ctx.font='13px sans-serif';ctx.fillText('These dimensions do not close at this phase.',20,25);}
  }
  if(state.stroke.length)line(state.stroke,'#137f89',3);
}
function renderResult(result){
  const report=result.report, status=report.state;
  const title={clear_under_model:'Clear across the whole cycle.',collision:'A collision is confirmed.',unresolved:'The check cannot settle it.',no_obstacles:'No obstacles to check.'}[status]||'Calculation returned.';
  $('resultCard').className='resultcard '+({clear_under_model:'clear',collision:'collision',unresolved:'unresolved'}[status]||'');
  $('resultLabel').textContent={clear_under_model:'MODELED CLEARANCE',collision:'NOMINAL COLLISION WITNESS',unresolved:'UNRESOLVED · NO CLEAR VERDICT',no_obstacles:'NO CLEARANCE CLAIM'}[status]||status;
  $('resultTitle').textContent=title;
  $('resultText').textContent=status==='clear_under_model'?`Checked ${state.request.components==='all'?'six bar capsules and the tool':'the tool only'} against ${state.request.obstacles.length} obstacle(s), for the full revolution and declared dimension intervals. This is a geometric model, not physical validation.`:status==='collision'?'A bounded phase interval puts a nominal checked shape inside the forbidden region. Jump to the witness to inspect it.':status==='no_obstacles'?'Add a forbidden region to ask a clearance question. Path fitting and geometry are still calculated.':report.reason||'Tangency, uncertain geometry or the finite subdivision budget prevents a clear verdict.';
  $('metrics').replaceChildren();
  const max=result.fit?.maxErrorMm;
  for(const [label,value]of [['PATH MAX ERROR',typeof max==='number'?max.toFixed(3)+' mm':'—'],['INTERVAL CELLS',String(report.cells??'—')]]){const d=document.createElement('div'),b=document.createElement('b');b.textContent=value;d.append(b,document.createTextNode(label));$('metrics').append(d);}
  if(result.baseline?.minimumGapMm!==null&&typeof result.baseline?.minimumGapMm==='number'){
    const d=document.createElement('div'),b=document.createElement('b');d.className='baseline';
    b.textContent=(result.baseline.intersects?'Overlap':'Misses')+' · '+result.baseline.minimumGapMm.toFixed(3)+' mm';
    d.append(b,document.createTextNode('64 NOMINAL FRAMES · SAMPLED GAP'));
    $('metrics').append(d);
  }
  if(typeof max==='number'&&max>state.request.pathToleranceMm){const p=document.createElement('p');p.textContent='Approximate fit: the requested path error was exceeded. Clearance refers to the actual mechanism path.';$('metrics').append(p);}
  $('witness').hidden=!report.witness;
  $('identity').textContent='CURRENT · '+String(report.inputSha256||report.inputHash||'').slice(0,8);
}
async function operation(kind){
  if(state.busy)return;
  let payload;
  try{state.request=request();state.design=design();payload=kind==='solve'?state.request:{request:state.request,design:state.design};}catch(e){notice(e.message);return;}
  state.busy=true;const revision=state.revision;
  ['solve','check','export','example'].forEach(k=>$(k).disabled=true);
  $('identity').textContent=kind==='solve'?'FITTING · FINITE SEARCH':'CHECKING ENTIRE CYCLE';
  $('resultLabel').textContent='CALCULATION IN PROGRESS';
  try{
    const response=await fetch('/api/'+kind,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(payload)});
    const result=await response.json();if(!response.ok)throw new Error(result.error||'Calculation failed.');
    if(revision!==state.revision){notice('Input changed while calculating. Recalculate the current draft.');return;}
    state.result=result;state.request=result.request;state.design=result.design;state.current=true;controls();renderResult(result);if(kind==='solve')fitView();
  }catch(e){state.current=false;$('identity').textContent='REFUSED · EDIT INPUT';$('resultLabel').textContent='NO VALID RESULT';$('resultTitle').textContent='This input was refused.';$('resultText').textContent=e.message;$('resultCard').className='resultcard unresolved';$('witness').hidden=true;}
  finally{state.busy=false;['solve','check','example'].forEach(k=>$(k).disabled=false);$('export').disabled=!state.current;}
}
function download(bytes,name,type){const url=URL.createObjectURL(new Blob([bytes],{type}));const a=document.createElement('a');a.href=url;a.download=name;a.click();setTimeout(()=>URL.revokeObjectURL(url),10000);}
async function exportDesign(){
  if(!state.current||state.busy)return;
  let payload;try{payload={request:request(),design:design()};}catch(e){notice(e.message);return;}
  const revision=state.revision;state.busy=true;['solve','check','export','example'].forEach(k=>$(k).disabled=true);$('identity').textContent='RECOMPUTING EXPORT';
  try{const reply=await fetch('/api/export',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(payload)});if(!reply.ok){const e=await reply.json();throw new Error(e.error||'Export failed.');}const bytes=await reply.arrayBuffer();if(revision!==state.revision){notice('The draft changed. Recalculate before exporting.');return;}download(bytes,'sweepforge-design.zip','application/zip');notice('Export includes frozen inputs, calculations, flat patterns and an offline replay.');renderResult(state.result);}
  catch(e){notice(e.message);}
  finally{state.busy=false;['solve','check','example'].forEach(k=>$(k).disabled=false);$('export').disabled=!state.current;}
}
function screen(event){const r=canvas.getBoundingClientRect();return [event.clientX-r.left,event.clientY-r.top];}
canvas.addEventListener('pointerdown',event=>{
  if(!state.request)return;canvas.setPointerCapture(event.pointerId);const p=view().toWorld(screen(event));
  if(state.mode==='obstacle'){
    try{state.request=request();}catch(e){notice(e.message);return;}
    if(state.request.obstacles.length>=8){notice('At most 8 obstacles are supported.');return;}
    state.request.obstacles.push({x:+p[0].toFixed(3),y:+p[1].toFixed(3),radius:6});obstacles();invalidate();setMode('edit');
  }else if(state.mode==='draw'){state.stroke=[p];state.drag='draw';}
  else{let best=-1,dist=13;state.request.target.forEach((a,i)=>{const b=view().toScreen(a),s=screen(event),d=Math.hypot(b[0]-s[0],b[1]-s[1]);if(d<dist){best=i;dist=d;}});if(best>=0){state.drag=best;invalidate();}}
});
canvas.addEventListener('pointermove',event=>{
  if(state.drag===null)return;const p=view().toWorld(screen(event));const bounded=p.map(x=>Math.max(-250,Math.min(250,x)));
  if(state.drag==='draw'){const last=state.stroke.at(-1);if(Math.hypot(bounded[0]-last[0],bounded[1]-last[1])>.2&&state.stroke.length<2048)state.stroke.push(bounded);}
  else state.request.target[state.drag]=bounded;
});
function endStroke(){if(state.drag==='draw'){try{state.request.target=resample(state.stroke);invalidate();notice('48 equal-phase points assigned. Fit a mechanism to the new path.');}catch(e){notice(e.message);}state.stroke=[];}state.drag=null;}
canvas.addEventListener('pointerup',endStroke);canvas.addEventListener('pointercancel',()=>{state.drag=null;state.stroke=[];});
$('editMode').onclick=()=>setMode('edit');$('drawMode').onclick=()=>setMode('draw');$('obstacleMode').onclick=()=>setMode('obstacle');$('addObstacle').onclick=()=>{setMode('obstacle');canvas.scrollIntoView({block:'center',behavior:'smooth'});canvas.focus();};
$('resetView').onclick=fitView;$('play').onclick=()=>{state.playing=!state.playing;$('play').textContent=state.playing?'Ⅱ':'▶';$('play').setAttribute('aria-label',state.playing?'Pause animation':'Play animation');};
$('phase').oninput=()=>{state.phase=Number($('phase').value);state.playing=false;$('play').textContent='▶';$('play').setAttribute('aria-label','Play animation');$('phaseValue').textContent=state.phase.toFixed(1)+'°';};
fields.forEach(k=>$(k).addEventListener('input',()=>{invalidate();try{state.request[k]=number($(k));}catch{}}));$('components').onchange=()=>{state.request.components=$('components').value;invalidate();};
$('solve').onclick=()=>operation('solve');$('check').onclick=()=>operation('check');$('export').onclick=exportDesign;
$('witness').onclick=()=>{const w=state.result?.report.witness;if(!w||!state.current)return;state.phase=(w.angleRad??(w.angleInterval?.reduce((a,b)=>a+b,0)/2)??0)*180/Math.PI;state.playing=false;$('phase').value=state.phase;$('phaseValue').textContent=state.phase.toFixed(2)+'°';$('play').textContent='▶';$('play').setAttribute('aria-label','Play animation');canvas.scrollIntoView({block:'center',behavior:'smooth'});};
$('saveRequest').onclick=()=>{try{download(JSON.stringify(request(),null,2)+'\n','sweepforge-request.json','application/json');}catch(e){notice(e.message);}};
$('import').onclick=async()=>{
  const revision=state.revision;
  try{const value=JSON.parse($('jsonInput').value);let r=Array.isArray(value)?{...request(),target:value}:value;
    if(!r||r.schema!=='sweepforge/1'||!Array.isArray(r.target)||r.target.length<8||r.target.length>128||r.target.some(p=>!Array.isArray(p)||p.length!==2||p.some(x=>typeof x!=='number'||!Number.isFinite(x)||Math.abs(x)>250))||!Array.isArray(r.obstacles)||r.obstacles.length>8)throw new Error('Expected a sweepforge/1 request or 8–128 finite [x,y] points within ±250 mm.');
    $('import').disabled=true;$('importStatus').textContent='Validating input…';
    const reply=await fetch('/api/validate',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(r)});
    const normalized=await reply.json();if(!reply.ok)throw new Error(normalized.error||'Input refused.');
    if(revision!==state.revision)throw new Error('The draft changed during validation. Paste again to replace it.');
    state.request=normalized.request;controls();invalidate();fitView();$('importStatus').textContent='Input loaded. Fit the requested path or check the existing dimensions.';
  }catch(e){$('importStatus').textContent=e.message;}
  finally{$('import').disabled=false;}
};
async function loadExample(index){const ex=state.examples[index];state.request=clone(ex.request);state.design=clone(ex.design);state.result=null;controls();invalidate();fitView();$('exampleDescription').textContent=ex.description;await operation('check');}
$('example').onchange=()=>loadExample(Number($('example').value));
let previous=0;
function frame(time){if(state.playing){state.phase=(state.phase+Math.min(50,time-previous)*.018)%360;$('phase').value=state.phase;$('phaseValue').textContent=Math.round(state.phase)+'°';}previous=time;draw();requestAnimationFrame(frame);}
async function start(){try{const reply=await fetch('/api/examples');state.examples=await reply.json();state.examples.forEach((ex,i)=>{const o=document.createElement('option');o.value=i;o.textContent=ex.name;$('example').append(o);});await loadExample(0);}catch(e){$('resultText').textContent=e.message;}requestAnimationFrame(frame);}
if(typeof document!=='undefined')start();
