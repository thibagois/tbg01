"""Utilitários de composição: fontes, easing, texto, glow, leitura de clipes, pós."""
import json
import math
import os
import subprocess

import numpy as np
from PIL import Image, ImageChops, ImageDraw, ImageFilter, ImageFont

from timeline import W, H, FPS

KIT = os.environ.get("KIT", "/home/user/kit")

C = dict(
    black=(6, 7, 9), white=(242, 242, 240), red=(232, 22, 30), red_deep=(140, 8, 12),
    gray=(150, 154, 162), dim=(95, 98, 104), green=(28, 200, 122), amber=(255, 188, 36),
    panel=(17, 19, 23), panel2=(26, 29, 35),
)

_fonts = {}


def F(name, size):
    key = (name, size)
    if key not in _fonts:
        _fonts[key] = ImageFont.truetype(os.path.join(KIT, "fonts", name), size)
    return _fonts[key]


def fit_font(name, text, max_w, start):
    size = start
    while size > 20 and F(name, size).getlength(text) > max_w:
        size -= 2
    return F(name, size)


def clamp(x, a=0.0, b=1.0):
    return a if x < a else b if x > b else x


def prog(t, a, b):
    return clamp((t - a) / (b - a)) if b > a else float(t >= a)


def e_out3(x):
    return 1 - (1 - x) ** 3


def e_inout3(x):
    return 4 * x ** 3 if x < 0.5 else 1 - (-2 * x + 2) ** 3 / 2


def e_outexpo(x):
    return 1.0 if x >= 1 else 1 - 2 ** (-10 * x)


def e_outback(x, s=1.9):
    x -= 1
    return x * x * ((s + 1) * x + s) + 1


def lerp(a, b, x):
    return a + (b - a) * x


def hash01(*k):
    """Ruído determinístico 0-1 (para flicker e glitch reproduzíveis)."""
    h = 2166136261
    for v in k:
        for b in str(v).encode():
            h = ((h ^ b) * 16777619) & 0xFFFFFFFF
    return (h % 100000) / 100000.0


def rgba(col, a=1.0):
    return (col[0], col[1], col[2], int(255 * clamp(a)))


# ---------------------------------------------------------------- texto

def text_img(txt, font, fill, tracking=0, pad=0):
    """Renderiza texto num RGBA justo (com `pad` px de margem). Retorna (img, baseline_y)."""
    asc, desc = font.getmetrics()
    if tracking:
        widths = [font.getlength(ch) for ch in txt]
        tw = int(sum(widths) + tracking * (len(txt) - 1))
    else:
        tw = int(font.getlength(txt))
    img = Image.new("RGBA", (tw + 2 * pad + 4, asc + desc + 2 * pad), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    if tracking:
        x = pad
        for ch, cw in zip(txt, widths):
            d.text((x, pad + asc), ch, font=font, fill=fill, anchor="ls")
            x += cw + tracking
    else:
        d.text((pad, pad + asc), txt, font=font, fill=fill, anchor="ls")
    return img, pad + asc


def paste_text(layer, txt, font, fill, x, y, anchor="ms", tracking=0, alpha=1.0, scale=1.0, blur=0.0):
    """Cola texto em `layer` (RGBA) com alpha/escala/blur. (x, y) = âncora ('ms' centro-baseline,
    'ls' esquerda-baseline)."""
    if alpha <= 0.003:
        return
    pad = int(8 + blur * 3)
    img, base = text_img(txt, font, fill, tracking, pad)
    if scale != 1.0:
        nw, nh = max(1, int(img.width * scale)), max(1, int(img.height * scale))
        img = img.resize((nw, nh), Image.BICUBIC)
        base *= scale
    if blur > 0.3:
        img = img.filter(ImageFilter.GaussianBlur(blur))
    if alpha < 1:
        a = img.getchannel("A").point(lambda v: int(v * alpha))
        img.putalpha(a)
    if anchor[0] == "m":
        px = x - img.width / 2
    elif anchor[0] == "r":
        px = x - img.width + pad * scale
    else:
        px = x - pad * scale
    py = y - base
    layer.alpha_composite(img, (int(round(px)), int(round(py))))


def glow(layer, radius, strength=1.0, down=4):
    """Glow barato: blur em resolução reduzida. Recebe/retorna RGBA."""
    w, h = layer.size
    small = layer.resize((max(1, w // down), max(1, h // down)), Image.BILINEAR)
    small = small.filter(ImageFilter.GaussianBlur(max(0.5, radius / down)))
    g = small.resize((w, h), Image.BILINEAR)
    if strength != 1.0:
        arr = np.asarray(g).astype(np.float32)
        arr[..., 3] = np.clip(arr[..., 3] * strength, 0, 255)
        g = Image.fromarray(arr.astype(np.uint8), "RGBA")
    return g


def add_rgb(base_rgb, add_rgba, k=1.0):
    """Soma aditiva (luz) de um RGBA sobre um RGB, ponderada pelo alpha."""
    b = np.asarray(base_rgb).astype(np.float32)
    a = np.asarray(add_rgba).astype(np.float32)
    b += a[..., :3] * (a[..., 3:4] / 255.0) * k
    return Image.fromarray(np.clip(b, 0, 255).astype(np.uint8), "RGB")


def vgrad(w, h, stops):
    """Gradiente vertical RGBA. stops = [(pos0-1, (r,g,b,a)), ...]."""
    ys = np.linspace(0, 1, h, dtype=np.float32)
    out = np.zeros((h, 4), np.float32)
    ps = [p for p, _ in stops]
    for ch in range(4):
        out[:, ch] = np.interp(ys, ps, [c[ch] for _, c in stops])
    arr = np.repeat(out[:, None, :], w, axis=1)
    return Image.fromarray(arr.astype(np.uint8), "RGBA")


def zoom(img, s, cx=0.5, cy=0.5, dx=0.0, dy=0.0):
    """Push-in: recorta 1/s da imagem em torno de (cx, cy) e reescala."""
    if abs(s - 1) < 1e-4 and dx == 0 and dy == 0:
        return img
    w, h = img.size
    cw, ch = w / s, h / s
    x0 = clamp(cx * w - cw / 2 + dx, 0, w - cw)
    y0 = clamp(cy * h - ch / 2 + dy, 0, h - ch)
    return img.resize((w, h), Image.BILINEAR, box=(x0, y0, x0 + cw, y0 + ch))


def darken(img, k):
    return Image.eval(img, lambda v: int(v * k))


# ---------------------------------------------------------------- clipes

class Reader:
    def __init__(self, name, t0, blur=0):
        path = os.path.join(KIT, "mezz", name + ".mp4")
        vf = f"gblur=sigma={blur}" if blur else "null"
        self.p = subprocess.Popen(["ffmpeg", "-v", "error", "-ss", f"{t0:.4f}", "-i", path, "-vf", vf,
                                   "-f", "rawvideo", "-pix_fmt", "rgb24", "-"],
                                  stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, bufsize=W * H * 3 * 2)
        self.next_fi = round(t0 * FPS)
        self.last = None

    def read(self):
        b = self.p.stdout.read(W * H * 3)
        if len(b) == W * H * 3:
            self.last = Image.frombytes("RGB", (W, H), b)
        elif self.last is None:
            self.last = Image.new("RGB", (W, H), C["black"])
        self.next_fi += 1
        return self.last

    def close(self):
        try:
            self.p.kill()
        except Exception:
            pass


class Clips:
    """Acesso a frames dos mezaninos por tempo de origem; sequencial = rápido."""

    def __init__(self):
        self.r = {}

    def get(self, name, src_t, blur=0):
        key = (name, blur)
        fi = max(0, round(src_t * FPS))
        r = self.r.get(key)
        if r is None or r.next_fi != fi:
            if r is not None:
                r.close()
            r = Reader(name, fi / FPS, blur)
            self.r[key] = r
        return r.read().copy()


def kit_meta():
    try:
        return json.load(open(os.path.join(KIT, "mezz", "meta.json")))
    except Exception:
        return {"op_light": 2.0}


# ---------------------------------------------------------------- pós

_rng = np.random.default_rng(7)
_GRAIN = None
_VIG = None


def _init_post():
    global _GRAIN, _VIG
    if _GRAIN is None:
        g = []
        for _ in range(6):
            n = _rng.normal(0, 1, (H // 2, W // 2)).astype(np.float32)
            n = np.asarray(Image.fromarray(((n * 40) + 128).clip(0, 255).astype(np.uint8)).resize(
                (W, H), Image.BILINEAR)).astype(np.int16) - 128
            g.append(n)
        _GRAIN = g
        yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
        r = np.sqrt(((xx - W / 2) / (W * 0.62)) ** 2 + ((yy - H / 2) / (H * 0.58)) ** 2)
        _VIG = (1 - 0.55 * np.clip(r - 0.35, 0, 1) ** 1.6).astype(np.float32)[..., None]


def post(img, fi, grain=0.30, vig=True, glitch_amt=0.0, shake=(0, 0)):
    """Vinheta + grão + glitch + tremida. Recebe PIL RGB, devolve uint8 HxWx3."""
    _init_post()
    a = np.asarray(img).astype(np.float32)
    if vig:
        a *= _VIG
    if grain > 0:
        g = _GRAIN[fi % len(_GRAIN)]
        a += (g * grain)[..., None]
    a = np.clip(a, 0, 255).astype(np.uint8)
    if shake != (0, 0):
        a = np.roll(a, (int(shake[1]), int(shake[0])), axis=(0, 1))
    if glitch_amt > 0.01:
        a = glitch(a, glitch_amt, fi)
    return a


def glitch(a, amt, seed):
    rng = np.random.default_rng(seed * 7919 + 13)
    out = a.copy()
    dx = int(6 + 34 * amt)
    out[..., 0] = np.roll(a[..., 0], dx, axis=1)
    out[..., 2] = np.roll(a[..., 2], -dx, axis=1)
    for _ in range(int(3 + 14 * amt)):
        y0 = int(rng.integers(0, H - 20))
        hh = int(rng.integers(6, int(20 + 160 * amt)))
        off = int(rng.integers(-int(40 + 220 * amt), int(40 + 220 * amt)))
        out[y0:y0 + hh] = np.roll(out[y0:y0 + hh], off, axis=1)
    if amt > 0.6:
        y0 = int(rng.integers(0, H - 200))
        out[y0:y0 + int(rng.integers(20, 140))] //= 3
    return out


def shake_at(t, hits, dur=0.22, mag=16):
    """Tremida de câmera decaindo após cada instante em `hits`."""
    sx = sy = 0.0
    for h in hits:
        if 0 <= t - h < dur:
            k = (1 - (t - h) / dur) ** 2 * mag
            sx += (hash01("sx", round(t * FPS)) - 0.5) * 2 * k
            sy += (hash01("sy", round(t * FPS)) - 0.5) * 2 * k
    return (sx, sy)


def flash_at(t, hits, dur=0.12, k=0.35):
    v = 0.0
    for h in hits:
        if 0 <= t - h < dur:
            v = max(v, (1 - (t - h) / dur) * k)
    return v
