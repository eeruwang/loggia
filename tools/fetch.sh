#!/usr/bin/env bash
# =============================================================================
# fetch.sh — 저장소를 받아 데이터를 풀어 놓는다. 갱신의 첫 걸음이다
#
#   bash fetch.sh <암호> <토큰> [<놓을 자리>]
#
#   보기
#     curl -sO https://raw.githubusercontent.com/eeruwang/loggia/main/tools/fetch.sh
#     bash fetch.sh "$PASS" "$TOKEN"        # → /tmp/lg 에 놓인다
#
# 끝나면 이렇게 놓여 있다.
#   <자리>/tools/               도구
#   <자리>/loggia-data.json     풀린 데이터. 고칠 것은 이것뿐
#   <자리>/data.enc             잠긴 채로 온 원본. 손대지 않는다
#
# 데이터는 디스크에 놓인다. 대화 안으로 끌어오지 않고 그 자리에서 고친다.
# 그래야 값이 들지 않는다.
# =============================================================================
set -euo pipefail

PASS="${1:?암호가 필요합니다}"
TOKEN="${2:?토큰이 필요합니다}"
DEST="${3:-/tmp/lg}"

rm -rf "$DEST"
git clone --depth 1 -q "https://x-access-token:${TOKEN}@github.com/eeruwang/loggia.git" "$DEST"

if [ -f "$DEST/data.enc" ]; then
  node "$DEST/tools/unseal.js" "$DEST/data.enc" "$DEST/loggia-data.json" "$PASS"
else
  echo "저장소에 data.enc 가 없습니다. 데이터를 따로 구해 $DEST/loggia-data.json 에 두세요."
fi

cat <<EOF

받았습니다  $DEST
  고칠 것    $DEST/loggia-data.json
  빚는 법    cd $DEST && python3 tools/build.py loggia-data.json site/
  올리는 법  cd $DEST && bash tools/publish.sh site/ "<암호>" "<토큰>" "<커밋 말>"
EOF
