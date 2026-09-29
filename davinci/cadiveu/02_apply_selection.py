"""CADIVEU — passo 2 do select: aplica a classificação na timeline SYNC.

Lê ~/Desktop/CADIVEU_SELECT/selection.json, no formato
  {"12": "select", "13": "reject", "14": "textura", ...}
(chave = índice do clipe na V1, o mesmo do clips.json / nome do still).

  reject  -> fica só na V1, cor Orange (câmera ruim, não entra no filme)
  select  -> copia o trecho do vídeo para a V2, na mesma posição; V1 fica Green
  textura -> igual ao select (sobe para a V2) e ainda:
             cor Pink na V1 e entra na timeline SYNC_TEXTURA (dentro do bin TEXTURA)
             (parede branca + packshot no fundo branco)

A V1 não é apagada: continua como referência por baixo. O áudio da A1 não muda.
Rodar no console do Resolve, com o projeto CADIVEU aberto.
"""
import json
import os

TIMELINE_NAME = "SYNC"
TEXTURA_BIN = "TEXTURA"
TEXTURA_TIMELINE = "SYNC_TEXTURA"
SEL_PATH = os.path.expanduser("~/Desktop/CADIVEU_SELECT/selection.json")
COLORS = {"reject": "Orange", "select": "Green", "textura": "Pink"}

resolve = app.GetResolve()  # noqa: F821
project = resolve.GetProjectManager().GetCurrentProject()
media_pool = project.GetMediaPool()

with open(SEL_PATH) as fh:
    selection = {int(k): v.lower() for k, v in json.load(fh).items()}

timeline = next(
    project.GetTimelineByIndex(i)
    for i in range(1, project.GetTimelineCount() + 1)
    if project.GetTimelineByIndex(i).GetName() == TIMELINE_NAME
)
project.SetCurrentTimeline(timeline)
if timeline.GetTrackCount("video") < 2:
    timeline.AddTrack("video")

items = timeline.GetItemListInTrack("video", 1) or []
to_v2, textura = [], []
for idx, item in enumerate(items, start=1):
    tag = selection.get(idx)
    if tag not in COLORS:
        continue
    item.SetClipColor(COLORS[tag])
    if tag == "reject":
        continue
    mpi = item.GetMediaPoolItem()
    src_in = item.GetSourceStartFrame() if hasattr(item, "GetSourceStartFrame") else item.GetLeftOffset()
    info = {
        "mediaPoolItem": mpi,
        "startFrame": src_in,
        "endFrame": src_in + item.GetDuration() - 1,
        "mediaType": 1,  # só vídeo; a A1 continua como está
    }
    to_v2.append(dict(info, trackIndex=2, recordFrame=item.GetStart()))
    if tag == "textura":
        textura.append((mpi, info))

placed = media_pool.AppendToTimeline(to_v2) or []
for tl_item in placed:
    tl_item.SetClipColor("Green")
print(f"V2: {len(placed)} de {len(to_v2)} clipes posicionados")

if textura:
    root = media_pool.GetRootFolder()
    folder = next((f for f in root.GetSubFolderList() if f.GetName() == TEXTURA_BIN), None)
    folder = folder or media_pool.AddSubFolder(root, TEXTURA_BIN)
    # Os clipes de origem ficam nos bins CARD_00x; o bin TEXTURA guarda a timeline.
    media_pool.SetCurrentFolder(folder)
    tex_tl = media_pool.CreateEmptyTimeline(TEXTURA_TIMELINE)
    project.SetCurrentTimeline(tex_tl)
    media_pool.AppendToTimeline([info for _, info in textura])
    project.SetCurrentTimeline(timeline)
    print(f"TEXTURA: {len(textura)} clipes na timeline {TEXTURA_TIMELINE}")

counts = {t: sum(1 for v in selection.values() if v == t) for t in COLORS}
print(f"Resumo: {counts} | V1 total: {len(items)}")
