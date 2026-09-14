#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ticktick-plan.py — 로지아와 틱틱 사이에 무엇을 옮길지 계산한다.

    python3 tools/ticktick-plan.py --current current.json --gongo gongo.json > plan.json

무엇을 하는가

    로지아 데이터와 공고 KV에서 틱틱에 있어야 할 과제의 목록을 짓고,
    틱틱에서 받아 온 지금의 과제와 견주어 할 일을 적어 낸다.
    스스로는 아무 데도 손대지 않는다. 부르는 쪽이 계획대로 움직인다.

    들어가는 것
      loggia-data.json      fetch.sh 로 받은 것
      --gongo   gongo.json  /gongo?k=<장부토큰> 이 준 것
      --current current.json  틱틱에서 받아 온 지금 상태
        {"todo": [과제...], "due": [과제...]}
        과제는 틱틱이 주는 그대로. id, title, content, dueDate, tags,
        status, completedTime 만 본다. 완료한 것도 todo 에 함께 담는다

    나오는 것 (JSON)
      create_todo[]  batch_add_tasks 에 그대로 넘길 것
      create_due[]   같음
      update[]       batch_update_tasks 에 넘길 것. id 와 projectId 가 들어 있다
      delete[]       {projectId, taskId, why}
      ledger{done,add,edit}  /done /add /edit 에 set 으로 보낼 것
      report[]       사람이 읽을 한 줄들

규칙

    할 일 목록은 두 쪽으로 오간다. 마감 목록은 로지아를 비추기만 한다.
    마감 과제는 체크하지 않는다. 날이 지나면 다음 회차에 저절로 빠진다.
    틱틱에서 새로 적은 할 일은 항목 아이디를 태그로 달아야 로지아로 간다.
"""
import json, argparse, hashlib, datetime, sys

TODO_PID = "6aa7ae1d8f084b19082e331e"
DUE_PID = "6aa7ae1f8f081102b5324922"


def fp(t):
    return hashlib.sha1(t.encode('utf-8')).hexdigest()[:8]


def iso(ds):
    return ds + "T00:00:00+0900"


def day(s):
    """틱틱이 준 날짜에서 앞 열 글자만. 없으면 None"""
    return s[:10] if s else None


def keyline(content):
    """본문 첫 줄에 박아 둔 열쇠. 없으면 None"""
    if not content:
        return None
    head = content.strip().split('\n')[0].strip()
    if head.startswith('로지아 마감 '):
        return head[7:].strip()
    if head.startswith('로지아 '):
        return head[4:].strip()
    return None


def todos_of(item):
    st = item.get('steps') or ([item['next']] if item.get('next') else [])
    return [{'t': x} if isinstance(x, str) else dict(x) for x in st]


def main():
    p = argparse.ArgumentParser(add_help=False)
    p.add_argument('-f', '--file', default='loggia-data.json')
    p.add_argument('--gongo')
    p.add_argument('--current', required=True)
    p.add_argument('--today', default=datetime.date.today().isoformat())
    p.add_argument('-h', '--help', action='store_true')
    a = p.parse_args()
    if a.help:
        print(__doc__)
        return

    d = json.load(open(a.file, encoding='utf-8'))
    cur = json.load(open(a.current, encoding='utf-8'))
    gongo = json.load(open(a.gongo, encoding='utf-8')) if a.gongo else {}
    today = a.today

    # ── 로지아가 바라는 모습 ────────────────────────────────────────────────
    want_todo = {}                      # key -> {t, due, item, title}
    want_due = {}                       # key -> 과제
    for s in d.get('sections', []):
        for it in s['items']:
            for x in todos_of(it):
                k = f"{it['id']}.{fp(x['t'])}"
                want_todo[k] = {'t': x['t'], 'due': x.get('due'),
                                'item': it['id'], 'title': it['title']}
            dl = (it.get('dates') or {}).get('deadline')
            if dl and dl >= today:
                want_due[f"item:{it['id']}"] = {
                    'title': f"마감 {it['title']}", 'due': dl, 'tag': '항목', 'body': ''}
    vens = {}
    for g in d.get('venueGroups', []):
        for v in g['venues']:
            vens[v['id']] = v
            if v.get('deadline') and v['deadline'] >= today:
                want_due[f"venue:{v['id']}"] = {
                    'title': f"낼 곳 마감 {v['name']}", 'due': v['deadline'],
                    'tag': '낼곳', 'body': v.get('url', '')}
    for r in d.get('repeats', []):
        v = vens.get(r.get('venue'), {})
        want_due[f"repeat:{r.get('venue','')}"] = {
            'title': f"{r['label']} {v.get('name', r.get('venue',''))}",
            'due': None, 'tag': '해마다', 'body': r.get('note', '')}
    for k, v in gongo.items():
        if v.get('deadline') and v['deadline'] >= today:
            want_due[f"gongo:{k}"] = {
                'title': f"공고 {v.get('title','')}"[:120], 'due': v['deadline'],
                'tag': '공고', 'body': v.get('url', '')}

    plan = {'create_todo': [], 'create_due': [], 'update': [], 'delete': [],
            'ledger': {'done': {}, 'add': {}, 'edit': {}}, 'report': []}

    def mk_todo(k, w):
        t = {'projectId': TODO_PID, 'title': w['t'],
             'content': f"로지아 {k}\n항목 {w['title']}", 'tags': [w['item']]}
        if w.get('due'):
            t.update(dueDate=iso(w['due']), isAllDay=True, timeZone='Asia/Seoul')
        return t

    def mk_due(k, w):
        t = {'projectId': DUE_PID, 'title': w['title'], 'tags': [w['tag']],
             'content': f"로지아 마감 {k}" + (f"\n{w['body']}" if w['body'] else '')}
        if w.get('due'):
            t.update(dueDate=iso(w['due']), isAllDay=True, timeZone='Asia/Seoul')
        return t

    # ── 할 일. 두 쪽으로 오간다 ─────────────────────────────────────────────
    seen = set()
    for t in cur.get('todo', []):
        k = keyline(t.get('content'))
        done = t.get('status') in (2, -1) or t.get('completedTime')
        if not k:
            # 틱틱에서 새로 적은 것. 태그가 항목 아이디면 로지아로 보낸다
            items = {i['id'] for s in d.get('sections', []) for i in s['items']}
            tag = next((x for x in (t.get('tags') or []) if x in items), None)
            if not tag:
                plan['report'].append(f"항목 태그가 없어 그냥 둔다 · {t.get('title','')}")
                continue
            row = {'item': tag, 't': t.get('title', ''), 'at': today}
            if day(t.get('dueDate')):
                row['due'] = day(t['dueDate'])
            plan['ledger']['add'][f"tt-{t['id']}"] = row
            nk = f"{tag}.{fp(row['t'])}"
            title = next(i['title'] for s in d['sections'] for i in s['items'] if i['id'] == tag)
            plan['update'].append({'id': t['id'], 'projectId': TODO_PID,
                                   'content': f"로지아 {nk}\n항목 {title}"})
            if done:
                plan['ledger']['done'][f"add:tt-{t['id']}"] = {'at': today}
                plan['delete'].append({'projectId': TODO_PID, 'taskId': t['id'],
                                       'why': '적자마자 체크한 것'})
            plan['report'].append(f"틱틱에서 적은 것을 {tag} 로 보낸다 · {row['t']}")
            continue
        seen.add(k)
        if done:
            plan['ledger']['done'][k] = {'at': day(t.get('completedTime')) or today}
            plan['delete'].append({'projectId': TODO_PID, 'taskId': t['id'],
                                   'why': '체크한 것. 로지아에서 빠진다'})
            plan['report'].append(f"체크 · {k}")
            continue
        w = want_todo.get(k)
        if not w:
            plan['delete'].append({'projectId': TODO_PID, 'taskId': t['id'],
                                   'why': '로지아에 없는 할 일'})
            continue
        # 글을 고쳤으면 열쇠가 어긋난다. 제목이 곧 열쇠이므로 제목으로 가린다
        if (t.get('title') or '') != w['t']:
            row = {'item': w['item'], 't': t['title'], 'at': today}
            if day(t.get('dueDate')):
                row['due'] = day(t['dueDate'])
            plan['ledger']['edit'][k] = row
            nk = f"{w['item']}.{fp(t['title'])}"
            plan['update'].append({'id': t['id'], 'projectId': TODO_PID,
                                   'content': f"로지아 {nk}\n항목 {w['title']}"})
            plan['report'].append(f"글을 고쳤다 · {k}")
            continue
        if day(t.get('dueDate')) != w.get('due'):
            row = {'item': w['item'], 't': w['t'], 'at': today}
            if day(t.get('dueDate')):
                row['due'] = day(t['dueDate'])
            plan['ledger']['edit'][k] = row
            plan['report'].append(f"마감을 고쳤다 · {k} → {row.get('due','없음')}")
    for k, w in want_todo.items():
        if k not in seen:
            plan['create_todo'].append(mk_todo(k, w))

    # ── 마감. 비추기만 한다 ────────────────────────────────────────────────
    seen = set()
    for t in cur.get('due', []):
        k = keyline(t.get('content'))
        if not k:
            plan['report'].append(f"마감 목록에 손으로 적은 것 · {t.get('title','')}")
            continue
        w = want_due.get(k)
        if not w:
            plan['delete'].append({'projectId': DUE_PID, 'taskId': t['id'],
                                   'why': '지났거나 로지아에서 빠진 마감'})
            continue
        seen.add(k)
        if (t.get('title') or '') != w['title'] or day(t.get('dueDate')) != w.get('due'):
            u = {'id': t['id'], 'projectId': DUE_PID, 'title': w['title']}
            if w.get('due'):
                u.update(dueDate=iso(w['due']), isAllDay=True, timeZone='Asia/Seoul')
            plan['update'].append(u)
            plan['report'].append(f"마감이 바뀌었다 · {k}")
    for k, w in want_due.items():
        if k not in seen:
            plan['create_due'].append(mk_due(k, w))

    json.dump(plan, sys.stdout, ensure_ascii=False, indent=1)
    print()


if __name__ == '__main__':
    main()
