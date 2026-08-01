#!/usr/bin/env bash
# =============================================================================
# publish.sh — 세 장을 한 소금으로 잠가 한 번에 올린다
#
#   bash publish.sh <site 폴더> <암호> <토큰> [<커밋 말>]
#
#   보기
#     bash publish.sh site/ "$PASS" "$TOKEN" "ARKO 마감 바뀜"
#
# 왜 한꺼번에 하는가
#   세 장이 같은 소금을 쓰면 한 장에서 뽑은 열쇠로 나머지도 곧바로 열린다.
#   장을 옮길 때마다 몇 초씩 기다리지 않아도 된다.
#   그래서 한 장만 따로 올리지 않는다. 늘 셋을 함께 올린다.
#
# 암호와 토큰은 드롭박스의 board_keys.txt 에서 읽어 넘긴다.
# 이 스크립트는 그 값을 어디에도 적어 두지 않는다.
# =============================================================================
set -euo pipefail

SITE="${1:?site 폴더가 필요합니다}"
PASS="${2:?암호가 필요합니다}"
TOKEN="${3:?토큰이 필요합니다}"
MSG="${4:-판 갱신}"

REPO="eeruwang/loggia"
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
WORK="$(mktemp -d)"

# 이번 배포의 소금 하나. 비밀이 아니라 페이지에 그대로 적힌다.
SALT="$(node -e "console.log(require('crypto').randomBytes(16).toString('base64'))")"

git clone --depth 1 -q "https://x-access-token:${TOKEN}@github.com/${REPO}.git" "$WORK/repo"

for f in index calendar journals archive; do
  if [ -f "$SITE/$f.html" ]; then
    node "$HERE/lock.js" "$SITE/$f.html" "$WORK/repo/$f.html" "$PASS" "$SALT"
  fi
done

cd "$WORK/repo"
git config user.email "eeruwang@gmail.com"
git config user.name "Il Sun Moon"

if git diff --quiet; then
  echo "바뀐 것이 없습니다. 올리지 않았습니다."
else
  git add -A
  git commit -q -m "$MSG"
  git push -q origin HEAD 2>&1 | sed "s/${TOKEN}/<token>/g" || true
  echo "올렸습니다  →  https://eeruwang.github.io/loggia/"
fi

rm -rf "$WORK"
