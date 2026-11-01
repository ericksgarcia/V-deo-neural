import sys,json,time,requests
M="https://api.replicate.com/v1/models/recraft-ai/recraft-v4-styles-pro-svg/predictions"
def upload(path):
    r=requests.post('https://api.replicate.com/v1/files',files={'content':(path.split('/')[-1],open(path,'rb'),'image/png')});r.raise_for_status();return r.json()['urls']['get']
def gerar(prompt,saida,size="2048x2048",refs=None,style_id=None,match="precise"):
    inp={"prompt":prompt,"size":size,"style_match":match}
    if style_id: inp["style_id"]=style_id
    else: inp["style_reference_images"]=refs
    while True:
        r=requests.post(M,headers={"Prefer":"wait=60"},json={"input":inp},timeout=180)
        if r.status_code!=429: break
        time.sleep(r.json().get("retry_after",3)+1)
    p=r.json()
    if "urls" not in p: raise SystemExit(p)
    while p.get("status") not in("succeeded","failed","canceled"):
        time.sleep(3);p=requests.get(p["urls"]["get"],timeout=60).json()
    if p["status"]!="succeeded": raise SystemExit(p)
    out=p["output"]; img=out["image"] if isinstance(out,dict) else (out[0] if isinstance(out,list) else out)
    if img.startswith("data:"):
        import base64; head,b=img.split(",",1); data=base64.b64decode(b) if ";base64" in head else b.encode()
    else: data=requests.get(img,timeout=120).content
    open(saida,"wb").write(data)
    out={k:(v if not (isinstance(v,str) and v.startswith("data:")) else "<data-uri>") for k,v in out.items()} if isinstance(out,dict) else out
    json.dump({"output":out,"metrics":p.get("metrics"),"input":{k:v for k,v in inp.items() if k!='prompt'}},open(saida+'.json','w'),indent=1)
    print(saida,p.get("metrics"),(out.get("style_id") if isinstance(out,dict) else None))
