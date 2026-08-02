#!/usr/bin/env node
/* =============================================================================
   pagekey.js — 워커에 넣을 PAGE_KEY 를 뽑는다.

     node tools/pagekey.js public/data.enc "<암호>"

   왜 있는가
     클라우드플레어 Workers 는 PBKDF2 반복을 10만 번까지만 허용한다.
     이 보드는 60만 번을 쓰므로 워커가 암호에서 키를 뽑을 수 없다.
     그래서 여기서 미리 뽑아 base64 로 내주고, 그 값을 워커 시크릿에 넣는다.

     덤으로 사람이 기억하는 암호가 클라우드플레어에 남지 않는다.

   키는 솔트에 매여 있다. data.enc 의 솔트가 바뀌면 이 키도 다시 뽑아야 한다.
   그래서 publish.sh 는 다시 암호화할 때 있던 솔트를 그대로 쓴다.

   나온 값을 채팅이나 로그에 붙이지 않는다. board_keys.txt 에 적어 둔다.
   ========================================================================== */
const fs = require('fs');
const crypto = require('crypto');

const [, , file, pass] = process.argv;
if (!file || !pass) {
  console.error('쓰는 법: node tools/pagekey.js <data.enc> <암호>');
  process.exit(1);
}

const parts = fs.readFileSync(file, 'utf8').trim().split('.');
if (parts[0] !== 'loggia1' || parts.length !== 4) {
  console.error('data.enc 형식이 낯섭니다. loggia1.<솔트>.<초기값>.<덩이> 여야 합니다.');
  process.exit(1);
}
const salt = Buffer.from(parts[1], 'base64');
const key = crypto.pbkdf2Sync(pass, salt, 600000, 32, 'sha256');

// 정말 열리는 키인지 확인하고 내준다. 안 그러면 워커에서야 틀린 걸 안다
const all = Buffer.from(parts[3], 'base64');
const d = crypto.createDecipheriv('aes-256-gcm', key, Buffer.from(parts[2], 'base64'));
d.setAuthTag(all.subarray(all.length - 16));
try {
  d.update(all.subarray(0, all.length - 16));
  d.final();
} catch (e) {
  console.error('암호가 맞지 않습니다.');
  process.exit(1);
}

console.error('이 값을 워커 시크릿 PAGE_KEY 에 넣으세요. 솔트가 바뀌면 다시 뽑아야 합니다.');
console.log(key.toString('base64'));
