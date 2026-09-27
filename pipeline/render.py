"""Render do reel.

  python3 render.py stills 1.0,2.5,...  sheet.jpg   # contact sheet de frames
  python3 render.py full out_dir                    # vídeo completo (paralelo) + áudio
"""
import os
import subprocess
import sys
import time
from concurrent.futures import ProcessPoolExecutor

import numpy as np
from PIL import Image, ImageDraw

import common
from timeline import SCENES, FPS, W, H, NFRAMES

TRANSITIONS = [3.3, 8.9, 15.6]


def make_scenes():
    import scenes
    clips = common.Clips()
    return {n: getattr(scenes, n.upper())(clips) for n, a, b in SCENES}


def scene_at(t):
    for n, a, b in SCENES:
        if t < b:
            return n
    return SCENES[-1][0]


def trans_glitch(t):
    g = 0.0
    for T in TRANSITIONS:
        d = t - T
        if -0.1 <= d < 0:
            g = max(g, 0.4 + 0.6 * (1 + d / 0.1))
        elif 0 <= d < 0.1:
            g = max(g, 1.0 - d / 0.1)
    return g


def frame(scn, fi):
    t = fi / FPS
    s = scn[scene_at(t)]
    img = s.render(t, fi)
    fx = s.fx(t)
    g = max(fx.get("glitch", 0.0), trans_glitch(t))
    return common.post(img, fi, grain=fx.get("grain", 0.3), glitch_amt=g, shake=fx.get("shake", (0, 0)))


def render_range(args):
    f0, f1, out = args
    scn = make_scenes()
    enc = subprocess.Popen(["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}",
                            "-r", str(FPS), "-i", "-", "-c:v", "libx264", "-preset", "medium", "-crf", "15",
                            "-pix_fmt", "yuv420p", "-g", "30", "-bf", "0", out], stdin=subprocess.PIPE)
    t0 = time.time()
    for fi in range(f0, f1):
        enc.stdin.write(frame(scn, fi).tobytes())
    enc.stdin.close()
    enc.wait()
    return out, f1 - f0, time.time() - t0


def stills(times, out, tile=(360, 640), cols=5):
    scn = make_scenes()
    ims = []
    for t in times:
        fi = int(round(t * FPS))
        im = Image.fromarray(frame(scn, fi)).resize(tile, Image.LANCZOS)
        ImageDraw.Draw(im).text((8, 6), f"{t:.2f}s", fill=(255, 255, 0))
        ims.append(im)
    rows = (len(ims) + cols - 1) // cols
    sheet = Image.new("RGB", (tile[0] * cols, tile[1] * rows), (40, 40, 40))
    for i, im in enumerate(ims):
        sheet.paste(im, ((i % cols) * tile[0], (i // cols) * tile[1]))
    sheet.save(out, quality=88)


def full(outdir, workers=8):
    os.makedirs(outdir, exist_ok=True)
    n = workers
    bounds = [round(i * NFRAMES / n) for i in range(n + 1)]
    jobs = [(bounds[i], bounds[i + 1], os.path.join(outdir, f"part{i:02d}.mp4")) for i in range(n)]
    t0 = time.time()
    with ProcessPoolExecutor(n) as ex:
        for out, nf, dt in ex.map(render_range, jobs):
            print(f"{out}: {nf} frames em {dt:.1f}s", flush=True)
    with open(os.path.join(outdir, "parts.txt"), "w") as f:
        for _, _, o in jobs:
            f.write(f"file '{os.path.abspath(o)}'\n")
    video = os.path.join(outdir, "video.mp4")
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "concat", "-safe", "0", "-i",
                    os.path.join(outdir, "parts.txt"), "-c", "copy", video], check=True)
    print(f"video ok em {time.time() - t0:.1f}s", flush=True)
    return video


def mux(video, audio, out):
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", video, "-i", audio, "-map", "0:v", "-map", "1:a",
                    "-c:v", "copy", "-c:a", "aac", "-b:a", "256k", "-ar", "48000", "-t", str(NFRAMES / FPS),
                    "-movflags", "+faststart", out], check=True)


if __name__ == "__main__":
    cmd = sys.argv[1]
    if cmd == "stills":
        stills([float(x) for x in sys.argv[2].split(",")], sys.argv[3])
    elif cmd == "full":
        outdir = sys.argv[2]
        v = full(outdir)
        import audio
        a = audio.mix(os.path.join(outdir, "mix.wav"))
        mux(v, a, os.path.join(outdir, "sem_bet_legal_reel.mp4"))
        print("FINAL_OK", flush=True)
