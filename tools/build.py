#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
build.py — loggia-data.json 에서 화면이 아닌 두 가지를 만든다.

    python3 tools/build.py loggia-data.json site/

만들어지는 것
    site/digest.json   아침 메일이 읽는 꾸러미. publish.sh 가 digest.enc 로 암호화한다
    site/스냅샷.md      눈으로 훑어보는 사본. 드롭박스에 넣어 둔다

다섯 페이지는 여기서 짓지 않는다. 2026년 8월 1일에 브라우저로 옮겼다.
화면 만드는 코드는 `public/app.js` 에 있고, HTML 틀은 `public/*.html` 다섯 페이지다.
옮긴 까닭은 이렇다. 암호화된 파일은 갱신할 때마다 처음부터 끝까지 달라 보이므로,
글자 하나를 고쳐도 368KB가 저장소에 새로 쌓였다. 이제 올라가는 것은 47KB의
data.enc 하나뿐이다.

날짜 셈은 여기서 하나도 하지 않는다. 오늘이 언제인지는 보드를 여는 그 순간과
메일을 보내는 그 순간에만 알 수 있다.
"""
import json, sys, os


def all_items(D):
    """진행 중, 기다리는 중, 지난 일을 한 줄로 잇는다."""
    for s in D['sections']:
        for it in s['items']:
            yield it, False
    for it in D.get('archive', []):
        yield it, True


def index_tags(venue, D):
    """색인 딱지를 (모양, 글자) 짝으로 돌려준다.

    데이터에는 키만 적는다.  "indexes": ["ahci", "scopus"]
    앞에 빼기표를 붙이면 미등재를 뜻한다.  "-ahci"  →  A&HCI 미등재
    예전 형식인 [["strong", "A&HCI"]] 도 그대로 받는다.

    화면에서 쓰는 같은 손이 `public/app.js` 의 indexTags 에 있다.
    둘이 어긋나면 스냅샷과 판이 다른 말을 한다. 고칠 때 함께 고친다.
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


def steps_of(item):
    """다음 할 일들. 저마다 제 날짜를 가질 수 있다.

        "추천인에게 메일 보내기"
        {"t": "초고 넘기기", "due": "2026-08-10"}

    기록에서 오는 할 일은 여기 없다. 그것은 보드에만 뜬다. 아침 메일은 데이터에
    적힌 것만 말한다. 아직 참이 아닌 것을 참인 척 부치지 않기 위해서다.
    """
    st = item.get('steps') or ([item['next']] if item.get('next') else [])
    return [{'t': x} if isinstance(x, str) else dict(x) for x in st]


def digest_json(D, venue_index):
    """워커가 아침에 읽는 작은 꾸러미.

    여기서는 날짜 셈을 하나도 하지 않는다. 보드가 몇 주 동안 올라가지 않아도
    아침 메일이 낡지 않으려면, 담는 것은 날것이어야 하고 며칠 남았는지는
    워커가 세야 한다.
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
                due.append(dict(base, due=d['deadline'], step=(ss[0]['t'] if ss else '')))
            if sec['id'] == 'now' and ss:
                doing.append(dict(base, step=ss[0]['t'], due=(ss[0].get('due') or d.get('deadline', '')),
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
        # 분기마다 돌아볼 때 쓰는 것들. 평소 편지는 이 둘을 보지 않는다
        'log': [x for x in ([{'d': it.get('dates', {}).get(k), 'k': lab, 't': it['title']}
                             for it, _arc in all_items(D)
                             for k, lab in (('sent', '냈다'), ('decided', '끝났다'),
                                            ('touched', '손댔다'))])
                if x['d'] and len(x['d']) == 10],
        'compass': (D.get('compass') or {}).get('lines') or [],
    }


def snapshot_md(D, venue_index):
    """눈으로 훑어보는 사본. 드롭박스에 내려놓아 눌러 보는 용도다.

    진짜 데이터가 아니다. 여기 고쳐 봐야 판에 반영되지 않는다.
    그 사실을 첫 줄에 적어 둔다.
    """
    L = ['# 로지아 스냅샷',
         '',
         f'갱신 {D["meta"]["updated"]} · {D["meta"].get("note", "")}',
         '',
         '> 이것은 **눈으로 훑어보는 사본**이다. 진짜 데이터는 저장소 `eeruwang/loggia` 의',
         '> `public/data.enc` 안에 암호화되어 있다. 여기를 고쳐도 보드는 바뀌지 않는다.',
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
                L.append(f'  \n  다음 할 일. {it["next"]}')
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

    venue_index = {}
    for g in D['venueGroups']:
        for v in g['venues']:
            venue_index[v['id']] = v

    md = snapshot_md(D, venue_index)
    with open(os.path.join(out_dir, '스냅샷.md'), 'w', encoding='utf-8') as f:
        f.write(md)
    print(f'  스냅샷.md  {len(md.encode())//1024}KB  (드롭박스에 넣어 둘 사본)')

    dg = json.dumps(digest_json(D, venue_index), ensure_ascii=False, separators=(',', ':'))
    with open(os.path.join(out_dir, 'digest.json'), 'w', encoding='utf-8') as f:
        f.write(dg)
    print(f'  digest.json  {len(dg.encode())//1024}KB  (아침 메일이 읽는 것)')
    print('  화면은 브라우저가 만든다. public/app.js 를 본다.')


if __name__ == '__main__':
    main()
