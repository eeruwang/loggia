#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ledger-apply.py — 사이트에서 직접 체크하거나 추가한 것을 데이터에 반영한다.

    LEDGER_TOKEN="..." python3 tools/ledger-apply.py            바뀔 내용만 보여준다
    LEDGER_TOKEN="..." python3 tools/ledger-apply.py -w         데이터에 반영한다
    LEDGER_TOKEN="..." python3 tools/ledger-apply.py --clear    기록을 비운다 (올린 뒤에)

무엇을 하는가

    사이트에서 체크박스를 눌러 끝냈다고 표시한 것과, 오른쪽 아래 「+」로 적어
    넣은 할 일이 워커에 임시로 쌓인다. 그걸 데이터에 옮기는 건 정해진 절차라
    사람이 판단할 게 없다. 그래서 이 도구가 대신 한다.

      /done 의 키는 <항목id>.<할 일 내용의 sha1 앞 8자>
        → 그 항목에서 키가 맞는 할 일을 빼고, 마지막 작업일을 그날로 바꾼다
      /add 는 직접 적어 넣은 할 일
        → 그 항목의 할 일 목록 끝에 넣는다. 날짜가 있으면 같이
      /done 의 키가 add: 로 시작하면 추가하자마자 체크한 것
        → 할 일에 넣지 않고 버린다. 마지막 작업일만 바꾼다
      /edit 는 사이트에서 수정하거나 삭제한 할 일. 키는 처음 글로 만든 것이다
        → 글과 날짜를 바꾼다. del 이 있으면 뺀다
      /seed 는 공고 판에서 담아 둔 것
        → 채용은 `later` 칸에 새 항목으로 심는다. 같은 id 가 있으면 건너뛴다
        → `venue` 가 적혀 있으면 그 낼 곳의 마감만 갈아 끼운다
        → 다만 지금 원고가 가고 있는 낼 곳이면 덮지 않고 알리기만 한다
        → 갈래가 지면인데 `venue` 가 없으면 낼 곳을 새로 만들 자리라 알려만 준다

    보통은 워커가 10분마다 알아서 한다. 이 도구는 워커가 못 할 때와,
    무엇이 쌓였는지 눈으로 보고 싶을 때 쓴다.

    판단이 필요한 건 하나뿐이다. 할 일이 다 없어진 항목에 다음에 뭘 할지
    정하는 것. 그건 여기서 알려만 주고 사람이 정한다.

기록을 비우는 시점

    **사이트에 올린 다음에 비운다.** 올리기 전에 비우면 그 사이에 사이트에서
    체크한 게 사라진다. -w 로 반영할 때 옮긴 키를 `.ledger-applied` 에 적어
    두므로, 올린 다음 --clear 만 부르면 된다.
"""
import json, os, sys, hashlib, datetime, argparse
import urllib.request, urllib.error, urllib.parse

DEFAULT = 'loggia-data.json'
MARK = '.ledger-applied'
SLOTS = ('done', 'add', 'edit', 'seed')


def die(msg):
    print(msg, file=sys.stderr)
    sys.exit(1)


def get(url):
    req = urllib.request.Request(url, headers={'user-agent': 'loggia-tools/1.0'})
    try:
        with urllib.request.urlopen(req, timeout=20) as r:
            return json.loads(r.read().decode('utf-8'))
    except urllib.error.HTTPError as e:
        die(f'기록을 읽지 못했습니다 ({e.code}). LEDGER_TOKEN 을 확인해 주세요.')
    except Exception as e:
        die(f'서버에 연결하지 못했습니다. {e}')


def post(url, body):
    req = urllib.request.Request(url, data=json.dumps(body).encode('utf-8'),
                                 headers={'content-type': 'application/json',
                                          'user-agent': 'loggia-tools/1.0'}, method='POST')
    try:
        with urllib.request.urlopen(req, timeout=20) as r:
            return json.loads(r.read().decode('utf-8'))
    except Exception as e:
        die(f'기록을 비우지 못했습니다. {e}')


def todos_of(item):
    st = item.get('steps') or ([item['next']] if item.get('next') else [])
    return [{'t': x} if isinstance(x, str) else dict(x) for x in st]


def put_todos(item, ss):
    item['steps'] = [s['t'] if not s.get('due') else {'t': s['t'], 'due': s['due']} for s in ss]
    if not item['steps']:
        del item['steps']
    item.pop('next', None)


def fingerprint(text):
    return hashlib.sha1(text.encode('utf-8')).hexdigest()[:8]


def find(d, iid):
    for s in d.get('sections', []):
        for it in s['items']:
            if it['id'] == iid:
                return it
    for it in d.get('archive', []):
        if it['id'] == iid:
            return it
    return None


def touch(item, when):
    """마지막 작업일은 뒤로 되돌리지 않는다. 이미 더 나중이면 그대로 둔다."""
    dt = item.setdefault('dates', {})
    if not dt.get('touched') or dt['touched'] < when:
        dt['touched'] = when


def main():
    p = argparse.ArgumentParser(add_help=False)
    p.add_argument('-f', '--file', default=DEFAULT)
    p.add_argument('-w', '--write', action='store_true')
    p.add_argument('--clear', action='store_true')
    p.add_argument('--site')
    p.add_argument('-h', '--help', action='store_true')
    args = p.parse_args()
    if args.help:
        print(__doc__)
        return

    tok = os.environ.get('LEDGER_TOKEN')
    if not tok:
        die('LEDGER_TOKEN 이 필요합니다. 드롭박스의 board_keys.txt 에 있습니다.')

    site = args.site
    if not site and os.path.exists(args.file):
        site = (json.load(open(args.file, encoding='utf-8')).get('meta') or {}).get('site')
    site = (site or 'https://loggia.moonilsun.com/').rstrip('/')
    q = '?k=' + urllib.parse.quote(tok)

    # ── 비우기. 사이트에 올린 다음에 부른다 ───────────────────────────────
    if args.clear:
        if not os.path.exists(MARK):
            die(f'{MARK} 가 없습니다. 먼저 -w 로 반영해 주세요.')
        mark = json.load(open(MARK, encoding='utf-8'))
        for slot in SLOTS:
            keys = mark.get(slot) or []
            if keys:
                left = post(f'{site}/{slot}{q}', {'del': keys})
                print(f'/{slot} 에서 {len(keys)}개를 지웠습니다. 남은 것 {len(left)}개')
        os.remove(MARK)
        print('기록을 비웠습니다.')
        return

    if not os.path.exists(args.file):
        die(f'데이터 파일이 없습니다: {args.file}')
    d = json.load(open(args.file, encoding='utf-8'))

    done = get(f'{site}/done{q}')
    add = get(f'{site}/add{q}')
    edit = get(f'{site}/edit{q}')
    seed = get(f'{site}/seed{q}')
    if not done and not add and not edit and not seed:
        print('사이트에서 체크하거나 추가한 것이 없습니다.')
        return

    plan, touched_ids = [], {}
    clear_done, clear_add, clear_edit, clear_seed = [], [], [], []
    used_add = set()
    seeds, venue_seeds = [], []

    # ── 공고 판에서 담아 둔 것 ────────────────────────────────────────────
    venue_index = {v['id']: v for g in d.get('venueGroups', []) for v in g.get('venues', [])}

    def going_now(vid):
        """지금 원고가 가고 있는 낼 곳인가. 판의 낼 곳 화면과 같은 셈이다."""
        for sec in d.get('sections', []):
            if sec['id'] not in ('now', 'waiting'):
                continue
            for it in sec['items']:
                if it.get('venue') != vid:
                    continue
                tone = (d.get('statuses', {}).get(it.get('status'), {}) or {}).get('tone')
                if tone in ('stop', 'done'):
                    continue
                return it['title']
        return None
    for sk, row in (seed or {}).items():
        clear_seed.append(sk)
        iid = row.get('id') or sk
        vid = row.get('venue')

        # 낼 곳이 적혀 있으면 그곳의 마감만 갈아 끼운다. 마감은 한 벌만 둔다
        if vid:
            v = venue_index.get(vid)
            if v is None:
                plan.append(('못 찾음', vid, row.get('title', ''), '그런 낼 곳이 없어 그냥 버립니다'))
                continue
            new = row.get('deadline') or ''
            if not new:
                plan.append(('건너뜀', vid, row.get('title', ''), '마감이 비어 있습니다'))
                continue
            if v.get('deadline') == new:
                plan.append(('그대로', vid, v['name'], f'이미 {new} 입니다'))
                continue
            # 원고가 가고 있는 곳의 마감은 스스로 건 시계인 때가 있다.
            # 저널이 적은 날짜로 덮으면 그 시계가 지워진다. 알리고 사람이 정한다.
            going = going_now(vid)
            if going:
                plan.append(('물어볼 것', vid, v['name'],
                             f'{going} 이(가) 가고 있는 곳입니다. '
                             f'{v.get("deadline") or "없음"} 을 {new} 로 바꿀지 물어보세요'))
                continue
            venue_seeds.append((vid, new))
            plan.append(('낼 곳 마감', vid, v['name'],
                         f'{v.get("deadline") or "없음"} → {new}'))
            continue

        if '지면' in str(row.get('strand') or ''):
            plan.append(('물어볼 것', iid, row.get('title', ''),
                         '낼 곳에 없는 지면입니다. 새 낼 곳으로 만들지 사용자에게 물어보세요'))
            continue

        if find(d, iid) is not None:
            plan.append(('있음', iid, row.get('title', ''), '같은 id 가 이미 있어 심지 않습니다'))
            continue
        seeds.append((iid, row))
        plan.append(('심기', iid, row.get('title', ''),
                     ('마감 ' + row['deadline']) if row.get('deadline') else '마감 모름'))

    # ── 추가하자마자 체크한 것. 할 일에 넣지 않고 버린다 ──────────────────
    for k, row in done.items():
        if not k.startswith('add:'):
            continue
        ak = k[4:]
        a = add.get(ak)
        iid = (a or {}).get('item')
        when = row.get('at') or (a or {}).get('at') or datetime.date.today().isoformat()
        txt = (a or {}).get('t') or row.get('s') or ak
        used_add.add(ak)
        clear_done.append(k)
        if ak in add:
            clear_add.append(ak)
        it = find(d, iid) if iid else None
        if it is None:
            plan.append(('제외', iid or '?', txt, '추가하자마자 체크한 것인데 항목을 못 찾아 그냥 버립니다'))
            continue
        touched_ids[iid] = max(touched_ids.get(iid, ''), when)
        plan.append(('제외', iid, txt, '추가하자마자 체크해서 할 일에 넣지 않습니다'))

    # ── 체크해서 끝냈다고 표시한 할 일 ────────────────────────────────────
    for k, row in done.items():
        if k.startswith('add:'):
            continue
        clear_done.append(k)
        if '.' not in k:
            plan.append(('알 수 없음', '?', k, '키 형식이 이상해서 그냥 버립니다'))
            continue
        iid, fp = k.rsplit('.', 1)
        when = row.get('at') or datetime.date.today().isoformat()
        it = find(d, iid)
        if it is None:
            plan.append(('못 찾음', iid, row.get('s', ''), '그런 항목이 없어서 그냥 버립니다'))
            continue
        touched_ids[iid] = max(touched_ids.get(iid, ''), when)
        ss = todos_of(it)
        hit = [i for i, s in enumerate(ss) if fingerprint(s['t']) == fp]
        if not hit:
            plan.append(('건너뜀', iid, row.get('s', ''), '데이터에 이미 없는 할 일이라 날짜만 바꿉니다'))
            continue
        plan.append(('완료', iid, ss[hit[0]]['t'], ''))

    # ── 수정하거나 삭제한 할 일 ──────────────────────────────────────────
    # 키는 처음 글로 만든 것이라 원본에서 그대로 찾힌다.
    # 끝냈다고 표시한 것을 먼저 뺐으므로, 이미 없어진 것은 그냥 넘어간다.
    for k, e in edit.items():
        clear_edit.append(k)
        # 일하는 기간은 할 일이 아니라 항목에 붙는다. 키가 `item:<아이디>` 다.
        if k.startswith('item:'):
            iid = e.get('item') or k[5:]
            when = e.get('at') or datetime.date.today().isoformat()
            it = find(d, iid)
            if it is None:
                plan.append(('못 찾음', iid, e.get('품', ''), '그런 항목이 없어서 그냥 버립니다'))
                continue
            touched_ids[iid] = max(touched_ids.get(iid, ''), when)
            lab = (d.get('efforts', {}).get(e.get('품'), {}) or {}).get('label', '안 정함')
            plan.append(('기간', iid, lab, ''))
            continue
        if '.' not in k:
            plan.append(('알 수 없음', '?', k, '키 형식이 이상해서 그냥 버립니다'))
            continue
        iid = e.get('item') or k.rsplit('.', 1)[0]
        fp = k.rsplit('.', 1)[1]
        when = e.get('at') or datetime.date.today().isoformat()
        it = find(d, iid)
        if it is None:
            plan.append(('못 찾음', iid, e.get('t', ''), '그런 항목이 없어서 그냥 버립니다'))
            continue
        touched_ids[iid] = max(touched_ids.get(iid, ''), when)
        ss = todos_of(it)
        if not any(fingerprint(x['t']) == fp for x in ss):
            plan.append(('건너뜀', iid, e.get('t', ''), '데이터에 이미 없는 할 일이라 날짜만 바꿉니다'))
            continue
        plan.append(('삭제' if e.get('del') else '수정', iid, e.get('t', ''),
                     f'{e["due"]}까지' if e.get('due') else ''))

    # ── 사이트에서 직접 적어 넣은 할 일 ───────────────────────────────────
    for ak, a in add.items():
        if ak in used_add:
            continue
        clear_add.append(ak)
        iid = a.get('item')
        it = find(d, iid) if iid else None
        when = a.get('at') or datetime.date.today().isoformat()
        if it is None:
            plan.append(('못 찾음', iid or '?', a.get('t', ''), '그런 항목이 없어서 그냥 버립니다'))
            continue
        touched_ids[iid] = max(touched_ids.get(iid, ''), when)
        plan.append(('추가', iid, a.get('t', ''),
                     f'{a["due"]}까지' if a.get('due') else ''))

    # ── 바뀔 내용 보여주기 ────────────────────────────────────────────────
    W = max((len(x[1]) for x in plan), default=8)
    for kind, iid, txt, note in plan:
        print(f'  {kind:<7} {iid:<{W}}  {txt}' + (f'   ({note})' if note else ''))
    if touched_ids:
        print('  마지막 작업일  '
              + ', '.join(f'{i} → {w}' for i, w in sorted(touched_ids.items())))

    if not args.write:
        print('\n아직 반영하지 않았습니다. 반영하려면 -w 를 붙여 주세요.')
        return

    # ── 반영하기 ──────────────────────────────────────────────────────────
    for k, row in done.items():
        if k.startswith('add:') or '.' not in k:
            continue
        iid, fp = k.rsplit('.', 1)
        it = find(d, iid)
        if it is None:
            continue
        ss = todos_of(it)
        keep = [s for s in ss if fingerprint(s['t']) != fp]
        if len(keep) != len(ss):
            put_todos(it, keep)
    for k, e in edit.items():
        if k.startswith('item:'):
            it = find(d, e.get('item') or k[5:])
            if it is None:
                continue
            if e.get('품'):
                it['품'] = e['품']
            else:
                it.pop('품', None)
            continue
        if '.' not in k:
            continue
        iid = e.get('item') or k.rsplit('.', 1)[0]
        fp = k.rsplit('.', 1)[1]
        it = find(d, iid)
        if it is None:
            continue
        out, hit = [], False
        for x in todos_of(it):
            if not hit and fingerprint(x['t']) == fp:
                hit = True
                if e.get('del'):
                    continue
                row = {'t': e.get('t', x['t'])}
                if e.get('due'):
                    row['due'] = e['due']
                out.append(row)
                continue
            out.append(x)
        if hit:
            put_todos(it, out)
    for ak, a in add.items():
        if ak in used_add:
            continue
        it = find(d, a.get('item'))
        if it is None:
            continue
        ss = todos_of(it)
        row = {'t': a.get('t', '')}
        if a.get('due'):
            row['due'] = a['due']
        ss.append(row)
        put_todos(it, ss)
    for vid, new in venue_seeds:
        v = venue_index.get(vid)
        if v is not None:
            v['deadline'] = new

    later = next((x for x in d.get('sections', []) if x['id'] == 'later'), None)
    for iid, row in seeds:
        if later is None:
            break
        dates = {'touched': row.get('at') or datetime.date.today().isoformat()}
        if row.get('deadline'):
            dates['deadline'] = row['deadline']
        it = {'id': iid, 'title': row.get('title', '') or iid,
              'kind': '강의직 지원' if row.get('strand') == '강의' else '연구직 지원',
              'status': '미착수', 'dates': dates,
              'steps': ['공고문 읽고 지원 여부 정하기']}
        if row.get('note'):
            it['note'] = row['note']
        if row.get('url'):
            it['links'] = [{'kind': 'web', 'label': '공고', 'url': row['url']}]
        later['items'].append(it)

    for iid, when in touched_ids.items():
        it = find(d, iid)
        if it is not None:
            touch(it, when)

    d.setdefault('meta', {})['updated'] = datetime.date.today().isoformat()
    with open(args.file, 'w', encoding='utf-8') as f:
        f.write(json.dumps(d, ensure_ascii=False, indent=1))
    print(f'\n반영했습니다  {args.file}')

    empty = [i for i in touched_ids if find(d, i) is not None and not todos_of(find(d, i))]
    if empty:
        print('  ! 할 일이 다 없어진 항목: ' + ', '.join(empty)
              + '\n    다음에 뭘 할지 사용자에게 물어봐야 합니다.')

    with open(MARK, 'w', encoding='utf-8') as f:
        json.dump({'done': clear_done, 'add': clear_add, 'edit': clear_edit,
                   'seed': clear_seed}, f, ensure_ascii=False)
    print(f'  옮긴 키를 {MARK} 에 적어 두었습니다.')
    print('  사이트에 올린 다음 --clear 로 기록을 비워 주세요.')


if __name__ == '__main__':
    main()
