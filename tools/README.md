# 도구

로지아 데이터를 풀고, 고치고, 암호화해서 올리는 도구들.
비밀은 하나도 들어 있지 않다.
암호와 토큰은 드롭박스 `01. Projects/00. Job Search/board_keys.txt` 에만 있다.

```
fetch.sh          저장소를 받아 public/data.enc 를 풀어 놓는다
lg.py             데이터를 한 항목씩 보고 고친다
ledger-apply.py   사이트에서 직접 체크하거나 추가한 것을 데이터에 반영한다
build.py          아침 메일 요약과 스냅샷을 만든다. 화면은 만들지 않는다
publish.sh        데이터를 암호화해 올린다

seal.js           데이터를 AES-256 으로 암호화한다
unseal.js         다시 푼다
ledger.js         장부 토큰을 데이터에 넣고 뺀다
rawseal.js        아침 메일 요약을 원본 키로 암호화한다
rawunseal.js      다시 푼다
render-test.js    브라우저 없이 화면을 만들어 본다
```

`lg.py` 와 `ledger-apply.py` 는 `-w` 를 붙여야 저장된다.
안 붙이면 바뀔 내용만 보여주고 멈춘다.

```bash
python3 tools/lg.py                    # 사용법 전체
python3 tools/lg.py show glasgow       # 그 항목만 간추려 보기
python3 tools/lg.py done glasgow "추천인" -w
```

화면은 여기서 만들지 않는다. 2026년 8월 1일에 브라우저로 옮겼다.
화면 만드는 코드는 `../public/app.js` 에, 스타일은 `../public/app.css` 에 있다.

## 사용 순서

```bash
curl -sO https://raw.githubusercontent.com/eeruwang/loggia/main/tools/fetch.sh
bash fetch.sh "<암호>"            # /tmp/lg 에 도구와 풀린 데이터가 놓인다
cd /tmp/lg

LEDGER_TOKEN="<장부토큰>" python3 tools/ledger-apply.py -w   # 사이트에서 한 것 반영
python3 tools/lg.py show                                     # 전체 확인
python3 tools/lg.py set glasgow status 제출 -w               # 고치기

python3 tools/build.py loggia-data.json site/
LEDGER_TOKEN="<장부토큰>" DIGEST_KEY="<메일키>" \
  bash tools/publish.sh site/ "<암호>" "<토큰>" "<커밋 메시지>"

LEDGER_TOKEN="<장부토큰>" python3 tools/ledger-apply.py --clear   # 올린 다음에 비우기
```

`loggia-data.json` 은 암호화된 상태로 이 저장소의 `public/data.enc` 안에 있다.
암호화하지 않은 상태로는 어디에도 두지 않는다. 이 저장소는 공개라서 내용이 드러난다.

## 화면을 고칠 때

```bash
node tools/render-test.js loggia-data.json /tmp/new/
```

`app.js` 는 문자열을 만드는 부분과 DOM을 만지는 부분이 나뉘어 있어서, 앞부분만
부르면 노드에서도 돈다. 고친 다음 만들어진 HTML을 텍스트로 비교하고, 휴대전화
너비 390px 에서 눈으로도 확인한다. 좁은 화면에서 생기는 문제는 넓은 화면에서
안 보인다.
