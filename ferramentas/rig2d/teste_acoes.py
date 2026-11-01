"""Folha de contato das ações da biblioteca: python teste_acoes.py saida.png"""
import sys, os, math, numpy as np, cv2
sys.path.insert(0, os.path.dirname(__file__))
import heroi, acoes
from motor import Camera

def main(saida, lista=None):
    lista = lista or ["acenar", "apontar", "oferecer", "reverencia", "surpresa", "gesticular"]
    cam = Camera(0.30, -90, 70, ss=1); W, H = 420, 700
    cols = []
    for nome in lista:
        ch = heroi.construir(1.4); m = acoes.criar_maquina()
        m.entradas["vel"] = 0.0
        for _ in range(20): heroi.aplicar(ch, m.passo())
        acoes.nova_acao(m, nome)
        alvo = {"acenar": 1.6, "apontar": 1.2, "oferecer": 1.4, "reverencia": 1.3, "surpresa": 0.9, "gesticular": 1.2}[nome]
        for _ in range(int(alvo * 30)): heroi.aplicar(ch, m.passo())
        c = ch.render(cam, W, H)
        fr = np.clip(c[..., :3] * 255 + np.array([40, 24, 16]) * (1 - c[..., 3:4]), 0, 255).astype(np.uint8)
        cv2.putText(fr, nome, (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.9, (255, 255, 255), 2)
        cols.append(fr)
    cv2.imwrite(saida, np.hstack(cols))

if __name__ == "__main__": main(sys.argv[1], sys.argv[2:] or None)
