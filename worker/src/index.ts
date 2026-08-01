// =============================================================================
// 로지아 아침 편지
//
// 하루 한 번, 판을 대신 읽고 한 줄을 부친다.
//
// 이 워커는 판을 갖고 있지 않다. 깃허브에 놓인 digest.enc 를 받아 풀 뿐이다.
// 그러므로 판을 고치는 길은 그대로다. 클로드가 저장소에서 받아 고치고 올린다.
// 워커가 더하는 것은 오직 하나, 클로드가 켜져 있지 않은 아침에도 판을 읽는
// 두 번째 눈이다.
//
// 깨어나는 길이 둘이다
//   scheduled  시계가 깨운다. wrangler.jsonc 의 crons 가 그 시계다.
//              아무도 주소를 열지 않아도, 데스크탑이 꺼져 있어도 깨어난다.
//   fetch      손으로 한 통 부쳐 볼 때만. 판의 알맹이는 돌려주지 않는다.
//
// 날짜 셈을 여기서 하는 이유
//   며칠 남았는지는 부치는 그 순간에만 참이다. 빌더가 미리 세어 두면
//   판을 두 주 동안 올리지 않은 아침에 거짓말을 하게 된다.
//   digest.enc 에는 날것만 들어 있고, 셈은 전부 아래에서 한다.
//
// 열쇠가 둘인 이유
//   사람이 손으로 치는 암호는 엔트로피가 낮아 PBKDF2 를 육십만 번 돌려야
//   한다. 그 셈은 무료 판의 십 밀리초를 훌쩍 넘긴다. 워커는 사람이 아니므로
//   처음부터 무작위 256비트를 준다. 늘일 것이 없으니 푸는 데 일 밀리초도
//   들지 않는다.
// =============================================================================

interface Env {
  EMAIL: {
    send(m: {
      to: string; from: string; subject: string; html: string; text: string;
    }): Promise<{ messageId: string }>;
  };
  DIGEST_KEY: string;      // 비밀. base64 로 적은 32바이트
  DIGEST_URL: string;
  MAIL_FROM: string;
  MAIL_TO: string;
  PREVIEW_TOKEN?: string;  // 비밀. 손으로 한 통 부쳐 볼 때 쓴다
  LEDGER?: KVNamespace;    // 해치운 걸음 장부. 없으면 판은 이 기기에만 적는다
  LEDGER_TOKEN?: string;   // 비밀. 판 안에 박혀 있다. 판이 암호문이므로 함께 잠긴다
}

/** 장부 한 칸. 무엇을 언제 해치웠는지. */
type DoneRow = { t: string; s: string; at: string };
type Ledger = Record<string, DoneRow>;

type Row = {
  t: string; v: string;
  due?: string; step?: string; pum?: string;
  sent?: string; until?: number; touched?: string;
};
type Rep = { m: number[]; day: number | string; t: string; v: string; guess: boolean };
type Digest = {
  built: string; site: string;
  due: Row[]; doing: Row[]; wait: Row[]; quiet: Row[]; repeats: Rep[];
};

// ── 날짜 ────────────────────────────────────────────────────────────────────
// 서울은 서머타임이 없다. 그래서 아홉 시간을 그냥 더하면 정확하다.
// Intl 에 기대지 않는 편이 여기서는 더 튼튼하다.
const SEOUL = 9 * 3600 * 1000;

function todaySeoul(now: number): string {
  return new Date(now + SEOUL).toISOString().slice(0, 10);
}

function dayNo(iso: string): number {
  const [y, m, d] = iso.split('-').map(Number);
  return Math.floor(Date.UTC(y, m - 1, d) / 86400000);
}

/** 오늘로부터 며칠 뒤인가. 어제면 -1, 내일이면 1. */
function until(today: string, iso: string): number {
  return dayNo(iso) - dayNo(today);
}

const WEEK = ['일', '월', '화', '수', '목', '금', '토'];

// ── 꾸러미 풀기 ──────────────────────────────────────────────────────────────
function b64(s: string): Uint8Array {
  const raw = atob(s);
  const out = new Uint8Array(raw.length);
  for (let i = 0; i < raw.length; i++) out[i] = raw.charCodeAt(i);
  return out;
}

async function fetchDigest(env: Env): Promise<Digest> {
  const res = await fetch(env.DIGEST_URL, { cf: { cacheTtl: 0 } });
  if (!res.ok) throw new Error(`digest.enc 를 받지 못했습니다 (${res.status})`);
  const parts = (await res.text()).trim().split('.');
  if (parts[0] !== 'loggiaR1' || parts.length !== 3) {
    throw new Error('digest.enc 의 꼴이 낯섭니다');
  }
  const key = await crypto.subtle.importKey(
    'raw', b64(env.DIGEST_KEY), { name: 'AES-GCM' }, false, ['decrypt']);
  const plain = await crypto.subtle.decrypt(
    { name: 'AES-GCM', iv: b64(parts[1]) }, key, b64(parts[2]));
  return JSON.parse(new TextDecoder().decode(plain));
}

// ── 판의 옷 ──────────────────────────────────────────────────────────────────
//
// 판과 같은 규칙을 따른다. 편지는 판의 조각이지 다른 물건이 아니다.
//
//   하나. 대비를 살린다. 옅은 회색으로 중요한 것을 적지 않는다.
//   둘.  제목이 가장 굵고 크다.
//   셋.  덩이로 자른다. 한 갈래가 한 상자다. 왼쪽 띠의 빛깔로 결을 안다.
//
// 빛깔은 꾸밈이 아니라 뜻이다.
//   붉음 급하다 · 주황 다가온다 · 파랑 남을 기다린다 · 회색 멎었다
//
// 메일에는 사용자 정의 속성도 flex 도 쓸 수 없다. 그래서 값을 그대로 적고
// 칸은 표로 짠다. 어두운 낯빛은 아래 <style> 이 덮어쓴다.

type Tone = 'now' | 'soon' | 'wait' | 'stop' | 'later';

const LIGHT = {
  paper: '#f6f7f8', surface: '#ffffff', sunk: '#edeff2',
  ink: '#11141d', ink2: '#494e5a', ink3: '#757b8a', rule: '#dcdfe4',
  now: '#d3231d', soon: '#c46008', wait: '#1861b4', stop: '#737782', later: '#6c727f',
};
const DARK = {
  paper: '#13151b', surface: '#1d1f26', sunk: '#23262f',
  ink: '#f3f4f7', ink2: '#b6bac3', ink3: '#8b919c', rule: '#373a43',
  now: '#f56a66', soon: '#f99f39', wait: '#5fb2f1', stop: '#8c919b', later: '#969ca6',
};

const FONT = "'Pretendard Variable',Pretendard,-apple-system,BlinkMacSystemFont,"
  + "'Apple SD Gothic Neo','Segoe UI','Noto Sans KR','Malgun Gothic',sans-serif";

/**
 * 어두운 낯빛.
 *
 * 초점 상자는 판에서 --ink 를 바탕으로 쓴다. 어두운 낯빛에서 --ink 는
 * 밝은 빛깔이 되므로 상자가 통째로 뒤집힌다. 판이 그러하니 편지도 그렇게 둔다.
 */
const DARK_CSS = `
@media (prefers-color-scheme: dark) {
  .bg      { background:${DARK.paper} !important }
  .card    { background:${DARK.surface} !important; border-color:${DARK.rule} !important }
  .h2      { color:${DARK.ink} !important }
  .t       { color:${DARK.ink} !important }
  .m,.d    { color:${DARK.ink3} !important }
  .cap     { color:${DARK.ink3} !important }
  .pill    { background:${DARK.sunk} !important; color:${DARK.ink3} !important }
  .rule    { border-color:${DARK.rule} !important }
  .k-now   { color:${DARK.now} !important }
  .k-soon  { color:${DARK.soon} !important }
  .k-wait  { color:${DARK.wait} !important }
  .k-stop  { color:${DARK.stop} !important }
  .k-later { color:${DARK.later} !important }
  .b-now   { background:${DARK.now} !important }
  .b-soon  { background:${DARK.soon} !important }
  .b-wait  { background:${DARK.wait} !important }
  .b-stop  { background:${DARK.stop} !important }
  .b-later { background:${DARK.later} !important }
  /* 초점 상자는 뒤집힌다 */
  .fx      { background:${DARK.ink} !important }
  .fx-cap  { color:#5c6270 !important }
  .fx-t    { color:${LIGHT.ink} !important }
  .fx-s    { color:${LIGHT.ink2} !important }
  .fx-m    { color:${LIGHT.ink3} !important }
  .fx-now  { color:${LIGHT.now} !important }
  .fx-soon { color:${LIGHT.soon} !important }
  .fx-later{ color:${LIGHT.later} !important }
  .btn     { background:${DARK.ink} !important; color:${DARK.paper} !important }
}
@media (max-width: 600px) {
  .pad  { padding-left:18px !important; padding-right:18px !important }
  .when { width:64px !important }
  .fxd  { font-size:34px !important }
  .fxt  { font-size:22px !important }
}`;

// ── 무엇을 말할까 ────────────────────────────────────────────────────────────
type Card = { big: string; small: string; title: string; meta: string; tone: Tone };
type Block = { cap: string; cards: Card[] };

const esc = (s: string) =>
  s.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');

/**
 * 판이 쓰는 말 그대로.
 *
 * 넓은 자리에서는 며칠 지났는지를 통째로 적는다. 좁은 칸에서는 숫자만 크게
 * 두고 아랫줄에 말을 붙인다. 「지남」 한 마디만 던지면 얼마나 지났는지가
 * 사라지고, 그 숫자가 실은 손을 움직이게 하는 것이다.
 */
function dBig(n: number): string {
  return n < 0 ? `${-n}일 지남` : n === 0 ? '오늘' : `D-${n}`;
}

/** 판이 쓰는 빛깔 그대로. 이레 안이면 붉고 한 달 안이면 주황이다. */
function dTone(n: number): Tone {
  return n < 0 ? 'now' : n <= 7 ? 'now' : n <= 30 ? 'soon' : 'later';
}

const md = (iso: string) => iso.slice(5).replace('-', '.');

function cut(s: string, n: number): string {
  return s.length <= n ? s : s.slice(0, n - 1) + '…';
}

/** 앞 문장이 할 일이고 뒷 문장이 그 까닭이다. */
function split2(step: string): [string, string] {
  const [a, ...rest] = step.split(/(?<=[.。])\s/);
  return [a.replace(/[.。]\s*$/, ''), rest.join(' ')];
}

/**
 * 오늘 하나.
 *
 * 진행 중인 것 가운데 첫 걸음이 있는 것을 고른다. 마감이 가장 가까운 것이
 * 먼저다. 이미 지난 마감은 뒤로 미루지 않고 맨 앞에 세운다. 지난 것을
 * 조용히 숨기면 그것이 있었다는 사실까지 함께 사라진다.
 */
function pickOne(d: Digest, today: string): Row | null {
  if (!d.doing.length) return null;
  const score = (r: Row) => {
    if (!r.due) return 9999;
    const n = until(today, r.due);
    return n < 0 ? -1000 + n : n;
  };
  return [...d.doing].sort((a, b) => score(a) - score(b))[0];
}

function compose(d: Digest, today: string) {
  const one = pickOne(d, today);
  const vsep = (v: string) => (v ? ' · ' + v : '');

  const soon = d.due
    .map((r) => ({ r, n: until(today, r.due!) }))
    .filter((x) => x.n <= 7)
    .sort((a, b) => a.n - b.n);
  const past = soon.filter((x) => x.n < 0);
  const ahead = soon.filter((x) => x.n >= 0);

  // 그 지면의 보통보다 오래 기다린 것. 보통을 모르면 마흔닷새를 넘겼을 때만
  // 부른다. 모르는 것을 아는 척하지 않는다.
  const late = d.wait
    .map((r) => ({ r, n: -until(today, r.sent!) }))
    .filter((x) => x.n > (x.r.until ?? 45))
    .sort((a, b) => b.n - a.n);

  const cold = d.quiet
    .map((r) => ({ r, n: -until(today, r.touched!) }))
    .filter((x) => x.n >= 21)
    .sort((a, b) => b.n - a.n);

  // 열흘 안에 돌아오는 되풀이
  const t = dayNo(today);
  const reps: { r: Rep; n: number }[] = [];
  for (const r of d.repeats) {
    for (const m of r.m) {
      for (const yr of [Number(today.slice(0, 4)), Number(today.slice(0, 4)) + 1]) {
        const last = new Date(Date.UTC(yr, m, 0)).getUTCDate();
        const day = typeof r.day === 'number' ? Math.min(r.day, last) : last;
        const n = Math.floor(Date.UTC(yr, m - 1, day) / 86400000) - t;
        if (n >= 0 && n <= 10) reps.push({ r, n });
      }
    }
  }
  reps.sort((a, b) => a.n - b.n);

  const blocks: Block[] = [];
  if (past.length) {
    blocks.push({
      cap: '지난 마감',
      cards: past.slice(0, 5).map((x) => ({
        big: String(-x.n), small: '일 지남', tone: 'now' as Tone,
        title: x.r.t, meta: `마감 ${md(x.r.due!)}` + vsep(x.r.v),
      })),
    });
  }
  if (ahead.length) {
    blocks.push({
      cap: '일주일 안',
      cards: ahead.map((x) => ({
        big: dBig(x.n), small: md(x.r.due!), tone: dTone(x.n),
        title: x.r.t, meta: (x.r.v || '') + (x.r.step ? vsep(cut(split2(x.r.step)[0], 30)) : ''),
      })),
    });
  }
  if (late.length) {
    blocks.push({
      cap: '오래 기다린 것',
      cards: late.map((x) => ({
        big: String(x.n), small: '일째', tone: 'wait' as Tone,
        title: x.r.t,
        meta: (x.r.v || '') + (x.r.until ? ` · 보통 ${x.r.until}일` : '') + ` · ${md(x.r.sent!)} 제출`,
      })),
    });
  }
  if (cold.length) {
    blocks.push({
      cap: '멈춰 있는 것',
      cards: cold.slice(0, 4).map((x) => ({
        big: String(x.n), small: '일째', tone: 'stop' as Tone,
        title: x.r.t, meta: (x.r.v || '') + ` · 마지막 작업 ${md(x.r.touched!)}`,
      })),
    });
  }
  if (reps.length) {
    blocks.push({
      cap: '다시 돌아오는 것',
      cards: reps.slice(0, 3).map((x) => ({
        // 되풀이는 참된 마감이 아니다. 같은 D- 글자를 다른 빛깔로 쓰면
        // 눈이 헷갈리므로 여기서는 아예 다른 말로 적는다.
        big: x.n === 0 ? '오늘' : String(x.n), small: x.n === 0 ? '' : '일 뒤',
        tone: 'later' as Tone,
        title: x.r.t, meta: (x.r.v || '') + (x.r.guess ? ' · 추정' : ''),
      })),
    });
  }

  const hot = soon.length ? soon[0].n : null;
  const [act] = one ? split2(one.step!) : [''];
  // 제목의 머리표. 상자 안의 「지남」은 좁은 칸에 맞춘 말이지만
  // 잠금 화면에서는 며칠 지났는지가 보여야 손이 움직인다.
  const badge = (n: number) =>
    n < 0 ? `${-n}일 지남` : n === 0 ? '오늘 마감' : `D-${n}`;
  const subject = one
    ? (hot !== null && hot <= 3 ? `[${badge(hot)}] ` : '') + `오늘 딱 하나 · ${cut(act, 42)}`
    : '오늘은 할 일이 없습니다';

  return { one, subject, blocks };
}

// ── 편지의 꼴 ────────────────────────────────────────────────────────────────
function card(c: Card): string {
  const L = LIGHT[c.tone];
  return `
<table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0"
  style="border-collapse:separate;margin:0 0 9px">
<tr>
  <td class="b-${c.tone}" width="6" style="width:6px;background:${L};
    border-radius:12px 0 0 12px;font-size:0;line-height:0">&nbsp;</td>
  <td class="card" style="background:${LIGHT.surface};border:1px solid ${LIGHT.rule};
    border-left:0;border-radius:0 12px 12px 0;padding:16px 20px 17px">
    <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0"><tr>
      <td class="when" width="80" valign="top" align="right" style="width:80px;padding-right:18px">
        <div class="k-${c.tone}" style="font-size:29px;font-weight:800;letter-spacing:-.03em;
          line-height:1.02;color:${L};font-variant-numeric:tabular-nums">${esc(c.big)}</div>
        ${c.small ? `<div class="d" style="margin-top:5px;font-size:12px;font-weight:600;
          color:${LIGHT.ink3};font-variant-numeric:tabular-nums">${esc(c.small)}</div>` : ''}
      </td>
      <td valign="top">
        <div class="t" style="font-size:19px;font-weight:800;letter-spacing:-.015em;
          line-height:1.36;color:${LIGHT.ink}">${esc(c.title)}</div>
        ${c.meta ? `<div class="m" style="margin-top:6px;font-size:13px;font-weight:600;
          line-height:1.5;color:${LIGHT.ink3}">${esc(c.meta)}</div>` : ''}
      </td>
    </tr></table>
  </td>
</tr>
</table>`;
}

function block(b: Block): string {
  return `
<table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0"
  style="margin:34px 0 14px"><tr>
  <td><span class="h2" style="font-size:21px;font-weight:800;letter-spacing:-.015em;
    color:${LIGHT.ink}">${esc(b.cap)}</span></td>
  <td align="right"><span class="pill" style="display:inline-block;font-size:12px;font-weight:700;
    color:${LIGHT.ink3};background:${LIGHT.sunk};padding:3px 11px;border-radius:99px">${b.cards.length}</span></td>
</tr></table>${b.cards.map(card).join('')}`;
}

function focusBox(one: Row | null, today: string): string {
  if (!one) {
    return `
<table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0"
  style="margin:22px 0 0"><tr><td class="fx" style="background:${LIGHT.ink};
  border-radius:14px;padding:26px 28px 28px">
  <div class="fx-cap" style="font-size:12px;font-weight:800;letter-spacing:.14em;
    color:#7b818f;margin-bottom:14px">오늘 딱 하나</div>
  <div class="fx-t" style="font-size:24px;font-weight:700;line-height:1.4;
    color:${LIGHT.paper}">오늘 할 일이 없습니다</div>
  <div class="fx-s" style="margin-top:10px;font-size:14px;line-height:1.66;color:#b9bec8">
    로지아에 다음 할 일을 하나만 적어 두면 내일 아침 이 자리에 뜹니다.</div>
</td></tr></table>`;
  }
  const n = one.due ? until(today, one.due) : null;
  const tone: Tone = n === null ? 'later' : dTone(n);
  const [act, why] = split2(one.step!);
  const meta = [one.t, one.v, one.pum].filter(Boolean).join(' · ');
  return `
<table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0"
  style="margin:22px 0 0"><tr><td class="fx pad" style="background:${LIGHT.ink};
  border-radius:14px;padding:26px 28px 28px">
  <div class="fx-cap" style="font-size:12px;font-weight:800;letter-spacing:.14em;
    color:#7b818f;margin-bottom:14px">오늘 딱 하나</div>
  ${n !== null ? `<div class="fxd fx-${tone}" style="font-size:42px;font-weight:800;
    letter-spacing:-.03em;line-height:1;color:${LIGHT[tone]};
    font-variant-numeric:tabular-nums">${esc(dBig(n))}</div>` : ''}
  <div class="fxt fx-t" style="margin-top:${n !== null ? 14 : 0}px;font-size:26px;font-weight:700;
    line-height:1.38;letter-spacing:-.01em;color:${LIGHT.paper}">${esc(act)}</div>
  ${why ? `<div class="fx-s" style="margin-top:10px;font-size:14.5px;line-height:1.66;
    color:#b9bec8">${esc(why)}</div>` : ''}
  <div class="fx-m" style="margin-top:14px;font-size:13px;line-height:1.6;color:#8f95a3">
    ${esc(meta)}${one.due ? ' · ' + esc(one.due.replace(/-/g, '.')) : ''}</div>
</td></tr></table>`;
}

function render(d: Digest, today: string) {
  const { one, subject, blocks } = compose(d, today);
  const w = WEEK[new Date(today + 'T00:00:00Z').getUTCDay()];

  const html = `<!doctype html><html lang="ko"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<meta name="color-scheme" content="light dark">
<meta name="supported-color-schemes" content="light dark">
<title>${esc(subject)}</title>
<style>${DARK_CSS}</style></head>
<body class="bg" style="margin:0;padding:0;background:${LIGHT.paper}">
<div style="display:none;max-height:0;overflow:hidden;opacity:0">${esc(
    blocks.map((b) => `${b.cap} ${b.cards.length}`).join(' · ') || '오늘은 조용합니다')}</div>
<table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0"
  class="bg" style="background:${LIGHT.paper}">
<tr><td align="center" style="padding:26px 12px 46px">
<table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0"
  style="max-width:600px;font-family:${FONT};line-height:1.62;
  -webkit-font-smoothing:antialiased;font-variant-numeric:tabular-nums">

<tr><td class="pad" style="padding:0 4px">
  <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0"><tr>
    <td><span class="cap" style="font-size:11px;font-weight:800;letter-spacing:.34em;
      color:${LIGHT.ink3}">LOGGIA</span></td>
    <td align="right"><span class="m" style="font-size:13px;font-weight:600;
      color:${LIGHT.ink3}">${esc(today.replace(/-/g, '.'))} ${w}</span></td>
  </tr></table>
</td></tr>

<tr><td style="padding:0 4px">${focusBox(one, today)}</td></tr>
<tr><td style="padding:0 4px">${blocks.map(block).join('')}</td></tr>

<tr><td style="padding:38px 4px 0">
  <a class="btn" href="${esc(d.site)}" style="display:inline-block;background:${LIGHT.ink};
    color:${LIGHT.paper};font-size:15px;font-weight:800;letter-spacing:-.01em;
    text-decoration:none;padding:14px 24px;border-radius:10px">로지아 열기 →</a>
  <div class="m" style="margin-top:14px;font-size:12px;color:${LIGHT.ink3}">
    마지막 업데이트 ${esc(d.built.replace(/-/g, '.'))}</div>
</td></tr>

</table></td></tr></table></body></html>`;

  const [act, why] = one ? split2(one.step!) : ['', ''];
  const text = [
    `LOGGIA  ${today.replace(/-/g, '.')} ${w}`,
    '',
    '── 오늘 딱 하나 ' + (one?.due ? dBig(until(today, one.due)) : ''),
    one ? act : '오늘 할 일이 없습니다',
    ...(why ? [why] : []),
    ...(one ? [[one.t, one.v, one.pum].filter(Boolean).join(' · ')] : []),
    ...blocks.map((b) => `\n── ${b.cap} (${b.cards.length})\n`
      + b.cards.map((c) => `${(c.big + ' ' + c.small).trim().padEnd(8)} ${c.title} · ${c.meta}`).join('\n')),
    '',
    d.site,
  ].join('\n');

  return { subject, html, text };
}

// ── 부치기 ──────────────────────────────────────────────────────────────────
async function send(env: Env): Promise<string> {
  const d = await fetchDigest(env);
  const today = todaySeoul(Date.now());
  const { subject, html, text } = render(d, today);
  const r = await env.EMAIL.send({
    to: env.MAIL_TO, from: env.MAIL_FROM, subject, html, text,
  });
  return r.messageId;
}

// ── 해치운 걸음 장부 ─────────────────────────────────────────────────────────
//
// 판은 미리 그려 둔 정적 파일이고 그리는 것은 파이썬이다. 그러므로 네모를
// 눌렀다고 원본이 따라 고쳐질 길은 없다. 고치려면 판의 암호와 깃허브 쓰기
// 열쇠를 이 워커 안에 넣어야 하는데, 그러면 아침 편지만 읽던 것이 판 전체를
// 읽고 쓰는 물건이 된다.
//
// 그래서 원본을 건드리지 않고 장부만 따로 쥔다. 얻는 것이 더 크다.
// 휴대전화에서 그은 줄이 노트북에서도 그어진다. 이 기기에만 남던 표시로는
// 되지 않던 일이다.
//
// 원본에 닿는 것은 다음 갱신 때 사람이 한다. 장부를 읽어 걸음을 빼고
// 손댄 날을 고치고 장부를 비운다.
//
// 열쇠는 판 안에 박혀 있다. 판이 암호문이므로 암호를 푼 사람만 그것을 본다.
// 지금 보안 모형과 어긋나지 않는다.
const KEY = 'board';

function json(v: unknown, status = 200): Response {
  return new Response(JSON.stringify(v), {
    status,
    headers: { 'content-type': 'application/json; charset=utf-8',
               'cache-control': 'no-store' },
  });
}

async function ledger(req: Request, env: Env, k: string | null): Promise<Response> {
  if (!env.LEDGER || !env.LEDGER_TOKEN || k !== env.LEDGER_TOKEN) {
    return new Response('없습니다', { status: 404 });
  }
  const now: Ledger = (await env.LEDGER.get(KEY, 'json')) ?? {};
  if (req.method === 'GET') return json(now);
  if (req.method !== 'POST') return new Response('안 됩니다', { status: 405 });

  // 한 번에 모아서 받는다. 누를 때마다 부르면 부질없는 왕복이 는다.
  const body = (await req.json()) as { set?: Ledger; del?: string[] };
  for (const [id, row] of Object.entries(body.set ?? {})) now[id] = row;
  for (const id of body.del ?? []) delete now[id];
  await env.LEDGER.put(KEY, JSON.stringify(now));
  return json(now);
}

export default {
  // 하루 한 번. 크론은 UTC 로 돈다. 서울 아침 일곱 시는 전날 22시다.
  async scheduled(_c: ScheduledController, env: Env, ctx: ExecutionContext) {
    ctx.waitUntil(send(env).then(
      (id) => console.log(`부쳤습니다 ${id}`),
      (e) => console.error(`부치지 못했습니다 ${e}`)));
  },

  // 손으로 한 통 부쳐 보고 싶을 때.
  //   GET /send?k=<PREVIEW_TOKEN>
  // 판의 알맹이는 어떤 경우에도 돌려주지 않는다. 결과는 편지함에서 본다.
  async fetch(req: Request, env: Env): Promise<Response> {
    const u = new URL(req.url);
    if (u.pathname === '/done') return ledger(req, env, u.searchParams.get('k'));
    if (u.pathname !== '/send' || !env.PREVIEW_TOKEN
        || u.searchParams.get('k') !== env.PREVIEW_TOKEN) {
      return new Response('없습니다', { status: 404 });
    }
    try {
      return new Response(`부쳤습니다 ${await send(env)}`);
    } catch (e) {
      return new Response(`부치지 못했습니다 ${e}`, { status: 500 });
    }
  },
} satisfies ExportedHandler<Env>;
