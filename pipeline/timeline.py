"""Timeline do reel "Sem bet legal, o que sobra?" (30 s, 1080x1920, 30 fps).

Tudo que depende de tempo mora aqui: cenas, falas da locução (com os tempos
por palavra medidos com faster-whisper), planos de vídeo e eventos de som.
"""

W, H, FPS = 1080, 1920, 30
DUR = 30.0
NFRAMES = int(DUR * FPS)

VO_TEMPO = 1.05  # locução levemente acelerada (atempo), sem mudar o timbre

# Tempos por palavra de cada fala, no arquivo original (antes do atempo).
# "bet" é escrito "bétchi" no texto enviado ao TTS para sair com pronúncia brasileira.
VO_WORDS = {
    "l1": [(0.00, 0.20, "Sem"), (0.20, 0.56, "bétchi"), (0.56, 0.86, "legal,"), (1.28, 1.40, "o"),
           (1.40, 1.48, "que"), (1.48, 1.86, "sobra?")],
    "l2": [(0.00, 0.14, "As"), (0.14, 0.56, "legais"), (0.56, 0.80, "podem"), (0.80, 1.20, "sair."),
           (1.80, 2.10, "Mas"), (2.10, 2.30, "quem"), (2.30, 2.46, "já"), (2.46, 2.78, "opera"),
           (2.78, 3.08, "fora"), (3.08, 3.26, "da"), (3.26, 3.48, "lei,"), (3.80, 3.96, "não"),
           (3.96, 4.14, "vai"), (4.14, 4.56, "simplesmente"), (4.56, 5.54, "desaparecer.")],
    "l3": [(0.00, 0.16, "É"), (0.16, 0.24, "no"), (0.24, 0.56, "mercado"), (0.56, 1.24, "clandestino"),
           (1.24, 1.40, "que"), (1.40, 1.72, "existe"), (1.72, 2.10, "espaço"), (2.10, 2.40, "para"),
           (2.40, 2.94, "golpes,"), (3.20, 3.78, "lavagem"), (3.78, 3.92, "de"), (3.92, 4.28, "dinheiro"),
           (4.28, 4.84, "e"), (4.84, 5.40, "atuação"), (5.40, 5.52, "do"), (5.52, 5.78, "crime"),
           (5.78, 6.48, "organizado.")],
    "l4": [(0.00, 0.46, "Proibir"), (0.46, 0.62, "quem"), (0.62, 0.94, "opera"), (0.94, 1.26, "dentro"),
           (1.26, 1.52, "das"), (1.52, 1.98, "regras"), (1.98, 2.38, "não"), (2.38, 2.64, "faz"),
           (2.64, 2.86, "quem"), (2.86, 3.06, "está"), (3.06, 3.36, "fora"), (3.36, 3.72, "delas"),
           (3.72, 3.92, "parar.")],
    "l5": [(0.00, 0.26, "Você"), (0.26, 0.58, "tira"), (0.58, 0.64, "a"), (0.64, 1.04, "regra."),
           (1.66, 1.98, "Tira"), (1.98, 2.08, "a"), (2.08, 2.76, "fiscalização."), (3.32, 3.66, "E"),
           (3.66, 3.74, "o"), (3.74, 4.18, "ilegal"), (4.18, 4.46, "continua.")],
    "l6": [(0.00, 0.18, "Sem"), (0.18, 0.58, "bétchi"), (0.58, 0.90, "legal,"), (1.16, 1.38, "só"),
           (1.38, 1.82, "resta"), (1.82, 1.96, "o"), (1.96, 2.16, "crime.")],
}

# Onde cada fala entra na timeline (segundos).
VO_AT = {"l1": 0.35, "l2": 3.50, "l3": 9.00, "l4": 15.90, "l5": 22.00, "l6": 26.70}


def w(line, idx, end=False):
    """Tempo global (s) do início (ou fim) da palavra idx da fala `line`."""
    s, e, _ = VO_WORDS[line][idx]
    return VO_AT[line] + (e if end else s) / VO_TEMPO


# Cenas: (nome, início, fim)
SCENES = [
    ("s1", 0.0, 3.3),    # gancho: dinheiro + sirene, SEM / BET / LEGAL, -> O QUE SOBRA?
    ("s2", 3.3, 8.9),    # bet legal sai do ar, sites clandestinos pipocam
    ("s3", 8.9, 15.6),   # golpes / lavagem / crime organizado
    ("s4", 15.6, 21.6),  # neon: LEGAL apaga, ILEGAL continua aceso
    ("s5", 21.6, 30.0),  # tela preta, frase final em vermelho
]

# Planos (mezaninos 1080x1920 @30fps gerados por prep.py).
#   src: arquivo em $KIT/src | ss/dur: trecho | crop: 'v' (já vertical),
#   '16x9' (recorte central 9:16), cx: centro horizontal do recorte (0-1)
#   grade: parâmetros do filtro eq/colorbalance do ffmpeg
GRADE_DOC = "eq=contrast=1.12:brightness=-0.035:saturation=0.72:gamma=0.96,colorbalance=rs=-0.05:bs=0.06:rh=0.04:bh=-0.03"
GRADE_COOL = "eq=contrast=1.10:brightness=-0.02:saturation=0.70,colorbalance=rs=-0.06:bs=0.08:rm=-0.02:bm=0.03"
SHOTS = {
    "hook":  dict(src="ai_hook.mp4", ss=0.0, dur=5.0, crop="v",
                  grade="eq=contrast=1.38:brightness=-0.11:saturation=0.95:gamma=0.85,colorbalance=rs=-0.04:bs=0.05"),
    "op":    dict(src="ai_opening.mp4", ss=0.0, dur=5.0, crop="v", grade=GRADE_COOL),
    "s2bg":  dict(src="4915.mp4", ss=2.0, dur=7.0, crop="16x9", cx=0.5, grade=GRADE_DOC),
    "crime": dict(src="ai_crime.mp4", ss=0.0, dur=5.0, crop="v", grade=GRADE_DOC),
    "scam":  dict(src="51123.mp4", ss=1.5, dur=4.0, crop="16x9", cx=0.46, grade=GRADE_DOC),
    "money": dict(src="ai_money.mp4", ss=0.0, dur=5.0, crop="v", grade=GRADE_DOC),
    "cash":  dict(src="46980.mp4", ss=4.0, dur=3.0, crop="16x9", cx=0.5, grade=GRADE_DOC, sharpen=True),
    "mask":  dict(src="24035.mp4", ss=2.0, dur=3.0, crop="16x9", cx=0.5, grade=GRADE_DOC, sharpen=True),
    "cctv":  dict(src="31372.mp4", ss=1.5, dur=3.0, crop="16x9", cx=0.3,
                  grade="eq=contrast=1.12:brightness=0.04:gamma=1.25:saturation=0.0"),
    "smoke": dict(src="1968.mp4", ss=0.0, dur=8.0, crop="v", grade="eq=brightness=-0.02:saturation=0.0"),
}

# Ponto do plano do gancho (s) que entra no frame 0: o punho já descendo; o impacto no
# maço (~0,92 s no plano) cai em HOOK_IMPACT na timeline.
HOOK_SRC0 = 0.72
HOOK_IMPACT = 0.20
