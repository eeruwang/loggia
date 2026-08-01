# Loggia

다섯 장의 판이다. 공개된 자리에 놓여 있으나 암호 없이는 아무것도 읽히지 않는다.
올라가는 것은 언제나 암호문이고, 푸는 일도 그리는 일도 브라우저 안에서만 일어난다.

```
현황판   index.html      지금 손이 가 있는 것과 남이 답을 줄 것
달력     calendar.html   오늘을 가운데 두고 앞뒤 여섯 달
낼 곳    journals.html   저널과 학회와 레지던시, 색인과 비용과 심사 속도
재료     materials.html  이론가와 개념과 읽기에서 거꾸로 글을 찾는다
지난 일  archive.html    끝난 갈래와 심사평
```

주소는 https://loggia.moonilsun.com/ 이다. 클라우드플레어 워커가 내준다.

## 어떻게 잠기는가

잠기는 것은 `public/data.enc` 하나뿐이다. `seal.js` 가 데이터를 통째로
AES-256-GCM 으로 감싼다. 암호에서 열쇠를 뽑을 때 PBKDF2 를 육십만 번 돌린다.
훔쳐 간 사람이 기계로 두들겨 볼 때 한 번의 시도에 드는 값을 올리기 위해서다.

껍데기 다섯 장과 옷(`app.css`)과 그리는 손(`app.js`)은 잠기지 않는다.
거기에는 비밀이 없다. 무엇을 어떻게 그리는지가 적혀 있을 뿐이다.
암호는 어디에도 들어가지 않고, 서버로 오가는 것도 없다.

암호를 넣으면 브라우저가 `data.enc` 를 받아 그 자리에서 풀고 화면을 그린다.
뽑은 열쇠는 그 열림 동안 세션에 남으므로, 다음 장은 다시 묻지 않고 곧바로 열린다.
처음 여는 데 1.5초 남짓, 그다음 장부터는 눈에 띄지 않는다.

2026년 8월 1일 저녁까지는 파이썬이 판 다섯 장을 미리 그려 각각 잠갔다.
잠근 덩이는 갱신할 때마다 처음부터 끝까지 달라 보이므로, 글자 하나를 고쳐도
368KB가 저장소에 새로 쌓였다. 커밋 아흔에 12MB였다. 그리는 일을 브라우저로
옮기면서 갱신 한 번에 바뀌는 것이 47KB 하나가 되었다. 여덟 분의 일이다.
소금을 다섯 장이 나눠 쓰던 셈도 함께 없어졌다. 소금은 이제 하나뿐이다.

## 하나뿐인 자리

| 무엇 | 어디 | 규칙 |
| --- | --- | --- |
| 데이터 | 이 저장소의 `public/data.enc` | 잠긴 채로 있다. 풀어서 고치고 다시 잠가 올린다 |
| 열쇠 | 드롭박스 `01. Projects/00. Job Search/board_keys.txt` | 저장소에는 두지 않는다 |
| 도구 | 이 저장소의 `tools/` | 사본을 만들지 않는다 |
| 껍데기 | 이 저장소의 `public/` | 내용이 바뀔 때에만 바뀐다 |

데이터가 잠긴 채로 여기 있는 까닭은 두 가지다.
하나는 저장소가 공개라 맨몸으로 둘 수 없기 때문이고,
둘은 도구와 같은 자리에 있어야 받아 오는 걸음이 한 번으로 끝나기 때문이다.

암호 하나가 데이터를 열고, 열린 데이터가 판 다섯 장이 된다. 그 암호는 저장소에 없다.

## 갱신하는 순서

```bash
curl -sO https://raw.githubusercontent.com/eeruwang/loggia/main/tools/fetch.sh
bash fetch.sh "<암호>"                 # /tmp/lg 에 도구와 풀린 데이터가 놓인다
cd /tmp/lg
LEDGER_TOKEN="<장부 열쇠>" python3 tools/ledger-apply.py -w   # 판에서 하신 것을 옮긴다
python3 tools/lg.py show glasgow                              # 지금 상태를 본다
python3 tools/lg.py step-done glasgow "추천인" -w             # 고친다
python3 tools/build.py loggia-data.json site/
LEDGER_TOKEN="<장부 열쇠>" DIGEST_KEY="<편지 열쇠>" \
  bash tools/publish.sh site/ "<암호>" "<토큰>" "<커밋 말>"
```

`build.py` 는 이제 판을 그리지 않는다. 아침 편지가 읽는 꾸러미와 눈으로 훑는
스냅샷 둘만 낸다. 판은 브라우저가 그린다.

받아 오는 데는 토큰이 필요 없다. 저장소가 공개이기 때문이다. 토큰은 올릴 때만 쓴다.
`LEDGER_TOKEN` 은 잠기는 데이터 안에 들어간다. 빠뜨리면 판에서 체크와 할 일
추가가 사라진다.

고칠 곳은 데이터 하나뿐이다. 손으로 열지 않고 `lg.py` 로 한 자리씩 집어 고친다.
그 둘은 아무것도 안 붙이면 무엇이 바뀔지 보여만 주고 멈춘다. 넣으려면 `-w`.

화면을 고칠 일이면 `public/app.js` 와 `public/app.css` 둘이고,
껍데기 다섯 장은 거의 손댈 일이 없다.

내용이 그대로면 `publish.sh` 는 아무것도 올리지 않는다.
암호문은 잠글 때마다 달라 보이므로 알맹이의 지문을 `.stamp` 에 남겨 견준다.

눈으로 훑고 싶으면 `build.py` 가 내는 `site/스냅샷.md` 를 본다.
전체를 담은 마크다운이고 저장소에는 올리지 않는다.

클로드에서는 `loggia-update` 스킬이 이 순서를 대신 밟는다.

## 도구

```
fetch.sh        저장소를 받아 데이터를 풀어 놓는다. 갱신의 첫 걸음
lg.py           데이터의 한 자리만 집어서 보고 고친다. 갱신의 손
ledger-apply.py 판에서 손으로 한 것을 데이터로 옮긴다
build.py        아침 편지 꾸러미와 스냅샷을 낸다. 판은 그리지 않는다
publish.sh      데이터를 잠가 올린다

seal.js         데이터를 잠근다.       node seal.js    <in> <out> <암호>
unseal.js       데이터를 푼다.         node unseal.js  <in> <out> <암호>
ledger.js       장부 열쇠를 넣고 뺀다. node ledger.js  <in> <out> [<열쇠>]
rawseal.js      아침 편지 꾸러미를 봉한다. 생열쇠로 봉하므로 늘일 것이 없다
rawunseal.js    그것을 도로 푼다

render-test.js  브라우저 없이 판을 그려 본다.
                node render-test.js loggia-data.json /tmp/new/
```

`render-test.js` 는 확인용이다. `app.js` 는 문자열을 짓는 손과 화면을 만지는
손이 나뉘어 있어, 앞의 손만 부르면 노드에서도 돈다. 옮겨 적은 것이 맞는지
눈으로 짐작하지 않고 글자로 견준다.

## 데이터의 뼈대

```
meta          제목과 갱신일과 한 줄 메모
statuses      상태의 어휘. 자유롭게 적지 않고 여기서 고른다
indexKinds    색인의 어휘. 마찬가지로 여기서 고른다
thinkers      이론가의 이름표와 찾을 말
readings      읽기 묶음. 파일 하나가 아니라 한 뭉치를 가리킨다
sections[]    now(진행 중)와 waiting(결과 기다리는 중)
  items[]     id, title, venue, kind, status, dates, next, note, uses, chats[], links[]
compass       연구 지형도
archive[]     끝난 갈래. review 에 심사평이 붙는다
venueGroups[] 낼 곳의 무리
  venues[]    id, name, sub, type, url, indexes[], flag, deadline, cost, review, note
watch[]       공모를 지켜보는 자리
memo[]        기억해 둘 것
```

`items` 의 `venue` 값이 `venues` 의 `id` 를 가리키면
낼 곳 장에서 그 처 아래로 무엇을 냈는지가 저절로 모인다. 두 번 적지 않는다.

날짜는 `dates` 안에 `deadline`, `sent`, `decided` 셋이다.
마감이 있으면 현황판에 D-가 뜨고 달력에 찍힌다.

색인은 `indexKinds` 의 열쇠말로만 적는다.
`ahci` `ssci` `scie` `esci` `scopus` `kci` `kcic` `erih` `doaj` `none` 열이다.
앞에 빼기표를 붙이면 미등재를 뜻한다.

```json
"indexes": ["ahci", "scopus"]
"indexes": ["scopus", "-ahci"]
```

이론가는 손으로 적지 않는다. `thinkers` 의 `말` 에 이름을 적어 두면
그리는 손이 항목의 제목과 메모와 다음 걸음에서 그 이름을 찾아 잇는다.
이론가를 나중에 더하면 이미 쌓인 메모를 거슬러 훑어 예전 항목도 그때 걸린다.

`말` 에는 사람 이름만 적는다. 학파나 개념 이름을 넣으면 잘못 걸린다.

메모에 이름이 없는데 실제로 쓰는 경우에만 `uses.이론가` 에 적는다.
개념과 읽기는 손으로 적는다. 개념은 부정문이나 딴 뜻으로 스치는 일이 잦아
저절로 걸리게 하지 않았다.

```json
"uses": {
  "개념": ["아우라", "매질"],
  "읽기": ["atmosphere-corpus"]
}
```

색인 등급은 클래리베이트 MJL 에서만 확인한다. 출판사 페이지는 양방향으로 낡는다.
대조를 마친 곳에는 `"clarivate": true` 를 붙여 어디까지 확인했는지 남긴다.

## 지키는 것

모르는 주소와 날짜는 비워 둔다. 짐작이면 짐작이라고 적는다.
지어낸 값 하나가 판 전체의 믿음을 무너뜨린다.

암호와 토큰은 채팅이나 로그에 적지 않는다.
스크립트에 인자로 넘기고, 남는 출력은 지운다.
