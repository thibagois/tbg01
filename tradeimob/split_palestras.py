#!/usr/bin/env python3
"""Separa a timeline PALESTRAS em uma timeline por palestra (DaVinci Resolve).

Rode com o projeto TRADEIMOB aberto no Resolve:
  - copie esta pasta pra
      Mac:  ~/Library/Application Support/Blackmagic Design/DaVinci Resolve/Fusion/Scripts/Utility/
    e rode por Workspace > Scripts > split_palestras
  - ou pelo terminal (Resolve aberto, Preferences > General > External scripting = Local):
      python3 split_palestras.py analisar
      python3 split_palestras.py separar
      python3 split_palestras.py graficos

Etapas:
  analisar  só lê a timeline e lista os blocos que encontrou (não muda nada).
  separar   duplica a timeline de origem uma vez por palestra e apaga o que
            está fora do bloco, preservando efeitos, transform, links, áudio
            e a segunda câmera. A original fica intacta.
  renomear  renomeia as timelines criadas com os nomes do config.json.
  graficos  importa os .mov de out/ (render_graphics.py) e coloca a abertura e
            o lower third de cada palestra numa trilha nova no topo.

Como o script acha onde cada palestra começa (config.json > divisao.modo):
  cortes      lista de timecodes em "cortes" (início de cada palestra);
  marcadores  um marcador na timeline de origem no início de cada palestra
              (o nome do marcador vira o nome da timeline);
  gaps        blocos de clipes separados por um vazio maior que gap_minimo_seg;
  auto        cortes se houver, senão marcadores, senão gaps.
"""
import json
import os
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent if "__file__" in globals() else Path.cwd()
CONFIG = HERE / "config.json"
REPORT = HERE / "analise_palestras.json"


# ---------------------------------------------------------------- Resolve
def get_resolve():
    r = globals().get("resolve")  # dentro do Resolve (Workspace > Scripts)
    if r:
        return r
    try:
        import DaVinciResolveScript as dvr
    except ImportError:
        mods = {
            "darwin": "/Library/Application Support/Blackmagic Design/DaVinci Resolve/Developer/Scripting/Modules",
            "win32": os.path.expandvars(r"%PROGRAMDATA%\Blackmagic Design\DaVinci Resolve\Support\Developer\Scripting\Modules"),
        }.get(sys.platform, "/opt/resolve/Developer/Scripting/Modules")
        sys.path.append(mods)
        import DaVinciResolveScript as dvr
    r = dvr.scriptapp("Resolve")
    if not r:
        sys.exit("Não achei o Resolve. Ele está aberto? External scripting está em Local?")
    return r


def timelines(project):
    return [project.GetTimelineByIndex(i) for i in range(1, project.GetTimelineCount() + 1)]


def find_timeline(project, name):
    for tl in timelines(project):
        if tl.GetName() == name:
            return tl
    return None


def all_items(tl):
    """[(tipo, trilha, item)] de todas as trilhas de vídeo e áudio."""
    out = []
    for kind in ("video", "audio"):
        for idx in range(1, tl.GetTrackCount(kind) + 1):
            for it in tl.GetItemListInTrack(kind, idx) or []:
                out.append((kind, idx, it))
    return out


# ---------------------------------------------------------------- timecode
def fps_of(tl):
    return float(tl.GetSetting("timelineFrameRate"))


def is_drop(tl):
    return tl.GetSetting("timelineDropFrameTimecode") in ("1", 1, True, "true")


def tc_to_frames(tc, fps, drop):
    tc = tc.replace(";", ":").replace(".", ":")
    h, m, s, f = (int(x) for x in tc.split(":"))
    nom = int(round(fps))
    frames = ((h * 3600 + m * 60 + s) * nom) + f
    if drop and nom in (30, 60):
        d = 2 * nom // 30
        mins = h * 60 + m
        frames -= d * (mins - mins // 10)
    return frames


def frames_to_tc(n, fps, drop):
    nom = int(round(fps))
    if drop and nom in (30, 60):
        d = 2 * nom // 30
        per10 = nom * 600 - d * 9
        per1 = nom * 60 - d
        tens, rem = divmod(n, per10)
        n += d * 9 * tens + (d * ((rem - d) // per1) if rem > d else 0)
    f = n % nom
    s = n // nom
    sep = ";" if drop else ":"
    return f"{s // 3600:02d}:{s // 60 % 60:02d}:{s % 60:02d}{sep}{f:02d}"


# ---------------------------------------------------------------- análise
def blocks_from_gaps(items, fps, gap_s):
    spans = sorted((it.GetStart(), it.GetEnd(), it.GetName()) for _, _, it in items)
    blocks = []
    for s, e, name in spans:
        if blocks and s - blocks[-1]["fim"] <= gap_s * fps:
            b = blocks[-1]
            b["fim"] = max(b["fim"], e)
            if name not in b["clipes"]:
                b["clipes"].append(name)
        else:
            blocks.append({"inicio": s, "fim": e, "clipes": [name], "nome": ""})
    return blocks


def blocks_from_cuts(items, cuts, tl_end, names=None):
    """cuts = frames absolutos do início de cada palestra."""
    cuts = sorted(cuts)
    blocks = []
    for i, c in enumerate(cuts):
        nxt = cuts[i + 1] if i + 1 < len(cuts) else tl_end
        inside = [it for _, _, it in items if it.GetStart() < nxt and it.GetEnd() > c]
        if not inside:
            continue
        blocks.append({
            "inicio": max(c, min(it.GetStart() for it in inside)),
            "fim": min(nxt, max(it.GetEnd() for it in inside)),
            "clipes": sorted({it.GetName() for it in inside}),
            "nome": (names or {}).get(c, ""),
        })
    return blocks


def analyze(project, cfg):
    src = find_timeline(project, cfg["timeline_origem"])
    if not src:
        sys.exit(f"Timeline '{cfg['timeline_origem']}' não encontrada.")
    fps, drop = fps_of(src), is_drop(src)
    t0, t1 = src.GetStartFrame(), src.GetEndFrame()
    items = all_items(src)
    div = cfg.get("divisao", {})
    modo = div.get("modo", "auto")
    markers = src.GetMarkers() or {}

    if modo == "auto":
        modo = "cortes" if div.get("cortes") else "marcadores" if markers else "gaps"
    if modo == "cortes":
        cuts = [tc_to_frames(tc, fps, drop) for tc in div["cortes"]]
        blocks = blocks_from_cuts(items, cuts, t1)
    elif modo == "marcadores":
        # GetMarkers() devolve frames relativos ao início da timeline
        names = {t0 + int(f): m.get("name", "") for f, m in markers.items()}
        blocks = blocks_from_cuts(items, list(names), t1, names)
    else:
        blocks = blocks_from_gaps(items, fps, float(div.get("gap_minimo_seg", 90)))
        min_len = float(div.get("duracao_minima_seg", 300)) * fps
        curtos = [b for b in blocks if b["fim"] - b["inicio"] < min_len]
        if curtos:
            print(f"(ignorando {len(curtos)} bloco(s) com menos de "
                  f"{div.get('duracao_minima_seg', 300)} s — veja o relatório)")
        blocks = [b for b in blocks if b["fim"] - b["inicio"] >= min_len] + \
                 [dict(b, ignorado=True) for b in curtos]
        blocks.sort(key=lambda b: b["inicio"])

    print(f"\nTimeline {src.GetName()}  ({fps:g} fps{' DF' if drop else ''})  modo: {modo}")
    print(f"{'#':>3}  {'início':>12}  {'fim':>12}  {'duração':>9}  clipes")
    n = 0
    for b in blocks:
        b["inicio_tc"] = frames_to_tc(b["inicio"], fps, drop)
        b["fim_tc"] = frames_to_tc(b["fim"], fps, drop)
        dur = (b["fim"] - b["inicio"]) / fps
        b["duracao"] = f"{int(dur // 3600)}h{int(dur // 60 % 60):02d}m{int(dur % 60):02d}s"
        tag = "  -" if b.get("ignorado") else f"{(n := n + 1):>3}"
        clips = ", ".join(b["clipes"][:4]) + (" ..." if len(b["clipes"]) > 4 else "")
        print(f"{tag}  {b['inicio_tc']:>12}  {b['fim_tc']:>12}  {b['duracao']:>9}  {clips}")
    REPORT.write_text(json.dumps({"modo": modo, "fps": fps, "blocos": blocks},
                                 indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"\nrelatório: {REPORT}")
    return src, [b for b in blocks if not b.get("ignorado")]


# ---------------------------------------------------------------- separar
def people(p):
    """[(nome, cargo)] de uma entrada do config (palestra solo ou conversa em dupla)."""
    if p.get("palestrantes"):
        return [(x.get("nome", ""), x.get("cargo", "")) for x in p["palestrantes"]]
    return [(p.get("palestrante", ""), p.get("cargo", ""))] if p.get("palestrante") else []


def timeline_name(cfg, i, block=None):
    """'03 - Fulano' ou '04 - Fulano & Beltrano'."""
    talks = cfg.get("palestras", [])
    p = talks[i - 1] if i <= len(talks) else {}
    who = " & ".join(n for n, _ in people(p) if n) or (block or {}).get("nome", "")
    return f"{i:02d} - {who}" if who else f"{i:02d} - {cfg.get('prefixo_timelines', 'PALESTRA').title()}"


def set_hd(tl, cfg):
    """Timeline própria em HD (ou o que estiver em config.resolucao)."""
    w, h = cfg.get("resolucao", [1920, 1080])
    ok = tl.SetSetting("useCustomSettings", "1")
    ok = tl.SetSetting("timelineResolutionWidth", str(w)) and ok
    ok = tl.SetSetting("timelineResolutionHeight", str(h)) and ok
    return ok


def audio_sources(tl, b):
    """Trechos de áudio da trilha com mais cobertura, pra transcrição fora do Resolve."""
    best, cover = None, -1
    for idx in range(1, tl.GetTrackCount("audio") + 1):
        items = tl.GetItemListInTrack("audio", idx) or []
        c = sum(it.GetDuration() for it in items)
        if c > cover:
            best, cover = items, c
    fps = fps_of(tl)
    out = []
    for it in best or []:
        mpi = it.GetMediaPoolItem()
        if not mpi:
            continue
        try:
            src_in = it.GetSourceStartFrame()  # Resolve 18.5+
        except Exception:
            src_in = it.GetLeftOffset()
        out.append({
            "arquivo": mpi.GetClipProperty("File Path"),
            "fps_clipe": float(mpi.GetClipProperty("FPS") or fps),
            "entrada_frames": src_in,
            "duracao_seg": it.GetDuration() / fps,
            "posicao_seg": (it.GetStart() - b["inicio"]) / fps,
        })
    return out


def split(project, cfg):
    src, blocks = analyze(project, cfg)
    if not blocks:
        sys.exit("Nenhum bloco encontrado.")
    fps, drop = fps_of(src), is_drop(src)
    t0 = src.GetStartFrame()
    made = []
    for i, b in enumerate(blocks, 1):
        name = timeline_name(cfg, i, b)
        if find_timeline(project, name):
            print(f"[{i:02d}] '{name}' já existe — pulei (apague ou renomeie pra refazer)")
            continue
        project.SetCurrentTimeline(src)
        tl = src.DuplicateTimeline(name)
        if not tl:
            print(f"[{i:02d}] falhou ao duplicar a timeline")
            continue
        if not set_hd(tl, cfg):
            print(f"[{i:02d}] aviso: não consegui mudar a resolução da timeline")
        fora, cortados = [], []
        for kind, idx, it in all_items(tl):
            s, e = it.GetStart(), it.GetEnd()
            if e <= b["inicio"] or s >= b["fim"]:
                fora.append(it)
            elif s < b["inicio"] or e > b["fim"]:
                cortados.append(f"{kind[0].upper()}{idx} {it.GetName()}")
        if fora and not tl.DeleteClips(fora, False):
            print(f"[{i:02d}] aviso: DeleteClips falhou (Resolve 18.5+ necessário)")
        for f in list((tl.GetMarkers() or {}).keys()):
            if not (b["inicio"] <= t0 + int(f) < b["fim"]):
                tl.DeleteMarkerAtFrame(f)
        rel = b["inicio"] - t0
        tl.AddMarker(rel, "Blue", "INÍCIO", name, 1)
        try:  # Resolve 19+: marca In/Out no bloco pra render direto
            tl.SetMarkInOut(b["inicio"], b["fim"] - 1)
        except Exception:
            pass
        print(f"[{i:02d}] {name}: {b['inicio_tc']} → {b['fim_tc']} ({b['duracao']}), "
              f"{len(fora)} clipes removidos")
        if cortados:
            print("      atenção, clipes atravessando o corte (ficaram inteiros): "
                  + ", ".join(cortados))
        made.append({"n": i, "timeline": name, "inicio": b["inicio"], "fim": b["fim"],
                     "audio": audio_sources(tl, b)})
    project.SetCurrentTimeline(src)
    state = HERE / "timelines_criadas.json"
    old = json.loads(state.read_text()) if state.exists() else []
    keep = {m["timeline"] for m in made}
    state.write_text(json.dumps([o for o in old if o["timeline"] not in keep] + made,
                                indent=2, ensure_ascii=False), encoding="utf-8")
    print("\nPronto. Em cada timeline nova o conteúdo continua na posição original:"
          "\nselecione tudo (Cmd+A) e arraste até o começo, ou renderize pelo In/Out.")


# ---------------------------------------------------------------- gráficos
def place_graphics(project, cfg):
    state = HERE / "timelines_criadas.json"
    if not state.exists():
        sys.exit("Rode 'separar' antes.")
    made = json.loads(state.read_text())
    g = cfg.get("graficos", {})
    out = (HERE / g.get("pasta_saida", "out")).resolve()
    lt_at = float(g.get("lower_third_entra_aos_seg", 20))

    mp = project.GetMediaPool()
    root = mp.GetRootFolder()
    folder = next((f for f in root.GetSubFolderList() if f.GetName() == "GRAFICOS_TRADEIMOB"), None) \
        or mp.AddSubFolder(root, "GRAFICOS_TRADEIMOB")
    mp.SetCurrentFolder(folder)

    for m in made:
        n = m["n"]
        tl = find_timeline(project, m["timeline"])
        ab_file = out / f"{n:02d}_abertura.mov"
        lt_files = sorted(out.glob(f"{n:02d}_lower_third*.mov"))  # 1 por pessoa
        if not tl or not ab_file.exists() or not lt_files:
            print(f"[{n:02d}] pulei (timeline ou .mov faltando em {out})")
            continue
        if any((tl.GetTrackName("video", i) or "") == "GRAFICOS"
               for i in range(1, tl.GetTrackCount("video") + 1)):
            print(f"[{n:02d}] já tem trilha GRAFICOS — pulei")
            continue
        clips = mp.ImportMedia([str(ab_file)] + [str(f) for f in lt_files]) or []
        if len(clips) != 1 + len(lt_files):
            print(f"[{n:02d}] falha ao importar os .mov")
            continue
        clips.sort(key=lambda c: c.GetName())  # abertura, lower_third, lower_third_2
        project.SetCurrentTimeline(tl)
        fps = fps_of(tl)
        tl.AddTrack("video")
        track = tl.GetTrackCount("video")
        tl.SetTrackName("video", track, "GRAFICOS")
        t0 = tl.GetStartFrame()

        def length(c, default):
            return int(c.GetClipProperty("Frames") or round(default * fps))

        ab = clips[0]
        ab_len = length(ab, g.get("abertura_seg", 6))
        # abertura antes da palestra se houver espaço vazio, senão por cima do começo
        ab_rec = m["inicio"] - ab_len if m["inicio"] - ab_len >= t0 else m["inicio"]
        plan = [{"mediaPoolItem": ab, "startFrame": 0, "endFrame": ab_len - 1,
                 "trackIndex": track, "recordFrame": ab_rec, "mediaType": 1}]
        at = m["inicio"] + int(lt_at * fps)
        for lt in clips[1:]:  # numa conversa, um lower third depois do outro
            lt_len = length(lt, g.get("lower_third_seg", 8))
            plan.append({"mediaPoolItem": lt, "startFrame": 0, "endFrame": lt_len - 1,
                         "trackIndex": track, "recordFrame": at, "mediaType": 1})
            at += lt_len + int(4 * fps)
        ok = mp.AppendToTimeline(plan)
        where = "antes do início" if ab_rec < m["inicio"] else "sobre o início"
        print(f"[{n:02d}] {m['timeline']}: abertura {where}, {len(clips) - 1} lower third(s) "
              f"a partir de {lt_at:g}s" + ("" if ok else "  (AppendToTimeline falhou)"))


# ---------------------------------------------------------------- renomear
def rename(project, cfg):
    """Depois de preencher nomes/temas no config: renomeia as timelines criadas."""
    state = HERE / "timelines_criadas.json"
    made = json.loads(state.read_text()) if state.exists() else []
    for m in made:
        tl = find_timeline(project, m["timeline"])
        new = timeline_name(cfg, m["n"])
        if tl and new != m["timeline"] and tl.SetName(new):
            print(f"[{m['n']:02d}] {m['timeline']} → {new}")
            m["timeline"] = new
    state.write_text(json.dumps(made, indent=2, ensure_ascii=False), encoding="utf-8")


# ---------------------------------------------------------------- main
def main():
    cfg = json.loads(CONFIG.read_text(encoding="utf-8"))
    project = get_resolve().GetProjectManager().GetCurrentProject()
    if not project:
        sys.exit("Nenhum projeto aberto.")
    cmd = sys.argv[1] if len(sys.argv) > 1 else "analisar"
    if cmd == "analisar":
        analyze(project, cfg)
    elif cmd == "separar":
        split(project, cfg)
    elif cmd == "renomear":
        rename(project, cfg)
    elif cmd == "graficos":
        place_graphics(project, cfg)
    else:
        sys.exit(__doc__)


if __name__ == "__main__":
    main()
