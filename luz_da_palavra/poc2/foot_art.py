"""Pé de perfil (olhando p/ a ESQUERDA) com sandália, desenhado em vetor no estilo do personagem. Coordenadas = px do SVG 2048 (tornozelo em ~(1030,1925))."""
SKIN='#f5b27c';SHADE='#d87f4b';DARK='#592612';STRAP='#783b20';RED='#a82e1e';OUT='#3d1a0b'
def sh(d,dx):
    import re
    k=[0]
    def f(m):
        v=float(m.group(0));i=k[0];k[0]+=1
        return ('%.2f'%(v+dx)) if i%2==0 else m.group(0)
    return re.sub(r'-?\d+\.?\d*',f,d)
def dark(c,f):
    return '#%02x%02x%02x'%tuple(int(int(c[i:i+2],16)*f) for i in (1,3,5))
def foot(dx=0,tone=1.0):
    S='stroke-linejoin="round" stroke-linecap="round"'
    L=[ # (cor, d, atributos extras)  — ordem de desenho
     (DARK,'M 836 1990 L 1096 1990 Q 1118 1990 1118 2009 Q 1118 2028 1096 2028 L 840 2028 Q 812 2028 812 2009 Q 812 1990 836 1990 z',f'stroke="{OUT}" stroke-width="3" {S}'),   # sola grossa
     (SHADE,'M 1090 1992 L 1090 1914 C 1088 1894 1072 1886 1052 1888 C 1022 1892 998 1904 968 1922 C 940 1940 898 1952 864 1966 C 840 1976 826 1985 828 1992 z',f'stroke="{OUT}" stroke-width="3" {S}'),  # base do pé (sombra)
     (SKIN,'M 1066 1992 L 1070 1916 C 1070 1900 1058 1894 1044 1896 C 1016 1900 992 1912 964 1928 C 936 1944 892 1954 862 1968 C 842 1977 832 1985 834 1992 z',''),   # pé claro
     ('#fbd9bb','M 833 1982 C 833 1971.6 859 1971.6 859 1982 C 859 1992.4 833 1992.4 833 1982 z',f'stroke="{OUT}" stroke-width="2.5" {S}'),
     ('#fbd9bb','M 859 1978 C 859 1967.6 885 1967.6 885 1978 C 885 1988.4 859 1988.4 859 1978 z',f'stroke="{OUT}" stroke-width="2.5" {S}'),
     ('#fbd9bb','M 886 1970 C 886 1960.4 910 1960.4 910 1970 C 910 1979.6 886 1979.6 886 1970 z',f'stroke="{OUT}" stroke-width="2.5" {S}'),
     ('#fbd9bb','M 911 1960 C 911 1951.2 933 1951.2 933 1960 C 933 1968.8 911 1968.8 911 1960 z',f'stroke="{OUT}" stroke-width="2.5" {S}'),
     ('none','M 1034 1986 L 1092 1906',f'fill="none" stroke="{OUT}" stroke-width="20" {S}'),('none','M 1034 1986 L 1092 1906',f'fill="none" stroke="{STRAP}" stroke-width="12" {S}'),   # tira do calcanhar
     ('none','M 952 1926 Q 988 1892 1034 1902',f'fill="none" stroke="{OUT}" stroke-width="22" {S}'),('none','M 952 1926 Q 988 1892 1034 1902',f'fill="none" stroke="{RED}" stroke-width="14" {S}'),     # tira do peito do pé
     ('none','M 990 1938 L 1020 1988',f'fill="none" stroke="{OUT}" stroke-width="20" {S}'),('none','M 990 1938 L 1020 1988',f'fill="none" stroke="{STRAP}" stroke-width="12" {S}'),           # tira central
    ]
    out=[]
    for c,d,a in L:
        if 'fill="none"' in a:
            import re
            a=re.sub(r'stroke="(#[0-9a-fA-F]{6})"',lambda m:'stroke="%s"'%dark(m.group(1),tone),a)
            out.append(('none',sh(d,dx),a))
        else: out.append((dark(c,tone),sh(d,dx),a))
    return out
if __name__=='__main__':
    P=foot(0,1.0)+foot(110,0.86)
    svg='<svg xmlns="http://www.w3.org/2000/svg" viewBox="780 1850 480 200" width="1920" height="800"><rect x="780" y="1850" width="480" height="200" fill="#fff"/>'+''.join(f'<path fill="{c}" d="{d}" {a}/>' for c,d,a in P)+'</svg>'
    open('poc2/_foot.svg','w').write(svg)
