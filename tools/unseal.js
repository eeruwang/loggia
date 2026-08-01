#!/usr/bin/env node
/* unseal.js — seal.js 로 잠근 데이터를 푼다
     node tools/unseal.js data.enc loggia-data.json <암호>                    */
const fs = require('fs');
const crypto = require('crypto');

const [inFile, outFile, pass] = process.argv.slice(2);
if (!inFile || !outFile || !pass) {
  console.error('쓰는 법: node tools/unseal.js <들어갈 파일> <나올 파일> <암호>');
  process.exit(1);
}

const parts = fs.readFileSync(inFile, 'utf8').trim().split('.');
if (parts[0] !== 'loggia1' || parts.length !== 4) {
  console.error('알아볼 수 없는 꼴입니다. loggia1.<소금>.<초기값>.<덩이> 여야 합니다.');
  process.exit(1);
}
const [, s, i, c] = parts;
const salt = Buffer.from(s, 'base64');
const iv = Buffer.from(i, 'base64');
const all = Buffer.from(c, 'base64');
const key = crypto.pbkdf2Sync(pass, salt, 600000, 32, 'sha256');

const d = crypto.createDecipheriv('aes-256-gcm', key, iv);
d.setAuthTag(all.subarray(all.length - 16));
let plain;
try {
  plain = Buffer.concat([d.update(all.subarray(0, all.length - 16)), d.final()]);
} catch (e) {
  console.error('암호가 맞지 않거나 파일이 상했습니다.');
  process.exit(1);
}
fs.writeFileSync(outFile, plain);
console.error(`풀었습니다  ${inFile} → ${outFile} (${plain.length}B)`);
