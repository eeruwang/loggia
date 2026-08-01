# Loggia

다섯 장의 판이다. 공개된 자리에 놓여 있으나 암호 없이는 아무것도 읽히지 않는다.
올라가는 것은 언제나 암호문이고, 푸는 일은 브라우저 안에서만 일어난다.

```
현황판   index.html      지금 손이 가 있는 것과 남이 답을 줄 것
달력     calendar.html   오늘을 가운데 두고 앞뒤 여섯 달
낼 곳    journals.html   저널과 학회와 레지던시, 색인과 비용과 심사 속도
재료     materials.html  이론가와 개념과 읽기에서 거꾸로 글을 찾는다
지난 일  archive.html    끝난 갈래와 심사평
```

주소는 https://eeruwang.github.io/loggia/ 이다.

## 어떻게 잠기는가

`lock.js` 가 완성된 HTML을 통째로 AES-256-GCM 으로 감싼다.
암호에서 열쇠를 뽑을 때 PBKDF2 를 육십만 번 돌린다.
훔쳐 간 사람이 기계로 두들겨 볼 때 한 번의 시도에 드는 값을 올리기 위해서다.

잠긴 덩이와 암호를 묻는 화면이 한 파일로 묶여 저장소에 올라간다.
암호는 어디에도 들어가지 않는다. 서버로 오가는 것도 없다.

다섯 장은 한 번의 배포에서 같은 소금을 쓴다.
한 장에서 뽑은 열쇠가 그 열림 동안 세션에 남아 나머지 셋을 곧바로 연다.
처음 여는 데 1.5초 남짓, 그다음 장부터는 0.7초 안팎이고 다시 묻지 않는다.
그래서 한 장만 따로 올리는 일은 하지 않는다. 소금이 어긋나면 장마다 다시 물어야 한다.

## 하나뿐인 자리

| 무엇 | 어디 | 규칙 |
| --- | --- | --- |
| 데이터 | 이 저장소의 `data.enc` | 잠긴 채로 있다. 풀어서 고치고 다시 잠가 올린다 |
| 열쇠 | 드롭박스 `01. Projects/00. Job Search/board_keys.txt` | 저장소에는 두지 않는다 |
| 도구 | 이 저장소의 `tools/` | 사본을 만들지 않는다 |
| 결과 | 위 다섯 장 | 데이터와 늘 함께 올린다 |

데이터가 잠긴 채로 여기 있는 까닭은 두 가지다.
하나는 저장소가 공개라 맨몸으로 둘 수 없기 때문이고,
둘은 도구와 같은 자리에 있어야 받아 오는 걸음이 한 번으로 끝나기 때문이다.

암호 하나가 판 다섯 장과 데이터를 모두 연다. 그 암호는 저장소에 없다.

## 갱신하는 순서

```bash
curl -sO https://raw.githubusercontent.com/eeruwang/loggia/main/tools/fetch.sh
bash fetch.sh "<암호>"                 # /tmp/lg 에 도구와 풀린 데이터가 놓인다
cd /tmp/lg
# loggia-data.json 을 고친다
python3 tools/build.py loggia-data.json site/
bash    tools/publish.sh  site/ "<암호>" "<토큰>" "<커밋 말>"
```

마지막 걸음이 다섯 장과 데이터를 함께 잠가 올린다. 되돌려 놓는 일이 따로 없다.
받아 오는 데는 토큰이 필요 없다. 저장소가 공개이기 때문이다. 토큰은 올릴 때만 쓴다.

빚어진 HTML은 손으로 고치지 않는다. 다음 갱신에서 그대로 지워진다.
고칠 곳은 데이터 하나뿐이다.

내용이 그대로면 `publish.sh` 는 아무것도 올리지 않는다.
암호문은 잠글 때마다 달라 보이므로 알맹이의 지문을 `.stamp` 에 남겨 견준다.

눈으로 훑고 싶으면 `build.py` 가 함께 내는 `site/스냅샷.md` 를 본다.
전체를 담은 마크다운이고 저장소에는 올리지 않는다.

클로드에서는 `loggia-status-update` 와 `loggia-journal-update` 스킬이 이 순서를 대신 밟는다.

## 도구

```
fetch.sh     저장소를 받아 데이터를 풀어 놓는다. 갱신의 첫 걸음
build.py     loggia-data.json 을 읽어 다섯 장과 스냅샷을 빚는다
publish.sh   다섯 장과 데이터를 한꺼번에 잠가 올린다

lock.js      한 장을 잠근다.        node lock.js   <in> <out> <암호> [<소금>]
unlock.js    잠긴 장을 도로 푼다.   node unlock.js <in> <out> <암호>
seal.js      데이터를 잠근다.       node seal.js   <in> <out> <암호>
unseal.js    데이터를 푼다.         node unseal.js <in> <out> <암호>
```

`lock` 과 `seal` 은 같은 자물쇠다. 다른 것은 껍데기뿐이다.
`lock` 은 암호를 묻는 화면을 함께 묶어 브라우저가 열 수 있게 하고,
`seal` 은 사람이 열 것이 아니므로 덩이만 남긴다.

`unlock.js` 는 확인용이다. 판이 어긋났다 싶을 때 올라간 것을 그 자리에서 풀어
무엇이 담겼는지, 소금이 같은지 본다.

## 데이터의 뼈대

```
meta          제목과 갱신일과 한 줄 메모
statuses      상태의 어휘. 자유롭게 적지 않고 여기서 고른다
indexKinds    색인의 어휘. 마찬가지로 여기서 고른다
thinkers      이론가의 이름표
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

항목의 `uses` 에 무엇으로 지었는지를 적는다. 재료 장이 이것을 뒤집어 모은다.

```json
"uses": {
  "이론가": ["benjamin", "boehme"],
  "개념":   ["아우라", "매질"],
  "읽기":   ["atmosphere-corpus"]
}
```

이론가는 `thinkers` 에서, 읽기는 `readings` 에서 고른다. 개념은 자유롭게 적되
이미 쓰인 말을 먼저 본다. 같은 것을 두 이름으로 부르면 두 칸으로 갈라진다.

색인 등급은 클래리베이트 MJL 에서만 확인한다. 출판사 페이지는 양방향으로 낡는다.
대조를 마친 곳에는 `"clarivate": true` 를 붙여 어디까지 확인했는지 남긴다.

## 지키는 것

모르는 주소와 날짜는 비워 둔다. 짐작이면 짐작이라고 적는다.
지어낸 값 하나가 판 전체의 믿음을 무너뜨린다.

암호와 토큰은 채팅이나 로그에 적지 않는다.
스크립트에 인자로 넘기고, 남는 출력은 지운다.
