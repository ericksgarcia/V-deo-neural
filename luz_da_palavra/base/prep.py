"""Imagens base (raster) -> RGBA sem fundo, escaladas para um canvas 2048 com pés em y=2025. Saída: base/{front,back,side}.png"""
import numpy as np
from PIL import Image
from scipy import ndimage
SRC={'back':'base/raw3.png','side':'base/raw4.png','front':'base/raw5.png'}
for n,p in SRC.items():
    im=Image.open(p).convert('RGB');a=np.array(im).astype(int)
    mx,mn=a.max(2),a.min(2)
    bgc=(mn>=180)&((mx-mn)<=14)
    # só o fundo conectado à borda
    lab,k=ndimage.label(bgc);edge=set(lab[0,:])|set(lab[-1,:])|set(lab[:,0])|set(lab[:,-1]);edge.discard(0)
    bg=np.isin(lab,list(edge))
    fg=~bg
    fg=ndimage.binary_opening(fg,iterations=1);lab2,k2=ndimage.label(fg)
    if k2>1:
        sz=ndimage.sum(fg,lab2,range(1,k2+1));fg=lab2==(1+int(np.argmax(sz)))
    holes=ndimage.binary_fill_holes(fg)&~fg;hl,hk=ndimage.label(holes)
    for i in range(1,hk+1):
        m=hl==i
        if m.sum()<1500: fg|=m                       # só buracos pequenos (olhos etc.); o vão entre as pernas fica vazio
    alpha=(fg*255).astype(np.uint8)
    rgba=np.dstack([np.array(im),alpha]);Image.fromarray(rgba).save(f'base/{n}_raw_rgba.png')
    ys,xs=np.where(fg);y0,y1,x0,x1=ys.min(),ys.max(),xs.min(),xs.max()
    crop=Image.fromarray(rgba[y0:y1+1,x0:x1+1]);s=2000/crop.height
    if crop.width*s>2020: s=2020/crop.width
    crop=crop.resize((round(crop.width*s),round(crop.height*s)),Image.LANCZOS)
    can=Image.new('RGBA',(2048,2048),(0,0,0,0));ox=(2048-crop.width)//2;oy=2025-crop.height
    can.alpha_composite(crop,(ox,oy));can.save(f'base/{n}.png')
    print(n,'bbox',(x0,y0,x1,y1),'escala',round(s,3),'canvas bbox',can.split()[-1].getbbox())
