#!/usr/bin/env node
// =============================================================================
// rawunseal.js — rawseal.js 가 봉한 것을 푼다. 확인할 때 쓴다.
//
//   node rawunseal.js <봉한 파일> <나올 파일> <열쇠 base64>
// =============================================================================
const fs = require('fs');
const crypto = require('crypto');

const [, , src, dst, keyB64] = process.argv;
if (!src || !dst || !keyB64) {
  console.error('쓰임  node rawunseal.js <봉한 파일> <나올 파일> <열쇠 base64>');
  process.exit(1);
}

const parts = fs.readFileSync(src, 'utf8').trim().split('.');
if (parts[0] !== 'loggiaR1' || parts.length !== 3) {
  console.error('rawseal 로 봉한 꼴이 아닙니다.');
  process.exit(1);
}

const key = Buffer.from(keyB64, 'base64');
const iv = Buffer.from(parts[1], 'base64');
const blob = Buffer.from(parts[2], 'base64');
const body = blob.subarray(0, blob.length - 16);
const tag = blob.subarray(blob.length - 16);

const d = crypto.createDecipheriv('aes-256-gcm', key, iv);
d.setAuthTag(tag);
fs.writeFileSync(dst, Buffer.concat([d.update(body), d.final()]));
console.log(`  ${dst}  풀었습니다`);
