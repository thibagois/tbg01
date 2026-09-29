"""CADIVEU — passo 1 do select: exporta um still por clipe da V1 da timeline SYNC.

Rodar dentro do DaVinci Resolve Studio (Workspace > Console > Py3, ou copiar para
~/Library/Application Support/Blackmagic Design/DaVinci Resolve/Fusion/Scripts/Edit
e chamar em Workspace > Scripts). Abra o projeto CADIVEU e a página Edit antes.

Saída em ~/Desktop/CADIVEU_SELECT/:
  clips.json            índice, nome, TC de entrada/saída e caminho de cada clipe
  stills/0001_MVI_xxxx.jpg  frame do meio de cada clipe
Mande a pasta de volta (zipada) para classificar reject / select / TEXTURA.
"""
import json
import os

TIMELINE_NAME = "SYNC"
OUT_DIR = os.path.expanduser("~/Desktop/CADIVEU_SELECT")

resolve = app.GetResolve()  # noqa: F821 (app existe no console do Resolve)
project = resolve.GetProjectManager().GetCurrentProject()
resolve.OpenPage("edit")

timeline = None
for i in range(1, project.GetTimelineCount() + 1):
    tl = project.GetTimelineByIndex(i)
    if tl.GetName() == TIMELINE_NAME:
        timeline = tl
        break
if timeline is None:
    raise SystemExit(f"Timeline '{TIMELINE_NAME}' não encontrada")
project.SetCurrentTimeline(timeline)

fps = float(timeline.GetSetting("timelineFrameRate"))


def frames_to_tc(frames):
    f = int(round(fps))
    return "%02d:%02d:%02d:%02d" % (
        frames // (3600 * f), frames // (60 * f) % 60, frames // f % 60, frames % f)


os.makedirs(os.path.join(OUT_DIR, "stills"), exist_ok=True)
clips = []
for idx, item in enumerate(timeline.GetItemListInTrack("video", 1) or [], start=1):
    mpi = item.GetMediaPoolItem()
    start, end = item.GetStart(), item.GetEnd()
    mid = start + (end - start) // 2
    name = item.GetName()
    still = os.path.join(OUT_DIR, "stills", "%04d_%s.jpg" % (idx, os.path.splitext(name)[0]))

    timeline.SetCurrentTimecode(frames_to_tc(mid))
    ok = project.ExportCurrentFrameAsStill(still)

    clips.append({
        "index": idx,
        "name": name,
        "record_in": frames_to_tc(start),
        "record_out": frames_to_tc(end),
        "duration_frames": item.GetDuration(),
        "file": mpi.GetClipProperty("File Path") if mpi else None,
        "still": os.path.basename(still) if ok else None,
    })
    print("%4d  %s  %s" % (idx, frames_to_tc(start), name))

with open(os.path.join(OUT_DIR, "clips.json"), "w") as fh:
    json.dump({"timeline": TIMELINE_NAME, "fps": fps, "clips": clips}, fh, indent=2)

print(f"\n{len(clips)} clipes exportados para {OUT_DIR}")
