#!/usr/bin/env node
/* ============================================================================
   lock.js — 판을 암호로 잠급니다

   쓰는 법
     node tools/lock.js <들어갈 파일> <나올 파일> <암호>

   하는 일
     1) 들어온 HTML 을 통째로 AES-256-GCM 으로 잠급니다.
     2) 암호에서 열쇠를 뽑을 때 PBKDF2 를 60만 번 돌립니다.
        훔쳐 간 사람이 기계로 두들겨 볼 때 한 번 시도에 드는 값을 올립니다.
     3) 잠긴 덩이와 암호를 묻는 화면을 한 파일로 묶어 내보냅니다.

   깃허브에 올라가는 것은 이 덩이뿐입니다. 암호는 어디에도 들어가지 않습니다.
   ========================================================================== */

const fs = require('fs');
const crypto = require('crypto');

const [inFile, outFile, passphrase, saltB64] = process.argv.slice(2);
if (!inFile || !outFile || !passphrase) {
  console.error('쓰는 법: node tools/lock.js <들어갈 파일> <나올 파일> <암호> [<소금 base64>]');
  process.exit(1);
}
// 소금은 비밀이 아니다. 페이지 안에 그대로 적힌다.
// 세 장이 같은 소금을 쓰면 한 장에서 뽑은 열쇠로 나머지도 곧바로 열린다.
// 그래서 장을 옮길 때 기다림이 없다.

const ITER = 600000;
const plain = fs.readFileSync(inFile);
const salt  = saltB64 ? Buffer.from(saltB64, 'base64') : crypto.randomBytes(16);
const iv    = crypto.randomBytes(12);
const key   = crypto.pbkdf2Sync(passphrase, salt, ITER, 32, 'sha256');

const cipher = crypto.createCipheriv('aes-256-gcm', key, iv);
const body   = Buffer.concat([cipher.update(plain), cipher.final()]);
const tag    = cipher.getAuthTag();
// 브라우저의 AES-GCM 은 덩이 끝에 인증표가 붙어 있기를 바랍니다
const payload = Buffer.concat([body, tag]).toString('base64');

const shell = `<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Loggia</title>
<link rel="preload" href="font/Pretendard-subset.woff2" as="font" type="font/woff2" crossorigin>
<meta name="robots" content="noindex, nofollow">
<style>
@font-face{font-family:'Pretendard Variable';font-weight:45 920;font-style:normal;
font-display:swap;src:url('font/Pretendard-subset.woff2') format('woff2')}
:root {
  --paper: hsl(40 12% 97%); --surface: hsl(40 20% 99.5%);
  --ink: hsl(28 10% 12%); --ink-2: hsl(28 6% 34%); --ink-3: hsl(28 5% 52%);
  --rule-2: hsl(35 10% 78%); --now: hsl(4 74% 45%);
  --font: 'Pretendard Variable', Pretendard, -apple-system, BlinkMacSystemFont,
          'Apple SD Gothic Neo', 'Noto Sans KR', 'Malgun Gothic', system-ui, sans-serif;
}
@media (prefers-color-scheme: dark) {
  :root { --paper: hsl(28 8% 10%); --surface: hsl(28 7% 14%);
    --ink: hsl(40 12% 94%); --ink-2: hsl(35 6% 72%); --ink-3: hsl(35 5% 56%);
    --rule-2: hsl(28 6% 32%); --now: hsl(4 84% 66%); }
}
* { box-sizing: border-box; }
body { margin:0; min-height:100vh; display:flex; align-items:center; justify-content:center;
  padding:24px; background:var(--paper); color:var(--ink); font-family:var(--font);
  -webkit-font-smoothing:antialiased; }
.gate { width:100%; max-width:330px; }
.name { font-size:12px; letter-spacing:0.3em; text-transform:uppercase; color:var(--ink-3);
  margin-bottom:26px; }
h1 { font-size:19px; font-weight:700; margin:0 0 6px; }
p.lede { font-size:14px; color:var(--ink-2); margin:0 0 22px; line-height:1.6; }
input[type=password] { width:100%; padding:13px 14px; font-size:16px; font-family:var(--font);
  color:var(--ink); background:var(--surface); border:2px solid var(--ink); border-radius:3px;
  outline:none; }
button { width:100%; margin-top:9px; padding:13px; font-size:15px; font-weight:700;
  font-family:var(--font); color:var(--paper); background:var(--ink); border:0; border-radius:3px;
  cursor:pointer; }
button:disabled { opacity:.5; cursor:default; }
label.remember { display:flex; align-items:center; gap:8px; margin-top:14px;
  font-size:13px; color:var(--ink-3); cursor:pointer; }
.msg { min-height:22px; margin-top:14px; font-size:13.5px; color:var(--now); }
.msg.calm { color:var(--ink-3); }
@keyframes nudge { 0%,100%{transform:translateX(0)} 25%{transform:translateX(-5px)} 75%{transform:translateX(5px)} }
.shake { animation:nudge .28s; }
</style>
</head>
<body>
<div class="gate">
  <div class="name">Loggia</div>
  <h1>잠긴 판입니다</h1>
  <p class="lede">암호를 넣으면 이 자리에서 풀립니다.<br>내용은 서버로 오가지 않습니다.</p>
  <form id="f">
    <input type="password" id="pw" placeholder="암호" autocomplete="current-password" autofocus>
    <button type="submit" id="go">열기</button>
    <label class="remember"><input type="checkbox" id="rm"> 이 기기에서 기억하기</label>
  </form>
  <div class="msg" id="m"></div>
</div>
<script>
const D = { s:"${salt.toString('base64')}", i:"${iv.toString('base64')}", c:"${payload}", n:${ITER} };
const PASS_KEY = 'loggia.pass';          // 이 기기에서 기억하기
const CACHE_KEY = 'loggia.key.' + D.s;   // 이 열림 동안 쓰는 열쇠. 소금마다 따로 둔다
const b64 = s => Uint8Array.from(atob(s), c => c.charCodeAt(0));
const $ = id => document.getElementById(id);

// 암호에서 열쇠를 뽑는다. 육십만 번을 돌리므로 몇 초 걸린다.
async function keyFromPass(pass) {
  const km = await crypto.subtle.importKey('raw', new TextEncoder().encode(pass), 'PBKDF2', false, ['deriveKey']);
  return crypto.subtle.deriveKey(
    { name:'PBKDF2', salt:b64(D.s), iterations:D.n, hash:'SHA-256' },
    km, { name:'AES-GCM', length:256 }, true, ['decrypt']);
}
async function decryptWith(k) {
  const pt = await crypto.subtle.decrypt({ name:'AES-GCM', iv:b64(D.i) }, k, b64(D.c));
  return new TextDecoder().decode(pt);
}
// 뽑아 둔 열쇠가 있으면 그것으로 곧바로 연다. 기다림이 없다.
async function keyFromCache() {
  const raw = sessionStorage.getItem(CACHE_KEY);
  if (!raw) return null;
  return crypto.subtle.importKey('raw', b64(raw), { name:'AES-GCM' }, true, ['decrypt']);
}
async function cache(k) {
  const raw = await crypto.subtle.exportKey('raw', k);
  var s = ''; new Uint8Array(raw).forEach(function (c) { s += String.fromCharCode(c); });
  sessionStorage.setItem(CACHE_KEY, btoa(s));
}

// 판을 그린다.
// 문서를 아직 읽는 중일 때 document.open 을 부르면 지워지지 않고 덧붙는다.
// 잠금 화면이 판 위에 그대로 남는 까닭이 이것이었다. 다 읽은 뒤에 부른다.
function show(html) {
  function go() { document.open(); document.write(html); document.close(); }
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', go, { once: true });
  } else {
    go();
  }
}

// 스스로 여는 동안에는 암호 칸을 감춘다. 그대로 두면 다시 묻는 것처럼 보인다.
function waiting(on) {
  document.getElementById('f').style.display = on ? 'none' : '';
  $('m').className = 'msg calm';
  $('m').textContent = on ? '여는 중…' : '';
}

async function openWithKey(k, pass, remember) {
  const html = await decryptWith(k);
  await cache(k);
  if (pass) {
    sessionStorage.setItem(PASS_KEY, pass);
    if (remember) localStorage.setItem(PASS_KEY, pass);
  }
  show(html);
}

async function tryOpen(pass, remember) {
  $('go').disabled = true;
  $('m').className = 'msg calm';
  $('m').textContent = '여는 중…';
  try {
    await openWithKey(await keyFromPass(pass), pass, remember);
  } catch (e) {
    $('go').disabled = false;
    $('m').className = 'msg';
    $('m').textContent = '암호가 맞지 않습니다.';
    const pw = $('pw');
    pw.classList.remove('shake'); void pw.offsetWidth; pw.classList.add('shake');
    pw.select();
  }
}

// 열 때 스스로 해 보는 순서.
// 하나, 이 열림에서 뽑아 둔 열쇠. 곧바로 열린다.
// 둘, 이 기기에 기억해 둔 암호. 몇 초 걸린다.
// 셋, 둘 다 없으면 암호를 묻는다.
async function autoOpen() {
  try {
    const k = await keyFromCache();
    if (k) { waiting(true); await openWithKey(k, null, false); return; }
  } catch (e) { sessionStorage.removeItem(CACHE_KEY); }
  const saved = localStorage.getItem(PASS_KEY);
  if (!saved) return;
  waiting(true);
  try {
    await openWithKey(await keyFromPass(saved), saved, true);
  } catch (e) {
    localStorage.removeItem(PASS_KEY);
    waiting(false);
  }
}

$('f').addEventListener('submit', e => {
  e.preventDefault();
  tryOpen($('pw').value, $('rm').checked);
});

if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', autoOpen, { once: true });
} else {
  autoOpen();
}
</script>
</body>
</html>
`;

fs.writeFileSync(outFile, shell);
const kb = n => (n / 1024).toFixed(0) + 'KB';
console.log(`잠금 완료  ${inFile} (${kb(plain.length)}) → ${outFile} (${kb(shell.length)})`);
