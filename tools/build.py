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
<link rel="preconnect" href="https://cdn.jsdelivr.net" crossorigin>
<link rel="stylesheet" href="https://cdn.jsdelivr.net/gh/orioncactus/pretendard/dist/web/variable/pretendardvariable-dynamic-subset.css">
<script>
/* 화면이 그려지기 전에 밝기를 정한다. 늦게 정하면 한 번 번쩍인다. */
(function(){{try{{document.documentElement.dataset.theme=localStorage.getItem('loggia.theme')||'auto'}}catch(e){{}}}})();
</script>
<style>{css}</style>
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
    el.textContent = Math.round((today - d) / 86400000) + '일째';
  });
})();
</script>
</body>
</html>
"""

CSS = """
:root{--paper:hsl(40 12% 97%);--surface:hsl(40 20% 99.5%);--ink:hsl(28 10% 12%);
--ink-2:hsl(28 6% 34%);--ink-3:hsl(28 5% 52%);--rule:hsl(35 12% 87%);--rule-2:hsl(35 10% 78%);
--now:hsl(4 74% 45%);--soon:hsl(30 88% 40%);--later:hsl(28 5% 45%);--good:hsl(154 44% 28%);
--font:'Pretendard Variable',Pretendard,-apple-system,BlinkMacSystemFont,'Apple SD Gothic Neo','Noto Sans KR','Malgun Gothic',system-ui,sans-serif;
--scale:1;--page-max:820px;--col:92px}
/* 어두운 판의 값. 두 곳에서 같은 값을 쓴다.
   하나는 기기 설정을 따르는 자동, 하나는 손으로 고른 어둡게.
   html 에 data-theme=light 가 걸리면 자동이 눌리지 않는다. */
@media(prefers-color-scheme:dark){html:not([data-theme=light]) {--paper:hsl(28 8% 10%);--surface:hsl(28 7% 14%);
--ink:hsl(40 12% 94%);--ink-2:hsl(35 6% 72%);--ink-3:hsl(35 5% 56%);--rule:hsl(28 6% 24%);
--rule-2:hsl(28 6% 32%);--now:hsl(4 84% 66%);--soon:hsl(34 92% 60%);--later:hsl(35 5% 58%);--good:hsl(154 44% 58%)}}
html[data-theme=dark]{--paper:hsl(28 8% 10%);--surface:hsl(28 7% 14%);
--ink:hsl(40 12% 94%);--ink-2:hsl(35 6% 72%);--ink-3:hsl(35 5% 56%);--rule:hsl(28 6% 24%);
--rule-2:hsl(28 6% 32%);--now:hsl(4 84% 66%);--soon:hsl(34 92% 60%);--later:hsl(35 5% 58%);--good:hsl(154 44% 58%)}

/* 밝기 고르는 단추. 표제 오른쪽에 작게 앉는다 */
.mode{display:inline-flex;border:1px solid var(--rule-2);border-radius:3px;overflow:hidden;margin-left:12px;vertical-align:middle}
.mode button{appearance:none;border:0;background:transparent;cursor:pointer;font-family:var(--font);
font-size:12px;font-weight:600;color:var(--ink-3);padding:6px 10px;border-right:1px solid var(--rule-2)}
.mode button:last-child{border-right:0}
.mode button:hover{color:var(--ink-2)}
.mode button[aria-pressed=true]{background:var(--ink);color:var(--paper)}
*{box-sizing:border-box}
body{margin:0;padding:0 22px 120px;background:var(--paper);color:var(--ink);font-family:var(--font);
font-size:calc(16.5px*var(--scale));line-height:1.68;-webkit-font-smoothing:antialiased;font-variant-numeric:tabular-nums}
.wrap{max-width:var(--page-max);margin:0 auto}
.masthead{display:flex;align-items:baseline;justify-content:space-between;gap:16px;flex-wrap:wrap;padding:36px 0 14px}
.masthead .name{font-size:12px;letter-spacing:.3em;text-transform:uppercase;color:var(--ink-3)}
.masthead h1{font-size:19px;font-weight:700;margin:4px 0 0}
.masthead .stamp{font-size:12px;color:var(--ink-3)}
.tabs{display:flex;gap:4px;flex-wrap:wrap;margin:4px 0 0;border-bottom:1px solid var(--rule)}
.tab{display:inline-flex;align-items:baseline;gap:7px;padding:12px 14px;margin-bottom:-1px;font-size:15px;
font-weight:600;color:var(--ink-3);text-decoration:none;border-bottom:3px solid transparent}
.tab:first-child{padding-left:0}
.tab .n{font-size:12.5px;font-weight:400;color:var(--ink-3)}
.tab.here{color:var(--ink);border-bottom-color:var(--ink)}
.focus{background:var(--surface);border:2px solid var(--ink);padding:22px 24px 24px;margin:10px 0 44px}
.focus .cap{font-size:12px;font-weight:700;letter-spacing:.06em;color:var(--ink-2);margin-bottom:14px}
.focus .line{display:flex;align-items:baseline;gap:14px;flex-wrap:wrap}
.focus .dday{font-size:34px;font-weight:700;letter-spacing:-.02em;line-height:1;color:var(--now)}
.focus .who{font-size:15px;color:var(--ink-2)}
.focus .todo{font-size:23px;font-weight:700;line-height:1.4;margin:12px 0 0}
.focus .when{font-size:13px;color:var(--ink-3);margin-top:10px}
.sec{display:flex;align-items:baseline;gap:12px;margin:46px 0 4px;padding-bottom:10px;border-bottom:2px solid var(--ink)}
.sec h2{font-size:15px;font-weight:700;letter-spacing:.06em;margin:0}
.sec .c{margin-left:auto;font-size:13px;color:var(--ink-3)}
.entry{display:grid;grid-template-columns:var(--col) 1fr;gap:22px;padding:26px 0 28px;border-bottom:1px solid var(--rule)}
.when-col{text-align:right}
.dday{font-size:26px;font-weight:700;letter-spacing:-.02em;line-height:1.05;color:var(--later);display:block}
.dday[data-urgency=now]{color:var(--now)}
.dday[data-urgency=soon]{color:var(--soon)}
.dday[data-urgency=past]{color:var(--ink-3)}
.dday.none{color:var(--ink-3);font-size:19px}
.when-col .date{display:block;margin-top:5px;font-size:12px;color:var(--ink-3)}
.title-line{display:flex;align-items:baseline;gap:10px;flex-wrap:wrap}
.title-line .t{font-size:14.5px;font-weight:600;color:var(--ink-2)}
.title-line .k{font-size:12px;color:var(--ink-3)}
.title-line .state{font-size:12px;font-weight:600;color:var(--ink-2);border:1px solid var(--rule-2);padding:2px 8px;border-radius:2px}
.venue{font-size:13.5px;font-weight:600;color:var(--ink-2);text-decoration:none;border-bottom:1.5px solid var(--rule-2);padding-bottom:1px}
.venue::before{content:'\\2192 ';color:var(--ink-3);font-weight:400}
.venue:hover{color:var(--ink);border-color:var(--ink)}
.todo{display:flex;align-items:baseline;gap:11px;font-size:19px;font-weight:700;line-height:1.45;margin:10px 0 0}
.todo::before{content:'';flex:none;align-self:baseline;width:.74em;height:.74em;transform:translateY(.04em);
border:.1em solid var(--ink);border-radius:2px}
.todo.none{font-weight:500;color:var(--ink-3)}
.todo.none::before{border-color:var(--rule-2)}
.note{margin:12px 0 0;font-size:14px;color:var(--ink-2);line-height:1.6;max-width:58ch}
.links{margin-top:14px;display:flex;flex-wrap:wrap;gap:8px}
.link{font-size:13px;color:var(--ink-2);text-decoration:none;border:1px solid var(--rule-2);border-radius:3px;padding:7px 12px}
.link:hover{color:var(--ink);border-color:var(--ink)}
.link::before{font-size:11px;color:var(--ink-3);margin-right:7px}
.link.file::before{content:'\\25B8'}
.link.chat::before{content:'/'}
.link.web::before{content:'\\2197'}
.venue-block{padding:26px 0 28px;border-bottom:1px solid var(--rule);scroll-margin-top:20px}
.venue-head{display:flex;align-items:baseline;gap:12px;flex-wrap:wrap}
.venue-head h3{font-size:19px;font-weight:700;margin:0}
.venue-head h3 a{color:inherit;text-decoration:none;border-bottom:2px solid var(--rule-2)}
.venue-head h3 a:hover{border-color:var(--ink)}
.venue-head .sub{font-size:13.5px;color:var(--ink-3)}
.idx-row{display:flex;flex-wrap:wrap;gap:5px;margin-top:9px;align-items:center}
.idx{font-size:11.5px;font-weight:700;letter-spacing:.04em;padding:3px 8px;border:1.5px solid var(--rule-2);
border-radius:2px;color:var(--ink-2);white-space:nowrap}
.idx.strong{background:var(--ink);border-color:var(--ink);color:var(--paper)}
.idx.plain{border-color:var(--ink-3);color:var(--ink-2)}
.idx.none{border-style:dashed;color:var(--ink-3)}
.flag{font-size:11.5px;font-weight:700;color:var(--soon);border:1.5px solid var(--soon);padding:3px 8px;border-radius:2px}
.venue-facts{display:flex;flex-wrap:wrap;gap:8px 22px;margin-top:10px;font-size:13.5px;color:var(--ink-2)}
.venue-facts b{font-weight:600;color:var(--ink)}
.venue-facts .lab{color:var(--ink-3);margin-right:6px}
.history{margin-top:18px;border-left:3px solid var(--rule);padding-left:18px}
.history .cap{font-size:12px;font-weight:700;letter-spacing:.06em;color:var(--ink-3);margin-bottom:10px}
.hrow{display:flex;align-items:baseline;gap:12px;flex-wrap:wrap;padding:9px 0;border-bottom:1px solid var(--rule);font-size:14.5px}
.hrow:last-child{border-bottom:0}
.hrow .t{font-weight:600}
.hrow .d{margin-left:auto;font-size:12.5px;color:var(--ink-3);white-space:nowrap}
.mark{font-size:12.5px;font-weight:700;padding:2px 8px;border:1.5px solid var(--rule-2);border-radius:2px;color:var(--ink-2)}
.mark.live{border-color:var(--ink);color:var(--ink)}
.mark.good{border-color:var(--good);color:var(--good)}
.mark.stop{border-color:var(--now);color:var(--now)}
.gist{width:100%;margin:10px 0 0;padding-left:14px;border-left:2px solid var(--rule);font-size:13.5px;color:var(--ink-2);line-height:1.7}
.gist .who{display:block;font-size:12px;color:var(--ink-3);margin-top:6px}
.compass{margin-top:46px;padding:20px 22px;border:1px solid var(--rule);background:var(--surface)}
.compass .cap{font-size:12px;font-weight:700;letter-spacing:.06em;color:var(--ink-3);margin-bottom:10px}
.compass p{margin:0 0 8px;font-size:14px;color:var(--ink-2);line-height:1.65}
.compass p:last-child{margin-bottom:0}
.watch{display:flex;flex-wrap:wrap;gap:8px;margin-top:16px}
.memo{margin-top:20px}
.memo p{font-size:13.5px;color:var(--ink-2);line-height:1.7;margin:0 0 12px;padding-left:14px;border-left:2px solid var(--rule)}

/* ── 달력 ────────────────────────────────────────────────────────────────
   한 해를 열세 칸으로 나눠 늘어놓는다. 오늘이 든 달이 가운데 온다.
   날짜에 표가 붙은 날은 굵고, 마감이면 급함의 빛깔이 밑줄로 깔린다. */
.cal-grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(230px,1fr));gap:28px 26px;margin-top:26px}
.cal-m{}
.cal-m.past{opacity:.5}
.cal-m h3{font-size:13.5px;font-weight:700;margin:0 0 8px;padding-bottom:6px;border-bottom:1px solid var(--rule)}
.cal-m.here h3{border-bottom:2px solid var(--ink)}
table.cal{width:100%;border-collapse:collapse;font-size:12.5px;table-layout:fixed}
table.cal th{font-size:10.5px;font-weight:600;color:var(--ink-3);padding:3px 0;text-align:center}
table.cal td{text-align:center;padding:4px 0 5px;color:var(--ink-2);position:relative}
table.cal td.off{color:transparent}
table.cal td.has{font-weight:700;color:var(--ink)}
table.cal td.has::after{content:'';position:absolute;left:50%;transform:translateX(-50%);bottom:1px;
width:14px;height:2.5px;background:var(--mark,var(--ink-3));border-radius:2px}
table.cal td.now::after{--mark:var(--now)}
table.cal td.soon::after{--mark:var(--soon)}
table.cal td.today{outline:1.5px solid var(--ink);border-radius:3px;font-weight:700;color:var(--ink)}
.cal-ev{margin-top:9px;font-size:12.5px}
.cal-ev .r{display:flex;gap:9px;align-items:baseline;padding:3px 0;line-height:1.45}
.cal-ev .dd{flex:none;width:20px;text-align:right;color:var(--ink-3)}
.cal-ev .tx{color:var(--ink-2)}
.cal-ev .r.now .tx{color:var(--now);font-weight:600}
.cal-ev .r.soon .tx{color:var(--soon);font-weight:600}
.cal-none{margin-top:9px;font-size:12px;color:var(--ink-3)}
.cal-legend{display:flex;flex-wrap:wrap;gap:16px;margin-top:16px;font-size:12.5px;color:var(--ink-3)}
.cal-legend b{font-weight:600}
@media(max-width:640px){.cal-grid{grid-template-columns:repeat(auto-fill,minmax(150px,1fr));gap:22px 16px}}
.colophon{margin-top:44px;font-size:12.5px;color:var(--ink-3)}
@media(max-width:640px){:root{--col:0px}
body{padding:0 18px 90px}
.entry{grid-template-columns:1fr;gap:0}
.when-col{text-align:left;display:flex;align-items:baseline;gap:10px;margin-bottom:8px}
.when-col .date{margin-top:0}
.hrow .d{margin-left:0;width:100%}}
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
    return f"""<article class="entry">{when_col(item)}
<div class="body"><div class="title-line"><span class="t">{esc(item['title'])}</span>{venue}
<span class="k">{esc(item.get('kind',''))}</span><span class="state">{esc(st['label'])}</span></div>
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
            if v.get('cost'):
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


def build_materials(D, nven, narc):
    """무엇으로 지었나. 이론가와 개념과 읽기에서 거꾸로 글을 찾는다.

    항목에 적은 열쇠말을 뒤집어 모은다. 손으로 두 번 적지 않는다.
    """
    thinkers = D.get('thinkers', {})
    readings = D.get('readings', {})

    by_thinker, by_concept, by_reading = {}, {}, {}
    for it, arc in all_items(D):
        u = it.get('uses', {})
        for t in u.get('이론가', []):
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

    out.append(FOOT.replace('{updated}', D['meta']['updated'].replace('-', '.')))
    return ''.join(out)


# ── 지난 일 ─────────────────────────────────────────────────────────────────
def build_archive(D, venue_index, nven, narc):
    out = [HEAD.format(title='지난 일', css=CSS, updated=D['meta']['updated'].replace('-', '.'),
                       h0='', hc='', h1='', h2=' here', h3='', nven=nven, narc=narc)]
    years = {}
    for it in D.get('archive', []):
        y = (it.get('dates', {}).get('decided') or '0000')[:4]
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


def build_calendar(D, venue_index, nven, narc):
    """달력. 날짜는 페이지가 열릴 때 그린다. 그래야 오늘이 늘 가운데 온다."""
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
    # 같은 날 같은 글은 한 번만
    uniq, key_seen = [], set()
    for e in sorted(ev, key=lambda x: (x['d'], x['t'])):
        k = (e['d'], e['k'], e['t'])
        if k not in key_seen:
            key_seen.add(k); uniq.append(e)

    out = [HEAD.format(title='달력', css=CSS, updated=D['meta']['updated'].replace('-', '.'),
                       h0='', hc=' here', h1='', h2='', h3='', nven=nven, narc=narc)]
    out.append("""<div class="sec"><h2>한 해</h2><span class="c">오늘 앞뒤 여섯 달</span></div>
<div class="cal-legend"><span><b>굵은 날</b> 무엇인가 있는 날</span>
<span><b>붉은 밑줄</b> 이레 안 마감</span><span><b>주황 밑줄</b> 한 달 안 마감</span>
<span><b>네모</b> 오늘</span></div>
<div class="cal-grid" id="cal"></div>""")
    out.append('<script>const EV = ' + json.dumps(uniq, ensure_ascii=False) + ';</script>')
    out.append("""<script>
(function () {
  var W = ['일','월','화','수','목','금','토'];
  var today = new Date(); today.setHours(0,0,0,0);
  var byDay = {};
  EV.forEach(function (e) { (byDay[e.d] = byDay[e.d] || []).push(e); });

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
        list.forEach(function (e) { if (e.k === '마감') { var u = urg(e.d).c; if (u === 'now' || (u === 'soon' && worst !== 'now')) worst = u; } });
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
          var u = e.k === '마감' ? urg(e.d).c : '';
          h += '<div class="r ' + u + '"><span class="dd">' + r.day + '</span>'
             + '<span class="tx">' + e.t + ' <span style="color:var(--ink-3)">' + e.k + '</span></span></div>';
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
