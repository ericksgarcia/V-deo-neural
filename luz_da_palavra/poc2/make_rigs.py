import sys,re,json
sys.path.insert(0,'poc2')
import meshlib as M
isred=lambda h:(lambda r,g,b:r>100 and g<70 and b<55 and r>g*2.2)(int(h[1:3],16),int(h[3:5],16),int(h[5:7],16))
OUT='poc2/out'
def tpose(sy,ey,wy,wyR):
    B=[('root',None,0,0),('pelvis','root',1010,1060),('skirt','pelvis',1010,1100),('chest','pelvis',1010,780),('neck','chest',1010,490),('head','neck',1010,490),
     ('shoL','chest',800,sy),('elbL','shoL',560,ey),('fore1L','elbL',477,(2*ey+wy)//3),('fore2L','fore1L',393,(ey+2*wy)//3),('handL','fore2L',310,wy),
     ('shoR','chest',1220,sy),('elbR','shoR',1460,ey),('wrR','elbR',1735,wyR)]
    C=[('root',(1010,1160),(1010,1660),235),('root',(930,1700),(840,1960),70),('root',(1090,1700),(1170,1960),70),('skirt',(1010,1730),(1010,1830),235),
     ('pelvis',(1010,1100),(1010,800),95),('chest',(1010,800),(1010,520),95),('neck',(1010,520),(1010,440),40),('head',(1010,440),(1005,110),135),
     ('shoL',(800,sy),(560,ey),38),('elbL',(560,ey),(477,(2*ey+wy)//3),38),('fore1L',(477,(2*ey+wy)//3),(393,(ey+2*wy)//3),38),('fore2L',(393,(ey+2*wy)//3),(310,wy),38),('handL',(310,wy),(45,wy),48),
     ('shoR',(1220,sy),(1460,ey),38),('elbR',(1460,ey),(1735,wyR),38),('wrR',(1735,wyR),(2000,wyR),48)]
    dense=[(800,sy,150),(560,ey,160),(310,wy,200),(180,wy,200),(1220,sy,120),(1460,ey,120),(1735,wyR,150),(1880,wyR,180),(1010,500,120)]
    return B,C,dense
st={}
# ---- frente / costas: uma camada
for view,svg,args in [('front','gen3/frente.svg',(545,595,605,610)),('back','gen3/costas.svg',(530,565,570,575))]:
    B,C,dense=tpose(*args);P=[p for p in M.load_paths(svg) if p[0] not in ('#f8f5f0','#f5f3ee')]   # halos da arte
    st[view]=M.build_view('jesus_'+view,B,[{'name':'body','paths':P,'caps':C,'dense':dense}],OUT)
# ---- perfil: camadas body / footB / footF / arm
P=M.load_paths('gen3/perfil.svg')
# sola unida -> duas
for i,(c,d) in enumerate(P):
    n=[float(v) for v in re.findall(r'-?\d+\.?\d*',d)]
    if len(n)>8 and 880<min(n[0::2])<900 and max(n[0::2])>1215 and min(n[1::2])>1980:
        P[i:i+1]=[(c,'M 891 1991 L 1108 1991 L 1108 2027 L 891 2027 z'),(c,'M 1012 1991 L 1223 1991 L 1223 2027 L 1012 2027 z')];break
IDX_F={86,89,90,91,92,93,94,111,112,113,114,120,121,122,123,124,125,126,127,128,129,130,132,141,142,145,146,151,152,154}
IDX_B={83,84,85,87,88,117,118,119,133,134,136,137,138,143,153,158}
TUBE_F={89,90};TUBE_B={83,84,85}
body=[];arm=[];fF=[];fB=[];tF=[];tB=[]
for ii,(c,d) in enumerate(P):
    x0,y0,x1,y1=M.bbox(d)
    if ii in TUBE_F: tF.append((c,d));continue
    if ii in TUBE_B: tB.append((c,d));continue
    if ii in IDX_F or ii in IDX_B: continue                       # fragmentos de sandália da arte original: substituídos pelo pé redesenhado
    if y1-y0>1500: body.append((c,d,'clip-path="url(#c)"'))
    elif x0>985 and x1<1340 and y0>450 and y1<1400 and not isred(c): arm.append((c,d))
    elif y0>=1800 and y1>1860: continue
    else: body.append((c,d))
def shift(d,dx):
    k=[0]
    def f(m):
        v=float(m.group(0));i=k[0];k[0]+=1
        return ('%.3f'%(v+dx)) if i%2==0 else m.group(0)
    return re.sub(r'-?\d+\.?\d*',f,d)
def dark(c,f=0.9): return '#%02x%02x%02x'%tuple(int(int(c[i:i+2],16)*f) for i in (1,3,5))
import foot_art as FA
fF=FA.foot(0,1.0);fB=FA.foot(100,0.86)                                # pés redesenhados em vetor (pé de trás um pouco mais escuro)
tF.insert(0,('#d87f4b','M 985 1650 L 1075 1650 L 1075 1830 L 985 1830 z'));tB.insert(0,('#d87f4b','M 1085 1650 L 1176 1650 L 1176 1830 L 1085 1830 z'))   # pele da perna sobe escondida atrás do manto
body.insert(1,('#fae4ca','M 985 1060 L 1185 1060 L 1185 1430 L 985 1430 z'))
import numpy as np
LEGB=['thighF','shinF','thighB','shinB']
def robe_follow(V,Wt,names):
    ix=[names.index(n) for n in LEGB];pel=names.index('pelvis')
    y=V[:,1];f=0.25+0.30*np.clip((y-1500)/330.0,0,1)          # 25% acima do joelho -> 55% na barra
    for j in ix:
        mv=Wt[:,j]*(1-f);Wt[:,j]-=mv;Wt[:,pel]+=mv
    return Wt
PB=[('root',None,0,0),('pelvis','root',1060,1090),('skirt','pelvis',1060,1100),('chest','pelvis',1055,800),('neck','chest',1010,470),('head','neck',1010,470),
 ('sho','chest',1130,540),('elb','sho',1115,830),('fore1','elb',1105,950),('hand','fore1',1090,1100),
 ('thighF','pelvis',1040,1100),('shinF','thighF',1010,1500),('footF','shinF',1030,1925),('thighB','pelvis',1090,1100),('shinB','thighB',1070,1500),('footB','shinB',1130,1925)]
LEGC=[('thighF',(1040,1100),(1010,1500),32),('shinF',(1010,1500),(1018,1780),32),('thighB',(1090,1100),(1070,1500),32),('shinB',(1070,1500),(1108,1780),32)]
PC=LEGC+[('pelvis',(1060,1100),(1055,800),95),('chest',(1055,800),(1040,520),95),
 ('neck',(1010,520),(1010,440),40),('head',(1010,440),(1010,110),135)]
AC=[('sho',(1130,540),(1115,830),38),('elb',(1115,830),(1105,950),38),('fore1',(1105,950),(1090,1100),38),('hand',(1090,1100),(1075,1370),45)]
st['side']=M.build_view('jesus_side',PB,[
 {'name':'legB','paths':tB,'grad':('shinB','footB',1850,1920)},{'name':'footB','paths':fB,'rigid':'footB'},{'name':'legF','paths':tF,'grad':('shinF','footF',1850,1920)},{'name':'footF','paths':fF,'rigid':'footF'},
 {'name':'body','paths':body,'caps':PC,'post':robe_follow},
 {'name':'arm','paths':arm,'caps':AC,'dense':[(1130,540,150),(1115,830,160),(1085,1200,170)]}],OUT)
print(json.dumps(st))
