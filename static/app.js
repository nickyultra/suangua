/* 易学占卜 —— 前端交互：起卦排盘 + SSE 流式解读 */
'use strict';

const $ = (sel) => document.querySelector(sel);

const TRIGRAM = {
  乾: '☰', 兑: '☱', 离: '☲', 震: '☳',
  巽: '☴', 坎: '☵', 艮: '☶', 坤: '☷',
};

const POS_NAME = ['初', '二', '三', '四', '五', '上'];

const state = { meta: null, matterLabels: {}, last: null, busy: false };

// ── 初始化 ────────────────────────────────────────────────────────────

async function loadMeta() {
  const meta = await (await fetch('/api/meta')).json();
  state.meta = meta;
  state.matterLabels = Object.fromEntries(meta.matters.map((m) => [m.value, m.label]));

  const modeSel = $('#mode');
  modeSel.innerHTML = '';
  for (const m of meta.modes) {
    modeSel.appendChild(new Option(m.label, m.value));
  }

  const matterSel = $('#matter');
  matterSel.innerHTML = '';
  matterSel.appendChild(new Option('自动判断（由模型识别所问之事）', 'auto'));
  for (const m of meta.matters) {
    matterSel.appendChild(new Option(m.label, m.value));
  }

  $('#llm-hint').textContent = meta.llm_ready
    ? `模型：${meta.model}`
    : '未配置模型，仅出排盘';
}

function localNowInput() {
  const d = new Date();
  const p = (n) => String(n).padStart(2, '0');
  return `${d.getFullYear()}-${p(d.getMonth() + 1)}-${p(d.getDate())}T${p(d.getHours())}:${p(d.getMinutes())}`;
}

function syncMode() {
  const isNumber = $('#mode').value === 'meihua_number';
  $('#numbers-field').hidden = !isNumber;
}

// ── 起卦 ──────────────────────────────────────────────────────────────

function buildPayload(extra) {
  const mode = $('#mode').value;
  const payload = {
    question: $('#question').value.trim(),
    mode,
    matter: $('#matter').value,
    gender: $('#gender').value,
    at: state.at,
    ...extra,
  };
  if (mode === 'meihua_number') {
    payload.numbers = [Number($('#num1').value), Number($('#num2').value)];
  }
  return payload;
}

function errorMessage(data, status) {
  const detail = data && data.detail;
  if (typeof detail === 'string') return detail;
  if (Array.isArray(detail) && detail.length) {
    return detail.map((e) => e.msg || JSON.stringify(e)).join('；');
  }
  return `请求失败（${status}）`;
}

async function onCast(ev) {
  ev.preventDefault();
  if (state.busy) return;
  setBusy(true);
  hideError();
  state.at = $('#at').value || localNowInput();

  let data;
  try {
    const resp = await fetch('/api/divine', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(buildPayload()),
    });
    data = await resp.json();
    if (!resp.ok) throw new Error(errorMessage(data, resp.status));
  } catch (err) {
    setBusy(false);
    showError(err.message);
    return;
  }

  state.last = data;
  $('#calendar-panel').hidden = false;
  $('#chart-panel').hidden = false;
  $('#result').hidden = false;
  renderCalendar(data.result.calendar);
  renderCharts(data.result);
  renderContext(data);
  setBusy(false);
  $('#result').scrollIntoView({ behavior: 'smooth', block: 'start' });

  streamInterpret(data);
}

function setBusy(busy) {
  state.busy = busy;
  const btn = $('#cast-btn');
  btn.disabled = busy;
  btn.textContent = busy ? '起卦中…' : '起　卦';
}

// ── 历法条 ────────────────────────────────────────────────────────────

function renderCalendar(cal) {
  const box = $('#calendar-panel');
  box.innerHTML = '';
  const grid = document.createElement('div');
  grid.className = 'cal-grid';

  const add = (key, val) => {
    const cell = document.createElement('div');
    const k = document.createElement('span');
    k.className = 'cal-key';
    k.textContent = key;
    const v = document.createElement('b');
    v.textContent = val;
    cell.append(k, v);
    grid.appendChild(cell);
  };

  add('公历', cal.solar_text);
  add('农历', cal.lunar_text);
  add('四柱', `${cal.year_gz}年 ${cal.month_gz}月 ${cal.day_gz}日 ${cal.hour_gz}时`);
  add('月建', cal.month_jian);
  add('日辰', cal.day_chen);
  add('旬空', `${cal.xun}旬空${cal.xun_kong}`);
  if (cal.jieqi) add('节气', cal.jieqi);

  box.appendChild(grid);
}

// ── 卦象 ──────────────────────────────────────────────────────────────

function renderGua(gua, opts) {
  const { label, liushen, najia, liuqin, shiying, reveal } = opts;
  const isLiuyao = liushen || najia || liuqin || shiying;

  const wrap = document.createElement('div');
  wrap.className = 'gua' + (isLiuyao ? '' : ' meihua');

  const head = document.createElement('div');
  head.className = 'gua-head';
  const name = document.createElement('span');
  name.className = 'gua-name';
  name.textContent = (label ? label + '　' : '') + gua.name;
  const meta = document.createElement('span');
  meta.className = 'gua-meta';
  const bits = [TRIGRAM[gua.upper] + TRIGRAM[gua.lower]];
  if (isLiuyao && gua.gong) bits.push(`宫${gua.gong}${gua.gong_wuxing}`);
  if (shiying) bits.push(`世${gua.shi_pos}应${gua.ying_pos}`);
  meta.textContent = bits.join('　');
  head.append(name, meta);
  wrap.appendChild(head);

  const header = document.createElement('div');
  header.className = 'yao-row head';
  for (const [cls, text] of [
    ['ls', '六神'], ['nj', '纳甲'], ['lq', '六亲'], ['bar', '卦画'], ['tags', ''],
  ]) {
    const cell = document.createElement('span');
    if (cls) cell.className = cls;
    cell.textContent = text;
    header.appendChild(cell);
  }
  wrap.appendChild(header);

  // 上爻在前
  const rows = [...gua.lines].reverse();
  rows.forEach((ln, i) => {
    const row = document.createElement('div');
    row.className = 'yao-row';
    if (ln.moving) row.classList.add('moving');
    if (ln.is_shi) row.classList.add('is-shi');
    if (ln.is_ying) row.classList.add('is-ying');
    if (reveal) {
      row.style.animationDelay = `${(rows.length - 1 - i) * 90}ms`;
      row.classList.add('reveal');
    }

    const ls = document.createElement('span');
    ls.className = 'ls';
    ls.textContent = liushen ? ln.liushen : '';

    const nj = document.createElement('span');
    nj.className = 'nj';
    nj.textContent = najia && ln.gan ? `${ln.gan}${ln.zhi}${ln.wuxing}` : '';

    const lq = document.createElement('span');
    lq.className = 'lq';
    lq.textContent = liuqin ? ln.liuqin : '';

    const bar = document.createElement('span');
    bar.className = 'bar' + (ln.yang ? ' yang' : ' yin');
    const segs = ln.yang ? 1 : 2;
    for (let k = 0; k < segs; k++) bar.appendChild(document.createElement('i'));

    const tags = document.createElement('span');
    tags.className = 'tags';
    const marks = [];
    if (shiying && ln.is_shi) marks.push('世');
    if (shiying && ln.is_ying) marks.push('应');
    if (ln.moving) marks.push('动');
    if (ln.kong) marks.push('空');
    tags.textContent = marks.join(' ');

    row.append(ls, nj, lq, bar, tags);
    wrap.appendChild(row);
  });

  return wrap;
}

function renderCharts(result) {
  const box = $('#chart-panel');
  box.innerHTML = '';
  const charts = document.createElement('div');
  charts.className = 'charts';

  if (result.mode === 'liuyao') {
    charts.appendChild(renderGua(result.ben, {
      label: '本卦', liushen: true, najia: true, liuqin: true, shiying: true, reveal: true,
    }));
    if (result.bian) {
      charts.appendChild(renderGua(result.bian, {
        label: '变卦', liushen: false, najia: true, liuqin: true, shiying: false,
      }));
    }
  } else {
    charts.appendChild(renderGua(result.ben, { label: '本卦' }));
    if (result.hu) charts.appendChild(renderGua(result.hu, { label: '互卦' }));
    if (result.bian) charts.appendChild(renderGua(result.bian, { label: '变卦' }));
  }

  box.appendChild(charts);
  box.appendChild(result.mode === 'liuyao' ? yongshenNote(result) : tiyongNote(result));
}

function noteBox(html) {
  const box = document.createElement('div');
  box.className = 'note-box';
  box.innerHTML = html;
  return box;
}

function yongshenNote(result) {
  const pos = result.yongshen_pos;
  const where = pos.length
    ? '居' + pos.map((p) => `${POS_NAME[p - 1]}爻`).join('、')
    : '不上卦';
  const marks = pos.length
    ? '；动则以此为应期之钥'
    : '（用神伏藏，需寻伏神）';
  return noteBox(
    `用神：<b>${result.yongshen}</b>　·　${where}${marks}`
  );
}

function tiyongNote(result) {
  const d = result.tiyong_detail || {};
  const line1 =
    `体 <b>${result.ti}</b>（${d.ti_wuxing || ''}）　用 <b>${result.yong}</b>（${d.yong_wuxing || ''}）` +
    `　·　<b>${result.ti_yong_relation}</b>（${d.judgement || ''}${d.note ? '，' + d.note : ''}）`;
  const line2 = d.yingqi ? `<br>应期参考：${d.yingqi}` : '';
  return noteBox(line1 + line2);
}

// ── 上下文提示 ────────────────────────────────────────────────────────

function renderContext(data) {
  const box = $('#notices');
  box.innerHTML = '';

  const label = state.matterLabels[data.matter] || data.matter;
  const auto = data.matter_auto ? '（自动判定）' : '';
  const gender = data.gender ? `　求测者：${data.gender}` : '';
  const line = document.createElement('div');
  line.className = 'notice';
  line.textContent = `所问：${label}${auto}${gender}`;
  box.appendChild(line);

  for (const note of data.notices || []) {
    const el = document.createElement('div');
    el.className = 'notice';
    el.textContent = note;
    box.appendChild(el);
  }
}

function showError(message) {
  $('#calendar-panel').hidden = true;
  $('#chart-panel').hidden = true;
  const reading = $('#reading');
  reading.textContent = '';
  finishReading(reading);

  const box = $('#notices');
  box.innerHTML = '';
  const el = document.createElement('div');
  el.className = 'notice error';
  el.textContent = `起卦失败：${message}`;
  box.appendChild(el);
  $('#result').hidden = false;
}

function hideError() {
  $('#notices').innerHTML = '';
}

// ── 流式解读 ──────────────────────────────────────────────────────────

async function streamInterpret(data) {
  const reading = $('#reading');
  const notices = $('#notices');
  reading.textContent = '';
  reading.classList.remove('done');
  reading.classList.add('cursor');

  const resolved = data.result;
  const payload = buildPayload({
    matter: data.matter,
    gender: data.gender,
  });
  if (resolved.mode === 'liuyao') payload.throws = resolved.raw.throws;

  let resp;
  try {
    resp = await fetch('/api/interpret', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    });
  } catch (err) {
    appendNotice(notices, `解读请求失败：${err.message}`, true);
    finishReading(reading);
    return;
  }

  const reader = resp.body.getReader();
  const decoder = new TextDecoder();
  let buf = '';

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    buf += decoder.decode(value, { stream: true });

    let idx;
    while ((idx = buf.indexOf('\n\n')) >= 0) {
      const chunk = buf.slice(0, idx);
      buf = buf.slice(idx + 2);
      const line = chunk.split('\n').find((l) => l.startsWith('data:'));
      if (!line) continue;
      const raw = line.slice(5).trim();
      if (raw === '[DONE]') {
        finishReading(reading);
        continue;
      }
      let evt;
      try {
        evt = JSON.parse(raw);
      } catch {
        continue;
      }
      if (evt.text) {
        reading.append(document.createTextNode(evt.text));
      } else if (evt.notice) {
        appendNotice(notices, evt.notice, false);
      } else if (evt.error) {
        appendNotice(notices, evt.error, true);
      }
    }
  }
  finishReading(reading);
}

function finishReading(reading) {
  reading.classList.remove('cursor');
  reading.classList.add('done');
}

function appendNotice(box, text, isError) {
  const el = document.createElement('div');
  el.className = 'notice' + (isError ? ' error' : '');
  el.textContent = text;
  box.appendChild(el);
}

// ── 绑定 ──────────────────────────────────────────────────────────────

$('#mode').addEventListener('change', syncMode);
$('#cast-form').addEventListener('submit', onCast);

loadMeta().then(syncMode).catch((err) => {
  $('#llm-hint').textContent = `初始化失败：${err.message}`;
});
