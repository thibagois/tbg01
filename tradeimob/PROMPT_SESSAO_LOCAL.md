Você está rodando no meu Mac e vai trabalhar direto no meu DaVinci Resolve Studio 21,
pela API de scripting em Python. O projeto **TRADEIMOB** já está aberto e o External
scripting está em Local (Preferences > System > General).

## Contexto

- A timeline **PALESTRAS** tem um evento inteiro, o TradeImob Experience (~7h16 a 29,97 fps DF).
  Tem palestras solo e também **conversas em dupla**. O dono do evento é o **Ramiro**. A última
  palestra é da **Rafa**: o arquivo dela está corrompido, então só sinaliza e segue.
- Câmeras: CAM_A_TBG (Sony, clipes zv17xx.MP4), CAM_B_Namp, CAM_C_Tato. V1/A1 são a câmera
  principal, V2/A2 outra câmera. Os clipes têm efeitos (fx) e estão linkados.
- Já existem ferramentas prontas no repositório `thibagois/tbg01`, branch
  `claude/blissful-brown-a2chiw`, pasta `tradeimob/`. Clone e leia o `README.md` primeiro.
  - `split_palestras.py`: `analisar` / `separar` / `renomear` / `graficos`
  - `transcrever.py`: corta o áudio de cada bloco dos arquivos originais e transcreve (faster-whisper)
  - `render_graphics.py`: abertura de 6 s e lower third de 8 s em ProRes 4444 com alfa
  - `config.json`: nomes, cargos, temas e parâmetros de divisão
  Esses scripts só foram testados com uma timeline simulada, nunca no Resolve de verdade.
  Valide cada chamada da API (DuplicateTimeline, DeleteClips, SetSetting, AppendToTimeline,
  GetSourceStartFrame) e corrija o que não funcionar no Resolve 21.

## O que eu quero

1. **Entender a timeline:** rode o `analisar` e me mostre quantos blocos existem, com início,
   fim, duração e clipes de cada um. Não assuma que são 5. Confira se algum bloco junta duas
   sessões, por exemplo uma palestra colada numa conversa. Se a divisão por vazios errar, use
   marcadores ou cortes. Me mostre a lista antes de criar qualquer coisa.
2. **Separar:** uma timeline **HD 1920×1080** por palestra ou conversa, nomeada com número e
   nome (`01 - Ramiro`, `04 - Fulano & Beltrana`). Preserve efeitos, transform, links e áudio.
   **Nunca altere a timeline PALESTRAS original.** Se conseguir, tire o vazio do começo pra
   cada timeline começar no início dela.
3. **Transcrever** o áudio de cada bloco. No Apple Silicon, se o faster-whisper ficar lento,
   use o mlx-whisper. Depois **leia as transcrições** e, pra cada bloco:
   - diga se é palestra ou conversa;
   - identifique quem fala, nome e cargo/empresa quando a pessoa se apresentar;
   - escreva um **tema curto e forte** pra abertura, de até umas 8 palavras.
   Me mostre essa tabela pra eu aprovar ou corrigir antes de gerar os gráficos.
4. **Gráficos:** preencha o `config.json` com o que eu aprovar, rode `renomear` e o
   `render_graphics.py`, e coloque a abertura e o(s) lower third(s) numa trilha GRAFICOS
   no topo de cada timeline.

Antes de qualquer alteração em massa no projeto, me diga o que vai fazer. Salve o projeto
(ProjectManager.SaveProject) depois de cada etapa que der certo.
