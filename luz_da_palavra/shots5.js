const {chromium}=require('playwright');
(async()=>{const b=await chromium.launch();const pg=await b.newPage({viewport:{width:1280,height:720}});
pg.on('pageerror',e=>console.log('ERR',e.message));pg.on('console',m=>console.log('LOG',m.text()));
await pg.goto('file://'+process.argv[2]);
console.log(JSON.stringify(await pg.evaluate(()=>({TOTAL,T_F,T_B,N:Object.fromEntries(Object.entries(VW).map(([k,v])=>[k,v.N]))}))));
for(const t of process.argv.slice(4).map(Number)){const ms=Date.now();await pg.evaluate(t=>setT(t),t);const e=Date.now()-ms;await pg.screenshot({path:`${process.argv[3]}/s_${t.toFixed(2)}.png`});console.log(t,'pose ms',e)}
await b.close()})();
