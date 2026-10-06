#!/usr/bin/env python3
"""Transcreve o áudio de cada palestra separada (roda no Mac, sem o Resolve).

Lê timelines_criadas.json (gerado pelo 'separar'), corta com ffmpeg o áudio de
cada trecho direto dos arquivos originais e transcreve com faster-whisper.

  pip3 install faster-whisper
  python3 transcrever.py                  # todas, modelo "small"
  python3 transcrever.py --so 3           # só a 03
  python3 transcrever.py --modelo medium  # mais preciso, mais lento

Saída: transcricoes/NN.txt (com [hh:mm:ss] desde o início da palestra) e
transcricoes/TODAS.txt juntando tudo. É esse arquivo que dá pra mandar pro
Claude ler e sugerir nome, tipo (palestra/conversa) e tema de cada uma.
"""
import argparse
import json
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
STATE = HERE / "timelines_criadas.json"
OUT = HERE / "transcricoes"


def hms(t):
    t = int(t)
    return f"{t // 3600:02d}:{t // 60 % 60:02d}:{t % 60:02d}"


def cut_audio(src, wav):
    start = src["entrada_frames"] / src["fps_clipe"]
    cmd = ["ffmpeg", "-y", "-v", "error", "-ss", f"{start:.3f}", "-i", src["arquivo"],
           "-t", f"{src['duracao_seg']:.3f}", "-vn", "-ac", "1", "-ar", "16000", str(wav)]
    return subprocess.run(cmd).returncode == 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--so", type=int)
    ap.add_argument("--modelo", default="small")
    a = ap.parse_args()
    if not STATE.exists():
        sys.exit("Rode o 'separar' no Resolve antes (ele gera timelines_criadas.json).")
    try:
        from faster_whisper import WhisperModel
    except ImportError:
        sys.exit("Instale antes:  pip3 install faster-whisper")

    model = WhisperModel(a.modelo, device="auto", compute_type="int8")
    OUT.mkdir(exist_ok=True)
    made = json.loads(STATE.read_text(encoding="utf-8"))
    for m in made:
        n = m["n"]
        if a.so and n != a.so:
            continue
        lines = [f"# {m['timeline']}"]
        with tempfile.TemporaryDirectory() as tmp:
            for k, src in enumerate(m.get("audio", [])):
                wav = Path(tmp) / f"{k}.wav"
                if not cut_audio(src, wav):
                    lines.append(f"[{hms(src['posicao_seg'])}] (falha lendo {src['arquivo']})")
                    continue
                print(f"[{n:02d}] transcrevendo {Path(src['arquivo']).name} "
                      f"({src['duracao_seg'] / 60:.0f} min)...", flush=True)
                segs, _ = model.transcribe(str(wav), language="pt", vad_filter=True)
                for sg in segs:
                    lines.append(f"[{hms(src['posicao_seg'] + sg.start)}] {sg.text.strip()}")
        (OUT / f"{n:02d}.txt").write_text("\n".join(lines) + "\n", encoding="utf-8")
        print(f"[{n:02d}] ok → transcricoes/{n:02d}.txt")

    parts = sorted(OUT.glob("[0-9][0-9].txt"))
    (OUT / "TODAS.txt").write_text(
        "\n\n".join(p.read_text(encoding="utf-8") for p in parts), encoding="utf-8")
    print("pronto: transcricoes/TODAS.txt")


if __name__ == "__main__":
    main()
