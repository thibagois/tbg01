# Sem bet legal, o que sobra? — Reel 30 s (9:16)

Reel de 30 s em 1080×1920 / 30 fps, feito com motion graphics programáticos,
banco de imagens gratuito (Mixkit) e poucos planos gerados no Higgsfield.

## Estrutura

| Tempo | Cena | Imagem | Texto na tela |
|---|---|---|---|
| 0–1,5 s | Gancho | Plano de IA (Kling 3.0): punho batendo um maço de dinheiro numa mesa cheia de celulares, sob luz de sirene; flashes subliminares de 2 frames do resto do filme | SEM / BET / LEGAL, (gigante, uma palavra por batida) |
| 1,5–3,3 s | Corte seco, silêncio | Plano de IA: celular acende no escuro | **O QUE SOBRA?** |
| 3,3–8,9 s | A bet legal sai do ar, sites clandestinos pipocam | Celular desenhado: site regulado (fictício) → "SITE FORA DO AR / Erro 451" → cassino clandestino; 10 pop-ups de sites piratas | O **ILEGAL** CONTINUA. |
| 8,9–15,6 s | Mercado clandestino | IA: sala clandestina com rack de celulares (HUD de vigilância) · Mixkit: mensagens de golpe · IA: máquina contando dinheiro + extrato de PIX · Mixkit: mascarado em data center + rede criminosa · Mixkit: câmera de segurança | GOLPES. / LAVAGEM DE DINHEIRO. / **CRIME ORGANIZADO.** |
| 15,6–21,6 s | Neon | Placas de neon desenhadas: LEGAL falha e apaga com faíscas; ILEGAL continua aceso | — |
| 21,6–30 s | Tela preta, silêncio | Legendas discretas + lampejo do neon ILEGAL | **SEM BET LEGAL, / SÓ RESTA O CRIME.** (vermelho) |

Os tempos de cada palavra da locução (medidos com faster-whisper) dirigem as
entradas de texto e os efeitos sonoros — está tudo em `pipeline/timeline.py`.

## Pipeline (`pipeline/`)

- `setup_kit.sh` — baixa as mídias (Higgsfield, Mixkit, Google Fonts) e gera os mezaninos.
- `prep.py` — recorte vertical 9:16, grade de cor e conformação a 30 fps de cada plano.
- `common.py` — texto, glow, easing, leitura de clipes via ffmpeg, grão/vinheta/glitch.
- `ui.py` — elementos desenhados: celular, telas de site, pop-ups, balões de golpe, HUD, extrato de PIX, rede, neon.
- `scenes.py` — as 5 cenas (cada uma é função pura do tempo).
- `audio.py` — mixagem em numpy (locução + drone + batimento + efeitos) e loudnorm a −14 LUFS.
- `render.py` — `stills` (contact sheet) ou `full` (render paralelo + mux).

```bash
HF_ASSETS=assets_hf.txt bash pipeline/setup_kit.sh   # "nome url" por linha dos arquivos do Higgsfield
cd pipeline && python3 render.py full ../out        # -> out/sem_bet_legal_reel.mp4
```

Dependências: Python 3 com Pillow e numpy, ffmpeg com libx264.

## Créditos e licenças

- **Higgsfield** (≈ 30 créditos no total): 4 planos Kling 3.0 std 5 s sem som
  (gancho, abertura, sala clandestina, máquina de contar dinheiro) e locução
  Text-to-Speech V2 / ElevenLabs, voz "Orion" ("bet" grafado "bétchi" para a pronúncia brasileira).
- **Mixkit** (licença gratuita Mixkit): vídeos 4915, 51123, 31372, 46980, 24035, 1968;
  efeitos sonoros 1143, 2908, 788, 2900, 498, 559, 1492, 2595, 1457, 2594, 2946,
  2951, 2354, 2356, 2357, 497, 2132, 1455, 2749, 2745, 784, 1641, 724, 2299.
- **Fontes** (SIL OFL, Google Fonts): Anton, Tilt Neon, Barlow, Barlow Condensed, Space Mono.

Marcas, sites e URLs mostrados no vídeo são fictícios.
