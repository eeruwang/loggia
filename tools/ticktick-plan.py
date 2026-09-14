#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ticktick-plan.py — 로지아와 틱틱 사이에 무엇을 옮길지 계산한다.

    python3 tools/ticktick-plan.py --current current.json --gongo gongo.json > plan.json

무엇을 하는가

    로지아 데이터와 공고 KV에서 틱틱에 있어야 할 과제의 목록을 짓고,
    틱틱에서 받아 온 지금의 과제와 견주어 할 일을 적어 낸다.
    스스로는 아무 데도 손대지 않는다. 부르는 쪽이 계획대로 움직인다.

구조

    할 일 목록은 항목이 어버이가 되고 할 일이 하위로 붙는다.
      어버이  제목은 항목 이름. 본문에 `로지아 항목 <아이디>` 한 줄. 태그는 항목의 갈래
      하위    제목은 판의 할 일 글 그대로. 본문에 `로지아 <아이디>.<지문>` 한 줄
    마감 목록은 로지아를 비추기만 한다. 본문에 `로지아 마감 <갈래>:<아이디>` 한 줄.

    **본문의 나머지는 사람의 자리다.** 열쇠 줄만 보고 나머지 메모는 건드리지 않는다.
    열쇠 줄은 첫 줄이 아니어도 된다. 줄마다 훑어 찾는다.

    **갈래는 틱틱이 정한다.** 사람이 어떤 줄을 노트로 바꾸면 그대로 둔다.
    노트는 체크할 수 없고 하위로도 못 들어간다. 틱틱이 막는다.
    그래서 노트가 된 할 일은 어버이 밖에 홀로 서고, 되받기에서 빠진다.

    들어가는 것
      loggia-data.json      fetch.sh 로 받은 것
      --gongo   gongo.json  /gongo?k=<장부토큰> 이 준 것
      --current current.json  틱틱에서 받아 온 지금 상태
        {"todo": [과제...], "due": [과제...]}
        과제는 틱틱이 주는 그대로. id, title, content, dueDate, tags, kind,
        parentId, status, completedTime 을 본다. 완료한 것도 todo 에 함께 담는다

    나오는 것 (JSON)
      create_parent[]  먼저 만든다. 각 항목의 어버이
      create_todo[]    어버이를 만든 뒤에 만든다. parentKey 를 그 어버이의 id 로 갈아 끼운다
      create_due[]     마감 목록에 넣을 것
      update[]         batch_update_tasks 에 넘길 것
      delete[]         {projectId, taskId, why}
      ledger{done,add,edit}  /done /add /edit 에 set 으로 보낼 것
      report[]         사람이 읽을 한 줄들
"""
import json, argparse, hashlib, datetime, sys

TODO_PID = "6aa7ae1d8f084b19082e331e"
DUE_PID = "6aa7ae1f8f081102b5324922"


def fp(t):
    return hashlib.sha1(t.encode('utf-8')).hexdigest()[:8]


def iso(ds):
    return ds + "T00:00:00+0900"


def day(s):
    return s[:10] if s else None


def keyline(content):
    """본문 어딘가에 박아 둔 열쇠 한 줄. 없으면 None.

    사람이 같은 본문에 메모를 적으므로 첫 줄만 보지 않는다. 줄마다 훑는다."""
    if not content:
        return None
    for line in content.split('\n'):
        head = line.strip()
        for mark in ('로지아 마감 ', '로지아 항목 ', '로지아 '):
            if head.startswith(mark):
                rest = head[len(mark):].strip()
                return ('항목:' + rest) if mark == '로지아 항목 ' else rest
    return None


def restamp(content, marker):
    """열쇠 줄만 갈아 끼우고 사람이 적은 나머지는 그대로 둔다."""
    lines = (content or '').split('\n')
    out, hit = [], False
    for line in lines:
        if not hit and line.strip().startswith('로지아 '):
            out.append(marker)
            hit = True
        else:
            out.append(line)
    if not hit:
        out = [marker] + [x for x in out if x.strip()]
    return '\n'.join(out).strip()


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

    items = {}
    want_parent = {}
    want_todo = {}
    want_due = {}
    for s in d.get('sections', []):
        for it in s['items']:
            items[it['id']] = it
            ts = todos_of(it)
            if ts:
                want_parent['항목:' + it['id']] = {'title': it['title'],
                                                 'kind': it.get('kind') or '항목'}
            for x in ts:
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

    plan = {'create_parent': [], 'create_todo': [], 'create_due': [], 'update': [],
            'delete': [], 'ledger': {'done': {}, 'add': {}, 'edit': {}}, 'report': []}

    parent_id = {}
    for t in cur.get('todo', []):
        k = keyline(t.get('content'))
        if k and k.startswith('항목:'):
            parent_id[k] = t['id']

    def mk_todo(k, w):
        t = {'projectId': TODO_PID, 'title': w['t'],
             'content': f"로지아 {k}",
             'parentKey': '항목:' + w['item']}
        pid = parent_id.get('항목:' + w['item'])
        if pid:
            t['parentId'] = pid
        if w.get('due'):
            t.update(dueDate=iso(w['due']), isAllDay=True, timeZone='Asia/Seoul')
        return t

    def mk_due(k, w):
        t = {'projectId': DUE_PID, 'title': w['title'], 'tags': [w['tag']],
             'content': f"로지아 마감 {k}" + (f"\n{w['body']}" if w['body'] else '')}
        if w.get('due'):
            t.update(dueDate=iso(w['due']), isAllDay=True, timeZone='Asia/Seoul')
        return t

    seen = set()
    seen_parent = set()
    for t in cur.get('todo', []):
        k = keyline(t.get('content'))
        note = (t.get('kind') == 'NOTE')
        done = (not note) and (t.get('status') in (2, -1) or t.get('completedTime'))

        if k and k.startswith('항목:'):
            w = want_parent.get(k)
            if not w:
                plan['delete'].append({'projectId': TODO_PID, 'taskId': t['id'],
                                       'why': '할 일이 남지 않은 항목'})
                continue
            seen_parent.add(k)
            if (t.get('title') or '') != w['title'] or (t.get('tags') or []) != [w['kind']]:
                plan['update'].append({'id': t['id'], 'projectId': TODO_PID,
                                       'title': w['title'], 'tags': [w['kind']]})
            if done:
                plan['update'].append({'id': t['id'], 'projectId': TODO_PID, 'status': 0})
                plan['report'].append(f"어버이를 체크했길래 되돌린다 · {w['title']}")
            continue

        if not k:
            iid = None
            for pk, pid in parent_id.items():
                if t.get('parentId') == pid:
                    iid = pk[3:]
            if not iid:
                names = {v['title']: i for i, v in items.items()}
                for x in (t.get('tags') or []):
                    if x in items:
                        iid = x
                    elif x in names:
                        iid = names[x]
            if not iid:
                plan['report'].append(f"어느 항목인지 알 수 없어 그냥 둔다 · {t.get('title','')}")
                continue
            row = {'item': iid, 't': t.get('title', ''), 'at': today}
            if day(t.get('dueDate')):
                row['due'] = day(t['dueDate'])
            plan['ledger']['add'][f"tt-{t['id']}"] = row
            nk = f"{iid}.{fp(row['t'])}"
            plan['update'].append({'id': t['id'], 'projectId': TODO_PID,
                                   'content': restamp(t.get('content'), f"로지아 {nk}")})
            if done:
                plan['ledger']['done'][f"add:tt-{t['id']}"] = {'at': today}
                plan['delete'].append({'projectId': TODO_PID, 'taskId': t['id'],
                                       'why': '적자마자 체크한 것'})
            plan['report'].append(f"틱틱에서 적은 것을 {iid} 로 보낸다 · {row['t']}")
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
        if (t.get('title') or '') != w['t']:
            row = {'item': w['item'], 't': t['title'], 'at': today}
            if day(t.get('dueDate')):
                row['due'] = day(t['dueDate'])
            plan['ledger']['edit'][k] = row
            nk = f"{w['item']}.{fp(t['title'])}"
            plan['update'].append({'id': t['id'], 'projectId': TODO_PID,
                                   'content': restamp(t.get('content'), f"로지아 {nk}")})
            plan['report'].append(f"글을 고쳤다 · {k}")
            continue
        if day(t.get('dueDate')) != w.get('due'):
            row = {'item': w['item'], 't': w['t'], 'at': today}
            if day(t.get('dueDate')):
                row['due'] = day(t['dueDate'])
            plan['ledger']['edit'][k] = row
            plan['report'].append(f"마감을 고쳤다 · {k} → {row.get('due','없음')}")
        if not note and not t.get('parentId'):
            pid = parent_id.get('항목:' + w['item'])
            if pid:
                plan['update'].append({'id': t['id'], 'projectId': TODO_PID,
                                       'parentId': pid})

    for k, w in want_parent.items():
        if k not in seen_parent:
            plan['create_parent'].append({'key': k, 'projectId': TODO_PID,
                                          'title': w['title'], 'tags': [w['kind']],
                                          'content': f"로지아 항목 {k[3:]}"})
    for k, w in want_todo.items():
        if k not in seen:
            plan['create_todo'].append(mk_todo(k, w))

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
