"""Gera os mezaninos 1080x1920 @30fps (recorte vertical + grade) de cada plano."""
import json
import os
import subprocess
from concurrent.futures import ThreadPoolExecutor

import numpy as np

from timeline import SHOTS, W, H, FPS

KIT = os.environ.get("KIT", "/home/user/kit")


def probe(path):
    out = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries",
                          "stream=width,height", "-of", "json", path], capture_output=True, text=True).stdout
    s = json.loads(out)["streams"][0]
    return s["width"], s["height"]


def build(name, sh):
    src = os.path.join(KIT, "src", sh["src"])
    iw, ih = probe(src)
    vf = []
    if sh["crop"] == "16x9":
        cw = round(ih * W / H / 2) * 2
        x = int(min(max(sh.get("cx", 0.5) * iw - cw / 2, 0), iw - cw))
        vf.append(f"crop={cw}:{ih}:{x}:0")
    vf += [f"scale={W}:{H}:flags=lanczos", f"fps={FPS}"]
    if sh.get("sharpen"):
        vf.append("unsharp=5:5:0.7:5:5:0.0")
    if sh.get("grade"):
        vf.append(sh["grade"])
    vf.append("format=yuv420p")
    out = os.path.join(KIT, "mezz", name + ".mp4")
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", str(sh["ss"]), "-t", str(sh["dur"]), "-i", src,
                    "-an", "-vf", ",".join(vf), "-c:v", "libx264", "-crf", "14", "-preset", "fast",
                    "-g", "15", out], check=True)
    return name


def light_up_time():
    """Instante em que a tela do celular acende no clipe de abertura."""
    raw = subprocess.run(["ffmpeg", "-v", "error", "-i", os.path.join(KIT, "mezz", "op.mp4"),
                          "-vf", "scale=54:96,format=gray", "-f", "rawvideo", "-"],
                         capture_output=True).stdout
    lum = np.frombuffer(raw, np.uint8).reshape(-1, 96 * 54).mean(1)
    jump = np.diff(lum)
    i = int(np.argmax(jump))
    return (i + 1) / FPS, lum.tolist()


if __name__ == "__main__":
    with ThreadPoolExecutor(4) as ex:
        for n in ex.map(lambda kv: build(*kv), SHOTS.items()):
            print("mezz", n)
    t, lum = light_up_time()
    json.dump({"op_light": t}, open(os.path.join(KIT, "mezz", "meta.json"), "w"))
    print("op_light", t)
