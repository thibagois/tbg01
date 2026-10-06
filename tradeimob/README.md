# TradeImob Experience — separar palestras + lower third + abertura

Ferramentas pro projeto **TRADEIMOB** no DaVinci Resolve (timeline `PALESTRAS`).

| Arquivo | O que faz |
|---|---|
| `config.json` | nomes, cargos e temas de cada palestra (na ordem do evento) e como dividir |
| `split_palestras.py` | `analisar` → `separar` → `graficos` dentro do Resolve |
| `TradeImob_1_analisar.py` etc. | atalhos pro menu **Workspace > Scripts** |
| `render_graphics.py` | gera `NN_abertura.mov` (6 s) e `NN_lower_third.mov` (8 s), ProRes 4444 com alfa |

## 1. Preencher o `config.json`

Uma entrada por palestra, **na ordem em que aconteceram** (Ramiro abre, Rafa é a última).
`palestrante` vai no nome da timeline, no lower third e na abertura; `tema` vai na abertura;
`cargo` é a segunda linha do lower third.

## 2. Gerar os gráficos (no seu Mac)

```bash
brew install ffmpeg            # se ainda não tiver
pip3 install pillow numpy
python3 render_graphics.py --preview   # só PNGs em out/preview/ pra conferir
python3 render_graphics.py             # .mov em out/
```

## 3. Rodar no Resolve

Copie a pasta `tradeimob/` inteira para
`~/Library/Application Support/Blackmagic Design/DaVinci Resolve/Fusion/Scripts/Utility/`,
abra o projeto e use **Workspace > Scripts**:

1. **TradeImob_1_analisar** — não altera nada; lista no Console (Workspace > Console) os blocos
   que encontrou, com início, fim e clipes, e salva `analise_palestras.json`.
   Confira se cada bloco é uma palestra.
2. **TradeImob_2_separar** — cria `PALESTRA 01 - Ramiro`, `PALESTRA 02 - ...` duplicando a
   `PALESTRAS` e apagando o que está fora de cada bloco. Efeitos, transform, links, nível de
   áudio e a câmera 2 continuam como estavam. A timeline original não é tocada.
   O conteúdo fica na posição original: **Cmd+A e arraste até o começo** (ou renderize pelo In/Out).
3. **TradeImob_3_graficos** — importa os `.mov` num bin `GRAFICOS_TRADEIMOB` e cria uma trilha
   `GRAFICOS` no topo de cada timeline: abertura logo antes do início (ou por cima, se não houver
   espaço) e lower third aos 20 s.

### Se a divisão automática errar

Por padrão o script separa onde há mais de 90 s sem nenhum clipe e ignora blocos com menos de 5 min.
Para mandar no corte:

- **marcadores**: coloque um marcador na `PALESTRAS` no início de cada palestra (o nome do
  marcador vira o nome da timeline); ou
- **cortes**: liste os timecodes em `divisao.cortes`, ex. `["01:12:30;00", "02:40:10;00"]`.

Requer Resolve Studio 18.5+ (usa `DuplicateTimeline` e `DeleteClips`).
Fonte: Montserrat (Google Fonts, OFL), baixada sozinha em `fonts/`.
