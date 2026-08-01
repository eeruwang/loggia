#!/usr/bin/env bash
# =============================================================================
# publish.sh — 네 장과 데이터를 한꺼번에 잠가 올린다
#
#   bash publish.sh <site 폴더> <암호> <토큰> [<커밋 말>] [<데이터 파일>]
#
#   보기
#     bash publish.sh site/ "$PASS" "$TOKEN" "ARKO 마감 바뀜"
#
# 데이터 파일을 적지 않으면 지금 자리의 loggia-data.json 을 찾는다.
# 있으면 data.enc 로 잠가 함께 올린다. 없으면 판만 올린다.
#
# 왜 한꺼번에 하는가
#   네 장이 같은 소금을 쓰면 한 장에서 뽑은 열쇠로 나머지도 곧바로 열린다.
#   장을 옮길 때마다 몇 초씩 기다리지 않아도 된다.
#   그래서 한 장만 따로 올리지 않는다. 늘 넷을 함께 올린다.
#   데이터도 같이 올려야 다음 사람이 지금 것을 받아 이어 고칠 수 있다.
#
# 암호와 토큰은 드롭박스의 board_keys.txt 에서 읽어 넘긴다.
# 이 스크립트는 그 값을 어디에도 적어 두지 않는다.
# =============================================================================
set -euo pipefail

SITE="${1:?site 폴더가 필요합니다}"
PASS="${2:?암호가 필요합니다}"
TOKEN="${3:?토큰이 필요합니다}"
MSG="${4:-판 갱신}"
DATA="${5:-loggia-data.json}"

REPO="eeruwang/loggia"
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
WORK="$(mktemp -d)"

# 이번 배포의 소금 하나. 비밀이 아니라 페이지에 그대로 적힌다.
SALT="$(node -e "console.log(require('crypto').randomBytes(16).toString('base64'))")"

git clone --depth 1 -q "https://x-access-token:${TOKEN}@github.com/${REPO}.git" "$WORK/repo"

# 잠글 때마다 소금과 초기값이 새로 나므로 암호문은 늘 달라 보인다.
# 그래서 알맹이의 지문을 따로 남긴다. 지문이 같으면 올릴 것이 없다.
STAMP="$( { for f in index calendar journals materials archive; do
             [ -f "$SITE/$f.html" ] && cat "$SITE/$f.html"
           done
           [ -f "$DATA" ] && cat "$DATA"
         } | sha256sum | cut -d' ' -f1 )"
if [ -f "$WORK/repo/.stamp" ] && [ "$(cat "$WORK/repo/.stamp")" = "$STAMP" ]; then
  echo "바뀐 것이 없습니다. 올리지 않았습니다."
  rm -rf "$WORK"; exit 0
fi
echo "$STAMP" > "$WORK/repo/.stamp"

for f in index calendar journals materials archive; do
  if [ -f "$SITE/$f.html" ]; then
    node "$HERE/lock.js" "$SITE/$f.html" "$WORK/repo/$f.html" "$PASS" "$SALT"
  fi
done

if [ -f "$DATA" ]; then
  node "$HERE/seal.js" "$DATA" "$WORK/repo/data.enc" "$PASS"
else
  echo "데이터 파일을 찾지 못했습니다 ($DATA). 판만 올립니다."
fi

cd "$WORK/repo"
git config user.email "eeruwang@gmail.com"
git config user.name "Il Sun Moon"

git add -A
git commit -q -m "$MSG"
git push -q origin HEAD 2>&1 | sed "s/${TOKEN}/<token>/g" || true
echo "올렸습니다  →  https://eeruwang.github.io/loggia/"

rm -rf "$WORK"
