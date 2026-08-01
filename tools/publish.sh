#!/usr/bin/env bash
# =============================================================================
# publish.sh — 데이터를 잠가 올린다
#
#   bash publish.sh <site 폴더> <암호> <토큰> [<커밋 말>] [<데이터 파일>]
#
#   보기
#     LEDGER_TOKEN="$LTOK" DIGEST_KEY="$DKEY" \
#       bash publish.sh site/ "$PASS" "$TOKEN" "ARKO 마감 바뀜"
#
# 2026년 8월 1일에 화면 만드는 일을 브라우저로 옮겼다. 그전에는 파이썬이 그린 다섯 페이지를
# 각각 잠가 올렸고, 암호화된 파일은 갱신할 때마다 처음부터 끝까지 달라 보이므로
# 글자 하나를 고쳐도 368KB가 저장소에 새로 쌓였다. 지금 갱신 한 번에 바뀌는
# 것은 public/data.enc 하나뿐이다.
#
# 그래서 솔트를 다섯 페이지가 나눠 쓰던 셈이 없어졌다. 솔트는 data.enc 안에
# 하나뿐이다. lock.js 도 함께 없어졌다.
#
# 암호와 토큰 네 개
#   <암호>        data.enc 를 잠근다. 보드를 여는 그 암호다
#   <토큰>        저장소에 올린다
#   DIGEST_KEY    아침 메일 요약을 암호화한다. 주지 않으면 그것만 건너뛴다
#   LEDGER_TOKEN  기록 토큰. 잠기는 데이터 안에 넣는다. 주지 않으면
#                 판에서 체크와 할 일 추가가 사라진다
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
ROOT="$(cd "$HERE/.." && pwd)"
WORK="$(mktemp -d)"

git clone --depth 1 -q "https://x-access-token:${TOKEN}@github.com/${REPO}.git" "$WORK/repo"

# 잠글 때마다 솔트와 초기값이 새로 나므로 암호문은 늘 달라 보인다.
# 그래서 내용 지문을 따로 남긴다. 지문이 같으면 올릴 것이 없다.
#
# 도구와 워커와 HTML 틀도 지문에 넣는다. 넣지 않으면 화면 만드는 코드를 고쳐도
# 데이터가 그대로일 때 「바뀐 것이 없습니다」라며 고친 손을 올리지 않는다.
# 그러면 저장소의 도구가 조용히 낡고, 다음 사람이 받아 쓰는 것이 옛 도구가 된다.
#
# 글꼴과 data.enc 는 뺀다. 글형식은 크고 바뀌지 않으며, data.enc 는 잠글 때마다
# 달라 보이므로 넣으면 지문이 늘 어긋나 빈 커밋이 쌓인다.
tree_hash() {
  local d="$1"
  [ -d "$d" ] || return 0
  find "$d" -type f \
       -not -path '*/node_modules/*' -not -path '*/.wrangler/*' \
       -not -path '*/font/*' -not -name 'data.enc' \
    | LC_ALL=C sort | while read -r f; do printf '%s\n' "$f"; cat "$f"; done
}

STAMP="$( { { [ -f "$DATA" ] && cat "$DATA"; } || true
           { [ -f "$SITE/digest.json" ] && cat "$SITE/digest.json"; } || true
           tree_hash "$ROOT/public"
           tree_hash "$ROOT/tools"
           tree_hash "$ROOT/worker"
           for f in wrangler.jsonc package.json package-lock.json tsconfig.json .gitignore; do
             { [ -f "$ROOT/$f" ] && cat "$ROOT/$f"; } || true
           done
         } | sha256sum | cut -d' ' -f1 )"
if [ -f "$WORK/repo/.stamp" ] && [ "$(cat "$WORK/repo/.stamp")" = "$STAMP" ]; then
  echo "바뀐 것이 없습니다. 올리지 않았습니다."
  rm -rf "$WORK"; exit 0
fi
echo "$STAMP" > "$WORK/repo/.stamp"

# ── 클라우드플레어가 내주는 자리 ────────────────────────────────────────────
# 워커의 assets 는 public/ 하나만 본다. HTML 다섯 페이지와 스타일과 화면 만드는 코드와
# 잠긴 데이터가 모두 여기 있다.
mkdir -p "$WORK/repo/public"
for f in index calendar journals materials archive; do
  [ -f "$ROOT/public/$f.html" ] && cp "$ROOT/public/$f.html" "$WORK/repo/public/$f.html" || true
done
cp "$ROOT/public/app.css" "$WORK/repo/public/app.css"
cp "$ROOT/public/app.js"  "$WORK/repo/public/app.js"

# 글형식은 public/ 이 제자리다. 옛 자리에 남아 있으면 옮긴다.
if [ -d "$ROOT/public/font" ] && [ ! -d "$WORK/repo/public/font" ]; then
  cp -r "$ROOT/public/font" "$WORK/repo/public/font"
fi

# 깃허브 페이지 시절과 파이썬이 판을 그리던 시절의 자취를 치운다.
# 두 자리에 같은 판이 있으면 언젠가 한쪽이 낡는다. 그것이 이 판을 한 번 갈라놓았다.
rm -rf "$WORK/repo/font"
rm -f "$WORK/repo/CNAME" "$WORK/repo/.nojekyll" "$WORK/repo/data.enc"
for f in index calendar journals materials archive; do
  rm -f "$WORK/repo/$f.html"
done

# 글형식은 한 번 받으면 바뀌지 않는다. HTML 틀과 옷과 손과 내용은 갱신될 때마다
# 달라질 수 있다. 이 파일은 내주지 않고 규칙으로만 읽힌다.
cat > "$WORK/repo/public/_headers" <<'HDR'
# 글형식은 이름에 내용이 박혀 있지 않으나 바뀌지 않는다. 한 해를 재운다.
/font/*
  Cache-Control: public, max-age=31536000, immutable

# HTML 틀과 스타일과 화면 만드는 코드. 자주 바뀌지 않으나 낡으면 판이 어긋난다.
/*.html
  Cache-Control: no-cache
  X-Content-Type-Options: nosniff
  Referrer-Policy: no-referrer
/app.css
  Cache-Control: no-cache
/app.js
  Cache-Control: no-cache

# 내용. 갱신할 때마다 달라진다. 늘 물어보게 한다.
/data.enc
  Cache-Control: no-cache
  X-Content-Type-Options: nosniff
HDR

# 데이터를 잠근다. 기록 토큰은 이 안에 넣는다.
# 화면 만드는 코드는 잠기지 않은 채 저장소에 그대로 있으므로 거기 적을 수 없다.
if [ -f "$DATA" ]; then
  SEALME="$DATA"
  if [ -n "${LEDGER_TOKEN:-}" ]; then
    SEALME="$WORK/data-with-ledger.json"
    node "$HERE/ledger.js" "$DATA" "$SEALME" "$LEDGER_TOKEN"
  else
    echo "LEDGER_TOKEN 이 없습니다. 판에서 체크와 할 일 추가가 사라집니다."
  fi
  node "$HERE/seal.js" "$SEALME" "$WORK/repo/public/data.enc" "$PASS"
  rm -f "$WORK/data-with-ledger.json"
else
  echo "데이터 파일을 찾지 못했습니다 ($DATA). HTML 틀만 올립니다."
fi

# 아침 메일이 읽는 꾸러미. 보드 암호가 아니라 원본 키로 암호화한다.
# 워커는 사람이 아니므로 반복 계산이 필요 없고, 그래서 푸는 데 1밀리초도 걸리지 않는다.
if [ -f "$SITE/digest.json" ] && [ -n "${DIGEST_KEY:-}" ]; then
  node "$HERE/rawseal.js" "$SITE/digest.json" "$WORK/repo/digest.enc" "$DIGEST_KEY"
elif [ -f "$SITE/digest.json" ]; then
  echo "DIGEST_KEY 가 없어 아침 메일 요약은 올리지 않았습니다."
fi

# 도구와 워커를 저장소에 그대로 옮긴다.
# fetch.sh 가 저장소에서 도구를 받아 쓰므로, 여기서 옮기지 않으면 저장소의
# 도구가 낡은 채로 남는다. 보드는 멀쩡한데 다음 사람이 옛 도구를 받게 된다.
for f in wrangler.jsonc package.json package-lock.json tsconfig.json .gitignore; do
  [ -f "$ROOT/$f" ] && cp "$ROOT/$f" "$WORK/repo/$f" || true
done
[ -f "$ROOT/README.md" ] && cp "$ROOT/README.md" "$WORK/repo/README.md" || true

for d in tools worker; do
  if [ -d "$ROOT/$d" ]; then
    rm -rf "${WORK:?}/repo/$d"
    mkdir -p "$WORK/repo/$d"
    tar cf - -C "$ROOT/$d" --exclude=node_modules --exclude=.wrangler --exclude=.dev.vars . \
      | tar xf - -C "$WORK/repo/$d"
  fi
done

cd "$WORK/repo"
git config user.email "eeruwang@gmail.com"
git config user.name "Il Sun Moon"

git add -A
git commit -q -m "$MSG"
git push -q origin HEAD 2>&1 | sed "s/${TOKEN}/<token>/g" || true
echo "올렸습니다  →  https://loggia.moonilsun.com/"

rm -rf "$WORK"
