#!/usr/bin/env bash
# =============================================================================
# publish.sh — 다섯 장과 데이터를 한꺼번에 잠가 올린다
#
#   bash publish.sh <site 폴더> <암호> <토큰> [<커밋 말>] [<데이터 파일>]
#
#   보기
#     DIGEST_KEY="$DKEY" bash publish.sh site/ "$PASS" "$TOKEN" "ARKO 마감 바뀜"
#
# DIGEST_KEY 는 아침 편지를 위한 다른 열쇠다. board_keys.txt 에 있다.
# 주면 digest.enc 도 함께 올라간다. 주지 않으면 그것만 건너뛴다.
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
ROOT="$(cd "$HERE/.." && pwd)"

# 도구와 워커도 지문에 넣는다. 넣지 않으면 빌더를 고쳐도 판이 그대로일 때
# 「바뀐 것이 없습니다」라며 고친 도구를 올리지 않는다. 그러면 저장소의
# 도구가 조용히 낡고, 다음 사람이 받아 쓰는 것이 옛 도구가 된다.
tree_hash() {
  local d="$1"
  [ -d "$d" ] || return 0
  find "$d" -type f \
       -not -path '*/node_modules/*' -not -path '*/.wrangler/*' \
    | LC_ALL=C sort | while read -r f; do printf '%s\n' "$f"; cat "$f"; done
}

STAMP="$( { for f in index calendar journals materials archive; do
             [ -f "$SITE/$f.html" ] && cat "$SITE/$f.html"
           done
           [ -f "$DATA" ] && cat "$DATA"
           [ -f "$SITE/digest.json" ] && cat "$SITE/digest.json"
           tree_hash "$ROOT/tools"
           tree_hash "$ROOT/worker"
           for f in wrangler.jsonc package.json package-lock.json tsconfig.json .gitignore; do
             [ -f "$ROOT/$f" ] && cat "$ROOT/$f"
           done
         } | sha256sum | cut -d' ' -f1 )"
if [ -f "$WORK/repo/.stamp" ] && [ "$(cat "$WORK/repo/.stamp")" = "$STAMP" ]; then
  echo "바뀐 것이 없습니다. 올리지 않았습니다."
  rm -rf "$WORK"; exit 0
fi
echo "$STAMP" > "$WORK/repo/.stamp"

# ── 클라우드플레어가 내주는 자리 ────────────────────────────────────────────
# 워커의 assets 는 public/ 하나만 본다. 저장소 뿌리를 통째로 내주면 도구와
# 데이터까지 딸려 나가므로, 내줄 것만 여기 모은다.
mkdir -p "$WORK/repo/public"
for f in index calendar journals materials archive; do
  if [ -f "$SITE/$f.html" ]; then
    node "$HERE/lock.js" "$SITE/$f.html" "$WORK/repo/public/$f.html" "$PASS" "$SALT"
  fi
done

# 글꼴은 public/ 이 제자리다. 옛 자리에 남아 있으면 옮긴다.
if [ -d "$WORK/repo/font" ] && [ ! -d "$WORK/repo/public/font" ]; then
  cp -r "$WORK/repo/font" "$WORK/repo/public/font"
fi

# 깃허브 페이지 시절의 자취를 치운다. 2026년 8월 1일에 클라우드플레어로 옮겼다.
# 두 자리에 같은 판이 있으면 언젠가 한쪽이 낡는다. 그것이 이 판을 한 번 갈라놓았다.
rm -rf "$WORK/repo/font"
rm -f "$WORK/repo/CNAME" "$WORK/repo/.nojekyll"
for f in index calendar journals materials archive; do
  rm -f "$WORK/repo/$f.html"
done

# 글꼴은 한 번 받으면 바뀌지 않는다. 판은 갱신될 때마다 달라진다.
# 이 파일은 내주지 않고 규칙으로만 읽힌다.
cat > "$WORK/repo/public/_headers" <<'HDR'
# 글꼴은 이름에 내용이 박혀 있지 않으나 바뀌지 않는다. 한 해를 재운다.
/font/*
  Cache-Control: public, max-age=31536000, immutable

# 판은 갱신될 때마다 달라진다. 늘 물어보게 한다.
/*.html
  Cache-Control: no-cache
  X-Content-Type-Options: nosniff
  Referrer-Policy: no-referrer
HDR

if [ -f "$DATA" ]; then
  node "$HERE/seal.js" "$DATA" "$WORK/repo/data.enc" "$PASS"
else
  echo "데이터 파일을 찾지 못했습니다 ($DATA). 판만 올립니다."
fi

# 아침 편지가 읽는 꾸러미. 판의 암호가 아니라 생열쇠로 봉한다.
# 워커는 사람이 아니므로 늘일 것이 없고, 그래서 푸는 데 일 밀리초도 들지 않는다.
# DIGEST_KEY 를 주지 않으면 그냥 건너뛴다. 판은 그것 없이도 온전하다.
if [ -f "$SITE/digest.json" ] && [ -n "${DIGEST_KEY:-}" ]; then
  node "$HERE/rawseal.js" "$SITE/digest.json" "$WORK/repo/digest.enc" "$DIGEST_KEY"
elif [ -f "$SITE/digest.json" ]; then
  echo "DIGEST_KEY 가 없어 아침 편지 꾸러미는 올리지 않았습니다."
fi

# 도구와 워커를 저장소에 그대로 옮긴다.
# fetch.sh 가 저장소에서 도구를 받아 쓰므로, 여기서 옮기지 않으면 저장소의
# 도구가 낡은 채로 남는다. 판은 멀쩡한데 다음 사람이 옛 빌더를 받게 된다.
for f in wrangler.jsonc package.json package-lock.json tsconfig.json .gitignore; do
  [ -f "$ROOT/$f" ] && cp "$ROOT/$f" "$WORK/repo/$f"
done

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
