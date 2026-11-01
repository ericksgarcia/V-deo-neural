const {chromium}=require('playwright');
(async()=>{const b=await chromium.launch();const pg=await b.newPage();
await pg.goto('file://'+process.argv[2]);
const r=await pg.evaluate(()=>[...document.querySelectorAll('path')].map((p,i)=>{const b=p.getBBox();return [i,Math.round(b.x),Math.round(b.y),Math.round(b.x+b.width),Math.round(b.y+b.height),p.getAttribute('fill')]}));
console.log(r.map(x=>x.join(' ')).join('\n'));await b.close()})();
