# 도구

로지아의 데이터를 풀고 잠그고 올리는 도구들. 비밀은 하나도 들어 있지 않다.
암호와 토큰은 드롭박스 `01. Projects/00. Job Search/board_keys.txt` 에만 있다.

```
fetch.sh        저장소를 받아 public/data.enc 를 풀어 놓는다
build.py        아침 편지 꾸러미와 스냅샷을 낸다. 판은 그리지 않는다
publish.sh      데이터를 잠가 올린다
seal.js         데이터를 AES-256 으로 잠근다
unseal.js       그것을 도로 푼다
ledger.js       장부 열쇠를 데이터에 넣고 뺀다
rawseal.js      아침 편지 꾸러미를 생열쇠로 봉한다
rawunseal.js    그것을 도로 푼다
render-test.js  브라우저 없이 판을 그려 본다
```

판 다섯 장은 여기서 짓지 않는다. 2026년 8월 1일에 브라우저로 옮겼다.
그리는 손은 `../public/app.js` 에, 옷은 `../public/app.css` 에 있다.

## 쓰는 순서

```bash
curl -sO https://raw.githubusercontent.com/eeruwang/loggia/main/tools/fetch.sh
bash fetch.sh "<암호>"            # /tmp/lg 에 도구와 풀린 데이터가 놓인다
cd /tmp/lg
# loggia-data.json 을 고친다
python3 tools/build.py loggia-data.json site/
LEDGER_TOKEN="<장부 열쇠>" DIGEST_KEY="<편지 열쇠>" \
  bash tools/publish.sh site/ "<암호>" "<토큰>" "<커밋 말>"
```

`loggia-data.json` 은 잠긴 채로 이 저장소의 `public/data.enc` 안에 있다.
맨몸으로는 어디에도 두지 않는다. 이 저장소는 공개라서 내용이 드러나기 때문이다.

## 화면을 고칠 때

```bash
node tools/render-test.js loggia-data.json /tmp/new/
```

`app.js` 는 문자열을 짓는 손과 화면을 만지는 손이 나뉘어 있어, 앞의 손만
부르면 노드에서도 돈다. 고친 뒤 그린 것을 글자로 견주고, 휴대전화 너비
390px 에서 눈으로도 본다. 좁은 화면에서 나는 문제는 넓은 화면에서 안 보인다.
