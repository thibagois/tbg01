"""As cinco cenas do reel. Cada cena é função pura do tempo global t."""
import math

import numpy as np
from PIL import Image, ImageDraw

import ui
from common import (C, F, fit_font, prog, clamp, lerp, e_out3, e_inout3, e_outexpo, e_outback, hash01, rgba,
                    paste_text, glow, vgrad, zoom, darken, kit_meta, shake_at, flash_at)
from timeline import W, H, FPS, w, OP_LIGHT_TARGET

BLACK = Image.new("RGB", (W, H), C["black"])
WHITE = Image.new("RGB", (W, H), (255, 255, 255))


def over(img, layer):
    base = img.convert("RGBA")
    base.alpha_composite(layer)
    return base.convert("RGB")


def red_glow_text(lay, draw_fn, radius=28, strength=0.9):
    """Desenha texto (via draw_fn(layer)) com halo vermelho por baixo."""
    tl = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    draw_fn(tl)
    lay.alpha_composite(glow(tl, radius, strength))
    lay.alpha_composite(tl)


def words_line(lay, words, times, font, fill, y, t, rise=26, cx=W / 2):
    """Linha centralizada com palavras entrando uma a uma nos tempos da locução."""
    sp = font.getlength(" ")
    ws = [font.getlength(x) for x in words]
    x = cx - (sum(ws) + sp * (len(ws) - 1)) / 2
    for wd, tw, ww in zip(words, times, ws):
        p = prog(t, tw - 0.05, tw + 0.2)
        if p > 0:
            q = e_out3(p)
            paste_text(lay, wd, font, fill, x, y + rise * (1 - q), anchor="ls", alpha=q, blur=5 * (1 - p))
        x += ww + sp


class Scene:
    def __init__(self, clips):
        self.clips = clips

    def fx(self, t):
        return {}


# ------------------------------------------------------------------ S1
class S1(Scene):
    """Tela preta, celular acende. SEM BET LEGAL, / O QUE SOBRA?"""

    def __init__(self, clips):
        super().__init__(clips)
        self.src0 = max(0.0, kit_meta()["op_light"] - OP_LIGHT_TARGET)
        self.f = F("Anton.ttf", 150)
        self.grad = vgrad(W, H, [(0, (0, 0, 0, 170)), (0.42, (0, 0, 0, 60)), (0.6, (0, 0, 0, 0)), (1, (0, 0, 0, 0))])

    def render(self, t, fi):
        img = self.clips.get("op", self.src0 + t)
        img = zoom(img, 1.0 + 0.07 * e_inout3(prog(t, 0, 3.3)), 0.5, 0.66)
        k = e_out3(prog(t, 0.05, 0.55))
        if k < 1:
            img = Image.blend(BLACK, img, k)
        lay = self.grad.copy()
        words_line(lay, ["SEM", "BET", "LEGAL,"], [w("l1", 0), w("l1", 1), w("l1", 2)], self.f,
                   rgba(C["white"]), 560, t)
        t2 = w("l1", 3)
        if t >= t2 - 0.02:
            dt = t - t2
            on = 1.0 if dt > 0.22 else (1.0 if hash01("s1", int(dt * FPS)) > 0.4 else 0.2)
            red_glow_text(lay, lambda L: paste_text(L, "O QUE SOBRA?", self.f, rgba(C["red"]), W / 2, 730,
                                                    anchor="ms", alpha=on), 26, 0.8 * on)
        return over(img, lay)

    def fx(self, t):
        return dict(glitch=0.35 if 0 <= t - w("l1", 3) < 0.07 else 0.0)


# ------------------------------------------------------------------ S2
class S2(Scene):
    """Bet legal sai do ar; sites clandestinos pipocam. O ILEGAL CONTINUA."""
    T0 = 3.3
    PX, PY = 240, 250  # canto do quadro do celular

    def __init__(self, clips):
        super().__init__(clips)
        self.phone = ui.phone_frame()
        self.mask = ui.screen_mask()
        self.legal = ui.screen_legal()
        self.down = ui.screen_down()
        self.t_sair = w("l2", 3)
        self.t_mas = w("l2", 4)
        self.t_slam = w("l2", 14)
        n = len(ui.POPUPS)
        span = (self.t_slam - 0.25) - (self.t_mas + 0.1)
        self.pop_t = [self.t_mas + 0.1 + i * span / (n - 1) for i in range(n)]
        self.pops = []
        for (u, ti, su, st, x, y, r) in ui.POPUPS:
            im = ui.popup_img(u, ti, su, st).rotate(r, resample=Image.BICUBIC, expand=True)
            self.pops.append((im, x, y))
        f = F("Anton.ttf", 210)
        blk = Image.new("RGBA", (W, 560), (0, 0, 0, 0))
        wo, wi = f.getlength("O "), f.getlength("ILEGAL")
        x0 = W / 2 - (wo + wi) / 2
        paste_text(blk, "O", f, rgba(C["white"]), x0, 250, anchor="ls")
        red = Image.new("RGBA", (W, 560), (0, 0, 0, 0))
        paste_text(red, "ILEGAL", f, rgba(C["red"]), x0 + wo, 250, anchor="ls")
        blk.alpha_composite(glow(red, 30, 0.9))
        blk.alpha_composite(red)
        paste_text(blk, "CONTINUA.", f, rgba(C["white"]), W / 2, 490, anchor="ms")
        self.block = blk

    def screen(self, t):
        if t < self.t_sair:
            scr = self.legal.copy()
            amt = prog(t, self.t_sair - 0.3, self.t_sair)
        elif t < self.t_mas:
            scr = self.down.copy()
            amt = max(1 - prog(t, self.t_sair, self.t_sair + 0.12), prog(t, self.t_mas - 0.18, self.t_mas))
        else:
            scr = ui.screen_shady(t)
            amt = 1 - prog(t, self.t_mas, self.t_mas + 0.15)
            amt = max(amt, 0.5 if hash01("sg", int(t * FPS)) > 0.9 else 0)
        if amt > 0.02:
            a = np.asarray(scr).copy()
            rng = np.random.default_rng(int(t * FPS) * 31)
            for _ in range(int(2 + 10 * amt)):
                y0 = int(rng.integers(0, ui.SC_H - 10))
                hh = int(rng.integers(4, int(10 + 80 * amt)))
                a[y0:y0 + hh] = np.roll(a[y0:y0 + hh], int(rng.integers(-int(20 + 140 * amt), int(20 + 140 * amt))), 1)
            dx = int(4 + 18 * amt)
            a[..., 0] = np.roll(a[..., 0], dx, 1)
            scr = Image.fromarray(a)
        return scr

    def render(self, t, fi):
        lt = t - self.T0
        bg = self.clips.get("s2bg", lt, blur=14)
        bg = darken(zoom(bg, 1.05 + 0.06 * prog(t, self.T0, 8.9)), 0.42)
        lay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        # celular
        ph = self.phone.copy()
        scr = self.screen(t).convert("RGBA")
        ph.paste(scr, (20 + ui.SC_PAD, 20 + ui.SC_PAD), self.mask)
        ph.alpha_composite(self.phone)  # borda/ilha por cima
        p_in = e_out3(prog(t, self.T0, self.T0 + 0.45))
        py = self.PY + 140 * (1 - p_in) + 8 * math.sin(t * 1.7)
        if p_in < 1:
            a = ph.getchannel("A").point(lambda v: int(v * p_in))
            ph.putalpha(a)
        lay.alpha_composite(ph, (self.PX, int(py)))
        # pop-ups
        for (im, x, y), pt in zip(self.pops, self.pop_t):
            if t < pt:
                continue
            p = prog(t, pt, pt + 0.2)
            s = 0.55 + 0.45 * e_outback(p)
            jx = (hash01("jx", fi, x) - 0.5) * 60 if p < 0.35 or hash01("pg", fi, y) > 0.96 else 0
            if s != 1:
                pim = im.resize((max(1, int(im.width * s)), max(1, int(im.height * s))), Image.BILINEAR)
            else:
                pim = im
            if p < 1:
                pim = pim.copy()
                pim.putalpha(pim.getchannel("A").point(lambda v: int(v * min(1, p * 3))))
            cx, cy = x + im.width / 2, y + im.height / 2
            lay.alpha_composite(pim, (int(cx - pim.width / 2 + jx), int(cy - pim.height / 2)))
        img = over(bg, lay)
        # slam
        if t >= self.t_slam - 0.12:
            dim = e_out3(prog(t, self.t_slam - 0.12, self.t_slam + 0.05))
            img = Image.blend(img, BLACK, 0.66 * dim)
            p = prog(t, self.t_slam, self.t_slam + 0.2)
            if t >= self.t_slam:
                s = 1 + 0.4 * (1 - e_outexpo(p))
                b = self.block
                if s != 1:
                    b = b.resize((int(W * s), int(560 * s)), Image.BILINEAR)
                L = Image.new("RGBA", (W, H), (0, 0, 0, 0))
                L.alpha_composite(b, (int(W / 2 - b.width / 2), int(1000 - b.height / 2)))
                if p < 1:
                    L.putalpha(L.getchannel("A").point(lambda v: int(v * min(1, p * 2.5))))
                img = over(img, L)
            fl = flash_at(t, [self.t_slam], 0.1, 0.3)
            if fl > 0:
                img = Image.blend(img, WHITE, fl)
        return img

    def fx(self, t):
        g = 0.0
        if 0 <= t - self.t_sair < 0.1:
            g = 0.3
        return dict(shake=shake_at(t, [self.t_slam], 0.25, 18), glitch=g)


# ------------------------------------------------------------------ S3
class S3(Scene):
    """Mercado clandestino: GOLPES. / LAVAGEM DE DINHEIRO. / CRIME ORGANIZADO."""
    T0 = 8.9

    def __init__(self, clips):
        super().__init__(clips)
        self.c1 = w("l3", 6) - 0.05       # -> golpes (espaço)
        self.c2 = w("l3", 9) - 0.03       # -> lavagem
        self.c3 = w("l3", 13) - 0.08      # -> atuação do crime organizado
        self.c4 = w("l3", 16) + 0.12      # -> cctv
        self.items = [("GOLPES.", w("l3", 8), C["white"]), ("LAVAGEM DE DINHEIRO.", w("l3", 9), C["white"]),
                      ("CRIME ORGANIZADO.", w("l3", 15), C["red"])]
        self.f = fit_font("Anton.ttf", "LAVAGEM DE DINHEIRO.", 930, 140)
        self.grad = vgrad(W, H, [(0, (0, 0, 0, 90)), (0.2, (0, 0, 0, 0)), (0.52, (0, 0, 0, 0)),
                                 (0.75, (0, 0, 0, 200)), (1, (0, 0, 0, 235))])
        self.bubbles = [ui.bubble_img(m) for m in ui.SCAM_MSGS]
        self.tag = F("SpaceMono-Bold.ttf", 40)

    def cuts(self):
        return [self.c1, self.c2, self.c3, self.c4]

    def render(self, t, fi):
        if t < self.c1:
            img = self.clips.get("crime", t - self.T0 + 0.2)
            img = zoom(img, 1.02 + 0.07 * prog(t, self.T0, self.c1), 0.5, 0.45)
        elif t < self.c2:
            img = self.clips.get("scam", t - self.c1)
            img = zoom(img, 1.04 + 0.05 * prog(t, self.c1, self.c2), 0.5, 0.5)
        elif t < self.c3:
            img = self.clips.get("money", t - self.c2 + 0.6)
            img = zoom(img, 1.02 + 0.05 * prog(t, self.c2, self.c3), 0.5, 0.5)
        elif t < self.c4:
            img = self.clips.get("mask", t - self.c3)
            img = zoom(img, 1.0 + 0.1 * prog(t, self.c3, self.c4), 0.5, 0.42)
        else:
            img = self.clips.get("cctv", t - self.c4)
        lay = self.grad.copy()
        if t < self.c1:
            ui.hud(lay, t)
            p = prog(t, w("l3", 3) - 0.05, w("l3", 3) + 0.2)
            if p > 0:
                d = ImageDraw.Draw(lay)
                txt = "MERCADO CLANDESTINO"
                tw = self.tag.getlength(txt) + 6 * len(txt)
                x0, y0 = 70, 1480
                d.rectangle((x0, y0 - 44, x0 + (tw + 36) * e_out3(p), y0 + 14), fill=(232, 22, 30, 235))
                if p > 0.5:
                    paste_text(lay, txt, self.tag, (255, 255, 255, 255), x0 + 18, y0, anchor="ls", tracking=6)
        elif t < self.c2:
            for k, (b, bt) in enumerate(zip(self.bubbles, [self.c1 + 0.05, self.c1 + 0.38, self.c1 + 0.72])):
                p = prog(t, bt, bt + 0.2)
                if p <= 0:
                    continue
                bb = b.copy()
                if p < 1:
                    bb.putalpha(bb.getchannel("A").point(lambda v: int(v * p)))
                lay.alpha_composite(bb, (int(60 - 80 * (1 - e_out3(p))), 430 + k * 185))
        elif t < self.c3:
            ledg = Image.new("RGBA", (W, H), (0, 0, 0, 0))
            ImageDraw.Draw(ledg).rectangle((40, 250, 1040, 1090), fill=(0, 0, 0, 110))
            ui.ledger(ledg, t, self.c2, alpha=prog(t, self.c2, self.c2 + 0.2))
            lay.alpha_composite(ledg)
        elif t < self.c4:
            ui.network(lay, prog(t, self.c3 + 0.05, self.c4 - 0.1))
        else:
            ui.hud(lay, t, "CAM 11", tc_base=2 * 3600 + 32 * 60 + 38)
        # lista empilhada
        for i, (txt, ti, col) in enumerate(self.items):
            if t < ti - 0.02:
                continue
            p = prog(t, ti, ti + 0.16)
            s = 1 + 0.3 * (1 - e_outexpo(p))
            nxt = self.items[i + 1][1] if i + 1 < len(self.items) else 99
            dim = 1 - 0.55 * prog(t, nxt, nxt + 0.2)
            c = tuple(int(v * dim + 40 * (1 - dim)) for v in col)
            y = 1250 + i * 145
            if col == C["red"]:
                red_glow_text(lay, lambda L: paste_text(L, txt, self.f, rgba(c), 75, y, anchor="ls",
                                                        alpha=min(1, p * 3), scale=s), 24, 0.8)
            else:
                paste_text(lay, txt, self.f, rgba(c), 75, y, anchor="ls", alpha=min(1, p * 3), scale=s)
        img = over(img, lay)
        fl = flash_at(t, [it[1] for it in self.items], 0.09, 0.22)
        if fl > 0:
            img = Image.blend(img, WHITE, fl)
        return img

    def fx(self, t):
        g = 0.0
        for c in self.cuts():
            if -0.034 <= t - c < 0.05:
                g = 0.45
        return dict(shake=shake_at(t, [it[1] for it in self.items], 0.22, 14), glitch=g)


# ------------------------------------------------------------------ S4
class S4(Scene):
    """Neon: LEGAL apaga; ILEGAL continua aceso."""
    T0, T1 = 15.6, 21.6

    def __init__(self, clips):
        super().__init__(clips)
        self.L = ui.Neon("LEGAL", 690, color=(70, 160, 255), core=(225, 240, 255), max_w=700, size=290)
        self.I = ui.Neon("ILEGAL", 1150, color=(255, 26, 38), core=(255, 222, 215), max_w=860, size=290)
        yy = np.linspace(0, 1, H, dtype=np.float32)[:, None, None]
        self.bg = np.broadcast_to((np.array([9, 10, 13], np.float32) * (1 - 0.5 * yy)), (H, W, 3)).copy()
        self.t_on_l, self.t_on_i = 15.78, 16.08
        self.t_bad = w("l4", 6)
        self.t_die = w("l4", 12)
        ys = np.nonzero(self.L.mask.max(1) > 0.5)[0]
        xs = np.nonzero(self.L.mask.max(0) > 0.5)[0]
        self.lbox = (xs.min(), xs.max(), ys.max())

    @staticmethod
    def ignite(t, t0, key):
        dt = t - t0
        if dt < 0:
            return 0.0
        if dt < 0.28:
            return 1.0 if hash01(key, int(dt * FPS)) > 0.45 else 0.08
        return 1.0

    def k_legal(self, t, fi):
        k = self.ignite(t, self.t_on_l, "ign_l")
        if k == 0:
            return 0.0
        k *= 0.94 + 0.06 * hash01("hl", fi)
        if self.t_bad <= t < self.t_die:
            p = prog(t, self.t_bad, self.t_die)
            if hash01("bad", fi) < 0.12 + 0.45 * p:
                k *= 0.1 + 0.3 * hash01("bd", fi)
        if t >= self.t_die:
            dt = t - self.t_die
            k = 1.35 if dt < 0.07 else 0.4 * math.exp(-(dt - 0.07) / 0.1)
        return k

    def k_ilegal(self, t, fi):
        k = self.ignite(t, self.t_on_i, "ign_i")
        if k == 0:
            return 0.0
        k *= 0.96 + 0.04 * hash01("hi", fi)
        if t >= self.t_die:
            k *= 1 + 0.12 * prog(t, self.t_die, self.T1) + 0.03 * math.sin(t * 5)
        return k

    def render(self, t, fi):
        kl, ki = self.k_legal(t, fi), self.k_ilegal(t, fi)
        base = self.bg.copy()
        sm = np.asarray(self.clips.get("smoke", t - self.T0)).astype(np.float32)
        tint = (np.array([70, 160, 255], np.float32) * kl + np.array([255, 40, 50], np.float32) * ki) / 255.0
        base += sm * tint * 0.3
        base = self.L.add(base, kl)
        base = self.I.add(base, ki)
        img = Image.fromarray(np.clip(base, 0, 255).astype(np.uint8), "RGB")
        if t >= self.t_die:
            lay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
            x0, x1, yb = self.lbox
            ui.sparks(lay, t, self.t_die, x0, x1, yb - 30)
            img = over(img, lay)
        s = 1.0 + 0.03 * prog(t, self.T0, self.t_die) + 0.14 * e_inout3(prog(t, self.t_die + 0.15, self.T1))
        cy = lerp(0.5, 1150 / H, prog(t, self.t_die, self.t_die + 1.2))
        return zoom(img, s, 0.5, cy)

    def fx(self, t):
        return dict(grain=0.34, shake=shake_at(t, [self.t_die], 0.2, 10))


# ------------------------------------------------------------------ S5
class S5(Scene):
    """Tela preta. Você tira a regra... SEM BET LEGAL, / SÓ RESTA O CRIME."""
    T0 = 21.6

    def __init__(self, clips):
        super().__init__(clips)
        self.sub = F("Barlow-SemiBold.ttf", 62)
        self.big = fit_font("Anton.ttf", "SÓ RESTA O CRIME.", 940, 150)
        self.I = ui.Neon("ILEGAL", 930, color=(255, 26, 38), core=(255, 222, 215), max_w=620, size=220)
        self.subs = [("Você tira a regra.", w("l5", 0), w("l5", 3, True) + 0.4, 960),
                     ("Tira a fiscalização.", w("l5", 4), w("l5", 6, True) + 0.4, 960),
                     ("E o ilegal continua.", w("l5", 7), w("l5", 10, True) + 0.35, 1240)]
        self.t_fin = w("l6", 0)
        self.t_crime = w("l6", 3)

    def render(self, t, fi):
        base = np.zeros((H, W, 3), np.float32) + np.array(C["black"], np.float32)
        t_il0, t_il1 = w("l5", 9) - 0.05, w("l5", 10, True) + 0.35
        if t_il0 <= t < t_il1:
            k = 0.6 if hash01("il5", fi) > 0.25 else 0.15
            k *= 1 - prog(t, t_il1 - 0.15, t_il1)
            base = self.I.add(base, k)
        img = Image.fromarray(np.clip(base, 0, 255).astype(np.uint8), "RGB")
        lay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        if t < self.t_fin - 0.1:
            for txt, a, b, y in self.subs:
                if a - 0.02 <= t < b:
                    n = int(len(txt) * prog(t, a, a + 0.028 * len(txt))) or 1
                    al = 1 - prog(t, b - 0.18, b)
                    paste_text(lay, txt[:n], self.sub, (175, 175, 178, 255), W / 2 - self.sub.getlength(txt) / 2,
                               y, anchor="ls", alpha=al)
        else:
            words_line(lay, ["SEM", "BET", "LEGAL,"], [w("l6", 0), w("l6", 1), w("l6", 2)], self.big,
                       rgba(C["red"]), 900, t)
            if t >= self.t_crime - 0.02:
                p = prog(t, self.t_crime, self.t_crime + 0.18)
                s = 1 + 0.35 * (1 - e_outexpo(p))
                red_glow_text(lay, lambda L: paste_text(L, "SÓ RESTA O CRIME.", self.big, rgba(C["red"]), W / 2,
                                                        1085, anchor="ms", alpha=min(1, p * 3), scale=s), 30, 1.0)
            fin = Image.new("RGBA", (W, H), (0, 0, 0, 0))
            fin.alpha_composite(glow(lay, 40, 0.5))
            fin.alpha_composite(lay)
            lay = fin
        img = over(img, lay)
        if t >= self.t_fin:
            img = zoom(img, 1 + 0.045 * e_inout3(prog(t, self.t_fin, 30.0)), 0.5, 0.52)
        fade = prog(t, 29.72, 30.0)
        if fade > 0:
            img = Image.blend(img, BLACK, fade)
        return img

    def fx(self, t):
        return dict(grain=0.26, shake=shake_at(t, [self.t_crime], 0.25, 16),
                    glitch=0.25 if 0 <= t - self.t_crime < 0.05 else 0.0)
