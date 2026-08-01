#!/usr/bin/env node
/* ============================================================================
   seal.js / unseal.js — 데이터 파일을 잠그고 푼다

     node tools/seal.js   loggia-data.json  data.enc  <암호>
     node tools/unseal.js data.enc  loggia-data.json  <암호>

   판을 잠그는 lock.js 와 같은 자물쇠다. AES-256-GCM 에 PBKDF2 육십만 번.
   다른 점은 HTML 틀이 없다는 것뿐이다. lock.js 는 암호를 묻는 화면을 함께 묶지만
   이 파일은 사람이 브라우저로 열 것이 아니므로 암호문만 남긴다.

   형식은 한 줄이다.  loggia1.<솔트>.<초기값>.<덩이>   모두 base64.
   ========================================================================== */
const fs = require('fs');
const crypto = require('crypto');

const ITER = 600000;
const [inFile, outFile, pass] = process.argv.slice(2);
if (!inFile || !outFile || !pass) {
  console.error('쓰는 법: node tools/seal.js <들어갈 파일> <나올 파일> <암호>');
  process.exit(1);
}

const plain = fs.readFileSync(inFile);
const salt = crypto.randomBytes(16);
const iv = crypto.randomBytes(12);
const key = crypto.pbkdf2Sync(pass, salt, ITER, 32, 'sha256');
const c = crypto.createCipheriv('aes-256-gcm', key, iv);
const body = Buffer.concat([c.update(plain), c.final()]);
const blob = Buffer.concat([body, c.getAuthTag()]);

fs.writeFileSync(outFile, ['loggia1', salt.toString('base64'), iv.toString('base64'),
                           blob.toString('base64')].join('.') + '\n');
console.error(`잠갔습니다  ${inFile} (${plain.length}B) → ${outFile}`);
