#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
lg.py — 데이터의 한 자리만 집어서 고친다.

    python3 tools/lg.py <시킬 일> [...]

왜 있는가

    갱신할 때마다 파일을 열고 갈래를 찾고 값을 바꾸고 다시 저장하는 뻔한
    뼈대를 처음부터 다시 쓰곤 했다. 뼈대는 늘 같고 다른 것은 무엇을 바꾸느냐
    하나뿐이다. 그 뼈대를 여기 넣어 두었다.

    그리고 고치기 전에 지금 상태를 봐야 하는데, 그러자고 데이터 덩이를
    통째로 꺼내 보면 값이 든다. `show` 는 그 갈래만 간추려 낸다.

보는 일

    lg.py show                     모든 갈래를 한 줄씩
    lg.py show glasgow             그 갈래 하나를 자세히
    lg.py steps glasgow            걸음만
    lg.py venues                   낼 곳을 한 줄씩
    lg.py venue mirac              낼 곳 하나

고치는 일  (아무것도 안 붙이면 무엇이 바뀌는지만 보여주고 멈춘다. 넣으려면 -w)

    lg.py touch glasgow                            손댄 날을 오늘로
    lg.py set glasgow status 제출                   상태를 바꾼다
    lg.py set glasgow deadline 2026-08-05          마감. sent decided expected 도 같다
    lg.py set glasgow 품 반나절
    lg.py set glasgow note "..."
    lg.py clear glasgow deadline                   그 자리를 지운다
    lg.py step-done glasgow "추천인"                걸음 하나를 뺀다. 글 일부로 찾는다
    lg.py step-add glasgow "면접 준비" --due 2026-08-20
    lg.py step-first glasgow "소리 내어"            그 걸음을 맨 앞으로
    lg.py move glasgow waiting                     칸을 옮긴다. now waiting later
    lg.py archive glasgow                          지난 일로 보낸다
    lg.py venue-set mirac deadline 2026-09-30      낼 곳의 자리를 고친다

    -w  실제로 넣는다. 안 붙이면 보여주기만 한다
    -d  오늘이 아닌 날로 적는다.  -d 2026-08-03

무엇을 고치든 `meta.updated` 와 그 갈래의 `dates.touched` 가 함께 오늘로 간다.
손댄 날을 따로 챙기다 빠뜨리는 일이 잦아 여기에 붙여 두었다.
`touched` 를 건드리고 싶지 않으면 `--no-touch` 를 준다.
"""
import json, sys, os, argparse, datetime, hashlib, copy

DEFAULT = 'loggia-data.json'

# 날짜가 사는 자리. 짧은 이름으로 부른다
DATE_KEYS = ('deadline', 'sent', 'decided', 'expected', 'touched')
# 항목에 바로 붙는 자리
FLAT_KEYS = ('title', 'status', 'kind', 'venue', 'note', '품', 'id')


def load(path):
    with open(path, encoding='utf-8') as f:
        return json.load(f)


def save(path, d):
    with open(path, 'w', encoding='utf-8') as f:
        f.write(json.dumps(d, ensure_ascii=False, indent=1))


def today(args):
    return args.date or datetime.date.today().isoformat()


def sections(d):
    return d.get('sections', [])


def find(d, iid):
    """갈래 하나를 찾는다. 지난 일에서도 찾는다."""
    for s in sections(d):
        for it in s['items']:
            if it['id'] == iid:
                return it, s
    for it in d.get('archive', []):
        if it['id'] == iid:
            return it, {'id': 'archive', 'label': '지난 일'}
    die(f'그런 갈래가 없습니다: {iid}\n' + '있는 것: ' + ', '.join(all_ids(d)))


def all_ids(d):
    out = [it['id'] for s in sections(d) for it in s['items']]
    out += [it['id'] for it in d.get('archive', [])]
    return out


def venue_of(d, vid):
    for g in d.get('venueGroups', []):
        for v in g['venues']:
            if v['id'] == vid:
                return v, g
    die(f'그런 낼 곳이 없습니다: {vid}')


def die(msg):
    print(msg, file=sys.stderr)
    sys.exit(1)


def steps_of(item):
    """걸음을 {'t':..., 'due':...} 꼴로 고르게 편다."""
    st = item.get('steps') or ([item['next']] if item.get('next') else [])
    return [{'t': x} if isinstance(x, str) else dict(x) for x in st]


def put_steps(item, ss):
    """다시 데이터 꼴로 접는다. 날짜 없는 것은 글만 남긴다."""
    item['steps'] = [s['t'] if not s.get('due') else {'t': s['t'], 'due': s['due']} for s in ss]
    if not item['steps']:
        del item['steps']
    item.pop('next', None)


def key_of(iid, text):
    """장부가 쓰는 그 열쇠. 판과 같은 셈이어야 한다."""
    return iid + '.' + hashlib.sha1(text.encode('utf-8')).hexdigest()[:8]


def pick_step(item, needle):
    """글 일부로 걸음 하나를 집는다. 둘 이상 걸리면 멈춘다."""
    ss = steps_of(item)
    hit = [i for i, s in enumerate(ss) if needle in s['t']]
    if not hit:
        die('그런 걸음이 없습니다: ' + needle + '\n'
            + '\n'.join(f'  {i+1} {s["t"]}' for i, s in enumerate(ss)))
    if len(hit) > 1:
        die('여럿이 걸립니다. 더 좁혀 주세요.\n'
            + '\n'.join(f'  {i+1} {ss[i]["t"]}' for i in hit))
    return hit[0], ss


# ── 보여 주기 ────────────────────────────────────────────────────────────────

def dday(iso, base):
    if not iso or len(iso) != 10:
        return ''
    try:
        n = (datetime.date.fromisoformat(iso) - datetime.date.fromisoformat(base)).days
    except ValueError:
        return ''
    return '오늘' if n == 0 else (f'D-{n}' if n > 0 else f'{-n}일 지남')


def line_of(item, d, base):
    st = d['statuses'].get(item.get('status'), {}).get('label', item.get('status', ''))
    dt = item.get('dates', {})
    when = ''
    if dt.get('deadline'):
        when = f'마감 {dt["deadline"]} {dday(dt["deadline"], base)}'
    elif dt.get('sent'):
        when = f'냄 {dt["sent"]}'
    ss = steps_of(item)
    return (f'{item["id"]:<10} {item["title"]}\n'
            f'{"":<10} {st}'
            + (f' · {when}' if when else '')
            + (f' · 손댄 날 {dt["touched"]}' if dt.get('touched') else ' · 손댄 기록 없음')
            + (f' · 걸음 {len(ss)}' if ss else ' · 걸음 없음'))


def cmd_show(d, args):
    base = today(args)
    if not args.id:
        for s in sections(d):
            print(f'\n[{s["id"]}] {s["label"]}  {len(s["items"])}')
            for it in s['items']:
                print('  ' + line_of(it, d, base).replace('\n', '\n  '))
        if d.get('archive'):
            print(f'\n[archive] 지난 일  {len(d["archive"])}')
            for it in d['archive']:
                print(f'  {it["id"]:<10} {it["title"]}')
        return
    it, sec = find(d, args.id)
    v = None
    for g in d.get('venueGroups', []):
        for x in g['venues']:
            if x['id'] == it.get('venue'):
                v = x
    st = d['statuses'].get(it.get('status'), {}).get('label', it.get('status', ''))
    print(f'{it["id"]}  {it["title"]}' + (f' · {v["name"]}' if v else ''))
    print(f'  칸 {sec["label"]} ({sec.get("id","")}) · 상태 {st} ({it.get("status","")})'
          + (f' · 품 {it["품"]}' if it.get('품') else '')
          + (f' · 결 {it["kind"]}' if it.get('kind') else ''))
    dt = it.get('dates', {})
    if dt:
        print('  날짜 ' + ' · '.join(
            f'{k} {dt[k]}' + (f' {dday(dt[k], base)}' if k == 'deadline' else '')
            for k in DATE_KEYS if dt.get(k)))
    ss = steps_of(it)
    if ss:
        print('  걸음')
        for i, s in enumerate(ss):
            print(f'    {i+1} {s["t"]}' + (f'  [{s["due"]} {dday(s["due"], base)}]' if s.get('due') else ''))
    else:
        print('  걸음 없음')
    if it.get('note'):
        print('  메모 ' + it['note'])
    u = it.get('uses') or {}
    if u:
        print('  씀 ' + ' · '.join(f'{k} {", ".join(vv)}' for k, vv in u.items() if vv))
    if it.get('links') or it.get('chats'):
        print(f'  링크 {len(it.get("links", []))}개 · 대화 {len(it.get("chats", []))}개')


def cmd_steps(d, args):
    it, _ = find(d, args.id)
    for i, s in enumerate(steps_of(it)):
        print(f'{i+1} {s["t"]}' + (f'  [{s["due"]}]' if s.get('due') else '')
              + f'   {key_of(it["id"], s["t"])}')


def cmd_venues(d, args):
    base = today(args)
    for g in d.get('venueGroups', []):
        print(f'\n[{g["name"]}]  {len(g["venues"])}')
        for v in g['venues']:
            bits = [v.get('sub', ''), v.get('type', '')]
            if v.get('deadline'):
                bits.append(f'마감 {v["deadline"]} {dday(v["deadline"], base)}')
            print(f'  {v["id"]:<16} {v["name"]}')
            print(f'  {"":<16} ' + ' · '.join(b for b in bits if b))


def cmd_venue(d, args):
    v, g = venue_of(d, args.id)
    print(f'{v["id"]}  {v["name"]}   [{g["name"]}]')
    for k, val in v.items():
        if k in ('id', 'name'):
            continue
        print(f'  {k} {json.dumps(val, ensure_ascii=False) if isinstance(val, (dict, list)) else val}')


# ── 고치기 ───────────────────────────────────────────────────────────────────

def stamp(d, item, args):
    """무엇을 고치든 갱신일을 오늘로. 갈래를 고쳤으면 손댄 날도."""
    d.setdefault('meta', {})['updated'] = today(args)
    if item is not None and not args.no_touch:
        item.setdefault('dates', {})['touched'] = today(args)


def cmd_touch(d, args):
    it, _ = find(d, args.id)
    it.setdefault('dates', {})['touched'] = today(args)
    d.setdefault('meta', {})['updated'] = today(args)
    return [f'{args.id} 손댄 날 → {today(args)}']


def cmd_set(d, args):
    it, _ = find(d, args.id)
    f, val = args.field, args.value
    if f in DATE_KEYS:
        old = it.get('dates', {}).get(f)
        it.setdefault('dates', {})[f] = val
        msg = f'{args.id} dates.{f}  {old or "없음"} → {val}'
    elif f in FLAT_KEYS:
        old = it.get(f)
        if f == 'status' and val not in d.get('statuses', {}):
            die(f'없는 상태입니다: {val}\n쓸 수 있는 것: ' + ' '.join(d.get('statuses', {})))
        if f == '품' and val not in d.get('efforts', {}):
            die(f'없는 품입니다: {val}\n쓸 수 있는 것: ' + ' '.join(d.get('efforts', {})))
        it[f] = val
        msg = f'{args.id} {f}  {old or "없음"} → {val}'
    else:
        die(f'고칠 수 없는 자리입니다: {f}\n'
            + '날짜 ' + ' '.join(DATE_KEYS) + '\n그 밖 ' + ' '.join(FLAT_KEYS))
    stamp(d, it, args)
    return [msg]


def cmd_clear(d, args):
    it, _ = find(d, args.id)
    f = args.field
    if f in DATE_KEYS:
        old = it.get('dates', {}).pop(f, None)
        if not it.get('dates'):
            it.pop('dates', None)
    else:
        old = it.pop(f, None)
    if old is None:
        die(f'{args.id} 에 {f} 가 없습니다')
    stamp(d, it, args)
    return [f'{args.id} {f} 지움 (있던 값 {old})']


def cmd_step_done(d, args):
    it, _ = find(d, args.id)
    i, ss = pick_step(it, args.text)
    gone = ss.pop(i)
    put_steps(it, ss)
    stamp(d, it, args)
    out = [f'{args.id} 걸음 뺌  {gone["t"]}']
    if not ss:
        out.append(f'   ! {args.id} 는 이제 걸음이 없습니다. 다음에 무엇을 할지 정해야 합니다')
    return out


def cmd_step_add(d, args):
    it, _ = find(d, args.id)
    ss = steps_of(it)
    row = {'t': args.text}
    if args.due:
        row['due'] = args.due
    if args.first:
        ss.insert(0, row)
    else:
        ss.append(row)
    put_steps(it, ss)
    stamp(d, it, args)
    return [f'{args.id} 걸음 더함  {args.text}' + (f'  [{args.due}]' if args.due else '')
            + ('  (맨 앞)' if args.first else '')]


def cmd_step_first(d, args):
    it, _ = find(d, args.id)
    i, ss = pick_step(it, args.text)
    ss.insert(0, ss.pop(i))
    put_steps(it, ss)
    stamp(d, it, args)
    return [f'{args.id} 맨 앞으로  {ss[0]["t"]}']


def cmd_move(d, args):
    it, sec = find(d, args.id)
    if sec.get('id') == args.to:
        die(f'{args.id} 는 이미 {args.to} 에 있습니다')
    dest = None
    for s in sections(d):
        if s['id'] == args.to:
            dest = s
    if dest is None:
        die('그런 칸이 없습니다: ' + args.to + '\n있는 것: '
            + ' '.join(s['id'] for s in sections(d)))
    for s in sections(d):
        if it in s['items']:
            s['items'].remove(it)
    dest['items'].append(it)
    stamp(d, it, args)
    return [f'{args.id}  {sec["label"]} → {dest["label"]}']


def cmd_archive(d, args):
    it, sec = find(d, args.id)
    if sec.get('id') == 'archive':
        die(f'{args.id} 는 이미 지난 일입니다')
    for s in sections(d):
        if it in s['items']:
            s['items'].remove(it)
    d.setdefault('archive', []).insert(0, it)
    stamp(d, it, args)
    out = [f'{args.id}  {sec["label"]} → 지난 일']
    if not it.get('dates', {}).get('decided'):
        out.append('   ! 결과 날짜(decided)가 비어 있습니다. lg.py set 으로 채워 주세요')
    return out


def cmd_venue_set(d, args):
    v, _ = venue_of(d, args.id)
    old = v.get(args.field)
    if isinstance(old, (dict, list)):
        die(f'{args.field} 는 여러 값이 든 자리라 여기서 못 고칩니다. 손으로 고쳐 주세요.')
    v[args.field] = args.value
    d.setdefault('meta', {})['updated'] = today(args)
    return [f'{args.id} {args.field}  {old or "없음"} → {args.value}']


# ── 들머리 ───────────────────────────────────────────────────────────────────

READERS = {'show': cmd_show, 'steps': cmd_steps, 'venues': cmd_venues, 'venue': cmd_venue}
WRITERS = {
    'touch': cmd_touch, 'set': cmd_set, 'clear': cmd_clear,
    'step-done': cmd_step_done, 'step-add': cmd_step_add, 'step-first': cmd_step_first,
    'move': cmd_move, 'archive': cmd_archive, 'venue-set': cmd_venue_set,
}


def main():
    p = argparse.ArgumentParser(add_help=False)
    p.add_argument('cmd', nargs='?')
    p.add_argument('a', nargs='?')
    p.add_argument('b', nargs='?')
    p.add_argument('c', nargs='?')
    p.add_argument('-f', '--file', default=DEFAULT)
    p.add_argument('-w', '--write', action='store_true')
    p.add_argument('-d', '--date')
    p.add_argument('--due')
    p.add_argument('--first', action='store_true')
    p.add_argument('--no-touch', action='store_true')
    p.add_argument('-h', '--help', action='store_true')
    args = p.parse_args()

    if args.help or not args.cmd:
        print(__doc__)
        return

    if not os.path.exists(args.file):
        die(f'데이터 파일이 없습니다: {args.file}\n먼저 tools/fetch.sh 로 받으세요.')
    d = load(args.file)

    if args.cmd in READERS:
        args.id = args.a
        READERS[args.cmd](d, args)
        return

    if args.cmd not in WRITERS:
        die('모르는 일입니다: ' + args.cmd + '\n'
            + '보는 일 ' + ' '.join(READERS) + '\n고치는 일 ' + ' '.join(WRITERS))

    # 자리 이름을 일에 맞게 붙여 준다
    args.id = args.a
    args.field = args.b
    args.value = args.c
    args.text = args.b
    args.to = args.b
    if args.id is None:
        die(f'{args.cmd} 에는 갈래 이름이 필요합니다')

    before = copy.deepcopy(d)
    msgs = WRITERS[args.cmd](d, args)
    for m in msgs:
        print(m)

    if before == d:
        print('바뀐 것이 없습니다.')
        return
    if args.write:
        save(args.file, d)
        print(f'넣었습니다  {args.file}')
    else:
        print('아직 안 넣었습니다. 넣으려면 -w 를 붙이세요.')


if __name__ == '__main__':
    main()
