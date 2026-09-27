"""Mixagem: locução + cama (drone/pulso) + efeitos sincronizados com a imagem.

Tudo em numpy a 48 kHz; normalização final em -14 LUFS (loudnorm em 2 passes).
"""
import json
import os
import subprocess

import numpy as np

from timeline import w, VO_AT, DUR, HOOK_IMPACT
import ui

KIT = os.environ.get("KIT", "/home/user/kit")
SR = 48000
N = int((DUR + 0.5) * SR)


def load(path, ch=2):
    raw = subprocess.run(["ffmpeg", "-v", "error", "-i", path, "-f", "f32le", "-ac", str(ch), "-ar", str(SR), "-"],
                         capture_output=True, check=True).stdout
    x = np.frombuffer(raw, np.float32).reshape(-1, ch).copy()
    pk = np.abs(x).max() or 1.0
    return x / pk * 0.89  # pico em -1 dBFS


_cache = {}


def sfx(i):
    if i not in _cache:
        _cache[i] = load(os.path.join(KIT, "sfx", f"{i}.wav"))
    return _cache[i]


def place(buf, x, t, db=0.0, fin=0.004, fout=0.02, dur=None, align="start", skip=0.0):
    """align: 'start' (início do arquivo em t), 'peak' (pico em t, com a subida antes) ou
    'hit' (corta a subida e começa 30 ms antes do pico, para batidas secas no frame)."""
    x = x[int(skip * SR):]
    if align == "hit":
        x = x[max(0, int(np.argmax(np.abs(x).max(1))) - int(0.03 * SR)):]
        t -= 0.03
    if dur is not None:
        x = x[:int(dur * SR)]
    x = x.copy()
    a, b = int(fin * SR), int(fout * SR)
    if a > 0:
        x[:a] *= np.linspace(0, 1, a, dtype=np.float32)[:, None]
    if b > 0:
        x[-b:] *= np.linspace(1, 0, b, dtype=np.float32)[:, None]
    if align == "peak":
        t -= np.argmax(np.abs(x).max(1)) / SR
    s = int(round(t * SR))
    if s < 0:
        x, s = x[-s:], 0
    e = min(N, s + len(x))
    if e > s:
        buf[s:e] += x[:e - s] * (10 ** (db / 20))


def mix(out):
    vo = np.zeros((N, 2), np.float32)
    bed = np.zeros((N, 2), np.float32)
    fx = np.zeros((N, 2), np.float32)

    for k, t in VO_AT.items():
        v = load(os.path.join(KIT, "vo", f"{k}.wav"), ch=1)
        place(vo, np.repeat(v, 2, 1), t, db=-2.0, fin=0.002, fout=0.03)

    CUT = 21.6  # tela preta: silêncio seco
    # cama
    place(bed, sfx(2749), 0.0, db=-13, fin=1.5, fout=0.03, dur=CUT)
    place(bed, sfx(2745), 8.9, db=-19, fin=0.8, fout=0.03, dur=CUT - 8.9)
    place(bed, sfx(2132), 15.75, db=-15, fin=0.05, fout=0.03, dur=CUT - 15.75)   # zumbido do neon
    place(bed, sfx(497), 19.6, db=-9, fin=0.2, fout=0.03, dur=CUT - 19.6)        # batimento

    # S1 (gancho): braaam + sirene cortados secos no "o que sobra?"
    t_cut = w("l1", 3) - 0.04
    place(bed, sfx(724), 0.0, db=-6, fout=0.04, dur=t_cut)
    place(bed, sfx(1641), 0.0, db=-15, fout=0.04, dur=t_cut)
    place(fx, sfx(2951), 0.0, db=-8)                            # glitch do frame 0
    place(fx, sfx(788), HOOK_IMPACT, db=-3, align="peak")       # punho no dinheiro
    for k in range(3):
        place(fx, sfx(2299), w("l1", k), db=-7)                  # SEM / BET / LEGAL,
    place(fx, sfx(2951), t_cut, db=-11)
    place(fx, sfx(2354), t_cut + 0.02, db=-10)                  # celular acende
    place(fx, sfx(1492), 3.3, db=-9, align="peak")              # transição
    # S2
    place(fx, sfx(1457), w("l2", 3) - 0.25, db=-13, dur=0.5)    # site caindo
    place(fx, sfx(2951), w("l2", 3), db=-10)
    t_mas, t_slam = w("l2", 4), w("l2", 14)
    n = len(ui.POPUPS)
    span = (t_slam - 0.25) - (t_mas + 0.1)
    for i in range(n):
        pid = (2357, 2356, 2354)[i % 3]
        place(fx, sfx(pid), t_mas + 0.1 + i * span / (n - 1), db=-15 + (i % 2) * 2)
    place(fx, sfx(788), t_slam, db=-5, align="hit")             # O ILEGAL CONTINUA.
    place(fx, sfx(498), t_slam, db=-8)
    place(fx, sfx(1143), 8.9, db=-8, align="peak")              # transição
    # S3
    c1 = w("l3", 6) - 0.05
    for k in range(3):
        place(fx, sfx(2354), c1 + 0.05 + 0.33 * k, db=-14)      # mensagens de golpe
    place(fx, sfx(498), w("l3", 8), db=-6)                      # GOLPES.
    place(fx, sfx(498), w("l3", 9), db=-6)                      # LAVAGEM DE DINHEIRO.
    place(fx, sfx(2595), w("l3", 13) - 0.08, db=-15)
    place(fx, sfx(2908), w("l3", 15), db=-4)                    # CRIME ORGANIZADO.
    place(fx, sfx(784), 15.6, db=-10, align="peak")             # entra o neon
    # S4
    place(fx, sfx(2594), 15.78, db=-12)                         # LEGAL acende
    place(fx, sfx(2594), 16.08, db=-11)                         # ILEGAL acende
    tb, td = w("l4", 6), w("l4", 12)
    for k, tt in enumerate(np.linspace(tb + 0.2, td - 0.25, 4)):
        place(fx, sfx(2595), float(tt), db=-16 + k)             # LEGAL falhando
    place(fx, sfx(1455), td, db=-7, dur=1.2, fout=0.3)          # LEGAL morre
    place(fx, sfx(2951), td, db=-10)
    # S5 (silêncio + locução)
    place(fx, sfx(2594), w("l5", 9) - 0.05, db=-17)             # lampejo do ILEGAL
    place(fx, sfx(559), w("l6", 0), db=-9)
    place(fx, sfx(2900), w("l6", 3), db=-3, fout=0.4, dur=DUR - w("l6", 3), align="hit")  # SÓ RESTA O CRIME.
    place(fx, sfx(788), w("l6", 3), db=-8, align="hit")

    # ducking da cama sob a voz
    env = np.abs(vo).max(1)
    k = int(0.08 * SR)
    env = np.convolve(env, np.ones(k, np.float32) / k, mode="same")
    duck = 1 - 0.5 * np.clip(env / 0.08, 0, 1)
    m = bed * duck[:, None] + fx + vo
    m[int(DUR * SR):] = 0
    m = np.tanh(m * 1.1) / np.tanh(1.1)
    raw = out + ".pre.wav"
    pcm = (np.clip(m, -1, 1) * 32767).astype("<i2")
    _write_wav(raw, pcm)
    meas = subprocess.run(["ffmpeg", "-hide_banner", "-i", raw, "-af", "loudnorm=I=-14:TP=-1.5:LRA=11:print_format=json",
                           "-f", "null", "-"], capture_output=True, text=True).stderr
    js = json.loads(meas[meas.rindex("{"):meas.rindex("}") + 1])
    af = ("loudnorm=I=-14:TP=-1.5:LRA=11:linear=true:"
          f"measured_I={js['input_i']}:measured_TP={js['input_tp']}:measured_LRA={js['input_lra']}:"
          f"measured_thresh={js['input_thresh']}:offset={js['target_offset']}")
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", raw, "-af", af, "-ar", str(SR), out], check=True)
    print("audio", js["input_i"], "->", out, flush=True)
    return out


def _write_wav(path, pcm):
    import wave
    with wave.open(path, "wb") as f:
        f.setnchannels(2)
        f.setsampwidth(2)
        f.setframerate(SR)
        f.writeframes(pcm.tobytes())


if __name__ == "__main__":
    mix(os.path.join(os.environ.get("OUT", "/home/user/out"), "mix.wav"))
