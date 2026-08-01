#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
build.py — loggia-data.json 하나에서 세 장을 빚는다.

    python tools/build.py loggia-data.json site/

만들어지는 것
    site/index.html     현황판
    site/journals.html  낼 곳
    site/archive.html   지난 일

남은 날수와 급함의 빛깔은 브라우저가 열릴 때마다 오늘 기준으로 다시 셈한다.
그래서 며칠 지나 열어도 D-day가 낡지 않는다.
"""
import json, sys, html, os, hashlib

def esc(s):
    return html.escape(str(s), quote=True) if s is not None else ''

# ── 껍데기 ──────────────────────────────────────────────────────────────────
HEAD = """<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>LOGGIA — {title}</title>
<link rel="preload" href="font/Pretendard-subset.woff2" as="font" type="font/woff2" crossorigin>
<script>
/* 화면이 그려지기 전에 밝기를 정한다. 늦게 정하면 한 번 번쩍인다. */
(function(){{try{{document.documentElement.dataset.theme=localStorage.getItem('loggia.theme')||'auto'}}catch(e){{}}}})();
</script>
<style>
/* 글꼴은 이 저장소 안에 있다. 남의 자리에 기대지 않는다.
   한글 상용 2350자에 라틴과 기호와 지금 판에 쓰인 글자를 더해 잘라 두었다. 445KB.
   못 받으면 기기에 있는 글꼴로 내려간다. */
@font-face{{font-family:'Pretendard Variable';font-weight:45 920;font-style:normal;
font-display:swap;src:url('font/Pretendard-subset.woff2') format('woff2')}}
{css}</style>
</head>
<body>
<div class="wrap">
<header class="masthead">
  <div><div class="name">Loggia</div><h1>{title}</h1></div>
  <span class="stamp">{updated}<span class="mode" role="group" aria-label="화면 밝기"><button type="button" data-mode="auto">자동</button><button type="button" data-mode="light">밝게</button><button type="button" data-mode="dark">어둡게</button></span></span>
</header>
<nav class="tabs">
  <a class="tab{h0}" href="index.html">현황판</a>
  <a class="tab{hc}" href="calendar.html">달력</a>
  <a class="tab{h1}" href="journals.html">낼 곳 <span class="n">{nven}</span></a>
  <a class="tab{h3}" href="materials.html">재료</a>
  <a class="tab{h2}" href="archive.html">지난 일 <span class="n">{narc}</span></a>
</nav>
"""

FOOT = """
<div class="colophon">암호로 잠긴 판 · 갱신 {updated}</div>
</div>
<script>
// 남은 날수. 열 때마다 오늘 기준으로 다시 센다.
(function () {
  var today = new Date(); today.setHours(0,0,0,0);
  document.querySelectorAll('[data-deadline]').forEach(function (el) {
    var p = el.dataset.deadline.split('-');
    var d = new Date(+p[0], +p[1]-1, +p[2]);
    var n = Math.round((d - today) / 86400000);
    var urg = n < 0 ? 'past' : n <= 7 ? 'now' : n <= 30 ? 'soon' : 'later';
    // 지난 마감. 좁은 칸에서는 숫자만 크게 두고 아랫줄에 말을 붙인다.
    // 넓은 자리에서는 「36일 지남」을 통째로 적는다.
    el.textContent = n < 0 ? (el.dataset.wide ? (-n) + '일 지남' : String(-n))
                   : n === 0 ? '오늘' : 'D-' + n;
    el.dataset.urgency = urg;
    if (n < 0 && !el.dataset.wide && el.parentNode) {
      var dt = el.parentNode.querySelector('.date[data-d]');
      if (dt) dt.textContent = '일 지남 · ' + dt.dataset.d;
    }
  });
  // 밝기 단추. 고른 값은 이 기기에 남는다.
  var root = document.documentElement;
  function paint() {
    var m = root.dataset.theme || 'auto';
    document.querySelectorAll('.mode button').forEach(function (b) {
      b.setAttribute('aria-pressed', b.dataset.mode === m);
    });
  }
  document.querySelectorAll('.mode button').forEach(function (b) {
    b.addEventListener('click', function () {
      root.dataset.theme = b.dataset.mode;
      try { localStorage.setItem('loggia.theme', b.dataset.mode); } catch (e) {}
      paint();
    });
  });
  paint();

  document.querySelectorAll('[data-since]').forEach(function (el) {
    var p = el.dataset.since.split('-');
    var d = new Date(+p[0], +p[1]-1, +p[2]);
    var n = Math.round((today - d) / 86400000);
    el.textContent = n + '일째';
    // 그 지면이 대개 걸리는 날수를 넘겼으면 물어볼 때다
    var box = el.closest('.clock');
    if (box && box.dataset.days && n > +box.dataset.days) box.dataset.late = '1';
  });
})();
</script>
</body>
</html>
"""

CSS = r"""
/* ===========================================================================
   로지아의 옷. 세 가지를 지킨다.

   하나. 대비를 살린다. 옅은 회색으로 중요한 것을 적지 않는다.
         크림빛 종이와 갈색 잉크는 눈에 순하나 무엇이 중요한지를 지운다.
   둘.  제목이 가장 굵고 크다. 본문보다 옅은 제목은 제목이 아니다.
   셋.  덩이로 자른다. 한 갈래가 한 상자다. 왼쪽 띠의 빛깔로 그 결을 안다.

   빛깔은 꾸밈이 아니라 뜻이다. 손이 움직이면 초록, 남을 기다리면 파랑,
   멈췄으면 회색, 급하면 붉음.
   =========================================================================== */
:root{
  --paper:hsl(220 14% 97%); --surface:hsl(0 0% 100%); --sunk:hsl(220 16% 94%);
  --ink:hsl(222 28% 9%); --ink-2:hsl(222 10% 32%); --ink-3:hsl(222 8% 50%);
  --rule:hsl(220 13% 88%); --rule-2:hsl(220 12% 76%);
  --now:hsl(2 76% 47%); --soon:hsl(28 92% 40%); --later:hsl(222 8% 46%);
  --live:hsl(160 68% 26%); --wait:hsl(212 76% 40%); --stop:hsl(222 6% 48%);
  --done:hsl(222 8% 62%); --good:hsl(160 68% 26%);
  --font:'Pretendard Variable',Pretendard,-apple-system,BlinkMacSystemFont,'Apple SD Gothic Neo','Noto Sans KR','Malgun Gothic',system-ui,sans-serif;
  --scale:1;--page-max:880px;--col:104px}
@media(prefers-color-scheme:dark){html:not([data-theme=light]){
  --paper:hsl(224 16% 9%); --surface:hsl(224 14% 13%); --sunk:hsl(224 14% 16%);
  --ink:hsl(220 20% 96%); --ink-2:hsl(220 10% 74%); --ink-3:hsl(220 8% 58%);
  --rule:hsl(224 10% 24%); --rule-2:hsl(224 9% 34%);
  --now:hsl(2 88% 68%); --soon:hsl(32 94% 60%); --later:hsl(220 8% 62%);
  --live:hsl(158 62% 55%); --wait:hsl(206 84% 66%); --stop:hsl(220 7% 58%);
  --done:hsl(220 8% 46%); --good:hsl(158 62% 55%)}}
html[data-theme=dark]{
  --paper:hsl(224 16% 9%); --surface:hsl(224 14% 13%); --sunk:hsl(224 14% 16%);
  --ink:hsl(220 20% 96%); --ink-2:hsl(220 10% 74%); --ink-3:hsl(220 8% 58%);
  --rule:hsl(224 10% 24%); --rule-2:hsl(224 9% 34%);
  --now:hsl(2 88% 68%); --soon:hsl(32 94% 60%); --later:hsl(220 8% 62%);
  --live:hsl(158 62% 55%); --wait:hsl(206 84% 66%); --stop:hsl(220 7% 58%);
  --done:hsl(220 8% 46%); --good:hsl(158 62% 55%)}

*{box-sizing:border-box}
body{margin:0;padding:0 20px 140px;background:var(--paper);color:var(--ink);
font-family:var(--font);font-size:calc(17px*var(--scale));line-height:1.62;
-webkit-font-smoothing:antialiased;font-variant-numeric:tabular-nums}
.wrap{max-width:var(--page-max);margin:0 auto}

/* 머리 */
.masthead{display:flex;align-items:flex-end;justify-content:space-between;gap:18px;
flex-wrap:wrap;padding:40px 0 18px}
.masthead .name{font-size:11px;font-weight:800;letter-spacing:.34em;text-transform:uppercase;
color:var(--ink-3)}
.masthead h1{font-size:30px;font-weight:800;letter-spacing:-.02em;margin:6px 0 0;line-height:1.1}
.masthead .stamp{font-size:13px;color:var(--ink-2);display:flex;align-items:center;gap:12px}
.mode{display:inline-flex;border:1px solid var(--rule-2);border-radius:6px;overflow:hidden}
.mode button{appearance:none;border:0;background:transparent;cursor:pointer;font-family:var(--font);
font-size:12px;font-weight:700;color:var(--ink-3);padding:6px 11px;border-right:1px solid var(--rule-2)}
.mode button:last-child{border-right:0}
.mode button:hover{color:var(--ink)}
.mode button[aria-pressed=true]{background:var(--ink);color:var(--paper)}

/* 칸 넘기기 */
.tabs{display:flex;gap:2px;flex-wrap:wrap;margin:6px 0 0;border-bottom:2px solid var(--rule)}
.tab{display:inline-flex;align-items:baseline;gap:7px;padding:13px 15px;margin-bottom:-2px;
font-size:16px;font-weight:700;color:var(--ink-3);text-decoration:none;
border-bottom:3px solid transparent;border-radius:6px 6px 0 0}
.tab:first-child{padding-left:0}
.tab:hover{color:var(--ink-2)}
.tab .n{font-size:13px;font-weight:600;color:var(--ink-3)}
.tab.here{color:var(--ink);border-bottom-color:var(--ink)}

/* 지금 이것부터. 이 판에서 가장 큰 덩이 */
.focus{background:var(--ink);color:var(--paper);padding:26px 28px 28px;margin:26px 0 46px;
border-radius:14px}
.focus .cap{font-size:12px;font-weight:800;letter-spacing:.14em;opacity:.62;margin-bottom:16px}
.focus .line{display:flex;align-items:baseline;gap:16px;flex-wrap:wrap}
.focus .dday{font-size:42px;font-weight:800;letter-spacing:-.03em;line-height:1;color:inherit}
.focus .who{font-size:15px;opacity:.72}
.focus .todo{font-size:26px;font-weight:700;line-height:1.38;margin:14px 0 0;letter-spacing:-.01em;color:inherit}
/* 이 상자는 바탕이 어둡다. 일반 규칙의 검은 글씨를 그대로 두면 글이 사라진다 */
.focus .todo::before{color:var(--now)}
.focus .when{font-size:13px;opacity:.62;margin-top:12px}

/* 마디의 머리 */
.sec{display:flex;align-items:baseline;gap:12px;margin:52px 0 16px;padding-bottom:0;border:0}
/* 마디 머리를 누르면 접힌다. 지금 안 보고 싶은 것을 치워 둘 수 있다.
   접고 편 상태는 이 기기에 남는다. */
details.group>summary.sec{cursor:pointer;list-style:none;padding:6px 0;border-radius:8px}
details.group>summary.sec::-webkit-details-marker{display:none}
details.group>summary.sec:hover h2{color:var(--ink-2)}
details.group>summary.sec .arrow{font-size:12px;color:var(--ink-3);transition:transform .14s;
margin-left:10px;align-self:center}
details.group[open]>summary.sec .arrow{transform:rotate(90deg)}
details.group>summary.sec .c{margin-left:auto}
details.group:not([open]){margin-bottom:10px}
details.group:not([open])>summary.sec{margin-bottom:0}
.sec h2{font-size:22px;font-weight:800;letter-spacing:-.015em;margin:0}
.sec .c{margin-left:auto;font-size:13px;font-weight:700;color:var(--ink-3);
background:var(--sunk);padding:3px 11px;border-radius:99px}

/* 갈래 하나가 상자 하나. 왼쪽 띠가 결을 말한다 */
.entry{display:grid;grid-template-columns:var(--col) 1fr;gap:20px;margin-bottom:12px;
padding:20px 22px 22px;background:var(--surface);border:1px solid var(--rule);
border-left:6px solid var(--tone,var(--rule-2));border-radius:12px}
.entry.t-live{--tone:var(--live)}
.entry.t-wait{--tone:var(--wait)}
.entry.t-stop{--tone:var(--stop)}
.entry.t-done{--tone:var(--done)}
.when-col{text-align:right}
.dday{font-size:31px;font-weight:800;letter-spacing:-.03em;line-height:1.02;color:var(--later);display:block}
.dday[data-urgency=now]{color:var(--now)}
.dday[data-urgency=soon]{color:var(--soon)}
.dday[data-urgency=past]{color:var(--ink-3)}
.dday.none{color:var(--ink-3);font-size:20px;font-weight:700}
.when-col .date{display:block;margin-top:6px;font-size:12.5px;font-weight:600;color:var(--ink-3)}
.title-line{display:flex;align-items:baseline;gap:12px;flex-wrap:wrap}
.title-line .t{font-size:21px;font-weight:800;letter-spacing:-.015em;color:var(--ink);margin:0;line-height:1.3}
.title-line .state{margin-left:auto;font-size:12px;font-weight:800;letter-spacing:.02em;
color:var(--surface);background:var(--tone,var(--ink-3));padding:3px 10px;border-radius:99px;white-space:nowrap}
.entry .meta{display:flex;align-items:baseline;gap:10px;flex-wrap:wrap;margin-top:7px}
.meta .k{font-size:13px;font-weight:600;color:var(--ink-3)}
.venue{font-size:13px;font-weight:700;color:var(--ink-2);text-decoration:none;
border-bottom:1.5px solid var(--rule-2)}
.venue:hover{color:var(--ink);border-bottom-color:var(--ink)}
.todo{margin:14px 0 0;font-size:17.5px;font-weight:700;line-height:1.5;color:var(--ink)}
.todo::before{content:'▸ ';color:var(--tone,var(--ink-3));font-weight:800}
.todo.none{font-weight:500;color:var(--ink-3)}
.todo.none::before{content:''}
.note{margin:9px 0 0;font-size:15px;color:var(--ink-2);line-height:1.6}
.links{margin-top:14px;display:flex;flex-wrap:wrap;gap:8px}
.link{font-size:12.5px;font-weight:700;color:var(--ink-2);text-decoration:none;
background:var(--sunk);padding:5px 11px;border-radius:7px}
.link:hover{color:var(--ink);background:var(--rule)}
.link.chat::before{content:'▪ ';color:var(--wait)}
.link.file::before{content:'▪ ';color:var(--soon)}
.link.web::before{content:'▪ ';color:var(--ink-3)}

/* 접는 마디. 오늘 할 일이 아니면 접는다 */
.fold{margin:52px 0 0;background:var(--surface);border:1px solid var(--rule);border-radius:12px;
overflow:hidden}
.fold>summary{display:flex;align-items:center;gap:12px;padding:18px 22px;cursor:pointer;
list-style:none;background:var(--surface)}
.fold>summary::-webkit-details-marker{display:none}
.fold>summary:hover{background:var(--sunk)}
.fold>summary h2{font-size:18px;font-weight:800;letter-spacing:-.01em;margin:0;color:var(--ink-2)}
.fold>summary .c{margin-left:auto;font-size:13px;font-weight:700;color:var(--ink-3);
background:var(--sunk);padding:3px 11px;border-radius:99px}
.fold>summary .arrow{font-size:12px;color:var(--ink-3);transition:transform .14s}
.fold[open]>summary{border-bottom:1px solid var(--rule)}
.fold[open]>summary h2{color:var(--ink)}
.fold[open]>summary .arrow{transform:rotate(90deg)}
.fold .lede{margin:20px 22px 0}
.fold>*:not(summary){padding-left:22px;padding-right:22px}
.fold>div:last-child{padding-bottom:8px}

/* 낼 곳과 재료의 상자 */
.venue-block{background:var(--surface);border:1px solid var(--rule);border-radius:12px;
padding:20px 22px 22px;margin-bottom:12px}
.venue-block.t-live{border-left:6px solid var(--live)}
.venue-block.t-wait{border-left:6px solid var(--wait)}
.venue-block.t-stop{border-left:6px solid var(--stop)}
.venue-block.t-done{border-left:6px solid var(--done)}
.venue-head .mark{margin-left:auto}
.rep .vn{font-size:12.5px;font-weight:600;color:var(--ink-3)}
.venue-head{display:flex;align-items:baseline;gap:12px;flex-wrap:wrap}
.venue-head h3{font-size:20px;font-weight:800;letter-spacing:-.015em;margin:0;line-height:1.3}
.venue-head h3 a{color:var(--ink);text-decoration:none;border-bottom:2px solid var(--rule-2)}
.venue-head h3 a:hover{border-bottom-color:var(--ink)}
.venue-head .sub{font-size:13.5px;color:var(--ink-3);font-weight:600}
.idx-row{display:flex;flex-wrap:wrap;gap:6px;margin-top:12px;align-items:center}
.idx{font-size:11.5px;font-weight:800;letter-spacing:.03em;padding:4px 9px;border-radius:6px;
border:1.5px solid var(--rule-2);color:var(--ink-3)}
.idx.strong{background:var(--ink);border-color:var(--ink);color:var(--paper)}
.idx.plain{border-color:var(--ink-3);color:var(--ink-2)}
.idx.none{border-style:dashed;color:var(--ink-3)}
.flag{font-size:11.5px;font-weight:800;color:var(--surface);background:var(--soon);
padding:4px 9px;border-radius:6px}
.venue-facts{display:flex;flex-wrap:wrap;gap:8px 20px;margin-top:14px;font-size:13.5px;color:var(--ink-2)}
.venue-facts .lab{color:var(--ink-3);font-weight:700;margin-right:7px}
.venue-facts b{font-weight:700;color:var(--ink)}
.history{margin-top:16px;padding-top:14px;border-top:1px solid var(--rule)}
.history .cap{font-size:12px;font-weight:800;letter-spacing:.08em;color:var(--ink-3);margin-bottom:10px}
.hrow{display:flex;align-items:baseline;gap:12px;flex-wrap:wrap;padding:9px 0}
.hrow+.hrow{border-top:1px solid var(--rule)}
.mark{font-size:11.5px;font-weight:800;color:var(--surface);background:var(--ink-3);
padding:3px 9px;border-radius:99px;white-space:nowrap}
.mark.live{background:var(--live)}
.mark.stop{background:var(--stop)}
.hrow .t{font-size:15.5px;font-weight:700;color:var(--ink)}
.hrow .d{margin-left:auto;font-size:12.5px;font-weight:600;color:var(--ink-3)}
.gist{flex-basis:100%;margin:7px 0 0;font-size:14.5px;color:var(--ink-2);
background:var(--sunk);padding:12px 14px;border-radius:9px}
.gist .who{display:block;margin-top:6px;font-size:12.5px;color:var(--ink-3);font-weight:600}
.lede{font-size:15.5px;color:var(--ink-2);margin:0 0 6px}

/* 알약은 기준선이 아니라 가운데를 맞춘다.
   기준선에 맞추면 알약의 상자가 제 글자의 밑선에 걸려 아래로 내려앉는다.
   곁의 글자보다 작은 글씨일수록 그 어긋남이 눈에 띈다. */
.title-line .state, .mark, .who-row .role, .rep .guess,
.venue-head .mark, .clock .v{align-self:center}
/* 이름 아래 출처가 한 줄 더 붙는 자리다. 알약은 두 줄의 가운데가 아니라
   첫 줄에 맞아야 한다. 그래서 첫 줄만 한 높이의 상자를 만들고 그 안에서 가운데를 잡는다. */
.reuse .to{align-self:flex-start;align-items:center;min-height:26.7px;min-height:1lh;
font-size:16.5px;line-height:1.62}
/* 글줄 안에 박히는 알약은 글자 가운데에 맞춘다 */
.dec .what .on{vertical-align:middle}

/* 해치운 것을 데이터로 옮기는 다리. 눌린 것이 있을 때만 뜬다 */
.carry{position:fixed;left:50%;bottom:22px;transform:translateX(-50%);z-index:9;
display:flex;align-items:center;gap:12px;flex-wrap:wrap;justify-content:center;
background:var(--ink);color:var(--paper);padding:12px 18px;border-radius:99px;
box-shadow:0 8px 28px rgba(0,0,0,.22);max-width:calc(100vw - 32px)}
.carry[hidden]{display:none}
.carry .cap{font-size:13.5px;font-weight:700}
.carry .cap b{font-weight:800}
.carry button{appearance:none;border:0;cursor:pointer;font-family:var(--font);
font-size:13px;font-weight:800;border-radius:99px;padding:7px 15px}
.carry .copy{background:var(--paper);color:var(--ink)}
.carry .clear{background:transparent;color:var(--paper);opacity:.66;padding:7px 8px}
.carry .clear:hover{opacity:1}
.carry .hint{font-size:12px;opacity:.6}
@media(max-width:560px){.carry .hint{display:none}}

/* 지난 서른 날에 한 일. 판을 열면 먼저 눈에 든다 */
.tally{display:flex;flex-wrap:wrap;align-items:baseline;gap:8px;margin:22px 0 0;
font-size:14px;color:var(--ink-2)}
.tally:empty{display:none}
.tally .cap{font-size:12px;font-weight:800;letter-spacing:.08em;color:var(--ink-3);margin-right:6px}
.tally b{font-weight:800;color:var(--ink)}
.tally .dot{color:var(--rule-2);margin:0 2px}

/* 마지막으로 손댄 날 */
.touch{font-size:12.5px;font-weight:600;color:var(--ink-3)}
.touch[data-cold]{color:var(--soon);font-weight:700}
.touch[data-stalled]{color:var(--now);font-weight:800}
.touch.none{font-style:normal;opacity:.7}

/* 다음 걸음. 첫 걸음은 크게, 나머지는 차례로 */
.step{display:flex;align-items:baseline;gap:11px;margin:14px 0 0}
.step .todo{margin:0;cursor:pointer}
.rest{list-style:none;margin:10px 0 0;padding:0}
.rest li{display:flex;align-items:baseline;gap:11px;padding:5px 0;font-size:15px;color:var(--ink-2)}
.rest li label{cursor:pointer}
input[data-done]{appearance:none;flex:none;width:1.05em;height:1.05em;margin:0;
border:2px solid var(--rule-2);border-radius:5px;background:var(--surface);cursor:pointer;
align-self:baseline;transform:translateY(0.12em)}
.step.first input[data-done]{width:1.15em;height:1.15em;border-color:var(--tone,var(--ink-3))}
input[data-done]:hover{border-color:var(--ink-3)}
input[data-done]:checked{background:var(--tone,var(--ink-3));border-color:var(--tone,var(--ink-3))}
input[data-done]:checked::after{content:'';display:block;width:100%;height:100%;
background:var(--surface);clip-path:polygon(16% 52%,38% 74%,84% 26%,92% 36%,38% 90%,8% 60%)}
[data-done="1"] .todo,[data-done="1"] label{text-decoration:line-through;color:var(--ink-3);
text-decoration-thickness:2px}
[data-done="1"] .todo::before{opacity:.35}
.cost{font-size:12px;font-weight:800;color:var(--ink-2);background:var(--sunk);
padding:3px 10px;border-radius:99px;white-space:nowrap;align-self:center;margin-left:auto}

/* 바로 가는 길. 장이 길 때 맨 위에 둔다 */
.jump{display:flex;flex-wrap:wrap;gap:7px;margin:18px 0 0}
.jump a{font-size:13.5px;font-weight:700;color:var(--ink-2);text-decoration:none;
background:var(--sunk);padding:7px 14px;border-radius:99px}
.jump a:hover{background:var(--rule);color:var(--ink)}
.jump a.hot{background:var(--ink);color:var(--paper)}

/* 거르개. 마디 위에 한 줄 */
.filters{display:flex;flex-wrap:wrap;gap:7px;margin:24px 0 8px}
.filters button{appearance:none;cursor:pointer;font-family:var(--font);font-size:13.5px;
font-weight:700;color:var(--ink-2);background:var(--surface);border:1.5px solid var(--rule-2);
border-radius:99px;padding:7px 15px;display:inline-flex;align-items:baseline;gap:7px}
.filters button:hover{border-color:var(--ink-3);color:var(--ink)}
.filters button b{font-size:12px;font-weight:700;color:var(--ink-3)}
.filters button[aria-pressed=true]{background:var(--ink);border-color:var(--ink);color:var(--paper)}
.filters button[aria-pressed=true] b{color:var(--paper);opacity:.6}
.group[hidden]{display:none}

/* 답을 기다리는 중 */
.clocks{margin-top:2px}
.clock{margin-bottom:10px;background:var(--surface);border:1px solid var(--rule);
border-left:6px solid var(--wait);border-radius:12px;overflow:hidden}
.clock>summary{display:flex;align-items:center;gap:16px;flex-wrap:wrap;padding:16px 20px;
cursor:pointer;list-style:none}
.clock>summary::-webkit-details-marker{display:none}
.clock>summary:hover{background:var(--sunk)}
.clock .arrow{font-size:12px;color:var(--ink-3);transition:transform .14s;flex:none}
.clock[open] .arrow{transform:rotate(90deg)}
.clock[open]>summary{border-bottom:1px solid var(--rule)}
.clock-body{padding:16px 20px 18px}
.clock-body .todo{margin-top:0}
.clock-body .todo::before{color:var(--wait)}
.clock .el{font-size:24px;font-weight:800;letter-spacing:-.02em;color:var(--ink);min-width:84px}
.clock[data-late]{border-left-color:var(--now)}
.clock[data-late] .el{color:var(--now)}
.clock .t{font-size:17px;font-weight:700;color:var(--ink)}
.clock .v{font-size:13px;font-weight:600;color:var(--ink-3)}
.clock .side{margin-left:auto;order:0;display:flex;gap:16px;font-size:13px;color:var(--ink-2);align-items:center}
.clock .side .lab{margin-right:6px;color:var(--ink-3);font-weight:700}
.clock[data-late] .side::after{content:'물어볼 때';color:var(--surface);background:var(--now);
font-weight:800;font-size:12px;padding:3px 10px;border-radius:99px}

/* 해마다 돌아오는 것 */
.reps{margin-top:4px}
.rep{display:flex;align-items:baseline;gap:14px;flex-wrap:wrap;padding:13px 0}
.rep+.rep{border-top:1px solid var(--rule)}
.rep .when{font-size:13px;font-weight:800;color:var(--ink);min-width:118px}
.rep .t{font-size:15.5px;font-weight:600;color:var(--ink-2)}
.rep .guess{font-size:11px;font-weight:800;color:var(--ink-3);border:1.5px dashed var(--rule-2);
padding:2px 8px;border-radius:6px}
.rep .n{font-size:13.5px;color:var(--ink-3);flex-basis:100%;margin-top:2px}

/* 정한 것 */
.decs{margin-top:4px}
.dec{display:flex;gap:18px;padding:15px 0}
.dec+.dec{border-top:1px solid var(--rule)}
.dec .when{font-size:13px;font-weight:700;color:var(--ink-3);min-width:82px;flex:none}
.dec .what{margin:0;font-size:16.5px;font-weight:700;color:var(--ink);line-height:1.45}
.dec .what .on{font-size:12px;font-weight:700;color:var(--surface);background:var(--ink-3);
padding:2px 9px;border-radius:99px;margin-left:10px;white-space:nowrap}
.dec .why{margin:6px 0 0;font-size:14.5px;color:var(--ink-2)}

/* 다시 쓸 것 */
.reuses{margin-top:4px}
.reuse{display:flex;align-items:baseline;gap:16px;flex-wrap:wrap;padding:15px 0}
.reuse+.reuse{border-top:1px solid var(--rule)}
.reuse .what{margin:0;font-size:16.5px;font-weight:700;color:var(--ink)}
.reuse .from{margin:3px 0 0;font-size:13.5px;color:var(--ink-3)}
.reuse .to{margin-left:auto;display:flex;gap:6px;flex-wrap:wrap}
.reuse .to span{font-size:12px;font-weight:700;color:var(--ink-2);background:var(--sunk);
padding:4px 10px;border-radius:7px}

/* 사람 */
.whos{margin-top:4px}
.who-row{display:flex;align-items:baseline;gap:14px;flex-wrap:wrap;padding:15px 0}
.who-row+.who-row{border-top:1px solid var(--rule)}
.who-row .nm{font-size:17px;font-weight:800;color:var(--ink)}
.who-row .role{font-size:12px;font-weight:700;color:var(--ink-2);background:var(--sunk);
padding:3px 10px;border-radius:7px}
.who-row .last{margin-left:auto;font-size:13px;font-weight:600;color:var(--ink-3)}
.who-row .n{flex-basis:100%;margin:5px 0 0;font-size:14.5px;color:var(--ink-2)}

/* 길목과 새겨 둘 것과 지형도 */
.watch{display:flex;flex-wrap:wrap;gap:8px;margin-top:6px}
.memo{margin-top:6px}
.memo p{margin:0 0 12px;font-size:15px;color:var(--ink-2);padding-left:16px;
border-left:3px solid var(--rule-2)}
.compass{margin-top:52px;background:var(--sunk);border-radius:12px;padding:22px 24px}
.compass .cap{font-size:12px;font-weight:800;letter-spacing:.1em;color:var(--ink-3);margin-bottom:12px}
.compass p{margin:0 0 9px;font-size:15px;color:var(--ink-2)}
.compass p:last-child{margin-bottom:0}
.colophon{margin-top:64px;padding-top:20px;border-top:1px solid var(--rule);
font-size:12.5px;color:var(--ink-3)}

/* 달력 */
.cal-legend{display:flex;flex-wrap:wrap;gap:8px 20px;font-size:12.5px;color:var(--ink-3);margin:0 0 16px}
.cal-legend b{color:var(--ink-2);font-weight:700}
.cal-grid{display:grid;grid-template-columns:repeat(3,1fr);gap:12px}
.cal-m{background:var(--surface);border:1px solid var(--rule);border-radius:12px;padding:16px 16px 14px}
.cal-m.here{border-color:var(--ink);border-width:2px}
.cal-m.past{opacity:.5}
.cal-m h3{font-size:14px;font-weight:800;margin:0 0 10px;color:var(--ink)}
table.cal{width:100%;border-collapse:collapse;font-size:12px}
table.cal th{font-weight:700;color:var(--ink-3);padding:3px 0;font-size:10.5px}
table.cal td{text-align:center;padding:4px 0;color:var(--ink-3);border-radius:5px}
table.cal td.off{color:transparent}
table.cal td.has{color:var(--ink);font-weight:800;background:var(--sunk)}
table.cal td.now{color:var(--surface);background:var(--now)}
table.cal td.soon{color:var(--surface);background:var(--soon)}
table.cal td.today{outline:2px solid var(--ink);outline-offset:-2px;font-weight:800;color:var(--ink)}
.cal-ev{margin-top:12px;padding-top:10px;border-top:1px solid var(--rule)}
.cal-ev .r{display:flex;gap:9px;font-size:12.5px;padding:4px 0;align-items:baseline}
.cal-ev .r .dd{font-weight:800;color:var(--ink-3);min-width:20px;text-align:right;flex:none}
.cal-ev .r .tx{color:var(--ink-2)}
.cal-ev .r.now .dd,.cal-ev .r.now .tx{color:var(--now);font-weight:700}
.cal-ev .r.soon .dd,.cal-ev .r.soon .tx{color:var(--soon)}
.cal-ev .r.rep .tx{color:var(--ink-3)}
.cal-none{margin-top:12px;padding-top:10px;border-top:1px solid var(--rule);
font-size:12.5px;color:var(--ink-3)}

@media(max-width:820px){.cal-grid{grid-template-columns:repeat(2,1fr)}}
@media(max-width:640px){
  :root{--col:auto;--scale:1}
  body{padding:0 16px 120px}
  .masthead h1{font-size:25px}
  .cal-grid{grid-template-columns:1fr}
  .entry{grid-template-columns:1fr;gap:0;padding:18px 18px 20px}
  .when-col{text-align:left;display:flex;align-items:baseline;gap:12px;margin-bottom:10px}
  .when-col .date{margin-top:0}
  .title-line .state{margin-left:0}
  .focus .todo{font-size:22px}
  .focus{padding:22px 20px 24px}
  .clock .side{margin-left:0;flex-basis:100%;margin-top:8px}
  .hrow .d{margin-left:0;width:100%}
  .reuse .to,.who-row .last{margin-left:0}
}
"""

# ── 조각들 ──────────────────────────────────────────────────────────────────
def index_tags(venue, D):
    """색인 딱지를 (모양, 글자) 짝으로 돌려준다.

    데이터에는 열쇠말만 적는다.  "indexes": ["ahci", "scopus"]
    앞에 빼기표를 붙이면 미등재를 뜻한다.  "-ahci"  →  A&HCI 미등재
    옛 꼴인 [["strong", "A&HCI"]] 도 그대로 받는다.
    """
    kinds = D.get('indexKinds', {})
    out = []
    for x in venue.get('indexes', []):
        if isinstance(x, str):
            neg = x.startswith('-')
            k = kinds.get(x.lstrip('-'))
            if not k:
                out.append(('none', x.lstrip('-')))
            elif neg:
                out.append(('none', k['label'] + ' 미등재'))
            else:
                out.append((k.get('tone', 'plain'), k['label']))
        else:
            out.append((x[0], x[1]))
    return out


def links_html(item):
    out = []
    for c in item.get('chats', []):
        lab = '대화 ' + c['date'][5:].replace('-', '.')
        out.append(f'<a class="link chat" href="{esc(c["url"])}" target="_blank" rel="noopener">{esc(lab)}</a>')
    for l in item.get('links', []):
        out.append(f'<a class="link {esc(l["kind"])}" href="{esc(l["url"])}" target="_blank" rel="noopener">{esc(l["label"])}</a>')
    return f'<div class="links">{"".join(out)}</div>' if out else ''


def when_col(item):
    d = item.get('dates', {})
    if d.get('deadline'):
        iso = d['deadline']
        md_ = iso[5:].replace("-", ".")
        return (f'<div class="when-col"><span class="dday" data-deadline="{iso}">D-</span>'
                f'<span class="date" data-d="{md_}">{md_}</span></div>')
    if d.get('sent'):
        iso = d['sent']
        return (f'<div class="when-col"><span class="dday none" data-since="{iso}"></span>'
                f'<span class="date">{iso[5:].replace("-", ".")} 냄</span></div>')
    return '<div class="when-col"><span class="dday none">—</span></div>'


def steps_of(item):
    """다음 걸음들. 한 줄만 적어도 되고 차례로 여럿을 적어도 된다."""
    st = item.get('steps')
    if st:
        return list(st)
    return [item['next']] if item.get('next') else []


def steps_html(item, D):
    """첫 걸음은 크게, 나머지는 작게 차례로.

    네모를 누르면 줄이 그어진다. 그 표시는 이 기기에만 남는다.
    데이터를 건드리지 않으므로 갱신하면 사라진다. 오늘의 매듭일 뿐이다.
    """
    ss = steps_of(item)
    if not ss:
        return '<p class="todo none">지금 할 일 없음</p>'
    eff = D.get('efforts', {}).get(item.get('품'))
    cost = f'<span class="cost">{esc(eff["label"])}</span>' if eff else ''
    k = esc(item['id'])

    def key(text):
        # 순서가 아니라 글에 맨다.
        # 순서로 매기면 갱신이 첫 걸음을 뺐을 때 둘째가 첫째의 표시를 물려받는다.
        # 글이 그대로면 표시도 그대로 남고, 글이 바뀌면 새 걸음으로 친다.
        h = hashlib.sha1(text.encode('utf-8')).hexdigest()[:8]
        return f'{k}.{h}'

    def box(text, i, cls=''):
        d = key(text)
        return (f'<input type="checkbox" id="s-{d}" data-done="{esc(d)}">'
                f'<label for="s-{d}"{cls}>{esc(text)}</label>')

    out = [f'<div class="step first">{box(ss[0], 0, chr(32) + "class=" + chr(34) + "todo" + chr(34))}{cost}</div>']
    if len(ss) > 1:
        rest = ''.join(f'<li>{box(x, i)}</li>' for i, x in enumerate(ss[1:], 1))
        out.append(f'<ol class="rest">{rest}</ol>')
    return ''.join(out)


def entry_html(item, D, venue_index):
    st = D['statuses'].get(item.get('status'), {'label': item.get('status', ''), 'tone': 'live'})
    v = venue_index.get(item.get('venue'))
    venue = f'<a class="venue" href="journals.html#{esc(item["venue"])}">{esc(v["name"])}</a>' if v else ''
    note = f'<p class="note">{esc(item["note"])}</p>' if item.get('note') else ''
    # 마지막으로 손댄 날. 오래 멎어 있으면 눈에 띄게 한다.
    # 마감만 보면 마감 없는 갈래가 조용히 가라앉는다.
    t = item.get('dates', {}).get('touched')
    touch = (f'<span class="touch" data-touched="{esc(t)}"></span>' if t
             else '<span class="touch none">손댄 날 모름</span>')
    tags = ' '.join(x for x in (item.get('status', ''), item.get('품', '')) if x)
    # 결마다 빛깔을 준다. 왼쪽 띠 하나로 무슨 종류인지 눈이 먼저 안다
    return f"""<article class="entry t-{esc(st.get('tone', 'live'))}" data-tags="{esc(tags)}">{when_col(item)}
<div class="body"><div class="title-line"><h3 class="t">{esc(item['title'])}</h3>
<span class="state">{esc(st['label'])}</span></div>
<div class="meta">{venue}<span class="k">{esc(item.get('kind',''))}</span>{touch}</div>
{steps_html(item, D)}{note}{links_html(item)}</div></article>"""


def pick_focus(D):
    best = None
    for s in D['sections']:
        for it in s['items']:
            dl = it.get('dates', {}).get('deadline')
            if dl and steps_of(it) and (best is None or dl < best['dates']['deadline']):
                best = it
    return best


# ── 현황판 ──────────────────────────────────────────────────────────────────
def build_index(D, venue_index, nven, narc):
    out = [HEAD.format(title=esc(D['meta']['title']), css=CSS,
                       updated=D['meta']['updated'].replace('-', '.'),
                       h0=' here', hc='', h1='', h2='', h3='', nven=nven, narc=narc)]
    # 지난 서른 날. 한 일이 눈에 보여야 한다.
    # 학계와 ADHD가 겹치면 자기가 한 일을 늘 실제보다 적게 본다.
    done = []
    for it, arc in all_items(D):
        d = it.get('dates', {})
        if d.get('sent'):
            done.append({'d': d['sent'], 'k': '냈다', 't': it['title']})
        if d.get('decided'):
            done.append({'d': d['decided'], 'k': '끝났다', 't': it['title']})
        if d.get('touched'):
            done.append({'d': d['touched'], 'k': '손댔다', 't': it['title']})
    done = [x for x in done if len(x['d']) == 10]
    out.append('<div class="carry" id="carry" hidden>'
               '<span class="cap">해치운 걸음 <b class="n">0</b></span>'
               '<button type="button" class="copy">옮겨 적기</button>'
               '<button type="button" class="clear">지우기</button>'
               '<span class="hint">베낀 것을 채팅에 붙이면 판이 따라옵니다</span></div>')
    out.append('<div class="tally" id="tally"></div>'
               '<script>const DONE = ' + json.dumps(done, ensure_ascii=False) + ';</script>')

    f = pick_focus(D)
    if f:
        v = venue_index.get(f.get('venue'))
        iso = f['dates']['deadline']
        out.append(f"""<section class="focus"><div class="cap">지금 이것부터</div>
<div class="line"><span class="dday" data-wide="1" data-deadline="{iso}">D-</span>
<span class="who">{esc(f['title'])}{' · ' + esc(v['name']) if v else ''}</span></div>
<p class="todo">{esc(steps_of(f)[0])}</p>
<div class="when">마감 {iso[5:7].lstrip('0')}월 {iso[8:].lstrip('0')}일</div></section>""")
    # 답을 기다리는 것은 달력의 응답 시계가 맡는다. 여기서 또 보이면 두 번 읽게 된다
    shown = [x for x in D['sections'] if x['id'] != 'waiting']

    # 거르개. 지금 판에 실제로 있는 상태만 단추로 낸다
    seen = {}
    for x in shown:
        for it in x['items']:
            seen[it.get('status')] = seen.get(it.get('status'), 0) + 1
    order = [k for k in D['statuses'] if k in seen]
    total = sum(seen.values())
    # 품. 지금 이십 분밖에 없을 때 무엇을 할 수 있는지 고르는 자리
    pum = {}
    for x in shown:
        for it in x['items']:
            if it.get('품'):
                pum[it['품']] = pum.get(it['품'], 0) + 1
    porder = [k for k in D.get('efforts', {}) if k in pum]
    out.append(filters_html([('*', '전체', total)]
                            + [(k, D['statuses'][k]['label'], seen[k]) for k in order]
                            + [(k, D['efforts'][k]['label'], pum[k]) for k in porder],
                            '상태와 품으로 골라 보기'))

    for x in shown:
        body = ''.join(entry_html(it, D, venue_index) for it in
                       sorted(x['items'], key=lambda i: i.get('dates', {}).get('deadline') or '9999'))
        out.append(secbox(x['label'], len(x['items']), body, key=x['id']))
    if D.get('decisions'):
        by = {}
        for it, _ in all_items(D):
            by[it['id']] = it['title']
        ds = ''.join(
            f'<div class="dec"><span class="when">{esc(d["date"].replace("-", "."))}</span>'
            f'<div><p class="what">{esc(d["what"])}'
            + (f'<span class="on">{esc(by[d["item"]])}</span>' if d.get('item') in by else '')
            + f'</p><p class="why">{esc(d.get("why", ""))}</p></div></div>'
            for d in sorted(D['decisions'], key=lambda x: x['date'], reverse=True))
        out.append(fold('정한 것', len(D['decisions']), f'<div class="decs">{ds}</div>'))
    out.append(BOARD_JS)
    out.append(FILTER_JS)
    out.append(SEC_JS)
    c = D.get('compass')
    if c:
        lines = ''.join(f'<p>{esc(l)}</p>' for l in c['lines'])
        out.append(f'<div class="compass"><div class="cap">{esc(c["label"])}</div>{lines}</div>')
    out.append(FOOT.replace('{updated}', D['meta']['updated'].replace('-', '.')))
    return ''.join(out)


# ── 낼 곳 ───────────────────────────────────────────────────────────────────
def build_journals(D, venue_index, items_by_venue, nven, narc):
    out = [HEAD.format(title='낼 곳', css=CSS, updated=D['meta']['updated'].replace('-', '.'),
                       h0='', hc='', h1=' here', h2='', h3='', nven=nven, narc=narc)]
    # 거르개. 색인과 마감으로 좁힌다
    tally, ndl = {}, 0
    for g in D['venueGroups']:
        for v in g['venues']:
            for _, t in index_tags(v, D):
                tally[t] = tally.get(t, 0) + 1
            if v.get('deadline'):
                ndl += 1
    keys = [t for t in ('A&HCI', 'SSCI', 'Scopus', 'KCI 등재', 'ESCI', '색인 없음') if t in tally]
    out.append(filters_html([('*', '전체', nven)]
                            + [(t, t, tally[t]) for t in keys]
                            + ([('마감', '마감 있음', ndl)] if ndl else []),
                            '색인과 마감으로 골라 보기'))

    for g in D['venueGroups']:
        body = []
        for v in g['venues']:
            name = (f'<a href="{esc(v["url"])}" target="_blank" rel="noopener">{esc(v["name"])}</a>'
                    if v.get('url') else esc(v['name']))
            tags = ''.join(f'<span class="idx {k}">{esc(t)}</span>' for k, t in index_tags(v, D))
            if v.get('flag'):
                tags += f'<span class="flag">{esc(v["flag"])}</span>'
            facts = []
            if v.get('deadline'):
                iso = v['deadline']
                facts.append(f'<span><span class="lab">마감</span><b>{iso.replace("-", ".")} · </b>'
                             f'<b class="dday" style="font-size:13.5px;display:inline" data-wide="1" data-deadline="{iso}">D-</b></span>')
            if isinstance(v.get('비용'), dict):
                for k2, val in v['비용'].items():
                    facts.append(f'<span><span class="lab">{esc(k2)}</span><b>{esc(val)}</b></span>')
            elif v.get('cost'):
                facts.append(f'<span><span class="lab">비용</span><b>{esc(v["cost"])}</b></span>')
            if v.get('review'):
                facts.append(f'<span><span class="lab">심사</span>{esc(v["review"])}</span>')
            if v.get('clarivate'):
                facts.append('<span><span class="lab">색인</span>클래리베이트 대조 완료</span>')
            hist = ''
            rows = items_by_venue.get(v['id'], [])
            if rows:
                rs = []
                for it, arc in rows:
                    st = D['statuses'].get(it.get('status'), {'label': it.get('status', ''), 'tone': 'live'})
                    cls = {'live': 'live', 'wait': '', 'stop': 'stop', 'done': ''}.get(st['tone'], '')
                    d = it.get('dates', {})
                    when = (d.get('decided') or d.get('sent') or d.get('deadline') or '')
                    tail = '결정' if d.get('decided') else ('냄' if d.get('sent') else ('마감' if d.get('deadline') else ''))
                    rs.append(f'<div class="hrow"><span class="mark {cls}">{esc(st["label"])}</span>'
                              f'<span class="t">{esc(it["title"])}</span>'
                              f'<span class="d">{when.replace("-", ".")} {tail}</span>'
                              + (f'<p class="gist">{esc(it["review"]["gist"])}'
                                 f'<span class="who">{esc(it["review"].get("who",""))}</span></p>'
                                 if it.get('review') else '')
                              + '</div>')
                hist = (f'<div class="history"><div class="cap">이 곳에 낸 것 · {len(rows)}건</div>'
                        + ''.join(rs) + '</div>')
            tagset = [t for _, t in index_tags(v, D)] + (['마감'] if v.get('deadline') else [])
            body.append(f"""<section class="venue-block" id="{esc(v['id'])}" data-tags="{esc(' '.join(tagset))}">
<div class="venue-head"><h3>{name}</h3><span class="sub">{esc(v.get('sub',''))} · {esc(v.get('type',''))}</span></div>
{f'<div class="idx-row">{tags}</div>' if tags else ''}
{f'<div class="venue-facts">{"".join(facts)}</div>' if facts else ''}
{f'<p class="note">{esc(v["note"])}</p>' if v.get('note') else ''}
{hist}</section>""")
        out.append(secbox(g['name'], len(g['venues']), ''.join(body)))
    out.append(FILTER_JS)
    out.append(SEC_JS)
    if D.get('watch'):
        ws = ''.join(f'<a class="link web" href="{esc(w["url"])}" target="_blank" rel="noopener">{esc(w["name"])}</a>'
                     for w in D['watch'])
        out.append(secbox('길목', len(D['watch']), f'<div class="watch">{ws}</div>'))
    if D.get('memo'):
        out.append(secbox('새겨 둘 것', len(D['memo']),
                       '<div class="memo">' + ''.join(f'<p>{esc(m)}</p>' for m in D['memo']) + '</div>'))
    out.append(FOOT.replace('{updated}', D['meta']['updated'].replace('-', '.')))
    return ''.join(out)


# ── 재료 ───────────────────────────────────────────────────────────────────
def all_items(D):
    """진행 중, 기다리는 중, 지난 일을 한 줄로 잇는다."""
    for s in D['sections']:
        for it in s['items']:
            yield it, False
    for it in D.get('archive', []):
        yield it, True


def fold(title, count, body, anchor=None):
    """접어 두는 마디. 읽을 것이지 오늘 할 일이 아니라면 접는다.

    펼쳐 둔 것이 많으면 무엇부터 볼지가 흐려진다.
    """
    n = f'<span class="c">{count}</span>' if count else ''
    a = f' id="{esc(anchor)}"' if anchor else ''
    return (f'<details class="fold"{a}><summary><h2>{esc(title)}</h2>{n}'
            f'<span class="arrow">\u25b8</span></summary>{body}</details>')


BOARD_JS = """<script>
(function () {
  var today = new Date(); today.setHours(0,0,0,0);
  function days(iso) {
    var p = iso.split('-');
    return Math.round((today - new Date(+p[0], +p[1]-1, +p[2])) / 86400000);
  }

  // 마지막으로 손댄 날. 오래 멎어 있으면 눈에 띄게 한다
  document.querySelectorAll('.touch[data-touched]').forEach(function (el) {
    var n = days(el.dataset.touched);
    if (n <= 7) { el.textContent = n <= 0 ? '오늘 손댐' : n + '일 전에 손댐'; }
    else if (n <= 20) { el.textContent = n + '일째 안 움직임'; el.dataset.cold = '1'; }
    else { el.textContent = n + '일째 멎어 있음'; el.dataset.stalled = '1'; }
  });

  // 지난 서른 날에 한 일
  var box = document.getElementById('tally');
  if (box && typeof DONE !== 'undefined') {
    var n = { '냈다': 0, '끝났다': 0, '손댔다': 0 };
    DONE.forEach(function (x) { if (days(x.d) <= 30 && days(x.d) >= 0) n[x.k]++; });
    var bits = [];
    if (n['냈다']) bits.push('낸 것 <b>' + n['냈다'] + '</b>');
    if (n['끝났다']) bits.push('끝난 것 <b>' + n['끝났다'] + '</b>');
    if (n['손댔다']) bits.push('손댄 갈래 <b>' + n['손댔다'] + '</b>');
    box.innerHTML = bits.length
      ? '<span class="cap">지난 서른 날</span>' + bits.join('<span class="dot">·</span>')
      : '';
  }

  // 해치운 표시. 이 기기에만 남는다. 데이터를 건드리지 않는다.
  //
  // 이 판은 서버가 없다. 네모를 누른 것이 저장소로 곧장 갈 길이 없다.
  // 가려면 쓰기 열쇠를 페이지 안에 넣어야 하는데, 그러면 암호를 아는 사람이
  // 저장소를 고칠 수 있게 된다. 판을 잠근 뜻이 없어진다.
  //
  // 그래서 다리를 놓는다. 누른 것을 한 덩이 글로 베껴 채팅에 붙이면
  // 다음 갱신이 그것을 읽어 데이터에서 걸음을 빼고 손댄 날을 오늘로 고친다.
  var boxes = document.querySelectorAll('input[data-done]');
  var bar = document.getElementById('carry');
  function label(b) {
    var el = document.querySelector('label[for="' + b.id + '"]');
    return el ? el.textContent.trim() : b.dataset.done;
  }
  function title(b) {
    var art = b.closest('.entry');
    var t = art && art.querySelector('.title-line .t');
    return t ? t.textContent.trim() : '';
  }
  function refresh() {
    if (!bar) return;
    var on = [].filter.call(boxes, function (b) { return b.checked; });
    bar.hidden = on.length === 0;
    var n = bar.querySelector('.n');
    if (n) n.textContent = on.length;
    bar.dataset.text = '로지아 갱신. 아래를 해치웠다.\\n'
      + on.map(function (b) { return '- ' + title(b) + ' · ' + label(b); }).join('\\n');
  }
  boxes.forEach(function (b) {
    var key = 'loggia.done.' + b.dataset.done;
    try { b.checked = localStorage.getItem(key) === '1'; } catch (e) {}
    b.closest('.step, li').dataset.done = b.checked ? '1' : '';
    b.addEventListener('change', function () {
      try { localStorage.setItem(key, b.checked ? '1' : '0'); } catch (e) {}
      b.closest('.step, li').dataset.done = b.checked ? '1' : '';
      refresh();
    });
  });
  if (bar) {
    bar.querySelector('.copy').addEventListener('click', function () {
      var t = bar.dataset.text;
      var done = function () {
        var el = bar.querySelector('.copy');
        var was = el.textContent; el.textContent = '베꼈습니다';
        setTimeout(function () { el.textContent = was; }, 1600);
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
      boxes.forEach(function (b) {
        if (!b.checked) return;
        b.checked = false;
        try { localStorage.setItem('loggia.done.' + b.dataset.done, '0'); } catch (e) {}
        b.closest('.step, li').dataset.done = '';
      });
      refresh();
    });
    refresh();
  }
})();
</script>"""


def secbox(title, count, body, key=None, open_=True):
    """마디 하나. 머리를 누르면 접힌다.

    펼침과 접힘은 이 기기에 남는다. 지금 안 보고 싶은 마디를 접어 두면
    다음에 열 때도 접혀 있다.
    """
    n = f'<span class="c">{count}</span>' if count is not None else ''
    k = f' data-k="{esc(key or title)}"' if key or title else ''
    a = f' id="{esc(key)}"' if key else ''
    return (f'<details class="group"{k}{a}{" open" if open_ else ""}>'
            f'<summary class="sec"><h2>{esc(title)}</h2>{n}'
            f'<span class="arrow">\u25b8</span></summary>{body}</details>')


SEC_JS = """<script>
// 마디의 펼침과 접힘을 이 기기에 남긴다.
// 자리표로 뛰어든 마디는 접혀 있어도 열어 준다. 아니면 머리만 보인다.
(function () {
  function openHash() {
    var el = location.hash && document.querySelector(location.hash);
    if (el && el.tagName === 'DETAILS' && !el.open) { el.open = true; el.scrollIntoView(); }
  }
  addEventListener('hashchange', openHash);
  setTimeout(openHash, 0);
  var page = location.pathname.split('/').pop() || 'index.html';
  document.querySelectorAll('details.group[data-k]').forEach(function (d) {
    var key = 'loggia.sec.' + page + '.' + d.dataset.k;
    try { var v = localStorage.getItem(key); if (v !== null) d.open = v === '1'; } catch (e) {}
    d.addEventListener('toggle', function () {
      if (d.dataset.auto) return;   // 거르개가 연 것은 기억하지 않는다
      try { localStorage.setItem(key, d.open ? '1' : '0'); } catch (e) {}
    });
  });
})();
</script>"""


def filters_html(buttons, label='골라 보기'):
    """거르는 단추 한 줄.

    단추마다 열쇠말 하나. 상자마다 data-tags 에 그 열쇠말이 적혀 있으면 남는다.
    빈 마디는 저절로 접힌다. 셈도 보이는 것만으로 다시 센다.
    """
    if len(buttons) < 2:
        return ''
    bs = ''.join(
        f'<button type="button" data-filter="{esc(k)}"'
        + (' aria-pressed="true"' if k == '*' else '')
        + f'>{esc(t)}' + (f'<b>{n}</b>' if n is not None else '') + '</button>'
        for k, t, n in buttons)
    return f'<div class="filters" role="group" aria-label="{esc(label)}">{bs}</div>'


FILTER_JS = """<script>
// 거르개. 누른 단추의 열쇠말을 가진 상자만 남긴다.
(function () {
  var bar = document.querySelector('.filters');
  if (!bar) return;
  var groups = Array.prototype.slice.call(document.querySelectorAll('.group'));
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
      var seen = 0;
      g.querySelectorAll('[data-tags]').forEach(function (el) {
        var on = k === '*' || (' ' + el.dataset.tags + ' ').indexOf(' ' + k + ' ') >= 0;
        el.hidden = !on;
        if (on) seen++;
      });
      g.hidden = seen === 0;
      // 거른 것이 접힌 마디 안에 있으면 안 보인다. 열어 준다.
      // 다만 이 열기는 기억하지 않는다. 손으로 접어 둔 뜻을 지우면 안 된다.
      if (k !== '*' && seen && g.tagName === 'DETAILS' && !g.open) {
        g.dataset.auto = '1'; g.open = true;
      } else if (k === '*' && g.dataset.auto) {
        g.dataset.auto = ''; g.open = false;
      }
      var c = g.querySelector('.c');
      if (c) c.textContent = k === '*' ? c.dataset.all : seen;
    });
  });
})();
</script>"""


def item_thinkers(item, D):
    """이 글이 누구를 쓰고 있나.

    두 길로 모은다.
    하나, 항목의 글에서 이름을 찾는다. thinkers 의 `말` 에 적어 둔 이름들이다.
    둘, `uses.이론가` 에 손으로 적은 것.

    첫째 길이 있어서 대개는 손으로 적을 일이 없다. 메모에 이름을 쓰면 그것으로 족하다.
    그리고 이론가를 나중에 더하면 이미 쌓인 메모를 거슬러 훑어 그때 걸린다.

    `말` 에는 사람 이름만 적는다. 학파나 개념 이름을 넣으면 잘못 걸린다.
    이를테면 '신현상학까지는 넓히지 않는다'는 메모는 슈미츠를 쓴다는 뜻이 아니다.
    """
    hay = ' '.join(str(item.get(k, '')) for k in ('title', 'kind', 'note', 'next'))
    found = []
    for tid, t in D.get('thinkers', {}).items():
        if any(w and w in hay for w in t.get('말', [])):
            found.append(tid)
    for tid in item.get('uses', {}).get('이론가', []):
        if tid not in found:
            found.append(tid)
    return found


def build_materials(D, nven, narc):
    """무엇으로 지었나. 이론가와 개념과 읽기에서 거꾸로 글을 찾는다.

    항목에 적은 열쇠말을 뒤집어 모은다. 손으로 두 번 적지 않는다.
    """
    thinkers = D.get('thinkers', {})
    readings = D.get('readings', {})

    by_thinker, by_concept, by_reading = {}, {}, {}
    for it, arc in all_items(D):
        u = it.get('uses', {})
        for t in item_thinkers(it, D):
            by_thinker.setdefault(t, []).append((it, arc))
        for c in u.get('개념', []):
            by_concept.setdefault(c, []).append((it, arc))
        for r in u.get('읽기', []):
            by_reading.setdefault(r, []).append((it, arc))

    def rows(entries):
        rs = []
        for it, arc in entries:
            st = D['statuses'].get(it.get('status'), {'label': it.get('status', ''), 'tone': 'live'})
            cls = {'live': 'live', 'wait': '', 'stop': 'stop', 'done': ''}.get(st['tone'], '')
            u = it.get('uses', {})
            cons = ' · '.join(u.get('개념', []))
            rs.append(f'<div class="hrow"><span class="mark {cls}">{esc(st["label"])}</span>'
                      f'<span class="t">{esc(it["title"])}</span>'
                      f'<span class="d">{esc(cons)}</span></div>')
        return ''.join(rs)

    out = [HEAD.format(title='재료', css=CSS, updated=D['meta']['updated'].replace('-', '.'),
                       h0='', hc='', h1='', h2='', h3=' here', nven=nven, narc=narc)]
    out.append('<p class="lede">무엇으로 지었나. 항목에 적어 둔 열쇠말을 뒤집어 모은 것이다. '
               '읽기는 파일이 아니라 읽기 묶음을 가리킨다. 글은 드롭박스에 있다.</p>')
    # 이 장은 길다. 맨 위에 바로 가는 길을 낸다
    out.append('<div class="jump">'
               '<a href="#thinkers">이론가</a><a href="#concepts">개념</a>'
               '<a href="#readings">읽기</a>'
               '<a href="#reuse" class="hot">다시 쓸 것 · CV와 지원서</a>'
               '<a href="#people">사람</a></div>')

    # 이론가. 많이 받치는 순서
    order = sorted(by_thinker.items(), key=lambda kv: (-len(kv[1]), kv[0]))
    body = []
    for tid, entries in order:
        t = thinkers.get(tid, {'name': tid})
        body.append(f"""<section class="venue-block" id="t-{esc(tid)}">
<div class="venue-head"><h3>{esc(t['name'])}</h3><span class="sub">{esc(t.get('sub',''))}</span></div>
<div class="history"><div class="cap">받치고 있는 글 · {len(entries)}편</div>{rows(entries)}</div></section>""")
    out.append(secbox('이론가', len(order), ''.join(body), key='thinkers'))

    # 개념
    corder = sorted(by_concept.items(), key=lambda kv: (-len(kv[1]), kv[0]))
    body = ['<div class="watch">' + ''.join(
        f'<a class="link web" href="#c-{esc(c)}">{esc(c)} <b>{len(e)}</b></a>' for c, e in corder) + '</div>']
    for cid, entries in corder:
        body.append(f"""<section class="venue-block" id="c-{esc(cid)}">
<div class="venue-head"><h3>{esc(cid)}</h3><span class="sub">{len(entries)}편</span></div>
<div class="history">{rows(entries)}</div></section>""")
    out.append(secbox('개념', len(corder), ''.join(body), key='concepts'))

    # 읽기. 아직 어디에도 안 쓴 묶음도 함께 보인다
    body = []
    for rid, r in readings.items():
        entries = by_reading.get(rid, [])
        name = (f'<a href="{esc(r["url"])}" target="_blank" rel="noopener">{esc(r["name"])}</a>'
                if r.get('url') else esc(r['name']))
        inner = (f'<div class="history"><div class="cap">여기서 흘러간 곳 · {len(entries)}편</div>{rows(entries)}</div>'
                 if entries else
                 '<p class="note">아직 어느 글에도 닿지 않았다. 덜 캔 광맥이거나, 다음 글의 씨앗이다.</p>')
        body.append(f"""<section class="venue-block" id="r-{esc(rid)}">
<div class="venue-head"><h3>{name}</h3><span class="sub">{esc(r.get('sub',''))}</span></div>
{inner}</section>""")
    out.append(secbox('읽기', len(readings), ''.join(body), key='readings'))

    if D.get('reuse'):
        rs = ''.join(
            '<div class="reuse"><div><p class="what">' + esc(r['이름'])
            + '</p><p class="from">' + esc(r.get('어디', '')) + '</p></div><div class="to">'
            + ''.join(f'<span>{esc(x)}</span>' for x in r.get('쓸 곳', []))
            + '</div>'
            + (f'<a class="link file" href="{esc(r["url"])}" target="_blank" rel="noopener">'
               f'{esc(r.get("파일", "파일"))}</a>'
               if r.get('url') else '')
            + '</div>'
            for r in D['reuse'])
        out.append(fold('다시 쓸 것', len(D['reuse']), anchor='reuse', body=
                        '<p class="lede">한 번 쓴 글의 어느 대목이 다음 어디로 가는가. '
                        '지원서를 열 때 여기부터 본다.</p>'
                        + f'<div class="reuses">{rs}</div>'))
    if D.get('people'):
        ps = ''.join(
            f'<div class="who-row"><span class="nm">{esc(pp["이름"])}</span>'
            f'<span class="role">{esc(pp.get("몫", ""))}</span>'
            + (f'<span class="last" data-since="{esc(pp["마지막"])}"></span>'
               if len(pp.get('마지막', '')) == 10 else
               f'<span class="last">{esc(pp.get("마지막", ""))}</span>')
            + f'<p class="n">{esc(pp.get("메모", ""))}</p></div>'
            for pp in D['people'])
        out.append(fold('사람', len(D['people']), anchor='people', body=
                        '<p class="lede">누구에게 무엇을 언제 부탁했나. '
                        '같은 사람에게 자주 갈 수는 없다.</p>'
                        + f'<div class="whos">{ps}</div>'))
    out.append(SEC_JS)
    out.append(FOOT.replace('{updated}', D['meta']['updated'].replace('-', '.')))
    return ''.join(out)


# ── 지난 일 ─────────────────────────────────────────────────────────────────
def build_archive(D, venue_index, nven, narc):
    out = [HEAD.format(title='지난 일', css=CSS, updated=D['meta']['updated'].replace('-', '.'),
                       h0='', hc='', h1='', h2=' here', h3='', nven=nven, narc=narc)]
    years = {}
    for it in D.get('archive', []):
        # 날짜는 연월까지만 아는 것도 있다. 그런 것은 연도만 떼어 묶는다
        dd = it.get('dates', {})
        y = (dd.get('decided') or dd.get('sent') or '')[:4] or '해 모름'
        years.setdefault(y, []).append(it)
    for y in sorted(years, reverse=True):
        body = []
        for it in years[y]:
            st = D['statuses'].get(it.get('status'), {'label': it.get('status', ''), 'tone': 'done'})
            cls = {'live': 'live', 'stop': 'stop'}.get(st['tone'], '')
            d = it.get('dates', {})
            facts = []
            if d.get('sent'):
                facts.append(f'<span><span class="lab">낸 날</span><b>{d["sent"].replace("-", ".")}</b></span>')
            if d.get('decided'):
                facts.append(f'<span><span class="lab">결과</span><b>{d["decided"].replace("-", ".")}</b></span>')
            rv = it.get('review')
            gist = (f'<p class="gist">{esc(rv["gist"])}<span class="who">{esc(rv.get("who",""))}</span></p>'
                    if rv else '')
            body.append(f"""<section class="venue-block t-{esc(st.get('tone', 'done'))}">
<div class="venue-head"><h3>{esc(it['title'])}</h3><span class="sub">{esc(it.get('kind',''))}</span>
<span class="mark {cls}">{esc(st['label'])}</span></div>
{f'<div class="venue-facts">{"".join(facts)}</div>' if facts else ''}
{gist}
{f'<p class="note">{esc(it["note"])}</p>' if it.get('note') else ''}
{links_html(it)}</section>""")
        out.append(secbox(str(y), len(years[y]), ''.join(body)))
    out.append(SEC_JS)
    out.append(FOOT.replace('{updated}', D['meta']['updated'].replace('-', '.')))
    return ''.join(out)


def waiting_clock(D, venue_index):
    """냈고 답을 기다리는 것들. 며칠째인지와 언제쯤 물어야 하는지.

    날수는 브라우저가 센다. 그래야 며칠 뒤에 열어도 낡지 않는다.
    `답까지` 는 그 지면이 대개 며칠 걸리는지다. 넘어가면 붉어진다.
    모르면 비워 둔다. 지어내지 않는다.
    """
    rows = []
    for sec in D['sections']:
        for it in sec['items']:
            d = it.get('dates', {})
            st = D['statuses'].get(it.get('status'), {})
            if not d.get('sent') or st.get('tone') != 'wait':
                continue
            v = venue_index.get(it.get('venue')) or {}
            days = v.get('답까지')
            expect = d.get('expected')
            side = []
            if days:
                side.append(f'<span class="lab">대개</span>{days}일')
            if expect:
                side.append(f'<span class="lab">짐작</span>{expect.replace("-", ".")}')
            body = ''
            if it.get('next'):
                body += f'<p class="todo">{esc(it["next"])}</p>'
            if it.get('note'):
                body += f'<p class="note">{esc(it["note"])}</p>'
            body += links_html(it)
            # 바깥 상자에는 data-since 를 걸지 않는다.
            # 날수를 적는 손이 그 상자의 안을 통째로 지워 버린다.
            rows.append(
                f'<details class="clock" data-sent="{esc(d["sent"])}"'
                + (f' data-days="{days}"' if days else '') + '><summary>'
                f'<span class="el" data-since="{esc(d["sent"])}"></span>'
                f'<span class="t">{esc(it["title"])}</span>'
                f'<span class="v">{esc(v.get("name", ""))}</span>'
                f'<span class="side">{"".join(f"<span>{s}</span>" for s in side)}</span>'
                f'<span class="arrow">\u25b8</span></summary>'
                f'<div class="clock-body">{body}</div></details>')
    if not rows:
        return ''
    return secbox('답을 기다리는 중', len(rows), '<div class="clocks">' + ''.join(rows) + '</div>')


def build_calendar(D, venue_index, nven, narc):
    """달력. 날짜는 페이지가 열릴 때 그린다. 그래야 오늘이 늘 가운데 온다.

    연월까지만 아는 날짜는 찍지 않는다. 하루를 지어내야 하기 때문이다.
    되풀이하는 마감은 브라우저가 그 달에 맞춰 셈한다. 그래야 해가 바뀌어도 이어진다.
    """
    ev = []
    for sec in D['sections']:
        for it in sec['items']:
            d = it.get('dates', {})
            v = venue_index.get(it.get('venue'))
            nm = it['title'] + (' · ' + v['name'] if v else '')
            if d.get('deadline'):
                ev.append({'d': d['deadline'], 'k': '마감', 't': nm})
            if d.get('sent'):
                ev.append({'d': d['sent'], 'k': '냄', 't': nm})
    for it in D.get('archive', []):
        d = it.get('dates', {})
        if d.get('decided'):
            ev.append({'d': d['decided'], 'k': '결과', 't': it['title']})
    # 처의 마감. 항목이 이미 같은 날 같은 처로 걸려 있으면 넣지 않는다.
    # 그러지 않으면 한 마감이 두 줄로 찍힌다.
    taken = set()
    for sec in D['sections']:
        for it in sec['items']:
            dl = it.get('dates', {}).get('deadline')
            if dl and it.get('venue'):
                taken.add((dl, it['venue']))
    for g in D['venueGroups']:
        for v in g['venues']:
            if v.get('deadline') and (v['deadline'], v['id']) not in taken:
                ev.append({'d': v['deadline'], 'k': '마감', 't': v['name']})
    ev = [e for e in ev if len(e['d']) == 10]   # 하루까지 아는 것만

    # 같은 날 같은 글은 한 번만
    uniq, key_seen = [], set()
    for e in sorted(ev, key=lambda x: (x['d'], x['t'])):
        k = (e['d'], e['k'], e['t'])
        if k not in key_seen:
            key_seen.add(k); uniq.append(e)

    # 되풀이하는 것들. 날짜는 브라우저가 그 달에 맞춰 짓는다
    reps = []
    for r in D.get('repeats', []):
        v = venue_index.get(r.get('venue')) or {}
        reps.append({'m': r['months'], 'day': r.get('day', '말일'),
                     't': r['label'] + (' · ' + v['name'] if v else ''),
                     'k': r.get('kind', '되풀이'), 'guess': bool(r.get('짐작'))})

    out = [HEAD.format(title='달력', css=CSS, updated=D['meta']['updated'].replace('-', '.'),
                       h0='', hc=' here', h1='', h2='', h3='', nven=nven, narc=narc)]
    out.append(waiting_clock(D, venue_index))
    if D.get('repeats'):
        rl = ''.join(
            f'<div class="rep"><span class="when">{"·".join(str(m) for m in r["months"])}월 '
            f'{r.get("day", "말일") if isinstance(r.get("day", "말일"), str) else str(r["day"]) + "일"}</span>'            + f'<span class="t">{esc(r["label"])}</span>'
            + (f'<span class="vn">{esc(venue_index[r["venue"]]["name"])}</span>'
               if r.get('venue') in venue_index else '')
            + ('<span class="guess">짐작</span>' if r.get('짐작') else '')
            + (f'<span class="n">{esc(r["note"])}</span>' if r.get('note') else '')
            + '</div>' for r in D['repeats'])
        out.append(fold('해마다 돌아오는 것', len(D['repeats']), f'<div class="reps">{rl}</div>'))
    out.append(secbox('한 해', None, """<div class="cal-legend"><span><b>굵은 날</b> 무엇인가 있는 날</span>
<span><b>붉은 밑줄</b> 이레 안 마감</span><span><b>주황 밑줄</b> 한 달 안 마감</span>
<span><b>네모</b> 오늘</span></div>
<div class="cal-grid" id="cal"></div>"""))
    out.append('<script>const EV = ' + json.dumps(uniq, ensure_ascii=False)
               + '; const REP = ' + json.dumps(reps, ensure_ascii=False) + ';</script>')
    out.append("""<script>
(function () {
  var W = ['일','월','화','수','목','금','토'];
  var today = new Date(); today.setHours(0,0,0,0);
  var byDay = {};
  EV.forEach(function (e) { (byDay[e.d] = byDay[e.d] || []).push(e); });

  // 되풀이하는 것을 그릴 달마다 앉힌다. 해가 바뀌어도 이어진다.
  function pad0(n) { return (n < 10 ? '0' : '') + n; }
  for (var o = -18; o <= 18; o++) {
    var mm = new Date(today.getFullYear(), today.getMonth() + o, 1);
    var yy = mm.getFullYear(), mn = mm.getMonth() + 1;
    REP.forEach(function (r) {
      if (r.m.indexOf(mn) < 0) return;
      var day = r.day === '말일' ? new Date(yy, mn, 0).getDate() : +r.day;
      var iso = yy + '-' + pad0(mn) + '-' + pad0(day);
      (byDay[iso] = byDay[iso] || []).push({ d: iso, k: r.k, t: r.t, rep: true, guess: r.guess });
    });
  }

  function urg(iso) {
    var p = iso.split('-'), d = new Date(+p[0], +p[1]-1, +p[2]);
    var n = Math.round((d - today) / 86400000);
    return { n: n, c: n < 0 ? '' : n <= 7 ? 'now' : n <= 30 ? 'soon' : '' };
  }
  function pad(n) { return (n < 10 ? '0' : '') + n; }

  var box = document.getElementById('cal');
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
        list.forEach(function (e) { if (e.k === '마감' && !e.rep) { var u = urg(e.d).c; if (u === 'now' || (u === 'soon' && worst !== 'now')) worst = u; } });
        if (worst) cls.push(worst);
        rows.push({ day: day, iso: iso, list: list });
      }
      if (iso === today.getFullYear() + '-' + pad(today.getMonth()+1) + '-' + pad(today.getDate())) cls.push('today');
      h += '<td class="' + cls.join(' ') + '">' + day + '</td>';
      if ((first + day) % 7 === 0 && day !== last) h += '</tr><tr>';
    }
    h += '</tr></tbody></table>';

    if (rows.length) {
      h += '<div class="cal-ev">';
      rows.forEach(function (r) {
        r.list.forEach(function (e) {
          var u = (e.k === '마감' && !e.rep) ? urg(e.d).c : '';
          h += '<div class="r ' + u + (e.rep ? ' rep' : '') + '"><span class="dd">' + r.day + '</span>'
             + '<span class="tx">' + e.t + ' <span style="color:var(--ink-3)">' + e.k
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
})();
</script>""")
    out.append(SEC_JS)
    out.append(FOOT.replace('{updated}', D['meta']['updated'].replace('-', '.')))
    return ''.join(out)


def digest_json(D, venue_index):
    """워커가 아침에 읽는 작은 꾸러미.

    여기서는 날짜 셈을 하나도 하지 않는다. 오늘이 언제인지는 편지를 부치는
    그 순간에만 알 수 있다. 판이 몇 주 동안 올라가지 않아도 아침 편지가
    낡지 않으려면, 담는 것은 날것이어야 하고 며칠 남았는지는 워커가 세야 한다.

    브라우저가 하는 일과 같은 원리다. 다만 손이 하나 더 늘었을 뿐이다.
    """
    def vname(vid):
        return (venue_index.get(vid) or {}).get('name', '')

    due, doing, wait, quiet = [], [], [], []
    for sec in D['sections']:
        for it in sec['items']:
            d = it.get('dates', {})
            st = D['statuses'].get(it.get('status'), {})
            ss = steps_of(it)
            base = {'t': it['title'], 'v': vname(it.get('venue'))}
            if d.get('deadline'):
                due.append(dict(base, due=d['deadline'], step=(ss[0] if ss else '')))
            if sec['id'] == 'now' and ss:
                doing.append(dict(base, step=ss[0], due=d.get('deadline', ''),
                                  pum=D.get('efforts', {}).get(it.get('품'), {}).get('label', '')))
            if d.get('sent') and st.get('tone') == 'wait':
                v = venue_index.get(it.get('venue')) or {}
                row = dict(base, sent=d['sent'])
                if v.get('답까지'):
                    row['until'] = v['답까지']
                wait.append(row)
            elif d.get('touched'):
                quiet.append(dict(base, touched=d['touched']))

    reps = [{'m': r['months'], 'day': r.get('day', '말일'),
             't': r['label'], 'v': vname(r.get('venue')), 'guess': bool(r.get('짐작'))}
            for r in D.get('repeats', [])]

    return {
        'built': D['meta']['updated'],
        'site': D['meta'].get('site') or 'https://loggia.moonilsun.com/',
        'due': sorted(due, key=lambda x: x['due']),
        'doing': doing,
        'wait': wait,
        'quiet': quiet,
        'repeats': reps,
    }


def snapshot_md(D, venue_index):
    """눈으로 훑는 사본. 드롭박스에 내려놓아 눌러 보는 용도다.

    진짜 데이터가 아니다. 여기 고쳐 봐야 판에 닿지 않는다.
    그 사실을 첫 줄에 적어 둔다.
    """
    L = ['# 로지아 스냅샷',
         '',
         f'갱신 {D["meta"]["updated"]} · {D["meta"].get("note", "")}',
         '',
         '> 이것은 **눈으로 보는 사본**이다. 진짜 데이터는 저장소 `eeruwang/loggia` 의',
         '> `data.enc` 안에 잠겨 있다. 여기를 고쳐도 판은 바뀌지 않는다.',
         '> 고치려면 `tools/fetch.sh` 로 받아 `loggia-data.json` 을 손본다.',
         '']
    for s in D['sections']:
        L += [f'## {s["label"]}', '']
        for it in s['items']:
            v = venue_index.get(it.get('venue'))
            st = D['statuses'].get(it.get('status'), {}).get('label', it.get('status', ''))
            d = it.get('dates', {})
            when = (('마감 ' + d['deadline']) if d.get('deadline')
                    else ('냄 ' + d['sent']) if d.get('sent') else '')
            head = f'- **{it["title"]}**'
            if v:
                head += f' · {v["name"]}'
            L.append(head + f'  \n  {it.get("kind", "")} · {st}' + (f' · {when}' if when else ''))
            if it.get('next'):
                L.append(f'  \n  다음 걸음. {it["next"]}')
            if it.get('note'):
                L.append(f'  \n  {it["note"]}')
            L.append('')
    if D.get('archive'):
        L += ['## 지난 일', '']
        for it in D['archive']:
            d = it.get('dates', {})
            L.append(f'- **{it["title"]}** · {D["statuses"].get(it.get("status"), {}).get("label", "")}'
                     + (f' · {d["decided"]}' if d.get('decided') else ''))
            if it.get('review', {}).get('gist'):
                L.append(f'  \n  심사평. {it["review"]["gist"]}')
            L.append('')
    L += ['## 낼 곳', '']
    for g in D['venueGroups']:
        L += [f'### {g["name"]}', '']
        for v in g['venues']:
            tags = ' · '.join(t for _, t in index_tags(v, D))
            bits = [b for b in [v.get('sub'), tags, v.get('flag'),
                                ('마감 ' + v['deadline']) if v.get('deadline') else None,
                                v.get('cost')] if b]
            L.append(f'- **{v["name"]}** — ' + ' · '.join(bits) if bits else f'- **{v["name"]}**')
            if v.get('note'):
                L.append(f'  \n  {v["note"]}')
            L.append('')
    if D.get('memo'):
        L += ['## 기억해 둘 것', ''] + [f'- {m}' for m in D['memo']] + ['']
    return '\n'.join(L)


def main():
    data_path, out_dir = sys.argv[1], sys.argv[2]
    D = json.load(open(data_path, encoding='utf-8'))
    os.makedirs(out_dir, exist_ok=True)

    venue_index, items_by_venue = {}, {}
    for g in D['venueGroups']:
        for v in g['venues']:
            venue_index[v['id']] = v
    for s in D['sections']:
        for it in s['items']:
            if it.get('venue'):
                items_by_venue.setdefault(it['venue'], []).append((it, False))
    for it in D.get('archive', []):
        if it.get('venue'):
            items_by_venue.setdefault(it['venue'], []).append((it, True))

    nven = sum(len(g['venues']) for g in D['venueGroups'])
    narc = len(D.get('archive', []))

    pages = {
        'index.html': build_index(D, venue_index, nven, narc),
        'journals.html': build_journals(D, venue_index, items_by_venue, nven, narc),
        'calendar.html': build_calendar(D, venue_index, nven, narc),
        'materials.html': build_materials(D, nven, narc),
        'archive.html': build_archive(D, venue_index, nven, narc),
    }
    for name, html_text in pages.items():
        with open(os.path.join(out_dir, name), 'w', encoding='utf-8') as f:
            f.write(html_text)
        print(f'  {name}  {len(html_text)//1024}KB')

    # 눈으로 보는 사본. 판과 함께 나오되 저장소에는 올리지 않는다
    md = snapshot_md(D, venue_index)
    with open(os.path.join(out_dir, '스냅샷.md'), 'w', encoding='utf-8') as f:
        f.write(md)
    print(f'  스냅샷.md  {len(md.encode())//1024}KB  (드롭박스에 내려놓는 사본)')

    # 아침 편지가 읽을 꾸러미. publish.sh 가 생열쇠로 봉해 digest.enc 로 올린다
    dg = json.dumps(digest_json(D, venue_index), ensure_ascii=False, separators=(',', ':'))
    with open(os.path.join(out_dir, 'digest.json'), 'w', encoding='utf-8') as f:
        f.write(dg)
    print(f'  digest.json  {len(dg.encode())//1024}KB  (아침 편지가 읽는 것)')


if __name__ == '__main__':
    main()
