#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
lg.py — 로지아 데이터를 한 항목씩 보고 고친다.

    python3 tools/lg.py <명령> [...]

왜 있는가

    갱신할 때마다 파일을 열고 항목을 찾고 값을 바꾸고 다시 저장하는 똑같은
    코드를 매번 새로 썼다. 그 부분을 여기에 넣어 두었다.
    고치기 전에 지금 상태를 확인해야 하는데, 그러자고 데이터 전체를 열어 보면
    낭비다. show 명령이 필요한 항목만 간추려 보여준다.

보기

    lg.py show                     전체 항목을 한 줄씩
    lg.py show glasgow             항목 하나를 자세히
    lg.py todos glasgow            할 일 목록과 각각의 체크 키
    lg.py venues                   낼 곳 전체를 한 줄씩
    lg.py venue mirac              낼 곳 하나

고치기  (-w 를 붙여야 실제로 저장된다. 안 붙이면 바뀔 내용만 보여준다)

    lg.py set glasgow status 제출 -w             상태 바꾸기
    lg.py set glasgow deadline 2026-08-05 -w     마감일. sent decided expected 도 같다
    lg.py set glasgow 품 반나절 -w                걸리는 시간
    lg.py set glasgow note "..." -w              메모
    lg.py clear glasgow deadline -w              값 지우기
    lg.py done glasgow "추천인" -w                할 일 하나 완료 처리 (내용 일부로 찾음)
    lg.py add glasgow "면접 준비" --due 2026-08-20 -w
    lg.py first glasgow "소리 내어" -w            그 할 일을 맨 위로
    lg.py move glasgow waiting -w                섹션 옮기기. now waiting later
    lg.py archive glasgow -w                     지난 일로 보내기
    lg.py venue-set mirac deadline 2026-09-30 -w 낼 곳 정보 고치기
    lg.py touch glasgow -w                       마지막 작업일만 오늘로

    -w  실제로 저장한다
    -d  오늘이 아닌 날짜로 기록한다.  -d 2026-08-03

무엇을 고치든 meta.updated 와 그 항목의 마지막 작업일이 함께 오늘로 바뀐다.
따로 챙기다 빠뜨리는 일이 잦아서 자동으로 묶어 두었다.
마지막 작업일을 건드리고 싶지 않으면 --no-touch 를 붙인다.
"""
import json, sys, os, argparse, datetime, hashlib, copy

DEFAULT = 'loggia-data.json'

# dates 안에 들어가는 값들
DATE_KEYS = ('deadline', 'sent', 'decided', 'expected', 'touched')
DATE_NAME = {'deadline': '마감', 'sent': '보낸 날', 'decided': '결과',
             'expected': '예상', 'touched': '마지막 작업'}
# 항목에 바로 붙는 값들
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
    """항목 하나를 찾는다. 지난 일에서도 찾는다."""
    for s in sections(d):
        for it in s['items']:
            if it['id'] == iid:
                return it, s
    for it in d.get('archive', []):
        if it['id'] == iid:
            return it, {'id': 'archive', 'label': '지난 일'}
    die(f'그런 항목이 없습니다: {iid}\n있는 항목: ' + ', '.join(all_ids(d)))


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


def todos_of(item):
    """할 일 목록을 {'t':..., 'due':...} 형태로 통일해서 돌려준다."""
    st = item.get('steps') or ([item['next']] if item.get('next') else [])
    return [{'t': x} if isinstance(x, str) else dict(x) for x in st]


def put_todos(item, ss):
    """다시 데이터 형태로 되돌린다. 날짜가 없으면 문자열로만 저장한다."""
    item['steps'] = [s['t'] if not s.get('due') else {'t': s['t'], 'due': s['due']} for s in ss]
    if not item['steps']:
        del item['steps']
    item.pop('next', None)


def check_key(iid, text):
    """사이트에서 체크할 때 쓰는 키. 화면과 계산이 같아야 한다."""
    return iid + '.' + hashlib.sha1(text.encode('utf-8')).hexdigest()[:8]


def pick(item, needle):
    """내용 일부로 할 일 하나를 고른다. 여러 개가 걸리면 멈춘다."""
    ss = todos_of(item)
    hit = [i for i, s in enumerate(ss) if needle in s['t']]
    if not hit:
        die('그런 할 일이 없습니다: ' + needle + '\n'
            + '\n'.join(f'  {i+1} {s["t"]}' for i, s in enumerate(ss)))
    if len(hit) > 1:
        die('여러 개가 걸립니다. 더 구체적으로 적어 주세요.\n'
            + '\n'.join(f'  {i+1} {ss[i]["t"]}' for i in hit))
    return hit[0], ss


# ── 보기 ─────────────────────────────────────────────────────────────────────

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
        when = f'마감 {dt["deadline"]} ({dday(dt["deadline"], base)})'
    elif dt.get('sent'):
        when = f'{dt["sent"]} 보냄'
    n = len(todos_of(item))
    return (f'{item["id"]:<10} {item["title"]}\n'
            f'{"":<10} {st}'
            + (f' · {when}' if when else '')
            + (f' · 마지막 작업 {dt["touched"]}' if dt.get('touched') else ' · 작업 기록 없음')
            + (f' · 할 일 {n}개' if n else ' · 할 일 없음'))


def cmd_show(d, args):
    base = today(args)
    if not args.id:
        for s in sections(d):
            print(f'\n[{s["id"]}] {s["label"]}  {len(s["items"])}개')
            for it in s['items']:
                print('  ' + line_of(it, d, base).replace('\n', '\n  '))
        if d.get('archive'):
            print(f'\n[archive] 지난 일  {len(d["archive"])}개')
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
    print(f'{it["id"]}  {it["title"]}' + (f'  ({v["name"]})' if v else ''))
    print('  ' + ' · '.join(x for x in [
        sec['label'], st, it.get('품', ''), it.get('kind', '')] if x))
    dt = it.get('dates', {})
    if dt:
        print('  ' + ' · '.join(
            f'{DATE_NAME.get(k, k)} {dt[k]}'
            + (f' ({dday(dt[k], base)})' if k == 'deadline' else '')
            for k in DATE_KEYS if dt.get(k)))
    ss = todos_of(it)
    if ss:
        print('  할 일')
        for i, s in enumerate(ss):
            print(f'    {i+1} {s["t"]}'
                  + (f'   [{s["due"]}까지 {dday(s["due"], base)}]' if s.get('due') else ''))
    else:
        print('  할 일 없음')
    if it.get('note'):
        print('  메모 ' + it['note'])
    u = it.get('uses') or {}
    if any(u.values()):
        print('  ' + ' · '.join(f'{k} {", ".join(vv)}' for k, vv in u.items() if vv))
    if it.get('links') or it.get('chats'):
        print(f'  링크 {len(it.get("links", []))}개 · 대화 {len(it.get("chats", []))}개')


def cmd_todos(d, args):
    it, _ = find(d, args.id)
    ss = todos_of(it)
    if not ss:
        print(f'{args.id} 에 할 일이 없습니다.')
        return
    for i, s in enumerate(ss):
        print(f'{i+1} {s["t"]}' + (f'   [{s["due"]}까지]' if s.get('due') else ''))
        print(f'   체크 키 {check_key(it["id"], s["t"])}')


def cmd_venues(d, args):
    base = today(args)
    for g in d.get('venueGroups', []):
        print(f'\n[{g["name"]}]  {len(g["venues"])}개')
        for v in g['venues']:
            bits = [v.get('sub', ''), v.get('type', '')]
            if v.get('deadline'):
                bits.append(f'마감 {v["deadline"]} ({dday(v["deadline"], base)})')
            print(f'  {v["id"]:<16} {v["name"]}')
            print(f'  {"":<16} ' + ' · '.join(b for b in bits if b))


def cmd_venue(d, args):
    v, g = venue_of(d, args.id)
    print(f'{v["id"]}  {v["name"]}   [{g["name"]}]')
    for k, val in v.items():
        if k in ('id', 'name'):
            continue
        print(f'  {k} ' + (json.dumps(val, ensure_ascii=False)
                           if isinstance(val, (dict, list)) else str(val)))


# ── 고치기 ───────────────────────────────────────────────────────────────────

def stamp(d, item, args):
    """뭘 고치든 갱신일을 오늘로. 항목을 고쳤으면 마지막 작업일도 함께."""
    d.setdefault('meta', {})['updated'] = today(args)
    if item is not None and not args.no_touch:
        item.setdefault('dates', {})['touched'] = today(args)


def cmd_touch(d, args):
    it, _ = find(d, args.id)
    it.setdefault('dates', {})['touched'] = today(args)
    d.setdefault('meta', {})['updated'] = today(args)
    return [f'{args.id} 마지막 작업일을 {today(args)} 로 바꿉니다']


def cmd_set(d, args):
    it, _ = find(d, args.id)
    f, val = args.field, args.value
    if val is None:
        die(f'무엇으로 바꿀지 적어 주세요.  lg.py set {args.id} {f} <값>')
    if f in DATE_KEYS:
        old = it.get('dates', {}).get(f)
        it.setdefault('dates', {})[f] = val
        msg = f'{args.id} {DATE_NAME.get(f, f)}: {old or "비어 있음"} → {val}'
    elif f in FLAT_KEYS:
        old = it.get(f)
        if f == 'status' and val not in d.get('statuses', {}):
            die(f'쓸 수 없는 상태입니다: {val}\n'
                + '가능한 값: ' + ' '.join(d.get('statuses', {})))
        if f == '품' and val not in d.get('efforts', {}):
            die(f'쓸 수 없는 값입니다: {val}\n'
                + '가능한 값: ' + ' '.join(d.get('efforts', {})))
        it[f] = val
        msg = f'{args.id} {f}: {old or "비어 있음"} → {val}'
    else:
        die(f'고칠 수 없는 항목입니다: {f}\n'
            + '날짜: ' + ' '.join(DATE_KEYS) + '\n그 외: ' + ' '.join(FLAT_KEYS))
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
    return [f'{args.id} {DATE_NAME.get(f, f)} 를 지웁니다 (원래 값 {old})']


def cmd_done(d, args):
    it, _ = find(d, args.id)
    i, ss = pick(it, args.text)
    gone = ss.pop(i)
    put_todos(it, ss)
    stamp(d, it, args)
    out = [f'{args.id} 완료 처리: {gone["t"]}']
    if not ss:
        out.append(f'   ! {args.id} 에 남은 할 일이 없습니다. 다음에 뭘 할지 정해야 합니다')
    return out


def cmd_add(d, args):
    it, _ = find(d, args.id)
    ss = todos_of(it)
    row = {'t': args.text}
    if args.due:
        row['due'] = args.due
    if args.first:
        ss.insert(0, row)
    else:
        ss.append(row)
    put_todos(it, ss)
    stamp(d, it, args)
    return [f'{args.id} 할 일 추가: {args.text}'
            + (f' ({args.due}까지)' if args.due else '')
            + (' [맨 위에]' if args.first else '')]


def cmd_first(d, args):
    it, _ = find(d, args.id)
    i, ss = pick(it, args.text)
    ss.insert(0, ss.pop(i))
    put_todos(it, ss)
    stamp(d, it, args)
    return [f'{args.id} 맨 위로 올림: {ss[0]["t"]}']


def cmd_move(d, args):
    it, sec = find(d, args.id)
    if sec.get('id') == args.to:
        die(f'{args.id} 는 이미 {args.to} 에 있습니다')
    dest = None
    for s in sections(d):
        if s['id'] == args.to:
            dest = s
    if dest is None:
        die('그런 섹션이 없습니다: ' + str(args.to)
            + '\n가능한 값: ' + ' '.join(s['id'] for s in sections(d)))
    for s in sections(d):
        if it in s['items']:
            s['items'].remove(it)
    dest['items'].append(it)
    stamp(d, it, args)
    return [f'{args.id} 을(를) {sec["label"]} 에서 {dest["label"]} 으로 옮깁니다']


def cmd_archive(d, args):
    it, sec = find(d, args.id)
    if sec.get('id') == 'archive':
        die(f'{args.id} 는 이미 지난 일입니다')
    for s in sections(d):
        if it in s['items']:
            s['items'].remove(it)
    d.setdefault('archive', []).insert(0, it)
    stamp(d, it, args)
    out = [f'{args.id} 을(를) {sec["label"]} 에서 지난 일로 옮깁니다']
    if not it.get('dates', {}).get('decided'):
        out.append('   ! 결과 날짜가 비어 있습니다.  lg.py set '
                   + args.id + ' decided <날짜> -w')
    return out


def cmd_venue_set(d, args):
    v, _ = venue_of(d, args.id)
    old = v.get(args.field)
    if isinstance(old, (dict, list)):
        die(f'{args.field} 는 값이 여러 개라 여기서는 못 고칩니다. 직접 고쳐 주세요.')
    if args.value is None:
        die(f'무엇으로 바꿀지 적어 주세요.  lg.py venue-set {args.id} {args.field} <값>')
    v[args.field] = args.value
    d.setdefault('meta', {})['updated'] = today(args)
    return [f'{args.id} {args.field}: {old or "비어 있음"} → {args.value}']


# ── 실행 ─────────────────────────────────────────────────────────────────────

READERS = {'show': cmd_show, 'todos': cmd_todos, 'venues': cmd_venues, 'venue': cmd_venue}
WRITERS = {
    'touch': cmd_touch, 'set': cmd_set, 'clear': cmd_clear,
    'done': cmd_done, 'add': cmd_add, 'first': cmd_first,
    'move': cmd_move, 'archive': cmd_archive, 'venue-set': cmd_venue_set,
}
# 예전 이름도 그대로 받는다
ALIAS = {'steps': 'todos', 'step-done': 'done', 'step-add': 'add', 'step-first': 'first'}


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

    cmd = ALIAS.get(args.cmd, args.cmd)

    if not os.path.exists(args.file):
        die(f'데이터 파일이 없습니다: {args.file}\n먼저 tools/fetch.sh 로 받아 주세요.')
    d = load(args.file)

    if cmd in READERS:
        args.id = args.a
        READERS[cmd](d, args)
        return

    if cmd not in WRITERS:
        die('모르는 명령입니다: ' + args.cmd + '\n'
            + '보기: ' + ' '.join(READERS) + '\n고치기: ' + ' '.join(WRITERS))

    args.id = args.a
    args.field = args.b
    args.value = args.c
    args.text = args.b
    args.to = args.b
    if args.id is None:
        die(f'{args.cmd} 에는 항목 이름이 필요합니다')

    before = copy.deepcopy(d)
    for m in WRITERS[cmd](d, args):
        print(m)

    if before == d:
        print('바뀐 것이 없습니다.')
        return
    if args.write:
        save(args.file, d)
        print(f'저장했습니다  {args.file}')
    else:
        print('아직 저장하지 않았습니다. 저장하려면 -w 를 붙여 주세요.')


if __name__ == '__main__':
    main()
