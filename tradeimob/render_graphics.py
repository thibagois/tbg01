#!/usr/bin/env python3
"""Lower third + mini abertura de cada palestra do TradeImob Experience.

Gera, para cada palestra do config.json, dois arquivos ProRes 4444 com alfa:
  out/NN_abertura.mov       tela cheia, termina dissolvendo pra transparente
  out/NN_lower_third.mov    nome + cargo, entra e sai sozinho
e PNGs de prévia em out/preview/.

Uso:
  python3 render_graphics.py                 # renderiza tudo
  python3 render_graphics.py --preview       # só os PNGs (rápido)
  python3 render_graphics.py --so 2          # só a palestra 2

Dependências: Python 3 com Pillow e numpy, ffmpeg. A fonte Montserrat
(Google Fonts, OFL) é baixada sozinha na primeira execução.
"""
import argparse
import json
import math
import subprocess
import sys
import urllib.request
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

HERE = Path(__file__).resolve().parent
FONT_URL = ("https://raw.githubusercontent.com/google/fonts/main/ofl/"
            "montserrat/Montserrat%5Bwght%5D.ttf")
FONT_PATH = HERE / "fonts" / "Montserrat.ttf"

# Paleta tirada do palco: painel de LED azul, fundo marinho, texto branco.
NAVY = (4, 10, 46)
NAVY_2 = (10, 31, 122)
BLUE = (30, 91, 255)
BLUE_LIGHT = (120, 160, 255)
WHITE = (255, 255, 255)


# ---------------------------------------------------------------- utilidades
def ensure_font():
    if not FONT_PATH.exists():
        FONT_PATH.parent.mkdir(parents=True, exist_ok=True)
        print("baixando Montserrat...")
        urllib.request.urlretrieve(FONT_URL, FONT_PATH)


_font_cache = {}


def font(size, weight="Bold"):
    key = (int(size), weight)
    if key not in _font_cache:
        f = ImageFont.truetype(str(FONT_PATH), int(size))
        f.set_variation_by_name(weight)
        _font_cache[key] = f
    return _font_cache[key]


def clamp01(x):
    return 0.0 if x < 0 else 1.0 if x > 1 else x


def ease_out(x):
    x = clamp01(x)
    return 1 - (1 - x) ** 3


def ease_in_out(x):
    x = clamp01(x)
    return 4 * x ** 3 if x < .5 else 1 - (-2 * x + 2) ** 3 / 2


def prog(t, start, dur):
    return clamp01((t - start) / dur)


def text_w(txt, f, tracking=0):
    if not txt:
        return 0
    return f.getlength(txt) + tracking * (len(txt) - 1)


def draw_text(d, xy, txt, f, fill, tracking=0):
    """Texto com espaçamento entre letras (tracking em px)."""
    if not tracking:
        d.text(xy, txt, font=f, fill=fill)
        return
    x, y = xy
    for ch in txt:
        d.text((x, y), ch, font=f, fill=fill)
        x += f.getlength(ch) + tracking


def with_alpha(layer, a):
    """Multiplica o alfa de uma camada RGBA por a (0..1)."""
    if a >= 1:
        return layer
    r, g, b, al = layer.split()
    al = al.point(lambda v: int(v * a))
    return Image.merge("RGBA", (r, g, b, al))


def reveal_up(layer, box, p):
    """Revela o conteúdo de box subindo de baixo pra cima (máscara deslizante)."""
    x0, y0, x1, y1 = box
    h = y1 - y0
    off = int((1 - ease_out(p)) * h)
    crop = layer.crop(box)
    out = Image.new("RGBA", layer.size, (0, 0, 0, 0))
    out.paste(crop.crop((0, 0, x1 - x0, h - off)), (x0, y0 + off))
    return out


def wrap_title(txt, max_w, sizes=(104, 92, 80, 70, 62)):
    """Quebra o tema em até 3 linhas, diminuindo a fonte até caber."""
    words = txt.upper().split()
    for size in sizes:
        f = font(size, "ExtraBold")
        lines, cur = [], ""
        for w in words:
            test = f"{cur} {w}".strip()
            if cur and text_w(test, f, -1) > max_w:
                lines.append(cur)
                cur = w
            else:
                cur = test
        lines.append(cur)
        if len(lines) <= 3 and all(text_w(l, f, -1) <= max_w for l in lines):
            return f, lines
    return f, lines[:3]


# ---------------------------------------------------------------- fundo LED
class LedWall:
    """Matriz de pontos azuis como o painel de LED do palco, com onda de brilho."""

    def __init__(self, w, h, pitch=16):
        self.w, self.h, self.p = w, h, pitch
        self.cols, self.rows = w // pitch + 2, h // pitch + 2
        yy, xx = np.mgrid[0:pitch, 0:pitch] - (pitch - 1) / 2
        self.dot = np.clip(1 - np.sqrt(xx ** 2 + yy ** 2) / (pitch * 0.32), 0, 1) ** 1.5
        rng = np.random.default_rng(7)
        self.noise = rng.random((self.rows, self.cols))
        gy, gx = np.mgrid[0:self.rows, 0:self.cols]
        self.gx, self.gy = gx / self.cols, gy / self.rows
        # gradiente de fundo marinho, mais claro no canto superior direito
        Y, X = np.mgrid[0:h, 0:w]
        d = np.sqrt(((X - w * .75) / w) ** 2 + ((Y - h * .2) / h) ** 2)
        k = np.clip(1 - d * 1.3, 0, 1)[..., None]
        self.base = (np.array(NAVY) * (1 - k) + np.array(NAVY_2) * k * .8)

    def frame(self, t):
        wave = 0.5 + 0.5 * np.sin((self.gx * 2.2 - self.gy * 1.2) * math.tau - t * 1.6)
        twinkle = 0.5 + 0.5 * np.sin(self.noise * 40 + t * 3.0)
        inten = 0.12 + 0.55 * wave ** 3 + 0.18 * twinkle * self.noise
        # mais denso à direita, some à esquerda onde fica o texto
        inten *= 0.25 + 0.75 * np.clip(self.gx * 1.4 - 0.15, 0, 1)
        full = np.kron(inten, self.dot)[:self.h, :self.w, None]
        img = self.base + full * np.array([70, 130, 255]) * 0.9
        return Image.fromarray(np.clip(img, 0, 255).astype(np.uint8), "RGB").convert("RGBA")


def arrow_mark(size, color):
    """Seta subindo à direita, inspirada no 'A' do logo."""
    im = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    w = max(3, size // 9)
    d.line([(size * .08, size * .92), (size * .88, size * .12)], fill=color, width=w)
    d.polygon([(size * .98, size * .02), (size * .55, size * .12),
               (size * .88, size * .45)], fill=color)
    return im


# ---------------------------------------------------------------- abertura
def abertura_frame(t, dur, info, W, H, wall):
    S = W / 1920  # escala relativa a 1080p
    img = wall.frame(t)
    # leve push-in
    z = 1 + 0.03 * t / dur
    if z > 1:
        zw, zh = int(W * z), int(H * z)
        img = img.resize((zw, zh), Image.BILINEAR).crop(
            ((zw - W) // 2, (zh - H) // 2, (zw - W) // 2 + W, (zh - H) // 2 + H))

    fg = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(fg)
    x0 = int(150 * S)

    # risco diagonal (a seta do logo) cruzando a tela no começo
    p = prog(t, 0.05, 0.9)
    if 0 < p < 1:
        streak = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        sd = ImageDraw.Draw(streak)
        e = ease_in_out(p)
        hx, hy = -200 * S + e * (W + 400 * S), H * .95 - e * H * 1.1
        tx, ty = hx - 520 * S, hy + 520 * S * H / W * 1.1
        sd.line([(tx, ty), (hx, hy)], fill=BLUE_LIGHT + (255,), width=int(6 * S))
        streak = streak.filter(ImageFilter.GaussianBlur(2 * S))
        fg.alpha_composite(streak)

    # kicker: seta + TRADEIMOB EXPERIENCE
    p = ease_out(prog(t, 0.35, 0.6))
    if p > 0:
        k = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        kd = ImageDraw.Draw(k)
        fk = font(30 * S, "Bold")
        ky = int(250 * S)
        k.alpha_composite(arrow_mark(int(40 * S), BLUE_LIGHT + (255,)), (x0, ky - int(4 * S)))
        draw_text(kd, (x0 + int(58 * S), ky), info["evento"], fk, WHITE + (255,), 7 * S)
        k = with_alpha(k, p)
        fg.alpha_composite(k, (int(-30 * S * (1 - p)), 0))

    # rótulo PALESTRA 0N
    p = ease_out(prog(t, 0.6, 0.6))
    if p > 0:
        fl = font(26 * S, "SemiBold")
        lab = info["rotulo"]
        ly = int(330 * S)
        lw = text_w(lab, fl, 5 * S) + 36 * S
        box = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        bd = ImageDraw.Draw(box)
        bd.rounded_rectangle([x0, ly, x0 + lw * p, ly + 50 * S], radius=int(6 * S),
                             fill=BLUE + (255,))
        if p > .5:
            draw_text(bd, (x0 + 18 * S, ly + 10 * S), lab, fl, WHITE + (255,), 5 * S)
        fg.alpha_composite(box)

    # título (tema), linha por linha subindo
    ftitle, lines = info["_title"]
    ty = int(420 * S)
    lh = int(ftitle.size * 1.08)
    for i, line in enumerate(lines):
        p = prog(t, 0.9 + i * 0.14, 0.7)
        if p <= 0:
            continue
        layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        ld = ImageDraw.Draw(layer)
        draw_text(ld, (x0, ty + i * lh), line, ftitle, WHITE + (255,), -1)
        fg.alpha_composite(reveal_up(layer, (0, ty + i * lh, W, ty + (i + 1) * lh + int(10 * S)), p))
    after_title = ty + len(lines) * lh + int(36 * S)

    # régua azul + palestrante
    p = ease_out(prog(t, 1.6, 0.7))
    if p > 0:
        d.rectangle([x0, after_title, x0 + int(120 * S * p), after_title + int(6 * S)],
                    fill=BLUE + (255,))
    p = ease_out(prog(t, 1.85, 0.7))
    if p > 0:
        sp = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        sd = ImageDraw.Draw(sp)
        fn = font(44 * S, "Bold")
        fc = font(28 * S, "Medium")
        sd.text((x0, after_title + 34 * S), info["palestrante"], font=fn, fill=WHITE + (255,))
        if info.get("cargo"):
            sd.text((x0, after_title + 92 * S), info["cargo"], font=fc, fill=BLUE_LIGHT + (255,))
        sp = with_alpha(sp, p)
        fg.alpha_composite(sp, (0, int(20 * S * (1 - p))))

    img.alpha_composite(fg)

    # saída: dissolve pra transparente no último segundo (vira transição pro vídeo)
    out = clamp01((dur - t) / 0.9)
    return with_alpha(img, ease_in_out(out))


# ---------------------------------------------------------------- lower third
def lower_third_frame(t, dur, info, W, H):
    S = W / 1920
    img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    x0 = int(110 * S)
    yb = int(H - 130 * S)  # base do bloco (margem de segurança)

    fn = font(54 * S, "ExtraBold")
    fc = font(28 * S, "SemiBold")
    fk = font(19 * S, "Bold")
    name, cargo = info["palestrante"], info.get("cargo") or info.get("tema", "")
    pad = int(34 * S)
    plate_w = int(max(text_w(name, fn), text_w(cargo, fc)) + pad * 2)
    plate_h = int(150 * S if cargo else 100 * S)
    py0 = yb - plate_h

    # in / out
    tin = t
    tout = dur - t
    k_out = ease_in_out(clamp01(1 - tout / 0.6))  # 0 → 1 nos 0,6 s finais

    # barra de acento (cresce do centro)
    pb = ease_out(prog(tin, 0.0, 0.35)) * (1 - k_out)
    if pb > 0:
        d = ImageDraw.Draw(img)
        cy = py0 + plate_h / 2
        hh = plate_h / 2 * pb
        d.rectangle([x0, cy - hh, x0 + int(10 * S), cy + hh], fill=BLUE + (255,))

    # placa marinho (abre pra direita)
    pp = ease_out(prog(tin, 0.15, 0.55))
    pw = plate_w * pp * (1 - ease_in_out(clamp01(1 - tout / 0.75)))
    if pw > 1:
        plate = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        pd = ImageDraw.Draw(plate)
        px = x0 + int(10 * S)
        pd.rectangle([px, py0, px + pw, yb], fill=NAVY + (228,))
        # brilho azul fininho no topo da placa
        pd.rectangle([px, py0, px + pw, py0 + max(1, int(2 * S))], fill=BLUE_LIGHT + (200,))
        img.alpha_composite(plate)

    # textos (sobem por máscara, somem antes da placa fechar)
    ta = 1 - k_out
    tx = x0 + int(10 * S) + pad
    pnm = prog(tin, 0.45, 0.5)
    if pnm > 0 and ta > 0:
        layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        ld = ImageDraw.Draw(layer)
        ny = py0 + int(20 * S)
        ld.text((tx, ny), name, font=fn, fill=WHITE + (255,))
        layer = reveal_up(layer, (tx - 4, ny, W, ny + int(72 * S)), pnm)
        img.alpha_composite(with_alpha(layer, ta))
    pcg = prog(tin, 0.6, 0.5)
    if cargo and pcg > 0 and ta > 0:
        layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        ld = ImageDraw.Draw(layer)
        cy = py0 + int(92 * S)
        ld.text((tx, cy), cargo, font=fc, fill=BLUE_LIGHT + (255,))
        layer = reveal_up(layer, (tx - 4, cy, W, cy + int(42 * S)), pcg)
        img.alpha_composite(with_alpha(layer, ta))

    # etiqueta do evento acima da placa
    pk = ease_out(prog(tin, 0.7, 0.5)) * ta
    if pk > 0:
        layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        ld = ImageDraw.Draw(layer)
        ky = py0 - int(36 * S)
        layer.alpha_composite(arrow_mark(int(22 * S), BLUE_LIGHT + (255,)), (x0, ky))
        draw_text(ld, (x0 + int(32 * S), ky + int(1 * S)), info["evento"], fk,
                  WHITE + (255,), 4 * S)
        img.alpha_composite(with_alpha(layer, pk), (int(-16 * S * (1 - pk)), 0))
    return img


# ---------------------------------------------------------------- render
def encoder(path, W, H, fps):
    num, den = (30000, 1001) if abs(fps - 29.97) < .01 else \
               (24000, 1001) if abs(fps - 23.976) < .01 else \
               (60000, 1001) if abs(fps - 59.94) < .01 else (int(round(fps)), 1)
    cmd = ["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgba",
           "-s", f"{W}x{H}", "-r", f"{num}/{den}", "-i", "-",
           "-c:v", "prores_ks", "-profile:v", "4444", "-pix_fmt", "yuva444p10le",
           "-alpha_bits", "16", "-vendor", "apl0", str(path)]
    return subprocess.Popen(cmd, stdin=subprocess.PIPE)


def render(fn, dur, fps, path, *args):
    n = int(round(dur * fps))
    W, H = args[1], args[2]
    p = encoder(path, W, H, fps)
    for i in range(n):
        p.stdin.write(fn(i / fps, dur, *args).tobytes())
    p.stdin.close()
    if p.wait():
        sys.exit(f"ffmpeg falhou em {path}")


def checker(W, H, s=32):
    """Xadrez de fundo pra prévia mostrar a transparência."""
    a = (np.indices((H, W)) // s).sum(0) % 2
    v = np.where(a, 70, 50).astype(np.uint8)
    return Image.fromarray(np.stack([v] * 3, -1), "RGB").convert("RGBA")


def load_config(path):
    cfg = json.loads(Path(path).read_text(encoding="utf-8"))
    talks = []
    for i, p in enumerate(cfg["palestras"], 1):
        info = dict(p)
        info["evento"] = cfg.get("evento", "TRADEIMOB EXPERIENCE")
        info["rotulo"] = f"PALESTRA {i:02d}"
        info["n"] = i
        talks.append(info)
    return cfg, talks


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", default=str(HERE / "config.json"))
    ap.add_argument("--preview", action="store_true", help="só PNGs de prévia")
    ap.add_argument("--so", type=int, help="renderiza só a palestra N")
    a = ap.parse_args()

    ensure_font()
    cfg, talks = load_config(a.config)
    W, H = cfg.get("resolucao", [1920, 1080])
    fps = float(cfg.get("fps", 29.97))
    g = cfg.get("graficos", {})
    d_ab, d_lt = float(g.get("abertura_seg", 6)), float(g.get("lower_third_seg", 8))
    out = (HERE / g.get("pasta_saida", "out")).resolve()
    (out / "preview").mkdir(parents=True, exist_ok=True)

    wall = LedWall(W, H, pitch=max(8, int(16 * W / 1920)))
    for info in talks:
        if a.so and info["n"] != a.so:
            continue
        info["_title"] = wrap_title(info["tema"], W * 0.72, sizes=[
            int(s * W / 1920) for s in (104, 92, 80, 70, 62)])
        n = info["n"]
        # prévias: abertura no auge e lower third parado
        abertura_frame(3.2, d_ab, info, W, H, wall).convert("RGB").save(
            out / "preview" / f"{n:02d}_abertura.png")
        lt = checker(W, H)
        lt.alpha_composite(lower_third_frame(3.0, d_lt, info, W, H))
        lt.convert("RGB").save(out / "preview" / f"{n:02d}_lower_third.png")
        if a.preview:
            print(f"prévia {n:02d} ok")
            continue
        render(abertura_frame, d_ab, fps, out / f"{n:02d}_abertura.mov", info, W, H, wall)
        render(lower_third_frame, d_lt, fps, out / f"{n:02d}_lower_third.mov", info, W, H)
        print(f"palestra {n:02d}: {info['palestrante']} — ok")
    print(f"arquivos em {out}")


if __name__ == "__main__":
    main()
