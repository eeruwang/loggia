#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ledger-apply.py — 판에서 손으로 하신 것을 데이터로 옮긴다.

    LEDGER_TOKEN="..." python3 tools/ledger-apply.py            무엇이 바뀔지 보여만 준다
    LEDGER_TOKEN="..." python3 tools/ledger-apply.py -w         데이터에 넣는다
    LEDGER_TOKEN="..." python3 tools/ledger-apply.py --clear    장부를 비운다 (올린 뒤에)

무엇을 하는가

    판에서 네모를 눌러 끝냈다고 표시하신 것과, 오른쪽 아래 「+」로 적어 넣으신
    할 일이 워커의 장부에 쌓인다. 그것을 데이터로 옮기는 일은 정해진 절차라
    사람이 판단할 여지가 없다. 그래서 이 도구가 대신 한다.

      /done 의 열쇠는 <갈래id>.<걸음글의 지문 여덟 자>
        → 그 갈래에서 지문이 맞는 걸음을 빼고, 손댄 날을 그날로 고친다
      /add 는 손으로 적어 넣으신 할 일
        → 그 갈래의 걸음 끝에 넣는다. 날짜가 있으면 함께
      /done 의 열쇠가 add: 로 시작하면 적어 넣자마자 끝내신 것
        → 걸음에 넣지 않고 버린다. 손댄 날만 고친다

    판단이 남는 자리는 하나뿐이다. 걸음이 다 없어진 갈래에 다음에 무엇을
    할지 정하는 것. 그것은 여기서 알려만 주고 사람이 정한다.

비우는 때

    **판을 올린 뒤에 비운다.** 올리기 전에 비우면 그 사이에 판을 열어
    네모를 누르신 것이 사라진다. -w 로 넣을 때 옮긴 열쇠를 `.ledger-applied`
    에 적어 두므로, 올린 다음 --clear 만 부르면 된다.
"""
import json, os, sys, hashlib, datetime, argparse
import urllib.request, urllib.error, urllib.parse

DEFAULT = 'loggia-data.json'
MARK = '.ledger-applied'


def die(msg):
    print(msg, file=sys.stderr)
    sys.exit(1)


def get(url):
    try:
        with urllib.request.urlopen(url, timeout=20) as r:
            return json.loads(r.read().decode('utf-8'))
    except urllib.error.HTTPError as e:
        die(f'장부를 읽지 못했습니다 ({e.code}). LEDGER_TOKEN 을 확인하세요.')
    except Exception as e:
        die(f'장부에 닿지 못했습니다. {e}')


def post(url, body):
    req = urllib.request.Request(url, data=json.dumps(body).encode('utf-8'),
                                 headers={'content-type': 'application/json'}, method='POST')
    try:
        with urllib.request.urlopen(req, timeout=20) as r:
            return json.loads(r.read().decode('utf-8'))
    except Exception as e:
        die(f'장부를 비우지 못했습니다. {e}')


def steps_of(item):
    st = item.get('steps') or ([item['next']] if item.get('next') else [])
    return [{'t': x} if isinstance(x, str) else dict(x) for x in st]


def put_steps(item, ss):
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
    """손댄 날은 뒤로 물리지 않는다. 이미 더 나중이면 그대로 둔다."""
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
        die('LEDGER_TOKEN 이 없습니다. 드롭박스의 board_keys.txt 에 있습니다.')

    site = args.site
    if not site and os.path.exists(args.file):
        site = (json.load(open(args.file, encoding='utf-8')).get('meta') or {}).get('site')
    site = (site or 'https://loggia.moonilsun.com/').rstrip('/')
    q = '?k=' + urllib.parse.quote(tok)

    # ── 비우기. 올린 뒤에 부른다 ──────────────────────────────────────────
    if args.clear:
        if not os.path.exists(MARK):
            die(f'{MARK} 가 없습니다. 먼저 -w 로 넣으세요.')
        mark = json.load(open(MARK, encoding='utf-8'))
        for slot in ('done', 'add'):
            keys = mark.get(slot) or []
            if keys:
                left = post(f'{site}/{slot}{q}', {'del': keys})
                print(f'/{slot} 에서 {len(keys)}개 지움. 남은 것 {len(left)}개')
        os.remove(MARK)
        print('장부를 비웠습니다.')
        return

    if not os.path.exists(args.file):
        die(f'데이터 파일이 없습니다: {args.file}')
    d = json.load(open(args.file, encoding='utf-8'))

    done = get(f'{site}/done{q}')
    add = get(f'{site}/add{q}')
    if not done and not add:
        print('장부가 비어 있습니다. 옮길 것이 없습니다.')
        return

    plan, touched_ids = [], {}
    clear_done, clear_add = [], []
    used_add = set()

    # ── 적어 넣자마자 끝내신 것. 걸음에 넣지 않고 버린다 ──────────────────
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
            plan.append(('버림', iid or '?', txt, '적자마자 끝내신 것. 갈래를 못 찾아 그냥 버립니다'))
            continue
        touched_ids[iid] = max(touched_ids.get(iid, ''), when)
        plan.append(('버림', iid, txt, '적자마자 끝내신 것. 걸음에 넣지 않습니다'))

    # ── 끝냈다고 표시하신 걸음 ────────────────────────────────────────────
    for k, row in done.items():
        if k.startswith('add:'):
            continue
        clear_done.append(k)
        if '.' not in k:
            plan.append(('모름', '?', k, '열쇠 꼴이 낯섭니다. 그냥 버립니다'))
            continue
        iid, fp = k.rsplit('.', 1)
        when = row.get('at') or datetime.date.today().isoformat()
        it = find(d, iid)
        if it is None:
            plan.append(('없음', iid, row.get('s', ''), '그런 갈래가 없습니다. 그냥 버립니다'))
            continue
        touched_ids[iid] = max(touched_ids.get(iid, ''), when)
        ss = steps_of(it)
        hit = [i for i, s in enumerate(ss) if fingerprint(s['t']) == fp]
        if not hit:
            plan.append(('이미없음', iid, row.get('s', ''), '데이터에 그 걸음이 없습니다. 손댄 날만 고칩니다'))
            continue
        plan.append(('걸음뺌', iid, ss[hit[0]]['t'], ''))

    # ── 손으로 적어 넣으신 할 일 ──────────────────────────────────────────
    for ak, a in add.items():
        if ak in used_add:
            continue
        clear_add.append(ak)
        iid = a.get('item')
        it = find(d, iid) if iid else None
        when = a.get('at') or datetime.date.today().isoformat()
        if it is None:
            plan.append(('없음', iid or '?', a.get('t', ''), '그런 갈래가 없습니다. 그냥 버립니다'))
            continue
        touched_ids[iid] = max(touched_ids.get(iid, ''), when)
        plan.append(('걸음더함', iid, a.get('t', ''),
                     f'마감 {a["due"]}' if a.get('due') else ''))

    # ── 보여 주기 ─────────────────────────────────────────────────────────
    W = max((len(x[1]) for x in plan), default=8)
    for kind, iid, txt, note in plan:
        print(f'  {kind:<8} {iid:<{W}}  {txt}' + (f'   ({note})' if note else ''))
    print(f'  손댄 날    ' + ', '.join(f'{i} → {w}' for i, w in sorted(touched_ids.items())))

    if not args.write:
        print('\n아직 안 넣었습니다. 넣으려면 -w 를 붙이세요.')
        return

    # ── 넣기 ──────────────────────────────────────────────────────────────
    for k, row in done.items():
        if k.startswith('add:') or '.' not in k:
            continue
        iid, fp = k.rsplit('.', 1)
        it = find(d, iid)
        if it is None:
            continue
        ss = steps_of(it)
        keep = [s for s in ss if fingerprint(s['t']) != fp]
        if len(keep) != len(ss):
            put_steps(it, keep)
    for ak, a in add.items():
        if ak in used_add:
            continue
        it = find(d, a.get('item'))
        if it is None:
            continue
        ss = steps_of(it)
        row = {'t': a.get('t', '')}
        if a.get('due'):
            row['due'] = a['due']
        ss.append(row)
        put_steps(it, ss)
    for iid, when in touched_ids.items():
        it = find(d, iid)
        if it is not None:
            touch(it, when)

    d.setdefault('meta', {})['updated'] = datetime.date.today().isoformat()
    with open(args.file, 'w', encoding='utf-8') as f:
        f.write(json.dumps(d, ensure_ascii=False, indent=1))
    print(f'\n넣었습니다  {args.file}')

    empty = [i for i in touched_ids if find(d, i) is not None and not steps_of(find(d, i))]
    if empty:
        print('  ! 걸음이 없어진 갈래: ' + ', '.join(empty)
              + '\n    다음에 무엇을 할지 사용자에게 물어야 합니다.')

    with open(MARK, 'w', encoding='utf-8') as f:
        json.dump({'done': clear_done, 'add': clear_add}, f, ensure_ascii=False)
    print(f'  옮긴 열쇠를 {MARK} 에 적어 두었습니다.')
    print('  판을 올린 뒤에 --clear 로 장부를 비우세요.')


if __name__ == '__main__':
    main()
