#!/usr/bin/env node
/* =============================================================================
   ledger.js — 데이터에 장부 열쇠를 넣거나 뺀다.

     node tools/ledger.js <들어갈 파일> <나올 파일> [<열쇠>]

   열쇠를 주면 `meta.ledger` 에 넣고, 주지 않으면 뺀다.

   왜 데이터 안에 넣는가.
     옛적에는 판을 파이썬이 그렸고 그린 판을 통째로 잠갔으므로, 열쇠를 판
     안에 적어 두어도 함께 잠겼다. 이제 그리는 손(app.js)은 잠기지 않은 채
     저장소에 그대로 있다. 거기 적으면 누구나 읽는다.
     잠기는 것은 data.enc 하나뿐이므로, 열쇠도 그 안에 들어가야 한다.

   글자 사이 띄움은 한 칸이다. 원본과 같은 꼴로 다시 쓰므로, 넣었다 뺐다
   해도 파일이 달라 보이지 않는다.
   ========================================================================== */
const fs = require('fs');

const [inFile, outFile, token] = process.argv.slice(2);
if (!inFile || !outFile) {
  console.error('쓰는 법: node tools/ledger.js <들어갈 파일> <나올 파일> [<열쇠>]');
  process.exit(1);
}

const d = JSON.parse(fs.readFileSync(inFile, 'utf8'));
d.meta = d.meta || {};
if (token) d.meta.ledger = token;
else delete d.meta.ledger;
fs.writeFileSync(outFile, JSON.stringify(d, null, 1));
