const {chromium}=require('playwright');
(async()=>{const b=await chromium.launch();const pg=await b.newPage({viewport:{width:1280,height:720}});
pg.on('pageerror',e=>console.log('ERR',e.message));pg.on('console',m=>{const t=m.text();if(!/GL Driver|PixiJS|DragonBones|Website|Source|background:/.test(t))console.log('LOG',t.slice(0,200))});
await pg.goto('file://'+process.argv[2]);await pg.waitForFunction('window.READY===true',{timeout:60000});
console.log(JSON.stringify(await pg.evaluate(()=>({TOTAL,T_F,T_B}))));
for(const t of process.argv.slice(4).map(Number)){const ms=Date.now();await pg.evaluate(t=>seek(t),t);console.log(t,'seek ms',Date.now()-ms);await pg.screenshot({path:`${process.argv[3]}/s_${t.toFixed(2)}.png`})}
await b.close()})();
