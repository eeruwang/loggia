/* =============================================================================
   ticktick.ts — 워커가 틱틱을 직접 읽고 쓴다.

   틱틱에는 알림을 밀어 주는 길이 없다. 그래서 열 분마다 들여다본다.
   읽어서 판과 견주고, 틱틱을 판에 맞추고, 사람이 틱틱에서 한 일은 장부에 적는다.
   장부에 적어 두면 같은 시계에 도는 flush 가 데이터에 옮긴다. 이 파일은
   data.enc 를 고치지 않는다. 읽기만 한다.

   갖춰야 할 것
     TICKTICK_CLIENT_ID, TICKTICK_CLIENT_SECRET  틱틱 개발자 센터에서 받는다
     KV 에 든 토큰                                /tt/login 을 한 번 눌러 받는다
   하나라도 없으면 조용히 건너뛴다.

   누가 고쳤는지 가리는 법
     회차마다 틱틱에서 본 값을 살림에 함께 적어 둔다. 이번에 본 값이 지난 회차와
     다르면 틱틱에서 고친 것이니 판으로 보낸다. 틱틱은 그대로인데 판이 다르면
     판에서 고친 것이니 틱틱을 고친다. 그래야 한쪽이 고친 것을 다른 쪽이
     되돌리지 않는다.

   어느 줄이 판의 무엇인지 알아보는 법
     과제 아이디와 열쇠를 짝지어 KV 에 둔다. 틱틱 과제의 본문에는 아무것도 적지
     않는다. 본문은 통째로 사람의 메모 자리다. 살림이 비면 어버이가 알려 주는
     항목과 제목의 지문으로 짝을 되찾고, 그래도 못 찾은 줄만 새로 적은 것으로 본다.
     예전에 본문 첫 줄에 박아 두었던 표시가 남아 있으면 읽어서 쓰고 그 줄은 지운다.

   체크와 지움을 가리는 법
     끝낸 것을 한꺼번에 돌려주는 자리는 없다. 그래서 지난 회차에 보이던 과제가
     이번에 안 보이면 그 하나를 아이디로 다시 불러 본다. status 가 2 면 체크한
     것이니 판에서도 끝낸 것으로 넘긴다. 0 이면 휴지통에 든 것이니 사람이 지운
     것으로 보고 그 할 일을 판에서도 지운다.
   ========================================================================== */
import { loadData, type FlushEnv } from './flush';

export interface TTEnv extends FlushEnv {
  LEDGER?: KVNamespace;
  TICKTICK_TOKEN?: string;        // 틱틱 웹에서 바로 받은 토큰. 이것만 있어도 된다
  TICKTICK_CLIENT_ID?: string;    // 아래 셋은 앱을 등록해 받는 길. 토큰이 없을 때만 쓴다
  TICKTICK_CLIENT_SECRET?: string;
  TICKTICK_REDIRECT?: string;
  LEDGER_TOKEN?: string;
}

type Any = any;

const TOKEN_KEY = 'ticktick:token';
const SEEN_KEY = 'ticktick:seen';
const HEALTH_KEY = 'ticktick:health';
const SEED_KEY = 'seeds';
const JOBS_KEY = 'jobs';
const DONE_KEY = 'board';
const ADD_KEY = 'added';
const EDIT_KEY = 'edited';

const TODO_PID = '6aa7ae1d8f084b19082e331e';
const DUE_PID = '6aa7ae1f8f081102b5324922';
const IN_PID = '6aaa00c98f08f43e978c4deb';   // 접수함. 여기 적은 것이 판의 새 항목이 된다
const API = 'https://api.ticktick.com/open/v1';
/* 하루짜리 일정의 알림. 자정을 기준으로 잰다.
   -PT15H 는 하루 전 아침 아홉 시, PT9H 는 당일 아침 아홉 시다.
   사람이 알림을 손본 과제는 건드리지 않는다. */
const REMIND = ['TRIGGER:-PT15H', 'TRIGGER:PT9H'];
const AUTH = 'https://ticktick.com/oauth/authorize';
const TOKEN = 'https://ticktick.com/oauth/token';

/* ── 토큰 ────────────────────────────────────────────────────────────────── */

function redirectUri(env: TTEnv) {
  return env.TICKTICK_REDIRECT || 'https://loggia.moonilsun.com/tt/callback';
}

/** 권한 허용 화면으로 보낸다.  GET /tt/login?k=<LEDGER_TOKEN> */
export function ttLogin(env: TTEnv): Response {
  if (!env.TICKTICK_CLIENT_ID) return new Response('설정이 없습니다', { status: 404 });
  const u = new URL(AUTH);
  u.searchParams.set('client_id', env.TICKTICK_CLIENT_ID);
  u.searchParams.set('scope', 'tasks:read tasks:write');
  u.searchParams.set('state', 'loggia');
  u.searchParams.set('redirect_uri', redirectUri(env));
  u.searchParams.set('response_type', 'code');
  return Response.redirect(u.toString(), 302);
}

/** 틱틱이 되돌려 보내는 자리.  GET /tt/callback?code=... */
export async function ttCallback(env: TTEnv, url: URL): Promise<Response> {
  const code = url.searchParams.get('code');
  if (!code) return new Response('코드가 없습니다', { status: 400 });
  if (!env.TICKTICK_CLIENT_ID || !env.TICKTICK_CLIENT_SECRET || !env.LEDGER) {
    return new Response('설정이 없습니다', { status: 404 });
  }
  const body = new URLSearchParams({
    code,
    grant_type: 'authorization_code',
    scope: 'tasks:read tasks:write',
    redirect_uri: redirectUri(env),
  });
  const basic = btoa(`${env.TICKTICK_CLIENT_ID}:${env.TICKTICK_CLIENT_SECRET}`);
  const res = await fetch(TOKEN, {
    method: 'POST',
    headers: { authorization: `Basic ${basic}`,
               'content-type': 'application/x-www-form-urlencoded' },
    body,
  });
  const j = (await res.json()) as Any;
  if (!res.ok || !j.access_token) {
    return new Response(`토큰을 받지 못했습니다 ${res.status}`, { status: 502 });
  }
  await env.LEDGER.put(TOKEN_KEY, JSON.stringify({ token: j.access_token, at: Date.now() }));
  return new Response('틱틱을 이었습니다. 이 창은 닫아도 됩니다.', {
    headers: { 'content-type': 'text/plain; charset=utf-8' },
  });
}

async function token(env: TTEnv): Promise<string | null> {
  // 손으로 넣어 둔 토큰이 먼저다. 틱틱 웹의 설정, 계정, API 토큰에서 받는다
  if (env.TICKTICK_TOKEN) return env.TICKTICK_TOKEN;
  if (!env.LEDGER) return null;
  const t = (await env.LEDGER.get(TOKEN_KEY, 'json')) as Any;
  return t?.token || null;
}

/** 토큰이 통하는지 눈으로 보는 자리.  GET /tt/probe?k=<LEDGER_TOKEN> */
export async function ttProbe(env: TTEnv): Promise<Response> {
  const tok = await token(env);
  const say = (t: string) => new Response(t, {
    headers: { 'content-type': 'text/plain; charset=utf-8' } });
  if (!tok) return say('토큰이 없습니다');
  try {
    const ps = await tt(tok, '/project');
    const names = (ps || []).map((p: Any) => `${p.name} ${p.id}`).join('\n');
    return say(`토큰이 통합니다. 목록 ${(ps || []).length}개\n${names}`);
  } catch (e) {
    return say(`통하지 않습니다\n${e}`);
  }
}

async function tt(tok: string, path: string, init?: RequestInit): Promise<Any> {
  const res = await fetch(`${API}${path}`, {
    ...init,
    headers: {
      authorization: `Bearer ${tok}`,
      'content-type': 'application/json',
      ...(init?.headers || {}),
    },
  });
  if (res.status === 204) return null;
  if (!res.ok) throw new Error(`틱틱 ${path} → ${res.status} ${await res.text()}`);
  const text = await res.text();
  return text ? JSON.parse(text) : null;
}

/* ── 판이 바라는 모습 ─────────────────────────────────────────────────────── */

async function sha1(t: string) {
  const b = new TextEncoder().encode(t);
  const h = await crypto.subtle.digest('SHA-1', b);
  return [...new Uint8Array(h)].map((x) => x.toString(16).padStart(2, '0')).join('');
}
const fp = async (t: string) => (await sha1(t)).slice(0, 8);

const iso = (d: string) => `${d}T00:00:00+0900`;
/** 틱틱은 하루짜리 일정을 협정시로 적는다. 서울로 옮겨 읽어야 날이 맞는다.
    9월 28일 하루짜리는 9월 27일 15시로 저장된다. 앞 열 글자만 자르면 하루가 밀린다. */
const day = (s?: string | null) => {
  if (!s) return null;
  const t = Date.parse(s);
  if (Number.isNaN(t)) return s.slice(0, 10);
  return new Date(t + 9 * 3600 * 1000).toISOString().slice(0, 10);
};

function keyline(content?: string | null): string | null {
  if (!content) return null;
  for (const line of content.split('\n')) {
    const h = line.trim();
    for (const mark of ['로지아 마감 ', '로지아 항목 ', '로지아 ']) {
      if (h.startsWith(mark)) {
        const rest = h.slice(mark.length).trim();
        return mark === '로지아 항목 ' ? `항목:${rest}` : rest;
      }
    }
  }
  return null;
}

function bodymemo(content?: string | null): string {
  const out: string[] = [];
  let hit = false;
  for (const line of (content || '').split('\n')) {
    if (!hit && line.trim().startsWith('로지아 ')) { hit = true; continue; }
    out.push(line);
  }
  return out.join('\n').trim();
}

function stepsOf(item: Any): Any[] {
  const st = item.steps || (item.next ? [item.next] : []);
  return st.map((x: Any) => (typeof x === 'string' ? { t: x } : { ...x }));
}

/* ── 한 회차 ─────────────────────────────────────────────────────────────── */

/** 틱틱이 끝낸 것을 돌려주는 자리가 있는지 두드려 본다. GET /tt/probe2?k= */
export async function ttProbe2(env: TTEnv): Promise<Response> {
  const tok = await token(env);
  if (!tok) return new Response('토큰이 없습니다');
  const paths = [
    `/project/${TODO_PID}/task/6aa9ff658f0824cbeea84358`,
    `/project/${TODO_PID}/task/6aa7b1af8f087a6320f80364`,
  ];
  const out: string[] = [];
  for (const p of paths) {
    try {
      const r = await tt(tok, p);
      out.push(`${p} → 열림 status=${r && r.status} title=${r && r.title}`);
    } catch (e) {
      out.push(`${p} → ${String(e).slice(0, 90)}`);
    }
  }
  return new Response(out.join('\n'), {
    headers: { 'content-type': 'text/plain; charset=utf-8' } });
}

export async function ttSync(env: TTEnv): Promise<string> {
  const tok = await token(env);
  if (!tok || !env.LEDGER || !env.PAGE_KEY || !env.GITHUB_TOKEN) {
    return '틱틱 설정이 없어 건너뜁니다';
  }
  const today = new Date(Date.now() + 9 * 3600 * 1000).toISOString().slice(0, 10);
  const d = await loadData(env);
  const gongo = ((await env.LEDGER.get(JOBS_KEY, 'json')) ?? {}) as Record<string, Any>;

  // 판이 바라는 모습
  const wantParent = new Map<string, Any>();
  const wantTodo = new Map<string, Any>();
  const wantDue = new Map<string, Any>();
  const items = new Map<string, Any>();
  for (const s of d.sections || []) {
    for (const it of s.items || []) {
      items.set(it.id, it);
      const ss = stepsOf(it);
      if (ss.length) wantParent.set(`항목:${it.id}`, {
        title: it.title, kind: it.kind || '항목', sec: s.label || s.id,
      });
      for (const x of ss) {
        wantTodo.set(`${it.id}.${await fp(x.t)}`, {
          t: x.t, due: x.due || null, from: x.from || null,
          memo: x.memo || '', pri: x.pri || 0, tags: x.tags || [],
          item: it.id, title: it.title,
        });
      }
      const dl = it.dates?.deadline;
      if (dl && dl >= today) {
        wantDue.set(`item:${it.id}`, { title: `마감 ${it.title}`, due: dl, tag: '항목', body: '' });
      }
    }
  }
  const vens = new Map<string, Any>();
  for (const g of d.venueGroups || []) {
    for (const v of g.venues || []) {
      vens.set(v.id, v);
      if (v.deadline && v.deadline >= today) {
        wantDue.set(`venue:${v.id}`, {
          title: `낼 곳 마감 ${v.name}`, due: v.deadline, tag: '낼곳', body: v.url || '',
        });
      }
    }
  }
  for (const r of d.repeats || []) {
    const v = vens.get(r.venue) || {};
    wantDue.set(`repeat:${r.venue || ''}`, {
      title: `${r.label} ${v.name || r.venue || ''}`, due: null, tag: '해마다', body: r.note || '',
    });
  }
  for (const [k, v] of Object.entries(gongo)) {
    if (v.deadline && v.deadline >= today) {
      wantDue.set(`gongo:${k}`, {
        title: `공고 ${v.title || ''}`.slice(0, 120), due: v.deadline, tag: '공고', body: v.url || '',
      });
    }
  }

  // 틱틱의 지금
  const todoData = await tt(tok, `/project/${TODO_PID}/data`);
  const dueData = await tt(tok, `/project/${DUE_PID}/data`);
  const cur: Any[] = todoData?.tasks || [];
  const curDue: Any[] = dueData?.tasks || [];
  // 살림. { todo: {과제아이디: 열쇠}, due: {과제아이디: 열쇠} }
  const raw = ((await env.LEDGER.get(SEEN_KEY, 'json')) ?? {}) as Any;
  const seen: { todo: Record<string, Any>; due: Record<string, string> } =
    raw.todo || raw.due
      ? { todo: raw.todo || {}, due: raw.due || {} }
      : { todo: Object.fromEntries(Object.entries(raw as Record<string, string>)
            .map(([k, v]) => [v, k])), due: {} };
  /* 살림의 값은 두 가지 꼴이다. 열쇠만 적힌 옛 꼴과, 열쇠와 지난 값이 함께 적힌
     새 꼴. 옛 꼴은 열쇠만 꺼내 쓰고 값은 없는 것으로 본다. */
  const keyOf = (v: Any) => (typeof v === 'string' ? v : (v && v.k) || null);
  const lastOf = (v: Any) => (typeof v === 'string' ? null : v);

  const done: Any = {}; const add: Any = {}; const edit: Any = {};
  const seen_parent_skip = new Set<string>();
  // 칸 이름과 아이디. 판이 이름을 바꾸면 여기도 함께 바꾼다
  const SECS: Record<string, string> = {};
  for (const sec of d.sections || []) SECS[String(sec.label || sec.id).toLowerCase()] = sec.id;
  SECS['완료'] = 'done';
  const secIdOf = (label: string) => SECS[String(label).toLowerCase()] || '';
  const note: string[] = [];
  const nowSeen: { todo: Record<string, Any>; due: Record<string, string> } =
    { todo: {}, due: {} };

  // 갈래마다 구획 하나. 없으면 만든다
  const column = new Map<string, string>();
  for (const c of todoData?.columns || []) column.set(c.name, c.id);
  for (const [, w] of wantParent) {
    if (column.has(w.kind)) continue;
    const made = await tt(tok, `/project/${TODO_PID}/column`, {
      method: 'POST',
      body: JSON.stringify({ projectId: TODO_PID, name: w.kind, sortOrder: column.size }),
    }).catch(() => null);
    if (made?.id) { column.set(w.kind, made.id); note.push(`구획 세움 ${w.kind}`); }
  }

  const parentId = new Map<string, string>();
  const byTitle = new Map<string, string>();
  for (const [k, w] of wantParent) byTitle.set(w.title, k);
  for (const t of cur) {
    let k = keyline(t.content);
    if (!k) k = keyOf(seen.todo[t.id]);
    if (!k && !t.parentId && byTitle.has(t.title)) k = byTitle.get(t.title)!;
    if (k && k.startsWith('항목:')) parentId.set(k, t.id);
  }

  // 어버이부터 세운다. 하위가 붙을 자리가 있어야 한다
  for (const [k, w] of wantParent) {
    if (parentId.has(k)) continue;
    const made = await tt(tok, '/task', {
      method: 'POST',
      body: JSON.stringify({ projectId: TODO_PID, title: w.title,
                             tags: [w.kind, w.sec, w.title],
                             columnId: column.get(w.kind) }),
    });
    if (made?.id) {
      parentId.set(k, made.id);
      nowSeen.todo[made.id] = k;
      note.push(`항목 세움 ${k.slice(3)}`);
    }
  }

  const here = new Set<string>();
  for (const t of cur) {
    const stamped = keyline(t.content);      // 예전 표시가 남아 있으면 읽는다
    let k = stamped || keyOf(seen.todo[t.id]);
    const isNote = t.kind === 'NOTE';
    // 살림이 비었으면 어버이와 제목으로 짝을 되찾는다
    if (!k && t.parentId) {
      for (const [pk, pid] of parentId) {
        if (t.parentId !== pid) continue;
        const guess = `${pk.slice(3)}.${await fp(t.title || '')}`;
        if (wantTodo.has(guess)) k = guess;
      }
    }
    if (!k && !t.parentId) {
      // 노트는 어버이 밑으로 못 들어간다. 제목의 지문으로 어느 항목인지 되찾는다
      const f = await fp(t.title || '');
      for (const id of items.keys()) {
        if (wantTodo.has(`${id}.${f}`)) { k = `${id}.${f}`; break; }
      }
    }

    if (k && k.startsWith('항목:')) {
      nowSeen.todo[t.id] = k;
      if (stamped) {
        await tt(tok, `/task/${t.id}`, {
          method: 'POST',
          body: JSON.stringify({ id: t.id, projectId: TODO_PID,
                                 content: bodymemo(t.content) }),
        });
      }
      const w = wantParent.get(k);
      if (!w) {
        await tt(tok, `/project/${TODO_PID}/task/${t.id}`, { method: 'DELETE' });
        delete nowSeen.todo[t.id];
        note.push(`항목 거둠 ${k.slice(3)}`);
        continue;
      }
      // 이름과 갈래는 판을 따른다
      const tags: string[] = (t.tags || []).map((x: string) => String(x).toLowerCase());
      // 사람이 칸 태그를 다른 것으로 바꿔 두었으면 판을 그쪽으로 옮긴다
      const secTag = tags.find((x) => SECS[x] && SECS[x] !== secIdOf(w.sec));
      if (secTag) {
        edit[`move:${k.slice(3)}`] = { item: k.slice(3), to: SECS[secTag], at: today };
        note.push(`칸 옮김 ${k.slice(3)} → ${secTag}`);
        seen_parent_skip.add(k);
        continue;
      }
      // 어버이는 태그 셋을 단다. 갈래와 칸과 제 이름
      const want2 = [w.kind, w.sec, w.title].map((x) => String(x).toLowerCase());
      const col = column.get(w.kind);
      if ((t.title || '') !== w.title
          || tags.length !== 3 || want2.some((x) => tags.indexOf(x) < 0)
          || (col && t.columnId !== col)) {
        const body: Any = { id: t.id, projectId: TODO_PID, title: w.title,
                            tags: [w.kind, w.sec, w.title] };
        if (col) body.columnId = col;
        await tt(tok, `/task/${t.id}`, { method: 'POST', body: JSON.stringify(body) });
        note.push(`항목 매만짐 ${k.slice(3)}`);
      }
      continue;
    }

    if (!k) {
      // 틱틱에서 새로 적은 것
      let iid: string | null = null;
      for (const [pk, pid] of parentId) if (t.parentId === pid) iid = pk.slice(3);
      if (!iid) {
        for (const x of t.tags || []) {
          if (items.has(x)) iid = x;
          else for (const [id, it] of items) if ((it.title || '').toLowerCase() === String(x).toLowerCase()) iid = id;
        }
      }
      if (!iid) { note.push(`항목 모름 ${t.title}`); continue; }
      const row: Any = { item: iid, t: t.title || '', at: today };
      if (day(t.dueDate)) row.due = day(t.dueDate);
      if (day(t.startDate) && day(t.startDate) !== day(t.dueDate)) row.from = day(t.startDate);
      if (Number(t.priority || 0)) row.pri = Number(t.priority);
      const memo = (t.content || '').trim();
      if (memo) row.memo = memo;
      add[`tt-${t.id}`] = row;
      nowSeen.todo[t.id] = { k: `${iid}.${await fp(row.t)}`, t: row.t,
                             due: row.due || null, from: row.from || null,
                             memo: row.memo || '', pri: row.pri || 0 };
      note.push(`새 할 일 ${iid}`);
      continue;
    }

    here.add(k);
    nowSeen.todo[t.id] = k;
    const w = wantTodo.get(k);
    if (!w) {
      await tt(tok, `/project/${TODO_PID}/task/${t.id}`, { method: 'DELETE' });
      delete nowSeen.todo[t.id];
      note.push(`판에 없어 거둠 ${k}`);
      continue;
    }
    const memo = bodymemo(t.content);
    // 시작일이 기한과 다르면 기간으로 본다
    const frm = (day(t.startDate) && day(t.startDate) !== day(t.dueDate))
      ? day(t.startDate) : null;
    const pri = Number(t.priority || 0);
    const drop = new Set([w.item, w.title, items.get(w.item)?.kind || '']
      .map((x) => String(x).toLowerCase()));
    const acts: string[] = (t.tags || [])
      .filter((x: string) => !drop.has(String(x).toLowerCase()));
    if (stamped) {
      // 본문에 남은 예전 표시를 걷어 낸다. 메모만 남긴다
      await tt(tok, `/task/${t.id}`, {
        method: 'POST',
        body: JSON.stringify({ id: t.id, projectId: TODO_PID, content: memo }),
      });
    }
    /* 지금 틱틱의 값과 판의 값과 지난 회차에 본 값, 셋을 견준다.
       틱틱이 지난 회차와 달라졌으면 사람이 틱틱에서 고친 것이다. 판으로 보낸다.
       틱틱은 그대로인데 판이 다르면 사람이 판에서 고친 것이다. 틱틱을 고친다.
       지난 값이 없으면 (처음 보는 것) 틱틱을 따른다. */
    const now2 = { t: t.title || '', due: day(t.dueDate), from: frm, memo: memo, pri: pri,
                   tags: acts.slice().sort() };
    const last = lastOf(seen.todo[t.id]);
    const ttMoved = !last
      || last.t !== now2.t || (last.due || null) !== now2.due
      || (last.from || null) !== now2.from || (last.memo || '') !== now2.memo
      || (last.pri || 0) !== now2.pri
      || (last.tags || []).join(',') !== now2.tags.join(',');
    const boardDiff = w.t !== now2.t || (w.due || null) !== now2.due
      || (w.from || null) !== now2.from || (w.memo || '') !== now2.memo
      || (w.pri || 0) !== now2.pri
      || (w.tags || []).slice().sort().join(',') !== now2.tags.join(',');

    if (boardDiff && ttMoved) {
      // 틱틱에서 고쳤다. 판으로 보낸다
      const row: Any = { item: w.item, t: now2.t, at: today };
      if (now2.due) row.due = now2.due;
      if (now2.from) row.from = now2.from;
      if (now2.memo !== (w.memo || '')) row.memo = now2.memo;
      if (now2.pri !== (w.pri || 0)) row.pri = now2.pri;
      if (now2.tags.join(',') !== (w.tags || []).slice().sort().join(',')) row.tags = now2.tags;
      edit[k] = row;
      note.push(`틱틱에서 고침 ${k}`);
      if (now2.t !== w.t) {
        nowSeen.todo[t.id] = { k: `${w.item}.${await fp(now2.t)}`, ...now2 };
        continue;
      }
    } else if (boardDiff) {
      // 판에서 고쳤다. 틱틱을 판에 맞춘다
      const body: Any = { id: t.id, projectId: TODO_PID, title: w.t,
                          content: w.memo || '', priority: w.pri || 0,
                          tags: (w.tags || []) };
      if (w.due) { body.dueDate = iso(w.due); body.isAllDay = true; body.timeZone = 'Asia/Seoul'; }
      if (w.from) { body.startDate = iso(w.from); body.isAllDay = true; body.timeZone = 'Asia/Seoul'; }
      await tt(tok, `/task/${t.id}`, { method: 'POST', body: JSON.stringify(body) });
      nowSeen.todo[t.id] = { k: k, t: w.t, due: w.due || null, from: w.from || null,
                             memo: w.memo || '', pri: w.pri || 0,
                             tags: (w.tags || []).slice().sort(), rem: true };
      note.push(`판에서 고침 ${k}`);
      continue;
    }
    /* 날짜가 붙었는데 알림이 없고 아직 한 번도 걸어 본 적 없으면 지금 건다.
       한 번 걸고 나면 살림에 표를 남겨, 사람이 지운 알림을 되살리지 않는다. */
    const marked = last && last.rem;
    if (now2.due && !marked && !(t.reminders || []).length) {
      await tt(tok, `/task/${t.id}`, {
        method: 'POST',
        body: JSON.stringify({ id: t.id, projectId: TODO_PID, reminders: REMIND }),
      });
      note.push(`알림 ${k}`);
    }
    nowSeen.todo[t.id] = { k: k, ...now2, rem: true };
    if (!isNote && !t.parentId) {
      const pid = parentId.get(`항목:${w.item}`);
      if (pid) {
        await tt(tok, `/task/${t.id}`, {
          method: 'POST',
          body: JSON.stringify({ id: t.id, projectId: TODO_PID, parentId: pid }),
        });
      }
    } else if (!isNote && t.parentId === parentId.get(`항목:${w.item}`)) {
      // 어버이가 이미 말하는 것을 태그가 되풀이할 까닭이 없다
      const keep = acts;
      if (keep.length !== (t.tags || []).length) {
        await tt(tok, `/task/${t.id}`, {
          method: 'POST',
          body: JSON.stringify({ id: t.id, projectId: TODO_PID, tags: keep }),
        });
      }
    }
  }

  // 지난 회차에 보던 과제가 이번에 안 보이면 체크했거나 지운 것이다
  /* 지난 회차에 보이던 과제가 이번에 안 보이면 하나씩 다시 불러 가린다.
     status 2 는 체크, 0 은 휴지통이다. 불러지지 않으면 손대지 않는다. */
  const gone = new Map<string, string>();     // 열쇠 → 'done' 또는 'trash'
  for (const [id, v] of Object.entries(seen.todo)) {
    const k0 = keyOf(v);
    if (!k0 || cur.some((t: Any) => t.id === id)) continue;
    try {
      const one = await tt(tok, `/project/${TODO_PID}/task/${id}`);
      gone.set(k0, (one && (one.status === 2 || one.completedTime)) ? 'done' : 'trash');
    } catch {
      gone.set(k0, 'done');
    }
  }

  // 없던 할 일을 만든다
  for (const [k, w] of wantTodo) {
    if (here.has(k)) continue;
    if (gone.get(k) === 'done') { done[k] = { at: today }; note.push(`체크 ${k}`); continue; }
    if (gone.get(k) === 'trash') {
      edit[k] = { item: w.item, t: w.t, del: true, at: today };
      note.push(`틱틱에서 지움 ${k}`);
      continue;
    }
    const body: Any = {
      projectId: TODO_PID, title: w.t, content: w.memo || '',
      priority: w.pri || 0, tags: w.tags || [],
    };
    const pid = parentId.get(`항목:${w.item}`);
    if (pid) body.parentId = pid;
    if (w.due) {
      body.dueDate = iso(w.due); body.isAllDay = true; body.timeZone = 'Asia/Seoul';
      body.reminders = REMIND;
    }
    if (w.from) { body.startDate = iso(w.from); body.isAllDay = true; body.timeZone = 'Asia/Seoul'; }
    const made = await tt(tok, '/task', { method: 'POST', body: JSON.stringify(body) });
    if (made?.id) {
      nowSeen.todo[made.id] = { k: k, t: w.t, due: w.due || null,
                                from: w.from || null, memo: w.memo || '', pri: w.pri || 0,
                                tags: (w.tags || []).slice().sort() };
    }
    note.push(`할 일 세움 ${k}`);
  }

  /* 접수함. 여기 적은 한 줄이 판의 새 항목이 된다.
     아이디는 제목에서 만든다. 라틴 글자가 없으면 시각으로 짓는다.
     심고 나면 접수함에서 거둔다. 판에 서면 할 일 목록에 어버이로 다시 나타난다. */
  try {
    const inbox = await tt(tok, `/project/${IN_PID}/data`);
    const rows: Any = {};
    for (const t of inbox?.tasks || []) {
      const title = (t.title || '').trim();
      if (!title) continue;
      const slug = title.toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/^-|-$/g, '');
      const id = (slug && slug.length > 2 ? slug : `new-${Date.now().toString(36)}`).slice(0, 24);
      const row: Any = { title, at: today };
      const memo = (t.content || '').trim();
      if (memo) row.note = memo;
      if (day(t.dueDate)) row.deadline = day(t.dueDate);
      const tag = (t.tags || [])[0];
      if (tag) row.kind = tag;
      rows[id] = row;
      await tt(tok, `/project/${IN_PID}/task/${t.id}`, { method: 'DELETE' });
      note.push(`새 항목 ${id}`);
    }
    if (Object.keys(rows).length) {
      const nowSeed: Any = (await env.LEDGER.get(SEED_KEY, 'json')) ?? {};
      for (const [k, v] of Object.entries(rows)) nowSeed[k] = v;
      await env.LEDGER.put(SEED_KEY, JSON.stringify(nowSeed));
    }
  } catch (e) {
    note.push(`접수함을 읽지 못했습니다`);
  }

  // 마감 판. 비추기만 한다
  const hereDue = new Set<string>();
  const dueByTitle = new Map<string, string>();
  for (const [k, w] of wantDue) dueByTitle.set(w.title, k);
  for (const t of curDue) {
    const stamped = keyline(t.content);
    const k = stamped || seen.due[t.id] || dueByTitle.get(t.title) || null;
    if (!k) continue;
    const w = wantDue.get(k);
    if (!w) {
      await tt(tok, `/project/${DUE_PID}/task/${t.id}`, { method: 'DELETE' });
      continue;
    }
    hereDue.add(k);
    nowSeen.due[t.id] = k;
    if (stamped) {
      await tt(tok, `/task/${t.id}`, {
        method: 'POST',
        body: JSON.stringify({ id: t.id, projectId: DUE_PID,
                               content: w.body || '' }),
      });
    }
    if ((t.title || '') !== w.title || day(t.dueDate) !== w.due) {
      const body: Any = { id: t.id, projectId: DUE_PID, title: w.title };
      if (w.due) { body.dueDate = iso(w.due); body.isAllDay = true; body.timeZone = 'Asia/Seoul'; }
      await tt(tok, `/task/${t.id}`, { method: 'POST', body: JSON.stringify(body) });
    }
  }
  for (const [k, w] of wantDue) {
    if (hereDue.has(k)) continue;
    const body: Any = {
      projectId: DUE_PID, title: w.title, tags: [w.tag], content: w.body || '',
    };
    if (w.due) {
      body.dueDate = iso(w.due); body.isAllDay = true; body.timeZone = 'Asia/Seoul';
      body.reminders = REMIND;
    }
    const made = await tt(tok, '/task', { method: 'POST', body: JSON.stringify(body) });
    if (made?.id) nowSeen.due[made.id] = k;
  }

  // 장부에 적는다. 같은 시계에 도는 flush 가 데이터로 옮긴다
  for (const [key, rows] of [[DONE_KEY, done], [ADD_KEY, add], [EDIT_KEY, edit]] as const) {
    if (!Object.keys(rows).length) continue;
    const now: Any = (await env.LEDGER.get(key, 'json')) ?? {};
    for (const [k, v] of Object.entries(rows)) now[k] = v;
    await env.LEDGER.put(key, JSON.stringify(now));
  }
  await env.LEDGER.put(SEEN_KEY, JSON.stringify(nowSeen));
  await env.LEDGER.put(HEALTH_KEY, JSON.stringify({ at: Date.now(), ok: true }));

  return note.length ? `틱틱 ${note.join(', ').slice(0, 300)}` : '틱틱 맞출 것이 없습니다';
}
