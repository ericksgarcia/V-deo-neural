const {chromium}=require('playwright');const fs=require('fs');
(async()=>{const b=await chromium.launch();const pg=await b.newPage({viewport:{width:1280,height:720}});
await pg.goto('file://'+process.argv[2]);const out=process.argv[3];fs.mkdirSync(out,{recursive:true});
const TF=await pg.evaluate(()=>T_F);const fps=24,n=Math.round(5.4*fps);
for(let i=0;i<n;i++){const t=Math.min(TF-0.45+i/fps,TF+4.2);await pg.evaluate(t=>setT(t),t);await pg.screenshot({path:`${out}/f${String(i).padStart(4,'0')}.png`})}
await b.close()})();
