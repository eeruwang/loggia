# Loggia

네 장의 판이다. 공개된 자리에 놓여 있으나 암호 없이는 아무것도 읽히지 않는다.
올라가는 것은 언제나 암호문이고, 푸는 일은 브라우저 안에서만 일어난다.

```
현황판   index.html      지금 손이 가 있는 것과 남이 답을 줄 것
달력     calendar.html   오늘을 가운데 두고 앞뒤 여섯 달
낼 곳    journals.html   저널과 학회와 레지던시, 색인과 비용과 심사 속도
지난 일  archive.html    끝난 갈래와 심사평
```

주소는 https://eeruwang.github.io/loggia/ 이다.

## 어떻게 잠기는가

`lock.js` 가 완성된 HTML을 통째로 AES-256-GCM 으로 감싼다.
암호에서 열쇠를 뽑을 때 PBKDF2 를 육십만 번 돌린다.
훔쳐 간 사람이 기계로 두들겨 볼 때 한 번의 시도에 드는 값을 올리기 위해서다.

잠긴 덩이와 암호를 묻는 화면이 한 파일로 묶여 저장소에 올라간다.
암호는 어디에도 들어가지 않는다. 서버로 오가는 것도 없다.

네 장은 한 번의 배포에서 같은 소금을 쓴다.
한 장에서 뽑은 열쇠가 그 열림 동안 세션에 남아 나머지 셋을 곧바로 연다.
처음 여는 데 1.5초 남짓, 그다음 장부터는 0.7초 안팎이고 다시 묻지 않는다.
그래서 한 장만 따로 올리는 일은 하지 않는다. 소금이 어긋나면 장마다 다시 물어야 한다.

## 하나뿐인 자리

| 무엇 | 어디 | 규칙 |
| --- | --- | --- |
| 데이터 | 드롭박스 `01. Projects/00. Job Search/loggia-data.json` | 손대는 것은 이 파일뿐 |
| 열쇠 | 같은 폴더 `board_keys.txt` | 저장소에는 두지 않는다 |
| 도구 | 이 저장소의 `tools/` | 사본을 만들지 않는다 |
| 결과 | 위 네 장 | 늘 함께 올린다 |

데이터가 저장소에 없는 까닭은 이곳이 공개이기 때문이다.
내용은 잠긴 채로만 이 자리에 놓인다.

## 갱신하는 순서

```bash
git clone https://github.com/eeruwang/loggia.git
# 드롭박스에서 loggia-data.json 을 받아 고친다
python3 loggia/tools/build.py loggia-data.json site/
bash    loggia/tools/publish.sh site/ "<암호>" "<토큰>" "<커밋 말>"
# 고친 데이터를 드롭박스에 되돌려 놓는다
```

빚어진 HTML은 손으로 고치지 않는다. 다음 갱신에서 그대로 지워진다.
고칠 곳은 데이터 하나뿐이다.

클로드에서는 `loggia-status-update` 와 `loggia-journal-update` 스킬이 이 순서를 대신 밟는다.

## 도구

```
build.py     loggia-data.json 을 읽어 네 장을 빚는다
lock.js      한 장을 잠근다.        node lock.js <in> <out> <암호> [<소금>]
unlock.js    잠긴 장을 도로 푼다.   node unlock.js <in> <out> <암호>
publish.sh   네 장을 한 소금으로 잠가 한 번에 올린다
```

`unlock.js` 는 확인용이다. 판이 어긋났다 싶을 때 올라간 것을 그 자리에서 풀어
무엇이 담겼는지, 소금이 같은지 본다.

## 데이터의 뼈대

```
meta          제목과 갱신일과 한 줄 메모
statuses      상태의 어휘. 자유롭게 적지 않고 여기서 고른다
sections[]    now(진행 중)와 waiting(결과 기다리는 중)
  items[]     id, title, venue, kind, status, dates, next, note, chats[], links[]
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

## 지키는 것

모르는 주소와 날짜는 비워 둔다. 짐작이면 짐작이라고 적는다.
지어낸 값 하나가 판 전체의 믿음을 무너뜨린다.

암호와 토큰은 채팅이나 로그에 적지 않는다.
스크립트에 인자로 넘기고, 남는 출력은 지운다.
