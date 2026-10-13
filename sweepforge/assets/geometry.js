export function pose(z, angle, ground=80) {
  const [r,p,q,u,v,phase,yaw,ox,oy]=z;
  const B=[r*Math.cos(angle+phase),r*Math.sin(angle+phase)], D=[ground,0];
  const dx=D[0]-B[0],dy=-B[1],d=Math.hypot(dx,dy);
  const s=(p*p-q*q+d*d)/(2*d),h2=p*p-s*s;
  if (!(d>0) || !(h2>0)) return null;
  const h=Math.sqrt(h2), C=[B[0]+s*dx/d-h*dy/d,B[1]+s*dy/d+h*dx/d];
  const ax=(C[0]-B[0])/p, ay=(C[1]-B[1])/p;
  const P=[B[0]+u*ax-v*ay,B[1]+u*ay+v*ax];
  const map=([x,y])=>[x*Math.cos(yaw)-y*Math.sin(yaw)+ox,x*Math.sin(yaw)+y*Math.cos(yaw)+oy];
  return Object.fromEntries(Object.entries({A:[0,0],B,C,D,P}).map(([k,v])=>[k,map(v)]));
}

export function resample(points, count=48) {
  if(points.length<3) throw new Error('Draw a longer closed path.');
  const loop=points.concat([points[0]]),length=[0];
  for(let i=1;i<loop.length;i++)length.push(length.at(-1)+Math.hypot(loop[i][0]-loop[i-1][0],loop[i][1]-loop[i-1][1]));
  const total=length.at(-1);
  if(!(total>1))throw new Error('The drawn path must be longer than 1 mm.');
  let j=1;
  return Array.from({length:count},(_,i)=>{
    const d=i*total/count;
    while(j<length.length-1&&length[j]<d)j++;
    const f=(d-length[j-1])/(length[j]-length[j-1]||1);
    return [0,1].map(k=>loop[j-1][k]+f*(loop[j][k]-loop[j-1][k]));
  });
}
