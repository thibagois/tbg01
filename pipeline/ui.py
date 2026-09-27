"""Elementos gráficos desenhados: celular, telas de site, pop-ups, balões, HUD, neon."""
import math

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

from common import C, F, rgba, text_img, glow, hash01, clamp

# ---------------------------------------------------------------- celular

PH_W, PH_H, PH_R = 560, 1140, 84      # corpo
SC_PAD = 16                            # borda
SC_W, SC_H = PH_W - 2 * SC_PAD, PH_H - 2 * SC_PAD


def phone_frame():
    """Corpo do celular (RGBA) com a tela transparente."""
    img = Image.new("RGBA", (PH_W + 40, PH_H + 40), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    # sombra
    sh = Image.new("RGBA", img.size, (0, 0, 0, 0))
    ImageDraw.Draw(sh).rounded_rectangle((26, 34, PH_W + 26, PH_H + 34), PH_R, fill=(0, 0, 0, 170))
    img.alpha_composite(sh.filter(ImageFilter.GaussianBlur(16)))
    d.rounded_rectangle((20, 20, PH_W + 20, PH_H + 20), PH_R, fill=(22, 23, 26, 255), outline=(70, 72, 78, 255), width=3)
    d.rounded_rectangle((20 + SC_PAD, 20 + SC_PAD, 20 + PH_W - SC_PAD, 20 + PH_H - SC_PAD), PH_R - SC_PAD,
                        fill=(0, 0, 0, 0))
    # "ilha" da câmera
    cx = 20 + PH_W // 2
    d.rounded_rectangle((cx - 70, 20 + SC_PAD + 16, cx + 70, 20 + SC_PAD + 54), 19, fill=(0, 0, 0, 255))
    return img


def screen_mask():
    m = Image.new("L", (SC_W, SC_H), 0)
    ImageDraw.Draw(m).rounded_rectangle((0, 0, SC_W - 1, SC_H - 1), PH_R - SC_PAD, fill=255)
    return m


def status_bar(d, fg=(235, 235, 235)):
    d.text((44, 50), "21:47", font=F("Barlow-SemiBold.ttf", 26), fill=fg, anchor="ls")
    x = SC_W - 44
    d.rounded_rectangle((x - 44, 30, x, 50), 5, outline=fg, width=2)
    d.rectangle((x - 40, 34, x - 14, 46), fill=fg)


def check(d, x, y, s, col, wdt=5):
    d.line([(x, y + s * 0.5), (x + s * 0.38, y + s * 0.88), (x + s, y + s * 0.1)], fill=col, width=wdt, joint="curve")


def screen_legal():
    """Casa de apostas regulada (fictícia)."""
    img = Image.new("RGB", (SC_W, SC_H), (12, 16, 20))
    d = ImageDraw.Draw(img)
    status_bar(d)
    d.rectangle((0, 80, SC_W, 190), fill=(14, 36, 28))
    d.text((34, 150), "JOGO CLARO", font=F("BarlowCondensed-Black.ttf", 50), fill=(240, 244, 240), anchor="ls")
    d.text((34, 176), ".bet.br", font=F("SpaceMono-Bold.ttf", 20), fill=C["green"], anchor="ls")
    # selo
    d.rounded_rectangle((SC_W - 214, 112, SC_W - 26, 158), 23, fill=C["green"])
    check(d, SC_W - 198, 122, 24, (10, 30, 20), 5)
    d.text((SC_W - 164, 145), "AUTORIZADA", font=F("BarlowCondensed-Bold.ttf", 28), fill=(10, 30, 20), anchor="ls")
    # banner
    d.rounded_rectangle((26, 220, SC_W - 26, 400), 22, fill=(20, 56, 42))
    d.text((52, 290), "Operadora autorizada", font=F("Barlow-Bold.ttf", 34), fill=(236, 246, 240), anchor="ls")
    d.text((52, 334), "Regras, fiscalização e", font=F("Barlow-Medium.ttf", 26), fill=(170, 210, 190), anchor="ls")
    d.text((52, 366), "jogo responsável.", font=F("Barlow-Medium.ttf", 26), fill=(170, 210, 190), anchor="ls")
    d.rounded_rectangle((SC_W - 118, 238, SC_W - 44, 282), 12, outline=(236, 246, 240), width=3)
    d.text((SC_W - 81, 270), "18+", font=F("BarlowCondensed-Bold.ttf", 30), fill=(236, 246, 240), anchor="ms")
    games = [("Leões", "Tubarões", "1.85", "3.20", "4.10"), ("Águias", "Falcões", "2.40", "3.05", "2.90"),
             ("Tigres", "Lobos", "1.60", "3.70", "5.25")]
    y = 440
    for a, b, o1, o2, o3 in games:
        d.rounded_rectangle((26, y, SC_W - 26, y + 170), 20, fill=(20, 25, 31))
        d.text((50, y + 50), f"{a}  x  {b}", font=F("Barlow-SemiBold.ttf", 30), fill=(230, 232, 236), anchor="ls")
        d.text((50, y + 80), "Campeonato • hoje 21:30", font=F("Barlow-Medium.ttf", 21), fill=(120, 128, 138), anchor="ls")
        bw = (SC_W - 52 - 48 - 24) / 3
        for k, (lab, o) in enumerate(zip(("1", "X", "2"), (o1, o2, o3))):
            x0 = 50 + k * (bw + 12)
            d.rounded_rectangle((x0, y + 98, x0 + bw, y + 150), 12, fill=(32, 40, 48))
            d.text((x0 + 16, y + 133), lab, font=F("Barlow-Medium.ttf", 22), fill=(130, 138, 148), anchor="ls")
            d.text((x0 + bw - 16, y + 134), o, font=F("SpaceMono-Bold.ttf", 26), fill=C["green"], anchor="rs")
        y += 190
    d.text((SC_W // 2, SC_H - 44), "Jogue com responsabilidade  •  Lei 14.790/2023", font=F("Barlow-Medium.ttf", 20),
           fill=(110, 118, 126), anchor="ms")
    return img


def screen_down():
    """Site fora do ar."""
    img = Image.new("RGB", (SC_W, SC_H), (14, 14, 16))
    d = ImageDraw.Draw(img)
    status_bar(d, (200, 200, 200))
    cx, cy, r = SC_W // 2, 440, 92
    d.ellipse((cx - r, cy - r, cx + r, cy + r), outline=C["red"], width=14)
    k = r * 0.68
    d.line([(cx - k, cy - k), (cx + k, cy + k)], fill=C["red"], width=14)
    d.text((cx, 650), "SITE FORA DO AR", font=F("BarlowCondensed-Black.ttf", 66), fill=(238, 238, 238), anchor="ms")
    d.text((cx, 710), "Erro 451", font=F("SpaceMono-Bold.ttf", 28), fill=(150, 150, 156), anchor="ms")
    d.text((cx, 752), "Indisponível por razões legais", font=F("Barlow-Medium.ttf", 26), fill=(120, 120, 126), anchor="ms")
    return img


def screen_shady(t):
    """Cassino clandestino (fictício), piscando."""
    img = Image.new("RGB", (SC_W, SC_H), (8, 4, 6))
    d = ImageDraw.Draw(img)
    status_bar(d)
    d.rectangle((0, 80, SC_W, 170), fill=(40, 6, 10))
    d.text((34, 142), "CASSINO 24H", font=F("BarlowCondensed-Black.ttf", 50), fill=C["amber"], anchor="ls")
    d.rounded_rectangle((SC_W - 128, 104, SC_W - 30, 148), 10, fill=C["red"])
    d.text((SC_W - 79, 138), "VIP", font=F("BarlowCondensed-Black.ttf", 32), fill=(255, 240, 200), anchor="ms")
    blink = 1.0 if int(t * 6) % 2 == 0 else 0.55
    amber = tuple(int(c * blink) for c in C["amber"])
    d.text((SC_W // 2, 330), "BÔNUS", font=F("Anton.ttf", 110), fill=(250, 250, 250), anchor="ms")
    d.text((SC_W // 2, 480), "500%", font=F("Anton.ttf", 150), fill=amber, anchor="ms")
    d.text((SC_W // 2, 540), "NO PRIMEIRO DEPÓSITO", font=F("BarlowCondensed-Bold.ttf", 34), fill=(230, 200, 200), anchor="ms")
    # rolos de caça-níquel
    bw = 138
    for k in range(3):
        x0 = SC_W // 2 - 1.5 * bw - 12 + k * (bw + 12)
        d.rounded_rectangle((x0, 590, x0 + bw, 760), 16, fill=(250, 244, 230))
        sym = "7" if (int(t * 14) + k * 3) % 5 else "$"
        d.text((x0 + bw / 2, 725), sym, font=F("Anton.ttf", 130), fill=C["red"], anchor="ms")
    pulse = 0.5 + 0.5 * math.sin(t * 12)
    d.rounded_rectangle((40, 810, SC_W - 40, 900), 45, fill=(int(200 + 50 * pulse), 20, 28))
    d.text((SC_W // 2, 870), "DEPOSITAR VIA PIX", font=F("BarlowCondensed-Black.ttf", 46), fill=(255, 255, 255), anchor="ms")
    d.text((SC_W // 2, 950), "sem CPF  •  sem verificação  •  saque na hora", font=F("Barlow-Medium.ttf", 22),
           fill=(200, 150, 150), anchor="ms")
    d.text((SC_W // 2, SC_H - 60), "cassino-vip24h.top", font=F("SpaceMono-Regular.ttf", 22), fill=(130, 90, 90), anchor="ms")
    return img


# ---------------------------------------------------------------- pop-ups

POPUPS = [
    # (url, título, subtítulo, estilo, x, y, rot)
    ("b3t-pix777.xyz", "BÔNUS DE 500%", "no primeiro depósito", "win", 40, 250, -4),
    ("cassino-vip24h.top", "SAQUE NA HORA VIA PIX", "sem limite de valor", "note", 470, 420, 3),
    ("grupo-sinais-vip.xyz", "GRUPO VIP DE SINAIS", "vagas limitadas — entre agora", "win", 10, 700, 5),
    ("apostamax-br.vip", "SEM CPF. SEM VERIFICAÇÃO.", "cadastro em 10 segundos", "note", 420, 860, -5),
    ("roleta-premiada.click", "GIRE E GANHE R$ 1.000", "oferta expira em 04:59", "win", 60, 1080, -2),
    ("bet-ilimitada.online", "DEPÓSITO MÍNIMO R$ 1", "aceitamos cartão de terceiros", "note", 450, 170, 6),
    ("app-aposta-pro.apk", "BAIXE O APP", "fora da loja oficial", "win", 480, 1230, 4),
    ("pix-cassino.club", "RODADAS GRÁTIS", "não precisa de documento", "note", 0, 470, -6),
    ("sorte-rapida.win", "DOBRE SEU PIX", "resultado garantido", "win", 380, 640, -3),
    ("vip-apostas.site", "SAQUE LIBERADO", "clique para receber", "note", 90, 1330, 3),
]


def warn_icon(d, x, y, s, col):
    d.polygon([(x + s / 2, y), (x + s, y + s * 0.9), (x, y + s * 0.9)], fill=col)
    d.text((x + s / 2, y + s * 0.82), "!", font=F("BarlowCondensed-Black.ttf", int(s * 0.8)), fill=(20, 10, 10), anchor="ms")


def popup_img(url, title, sub, style):
    wdt = 560
    if style == "win":
        hgt = 250
        img = Image.new("RGBA", (wdt + 30, hgt + 30), (0, 0, 0, 0))
        sh = Image.new("RGBA", img.size, (0, 0, 0, 0))
        ImageDraw.Draw(sh).rounded_rectangle((12, 18, wdt + 12, hgt + 18), 18, fill=(0, 0, 0, 200))
        img.alpha_composite(sh.filter(ImageFilter.GaussianBlur(10)))
        d = ImageDraw.Draw(img)
        d.rounded_rectangle((0, 0, wdt, hgt), 18, fill=(20, 21, 25, 255), outline=(90, 30, 34, 255), width=2)
        d.rounded_rectangle((0, 0, wdt, 64), 18, fill=(34, 36, 42, 255))
        d.rectangle((0, 40, wdt, 64), fill=(34, 36, 42, 255))
        for k, col in enumerate(((236, 90, 80), (240, 190, 60), (100, 200, 90))):
            d.ellipse((20 + k * 26, 24, 36 + k * 26, 40), fill=col)
        d.rounded_rectangle((104, 14, wdt - 18, 50), 18, fill=(18, 19, 22, 255))
        warn_icon(d, 116, 20, 24, C["red"])
        d.text((150, 41), url, font=F("SpaceMono-Regular.ttf", 22), fill=(230, 120, 120), anchor="ls")
        tf = F("BarlowCondensed-Black.ttf", 58)
        while tf.getlength(title) > wdt - 60:
            tf = F("BarlowCondensed-Black.ttf", tf.size - 2)
        d.text((30, 142), title, font=tf, fill=C["amber"], anchor="ls")
        d.text((30, 186), sub, font=F("Barlow-Medium.ttf", 26), fill=(190, 190, 196), anchor="ls")
        d.rounded_rectangle((30, 204, 210, 238), 17, fill=C["red"])
        d.text((120, 229), "CLIQUE AQUI", font=F("BarlowCondensed-Bold.ttf", 24), fill=(255, 255, 255), anchor="ms")
    else:
        hgt = 150
        img = Image.new("RGBA", (wdt + 30, hgt + 30), (0, 0, 0, 0))
        sh = Image.new("RGBA", img.size, (0, 0, 0, 0))
        ImageDraw.Draw(sh).rounded_rectangle((12, 18, wdt + 12, hgt + 18), 30, fill=(0, 0, 0, 190))
        img.alpha_composite(sh.filter(ImageFilter.GaussianBlur(10)))
        d = ImageDraw.Draw(img)
        d.rounded_rectangle((0, 0, wdt, hgt), 30, fill=(38, 38, 44, 245))
        d.rounded_rectangle((22, 26, 90, 94), 16, fill=C["red"])
        d.text((56, 82), "$", font=F("Anton.ttf", 56), fill=(255, 230, 120), anchor="ms")
        d.text((110, 52), url, font=F("Barlow-SemiBold.ttf", 24), fill=(170, 170, 178), anchor="ls")
        d.text((wdt - 24, 52), "agora", font=F("Barlow-Medium.ttf", 22), fill=(130, 130, 138), anchor="rs")
        tf = F("BarlowCondensed-Black.ttf", 44)
        while tf.getlength(title) > wdt - 140:
            tf = F("BarlowCondensed-Black.ttf", tf.size - 2)
        d.text((110, 98), title, font=tf, fill=(250, 250, 250), anchor="ls")
        d.text((110, 132), sub, font=F("Barlow-Medium.ttf", 24), fill=(200, 200, 206), anchor="ls")
    return img


# ---------------------------------------------------------------- balões de golpe

SCAM_MSGS = [
    "Parabéns! Você ganhou um BÔNUS de R$ 500.",
    "Deposite R$ 50 via PIX para liberar o saque.",
    "Seu saque está BLOQUEADO. Pague a taxa de liberação.",
]


def bubble_img(txt, maxw=700):
    f = F("Barlow-Medium.ttf", 38)
    words, lines, cur = txt.split(), [], ""
    for wd in words:
        tst = (cur + " " + wd).strip()
        if f.getlength(tst) > maxw - 60:
            lines.append(cur)
            cur = wd
        else:
            cur = tst
    lines.append(cur)
    bw = int(max(f.getlength(li) for li in lines) + 60)
    bh = 34 + 50 * len(lines) + 36
    img = Image.new("RGBA", (bw + 30, bh + 30), (0, 0, 0, 0))
    sh = Image.new("RGBA", img.size, (0, 0, 0, 0))
    ImageDraw.Draw(sh).rounded_rectangle((10, 16, bw + 10, bh + 16), 28, fill=(0, 0, 0, 160))
    img.alpha_composite(sh.filter(ImageFilter.GaussianBlur(9)))
    d = ImageDraw.Draw(img)
    d.rounded_rectangle((0, 0, bw, bh), 28, fill=(34, 36, 40, 240))
    d.polygon([(0, bh - 40), (-2, bh + 8), (34, bh - 6)], fill=(34, 36, 40, 240))
    for k, li in enumerate(lines):
        d.text((30, 30 + 50 * k + 36), li, font=f, fill=(240, 240, 240), anchor="ls")
    d.text((bw - 20, bh - 14), "21:48", font=F("Barlow-Medium.ttf", 20), fill=(140, 140, 148), anchor="rs")
    return img


# ---------------------------------------------------------------- HUD / ledger / rede

def hud(layer, t, label="CAM 04", tc_base=3 * 3600 + 17 * 60 + 42):
    d = ImageDraw.Draw(layer)
    m, L, col = 70, 70, (235, 235, 235, 190)
    for (x, y, sx, sy) in ((m, 250, 1, 1), (1080 - m, 250, -1, 1), (m, 1560, 1, -1), (1080 - m, 1560, -1, -1)):
        d.line([(x, y), (x + sx * L, y)], fill=col, width=4)
        d.line([(x, y), (x, y + sy * L)], fill=col, width=4)
    if int(t * 2) % 2 == 0:
        d.ellipse((m + 26, 290, m + 50, 314), fill=(235, 30, 36, 235))
    d.text((m + 62, 312), "REC", font=F("SpaceMono-Bold.ttf", 30), fill=col, anchor="ls")
    d.text((1080 - m - 26, 312), label, font=F("SpaceMono-Bold.ttf", 30), fill=col, anchor="rs")
    s = tc_base + t
    tc = f"{int(s // 3600):02d}:{int(s % 3600 // 60):02d}:{int(s % 60):02d}:{int((s % 1) * 30):02d}"
    d.text((1080 - m - 26, 356), tc, font=F("SpaceMono-Regular.ttf", 26), fill=(235, 235, 235, 150), anchor="rs")


def ledger(layer, t, t0, alpha=1.0):
    """Lista de PIX rolando (evoca pulverização de depósitos)."""
    d = ImageDraw.Draw(layer)
    f = F("SpaceMono-Regular.ttf", 25)
    fb = F("SpaceMono-Bold.ttf", 25)
    row = 46
    scroll = (t - t0) * 260
    for k in range(-1, 26):
        i = int(scroll // row) + k
        y = 300 + k * row - (scroll % row)
        if y < 280 or y > 1080:
            continue
        fade = clamp(min((y - 280) / 120, (1080 - y) / 160))
        a = int(200 * fade * alpha)
        val = 4000 + int(hash01("v", i) * 990)
        cpf = f"***.{int(hash01('c', i) * 900) + 100}.***-**"
        d.text((70, y), "PIX", font=fb, fill=(40, 210, 140, a), anchor="ls")
        d.text((140, y), cpf, font=f, fill=(200, 205, 210, a), anchor="ls")
        d.text((1010, y), f"R$ {val // 1000}.{val % 1000:03d},00", font=fb, fill=(235, 235, 235, a), anchor="rs")


NET_NODES = [(180, 420), (520, 330), (880, 470), (300, 760), (760, 820), (130, 1080), (560, 1040), (930, 1160)]
NET_EDGES = [(0, 1), (1, 2), (0, 3), (1, 4), (2, 4), (3, 4), (3, 5), (4, 6), (5, 6), (6, 7), (4, 7), (1, 3)]


def network(layer, p):
    """Rede de nós vermelhos se conectando (p: 0-1)."""
    d = ImageDraw.Draw(layer)
    ne = len(NET_EDGES)
    for k, (a, b) in enumerate(NET_EDGES):
        q = clamp(p * ne * 0.55 - k * 0.45)
        if q <= 0:
            continue
        (x0, y0), (x1, y1) = NET_NODES[a], NET_NODES[b]
        d.line([(x0, y0), (x0 + (x1 - x0) * q, y0 + (y1 - y0) * q)], fill=(235, 30, 36, 200), width=4)
    for k, (x, y) in enumerate(NET_NODES):
        q = clamp(p * 3 - k * 0.25)
        if q <= 0:
            continue
        r = 10 + 8 * q
        d.ellipse((x - r, y - r, x + r, y + r), outline=(235, 30, 36, 230), width=4)
        d.ellipse((x - 6, y - 6, x + 6, y + 6), fill=(255, 80, 80, 255))


# ---------------------------------------------------------------- neon

class Neon:
    """Placa de neon pré-renderizada: tubo apagado + luz acesa (float32 aditivo)."""

    def __init__(self, word, cy, color, core, max_w=900, size=300):
        f = F("TiltNeon.ttf", size)
        while f.getlength(word) > max_w:
            f = F("TiltNeon.ttf", f.size - 4)
        tube, base = text_img(word, f, (255, 255, 255, 255), tracking=6, pad=120)
        self.x = int(540 - tube.width / 2)
        self.y = int(cy - tube.height / 2)
        full = Image.new("RGBA", (1080, 1920), (0, 0, 0, 0))
        full.alpha_composite(tube, (self.x, self.y))
        a = np.asarray(full.getchannel("A")).astype(np.float32) / 255.0
        self.mask = a
        col = np.array(color, np.float32)
        core = np.array(core, np.float32)

        def blur(r):
            im = Image.fromarray((a * 255).astype(np.uint8), "L")
            sm = im.resize((270, 480), Image.BILINEAR).filter(ImageFilter.GaussianBlur(max(0.6, r / 4)))
            return np.asarray(sm.resize((1080, 1920), Image.BILINEAR)).astype(np.float32) / 255.0

        light = a[..., None] * core
        light += blur(10)[..., None] * col * 1.6
        light += blur(34)[..., None] * col * 1.1
        light += blur(110)[..., None] * col * 0.9
        light += blur(320)[..., None] * col * 0.55
        self.light = light
        sh = np.asarray(full.filter(ImageFilter.GaussianBlur(3)).getchannel("A")).astype(np.float32) / 255.0
        self.off = sh[..., None] * np.array([34, 34, 38], np.float32)

    def add(self, base, k):
        """base: float32 HxWx3; k: intensidade 0-1.3"""
        base += self.off * (1 - clamp(k))
        if k > 0.002:
            base += self.light * k
        return base


def sparks(layer, t, t0, x0, x1, y0, n=26):
    d = ImageDraw.Draw(layer)
    dt = t - t0
    if dt < 0 or dt > 1.2:
        return
    for i in range(n):
        sx = x0 + (x1 - x0) * hash01("sx", i)
        vx = (hash01("vx", i) - 0.5) * 380
        vy = -120 - 260 * hash01("vy", i)
        life = 0.4 + 0.8 * hash01("l", i)
        if dt > life:
            continue
        x = sx + vx * dt
        y = y0 + vy * dt + 0.5 * 2400 * dt * dt
        a = int(255 * (1 - dt / life))
        r = 3 + 3 * hash01("r", i)
        d.ellipse((x - r, y - r, x + r, y + r), fill=(255, 240, 220, a))
        d.line([(x, y), (x - vx * 0.02, y - (vy + 2400 * dt) * 0.02)], fill=(255, 200, 150, a // 2), width=2)
