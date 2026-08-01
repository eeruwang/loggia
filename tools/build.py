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
import json, sys, html, os

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
    el.textContent = n < 0 ? '지남' : n === 0 ? '오늘' : 'D-' + n;
    el.dataset.urgency = urg;
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

/* 답을 기다리는 중 */
.clocks{margin-top:2px}
.clock{display:flex;align-items:center;gap:16px;flex-wrap:wrap;padding:16px 20px;margin-bottom:10px;
background:var(--surface);border:1px solid var(--rule);border-left:6px solid var(--wait);border-radius:12px}
.clock .el{font-size:24px;font-weight:800;letter-spacing:-.02em;color:var(--ink);min-width:84px}
.clock[data-late]{border-left-color:var(--now)}
.clock[data-late] .el{color:var(--now)}
.clock .t{font-size:17px;font-weight:700;color:var(--ink)}
.clock .v{font-size:13px;font-weight:600;color:var(--ink-3)}
.clock .side{margin-left:auto;display:flex;gap:16px;font-size:13px;color:var(--ink-2);align-items:center}
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
        return (f'<div class="when-col"><span class="dday" data-deadline="{iso}">D-</span>'
                f'<span class="date">{iso[5:].replace("-", ".")}</span></div>')
    if d.get('sent'):
        iso = d['sent']
        return (f'<div class="when-col"><span class="dday none" data-since="{iso}"></span>'
                f'<span class="date">{iso[5:].replace("-", ".")} 냄</span></div>')
    return '<div class="when-col"><span class="dday none">—</span></div>'


def entry_html(item, D, venue_index):
    st = D['statuses'].get(item.get('status'), {'label': item.get('status', ''), 'tone': 'live'})
    v = venue_index.get(item.get('venue'))
    venue = f'<a class="venue" href="journals.html#{esc(item["venue"])}">{esc(v["name"])}</a>' if v else ''
    nxt = item.get('next')
    todo = (f'<p class="todo">{esc(nxt)}</p>' if nxt
            else '<p class="todo none">지금 할 일 없음</p>')
    note = f'<p class="note">{esc(item["note"])}</p>' if item.get('note') else ''
    # 결마다 빛깔을 준다. 왼쪽 띠 하나로 무슨 종류인지 눈이 먼저 안다
    return f"""<article class="entry t-{esc(st.get('tone', 'live'))}">{when_col(item)}
<div class="body"><div class="title-line"><h3 class="t">{esc(item['title'])}</h3>
<span class="state">{esc(st['label'])}</span></div>
<div class="meta">{venue}<span class="k">{esc(item.get('kind',''))}</span></div>
{todo}{note}{links_html(item)}</div></article>"""


def pick_focus(D):
    best = None
    for s in D['sections']:
        for it in s['items']:
            dl = it.get('dates', {}).get('deadline')
            if dl and it.get('next') and (best is None or dl < best['dates']['deadline']):
                best = it
    return best


# ── 현황판 ──────────────────────────────────────────────────────────────────
def build_index(D, venue_index, nven, narc):
    out = [HEAD.format(title=esc(D['meta']['title']), css=CSS,
                       updated=D['meta']['updated'].replace('-', '.'),
                       h0=' here', hc='', h1='', h2='', h3='', nven=nven, narc=narc)]
    f = pick_focus(D)
    if f:
        v = venue_index.get(f.get('venue'))
        iso = f['dates']['deadline']
        out.append(f"""<section class="focus"><div class="cap">지금 이것부터</div>
<div class="line"><span class="dday" data-deadline="{iso}">D-</span>
<span class="who">{esc(f['title'])}{' · ' + esc(v['name']) if v else ''}</span></div>
<p class="todo">{esc(f['next'])}</p>
<div class="when">마감 {iso[5:7].lstrip('0')}월 {iso[8:].lstrip('0')}일</div></section>""")
    for s in D['sections']:
        out.append(f'<div class="sec"><h2>{esc(s["label"])}</h2><span class="c">{len(s["items"])}</span></div>')
        for it in sorted(s['items'], key=lambda i: i.get('dates', {}).get('deadline') or '9999'):
            out.append(entry_html(it, D, venue_index))
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
    for g in D['venueGroups']:
        out.append(f'<div class="sec"><h2>{esc(g["name"])}</h2><span class="c">{len(g["venues"])}</span></div>')
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
                             f'<b class="dday" style="font-size:13.5px;display:inline" data-deadline="{iso}">D-</b></span>')
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
            out.append(f"""<section class="venue-block" id="{esc(v['id'])}">
<div class="venue-head"><h3>{name}</h3><span class="sub">{esc(v.get('sub',''))} · {esc(v.get('type',''))}</span></div>
{f'<div class="idx-row">{tags}</div>' if tags else ''}
{f'<div class="venue-facts">{"".join(facts)}</div>' if facts else ''}
{f'<p class="note">{esc(v["note"])}</p>' if v.get('note') else ''}
{hist}</section>""")
    if D.get('watch'):
        out.append('<div class="sec"><h2>길목</h2><span class="c">%d</span></div>' % len(D['watch']))
        ws = ''.join(f'<a class="link web" href="{esc(w["url"])}" target="_blank" rel="noopener">{esc(w["name"])}</a>'
                     for w in D['watch'])
        out.append(f'<div class="watch">{ws}</div>')
    if D.get('memo'):
        out.append('<div class="sec"><h2>새겨 둘 것</h2></div><div class="memo">'
                   + ''.join(f'<p>{esc(m)}</p>' for m in D['memo']) + '</div>')
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


def fold(title, count, body):
    """접어 두는 마디. 읽을 것이지 오늘 할 일이 아니라면 접는다.

    펼쳐 둔 것이 많으면 무엇부터 볼지가 흐려진다.
    """
    n = f'<span class="c">{count}</span>' if count else ''
    return (f'<details class="fold"><summary><h2>{esc(title)}</h2>{n}'
            f'<span class="arrow">\u25b8</span></summary>{body}</details>')


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

    # 이론가. 많이 받치는 순서
    order = sorted(by_thinker.items(), key=lambda kv: (-len(kv[1]), kv[0]))
    out.append(f'<div class="sec"><h2>이론가</h2><span class="c">{len(order)}</span></div>')
    for tid, entries in order:
        t = thinkers.get(tid, {'name': tid})
        out.append(f"""<section class="venue-block" id="t-{esc(tid)}">
<div class="venue-head"><h3>{esc(t['name'])}</h3><span class="sub">{esc(t.get('sub',''))}</span></div>
<div class="history"><div class="cap">받치고 있는 글 · {len(entries)}편</div>{rows(entries)}</div></section>""")

    # 개념
    corder = sorted(by_concept.items(), key=lambda kv: (-len(kv[1]), kv[0]))
    out.append(f'<div class="sec"><h2>개념</h2><span class="c">{len(corder)}</span></div>')
    out.append('<div class="watch">' + ''.join(
        f'<a class="link web" href="#c-{esc(c)}">{esc(c)} <b>{len(e)}</b></a>' for c, e in corder) + '</div>')
    for cid, entries in corder:
        out.append(f"""<section class="venue-block" id="c-{esc(cid)}">
<div class="venue-head"><h3>{esc(cid)}</h3><span class="sub">{len(entries)}편</span></div>
<div class="history">{rows(entries)}</div></section>""")

    # 읽기. 아직 어디에도 안 쓴 묶음도 함께 보인다
    out.append(f'<div class="sec"><h2>읽기</h2><span class="c">{len(readings)}</span></div>')
    for rid, r in readings.items():
        entries = by_reading.get(rid, [])
        name = (f'<a href="{esc(r["url"])}" target="_blank" rel="noopener">{esc(r["name"])}</a>'
                if r.get('url') else esc(r['name']))
        body = (f'<div class="history"><div class="cap">여기서 흘러간 곳 · {len(entries)}편</div>{rows(entries)}</div>'
                if entries else
                '<p class="note">아직 어느 글에도 닿지 않았다. 덜 캔 광맥이거나, 다음 글의 씨앗이다.</p>')
        out.append(f"""<section class="venue-block" id="r-{esc(rid)}">
<div class="venue-head"><h3>{name}</h3><span class="sub">{esc(r.get('sub',''))}</span></div>
{body}</section>""")

    if D.get('reuse'):
        rs = ''.join(
            '<div class="reuse"><div><p class="what">' + esc(r['이름'])
            + '</p><p class="from">' + esc(r.get('어디', '')) + '</p></div><div class="to">'
            + ''.join(f'<span>{esc(x)}</span>' for x in r.get('쓸 곳', []))
            + '</div>'
            + (f'<a class="link file" href="{esc(r["url"])}" target="_blank" rel="noopener">파일</a>'
               if r.get('url') else '')
            + '</div>'
            for r in D['reuse'])
        out.append(fold('다시 쓸 것', len(D['reuse']),
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
        out.append(fold('사람', len(D['people']),
                        '<p class="lede">누구에게 무엇을 언제 부탁했나. '
                        '같은 사람에게 자주 갈 수는 없다.</p>'
                        + f'<div class="whos">{ps}</div>'))
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
        out.append(f'<div class="sec"><h2>{y}</h2><span class="c">{len(years[y])}</span></div>')
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
            out.append(f"""<section class="venue-block">
<div class="venue-head"><h3>{esc(it['title'])}</h3><span class="sub">{esc(it.get('kind',''))}</span></div>
<div class="idx-row"><span class="mark {cls}">{esc(st['label'])}</span></div>
{f'<div class="venue-facts">{"".join(facts)}</div>' if facts else ''}
{gist}
{f'<p class="note">{esc(it["note"])}</p>' if it.get('note') else ''}
{links_html(it)}</section>""")
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
            rows.append(
                # 바깥 상자에는 data-since 를 걸지 않는다.
                # 날수를 적는 손이 그 상자의 안을 통째로 지워 버린다.
                f'<div class="clock" data-sent="{esc(d["sent"])}"'
                + (f' data-days="{days}"' if days else '') + '>'
                f'<span class="el" data-since="{esc(d["sent"])}"></span>'
                f'<span class="t">{esc(it["title"])}</span>'
                f'<span class="v">{esc(v.get("name", ""))}</span>'
                f'<span class="side">{"".join(f"<span>{s}</span>" for s in side)}</span></div>')
    if not rows:
        return ''
    return ('<div class="sec"><h2>답을 기다리는 중</h2><span class="c">%d</span></div>' % len(rows)
            + '<div class="clocks">' + ''.join(rows) + '</div>')


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
            f'{r.get("day", "말일") if isinstance(r.get("day", "말일"), str) else str(r["day"]) + "일"}</span>'
            f'<span class="t">{esc(r["label"])}</span>'
            + ('<span class="guess">짐작</span>' if r.get('짐작') else '')
            + (f'<span class="n">{esc(r["note"])}</span>' if r.get('note') else '')
            + '</div>' for r in D['repeats'])
        out.append(fold('해마다 돌아오는 것', len(D['repeats']), f'<div class="reps">{rl}</div>'))
    out.append("""<div class="sec"><h2>한 해</h2><span class="c">오늘 앞뒤 여섯 달</span></div>
<div class="cal-legend"><span><b>굵은 날</b> 무엇인가 있는 날</span>
<span><b>붉은 밑줄</b> 이레 안 마감</span><span><b>주황 밑줄</b> 한 달 안 마감</span>
<span><b>네모</b> 오늘</span></div>
<div class="cal-grid" id="cal"></div>""")
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
    out.append(FOOT.replace('{updated}', D['meta']['updated'].replace('-', '.')))
    return ''.join(out)


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


if __name__ == '__main__':
    main()
