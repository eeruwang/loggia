#!/usr/bin/env node
/* unlock.js — 잠긴 판을 도로 풉니다 (확인용)
   node tools/unlock.js <잠긴 파일> <나올 파일> <암호>            */
const fs = require('fs');
const crypto = require('crypto');
const [inFile, outFile, pass] = process.argv.slice(2);
const src = fs.readFileSync(inFile, 'utf8');
const m = src.match(/const D = \{ s:"([^"]*)", i:"([^"]*)", c:"([^"]*)", n:(\d+) \}/);
if (!m) { console.error('덩이를 찾지 못했습니다'); process.exit(1); }
const [, s, i, c, n] = m;
const salt = Buffer.from(s, 'base64');
const iv = Buffer.from(i, 'base64');
const all = Buffer.from(c, 'base64');
const body = all.subarray(0, all.length - 16);
const tag = all.subarray(all.length - 16);
const key = crypto.pbkdf2Sync(pass, salt, Number(n), 32, 'sha256');
const d = crypto.createDecipheriv('aes-256-gcm', key, iv);
d.setAuthTag(tag);
const plain = Buffer.concat([d.update(body), d.final()]);
fs.writeFileSync(outFile, plain);
console.error(`풀었습니다  소금=${s}  ${inFile} → ${outFile} (${plain.length}B)`);
