#!/usr/bin/env node
// =============================================================================
// rawseal.js — 원본 키 하나로 작은 꾸러미를 암호화한다
//
//   node rawseal.js <들어갈 파일> <나올 파일> <키 base64 32바이트>
//
// seal.js 와 무엇이 다른가
//   seal.js 는 사람이 손으로 치는 암호를 받는다. 사람의 암호는 엔트로피가
//   낮으므로 PBKDF2 를 육십만 번 돌려 늘여야 한다. 그 늘이는 일이 무겁다.
//
//   여기서 키를 쥐는 것은 사람이 아니라 워커다. 워커에게는 처음부터
//   무작위 256비트를 주면 된다. 반복 계산이 필요 없다. 그래서 KDF 가 없다.
//   덕분에 워커가 이 꾸러미를 푸는 데 드는 셈이 일 밀리초에 못 미친다.
//   클라우드플레어 무료 판의 십 밀리초 안에 넉넉히 들어간다.
//
// 꼴
//   loggiaR1.<iv base64>.<암호문+태그 base64>
//   웹크립토가 그러하듯 인증 태그를 암호문 뒤에 붙여 둔다.
//   그래야 워커에서 crypto.subtle.decrypt 가 그대로 받아 먹는다.
// =============================================================================
const fs = require('fs');
const crypto = require('crypto');

const [, , src, dst, keyB64] = process.argv;
if (!src || !dst || !keyB64) {
  console.error('쓰임  node rawseal.js <들어갈 파일> <나올 파일> <키 base64>');
  process.exit(1);
}

const key = Buffer.from(keyB64, 'base64');
if (key.length !== 32) {
  console.error(`키는 32바이트여야 합니다. 지금은 ${key.length}바이트입니다.`);
  process.exit(1);
}

const iv = crypto.randomBytes(12);
const c = crypto.createCipheriv('aes-256-gcm', key, iv);
const body = Buffer.concat([c.update(fs.readFileSync(src)), c.final()]);
const blob = Buffer.concat([body, c.getAuthTag()]);

fs.writeFileSync(dst, `loggiaR1.${iv.toString('base64')}.${blob.toString('base64')}`);
console.log(`  ${dst}  ${Math.round(blob.length / 1024)}KB  (원본 키로 암호화)`);
