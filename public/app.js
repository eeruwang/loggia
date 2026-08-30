/* =============================================================================
   app.js — 화면을 브라우저에서 만든다.

   예전에는 파이썬이 다섯 페이지를 미리 만들어 각각 암호화했다. 암호화된 파일은 갱신할
   때마다 처음부터 끝까지 달라 보이므로, 글자 하나를 고쳐도 368KB가 저장소에
   새로 쌓였다. 이제 올라가는 것은 data.enc 하나뿐이다. HTML 파일과 이 파일은
   내용이 바뀔 때에만 바뀐다.

   순서는 이렇다.
     암호를 받는다 → 키를 만든다 → data.enc 를 받아 푼다
     → 체크 기록을 읽어 데이터와 합친다 → 화면을 만든다

   체크 기록을 미리 읽어 합치므로, 새로 추가한 할 일이 다른 할 일과 같은 목록에
   처음부터 서 있다. 다 그린 다음 나중에 끼워 넣던 처리가 없어졌다.

   이 파일의 내용은 비밀이 아니다. 비밀은 data.enc 안에만 있다.
   ========================================================================== */
(function () {
'use strict';

/* ── 잔손 ────────────────────────────────────────────────────────────────── */

function esc(s) {
  if (s === null || s === undefined) return '';
  return String(s).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
                  .replace(/"/g, '&quot;').replace(/'/g, '&#x27;');
}

/* 할 일의 키는 순서가 아니라 내용으로 만든다. 순서로 매기면 갱신이 첫 할 일을
   뺐을 때 둘째가 첫째의 표시를 물려받는다. 파이썬이 쓰던 sha1 과 같은 값이
   나와야 이미 기록에 쌓인 표시가 살아남는다. */
function sha1hex(str) {
  var bytes = new TextEncoder().encode(str);
  var ml = bytes.length;
  var withOne = new Uint8Array(((ml + 8) >> 6 << 6) + 64);
  withOne.set(bytes);
  withOne[ml] = 0x80;
  var bits = ml * 8;
  var dv = new DataView(withOne.buffer);
  dv.setUint32(withOne.length - 8, Math.floor(bits / 4294967296));
  dv.setUint32(withOne.length - 4, bits >>> 0);

  var h0 = 0x67452301, h1 = 0xEFCDAB89, h2 = 0x98BADCFE, h3 = 0x10325476, h4 = 0xC3D2E1F0;
  var w = new Int32Array(80);
  function rol(n, s) { return (n << s) | (n >>> (32 - s)); }

  for (var i = 0; i < withOne.length; i += 64) {
    for (var j = 0; j < 16; j++) w[j] = dv.getInt32(i + j * 4);
    for (j = 16; j < 80; j++) w[j] = rol(w[j-3] ^ w[j-8] ^ w[j-14] ^ w[j-16], 1);
    var a = h0, b = h1, c = h2, d = h3, e = h4;
    for (j = 0; j < 80; j++) {
      var f, k;
      if (j < 20)      { f = (b & c) | (~b & d);          k = 0x5A827999; }
      else if (j < 40) { f = b ^ c ^ d;                   k = 0x6ED9EBA1; }
      else if (j < 60) { f = (b & c) | (b & d) | (c & d); k = 0x8F1BBCDC; }
      else             { f = b ^ c ^ d;                   k = 0xCA62C1D6; }
      var t = (rol(a, 5) + f + e + k + w[j]) | 0;
      e = d; d = c; c = rol(b, 30); b = a; a = t;
    }
    h0 = (h0 + a) | 0; h1 = (h1 + b) | 0; h2 = (h2 + c) | 0;
    h3 = (h3 + d) | 0; h4 = (h4 + e) | 0;
  }
  function hex(n) { return ((n >>> 0) + 0x100000000).toString(16).slice(-8); }
  return hex(h0) + hex(h1) + hex(h2) + hex(h3) + hex(h4);
}

function dots(iso) { return String(iso || '').replace(/-/g, '.'); }
function md(iso) { return String(iso || '').slice(5).replace(/-/g, '.'); }

/* 파이썬의 sorted 는 같은 값끼리 자리를 바꾸지 않는다. 자바스크립트의 sort 도
   그러하므로, 견줌만 0을 제때 돌려주면 두 쪽의 차례가 같다. */
function cmp(a, b) { return a < b ? -1 : a > b ? 1 : 0; }

/* ── 데이터에서 곧바로 나오는 것들 ───────────────────────────────────────── */

var D = null;         // 보드 데이터
var VEN = {};         // 처 id → 처
var BYVEN = {};       // 처 id → [[항목, 지난일인가]]
var NVEN = 0, NARC = 0, NJOB = 0;
var ADD = {};         // 사이트에서 직접 적어 넣은 할 일
var EDIT = {};        // 사이트에서 고치거나 지운 할 일
var SRV = {};         // 끝냈다고 표시한 것
var JOB = {};         // 공고. 판이 아니라 워커에 산다

function indexData() {
  VEN = {}; BYVEN = {};
  (D.venueGroups || []).forEach(function (g) {
    (g.venues || []).forEach(function (v) { VEN[v.id] = v; });
  });
  (D.sections || []).forEach(function (s) {
    (s.items || []).forEach(function (it) {
      if (it.venue) (BYVEN[it.venue] = BYVEN[it.venue] || []).push([it, false]);
    });
  });
  (D.archive || []).forEach(function (it) {
    if (it.venue) (BYVEN[it.venue] = BYVEN[it.venue] || []).push([it, true]);
  });
  NVEN = (D.venueGroups || []).reduce(function (n, g) { return n + g.venues.length; }, 0);
  NARC = (D.archive || []).length;
}

function allItems() {
  var out = [];
  (D.sections || []).forEach(function (s) {
    (s.items || []).forEach(function (it) { out.push([it, false]); });
  });
  (D.archive || []).forEach(function (it) { out.push([it, true]); });
  return out;
}

function statusOf(item, fallbackTone) {
  var st = (D.statuses || {})[item.status];
  return st || { label: item.status || '', tone: fallbackTone || 'live' };
}

/* ── 조각들 ──────────────────────────────────────────────────────────────── */

/* 색인 딱지를 [모양, 글자] 짝으로 돌려준다.
   데이터에는 키만 적는다.  "indexes": ["ahci", "scopus"]
   앞에 빼기표를 붙이면 미등재를 뜻한다.  "-ahci"  →  A&HCI 미등재
   예전 형식인 [["strong", "A&HCI"]] 도 그대로 받는다. */
function indexTags(venue) {
  var kinds = D.indexKinds || {};
  var out = [];
  (venue.indexes || []).forEach(function (x) {
    if (typeof x === 'string') {
      var neg = x.charAt(0) === '-';
      var bare = neg ? x.replace(/^-+/, '') : x;
      var k = kinds[bare];
      if (!k) out.push(['none', bare]);
      else if (neg) out.push(['none', k.label + ' 미등재']);
      else out.push([k.tone || 'plain', k.label]);
    } else {
      out.push([x[0], x[1]]);
    }
  });
  return out;
}

function linksHtml(item) {
  var out = [];
  (item.chats || []).forEach(function (c) {
    var lab = '대화 ' + c.date.slice(5).replace(/-/g, '.');
    out.push('<a class="link chat" href="' + esc(c.url) + '" target="_blank" rel="noopener">'
             + esc(lab) + '</a>');
  });
  (item.links || []).forEach(function (l) {
    out.push('<a class="link ' + esc(l.kind) + '" href="' + esc(l.url)
             + '" target="_blank" rel="noopener">' + esc(l.label) + '</a>');
  });
  return out.length ? '<div class="links">' + out.join('') + '</div>' : '';
}

function whenCol(item) {
  var d = item.dates || {};
  if (d.deadline) {
    return '<div class="when-col"><span class="dday" data-deadline="' + d.deadline + '">D-</span>'
         + '<span class="date" data-d="' + md(d.deadline) + '">' + md(d.deadline) + '</span></div>';
  }
  if (d.sent) {
    return '<div class="when-col"><span class="dday none" data-since="' + d.sent + '"></span>'
         + '<span class="date">' + md(d.sent) + ' 냄</span></div>';
  }
  return '<div class="when-col"><span class="dday none">—</span></div>';
}

/* 다음 할 일들. 저마다 제 날짜를 가질 수 있다.

   데이터에는 두 꼴 다 적을 수 있다.
       "추천인에게 메일 보내기"
       {"t": "초고 넘기기", "due": "2026-08-10"}

   여기에 기록에서 온 것을 이어 붙인다. 손으로 더한 할 일도 같은 목록에 선다.
   따로 상자를 만들면 눈이 두 번 읽는다. 아직 데이터에 없으므로 글의 지문
   대신 기록 토큰을 그대로 쓰고, 표를 하나 달아 아직 참이 아님을 밝힌다. */
/* 이 항목의 일하는 기간. 사이트에서 고쳐 두었으면 그것이 먼저다.
   기간은 할 일 하나가 아니라 항목에 붙는 값이라 기록의 키도 다르다.
   `item:<항목 아이디>` 로 적어 두면 할 일 키(`<아이디>.<지문>`)와 섞이지 않는다. */
function pumOf(item) {
  var e = EDIT['item:' + item.id];
  return (e && e['품'] !== undefined) ? e['품'] : item['품'];
}

function stepsOf(item) {
  var out = [];
  var st = item.steps || (item.next ? [item.next] : []);
  st.forEach(function (x) {
    var o = (typeof x === 'string') ? { t: x } : { t: x.t, due: x.due };
    // 키는 처음 글로 만든다. 고쳐도 그대로 둔다. 그래야 체크한 것과 고친 것이
    // 같은 할 일을 가리키고, 반영할 때 원본에서 찾을 수 있다.
    o.key = item.id + '.' + sha1hex(o.t).slice(0, 8);
    var e = EDIT[o.key];
    if (e) {
      if (e.del) return;                       // 삭제로 표시한 것은 안 보인다
      o.t = e.t; o.due = e.due; o.edited = true;
    }
    out.push(o);
  });
  Object.keys(ADD).forEach(function (k) {
    var a = ADD[k];
    if (a.item !== item.id) return;
    out.push({ t: a.t, due: a.due, key: 'add:' + k, addKey: k, fresh: true });
  });
  return out;
}

/* 첫 할 일은 크게, 나머지는 작게 차례로.
   네모를 누르면 기록에 적히고, 저장하면 목록에서 내려간다. */
function stepsHtml(item) {
  var ss = stepsOf(item);
  if (!ss.length) return '<p class="todo none">지금 할 일 없음</p>';
  var eff = (D.efforts || {})[pumOf(item)];
  var cost = eff ? '<span class="cost">' + esc(eff.label) + '</span>' : '';

  function box(st, cls) {
    var due = st.due ? '<span class="sdue" data-deadline="' + esc(st.due) + '">D-</span>' : '';
    var tag = st.fresh ? '<span class="tag">새로 추가</span>'
            : st.edited ? '<span class="tag">수정됨</span>' : '';
    return '<input type="checkbox" id="s-' + esc(st.key) + '" data-done="' + esc(st.key) + '">'
         + '<label for="s-' + esc(st.key) + '"' + (cls || '') + '>' + esc(st.t) + '</label>'
         + due + tag
         + '<button type="button" class="edit" data-edit="' + esc(st.key) + '"'
         + ' data-item="' + esc(item.id) + '" aria-label="이 할 일 수정">수정</button>';
  }

  var out = ['<div class="step first">' + box(ss[0], ' class="todo"') + cost + '</div>'];
  if (ss.length > 1) {
    out.push('<ol class="rest">' + ss.slice(1).map(function (x) {
      return '<li' + (x.fresh ? ' class="pend"' : '') + '>' + box(x) + '</li>';
    }).join('') + '</ol>');
  }
  return out.join('');
}

function entryHtml(item) {
  var st = statusOf(item);
  var v = VEN[item.venue];
  var venue = v ? '<a class="venue" href="journals.html#' + esc(item.venue) + '">'
                  + esc(v.name) + '</a>' : '';
  var note = item.note ? '<p class="note">' + esc(item.note) + '</p>' : '';
  // 마지막으로 마지막 작업일. 오래 멎어 있으면 눈에 띄게 한다.
  // 마감만 보면 마감 없는 항목이 조용히 가라앉는다.
  var t = (item.dates || {}).touched;
  var touch = t ? '<span class="touch" data-touched="' + esc(t) + '"></span>'
                : '<span class="touch none">작업 기록 없음</span>';
  var tags = [item.status || '', item['품'] || ''].filter(Boolean).join(' ');
  // 종류마다 색을 준다. 왼쪽 막대 하나로 무슨 종류인지 눈이 먼저 안다
  return '<article class="entry t-' + esc(st.tone || 'live') + '" data-id="' + esc(item.id)
       + '" data-tags="' + esc(tags) + '">' + whenCol(item) + '\n'
       + '<div class="body"><div class="title-line"><h3 class="t">' + esc(item.title) + '</h3>\n'
       + '<span class="state">' + esc(st.label) + '</span></div>\n'
       + '<div class="meta">' + venue + '<span class="k">' + esc(item.kind || '') + '</span>'
       + touch + '</div>\n'
       + stepsHtml(item) + note + linksHtml(item) + '</div></article>';
}

/* 무게는 낼 곳의 갈래와 색인에서 뽑는다. 항목마다 손으로 붙이지 않는다.
   낼 곳이 바뀌면 무게도 따라 바뀐다. */
var SEAT_W = { '교원 공고': 2, '연구직 공고': 2, '펠로십': 2, '레지던시': 1.5,
  '페스티벌': 1, '학회': 0.8, '공모': 0.8, '잡지': 0.7, '자격': 0.6, '단행본': 0.5 };
var INDEX_W = { ahci: 2, ssci: 2, scie: 2, scopus: 1.5, kci: 1.3,
  kcic: 1, esci: 1, erih: 1, doaj: 1 };
var PUM_D = { '십분': 0, '한시간': 0, '반나절': 0.5, '며칠': 3 };

function weightOf(item) {
  var v = VEN[item.venue];
  if (!v) return 1;
  if (v.type !== '저널') return SEAT_W[v.type] || 1;
  var w = 0.7;
  (v.indexes || []).forEach(function (x) {
    if (typeof x !== 'string' || x.charAt(0) === '-') return;   // 앞의 - 는 미등재
    var n = INDEX_W[x];
    if (n && n > w) w = n;
  });
  return w;
}

function daysBetween(a, b) {
  return Math.round((fromIso(b) - fromIso(a)) / 86400000);
}

/* 급함은 마감에서 품에 드는 날을 뺀 여유로 센다. 며칠 걸리는 일이 사흘 남았으면
   이미 늦은 것인데, 날짜만 보면 반나절짜리와 같은 급함으로 보인다. */
function focusScore(item, today) {
  var d = item.dates || {};
  var iso = d.deadline || d.expected || '';
  var slack = 999, over = false;
  if (iso.length === 10) {
    var n = daysBetween(today, iso);
    over = n < 0;
    slack = n - (PUM_D[item['품']] || 0);
  }
  var s = 100 / (Math.max(slack, 0) + 1) * weightOf(item);
  if (d.touched && d.touched.length === 10 && daysBetween(d.touched, today) > 21) s += 8;
  if (over) s += 1000;                       // 지난 마감은 숨기지 않고 맨 앞에 세운다
  return s;
}

/* 진행 중인 것만 본다. 낸 것과 물린 것과 멈춘 것은 오늘 손댈 자리가 아니다.
   위에서 셋을 고른다. */
function pickFocus() {
  var today = isoOf(today0()), rows = [];
  (D.sections || []).forEach(function (s) {
    if (s.id !== 'now') return;
    (s.items || []).forEach(function (it) {
      var tone = ((D.statuses || {})[it.status] || {}).tone;
      if (tone === 'wait' || tone === 'stop' || tone === 'done') return;
      if (!stepsOf(it).length) return;
      rows.push({ it: it, s: focusScore(it, today) });
    });
  });
  rows.sort(function (a, b) { return b.s - a.s; });
  return rows.slice(0, 3).map(function (r) { return r.it; });
}

/* 접어 두는 섹션. 읽을 것이지 오늘 할 일이 아니라면 접는다. */
function fold(title, count, body, anchor) {
  var n = count ? '<span class="c">' + count + '</span>' : '';
  var a = anchor ? ' id="' + esc(anchor) + '"' : '';
  return '<details class="fold"' + a + '><summary><h2>' + esc(title) + '</h2>' + n
       + '<span class="arrow">▸</span></summary>' + body + '</details>';
}

/* 섹션 하나. 머리를 누르면 접힌다. 펼침과 접힘은 이 기기에 남는다. */
function secbox(title, count, body, key, open_) {
  var n = (count === null || count === undefined) ? '' : '<span class="c">' + count + '</span>';
  var k = (key || title) ? ' data-k="' + esc(key || title) + '"' : '';
  var a = key ? ' id="' + esc(key) + '"' : '';
  return '<details class="group"' + k + a + (open_ === false ? '' : ' open') + '>'
       + '<summary class="sec"><h2>' + esc(title) + '</h2>' + n
       + '<span class="arrow">▸</span></summary>' + body + '</details>';
}

/* 거르는 단추 한 줄. 단추마다 키 하나. 상자의 data-tags 에 그 말이
   적혀 있으면 남는다. */
function filtersHtml(buttons, label) {
  if (buttons.length < 2) return '';
  var bs = buttons.map(function (b) {
    var k = b[0], t = b[1], n = b[2];
    return '<button type="button" data-filter="' + esc(k) + '"'
         + (k === '*' ? ' aria-pressed="true"' : '') + '>' + esc(t)
         + (n === null || n === undefined ? '' : '<b>' + n + '</b>') + '</button>';
  }).join('');
  return '<div class="filters" role="group" aria-label="' + esc(label || '골라 보기') + '">'
       + bs + '</div>';
}

/* 몇 편이 무슨 상태로 이 처(또는 이 이론가)에 걸려 있나 */
function historyRows(entries, conceptsInstead, tagOf) {
  return entries.map(function (pair) {
    var it = pair[0];
    var tg = tagOf ? tagOf(pair) : '';
    var st = statusOf(it);
    var cls = { live: 'live', wait: '', stop: 'stop', done: '' }[st.tone] || '';
    var right;
    if (conceptsInstead) {
      right = esc(((it.uses || {})['개념'] || []).join(' · '));
    } else {
      var d = it.dates || {};
      var when = d.decided || d.sent || d.deadline || '';
      var tail = d.decided ? '결정' : d.sent ? '냄' : d.deadline ? '마감' : '';
      right = dots(when) + ' ' + tail;
    }
    return '<div class="hrow"' + (tagOf ? ' data-rowtags="' + esc(tg) + '"' : '')
         + '><span class="mark ' + cls + '">' + esc(st.label) + '</span>'
         + '<span class="t">' + esc(it.title) + '</span>'
         + '<span class="d">' + right + '</span>'
         + (!conceptsInstead && it.review
            ? '<p class="gist">' + esc(it.review.gist)
              + '<span class="who">' + esc(it.review.who || '') + '</span></p>' : '')
         + '</div>';
  }).join('');
}

/* ── 머리와 꼬리 ─────────────────────────────────────────────────────────── */

var TABS = [
  ['index',     'index.html',     '현황판',  null],
  ['calendar',  'calendar.html',  '달력',    null],
  ['journals',  'journals.html',  '낼 곳',   'ven'],
  ['jobs',      'jobs.html',      '공고',    'job'],
  ['materials', 'materials.html', '재료',    null],
  ['archive',   'archive.html',   '지난 일', 'arc']
];

function headHtml(page, title) {
  var updated = dots(D.meta.updated);
  var tabs = TABS.map(function (t) {
    var n = t[3] === 'ven' ? NVEN : t[3] === 'arc' ? NARC : t[3] === 'job' ? NJOB : null;
    return '<a class="tab' + (t[0] === page ? ' here' : '') + '" href="' + t[1] + '">'
         + t[2] + (n === null ? '' : ' <span class="n">' + n + '</span>') + '</a>';
  }).join('\n  ');
  return '<div class="wrap">\n'
    + '<header class="masthead">\n'
    + '  <div><div class="name">Loggia</div><h1>' + esc(title) + '</h1></div>\n'
    + '  <span class="stamp">' + updated
    + '<span class="mode" role="group" aria-label="화면 밝기">'
    + '<button type="button" data-mode="auto">자동</button>'
    + '<button type="button" data-mode="light">밝게</button>'
    + '<button type="button" data-mode="dark">어둡게</button></span></span>\n'
    + '</header>\n'
    + '<nav class="tabs">\n  ' + tabs + '\n</nav>\n';
}

function footHtml() {
  return '\n<div class="colophon">암호로 잠긴 보드 · 갱신 ' + dots(D.meta.updated) + '</div>\n</div>';
}

/* ── 현황판 ──────────────────────────────────────────────────────────────── */

function buildIndex() {
  var out = [headHtml('index', D.meta.title)];

  // 지난 서른 날. 한 일이 눈에 보여야 한다.
  // 학계와 ADHD가 겹치면 자기가 한 일을 늘 실제보다 적게 본다.
  var done = [];
  allItems().forEach(function (pair) {
    var it = pair[0], d = it.dates || {};
    if (d.sent) done.push({ d: d.sent, k: '냈다', t: it.title });
    if (d.decided) done.push({ d: d.decided, k: '끝났다', t: it.title });
    if (d.touched) done.push({ d: d.touched, k: '손댔다', t: it.title });
  });
  done = done.filter(function (x) { return x.d.length === 10; });

  var lt = D.meta.ledger || '';
  out.push('<div class="carry" id="carry" hidden>'
    + '<span class="cap">끝낸 일 <b class="n">0</b></span>'
    + (lt ? '<button type="button" class="save">저장</button>'
          : '<button type="button" class="copy">복사</button>')
    + '<button type="button" class="clear">전체 해제</button>'
    + '<span class="hint">'
    + (lt ? '한 번에 저장합니다. 다른 기기에서도 보입니다'
          : '복사해서 채팅에 붙이면 반영됩니다')
    + '</span></div>');
  out.push('<div class="tally" id="tally"></div>');

  // 할 일을 더하는 자리. 화면 오른쪽 아래 하나뿐이다.
  if (lt) {
    var opts = '';
    (D.sections || []).forEach(function (sec) {
      if (sec.id === 'waiting') return;
      (sec.items || []).forEach(function (it) {
        opts += '<option value="' + esc(it.id) + '">' + esc(it.title) + '</option>';
      });
    });
    out.push('<button type="button" class="fab" id="fab" aria-label="할 일 추가">+</button>'
      + '<div class="sheet" id="sheet" hidden role="dialog" aria-label="할 일 추가">'
      + '<form class="sheetform">'
      + '<label class="sl">어디에</label>'
      + '<select class="ai">' + opts + '</select>'
      + '<label class="sl">무엇을</label>'
      + '<input type="text" class="at" placeholder="할 일을 적으세요" maxlength="200" required>'
      + '<label class="sl">언제까지 <span class="opt">비워 둬도 됩니다</span></label>'
      + '<input type="date" class="ad">'
      + '<div class="srow"><button type="submit" class="ok">추가</button>'
      + '<button type="button" class="cancel">취소</button></div>'
      + '</form></div>');
  }

  var picks = pickFocus();
  if (picks.length) {
    var f = picks[0], v = VEN[f.venue];
    var fd = f.dates || {};
    var iso = fd.deadline || fd.expected || '';
    var wide = (iso.length === 10)
      ? '<span class="dday" data-wide="1" data-deadline="' + iso + '">D-</span>\n' : '';
    var when = (iso.length === 10)
      ? '<div class="when">마감 ' + iso.slice(5, 7).replace(/^0+/, '') + '월 '
        + iso.slice(8).replace(/^0+/, '') + '일</div>' : '';
    var rest = picks.slice(1).map(function (it) {
      var v2 = VEN[it.venue], d2 = it.dates || {};
      var i2 = d2.deadline || d2.expected || '';
      return '<li>' + (i2.length === 10
          ? '<span class="dday" data-deadline="' + i2 + '">D-</span>' : '<span class="dday"></span>')
        + '<span class="t">' + esc(stepsOf(it)[0].t) + '</span>'
        + '<span class="who">' + esc(it.title) + (v2 ? ' · ' + esc(v2.name) : '') + '</span></li>';
    }).join('');
    out.push('<section class="focus"><div class="cap">지금 이것부터</div>\n'
      + '<div class="line">' + wide
      + '<span class="who">' + esc(f.title) + (v ? ' · ' + esc(v.name) : '') + '</span></div>\n'
      + '<p class="todo">' + esc(stepsOf(f)[0].t) + '</p>\n'
      + when
      + (rest ? '<ul class="also">' + rest + '</ul>' : '')
      + '</section>');
  }

  // 답을 기다리는 것은 달력의 응답 시계가 맡는다. 여기서 또 보이면 두 번 읽게 된다
  var shown = (D.sections || []).filter(function (x) { return x.id !== 'waiting'; });

  // 상태 필터는 뺐다(2026-08-19). 보낸 것이 현황판에 없어 반쪽이었다.


  shown.forEach(function (x) {
    var items = (x.items || []).slice().sort(function (a, b) {
      return cmp((a.dates || {}).deadline || '9999', (b.dates || {}).deadline || '9999');
    });
    out.push(secbox(x.label, x.items.length, items.map(entryHtml).join(''), x.id));
  });

  if (D.decisions && D.decisions.length) {
    var by = {};
    allItems().forEach(function (p) { by[p[0].id] = p[0].title; });
    var ds = D.decisions.slice().sort(function (a, b) { return cmp(b.date, a.date); })
      .map(function (d) {
        return '<div class="dec"><span class="when">' + esc(dots(d.date)) + '</span>'
             + '<div><p class="what">' + esc(d.what)
             + (by[d.item] ? '<span class="on">' + esc(by[d.item]) + '</span>' : '')
             + '</p><p class="why">' + esc(d.why || '') + '</p></div></div>';
      }).join('');
    out.push(fold('정한 것', D.decisions.length, '<div class="decs">' + ds + '</div>'));
  }

  var c = D.compass;
  if (c) {
    out.push('<div class="compass"><div class="cap">' + esc(c.label) + '</div>'
      + c.lines.map(function (l) { return '<p>' + esc(l) + '</p>'; }).join('') + '</div>');
  }
  out.push(footHtml());
  return { html: out.join(''), done: done };
}

/* ── 낼 곳 ───────────────────────────────────────────────────────────────── */

/* 지금 원고가 가고 있는 곳. 따로 적어 두지 않고 항목에서 거꾸로 센다.
   진행 중과 보낸 것 칸만 보고, 물렸거나 멈췄거나 끝난 것은 세지 않는다.
   아직 안 한 것은 언젠가 갈 곳이지 지금 가는 곳이 아니라 뺀다. */
function goingNow(vid) {
  var n = 0;
  (D.sections || []).forEach(function (s) {
    if (s.id !== 'now' && s.id !== 'waiting') return;
    (s.items || []).forEach(function (it) {
      if (it.venue !== vid) return;
      var tone = ((D.statuses || {})[it.status] || {}).tone;
      if (tone === 'stop' || tone === 'done') return;
      n++;
    });
  });
  return n;
}

function buildJournals() {
  var out = [headHtml('journals', '낼 곳')];

  // 필터. 색인과 마감으로 좁힌다
  var tally = {}, ndl = 0, ngo = 0;
  (D.venueGroups || []).forEach(function (g) {
    g.venues.forEach(function (v) {
      indexTags(v).forEach(function (p) { tally[p[1]] = (tally[p[1]] || 0) + 1; });
      if (v.deadline) ndl++;
      if (goingNow(v.id)) ngo++;
    });
  });
  var order = ['A&HCI', 'SSCI', 'Scopus', 'KCI 등재', 'ESCI', '색인 없음'];
  var buttons = [['*', '전체', NVEN]];
  if (ngo) buttons.push(['진행', '지금 가는 곳', ngo]);
  order.forEach(function (t) { if (tally[t]) buttons.push([t, t, tally[t]]); });
  if (ndl) buttons.push(['마감', '마감 있음', ndl]);
  out.push(filtersHtml(buttons, '색인과 마감으로 골라 보기'));

  (D.venueGroups || []).forEach(function (g) {
    var body = g.venues.map(function (v) {
      var name = v.url
        ? '<a href="' + esc(v.url) + '" target="_blank" rel="noopener">' + esc(v.name) + '</a>'
        : esc(v.name);
      var tg = indexTags(v);
      var tags = tg.map(function (p) {
        return '<span class="idx ' + p[0] + '">' + esc(p[1]) + '</span>';
      }).join('');
      if (v.flag) tags += '<span class="flag">' + esc(v.flag) + '</span>';
      var going = goingNow(v.id);

      var facts = [];
      if (v.deadline) {
        facts.push('<span><span class="lab">마감</span><b>' + dots(v.deadline) + ' · </b>'
          + '<b class="dday" style="font-size:13.5px;display:inline" data-wide="1" data-deadline="'
          + v.deadline + '">D-</b></span>');
      }
      if (v['비용'] && typeof v['비용'] === 'object') {
        Object.keys(v['비용']).forEach(function (k2) {
          facts.push('<span><span class="lab">' + esc(k2) + '</span><b>'
                     + esc(v['비용'][k2]) + '</b></span>');
        });
      } else if (v.cost) {
        facts.push('<span><span class="lab">비용</span><b>' + esc(v.cost) + '</b></span>');
      }
      if (v.review) facts.push('<span><span class="lab">심사</span>' + esc(v.review) + '</span>');
      if (v.clarivate) facts.push('<span><span class="lab">색인</span>클래리베이트 대조 완료</span>');
      if (v['라이선스']) facts.push('<span><span class="lab">라이선스</span>' + esc(v['라이선스']) + '</span>');

      var rows = BYVEN[v.id] || [];
      var hist = rows.length
        ? '<div class="history"><div class="cap">여기에 낸 것 · ' + rows.length + '건</div>'
          + historyRows(rows) + '</div>'
        : '';
      var tagset = tg.map(function (p) { return p[1]; })
        .concat(v.deadline ? ['마감'] : []).concat(going ? ['진행'] : []);
      return '<section class="venue-block" id="' + esc(v.id) + '" data-tags="'
        + esc(tagset.join(' ')) + '">\n'
        + '<div class="venue-head"><h3>' + name + '</h3><span class="sub">'
        + esc(v.sub || '') + ' · ' + esc(v.type || '') + '</span>'
        + (going ? '<span class="mark live">지금 원고가 간다</span>' : '') + '</div>\n'
        + (tags ? '<div class="idx-row">' + tags + '</div>' : '') + '\n'
        + (facts.length ? '<div class="venue-facts">' + facts.join('') + '</div>' : '') + '\n'
        + (v.note ? '<p class="note">' + esc(v.note) + '</p>' : '') + '\n'
        + hist + '</section>';
    }).join('');
    out.push(secbox(g.name, g.venues.length, body, g.id || g.name, !g['접힘']));
  });

  if (D.watch && D.watch.length) {
    var ws = D.watch.map(function (w) {
      return '<a class="link web" href="' + esc(w.url) + '" target="_blank" rel="noopener">'
           + esc(w.name) + '</a>';
    }).join('');
    out.push(secbox('길목', D.watch.length, '<div class="watch">' + ws + '</div>'));
  }
  if (D.memo && D.memo.length) {
    out.push(secbox('새겨 둘 것', D.memo.length, '<div class="memo">'
      + D.memo.map(function (m) { return '<p>' + esc(m) + '</p>'; }).join('') + '</div>'));
  }
  out.push(footHtml());
  return { html: out.join('') };
}

/* ── 재료 ────────────────────────────────────────────────────────────────── */

/* 이 글이 누구를 쓰고 있나. 두 길로 모은다.
   하나, 항목의 글에서 이름을 찾는다. thinkers 의 `말` 에 적어 둔 이름들이다.
   둘, `uses.이론가` 에 손으로 적은 것. */
function itemThinkers(item) {
  var hay = ['title', 'kind', 'note', 'next'].map(function (k) {
    return item[k] === undefined || item[k] === null ? '' : String(item[k]);
  }).join(' ');
  var found = [];
  var th = D.thinkers || {};
  Object.keys(th).forEach(function (tid) {
    var ws = th[tid]['말'] || [];
    for (var i = 0; i < ws.length; i++) {
      if (ws[i] && hay.indexOf(ws[i]) >= 0) { found.push(tid); return; }
    }
  });
  ((item.uses || {})['이론가'] || []).forEach(function (tid) {
    if (found.indexOf(tid) < 0) found.push(tid);
  });
  return found;
}

/* 읽기 묶음 하나가 누구를 담고 있나. 묶음 이름과 딸린 줄에서 이름을 찾는다.
   항목의 글에서 이론가를 찾는 방식과 같다. 묶음에 `이론가` 를 손으로 적어
   두었으면 그것도 더한다. */
function readingThinkers(r) {
  var hay = [r.name, r.sub].filter(Boolean).join(' ');
  var found = [];
  var th = D.thinkers || {};
  Object.keys(th).forEach(function (tid) {
    var ws = th[tid]['말'] || [];
    for (var i = 0; i < ws.length; i++) {
      if (ws[i] && hay.indexOf(ws[i]) >= 0) { found.push(tid); return; }
    }
  });
  (r['이론가'] || []).forEach(function (tid) {
    if (found.indexOf(tid) < 0) found.push(tid);
  });
  return found;
}

/* 이름표 하나. 눌러서 개념을 고르거나 다른 상자로 건너간다. */
function chip(kind, label, count, attr) {
  return '<button type="button" class="chip ' + kind + '" ' + attr + '>' + esc(label)
       + (count === null || count === undefined ? '' : '<b>' + count + '</b>') + '</button>';
}

/* 이름표 줄. 무엇의 이름표인지 왼쪽에 한 번만 적는다.
   이름표마다 「이론가」를 붙이면 글자가 이름을 덮는다. */
function chipRows(rows) {
  return rows.filter(function (r) { return r[1]; }).map(function (r) {
    return '<div class="chips"><span class="ck">' + esc(r[0]) + '</span>' + r[1] + '</div>';
  }).join('');
}

function buildMaterials() {
  var thinkers = D.thinkers || {}, readings = D.readings || {};
  var byThinker = {}, byConcept = {}, byReading = {};
  var tOrder = [], cOrder = [], rOrder = [];
  function push(map, order, k, v) {
    if (!map[k]) { map[k] = []; order.push(k); }
    map[k].push(v);
  }
  // 이어짐은 한 항목 안에서 생긴다. 같은 글에 벤야민과 아우라가 함께 적혀
  // 있으면 그 둘은 이어져 있다. 그 셈을 여기서 미리 해 둔다.
  var tCon = {}, tRead = {}, rCon = {}, rThink = {};
  function bump(map, a, b) {
    if (!map[a]) map[a] = {};
    map[a][b] = (map[a][b] || 0) + 1;
  }
  allItems().forEach(function (pair) {
    var it = pair[0], u = it.uses || {};
    var ts = itemThinkers(it), cs = u['개념'] || [], rs = u['읽기'] || [];
    ts.forEach(function (t) { push(byThinker, tOrder, t, pair); });
    cs.forEach(function (c) { push(byConcept, cOrder, c, pair); });
    rs.forEach(function (r) { push(byReading, rOrder, r, pair); });
    ts.forEach(function (t) {
      cs.forEach(function (c) { bump(tCon, t, c); });
      rs.forEach(function (r) { bump(tRead, t, r); bump(rThink, r, t); });
    });
    rs.forEach(function (r) { cs.forEach(function (c) { bump(rCon, r, c); }); });
  });
  // 읽기 묶음이 스스로 담고 있는 이론가. 항목을 거치지 않고 묶음 이름에서 바로 온다.
  // 아직 어느 글에도 쓰지 않은 묶음이 여기서 이론가와 이어진다. 정독노트가
  // 쌓여 있는데 글이 없다는 사실이 화면에서 사라지지 않게 하는 자리다.
  var reading0 = [];
  Object.keys(readings).forEach(function (rid) {
    readingThinkers(readings[rid]).forEach(function (tid) {
      if (!rThink[rid]) rThink[rid] = {};
      if (!rThink[rid][tid]) rThink[rid][tid] = 0;
      if (!tRead[tid]) tRead[tid] = {};
      if (!tRead[tid][rid]) tRead[tid][rid] = 0;
      if (!byThinker[tid] && reading0.indexOf(tid) < 0) reading0.push(tid);
    });
  });

  function ranked(map, order) {
    return order.slice().sort(function (a, b) {
      return cmp(-map[a].length, -map[b].length) || cmp(a, b);
    });
  }

  // 개념의 키는 이름이 아니라 번호다. 이름에 띄어쓰기가 있으면
  // (「일기적 실천」) 띄어쓰기로 가르는 견줌이 무너진다.
  var co = ranked(byConcept, cOrder);
  var ckey = {};
  co.forEach(function (c, i) { ckey[c] = 'c' + i; });
  function conKeys(list) {
    return (list || []).map(function (c) { return ckey[c]; })
      .filter(Boolean).join(' ');
  }
  // 상자 안의 각 줄에도 개념을 달아 둔다. 개념을 고르면 상자만 남기는 것이
  // 아니라 그 개념과 상관없는 줄까지 함께 접힌다.
  function rowTags(pair) { return conKeys((pair[0].uses || {})['개념']); }
  // 개념 하나를 세어 큰 것부터 늘어놓는다
  function conChips(counts) {
    return Object.keys(counts || {}).sort(function (a, b) {
      return cmp(-counts[a], -counts[b]) || cmp(a, b);
    }).map(function (c) {
      return chip('c', c, counts[c], 'data-pick="' + esc(ckey[c] || '') + '"');
    }).join('');
  }

  var out = [headHtml('materials', '재료')];
  out.push('<p class="lede">무엇으로 썼나. 읽은 것이 먼저 있고 거기서 이론가와 개념이 나온다. '
    + '읽기 묶음은 파일 하나가 아니라 드롭박스에 쌓인 정독노트 한 뭉치를 가리킨다. '
    + '아래에서 개념을 하나 고르면 그 개념이 지나간 자리만 남는다.</p>');
  out.push('<div class="jump">'
    + '<a href="#readings">읽기</a><a href="#thinkers">이론가와 개념</a>'
    + '<a href="#reuse" class="hot">다시 쓸 것 · CV와 지원서</a>'
    + '<a href="#people">사람</a></div>');

  // 개념 고르는 줄. 어느 섹션에도 들어 있지 않으므로 읽기와 이론가를 함께 거른다.
  out.push(filtersHtml(
    [['*', '전체', co.length]].concat(co.map(function (c) {
      return [ckey[c], c, byConcept[c].length];
    })), '개념으로 골라 보기'));

  // 읽기. 여기가 시작이다. 아직 어느 글에도 안 쓴 묶음도 자리를 지킨다.
  var ro = Object.keys(readings);
  var rbody = ro.map(function (rid) {
    var r = readings[rid], e = byReading[rid] || [];
    var name = r.url
      ? '<a href="' + esc(r.url) + '" target="_blank" rel="noopener">' + esc(r.name) + '</a>'
      : esc(r.name);
    var ths = readingThinkers(r);
    Object.keys(rThink[rid] || {}).forEach(function (t) {
      if (ths.indexOf(t) < 0) ths.push(t);
    });
    var chips = chipRows([
      ['이론가', ths.map(function (tid) {
        var t = thinkers[tid] || { name: tid };
        return chip('t', t.name, (rThink[rid] || {})[tid] || null,
          'data-goto="t-' + esc(tid) + '"');
      }).join('')],
      ['개념', conChips(rCon[rid])]
    ]);
    var inner = e.length
      ? '<div class="history"><div class="cap">여기서 이어진 글 · <b>' + e.length + '</b>편</div>'
        + historyRows(e, true, rowTags) + '</div>'
      : '<p class="note">읽고 적어 두었으나 아직 어느 글에도 쓰지 않았다.</p>';
    return '<section class="venue-block" id="r-' + esc(rid) + '"'
      + ' data-tags="' + esc(Object.keys(rCon[rid] || {}).map(function (c) {
          return ckey[c];
        }).filter(Boolean).join(' ')) + '">\n'
      + '<div class="venue-head"><h3>' + name + '</h3><span class="sub">'
      + esc(r.sub || '') + '</span></div>\n'
      + chips + '\n' + inner + '</section>';
  }).join('');
  out.push(secbox('읽기', ro.length,
    '<p class="lede">읽은 것을 묶음으로 둔다. 묶음마다 그 안에서 나온 이론가와 개념이 붙어 '
    + '있고, 이름을 누르면 드롭박스의 노트로 간다.</p>' + rbody, 'readings'));

  // 이론가와 개념을 한 상자에 둔다. 이론가가 기둥이고 개념이 그 아래 붙는다.
  var to = ranked(byThinker, tOrder);
  function thinkerCard(tid) {
    var t = thinkers[tid] || { name: tid };
    var e = byThinker[tid];
    var chips = chipRows([
      ['개념', conChips(tCon[tid])],
      ['읽기', Object.keys(tRead[tid] || {}).map(function (rid) {
        var r = readings[rid] || { name: rid };
        return chip('r', r.name, null, 'data-goto="r-' + esc(rid) + '"');
      }).join('')]
    ]);
    return '<section class="venue-block' + (e ? '' : ' loose') + '" id="t-' + esc(tid) + '"'
      + ' data-tags="' + esc(Object.keys(tCon[tid] || {}).map(function (c) {
          return ckey[c];
        }).filter(Boolean).join(' ')) + '">\n'
      + '<div class="venue-head"><h3>' + esc(t.name) + '</h3><span class="sub">'
      + esc(t.sub || '') + '</span></div>\n'
      + chips + '\n'
      + (e
         ? '<div class="history"><div class="cap">참고한 글 · <b>' + e.length + '</b>편</div>'
           + historyRows(e, true, rowTags) + '</div>'
         : '<p class="note">읽는 중이다. 아직 어느 글에도 쓰지 않았다.</p>')
      + '</section>';
  }
  var tbody = to.map(thinkerCard).join('')
    + (reading0.length
       ? '<p class="lede loose-cap">아래는 읽고 있으나 아직 글로 옮기지 않은 이론가다.</p>'
         + reading0.map(thinkerCard).join('')
       : '');

  // 아직 사람과 묶이지 않은 개념. 여기 오래 남아 있으면 읽을 것이 하나 밀려 있다는 뜻이다.
  var loose = co.filter(function (c) { return !Object.keys(tCon).some(function (t) { return tCon[t][c]; }); });
  var lbody = loose.map(function (c) {
    var e = byConcept[c];
    return '<section class="venue-block loose" id="c-' + esc(ckey[c]) + '"'
      + ' data-tags="' + esc(ckey[c]) + '">\n'
      + '<div class="venue-head"><h3>' + esc(c) + '</h3><span class="sub">이론가 없이 쓴 개념</span></div>\n'
      + '<div class="history"><div class="cap">쓴 글 · <b>' + e.length + '</b>편</div>'
      + historyRows(e, true, rowTags) + '</div></section>';
  }).join('');

  out.push(secbox('이론가와 개념', to.length + reading0.length,
    '<p class="lede">이론가마다 그 사람과 같은 글에 적힌 개념이 붙어 있다. '
    + '개념을 누르면 위의 고르는 줄이 함께 움직인다.</p>'
    + tbody
    + (lbody ? '<p class="lede loose-cap">아래 개념은 아직 어느 이론가와도 같은 글에 놓이지 않았다.</p>'
        + lbody : ''), 'thinkers'));

  if (D.reuse && D.reuse.length) {
    var rs = D.reuse.map(function (r) {
      return '<div class="reuse"><div><p class="what">' + esc(r['이름'])
        + '</p><p class="from">' + esc(r['어디'] || '') + '</p></div><div class="to">'
        + (r['쓸 곳'] || []).map(function (x) { return '<span>' + esc(x) + '</span>'; }).join('')
        + '</div>'
        + (r.url ? '<a class="link file" href="' + esc(r.url) + '" target="_blank" rel="noopener">'
                   + esc(r['파일'] || '파일') + '</a>' : '')
        + '</div>';
    }).join('');
    out.push(fold('다시 쓸 것', D.reuse.length,
      '<p class="lede">한 번 쓴 글의 어느 부분을 다음에 어디로 쓸지. '
      + '지원서를 쓸 때 여기부터 본다.</p><div class="reuses">' + rs + '</div>', 'reuse'));
  }
  if (D.people && D.people.length) {
    var ps = D.people.map(function (pp) {
      var last = (pp['마지막'] || '').length === 10
        ? '<span class="last" data-since="' + esc(pp['마지막']) + '"></span>'
        : '<span class="last">' + esc(pp['마지막'] || '') + '</span>';
      return '<div class="who-row"><span class="nm">' + esc(pp['이름']) + '</span>'
        + '<span class="role">' + esc(pp['몫'] || '') + '</span>' + last
        + '<p class="n">' + esc(pp['메모'] || '') + '</p></div>';
    }).join('');
    out.push(fold('사람', D.people.length,
      '<p class="lede">누구에게 무엇을 언제 부탁했나. '
      + '같은 사람에게 자주 갈 수는 없다.</p><div class="whos">' + ps + '</div>', 'people'));
  }
  out.push(footHtml());
  return { html: out.join('') };
}

/* ── 지난 일 ─────────────────────────────────────────────────────────────── */

/* ── 공고 ────────────────────────────────────────────────────────────────
   하루 두 번 도는 루틴이 워커의 /jobs 에 밀어 넣는다. 판에 들어가지 않으므로
   세션을 열지 않아도 쌓이고, 이 화면이 그때그때 읽어 온다.
   담아 두면 kept 가 서고, 버리면 지워져 다음 회차에 다시 오지 않는다. */

function jobsLive() {
  return Object.keys(JOB).map(function (k) {
    var j = JOB[k] || {}; j.id = j.id || k; return j;
  }).filter(function (j) { return !jobDead(j); });
}

function jobFresh(j) {
  if (!j.posted) return false;
  return (Date.now() - fromIso(j.posted)) < 7 * 864e5;
}

/* 마감이 지난 것은 여드레 뒤에 내린다. 마감을 못 찾은 것은 올라온 날에서
   마흔닷새를 세고 내린다. 그러지 않으면 쉰 건이 영영 쌓인 채로 남는다. */
function jobDead(j) {
  if (j.kept) return false;
  if (j.deadline && String(j.deadline).length === 10) {
    return (Date.now() - fromIso(j.deadline)) > 8 * 864e5;
  }
  if (j.posted && String(j.posted).length === 10) {
    return (Date.now() - fromIso(j.posted)) > 45 * 864e5;
  }
  return false;
}

function buildJobs() {
  var out = [headHtml('jobs', '공고')];
  var all = jobsLive();
  NJOB = all.length;

  var kept = all.filter(function (j) { return j.kept; });
  if (kept.length) {
    out.push(secbox('담아 둔 것', kept.length, kept.map(jobCard).join(''), 'jobkept', true));
  }

  // 루틴이 갈래를 여러 말로 적어 보낸 적이 있다. 아는 말 둘로 모으고,
  // 모르는 말이 오면 「그 밖」으로 떨어뜨린다. 판에서 통째로 사라지지 않게.
  function strandOf(j) {
    var s = String(j.strand || '').replace(/\s/g, '');
    if (!s) return '연구소';
    if (s.indexOf('연구') >= 0) return '연구소';
    if (s.indexOf('강의') >= 0 || s.indexOf('영국') >= 0) return '강의';
    return '그 밖';
  }
  var box = { '연구소': [], '강의': [], '그 밖': [] };
  all.forEach(function (j) { if (!j.kept) box[strandOf(j)].push(j); });

  [['연구소', '연구소'], ['강의', '영국 강의직'], ['그 밖', '그 밖']].forEach(function (st) {
    var rows = box[st[0]];
    if (!rows.length) return;
    rows.sort(function (a, b) {
      var fa = jobFresh(a) ? 0 : 1, fb = jobFresh(b) ? 0 : 1;
      if (fa !== fb) return fa - fb;
      return cmp(a.deadline || '9999', b.deadline || '9999');
    });
    out.push(secbox(st[1], rows.length, rows.map(jobCard).join(''), 'job' + st[0], true));
  });

  if (!all.length) {
    out.push('<p class="lede" style="padding:18px 2px">열려 있는 공고가 없습니다. '
      + '루틴은 아침 아홉 시와 저녁 여섯 시에 돕니다.</p>');
  }

  out.push(footHtml());
  return { html: out.join('') };
}

function jobCard(j) {
  var facts = [];
  if (j.posted) facts.push('<span><span class="lab">올라온 날</span><b>' + dots(j.posted) + '</b></span>');
  if (j.deadline) facts.push('<span><span class="lab">마감</span><b data-deadline="'
    + esc(j.deadline) + '" data-wide="1"></b></span>');
  var tag = j.region ? '<span class="sub">[' + esc(j.region) + ']</span>' : '';
  var fresh = jobFresh(j) ? '<span class="mark live">새로 올라옴</span>' : '';
  var title = j.url
    ? '<a href="' + esc(j.url) + '" target="_blank" rel="noopener">' + esc(j.title) + '</a>'
    : esc(j.title);
  var acts = '<div class="jobacts">'
    + '<button type="button" class="jkeep" data-id="' + esc(j.id) + '">'
    + (j.kept ? '담아 둠' : '담아두기') + '</button>'
    + '<button type="button" class="jdrop" data-id="' + esc(j.id) + '">버리기</button>'
    + '</div>';
  return '<section class="venue-block" data-job="' + esc(j.id) + '">\n'
    + '<div class="venue-head"><h3>' + title + '</h3>' + tag + fresh + '</div>\n'
    + (facts.length ? '<div class="venue-facts">' + facts.join('') + '</div>' : '') + '\n'
    + (j.note ? '<p class="note">' + esc(j.note) + '</p>' : '') + '\n'
    + acts + '</section>';
}

/* 두 단추. 누르면 워커에 바로 보낸다. 모아 두었다 보내지 않는다. 수가 적다. */
function bindJobs(app) {
  var lt = (D.meta && D.meta.ledger) || '';
  if (!lt) return;
  var q = '?k=' + encodeURIComponent(lt);
  function send(body, el) {
    el.disabled = true;
    return fetch('/gongo' + q, { method: 'POST',
        headers: { 'content-type': 'application/json' }, body: JSON.stringify(body) })
      .then(function (r) { if (!r.ok) throw 0; return r.json(); })
      .then(function (m) { JOB = m; render('jobs', app); })
      .catch(function () { el.disabled = false; el.textContent = '안 됐습니다'; });
  }
  app.querySelectorAll('.jkeep').forEach(function (b) {
    b.addEventListener('click', function () {
      var id = b.dataset.id, j = JOB[id];
      if (!j) return;
      var row = {}; for (var k in j) row[k] = j[k];
      row.kept = !j.kept;
      var set = {}; set[id] = row;
      send({ set: set }, b);
    });
  });
  app.querySelectorAll('.jdrop').forEach(function (b) {
    b.addEventListener('click', function () { send({ del: [b.dataset.id] }, b); });
  });
}

function buildArchive() {
  var out = [headHtml('archive', '지난 일')];
  var years = {}, order = [];
  (D.archive || []).forEach(function (it) {
    // 날짜는 연월까지만 아는 것도 있다. 그런 것은 연도만 떼어 묶는다
    var dd = it.dates || {};
    var y = (dd.decided || dd.sent || '').slice(0, 4) || '해 모름';
    if (!years[y]) { years[y] = []; order.push(y); }
    years[y].push(it);
  });
  order.slice().sort(function (a, b) { return cmp(b, a); }).forEach(function (y) {
    var body = years[y].map(function (it) {
      var st = statusOf(it, 'done');
      var cls = { live: 'live', stop: 'stop' }[st.tone] || '';
      var d = it.dates || {};
      var facts = [];
      if (d.sent) facts.push('<span><span class="lab">낸 날</span><b>' + dots(d.sent) + '</b></span>');
      if (d.decided) facts.push('<span><span class="lab">결과</span><b>' + dots(d.decided) + '</b></span>');
      var rv = it.review;
      var gist = rv ? '<p class="gist">' + esc(rv.gist) + '<span class="who">'
                      + esc(rv.who || '') + '</span></p>' : '';
      return '<section class="venue-block t-' + esc(st.tone || 'done') + '">\n'
        + '<div class="venue-head"><h3>' + esc(it.title) + '</h3><span class="sub">'
        + esc(it.kind || '') + '</span>\n'
        + '<span class="mark ' + cls + '">' + esc(st.label) + '</span></div>\n'
        + (facts.length ? '<div class="venue-facts">' + facts.join('') + '</div>' : '') + '\n'
        + gist + '\n'
        + (it.note ? '<p class="note">' + esc(it.note) + '</p>' : '') + '\n'
        + linksHtml(it) + '</section>';
    }).join('');
    out.push(secbox(String(y), years[y].length, body));
  });
  out.push(footHtml());
  return { html: out.join('') };
}

/* ── 달력 ────────────────────────────────────────────────────────────────── */

/* 냈고 답을 기다리는 것들. 며칠째인지와 언제쯤 물어야 하는지.
   `답까지` 는 그 지면이 대개 며칠 걸리는지다. 넘어가면 붉어진다.
   모르면 비워 둔다. 지어내지 않는다. */
function waitingClock() {
  var rows = [];
  (D.sections || []).forEach(function (sec) {
    (sec.items || []).forEach(function (it) {
      var d = it.dates || {};
      var st = (D.statuses || {})[it.status] || {};
      if (!d.sent || st.tone !== 'wait') return;
      var v = VEN[it.venue] || {};
      var days = v['답까지'];
      var side = [];
      if (days) side.push('<span class="lab">보통</span>' + days + '일');
      if (d.expected) side.push('<span class="lab">짐작</span>' + dots(d.expected));
      var body = '';
      if (it.next) body += '<p class="todo">' + esc(it.next) + '</p>';
      if (it.note) body += '<p class="note">' + esc(it.note) + '</p>';
      body += linksHtml(it);
      // 바깥 상자에는 data-since 를 걸지 않는다.
      // 날수를 적는 손이 그 상자의 안을 통째로 지워 버린다.
      rows.push('<details class="clock" data-sent="' + esc(d.sent) + '"'
        + (days ? ' data-days="' + days + '"' : '')
        + (d.expected ? ' data-until="' + esc(d.expected) + '"' : '') + '><summary>'
        + '<span class="el" data-since="' + esc(d.sent) + '"></span>'
        + '<span class="t">' + esc(it.title) + '</span>'
        + '<span class="v">' + esc(v.name || '') + '</span>'
        + '<span class="side">' + side.map(function (s) { return '<span>' + s + '</span>'; }).join('')
        + '</span><span class="arrow">▸</span></summary>'
        + '<div class="clock-body">' + body + '</div></details>');
    });
  });
  if (!rows.length) return '';
  return secbox('보낸 것', rows.length, '<div class="clocks">' + rows.join('') + '</div>');
}

/* 달력. 날짜는 페이지가 열릴 때 그린다. 그래야 오늘이 늘 가운데 온다.
   연월까지만 아는 날짜는 찍지 않는다. 하루를 지어내야 하기 때문이다. */
/* 짐작으로 적어 둔 되풀이는 그 날이 오기 전에 확인해야 한다. 지금은 달력에
   「짐작」이라는 글자만 붙어 있고 확인하라는 말이 어디에도 없다. 예순 날 앞에서부터
   여기 세운다. 그 낼 곳에 올해 마감이 이미 확정돼 있으면 세우지 않는다. */
function guessChecks() {
  var today = today0(), rows = [];
  (D.repeats || []).forEach(function (r) {
    if (!r['짐작']) return;

    var fixed = VEN[r.venue] && VEN[r.venue].deadline
      && VEN[r.venue].deadline >= isoOf(today);
    (D.sections || []).forEach(function (sec) {
      (sec.items || []).forEach(function (it) {
        var dl = (it.dates || {}).deadline;
        if (it.venue === r.venue && dl && dl >= isoOf(today)) fixed = true;
      });
    });
    if (fixed) return;

    var next = null;
    for (var o = 0; o <= 14 && !next; o++) {
      var m = new Date(today.getFullYear(), today.getMonth() + o, 1);
      var yy = m.getFullYear(), mn = m.getMonth() + 1;
      if ((r.months || []).indexOf(mn) < 0) continue;
      var last = new Date(yy, mn, 0).getDate();
      var day = (typeof r.day === 'number') ? Math.min(r.day, last) : last;
      var dt = new Date(yy, mn - 1, day);
      if (dt >= today) next = dt;
    }
    if (!next) return;
    var n = Math.round((next - today) / 86400000);
    if (n > 60) return;
    rows.push({ r: r, n: n, iso: isoOf(next) });
  });
  if (!rows.length) return '';

  rows.sort(function (a, b) { return a.n - b.n; });
  var body = rows.map(function (x) {
    var v = VEN[x.r.venue] || {};
    var nm = v.url
      ? '<a href="' + esc(v.url) + '" target="_blank" rel="noopener">' + esc(v.name || '') + '</a>'
      : esc(v.name || '');
    return '<div class="rep"><span class="when">' + esc(dots(x.iso)) + ' 무렵</span>'
      + '<span class="t">' + esc(x.r.label) + '</span>'
      + (nm ? '<span class="vn">' + nm + '</span>' : '')
      + '<span class="guess">짐작</span>'
      + (x.r.note ? '<span class="n">' + esc(x.r.note) + '</span>' : '')
      + '</div>';
  }).join('');
  return secbox('올해 날짜를 확인할 것', rows.length,
    '<p class="lede" style="padding:2px 2px 10px">지난해 날짜로 적어 둔 것입니다. '
    + '낼 곳을 열어 올해 마감을 확인하고 판에 옮겨 주세요.</p>'
    + '<div class="reps">' + body + '</div>');
}

function buildCalendar() {
  var ev = [];
  (D.sections || []).forEach(function (sec) {
    (sec.items || []).forEach(function (it) {
      var d = it.dates || {}, v = VEN[it.venue];
      var nm = it.title + (v ? ' · ' + v.name : '');
      // 낸 날이 있으면 그 마감은 지켰다. 지난 마감을 다 놓친 것으로 칠할 수 없다
      if (d.deadline) ev.push({ d: d.deadline, k: '마감', t: nm, done: !!d.sent });
      if (d.sent) ev.push({ d: d.sent, k: '냄', t: nm });
    });
  });
  (D.archive || []).forEach(function (it) {
    var d = it.dates || {};
    if (d.decided) ev.push({ d: d.decided, k: '결과', t: it.title });
  });
  // 처의 마감. 항목이 이미 같은 날 같은 처로 걸려 있으면 넣지 않는다.
  var taken = {};
  (D.sections || []).forEach(function (sec) {
    (sec.items || []).forEach(function (it) {
      var dl = (it.dates || {}).deadline;
      if (dl && it.venue) taken[dl + ' ' + it.venue] = 1;
    });
  });
  (D.venueGroups || []).forEach(function (g) {
    g.venues.forEach(function (v) {
      if (v.deadline && !taken[v.deadline + ' ' + v.id]) {
        ev.push({ d: v.deadline, k: '마감', t: v.name });
      }
    });
  });
  // 담아 둔 공고의 마감. 담지 않은 것까지 올리면 마흔 몇 건이 달력을 덮는다
  jobsLive().forEach(function (j) {
    if (!j.kept || !j.deadline) return;
    ev.push({ d: j.deadline, k: '공고 마감', t: j.title });
  });

  ev = ev.filter(function (e) { return String(e.d).length === 10; });

  // 같은 날 같은 글은 한 번만
  var uniq = [], seen = {};
  ev.slice().sort(function (a, b) { return cmp(a.d, b.d) || cmp(a.t, b.t); })
    .forEach(function (e) {
      var k = [e.d, e.k, e.t].join(' ');
      if (!seen[k]) { seen[k] = 1; uniq.push(e); }
    });

  // 되풀이하는 것들. 날짜는 브라우저가 그 달에 맞춰 짓는다
  var reps = (D.repeats || []).map(function (r) {
    var v = VEN[r.venue] || {};
    return { m: r.months, day: r.day === undefined ? '말일' : r.day,
             t: r.label + (VEN[r.venue] ? ' · ' + v.name : ''),
             k: r.kind || '되풀이', guess: !!r['짐작'] };
  });

  var out = [headHtml('calendar', '달력')];
  out.push(guessChecks());
  out.push(waitingClock());
  if (D.repeats && D.repeats.length) {
    var rl = D.repeats.map(function (r) {
      var day = (r.day === undefined || r.day === null) ? '말일' : r.day;
      return '<div class="rep"><span class="when">' + r.months.join('·') + '월 '
        + (typeof day === 'string' ? day : day + '일') + '</span>'
        + '<span class="t">' + esc(r.label) + '</span>'
        + (VEN[r.venue] ? '<span class="vn">' + esc(VEN[r.venue].name) + '</span>' : '')
        + (r['짐작'] ? '<span class="guess">짐작</span>' : '')
        + (r.note ? '<span class="n">' + esc(r.note) + '</span>' : '')
        + '</div>';
    }).join('');
    out.push(fold('해마다 돌아오는 것', D.repeats.length, '<div class="reps">' + rl + '</div>'));
  }
  out.push(secbox('한 해', null,
    '<div class="cal-legend"><span><b>굵은 날</b> 무엇인가 있는 날</span>\n'
    + '<span><b>붉은 밑줄</b> 일주일 안 마감</span><span><b>주황 밑줄</b> 한 달 안 마감</span>\n'
    + '<span><b>네모</b> 오늘</span></div>\n'
    + '<div class="cal-grid" id="cal"></div>'));
  out.push(footHtml());
  return { html: out.join(''), ev: uniq, rep: reps };
}

/* ── 그린 뒤에 움직이는 것들 ─────────────────────────────────────────────── */

function today0() { var t = new Date(); t.setHours(0, 0, 0, 0); return t; }
function fromIso(iso) { var p = iso.split('-'); return new Date(+p[0], +p[1] - 1, +p[2]); }
function isoOf(dt) {
  return dt.getFullYear() + '-' + String(dt.getMonth() + 1).padStart(2, '0')
       + '-' + String(dt.getDate()).padStart(2, '0');
}

/* 남은 날수. 열 때마다 오늘 기준으로 다시 센다. */
function paintDates(root) {
  var today = today0();
  root.querySelectorAll('[data-deadline]').forEach(function (el) {
    var n = Math.round((fromIso(el.dataset.deadline) - today) / 86400000);
    var urg = n < 0 ? 'past' : n <= 7 ? 'now' : n <= 30 ? 'soon' : 'later';
    // 지난 마감. 좁은 칸에서는 숫자만 크게 두고 아랫줄에 말을 붙인다.
    el.textContent = n < 0 ? (el.dataset.wide ? (-n) + '일 지남' : String(-n))
                   : n === 0 ? '오늘' : 'D-' + n;
    el.dataset.urgency = urg;
    if (n < 0 && !el.dataset.wide && el.parentNode) {
      var dt = el.parentNode.querySelector('.date[data-d]');
      if (dt) dt.textContent = '일 지남 · ' + dt.dataset.d;
    }
  });
  root.querySelectorAll('[data-since]').forEach(function (el) {
    var n = Math.round((today - fromIso(el.dataset.since)) / 86400000);
    el.textContent = n + '일째';
    // 그 지면이 대개 걸리는 날수를 넘겼으면 물어볼 때다
    var box = el.closest('.clock');
    if (!box) return;
    if (box.dataset.days && n > +box.dataset.days) box.dataset.late = '1';
    // 답이 올 달만 아는 것도 있다. 그 달이 다 가면 물어볼 때다
    var u = box.dataset.until;
    if (u && u.length >= 7) {
      var y = +u.slice(0, 4), mo = +u.slice(5, 7);
      if (today > new Date(y, mo, 0)) box.dataset.late = '1';
    }
  });
  // 마지막으로 마지막 작업일. 오래 멎어 있으면 눈에 띄게 한다
  root.querySelectorAll('.touch[data-touched]').forEach(function (el) {
    var n = Math.round((today - fromIso(el.dataset.touched)) / 86400000);
    if (n <= 7) { el.textContent = n <= 0 ? '오늘 작업' : n + '일 전 작업'; }
    else if (n <= 20) { el.textContent = n + '일 전 작업'; el.dataset.cold = '1'; }
    else { el.textContent = n + '일째 멈춤'; el.dataset.stalled = '1'; }
  });
}

/* 밝기 단추. 고른 값은 이 기기에 남는다. */
function bindTheme(root) {
  var html = document.documentElement;
  function paint() {
    var m = html.dataset.theme || 'auto';
    root.querySelectorAll('.mode button').forEach(function (b) {
      b.setAttribute('aria-pressed', b.dataset.mode === m);
    });
  }
  root.querySelectorAll('.mode button').forEach(function (b) {
    b.addEventListener('click', function () {
      html.dataset.theme = b.dataset.mode;
      try { localStorage.setItem('loggia.theme', b.dataset.mode); } catch (e) {}
      paint();
    });
  });
  paint();
}

/* 섹션의 펼침과 접힘을 이 기기에 남긴다.
   자리표로 뛰어든 섹션은 접혀 있어도 열어 준다. */
function bindSections(root, page) {
  function openHash() {
    var el = location.hash && document.querySelector(location.hash);
    if (el && el.tagName === 'DETAILS' && !el.open) { el.open = true; el.scrollIntoView(); }
  }
  addEventListener('hashchange', openHash);
  setTimeout(openHash, 0);
  root.querySelectorAll('details.group[data-k]').forEach(function (d) {
    var key = 'loggia.sec.' + page + '.html.' + d.dataset.k;
    try { var v = localStorage.getItem(key); if (v !== null) d.open = v === '1'; } catch (e) {}
    d.addEventListener('toggle', function () {
      if (d.dataset.auto) return;   // 필터가 연 것은 기억하지 않는다
      try { localStorage.setItem(key, d.open ? '1' : '0'); } catch (e) {}
    });
  });
}

/* 필터. 누른 단추의 키를 가진 상자만 남긴다.

   필터는 두 군데에 놓일 수 있다. 섹션 밖에 있으면 페이지의 모든 섹션을 거르고,
   섹션 안에 있으면 자기가 속한 섹션 안만 거른다. 재료 페이지의 개념 필터는
   섹션 밖에 있다. 개념 하나를 고르면 읽기 묶음과 이론가가 함께 걸러져야
   이어짐이 보이기 때문이다. */
function bindFilters(root) {
  root.querySelectorAll('.filters').forEach(function (bar) {
    var own = bar.closest('details.group');
    var groups = own ? [own] : [].slice.call(root.querySelectorAll('.group'));
    groups.forEach(function (g) {
      var c = g.querySelector('.c');
      if (c) c.dataset.all = c.textContent;
    });
    bar.addEventListener('click', function (e) {
      var b = e.target.closest('button');
      if (!b) return;
      var k = b.dataset.filter;
      bar.querySelectorAll('button').forEach(function (x) {
        x.setAttribute('aria-pressed', x === b);
      });
      groups.forEach(function (g) {
        // 거를 것이 하나도 없는 섹션은 건드리지 않는다. 낼 곳의 「길목」과
        // 「새겨 둘 것」이 그렇다. 건드리면 단추를 한 번 누른 뒤로 그 둘이
        // 사라지고 「전체」로 돌아와도 오지 않는다.
        var taggable = g.querySelectorAll('[data-tags]');
        if (!taggable.length) return;
        var seen = 0;
        taggable.forEach(function (el) {
          var hay = ' ' + el.dataset.tags + ' ';
          var on = k === '*' || k.split(' ').some(function (kk) {
            return hay.indexOf(' ' + kk + ' ') >= 0;
          });
          el.hidden = !on;
          if (on) seen++;
          // 상자를 남기는 데서 그치지 않고 그 안의 줄도 함께 줄인다. 상자만
          // 남기면 벤야민 밑에 아우라와 상관없는 글이 그대로 남아 이어짐이
          // 있는 것처럼 보인다.
          var rows = el.querySelectorAll('[data-rowtags]');
          if (!rows.length) return;
          var n = 0;
          rows.forEach(function (r) {
            var ok = k === '*' || (' ' + r.dataset.rowtags + ' ').indexOf(' ' + k + ' ') >= 0;
            r.hidden = !ok;
            if (ok) n++;
          });
          var cap = el.querySelector('.history .cap b');
          if (cap) {
            if (cap.dataset.all === undefined) cap.dataset.all = cap.textContent;
            cap.textContent = k === '*' ? cap.dataset.all : n;
          }
        });
        // 제 필터가 든 섹션은 감추지 않는다. 감추면 필터도 함께 사라진다.
        if (g !== own) g.hidden = seen === 0;
        // 거른 것이 접힌 섹션 안에 있으면 안 보인다. 열어 준다.
        // 다만 이 열기는 기억하지 않는다. 손으로 접어 둔 뜻을 지우면 안 된다.
        if (k !== '*' && seen && g !== own && g.tagName === 'DETAILS' && !g.open) {
          g.dataset.auto = '1'; g.open = true;
        } else if (k === '*' && g.dataset.auto) {
          g.dataset.auto = ''; g.open = false;
        }
        var c = g.querySelector('.c');
        if (c) c.textContent = k === '*' ? c.dataset.all : seen;
      });
    });
  });
}

/* 상자 안에 붙은 이름표. 개념을 누르면 위의 고르는 줄이 함께 눌리고,
   이론가나 읽기 묶음을 누르면 그 상자로 건너간다. 재료 페이지에서
   이론가와 개념과 읽기가 서로 이어져 있다는 것을 손으로 확인하는 자리다. */
function bindChips(root) {
  function bar() { return root.querySelector('.filters'); }
  function press(key) {
    var f = bar();
    if (!f) return;
    var b = f.querySelector('button[data-filter="' + key + '"]');
    if (!b) return;
    b.click();
    var r = f.getBoundingClientRect();
    if (r.top < 0 || r.bottom > innerHeight) f.scrollIntoView({ block: 'center' });
  }
  // 고르는 줄에서 무엇을 눌렀는지 상자 안의 이름표에도 표시한다.
  // 그래야 지금 보고 있는 것이 어느 개념으로 걸러진 것인지 잊지 않는다.
  var f0 = bar();
  if (f0) f0.addEventListener('click', function (e) {
    var b = e.target.closest('button');
    if (!b) return;
    var k = b.dataset.filter;
    root.querySelectorAll('.chip.c').forEach(function (c) {
      c.setAttribute('aria-pressed', k !== '*' && c.dataset.pick === k);
    });
  });
  root.addEventListener('click', function (e) {
    var b = e.target.closest('.chip');
    if (!b) return;
    if (b.dataset.pick) { press(b.dataset.pick); return; }
    var id = b.dataset.goto;
    if (!id) return;
    // 걸러 놓은 채로 건너가면 가려는 상자가 접혀 있을 수 있다. 먼저 전체로 돌린다.
    press('*');
    var el = root.querySelector('#' + id.replace(/([^\w-])/g, '\\$1'));
    if (!el) return;
    var d = el.closest('details');
    if (d && !d.open) d.open = true;
    el.scrollIntoView({ block: 'start' });
    el.classList.add('lit');
    setTimeout(function () { el.classList.remove('lit'); }, 1400);
  });
}

/* 지난 서른 날에 한 일. 보드를 열면 먼저 눈에 든다 */
function paintTally(root, done) {
  var box = root.querySelector('#tally');
  if (!box) return;
  var today = today0();
  var groups = { '냈다': [], '끝났다': [], '손댔다': [] };
  done.forEach(function (x) {
    var days = Math.round((today - fromIso(x.d)) / 86400000);
    if (days <= 30 && days >= 0) groups[x.k].push(x);
  });
  var names = { '냈다': '낸 것', '끝났다': '끝난 것', '손댔다': '작업한 것' };
  var bits = [];
  ['냈다', '끝났다', '손댔다'].forEach(function (k) {
    if (groups[k].length) bits.push('<button type="button" class="tt" data-k="' + k + '">'
      + names[k] + ' <b>' + groups[k].length + '</b></button>');
  });
  box.innerHTML = bits.length
    ? '<span class="cap">지난 30일</span>' + bits.join('<span class="dot">·</span>') : '';
  if (!bits.length) return;

  /* 숫자를 누르면 그 숫자를 이루는 목록이 뜬다. 셈만 보이면
     무엇을 했는지는 여전히 기억에 기대게 되기 때문이다. */
  var wrap = document.createElement('div');
  wrap.className = 'tmodal'; wrap.hidden = true;
  wrap.innerHTML = '<div class="tm-back"></div>'
    + '<div class="tm-box" role="dialog" aria-modal="true">'
    + '<div class="tm-head"><span class="tm-title"></span>'
    + '<button type="button" class="tm-x" aria-label="닫기">&times;</button></div>'
    + '<ul class="tm-list"></ul></div>';
  root.appendChild(wrap);
  function open(k) {
    var rows = groups[k].slice().sort(function (a, b) { return a.d < b.d ? 1 : -1; });
    wrap.querySelector('.tm-title').textContent = names[k] + ' · 지난 30일 · ' + rows.length + '건';
    wrap.querySelector('.tm-list').innerHTML = rows.map(function (x) {
      return '<li><span class="tm-d">' + x.d.slice(5).replace('-', '.') + '</span>'
        + '<span class="tm-t">' + esc(x.t || '') + '</span></li>';
    }).join('');
    wrap.hidden = false;
  }
  function shut() { wrap.hidden = true; }
  box.addEventListener('click', function (e) {
    var b = e.target.closest('.tt');
    if (b) open(b.dataset.k);
  });
  wrap.querySelector('.tm-back').addEventListener('click', shut);
  wrap.querySelector('.tm-x').addEventListener('click', shut);
  document.addEventListener('keydown', function (e) { if (e.key === 'Escape') shut(); });
}

/* 완료 표시.

   원본을 건드리지 않는다. 데이터는 암호로 잠겨 있고 그 암호는 이 파일에
   없다. 그래서 워커가 기록만 따로 쥔다. 얻는 것이 더 크다. 휴대전화에서 그은
   줄이 노트북에서도 그어진다. 원본에 닿는 것은 다음 갱신 때 사람이 한다.

   저장은 누를 때마다 하지 않고 모았다가 한 번에 보낸다. */
function bindBoard(root) {
  var LT = D.meta.ledger || '';
  var bar = root.querySelector('#carry');
  var dirty = false;

  function allBoxes() { return [].slice.call(root.querySelectorAll('input[data-done]')); }
  function label(b) {
    var el = root.querySelector('label[for="' + b.id + '"]');
    return el ? el.textContent.trim() : b.dataset.done;
  }
  function title(b) {
    var art = b.closest('.entry');
    var t = art && art.querySelector('.title-line .t');
    return t ? t.textContent.trim() : '';
  }
  function mark(b) { b.closest('.step, li').dataset.done = b.checked ? '1' : ''; }
  function lset(b) {
    try { localStorage.setItem('loggia.done.' + b.dataset.done, b.checked ? '1' : '0'); } catch (e) {}
  }

  /* 저장이 끝난 것은 목록에서 내린다. 끝낸 것이 계속 남아 있으면
     무엇이 남았는지가 흐려진다. 「전체 해제」로 되돌릴 수 있다. */
  function tuck() {
    root.querySelectorAll('.entry').forEach(function (art) {
      var bs = [].slice.call(art.querySelectorAll('input[data-done]'));
      var left = 0;
      bs.forEach(function (b) {
        var row = b.closest('.step, li');
        var gone = b.checked && !!SRV[b.dataset.done];
        row.hidden = gone;
        if (!gone) left++;
      });
      var note = art.querySelector('.cleared');
      if (bs.length && left === 0) {
        if (!note) {
          note = document.createElement('p');
          note.className = 'cleared'; note.textContent = '다 끝냈습니다';
          art.querySelector('.body').appendChild(note);
        }
      } else if (note) { note.remove(); }
    });
  }

  function refresh() {
    if (!bar) return;
    var on = allBoxes().filter(function (b) { return b.checked; });
    bar.hidden = on.length === 0 && !dirty;
    var n = bar.querySelector('.n');
    if (n) n.textContent = on.length;
    bar.dataset.text = '로지아 갱신. 아래를 끝냈습니다.\n'
      + on.map(function (b) { return '- ' + title(b) + ' · ' + label(b); }).join('\n');
    var sv = bar.querySelector('.save');
    if (sv) { sv.disabled = !dirty; sv.textContent = dirty ? '저장' : '저장됨'; }
  }

  // 지금 화면 상태와 기록을 견주어 보낼 것만 추린다
  function diff() {
    var set = {}, del = [], d = isoOf(new Date());
    allBoxes().forEach(function (b) {
      var k = b.dataset.done;
      if (b.checked && !SRV[k]) set[k] = { t: title(b), s: label(b), at: d };
      if (!b.checked && SRV[k]) del.push(k);
    });
    return { set: set, del: del };
  }

  function save(quiet) {
    if (!LT || !dirty) return;
    var d = diff();
    if (!Object.keys(d.set).length && !d.del.length) { dirty = false; refresh(); return; }
    var url = '/done?k=' + encodeURIComponent(LT);
    var body = JSON.stringify(d);
    // 창을 덮을 때는 답을 기다릴 수 없다. 흘려보내고 끝낸다
    if (quiet && navigator.sendBeacon) {
      navigator.sendBeacon(url, new Blob([body], { type: 'application/json' }));
      Object.keys(d.set).forEach(function (k) { SRV[k] = d.set[k]; });
      d.del.forEach(function (k) { delete SRV[k]; });
      dirty = false;
      return;
    }
    var sv = bar && bar.querySelector('.save');
    if (sv) { sv.disabled = true; sv.textContent = '저장 중'; }
    fetch(url, { method: 'POST', headers: { 'content-type': 'application/json' }, body: body })
      .then(function (r) { if (!r.ok) throw 0; return r.json(); })
      .then(function (j) { SRV = j; dirty = false; refresh(); tuck(); })
      .catch(function () { if (sv) { sv.disabled = false; sv.textContent = '다시 저장'; } });
  }

  function bind(b) {
    if (b.dataset.bound) return;
    b.dataset.bound = '1';
    var key = 'loggia.done.' + b.dataset.done;
    var srvOn = !!SRV[b.dataset.done];
    try {
      var v = localStorage.getItem(key);
      b.checked = v === null ? srvOn : v === '1';
    } catch (e) { b.checked = srvOn; }
    // 기록이 이미 알고 있는 것은 기록이 옳다. 다른 기기에서 그은 줄이 여기에도 온다
    if (srvOn && !b.checked) { b.checked = true; lset(b); }
    mark(b);
    b.addEventListener('change', function () { lset(b); mark(b); dirty = true; refresh(); });
  }

  /* 데이터에 이미 없는 할 일의 표시는 지운다.
     반영이 끝나면 그 할 일이 데이터에서 빠지므로, 이 기기에 남은 표시가
     갈 곳을 잃는다. 그대로 두면 「끝낸 일 1」이 영영 붙어 있다. */
  function prune() {
    var live = {};
    allBoxes().forEach(function (b) { live['loggia.done.' + b.dataset.done] = 1; });
    try {
      for (var i = localStorage.length - 1; i >= 0; i--) {
        var k = localStorage.key(i);
        if (k && k.indexOf('loggia.done.') === 0 && !live[k]) localStorage.removeItem(k);
      }
    } catch (e) {}
  }

  function rebind() { allBoxes().forEach(bind); prune(); refresh(); tuck(); }
  rebind();

  if (LT) {
    addEventListener('visibilitychange', function () {
      if (document.visibilityState === 'hidden') save(true);
    });
  }

  if (bar) {
    var sbtn = bar.querySelector('.save');
    if (sbtn) sbtn.addEventListener('click', function () { save(false); });
    var cbtn = bar.querySelector('.copy');
    if (cbtn) cbtn.addEventListener('click', function () {
      var t = bar.dataset.text;
      var done = function () {
        var was = cbtn.textContent; cbtn.textContent = '복사했습니다';
        setTimeout(function () { cbtn.textContent = was; }, 1600);
      };
      if (navigator.clipboard) { navigator.clipboard.writeText(t).then(done, done); }
      else {
        var ta = document.createElement('textarea');
        ta.value = t; document.body.appendChild(ta); ta.select();
        try { document.execCommand('copy'); } catch (e) {}
        document.body.removeChild(ta); done();
      }
    });
    bar.querySelector('.clear').addEventListener('click', function () {
      allBoxes().forEach(function (b) {
        if (!b.checked) return;
        b.checked = false; lset(b); mark(b); dirty = true;
      });
      refresh(); tuck();
    });
    refresh();
  }
  return { rebind: rebind, isDirty: function () { return dirty; } };
}

/* 할 일을 직접 추가하는 자리.

   적은 것은 워커의 기록에 바로 들어가고 화면에는 「새로 추가」 표시가 붙는다.
   깃허브 데이터에 들어가는 건 다음 갱신 때다. 그때까지 표시를 붙여 두는 이유는,
   아직 확정되지 않은 것을 확정된 것처럼 보이지 않게 하려는 것이다. */
function bindAdd(root, redrawEntry, board) {
  var LT = D.meta.ledger || '';
  if (!LT) return;
  var fab = root.querySelector('#fab');
  var sheet = root.querySelector('#sheet');
  if (!fab || !sheet) return;
  var form = sheet.querySelector('.sheetform');

  // 기록 한 칸에 보내고, 건드린 항목만 다시 그린다.
  // 화면 전체를 다시 그리면 접어 둔 섹션과 보던 자리가 튄다.
  function post(slot, body, extraIds) {
    var url = '/' + slot + '?k=' + encodeURIComponent(LT);
    return fetch(url, { method: 'POST', headers: { 'content-type': 'application/json' },
                        body: JSON.stringify(body) })
      .then(function (r) { if (!r.ok) throw 0; return r.json(); })
      .then(function (j) {
        var before = slot === 'add' ? ADD : EDIT;
        var ids = {};
        (extraIds || []).forEach(function (x) { ids[x] = 1; });
        [before, j].forEach(function (m) {
          Object.keys(m).forEach(function (k) { if (m[k].item) ids[m[k].item] = 1; });
        });
        if (slot === 'add') ADD = j; else EDIT = j;
        Object.keys(ids).forEach(redrawEntry);
        board.rebind();
      });
  }

  function open_(on) {
    sheet.hidden = !on; fab.hidden = on;
    if (on) sheet.querySelector('.at').focus();
  }

  fab.addEventListener('click', function () { open_(true); });
  sheet.querySelector('.cancel').addEventListener('click', function () {
    form.reset(); open_(false);
  });
  document.addEventListener('keydown', function (e) {
    if (e.key === 'Escape' && !sheet.hidden) { form.reset(); open_(false); }
  });
  /* 이미 있는 할 일을 수정하거나 삭제한다.

     수정해도 키는 처음 글로 만든 그대로 둔다. 그래야 반영할 때 원본에서 그
     할 일을 찾을 수 있다. 사이트에서 적어 넣은 할 일은 아직 원본에 없으므로
     그 자리에서 바로 고친다. */
  root.addEventListener('click', function (e) {
    var b = e.target.closest('[data-edit]');
    if (!b) return;
    var row = b.closest('.step, li');
    if (!row || row.querySelector('.tedit')) return;
    openEditor(row, b.dataset.edit, b.dataset.item);
  });

  function openEditor(row, key, itemId) {
    var fresh = key.indexOf('add:') === 0;
    // 일하는 기간은 할 일이 아니라 항목에 붙는다. 같은 자리에서 함께 고친다.
    var it0 = null;
    allItems().forEach(function (pr) { if (pr[0].id === itemId) it0 = pr[0]; });
    var effs = D.efforts || {};
    var pum0 = it0 ? (it0['품'] || '') : '';
    var pumNow = it0 ? (pumOf(it0) || '') : '';
    var cur = fresh ? (ADD[key.slice(4)] || {})
                    : (EDIT[key] || { t: row.querySelector('label').textContent,
                                      due: (row.querySelector('.sdue') || {}).dataset
                                           ? row.querySelector('.sdue').dataset.deadline : '' });
    var t = cur.t || row.querySelector('label').textContent;
    var due = cur.due || '';
    var form = document.createElement('form');
    form.className = 'tedit';
    var pumSel = it0 && Object.keys(effs).length
      ? '<label class="ef"><span>일하는 기간</span><select>'
        + '<option value="">안 정함</option>'
        + Object.keys(effs).map(function (k) {
            return '<option value="' + esc(k) + '">' + esc(effs[k].label) + '</option>';
          }).join('')
        + '</select></label>'
      : '';
    form.innerHTML =
      '<input type="text" class="et" maxlength="200" required>'
      + pumSel
      + '<div class="erow"><input type="date" class="ed">'
      + '<button type="submit" class="ok">저장</button>'
      + '<button type="button" class="cancel">취소</button>'
      + '<button type="button" class="rm">삭제</button></div>';
    row.appendChild(form);
    form.querySelector('.et').value = t;
    form.querySelector('.ed').value = due;
    if (pumSel) form.querySelector('.ef select').value = pumNow;
    form.querySelector('.et').focus();

    form.querySelector('.cancel').addEventListener('click', function () { form.remove(); });
    form.querySelector('.rm').addEventListener('click', function () {
      if (fresh) post('add', { del: [key.slice(4)] }, [itemId]);
      else { var set = {}; set[key] = { item: itemId, del: true, at: isoOf(new Date()) };
             post('edit', { set: set }, [itemId]); }
    });
    form.addEventListener('submit', function (e) {
      e.preventDefault();
      var nt = form.querySelector('.et').value.trim();
      if (!nt) return;
      var nd = form.querySelector('.ed').value;
      var np = pumSel ? form.querySelector('.ef select').value : pumNow;
      var ok = form.querySelector('.ok');
      ok.disabled = true; ok.textContent = '저장 중';
      var fail = function () { ok.disabled = false; ok.textContent = '다시 시도'; };
      // 기간이 원본과 같아지면 기록에서 지운다. 같은 값을 두 군데 두지 않는다.
      var pumBody = null;
      if (it0 && np !== pumNow) {
        pumBody = np === pum0
          ? { del: ['item:' + itemId] }
          : { set: (function () { var m = {};
                m['item:' + itemId] = { item: itemId, '품': np, at: isoOf(new Date()) };
                return m; })() };
      }
      var set = {};
      if (fresh) {
        var a = ADD[key.slice(4)] || {};
        set[key.slice(4)] = { item: itemId, t: nt, at: a.at || isoOf(new Date()) };
        if (nd) set[key.slice(4)].due = nd;
        post('add', { set: set }, [itemId])
          .then(function () { return pumBody ? post('edit', pumBody, [itemId]) : null; })
          .catch(fail);
      } else {
        set[key] = { item: itemId, t: nt, at: isoOf(new Date()) };
        if (nd) set[key].due = nd;
        var body = { set: set };
        if (pumBody && pumBody.set) {
          Object.keys(pumBody.set).forEach(function (k2) { set[k2] = pumBody.set[k2]; });
        } else if (pumBody && pumBody.del) {
          body.del = pumBody.del;
        }
        post('edit', body, [itemId]).catch(fail);
      }
    });
  }

  form.addEventListener('submit', function (e) {
    e.preventDefault();
    var t = form.querySelector('.at').value.trim();
    if (!t) return;
    var due = form.querySelector('.ad').value;
    var row = { item: form.querySelector('.ai').value, t: t, at: isoOf(new Date()) };
    if (due) row.due = due;
    var id = (self.crypto && crypto.randomUUID ? crypto.randomUUID()
              : String(Date.now()) + Math.random().toString(36).slice(2)).slice(0, 12);
    var set = {}; set[id] = row;
    var ok = form.querySelector('.ok');
    ok.disabled = true; ok.textContent = '저장 중';
    post('add', { set: set }).then(function () {
      form.reset(); open_(false); ok.textContent = '추가';
    }, function () { ok.textContent = '다시 시도'; })
      .then(function () { ok.disabled = false; });
  });
}

/* 달력의 칸을 그린다. 되풀이하는 것은 그릴 달마다 앉힌다. */
function paintCalendar(root, EV, REP) {
  var box = root.querySelector('#cal');
  if (!box) return;
  var W = ['일', '월', '화', '수', '목', '금', '토'];
  var today = today0();
  var byDay = {};
  EV.forEach(function (e) { (byDay[e.d] = byDay[e.d] || []).push(e); });

  function pad(n) { return (n < 10 ? '0' : '') + n; }
  for (var o = -18; o <= 18; o++) {
    var mm = new Date(today.getFullYear(), today.getMonth() + o, 1);
    var yy = mm.getFullYear(), mn = mm.getMonth() + 1;
    REP.forEach(function (r) {
      if (r.m.indexOf(mn) < 0) return;
      var day = r.day === '말일' ? new Date(yy, mn, 0).getDate() : +r.day;
      var iso = yy + '-' + pad(mn) + '-' + pad(day);
      (byDay[iso] = byDay[iso] || []).push({ d: iso, k: r.k, t: r.t, rep: true, guess: r.guess });
    });
  }

  /* 지난 마감은 놓친 것으로 표시한다. 다만 낸 날이 있는 것과, 항목 없이
     낼 곳에만 적힌 마감은 뺀다. 냈는지 여부를 알 수 없기 때문이다. */
  function urg(e) {
    var n = Math.round((fromIso(e.d) - today) / 86400000);
    if (n < 0) return { n: n, c: (e.done || e.done === undefined) ? '' : 'miss' };
    return { n: n, c: n <= 7 ? 'now' : n <= 30 ? 'soon' : '' };
  }

  for (var off = -6; off <= 6; off++) {
    var m = new Date(today.getFullYear(), today.getMonth() + off, 1);
    var y = m.getFullYear(), mo = m.getMonth();
    var first = new Date(y, mo, 1).getDay(), last = new Date(y, mo + 1, 0).getDate();

    var cell = document.createElement('div');
    cell.className = 'cal-m' + (off === 0 ? ' here' : '') + (off < 0 ? ' past' : '');
    var h = '<h3>' + y + '. ' + (mo + 1) + '</h3><table class="cal"><thead><tr>';
    W.forEach(function (w) { h += '<th>' + w + '</th>'; });
    h += '</tr></thead><tbody><tr>';
    for (var i = 0; i < first; i++) h += '<td class="off">·</td>';
    var rows = [];
    for (var day = 1; day <= last; day++) {
      var iso = y + '-' + pad(mo + 1) + '-' + pad(day);
      var list = byDay[iso];
      var cls = [];
      if (list) {
        cls.push('has');
        var worst = '';
        list.forEach(function (e) {
          if (e.k.indexOf('마감') >= 0 && !e.rep) {
            var u = urg(e).c;
            if (u === 'miss') worst = 'miss';
            else if (worst !== 'miss'
                     && (u === 'now' || (u === 'soon' && worst !== 'now'))) worst = u;
          }
        });
        if (worst) cls.push(worst);
        rows.push({ day: day, iso: iso, list: list });
      }
      if (iso === isoOf(today)) cls.push('today');
      h += '<td class="' + cls.join(' ') + '">' + day + '</td>';
      if ((first + day) % 7 === 0 && day !== last) h += '</tr><tr>';
    }
    h += '</tr></tbody></table>';

    if (rows.length) {
      h += '<div class="cal-ev">';
      rows.forEach(function (r) {
        r.list.forEach(function (e) {
          var u = (e.k.indexOf('마감') >= 0 && !e.rep) ? urg(e).c : '';
          h += '<div class="r ' + u + (e.rep ? ' rep' : '') + '"><span class="dd">' + r.day + '</span>'
             + '<span class="tx">' + esc(e.t) + ' <span style="color:var(--ink-3)">' + esc(e.k)
             + (e.guess ? ' 짐작' : '') + '</span></span></div>';
        });
      });
      h += '</div>';
    } else {
      h += '<div class="cal-none">없음</div>';
    }
    cell.innerHTML = h;
    box.appendChild(cell);
  }
}

/* ── 반영되었는지 지켜보기 ───────────────────────────────────────────────

   워커가 10분마다 체크 기록을 데이터에 반영하고 기록을 비운다. 그때 화면이
   가만히 있으면 「끝낸 일 1 · 저장됨」이 계속 붙어 있어, 반영이 됐는지 안 됐는지
   알 수가 없다.

   그래서 data.enc 가 바뀌었는지 이따금 들여다본다. 기록이 비었는지를 보지
   않는다. 워커가 깃허브에 쓴 다음 클라우드플레어가 다시 배포하기까지 1~2분이
   걸리는데, 그 사이에는 기록만 비어 있고 사이트가 내주는 데이터는 아직 옛
   것이다. 그때 화면을 다시 그리면 끝낸 할 일이 되살아나 보인다.

   파일이 실제로 바뀌었을 때에만 다시 그린다. 그러면 어긋날 일이 없다.
   `_headers` 가 data.enc 에 no-cache 를 걸어 두어서, 안 바뀌었으면 브라우저와
   서버가 304 한 번으로 끝낸다.

   아직 저장하지 않은 것이 있으면 건드리지 않는다. 덮어써 버리면 방금 누른
   것이 사라진다. */

var WATCH = null;

/** 화면 위쪽에 잠깐 뜨는 한 줄. 무슨 일이 일어났는지 알린다. */
function flash(msg) {
  var el = document.getElementById('flash');
  if (!el) {
    el = document.createElement('div');
    el.id = 'flash'; el.className = 'flash';
    document.body.appendChild(el);
  }
  el.textContent = msg;
  el.hidden = false;
  clearTimeout(flash.t);
  flash.t = setTimeout(function () { el.hidden = true; }, 4000);
}

/** 바뀐 data.enc 를 풀어 처음부터 다시 그린다. 키는 이미 손에 있다. */
function reloadAndRender(text, note) {
  var y = window.scrollY;
  var was = [];
  document.querySelectorAll('#app input[data-done]').forEach(function (b) {
    if (b.checked) was.push(b.dataset.done);
  });
  BLOBTEXT = text;
  BLOB = text.trim().split('.');
  return keyFromCache().then(function (k) {
    if (!k) throw new Error('키가 없습니다');
    return decryptWith(k);
  }).then(function (plain) {
    D = JSON.parse(plain);
    indexData();
    return loadLedger();
  }).then(function () {
    var app = document.getElementById('app');
    render(document.body.dataset.page || 'index', app);
    window.scrollTo(0, y);
    var left = {};
    app.querySelectorAll('input[data-done]').forEach(function (b) { left[b.dataset.done] = 1; });
    var gone = was.filter(function (k) { return !left[k]; }).length;
    flash(note || (gone ? '끝낸 일 ' + gone + '개가 데이터에 반영되었습니다'
                        : '새 내용을 받았습니다'));
  });
}

function watchData(page, board) {
  if (WATCH) { clearInterval(WATCH); WATCH = null; }
  if (page !== 'index') return;
  function tick() {
    if (document.visibilityState !== 'visible') return;
    if (board && board.isDirty()) return;
    fetch('data.enc', { cache: 'no-cache' })
      .then(function (r) { return r.ok ? r.text() : null; })
      .then(function (t) {
        if (!t || t === BLOBTEXT) return;
        return reloadAndRender(t);
      })
      .catch(function () {});
  }
  WATCH = setInterval(tick, 30000);
  // visibilitychange 는 document 에서 난다. window 에 걸면 못 받는 경우가 있다.
  document.addEventListener('visibilitychange', function () {
    if (document.visibilityState === 'visible') tick();
  });
}

/* ── 화면 만들기 ─────────────────────────────────────────────────────────── */

var BUILD = {
  index: buildIndex, calendar: buildCalendar, journals: buildJournals,
  materials: buildMaterials, archive: buildArchive, jobs: buildJobs
};

function render(page, app) {
  var r = BUILD[page]();
  app.innerHTML = r.html;
  document.title = 'LOGGIA — ' + (page === 'index' ? D.meta.title
    : { calendar: '달력', journals: '낼 곳', materials: '재료', archive: '지난 일', jobs: '공고' }[page]);
  paintDates(app);
  bindTheme(app);
  bindFilters(app);
  bindChips(app);
  bindSections(app, page);
  if (page === 'jobs') bindJobs(app);
  if (page === 'index') {
    paintTally(app, r.done);
    var itemById = {};
    (D.sections || []).forEach(function (s) {
      (s.items || []).forEach(function (it) { itemById[it.id] = it; });
    });
    var board = bindBoard(app);
    bindAdd(app, function (id) {
      var art = app.querySelector('.entry[data-id="' + (window.CSS && CSS.escape ? CSS.escape(id) : id) + '"]');
      var item = itemById[id];
      if (!art || !item) return;
      var tmp = document.createElement('div');
      tmp.innerHTML = entryHtml(item);
      art.replaceWith(tmp.firstElementChild);
      paintDates(app);
    }, board);
    watchData(page, board);
  }
  if (page === 'calendar') paintCalendar(app, r.ev, r.rep);
}

/* ── 자물쇠 ──────────────────────────────────────────────────────────────── */
/* data.enc 하나만 암호화되어 있다. 솔트도 그 안에 하나뿐이므로, 페이지마다 솔트가
   갈리던 옛 걱정이 없다. */

var ITER = 600000;
var PASS_KEY = 'loggia.pass';
var $ = function (id) { return document.getElementById(id); };
function b64(s) { return Uint8Array.from(atob(s), function (c) { return c.charCodeAt(0); }); }

var BLOB = null;       // ['loggia1', 솔트, 초기값, 덩이]
var BLOBTEXT = '';     // 받아 온 그대로. 바뀌었는지 견주는 데 쓴다

function loadBlob() {
  return fetch('data.enc', { cache: 'no-cache' }).then(function (r) {
    if (!r.ok) throw new Error('data.enc 를 받지 못했습니다');
    return r.text();
  }).then(function (t) {
    var p = t.trim().split('.');
    if (p[0] !== 'loggia1' || p.length !== 4) throw new Error('알아볼 수 없는 형식입니다');
    BLOB = p;
    BLOBTEXT = t;
  });
}

function keyFromPass(pass) {
  return crypto.subtle.importKey('raw', new TextEncoder().encode(pass), 'PBKDF2', false, ['deriveKey'])
    .then(function (km) {
      return crypto.subtle.deriveKey(
        { name: 'PBKDF2', salt: b64(BLOB[1]), iterations: ITER, hash: 'SHA-256' },
        km, { name: 'AES-GCM', length: 256 }, true, ['decrypt']);
    });
}
function decryptWith(k) {
  return crypto.subtle.decrypt({ name: 'AES-GCM', iv: b64(BLOB[2]) }, k, b64(BLOB[3]))
    .then(function (pt) { return new TextDecoder().decode(pt); });
}
function cacheKey() { return 'loggia.key.' + BLOB[1]; }
function keyFromCache() {
  var raw = sessionStorage.getItem(cacheKey());
  if (!raw) return Promise.resolve(null);
  return crypto.subtle.importKey('raw', b64(raw), { name: 'AES-GCM' }, true, ['decrypt']);
}
function cache(k) {
  return crypto.subtle.exportKey('raw', k).then(function (raw) {
    var s = '';
    new Uint8Array(raw).forEach(function (c) { s += String.fromCharCode(c); });
    try { sessionStorage.setItem(cacheKey(), btoa(s)); } catch (e) {}
  });
}

/* 기록 두 개를 먼저 읽어 데이터와 합친다. 그려 놓고 끼워 넣지 않는다. */
function loadLedger() {
  var lt = D.meta.ledger;
  var page = document.body.dataset.page || 'index';
  if (!lt || (page !== 'index' && page !== 'jobs' && page !== 'calendar')) {
    return Promise.resolve();
  }
  var q = '?k=' + encodeURIComponent(lt);
  function get(path) {
    return fetch(path + q, { cache: 'no-store' })
      .then(function (r) { return r.ok ? r.json() : null; })
      .catch(function () { return null; });
  }
  // 달력도 공고를 읽는다. 담아 둔 공고의 마감이 다른 마감과 같은 줄에 서야 한다
  if (page === 'jobs' || page === 'calendar') {
    return get('/gongo').then(function (j) { if (j) JOB = j; NJOB = jobsLive().length; });
  }
  return Promise.all([get('/done'), get('/add'), get('/edit')]).then(function (r) {
    if (r[0]) SRV = r[0];
    if (r[1]) ADD = r[1];
    if (r[2]) EDIT = r[2];
  });
}

function openWith(k, pass, remember) {
  return decryptWith(k).then(function (text) {
    D = JSON.parse(text);
    indexData();
    return cache(k);
  }).then(function () {
    if (pass) {
      try {
        sessionStorage.setItem(PASS_KEY, pass);
        if (remember) localStorage.setItem(PASS_KEY, pass);
      } catch (e) {}
    }
    return loadLedger();
  }).then(function () {
    var app = $('app');
    app.hidden = false;
    $('gate').hidden = true;
    render(document.body.dataset.page || 'index', app);
  });
}

/* 스스로 여는 동안에는 암호 칸을 감춘다. 그대로 두면 다시 묻는 것처럼 보인다. */
function waiting(on) {
  $('f').style.display = on ? 'none' : '';
  $('m').className = 'msg calm';
  $('m').textContent = on ? '여는 중…' : '';
}

function tryOpen(pass, remember) {
  $('go').disabled = true;
  $('m').className = 'msg calm';
  $('m').textContent = '여는 중…';
  return keyFromPass(pass).then(function (k) { return openWith(k, pass, remember); })
    .catch(function () {
      $('go').disabled = false;
      $('m').className = 'msg';
      $('m').textContent = '암호가 맞지 않습니다.';
      var pw = $('pw');
      pw.classList.remove('shake'); void pw.offsetWidth; pw.classList.add('shake');
      pw.select();
    });
}

/* 열 때 스스로 해 보는 순서.
   하나, 이 열림에서 뽑아 둔 키. 곧바로 열린다.
   둘, 이 기기에 기억해 둔 암호. 몇 초 걸린다.
   셋, 둘 다 없으면 암호를 묻는다. */
function autoOpen() {
  return keyFromCache().then(function (k) {
    if (!k) return null;
    waiting(true);
    return openWith(k, null, false).then(function () { return true; });
  }).catch(function () {
    try { sessionStorage.removeItem(cacheKey()); } catch (e) {}
    return null;
  }).then(function (ok) {
    if (ok) return;
    var saved = null;
    try { saved = localStorage.getItem(PASS_KEY); } catch (e) {}
    if (!saved) { waiting(false); return; }
    waiting(true);
    return keyFromPass(saved).then(function (k) { return openWith(k, saved, true); })
      .catch(function () {
        try { localStorage.removeItem(PASS_KEY); } catch (e) {}
        waiting(false);
      });
  });
}

function start() {
  $('f').addEventListener('submit', function (e) {
    e.preventDefault();
    tryOpen($('pw').value, $('rm').checked);
  });
  loadBlob().then(autoOpen).catch(function (e) {
    $('m').className = 'msg';
    $('m').textContent = (e && e.message) || '데이터를 받지 못했습니다.';
  });
}

/* 브라우저 밖에서는 화면 만드는 코드만 내준다. tools/render-test.js 가 이것으로
   파이썬이 내던 판과 글자 하나까지 견준다. */
if (typeof document === 'undefined') {
  if (typeof module !== 'undefined' && module.exports) {
    module.exports = {
      build: function (data, page) { D = data; ADD = {}; SRV = {}; indexData(); return BUILD[page](); },
      sha1hex: sha1hex
    };
  }
} else if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', start, { once: true });
} else {
  start();
}

})();
