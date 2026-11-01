"""Ciclo de caminhada único (usado por Blender e Inochi2D). Fase phi em [0,1). Unidades: vb (pixels do SVG 2048), eixo x p/ direita, 'up' p/ cima.
O personagem olha para a ESQUERDA (frente = -x). Rotações em graus, positivas = horário na tela (pitch>0 = ponta do pé para cima)."""
import math
T=1.2            # período (2 passos)
A=120.0          # meia excursão do pé no referencial do corpo
STANCE=0.60      # fração de apoio
LIFT=42.0
def sm(u): u=max(0.0,min(1.0,u)); return u*u*(3-2*u)
def foot(phi):
    u=phi%1.0
    if u<STANCE:                      # apoio: pé parado no chão => anda para trás no referencial do corpo
        s=u/STANCE; dx=-A+2*A*s; up=0.0
        pitch=10*(1-sm(s/0.18))+(-24*sm((s-0.80)/0.20))      # calcanhar toca (ponta p/ cima) -> chato -> calcanhar sobe
    else:                             # balanço
        s=(u-STANCE)/(1-STANCE); e=sm(s)*0.85+s*0.15
        dx=A-2*A*e; up=LIFT*math.sin(math.pi*s)**0.8
        pitch=-24+34*sm(s*1.2)
    return dx,up,pitch
def body(phi):
    c=math.cos(2*math.pi*phi)
    return dict(pelvis_up=-14*(1+math.cos(4*math.pi*phi))/2,chest=1.1*math.sin(4*math.pi*phi),neck=-1.1*math.sin(4*math.pi*phi),
                head=1.2*math.sin(4*math.pi*phi+0.6),sho=-11*c,elb=-3.5*max(0,c),fore1=-4*max(0,c),hand=2*c,skirt=-3.5*math.sin(2*math.pi*phi+0.6))
V_VB=2*A/(STANCE*T)    # velocidade do corpo (vb/s) para o pé de apoio ficar parado no chão
