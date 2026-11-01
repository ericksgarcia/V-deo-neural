const {chromium}=require('playwright');
(async()=>{const b=await chromium.launch();const ctx=await b.newContext({viewport:{width:1280,height:720},deviceScaleFactor:4});const pg=await ctx.newPage();
await pg.goto('file://'+process.argv[2]);await pg.waitForFunction('window.READY===true');
for(const t of process.argv.slice(4).map(Number)){await pg.evaluate(t=>seek(t),t);const x=await pg.evaluate(()=>st.x);const cx=x-95;
 await pg.screenshot({path:`${process.argv[3]}/h_${t.toFixed(2)}.png`,clip:{x:cx,y:610,width:190,height:62}})}
await b.close()})();
