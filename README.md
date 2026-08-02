# Loggia

페이지 다섯 개짜리 개인 연구 보드다. 공개된 저장소에 있지만 암호 없이는
아무것도 읽히지 않는다. 올라가는 건 언제나 암호문이고, 푸는 것도 화면을
만드는 것도 브라우저 안에서만 일어난다.

```
현황판   index.html      지금 작업 중인 것과 상대의 답을 기다리는 것
달력     calendar.html   오늘을 가운데 두고 앞뒤 여섯 달
낼 곳    journals.html   저널·학회·레지던시, 색인과 비용과 심사 속도
재료     materials.html  이론가와 개념과 읽기에서 거꾸로 글을 찾는다
지난 일  archive.html    끝난 항목과 심사평
```

주소는 https://loggia.moonilsun.com/ 이다. 클라우드플레어 워커가 서빙한다.

## 어떻게 잠기는가

암호화되는 건 `public/data.enc` 하나뿐이다. `seal.js` 가 데이터 전체를
AES-256-GCM 으로 감싼다. 암호에서 키를 만들 때 PBKDF2 를 60만 번 돌린다.
무차별 대입을 시도할 때 한 번의 비용을 올리기 위해서다.

HTML 다섯 개와 `app.css` 와 `app.js` 는 암호화하지 않는다. 거기엔 비밀이 없다.
무엇을 어떻게 그리는지가 적혀 있을 뿐이다. 암호는 어디에도 들어가지 않고
서버로 오가는 것도 없다.

암호를 넣으면 브라우저가 `data.enc` 를 받아 그 자리에서 풀고 화면을 만든다.
만들어진 키는 세션에 남으므로 다음 페이지는 다시 묻지 않고 바로 열린다.
처음 여는 데 1.5초 남짓, 그다음부터는 눈에 띄지 않는다.

2026년 8월 1일 저녁까지는 파이썬이 다섯 페이지를 미리 만들어 각각 암호화했다.
암호화된 파일은 갱신할 때마다 처음부터 끝까지 달라 보이므로, 글자 하나를 고쳐도
368KB가 저장소에 새로 쌓였다. 커밋 90개에 12MB였다. 화면 만드는 일을 브라우저로
옮기면서 갱신 한 번에 바뀌는 게 47KB 하나가 되었다. 8분의 1이다.
페이지마다 솔트가 달라서 생기던 문제도 함께 없어졌다. 솔트는 이제 하나뿐이다.

## 위치

| 무엇 | 어디 | 규칙 |
| --- | --- | --- |
| 데이터 | 이 저장소의 `public/data.enc` | 암호화된 상태로 있다. 풀어서 고치고 다시 암호화해 올린다 |
| 암호와 토큰 | 드롭박스 `01. Projects/00. Job Search/board_keys.txt` | 저장소에는 두지 않는다 |
| 도구 | 이 저장소의 `tools/` | 복사본을 만들지 않는다 |
| HTML과 스타일 | 이 저장소의 `public/` | 화면을 고칠 때만 바뀐다 |

데이터를 암호화된 채로 여기 두는 이유는 두 가지다. 저장소가 공개라서 그대로
둘 수 없고, 도구와 같은 곳에 있어야 받아 오는 게 한 번에 끝나기 때문이다.

암호 하나가 데이터를 열고, 열린 데이터가 다섯 페이지가 된다. 그 암호는 저장소에 없다.

## 갱신하는 순서

```bash
curl -sO https://raw.githubusercontent.com/eeruwang/loggia/main/tools/fetch.sh
bash fetch.sh "<암호>"                 # /tmp/lg 에 도구와 풀린 데이터가 놓인다
cd /tmp/lg

# 사이트에서 직접 체크하거나 추가한 것을 먼저 반영한다
LEDGER_TOKEN="<장부토큰>" python3 tools/ledger-apply.py -w

# 데이터를 고친다
python3 tools/lg.py show glasgow
python3 tools/lg.py done glasgow "추천인" -w

python3 tools/build.py loggia-data.json site/
LEDGER_TOKEN="<장부토큰>" DIGEST_KEY="<메일키>" \
  bash tools/publish.sh site/ "<암호>" "<토큰>" "<커밋 메시지>"

# 올린 다음에 기록을 비운다
LEDGER_TOKEN="<장부토큰>" python3 tools/ledger-apply.py --clear
```

`build.py` 는 이제 화면을 만들지 않는다. 아침 메일이 읽는 요약과 눈으로 보는
스냅샷 두 가지만 만든다. 화면은 브라우저가 만든다.

받아 오는 데는 토큰이 필요 없다. 저장소가 공개라서다. 토큰은 올릴 때만 쓴다.
`LEDGER_TOKEN` 은 암호화되는 데이터 안에 들어간다. 빠뜨리면 사이트에서 체크와
할 일 추가 기능이 사라진다.

데이터는 직접 열지 않고 `lg.py` 로 한 항목씩 고친다. `lg.py` 와 `ledger-apply.py`
둘 다 `-w` 를 붙여야 저장된다. 안 붙이면 바뀔 내용만 보여준다.

화면을 고칠 일이면 `public/app.js` 와 `public/app.css` 두 개다.
HTML 다섯 개는 거의 손댈 일이 없다.

내용이 그대로면 `publish.sh` 는 아무것도 올리지 않는다. 암호문은 암호화할 때마다
달라 보이므로 내용의 해시를 `.stamp` 에 남겨 비교한다.

전체를 훑어보고 싶으면 `build.py` 가 만드는 `site/스냅샷.md` 를 본다.
저장소에는 올리지 않는다.

클로드에서는 `loggia-update` 스킬이 이 순서를 대신 밟는다.

## 도구

```
fetch.sh        저장소를 받아 데이터를 풀어 놓는다. 갱신의 첫 단계
lg.py           데이터를 한 항목씩 보고 고친다
ledger-apply.py 사이트에서 직접 체크하거나 추가한 것을 데이터에 반영한다
build.py        아침 메일 요약과 스냅샷을 만든다. 화면은 만들지 않는다
publish.sh      데이터를 암호화해 올린다

seal.js         데이터를 암호화한다.   node seal.js    <in> <out> <암호> [<솔트>]
pagekey.js      워커에 넣을 키를 뽑는다. node pagekey.js <data.enc> <암호>
unseal.js       다시 푼다.             node unseal.js  <in> <out> <암호>
ledger.js       장부 토큰을 넣고 뺀다. node ledger.js  <in> <out> [<토큰>]
rawseal.js      아침 메일 요약을 암호화한다. 원본 키를 쓰므로 PBKDF2 를 돌리지 않는다
rawunseal.js    다시 푼다

render-test.js  브라우저 없이 화면을 만들어 본다.
                node render-test.js loggia-data.json /tmp/new/
```

`render-test.js` 는 확인용이다. `app.js` 는 문자열을 만드는 부분과 DOM을 만지는
부분이 나뉘어 있어서, 앞부분만 부르면 노드에서도 돈다. 옮긴 코드가 맞는지
눈으로 짐작하지 않고 텍스트로 비교한다.

## 데이터 구조

```
meta          제목과 갱신일과 한 줄 메모
statuses      상태 목록. 임의로 적지 않고 여기서 고른다
indexKinds    색인 목록. 마찬가지
thinkers      이론가 이름과 검색어
readings      읽기 묶음. 파일 하나가 아니라 한 뭉치를 가리킨다
sections[]    now 진행 중, waiting 보낸 것, later 아직 안 한 것
  items[]     id, title, venue, kind, status, dates, steps, note, uses, chats[], links[]
compass       연구 지형도
decisions[]   결정 기록
reuse[]       재사용할 문서
people[]      사람
repeats[]     반복 일정
archive[]     끝난 항목. review 에 심사평
venueGroups[] 낼 곳 그룹
  venues[]    id, name, sub, type, url, indexes[], flag, deadline, 비용, review, 답까지, note
watch[]       공모를 지켜보는 곳
memo[]        기억해 둘 것
```

`items` 의 `venue` 값이 `venues` 의 `id` 를 가리키면, 낼 곳 페이지에서 그 저널
아래에 무엇을 냈는지가 자동으로 모인다. 두 번 적지 않는다.

날짜는 `dates` 안에 `deadline`, `sent`, `decided` 세 가지다.
마감이 있으면 현황판에 D-day 가 뜨고 달력에 표시된다.

색인은 `indexKinds` 의 키로만 적는다.
`ahci` `ssci` `scie` `esci` `scopus` `kci` `kcic` `erih` `doaj` `none` 열 가지다.
앞에 빼기표를 붙이면 미등재라는 뜻이다.

```json
"indexes": ["ahci", "scopus"]
"indexes": ["scopus", "-ahci"]
```

이론가는 직접 적지 않는다. `thinkers` 의 `말` 에 이름을 적어 두면 화면 만드는
코드가 항목의 제목과 메모와 할 일에서 그 이름을 찾아 연결한다. 이론가를 나중에
추가하면 이미 쌓인 메모를 거슬러 훑어서 예전 항목도 그때 걸린다.

`말` 에는 사람 이름만 적는다. 학파나 개념 이름을 넣으면 잘못 걸린다.

메모에 이름이 없는데 실제로 참고한 경우에만 `uses.이론가` 에 적는다.
개념과 읽기는 직접 적는다. 개념은 부정문이나 다른 뜻으로 스치는 일이 많아서
자동으로 걸리게 하지 않았다.

```json
"uses": {
  "개념": ["아우라", "매질"],
  "읽기": ["atmosphere-corpus"]
}
```

색인 등급은 클래리베이트 MJL 에서만 확인한다. 출판사 페이지는 오래된 경우가 많다.
확인을 마친 곳에는 `"clarivate": true` 를 붙여 어디까지 확인했는지 남긴다.

## 지키는 것

모르는 주소와 날짜는 비워 둔다. 추측이면 추측이라고 적는다.
지어낸 값 하나가 보드 전체의 신뢰를 무너뜨린다.

암호와 토큰은 대화나 로그에 적지 않는다.
스크립트에 인자로 넘기고, 남는 출력은 지운다.
