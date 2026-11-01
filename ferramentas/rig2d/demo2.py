"""Demo da camada de animação: máquina de estados + mocap + parâmetros. python demo2.py saida.mp4 [--ss 1]"""
import sys, os, math, argparse, subprocess, numpy as np, cv2
sys.path.insert(0, os.path.dirname(__file__))
import heroi, acoes
from motor import Camera
from demo import fundo, envelope_sintetico

# roteiro: (tempo, tipo, valor)
ROTEIRO = [(0.0, "vel", 1.0), (3.0, "vel", 0.0), (3.8, "cima", "acenar"), (3.8, "fala", 1), (6.6, "olhar", (0.9, 0.0)), (7.6, "olhar", (-0.9, 0.3)),
           (8.6, "olhar", (0.0, 0.0)), (8.8, "cima", "apontar_bvh"), (11.6, "cima", "pensar_bvh"), (14.8, "cima", "surpresa"), (16.8, "base", "pular_bvh"),
           (19.0, "vel", 1.0), (22.0, "vel", 0.0), (22.3, "cima", "reverencia"), (24.5, "fala", 0)]

def main():
    ap = argparse.ArgumentParser(); ap.add_argument("saida"); ap.add_argument("--ss", type=int, default=1); ap.add_argument("--seg", type=float, default=25.0)
    ap.add_argument("--fps", type=int, default=30); a = ap.parse_args()
    W, H, fps = 1080, 1920, a.fps; nfr = int(a.seg * fps)
    ch = heroi.construir(); cam = Camera(0.8, -180, 130, ss=a.ss); m = acoes.criar_maquina()
    env = envelope_sintetico(fps, a.seg, 3.8)
    bg0 = fundo(W, H)
    pr = subprocess.Popen(["ffmpeg", "-y", "-v", "error", "-f", "rawvideo", "-pix_fmt", "bgr24", "-s", f"{W}x{H}", "-r", str(fps), "-i", "-",
                           "-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "18", a.saida], stdin=subprocess.PIPE)
    ev = list(ROTEIRO); solo = 0.0; fala = 0.0; olhar = np.zeros(2); olhar_alvo = np.zeros(2)
    for i in range(nfr):
        t = i / fps
        while ev and ev[0][0] <= t:
            _, k, v = ev.pop(0)
            if k == "vel": m.entradas["vel"] = v
            elif k == "cima": m.ir("cima", v, 0.3)
            elif k == "base": m.ir("base", v, 0.25)
            elif k == "fala": fala = v; m.entradas["falando"] = v
            elif k == "olhar": olhar_alvo = np.array(v)
        olhar += (olhar_alvo - olhar) * min(1.0, 6.0 / fps)       # olhar suave
        m.par_extra.update(olhar_x=float(olhar[0]), olhar_y=float(olhar[1]))
        m.par_extra["olho"] = heroi.piscar(t)
        m.par_extra["boca"] = float(env[i]) if fala else 0.0
        m.par_extra["boca_larg"] = 1.0 + 0.25 * math.sin(2 * math.pi * 2.1 * t)
        pose = m.passo(1 / fps)
        heroi.aplicar(ch, pose, 1 / fps)
        base = m.camadas["base"].atual
        vel_chao = getattr(base, "vel_chao", None)
        v_scroll = (vel_chao * 0.8 if vel_chao and m.camadas["base"].nome_atual != "andar" else 760.0 * 0.8 * base.vel if hasattr(base, "vel") and base.vel > 0 else 0.0)
        if m.camadas["base"].nome_atual == "pular_bvh": v_scroll = 0.0
        solo += v_scroll / fps
        fr = bg0.copy(); gy = int(130 + 0.8 * 1905)
        cv2.rectangle(fr, (0, gy), (W, H), (70, 36, 20), -1); cv2.line(fr, (0, gy), (W, gy), (255, 220, 80), 3, cv2.LINE_AA)
        for k in range(-2, 14):
            x = int((k * 120 + solo) % (W + 240)) - 120
            cv2.line(fr, (x, gy), (int(540 + (x - 540) * 2.6), H), (170, 110, 30), 2, cv2.LINE_AA)
        sh = np.zeros((H, W), np.float32); cv2.ellipse(sh, (550, gy + 18), (255, 25), 0, 0, 360, 1.0, -1, cv2.LINE_AA)
        fr = fr * (1 - cv2.GaussianBlur(sh, (0, 0), 14)[..., None] * 0.55)
        c = ch.render(cam, W, H); fr = c[..., :3] * 255 + fr * (1 - c[..., 3:4])
        pr.stdin.write(np.clip(fr, 0, 255).astype(np.uint8).tobytes())
    pr.stdin.close(); pr.wait()

if __name__ == "__main__": main()
