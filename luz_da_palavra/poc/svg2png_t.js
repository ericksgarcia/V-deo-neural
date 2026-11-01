const {chromium}=require('playwright');const fs=require('fs');
(async()=>{const [svg,png,w]=process.argv.slice(2);let s=fs.readFileSync(svg,'utf8').replace(/width="\d+" height="\d+"/,`width="${w}" height="${w}"`);
fs.writeFileSync(png+'.html',`<body style="margin:0;background:transparent">${s}`);
const b=await chromium.launch();const pg=await b.newPage({viewport:{width:+w,height:+w}});await pg.goto('file://'+png+'.html');
await pg.screenshot({path:png,omitBackground:true});await b.close();fs.unlinkSync(png+'.html')})();
