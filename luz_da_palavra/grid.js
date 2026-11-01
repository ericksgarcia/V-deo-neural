// node grid.js svg out.png x y w h px step
const {chromium}=require('playwright');const fs=require('fs');
(async()=>{const [svg,png,x,y,w,h,px,step]=process.argv.slice(2);let s=fs.readFileSync(svg,'utf8').replace(/<metadata>[\s\S]*?<\/metadata>/,'');
const vbm=s.match(/viewBox="([^"]*)"/)[1];
s=s.replace(/viewBox="[^"]*" width="\d+" height="\d+" preserveAspectRatio="none"/,`viewBox="${x} ${y} ${w} ${h}" width="${px}" height="${Math.round(px*h/w)}"`);
let g='';const st=+step;
for(let gx=Math.ceil(x/st)*st;gx<=+x+ +w;gx+=st)g+=`<line x1="${gx}" y1="${y}" x2="${gx}" y2="${+y+ +h}" stroke="#00f" stroke-width="${w/900}" opacity=".5"/><text x="${gx+2}" y="${+y+ +h*0.03}" font-size="${w/55}" fill="#00f">${gx}</text>`;
for(let gy=Math.ceil(y/st)*st;gy<=+y+ +h;gy+=st)g+=`<line x1="${x}" y1="${gy}" x2="${+x+ +w}" y2="${gy}" stroke="#f0f" stroke-width="${w/900}" opacity=".5"/><text x="${+x+ +w*0.005}" y="${gy-2}" font-size="${w/55}" fill="#f0f">${gy}</text>`;
const html=`<body style="margin:0;position:relative">${s}<svg style="position:absolute;left:0;top:0" width="${px}" height="${Math.round(px*h/w)}" viewBox="${x} ${y} ${w} ${h}">${g}</svg>`;
fs.writeFileSync(png+'.html',html);
const b=await chromium.launch();const pg=await b.newPage({viewport:{width:+px,height:Math.round(px*h/w)}});
await pg.goto('file://'+png+'.html');await pg.screenshot({path:png});await b.close();fs.unlinkSync(png+'.html')})();
