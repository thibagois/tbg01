#!/usr/bin/env bash
# Baixa e prepara todas as mídias do reel.
#
# Uso: HF_ASSETS=assets_hf.txt bash setup_kit.sh
#   assets_hf.txt: uma linha por arquivo gerado no Higgsfield -> "<nome> <url>"
#   (ai_opening.mp4, ai_crime.mp4, ai_money.mp4, vo_l1.mp3 ... vo_l6.mp3)
#
# Banco de imagens/sons: Mixkit (licença Mixkit, uso gratuito).
# Fontes: Google Fonts (OFL).
set -euo pipefail
KIT=${KIT:-/home/user/kit}
HERE=$(cd "$(dirname "$0")" && pwd)
mkdir -p "$KIT"/{src,vo,sfx,fonts,mezz}
cd "$KIT"

while read -r name url; do
  [ -n "${name:-}" ] && curl -sf -o "src/$name" "$url" &
done < "${HF_ASSETS:?defina HF_ASSETS}"
wait

# Vídeos Mixkit (id:resolução máxima disponível)
for pair in 4915:2160 51123:2160 31372:2160 46980:720 24035:720 1968:1080; do
  id=${pair%%:*}; q=${pair##*:}
  curl -sf -o "src/$id.mp4" "https://assets.mixkit.co/videos/$id/$id-$q.mp4" &
done
# Efeitos sonoros Mixkit
for id in 1143 2908 788 2900 498 559 1492 2595 1457 2594 2946 2951 2354 2356 2357 497 2132 1455 2749 2745 784; do
  curl -sf -o "src/sfx_$id.mp3" "https://assets.mixkit.co/active_storage/sfx/$id/$id-preview.mp3" &
done
wait

G=https://raw.githubusercontent.com/google/fonts/main/ofl
curl -sf -o fonts/Anton.ttf $G/anton/Anton-Regular.ttf
curl -sf -o fonts/TiltNeon.ttf "$G/tiltneon/TiltNeon%5BXROT,YROT%5D.ttf"
for wt in Black ExtraBold Bold SemiBold; do
  curl -sf -o fonts/BarlowCondensed-$wt.ttf $G/barlowcondensed/BarlowCondensed-$wt.ttf
done
for wt in Medium SemiBold Bold; do curl -sf -o fonts/Barlow-$wt.ttf $G/barlow/Barlow-$wt.ttf; done
curl -sf -o fonts/SpaceMono-Regular.ttf $G/spacemono/SpaceMono-Regular.ttf
curl -sf -o fonts/SpaceMono-Bold.ttf $G/spacemono/SpaceMono-Bold.ttf

# Locução: atempo (ver timeline.VO_TEMPO), 48 kHz mono
TEMPO=$(cd "$HERE" && python3 -c "import timeline; print(timeline.VO_TEMPO)")
for i in 1 2 3 4 5 6; do
  ffmpeg -v error -y -i "src/vo_l$i.mp3" -af "atempo=$TEMPO" -ar 48000 -ac 1 "vo/l$i.wav"
done
for f in src/sfx_*.mp3; do
  n=$(basename "$f" .mp3); ffmpeg -v error -y -i "$f" -ar 48000 -ac 2 "sfx/${n#sfx_}.wav"
done

cd "$HERE" && KIT="$KIT" python3 prep.py
echo KIT_OK
