/* =============================================================================
   flush.ts — 사이트에서 체크하거나 추가한 것을 데이터에 직접 반영한다.

   예전에는 이 일을 사람이 했다. 사이트에서 체크박스를 누르면 워커의 KV 에
   쌓이고, 다음 갱신 때 사람이 그걸 읽어 JSON 에 옮기고 다시 올렸다.
   이제 워커가 10분마다 깨어나 스스로 한다.

   순서
     KV 를 읽는다 → 비었으면 아무것도 안 한다
     깃허브에서 public/data.enc 를 받아 푼다
     끝낸 할 일을 빼고, 수정과 삭제를 적용하고, 추가한 할 일을 넣는다
     다시 암호화하고 아침 메일 요약도 새로 만든다
     둘을 한 커밋으로 올린다
     그 다음에 KV 를 비운다

   KV 를 마지막에 비우는 게 중요하다. 먼저 비우면 올리다 실패했을 때 사용자가
   체크한 게 사라진다. 나중에 비우면 최악의 경우 다음 번에 한 번 더 반영할 뿐이고,
   같은 걸 두 번 반영해도 결과는 같다.

   워커는 암호를 모른다. 암호에서 뽑아 놓은 키를 그대로 받는다.
   까닭이 둘이다. 하나, 클라우드플레어 Workers 는 PBKDF2 반복을 10만 번까지만
   허용하는데 이 보드는 60만 번을 쓴다. 둘, 그래야 사람이 기억하는 암호가
   클라우드플레어에 남지 않는다.

   그 대신 솔트를 고정한다. 솔트가 바뀌면 뽑아 둔 키가 안 맞기 때문이다.
   publish.sh 도 다시 암호화할 때 있던 솔트를 그대로 쓴다. 솔트는 비밀이 아니고
   암호가 길기 때문에 같은 값을 계속 써도 안전하다. 덤으로 브라우저가 세션에
   넣어 둔 키가 갱신 뒤에도 살아 있어 다시 열 때 기다림이 없다.

   설정이 하나라도 없으면 조용히 건너뛴다. 그래서 시크릿을 넣기 전에 배포해도
   아무 일도 일어나지 않는다.
   ========================================================================== */

export interface FlushEnv {
  LEDGER?: KVNamespace;
  PAGE_KEY?: string;          // 비밀. 암호에서 뽑은 32바이트 키를 base64 로
  GITHUB_TOKEN?: string;      // 비밀. 저장소에 쓴다
  GITHUB_REPO?: string;       // "eeruwang/loggia"
  GITHUB_API?: string;        // 시험할 때만 바꾼다. 평소에는 비워 둔다
  DIGEST_KEY?: string;
}

const DATA_PATH = 'public/data.enc';
const DIGEST_PATH = 'digest.enc';
const BRANCH = 'main';

const DONE_KEY = 'board';
const ADD_KEY = 'added';
const EDIT_KEY = 'edited';

type Any = Record<string, any>;

/* ── 바이트와 글자 ─────────────────────────────────────────────────────────── */

/** base64 를 바이트로. 어디가 잘못됐는지 말해 주려고 이름을 함께 받는다. */
function toBytes(b64: string, what = '값'): Uint8Array {
  const clean = String(b64).trim().replace(/\s+/g, '')
    .replace(/-/g, '+').replace(/_/g, '/');
  if (!/^[A-Za-z0-9+/]*={0,2}$/.test(clean)) {
    const bad = (clean.match(/[^A-Za-z0-9+/=]/g) || []).slice(0, 5).join(' ');
    throw new Error(
      `${what} 이(가) base64 가 아닙니다. 쓸 수 없는 글자: ${bad}\n`
      + '보드 암호를 그대로 넣으신 것은 아닌지 보세요. '
      + 'PAGE_KEY 는 암호가 아니라 암호에서 뽑은 44글자 base64 입니다. '
      + 'node tools/pagekey.js public/data.enc "<암호>" 로 뽑습니다.');
  }
  let raw: string;
  try {
    raw = atob(clean);
  } catch (e) {
    throw new Error(`${what} 을(를) base64 로 읽지 못했습니다 (길이 ${clean.length}).`);
  }
  const out = new Uint8Array(raw.length);
  for (let i = 0; i < raw.length; i++) out[i] = raw.charCodeAt(i);
  return out;
}

function toB64(buf: ArrayBuffer | Uint8Array): string {
  const a = buf instanceof Uint8Array ? buf : new Uint8Array(buf);
  let s = '';
  for (let i = 0; i < a.length; i++) s += String.fromCharCode(a[i]);
  return btoa(s);
}

/** 할 일의 키. 화면과 파이썬 도구와 셋이 같은 값을 내야 한다. */
async function fingerprint(text: string): Promise<string> {
  const h = await crypto.subtle.digest('SHA-1', new TextEncoder().encode(text));
  return [...new Uint8Array(h)].map((x) => x.toString(16).padStart(2, '0'))
    .join('').slice(0, 8);
}

/* ── 자물쇠 ────────────────────────────────────────────────────────────────── */

/** loggia1.<솔트>.<초기값>.<암호문+태그> 를 푼다. 솔트를 함께 돌려준다. */
async function unseal(text: string, key: CryptoKey) {
  const p = text.trim().split('.');
  if (p[0] !== 'loggia1' || p.length !== 4) throw new Error('data.enc 형식이 낯섭니다');
  const salt = toBytes(p[1], 'data.enc 의 솔트');
  let plain: ArrayBuffer;
  try {
    plain = await crypto.subtle.decrypt(
      { name: 'AES-GCM', iv: toBytes(p[2], 'data.enc 의 초기값') },
      key, toBytes(p[3], 'data.enc 의 본문'));
  } catch (e) {
    throw new Error('PAGE_KEY 로 열리지 않습니다. 솔트가 바뀌었거나 키가 틀렸습니다. '
      + 'node tools/pagekey.js public/data.enc "<암호>" 로 다시 뽑아 주세요.');
  }
  return { data: JSON.parse(new TextDecoder().decode(plain)) as Any, salt };
}

/** 같은 솔트, 새 초기값으로 다시 암호화한다. */
async function seal(obj: Any, key: CryptoKey, salt: Uint8Array): Promise<string> {
  const iv = crypto.getRandomValues(new Uint8Array(12));
  const body = new TextEncoder().encode(JSON.stringify(obj, null, 1));
  const blob = await crypto.subtle.encrypt({ name: 'AES-GCM', iv }, key, body);
  return ['loggia1', toB64(salt), toB64(iv), toB64(blob)].join('.') + '\n';
}

/** 아침 메일 요약. 원본 키로 봉하므로 반복 계산이 없다. */
async function rawSeal(obj: Any, keyB64: string): Promise<string> {
  const key = await crypto.subtle.importKey(
    'raw', toBytes(keyB64, 'DIGEST_KEY'), { name: 'AES-GCM' }, false, ['encrypt']);
  const iv = crypto.getRandomValues(new Uint8Array(12));
  const body = new TextEncoder().encode(JSON.stringify(obj));
  const blob = await crypto.subtle.encrypt({ name: 'AES-GCM', iv }, key, body);
  return ['loggiaR1', toB64(iv), toB64(blob)].join('.') + '\n';
}

/* ── 데이터 만지기 ─────────────────────────────────────────────────────────── */

type Todo = { t: string; due?: string };

function todosOf(item: Any): Todo[] {
  const st = item.steps || (item.next ? [item.next] : []);
  return st.map((x: any) => (typeof x === 'string' ? { t: x } : { t: x.t, due: x.due }));
}

function putTodos(item: Any, ss: Todo[]) {
  if (!ss.length) delete item.steps;
  else item.steps = ss.map((s) => (s.due ? { t: s.t, due: s.due } : s.t));
  delete item.next;
}

function findItem(d: Any, id: string): Any | null {
  for (const s of d.sections || []) for (const it of s.items || []) if (it.id === id) return it;
  for (const it of d.archive || []) if (it.id === id) return it;
  return null;
}

/** 마지막 작업일은 뒤로 되돌리지 않는다. */
function touch(item: Any, when: string) {
  item.dates = item.dates || {};
  if (!item.dates.touched || item.dates.touched < when) item.dates.touched = when;
}

/* ── 아침 메일 요약 만들기 ─────────────────────────────────────────────────── */
/* tools/build.py 의 digest_json 과 같은 것을 낸다. 데이터가 바뀌었는데 요약이
   그대로면 다음 날 아침 메일이 이미 끝낸 할 일을 다시 말한다. */

function buildDigest(d: Any): Any {
  const venues: Any = {};
  for (const g of d.venueGroups || []) for (const v of g.venues || []) venues[v.id] = v;
  const vname = (id: string) => (venues[id] || {}).name || '';

  const due: Any[] = [], doing: Any[] = [], wait: Any[] = [], quiet: Any[] = [];
  for (const sec of d.sections || []) {
    for (const it of sec.items || []) {
      const dt = it.dates || {};
      const st = (d.statuses || {})[it.status] || {};
      const ss = todosOf(it);
      const base = { t: it.title, v: vname(it.venue) };
      if (dt.deadline) due.push({ ...base, due: dt.deadline, step: ss.length ? ss[0].t : '' });
      if (sec.id === 'now' && ss.length) {
        doing.push({
          ...base, step: ss[0].t, due: ss[0].due || dt.deadline || '',
          pum: ((d.efforts || {})[it['품']] || {}).label || '',
        });
      }
      if (dt.sent && st.tone === 'wait') {
        const v = venues[it.venue] || {};
        const row: Any = { ...base, sent: dt.sent };
        if (v['답까지']) row.until = v['답까지'];
        wait.push(row);
      } else if (dt.touched) {
        quiet.push({ ...base, touched: dt.touched });
      }
    }
  }

  const reps = (d.repeats || []).map((r: Any) => ({
    m: r.months, day: r.day === undefined ? '말일' : r.day,
    t: r.label, v: vname(r.venue), guess: !!r['짐작'],
  }));

  const log: Any[] = [];
  const all = [...(d.sections || []).flatMap((s: Any) => s.items || []), ...(d.archive || [])];
  for (const it of all) {
    for (const [k, lab] of [['sent', '냈다'], ['decided', '끝났다'], ['touched', '손댔다']]) {
      const v = (it.dates || {})[k];
      if (v && v.length === 10) log.push({ d: v, k: lab, t: it.title });
    }
  }

  return {
    built: d.meta.updated,
    site: d.meta.site || 'https://loggia.moonilsun.com/',
    due: due.slice().sort((a, b) => (a.due < b.due ? -1 : a.due > b.due ? 1 : 0)),
    doing, wait, quiet, repeats: reps, log,
    compass: (d.compass || {}).lines || [],
  };
}

/* ── 깃허브 ────────────────────────────────────────────────────────────────── */

async function gh(env: FlushEnv, path: string, init?: RequestInit): Promise<any> {
  const base = env.GITHUB_API || 'https://api.github.com';
  const res = await fetch(`${base}${path}`, {
    ...init,
    headers: {
      authorization: `Bearer ${env.GITHUB_TOKEN}`,
      accept: 'application/vnd.github+json',
      'user-agent': 'loggia-worker',
      'content-type': 'application/json',
      ...(init?.headers || {}),
    },
  });
  if (!res.ok) throw new Error(`깃허브 ${path} → ${res.status} ${await res.text()}`);
  return res.json();
}

/** 파일 둘을 한 커밋으로 올린다. 따로 올리면 커밋이 두 개 쌓인다. */
async function commitFiles(env: FlushEnv, repo: string, files: { path: string; text: string }[],
                           message: string): Promise<string> {
  const ref = await gh(env, `/repos/${repo}/git/ref/heads/${BRANCH}`);
  const parent = ref.object.sha;
  const base = await gh(env, `/repos/${repo}/git/commits/${parent}`);

  const tree: Any[] = [];
  for (const f of files) {
    const blob = await gh(env, `/repos/${repo}/git/blobs`, {
      method: 'POST', body: JSON.stringify({ content: f.text, encoding: 'utf-8' }),
    });
    tree.push({ path: f.path, mode: '100644', type: 'blob', sha: blob.sha });
  }
  const newTree = await gh(env, `/repos/${repo}/git/trees`, {
    method: 'POST', body: JSON.stringify({ base_tree: base.tree.sha, tree }),
  });
  const commit = await gh(env, `/repos/${repo}/git/commits`, {
    method: 'POST',
    body: JSON.stringify({ message, tree: newTree.sha, parents: [parent] }),
  });
  await gh(env, `/repos/${repo}/git/refs/heads/${BRANCH}`, {
    method: 'PATCH', body: JSON.stringify({ sha: commit.sha }),
  });
  return commit.sha.slice(0, 7);
}

/* ── 반영하기 ──────────────────────────────────────────────────────────────── */

export async function flush(env: FlushEnv): Promise<string> {
  if (!env.LEDGER || !env.PAGE_KEY || !env.GITHUB_TOKEN) {
    return '설정이 없어 건너뜁니다 (PAGE_KEY 와 GITHUB_TOKEN 이 필요합니다)';
  }
  const repo = env.GITHUB_REPO || 'eeruwang/loggia';

  // 잘못 넣은 값은 여기서 잡는다. 깃허브를 부르기 전에 알아야 헛걸음이 없다.
  const rawKey = toBytes(env.PAGE_KEY, 'PAGE_KEY');
  if (rawKey.length !== 32) {
    throw new Error(`PAGE_KEY 는 32바이트여야 하는데 ${rawKey.length}바이트입니다. `
      + '앞뒤에 딴 글자가 붙지 않았는지 보세요. 제대로 된 값은 44글자이고 = 로 끝납니다.');
  }

  const done: Any = (await env.LEDGER.get(DONE_KEY, 'json')) ?? {};
  const add: Any = (await env.LEDGER.get(ADD_KEY, 'json')) ?? {};
  const edit: Any = (await env.LEDGER.get(EDIT_KEY, 'json')) ?? {};
  if (!Object.keys(done).length && !Object.keys(add).length && !Object.keys(edit).length) {
    return '반영할 것이 없습니다';
  }

  // 데이터를 받아 푼다. 커밋에 붙일 부모는 commitFiles 가 그때 다시 읽는다
  const meta = await gh(env, `/repos/${repo}/contents/${DATA_PATH}?ref=${BRANCH}`);
  const text = new TextDecoder().decode(toBytes(String(meta.content), '깃허브가 준 파일'));
  const key = await crypto.subtle.importKey(
    'raw', rawKey, { name: 'AES-GCM' }, false, ['encrypt', 'decrypt']);
  const { data, salt } = await unseal(text, key);

  const today = new Date(Date.now() + 9 * 3600 * 1000).toISOString().slice(0, 10);
  const touched: Record<string, string> = {};
  const usedAdd = new Set<string>();
  const doneKeys = Object.keys(done);
  const addKeys: string[] = [];
  const note: string[] = [];

  // 추가하자마자 체크한 것. 할 일에 넣지 않고 버린다
  for (const k of doneKeys) {
    if (!k.startsWith('add:')) continue;
    const ak = k.slice(4);
    usedAdd.add(ak);
    if (add[ak]) addKeys.push(ak);
    const id = (add[ak] || {}).item;
    const when = (done[k] || {}).at || (add[ak] || {}).at || today;
    if (id && findItem(data, id)) {
      touched[id] = touched[id] > when ? touched[id] : when;
      note.push(`제외 ${id}`);
    }
  }

  // 체크해서 끝냈다고 표시한 할 일
  for (const k of doneKeys) {
    if (k.startsWith('add:') || !k.includes('.')) continue;
    const i = k.lastIndexOf('.');
    const id = k.slice(0, i), fp = k.slice(i + 1);
    const it = findItem(data, id);
    const when = (done[k] || {}).at || today;
    if (!it) { note.push(`못 찾음 ${id}`); continue; }
    touched[id] = touched[id] > when ? touched[id] : when;
    const ss = todosOf(it);
    const keep: Todo[] = [];
    let hit = false;
    for (const s of ss) {
      if (!hit && (await fingerprint(s.t)) === fp) { hit = true; continue; }
      keep.push(s);
    }
    if (hit) { putTodos(it, keep); note.push(`완료 ${id}`); }
    else note.push(`건너뜀 ${id}`);
  }

  // 수정하거나 삭제한 할 일. 키는 처음 글로 만든 것이라 원본에서 그대로 찾힌다.
  // 끝냈다고 표시한 것을 먼저 뺐으므로, 이미 없어진 것은 그냥 넘어간다.
  const editKeys = Object.keys(edit);
  for (const k of editKeys) {
    const e = edit[k];
    const i = k.lastIndexOf('.');
    if (i < 0) continue;
    const id = e.item || k.slice(0, i), fp = k.slice(i + 1);
    const it = findItem(data, id);
    const when = e.at || today;
    if (!it) { note.push(`못 찾음 ${id}`); continue; }
    touched[id] = touched[id] > when ? touched[id] : when;
    const ss = todosOf(it);
    const out: Todo[] = [];
    let hit = false;
    for (const s of ss) {
      if (!hit && (await fingerprint(s.t)) === fp) {
        hit = true;
        if (e.del) continue;                       // 삭제
        out.push(e.due ? { t: e.t, due: e.due } : { t: e.t });
        continue;
      }
      out.push(s);
    }
    if (hit) { putTodos(it, out); note.push(`${e.del ? '삭제' : '수정'} ${id}`); }
    else note.push(`건너뜀 ${id}`);
  }

  // 사이트에서 직접 적어 넣은 할 일
  for (const ak of Object.keys(add)) {
    if (usedAdd.has(ak)) continue;
    addKeys.push(ak);
    const a = add[ak];
    const it = a.item ? findItem(data, a.item) : null;
    if (!it) { note.push(`못 찾음 ${a.item || '?'}`); continue; }
    const when = a.at || today;
    touched[a.item] = touched[a.item] > when ? touched[a.item] : when;
    const ss = todosOf(it);
    ss.push(a.due ? { t: a.t, due: a.due } : { t: a.t });
    putTodos(it, ss);
    note.push(`추가 ${a.item}`);
  }

  for (const [id, when] of Object.entries(touched)) {
    const it = findItem(data, id);
    if (it) touch(it, when);
  }
  data.meta = data.meta || {};
  data.meta.updated = today;

  // 다시 암호화해서 요약과 함께 한 커밋으로 올린다
  const files = [{ path: DATA_PATH, text: await seal(data, key, salt) }];
  if (env.DIGEST_KEY) {
    files.push({ path: DIGEST_PATH, text: await rawSeal(buildDigest(data), env.DIGEST_KEY) });
  }
  const msg = `사이트에서 한 것 반영 · ${note.join(', ') || '없음'}`;
  const sha = await commitFiles(env, repo, files, msg.slice(0, 200));

  // 올린 다음에 비운다. 읽어 온 키만 지우므로 그 사이에 누른 것은 남는다
  if (doneKeys.length) {
    const now: Any = (await env.LEDGER.get(DONE_KEY, 'json')) ?? {};
    for (const k of doneKeys) delete now[k];
    await env.LEDGER.put(DONE_KEY, JSON.stringify(now));
  }
  if (addKeys.length) {
    const now: Any = (await env.LEDGER.get(ADD_KEY, 'json')) ?? {};
    for (const k of addKeys) delete now[k];
    await env.LEDGER.put(ADD_KEY, JSON.stringify(now));
  }
  if (editKeys.length) {
    const now: Any = (await env.LEDGER.get(EDIT_KEY, 'json')) ?? {};
    for (const k of editKeys) delete now[k];
    await env.LEDGER.put(EDIT_KEY, JSON.stringify(now));
  }

  return `${sha} 로 반영했습니다 · ${note.join(', ')}`;
}
