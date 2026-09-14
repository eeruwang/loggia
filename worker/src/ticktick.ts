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

   체크를 알아보는 법
     틱틱의 공개 API 에는 끝낸 것을 돌려주는 자리가 없다. 그래서 지난 회차에
     보았던 열쇠가 이번에 안 보이면 체크한 것으로 친다. 틱틱에서 과제를 지워도
     같은 자리로 들어온다. 지우는 것과 체크하는 것을 가리지 못한다.
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
const JOBS_KEY = 'jobs';
const DONE_KEY = 'board';
const ADD_KEY = 'added';
const EDIT_KEY = 'edited';

const TODO_PID = '6aa7ae1d8f084b19082e331e';
const DUE_PID = '6aa7ae1f8f081102b5324922';
const API = 'https://api.ticktick.com/open/v1';
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
const day = (s?: string | null) => (s ? s.slice(0, 10) : null);

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

function restamp(content: string | null | undefined, marker: string): string {
  const lines = (content || '').split('\n');
  const out: string[] = [];
  let hit = false;
  for (const line of lines) {
    if (!hit && line.trim().startsWith('로지아 ')) { out.push(marker); hit = true; }
    else out.push(line);
  }
  if (!hit) return [marker, ...out.filter((x) => x.trim())].join('\n').trim();
  return out.join('\n').trim();
}

function stepsOf(item: Any): Any[] {
  const st = item.steps || (item.next ? [item.next] : []);
  return st.map((x: Any) => (typeof x === 'string' ? { t: x } : { ...x }));
}

/* ── 한 회차 ─────────────────────────────────────────────────────────────── */

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
      if (ss.length) wantParent.set(`항목:${it.id}`, { title: it.title, kind: it.kind || '항목' });
      for (const x of ss) {
        wantTodo.set(`${it.id}.${await fp(x.t)}`, {
          t: x.t, due: x.due || null, memo: x.memo || '', item: it.id, title: it.title,
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
  const seen = ((await env.LEDGER.get(SEEN_KEY, 'json')) ?? {}) as Record<string, string>;

  const done: Any = {}; const add: Any = {}; const edit: Any = {};
  const note: string[] = [];
  const nowSeen: Record<string, string> = {};

  const parentId = new Map<string, string>();
  for (const t of cur) {
    const k = keyline(t.content);
    if (k && k.startsWith('항목:')) parentId.set(k, t.id);
  }

  // 어버이부터 세운다. 하위가 붙을 자리가 있어야 한다
  for (const [k, w] of wantParent) {
    if (parentId.has(k)) continue;
    const made = await tt(tok, '/task', {
      method: 'POST',
      body: JSON.stringify({ projectId: TODO_PID, title: w.title,
                             content: `로지아 항목 ${k.slice(3)}`, tags: [w.kind] }),
    });
    if (made?.id) { parentId.set(k, made.id); note.push(`항목 세움 ${k.slice(3)}`); }
  }

  const here = new Set<string>();
  for (const t of cur) {
    const k = keyline(t.content);
    const isNote = t.kind === 'NOTE';

    if (k && k.startsWith('항목:')) {
      const w = wantParent.get(k);
      if (!w) {
        await tt(tok, `/project/${TODO_PID}/task/${t.id}`, { method: 'DELETE' });
        note.push(`항목 거둠 ${k.slice(3)}`);
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
      const memo = (t.content || '').trim();
      if (memo) row.memo = memo;
      add[`tt-${t.id}`] = row;
      const nk = `${iid}.${await fp(row.t)}`;
      await tt(tok, `/task/${t.id}`, {
        method: 'POST',
        body: JSON.stringify({ id: t.id, projectId: TODO_PID,
                               content: restamp(t.content, `로지아 ${nk}`) }),
      });
      nowSeen[nk] = t.id;
      note.push(`새 할 일 ${iid}`);
      continue;
    }

    here.add(k);
    nowSeen[k] = t.id;
    const w = wantTodo.get(k);
    if (!w) {
      await tt(tok, `/project/${TODO_PID}/task/${t.id}`, { method: 'DELETE' });
      note.push(`판에 없어 거둠 ${k}`);
      continue;
    }
    const memo = bodymemo(t.content);
    if ((t.title || '') !== w.t) {
      const row: Any = { item: w.item, t: t.title, at: today };
      if (day(t.dueDate)) row.due = day(t.dueDate);
      if (memo !== (w.memo || '')) row.memo = memo;
      edit[k] = row;
      const nk = `${w.item}.${await fp(t.title)}`;
      await tt(tok, `/task/${t.id}`, {
        method: 'POST',
        body: JSON.stringify({ id: t.id, projectId: TODO_PID,
                               content: restamp(t.content, `로지아 ${nk}`) }),
      });
      delete nowSeen[k]; nowSeen[nk] = t.id;
      note.push(`글 고침 ${k}`);
      continue;
    }
    if (day(t.dueDate) !== w.due || memo !== (w.memo || '')) {
      const row: Any = { item: w.item, t: w.t, at: today };
      if (day(t.dueDate)) row.due = day(t.dueDate);
      if (memo !== (w.memo || '')) row.memo = memo;
      edit[k] = row;
      note.push(`고침 ${k}`);
    }
    if (!isNote && !t.parentId) {
      const pid = parentId.get(`항목:${w.item}`);
      if (pid) {
        await tt(tok, `/task/${t.id}`, {
          method: 'POST',
          body: JSON.stringify({ id: t.id, projectId: TODO_PID, parentId: pid }),
        });
      }
    }
  }

  // 없던 할 일을 만든다
  for (const [k, w] of wantTodo) {
    if (here.has(k)) continue;
    // 지난 회차에 보았는데 이번에 안 보이면 체크했거나 지운 것이다
    if (seen[k]) { done[k] = { at: today }; note.push(`체크 ${k}`); continue; }
    const body: Any = {
      projectId: TODO_PID, title: w.t,
      content: `로지아 ${k}` + (w.memo ? `\n\n${w.memo}` : ''),
    };
    const pid = parentId.get(`항목:${w.item}`);
    if (pid) body.parentId = pid;
    if (w.due) { body.dueDate = iso(w.due); body.isAllDay = true; body.timeZone = 'Asia/Seoul'; }
    const made = await tt(tok, '/task', { method: 'POST', body: JSON.stringify(body) });
    if (made?.id) nowSeen[k] = made.id;
    note.push(`할 일 세움 ${k}`);
  }

  // 마감 판. 비추기만 한다
  const hereDue = new Set<string>();
  for (const t of curDue) {
    const k = keyline(t.content);
    if (!k) continue;
    const w = wantDue.get(k);
    if (!w) {
      await tt(tok, `/project/${DUE_PID}/task/${t.id}`, { method: 'DELETE' });
      continue;
    }
    hereDue.add(k);
    if ((t.title || '') !== w.title || day(t.dueDate) !== w.due) {
      const body: Any = { id: t.id, projectId: DUE_PID, title: w.title };
      if (w.due) { body.dueDate = iso(w.due); body.isAllDay = true; body.timeZone = 'Asia/Seoul'; }
      await tt(tok, `/task/${t.id}`, { method: 'POST', body: JSON.stringify(body) });
    }
  }
  for (const [k, w] of wantDue) {
    if (hereDue.has(k)) continue;
    const body: Any = {
      projectId: DUE_PID, title: w.title, tags: [w.tag],
      content: `로지아 마감 ${k}` + (w.body ? `\n${w.body}` : ''),
    };
    if (w.due) { body.dueDate = iso(w.due); body.isAllDay = true; body.timeZone = 'Asia/Seoul'; }
    await tt(tok, '/task', { method: 'POST', body: JSON.stringify(body) });
  }

  // 장부에 적는다. 같은 시계에 도는 flush 가 데이터로 옮긴다
  for (const [key, rows] of [[DONE_KEY, done], [ADD_KEY, add], [EDIT_KEY, edit]] as const) {
    if (!Object.keys(rows).length) continue;
    const now: Any = (await env.LEDGER.get(key, 'json')) ?? {};
    for (const [k, v] of Object.entries(rows)) now[k] = v;
    await env.LEDGER.put(key, JSON.stringify(now));
  }
  await env.LEDGER.put(SEEN_KEY, JSON.stringify(nowSeen));

  return note.length ? `틱틱 ${note.join(', ').slice(0, 300)}` : '틱틱 맞출 것이 없습니다';
}
