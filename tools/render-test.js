#!/usr/bin/env node
/* =============================================================================
   render-test.js — 브라우저가 그릴 판을 브라우저 없이 뽑아 본다.

     node tools/render-test.js loggia-data.json /tmp/new/

   app.js 는 문자열을 짓는 손과 화면을 만지는 손이 나뉘어 있다. 앞의 손만
   부르면 노드에서도 돈다. 그래서 파이썬이 내던 판과 글자 하나까지 견줄 수
   있다. 옮겨 적은 것이 맞는지 눈으로 짐작하지 않는다.
   ========================================================================== */
const fs = require('fs');
const path = require('path');

const [dataPath, outDir] = process.argv.slice(2);
if (!dataPath || !outDir) {
  console.error('쓰는 법: node tools/render-test.js <데이터> <나올 자리>');
  process.exit(1);
}
const app = require(path.join(__dirname, '..', 'public', 'app.js'));
const D = JSON.parse(fs.readFileSync(dataPath, 'utf8'));
fs.mkdirSync(outDir, { recursive: true });

for (const page of ['index', 'calendar', 'journals', 'materials', 'archive']) {
  const r = app.build(JSON.parse(JSON.stringify(D)), page);
  fs.writeFileSync(path.join(outDir, page + '.html'), r.html);
  console.log('  ' + page + '.html  ' + Math.round(r.html.length / 1024) + 'KB');
}
