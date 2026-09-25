/* 组学研究设计工作台 · Web 版 —— 前端逻辑
   四个视图：工作台（可编辑 + 追问→回答→改写→采纳 + 汇总导出）、统计、SCI 结构、总览（收敛推理）。
   业务判断全部在服务端（复用桌面版同一套代码），这里只负责显示与交互。
   约定：凡是会改数据或调用模型的接口，成功时都会回传整份 state —— 前端整体重绘，不做局部同步。 */
'use strict';

var API = '/api';
var STEPS = [
  { key: 'work', n: 1, name: '工作台', sub: '十阶段' },
  { key: 'stat', n: 2, name: '统计', sub: '九阶段' },
  { key: 'shape', n: 3, name: 'SCI 结构', sub: '七章' },
  { key: 'ov', n: 4, name: '总览', sub: '收敛推理' }
];
var STATE = null;
var VIEW = 'ov';
var ABORT = null;
var BUSY = false;
var WORK_SID = 1;
var LAST_FINAL = null;
var QQ = new URLSearchParams(location.search);

function $(id) { return document.getElementById(id); }

function esc(s) {
  return String(s === null || s === undefined ? '' : s)
    .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;');
}

function pad2(n) { return (n < 10 ? '0' : '') + n; }

function toast(msg, ms) {
  var t = $('toast');
  t.textContent = msg;
  t.hidden = false;
  clearTimeout(toast._t);
  toast._t = setTimeout(function () { t.hidden = true; }, ms || 3600);
}

function pct(a, b) { return Math.round(100 * a / Math.max(1, b)); }

function bar(done, total, cls) {
  var p = pct(done, total);
  var k = cls || (p >= 100 ? 'ok' : (p > 0 ? 'warn' : ''));
  return '<div class="bar ' + k + '" title="' + done + '/' + total + '"><i style="width:' + p + '%"></i></div>';
}

function ul(items, cls) {
  if (!items || !items.length) { return '<div class="empty">—</div>'; }
  return '<ul class="kv ' + (cls || '') + '">' +
         items.map(function (x) { return '<li>' + esc(x) + '</li>'; }).join('') + '</ul>';
}

function sec(title, body, cls) {
  return '<div class="wsec"><div class="wt ' + (cls || '') + '">' + esc(title) +
         '</div>' + body + '</div>';
}

/* ------------------------------------------------------------------ 主题 */
function applyTheme(t) {
  document.documentElement.setAttribute('data-theme', t);
  $('btnTheme').textContent = (t === 'dark' ? '☾ 深色' : '☀ 浅色');
  try { localStorage.setItem('pcl-theme', t); } catch (e) { /* 隐私模式忽略 */ }
}

function initTheme() {
  var t = QQ.get('theme');
  if (!t) { try { t = localStorage.getItem('pcl-theme'); } catch (e) { t = ''; } }
  applyTheme(t === 'light' ? 'light' : 'dark');
}

/* -------------------------------------------------------------- 兼容检查 */
function checkCompat() {
  var ok = window.fetch && window.TextDecoder && window.ReadableStream &&
           document.documentElement.classList && window.Promise && window.URLSearchParams;
  $('compat').hidden = !!ok;
  if (!ok) { $('btnConv').disabled = true; }
  return !!ok;
}

/* ------------------------------------------------------------ 流程条/视图 */
function renderStepper() {
  var idx = STEPS.findIndex(function (s) { return s.key === VIEW; });
  var html = '';
  STEPS.forEach(function (s, i) {
    var cls = 'step' + (s.key === VIEW ? ' active' : (i < idx ? ' done' : ''));
    html += '<button class="' + cls + '" type="button" data-view="' + s.key + '">' +
            '<span class="knob">' + s.n + '</span>' +
            '<span class="txt"><b>' + esc(s.name) + '</b><i>' + esc(s.sub) + '</i></span></button>';
    if (i < STEPS.length - 1) {
      var p = i < idx ? 100 : (i === idx ? 50 : 0);
      html += '<span class="link"><i style="width:' + p + '%"></i></span>';
    }
  });
  $('stepper').innerHTML = html;
  Array.prototype.forEach.call($('stepper').querySelectorAll('.step'), function (b) {
    b.addEventListener('click', function () { showView(b.getAttribute('data-view')); });
  });
}

function showView(key) {
  VIEW = key;
  STEPS.forEach(function (s) { $('view-' + s.key).hidden = (s.key !== key); });
  renderStepper();
  window.scrollTo(0, 0);
}

/* -------------------------------------------------------------- 忙碌状态 */
function setBusy(on) {
  BUSY = !!on;
  ['btnKickoff', 'btnFinalize', 'btnConv', 'btnRawSave', 'btnNew', 'btnRename',
   'btnDelete'].forEach(function (id) {
    var el = $(id);
    if (el) { el.disabled = !!on; }
  });
  Array.prototype.forEach.call(document.querySelectorAll('#wActions button'), function (b) {
    b.disabled = !!on;
  });
  $('btnWorkStop').hidden = !(on && STREAM && STREAM.target === 'work');
  $('btnConvStop').hidden = !(on && STREAM && STREAM.target === 'ov');
}

/* -------------------------------------------------------------- 顶栏渲染 */
function renderTopbar(d) {
  $('verLine').textContent = 'Web 版 v' + d.version + ' · Python ' + d.python +
                            (d.frozen ? ' · 冻结版' : '');
  var sel = $('projSel');
  if (!d.projects.length) {
    sel.innerHTML = '<option value="">（还没有课题）</option>';
  } else {
    sel.innerHTML = d.projects.map(function (p) {
      var on = (p.name === d.current) ? ' selected' : '';
      return '<option value="' + esc(p.name) + '"' + on + '>' + esc(p.name) +
             ' · ' + p.done + '/10 · ' + esc(p.updated) + '</option>';
    }).join('');
  }
  var llm = d.llm || {};
  var pill = $('llmPill');
  pill.textContent = (llm.ready ? '● ' : '○ ') + (llm.model || '?') +
                     (llm.ready ? '' : ' · 未配密钥');
  pill.className = 'pill ' + (llm.ready ? 'on' : 'off');
  pill.title = (llm.base_url || '') + ' · 密钥 ' + (llm.key || '（无）') +
               ' · 来源 ' + (llm.key_source || 'none');
  var dis = !d.current || BUSY;
  $('btnRename').disabled = dis;
  $('btnDelete').disabled = dis;
  $('btnConv').disabled = dis;
  $('btnKickoff').disabled = dis;
  $('btnFinalize').disabled = dis;
  $('rawDesign').disabled = !d.current || BUSY;
}

/* ------------------------------------------------------------ 工作台视图 */
function stageById(sid) {
  var stages = ((STATE || {}).overview || {}).stages || [];
  for (var i = 0; i < stages.length; i++) {
    if (stages[i].id === sid) { return stages[i]; }
  }
  return null;
}

function renderWork(ov) {
  var stages = ov.stages || [];
  var c = ov.stage_counts || {};
  $('rawMeta').textContent = '研究设想 ' + ov.raw_len + ' 字 · 创建 ' + ov.created +
                             ' · 更新 ' + ov.updated + (ov.model ? ' · 模型 ' + ov.model : '');
  $('workCount').textContent = '已定稿 ' + (c.done || 0) + ' · 追问 ' + (c.asked || 0) +
                              ' · 待采纳 ' + (c.drafted || 0) + ' · 未开始 ' + (c.todo || 0);
  if (!stageById(WORK_SID) && stages.length) { WORK_SID = stages[0].id; }
  $('stageRail').innerHTML = stages.map(function (s) {
    return '<button class="railitem' + (s.id === WORK_SID ? ' sel' : '') +
      '" type="button" data-sid="' + s.id + '">' +
      '<span class="num">' + pad2(s.id) + '</span>' +
      '<span class="rtxt"><b>' + esc(s.title) + '</b><i>' + esc(s.label) +
      (s.body_len ? ' · ' + s.body_len + ' 字' : '') + '</i></span>' +
      '<span class="dot ' + s.status + '"></span></button>';
  }).join('');
  Array.prototype.forEach.call($('stageRail').querySelectorAll('.railitem'), function (b) {
    b.addEventListener('click', function () {
      if (BUSY) { return; }
      WORK_SID = parseInt(b.getAttribute('data-sid'), 10) || 1;
      try { localStorage.setItem('pcl-sid', String(WORK_SID)); } catch (e) { /* ignore */ }
      QQ.set('sid', String(WORK_SID));
      history.replaceState(null, '', '?' + QQ.toString());
      renderWork(STATE.overview);
    });
  });
  renderStageDetail();

  $('finalDoc').textContent = (ov.final_doc || '').trim() || '（还没有生成）';
  var fe = LAST_FINAL || {};
  $('finalExtra').innerHTML =
    (fe.todo || fe.selfcheck)
      ? ((fe.todo ? sec('待补数据清单', '<div class="box">' + esc(fe.todo) + '</div>') : '') +
         (fe.selfcheck ? sec('投稿前自查', '<div class="box">' + esc(fe.selfcheck) + '</div>') : ''))
      : '';
  var q = 'project=' + encodeURIComponent(STATE.current);
  $('dlMd').setAttribute('href', API + '/export?' + q + '&fmt=md');
  $('dlDocx').setAttribute('href', API + '/export?' + q + '&fmt=docx');
}

function renderStageDetail() {
  var s = stageById(WORK_SID);
  var acts = $('wActions');
  if (!s) {
    $('wTitle').textContent = '选择一个阶段';
    $('wState').textContent = '';
    $('wSpec').textContent = '';
    $('wDetail').innerHTML = '<div class="empty">还没有课题。</div>';
    acts.innerHTML = '';
    return;
  }
  $('wTitle').innerHTML = '阶段 ' + pad2(s.id) + ' · ' + esc(s.title);
  $('wState').textContent = s.label +
    (s.body_len ? '　·　' + (s.is_final ? '定稿 ' : '草稿 ') + s.body_len + ' 字' : '');
  $('wState').className = 'tag ' + (s.status === 'done' ? 'ok'
                                    : (s.status === 'todo' ? '' : 'warn'));
  $('wSpec').textContent = '规范出处：' + s.spec + (s.goal ? '　｜　' + s.goal : '');

  var h = [];
  h.push('<div class="wcols">' +
    sec('本阶段必做动作', ul(s.actions)) +
    sec('必报参数', ul(s.reports)) +
    sec('常见缺陷', ul(s.pitfalls, 'bad')) +
    sec('参考条目', ul(s.refs, 'muted')) +
    '</div>');
  if (s.assessment) {
    h.push(sec('现状评估', '<div class="box">' + esc(s.assessment) + '</div>'));
  }
  if (s.questions && s.questions.length) {
    h.push(sec('追问（回答后生成改写稿）', s.questions.map(function (q, i) {
      return '<div class="qbox"><div class="q">Q' + (i + 1) + '　' + esc(q.q || '') + '</div>' +
        (q.why ? '<div class="why">为什么问：' + esc(q.why) + '</div>' : '') +
        '<textarea class="ta qa" rows="2" placeholder="在这里回答（留空则由模型按常规做法给建议值）">' +
        esc(s.answers[i] || '') + '</textarea></div>';
    }).join('')));
  }
  if (s.draft) {
    h.push(sec('改写稿（可直接编辑；采纳后成为定稿）',
      '<textarea id="draftBox" class="ta" rows="10">' + esc(s.draft) + '</textarea>'));
  }
  if (s.risks) {
    h.push(sec('风险提示', '<div class="box warn">' + esc(s.risks) + '</div>'));
  }
  if (s.checklist && s.checklist.length) {
    h.push(sec('检查表', ul(s.checklist, 'check')));
  }
  if (s.next) { h.push(sec('下一步', '<div class="box">' + esc(s.next) + '</div>')); }
  if (s.final) {
    h.push(sec('已收录定稿（可编辑后保存）',
      '<textarea id="finalBox" class="ta" rows="8">' + esc(s.final) + '</textarea>', 'ok'));
  }
  $('wDetail').innerHTML = h.join('');

  var b = [];
  function btn(act, text, cls) {
    return '<button class="btn ' + (cls || 'ghost') + '" type="button" data-act="' + act +
           '">' + text + '</button>';
  }
  if (!s.assessment && !s.questions.length) {
    b.push(btn('ask', '开始追问', 'primary'));
  } else {
    b.push(btn('ask', '重新追问'));
  }
  if (s.questions.length) {
    b.push(btn('rewrite', s.draft ? '重新生成改写稿' : '提交回答并改写', 'primary'));
    b.push(btn('saveAnswers', '只保存回答'));
  }
  if (s.draft) { b.push(btn('accept', '采纳为定稿', 'primary')); }
  if (s.final) { b.push(btn('saveFinal', '保存定稿修改')); }
  acts.innerHTML = b.join('');
  setBusy(BUSY);
}

function readAnswers() {
  return Array.prototype.map.call(document.querySelectorAll('#wDetail textarea.qa'),
                                  function (t) { return t.value; });
}

function boxText(id) {
  var el = $(id);
  return el ? el.value : '';
}

/* ------------------------------------------------------- 统计 / SCI 结构 */
function renderScope(target, rows) {
  $(target).innerHTML = rows.map(function (r) {
    var extra = [];
    if (r.has_final) { extra.push('已定稿 ' + r.final_len + ' 字'); }
    else if (r.draft_len) { extra.push('待采纳稿 ' + r.draft_len + ' 字'); }
    if (r.questions) { extra.push('追问 ' + r.questions + ' 条'); }
    return '<div class="srow">' +
      '<div class="num">' + r.id + '</div>' +
      '<div class="body"><b>' + esc(r.title) + '</b><span class="spec">' + esc(r.spec) +
      '</span><div class="desc">' + esc(r.desc || '') +
      (extra.length ? '　｜　' + esc(extra.join(' · ')) : '') + '</div></div>' +
      '<div class="side"><span class="state">' + esc(r.guide_label) + '</span>' +
      bar(r.checks_done, r.checks_total) +
      '<span class="state ' + r.state + '">' + esc(r.state_label) + '</span></div>' +
      '</div>';
  }).join('');
}

/* ------------------------------------------------------------------ 总览 */
function renderLanes(ov) {
  $('laneBox').innerHTML = (ov.lanes || []).map(function (l) {
    var p = pct(l.done, l.total);
    return '<div class="lane">' +
      '<div class="lt"><b>' + esc(l.name) + '</b><i>' + esc(l.unit) + '</i>' +
      '<span>' + l.done + '/' + l.total + '　' + p + '%</span></div>' +
      bar(l.done, l.total, 'wide') + '</div>';
  }).join('');

  var dg = ov.digest || {};
  var cells = [['工作台定稿', dg.work_final], ['统计定稿', dg.stat_final],
               ['SCI 定稿', dg.shape_final], ['scope 定稿合计', dg.scope_final]];
  $('digestBox').innerHTML = cells.map(function (c) {
    return '<div><b>' + (c[1] || 0) + '</b> ' + esc(c[0]) + '</div>';
  }).join('');

  var t = ov.totals || {};
  $('projMeta').innerHTML =
    '<span>课题：' + esc(ov.name) + '　创建 ' + esc(ov.created) + '　更新 ' + esc(ov.updated) + '</span>' +
    '<span>研究设想 ' + ov.raw_len + ' 字　对话记录 ' + (ov.transcript_len || 0) + ' 条' +
    (ov.has_final_doc ? '　已生成汇总草案' : '') + '</span>' +
    '<span>统计 ' + (t.stat_done || 0) + '/' + (ov.stat || []).length + ' 环节（进行中 ' +
    (t.stat_doing || 0) + '）· 自检 ' + (t.stat_ticks || 0) + '/' + (t.stat_checks || 0) + '</span>' +
    '<span>SCI ' + (t.shape_done || 0) + '/' + (ov.shape || []).length + ' 章（进行中 ' +
    (t.shape_doing || 0) + '）· 自检 ' + (t.shape_ticks || 0) + '/' + (t.shape_checks || 0) + '</span>';
}

function renderStageTable(ov) {
  var rows = ov.stages || [];
  $('ovStages').querySelector('tbody').innerHTML = rows.map(function (s) {
    return '<tr><td class="num">' + s.id + '</td><td>' + esc(s.title) + '</td>' +
      '<td class="dim">' + esc(s.spec) + '</td>' +
      '<td><span class="state ' + s.status + '">' + esc(s.label) + '</span></td>' +
      '<td class="center">' + (s.is_final ? '✅ ' + s.body_len + ' 字'
                                          : (s.body_len ? '◐ 草稿' : '—')) + '</td>' +
      '<td class="center">' + ((s.questions || []).length || '—') + '</td>' +
      '<td class="center">' + ((s.checklist || []).length || '—') + '</td></tr>';
  }).join('');
  var c = ov.stage_counts || {};
  $('stageCounts').textContent = '已定稿 ' + (c.done || 0) + ' · 已追问 ' + (c.asked || 0) +
                                ' · 待采纳 ' + (c.drafted || 0) + ' · 未开始 ' + (c.todo || 0);
}

function renderConvergence(conv) {
  conv = conv || {};
  var chapters = conv.chapters || [];
  var actions = conv.actions || [];
  var st = $('convState');
  if (chapters.length) {
    st.textContent = '已更新 · ' + (conv.updated || '') + ' · ' + (conv.model || '') +
                     ' · ' + (conv.elapsed || '') + 's · ' + chapters.length + ' 章';
    st.className = 'tag ok';
  } else {
    st.textContent = '尚未推理';
    st.className = 'tag warn';
  }
  $('convMeta').textContent = (conv.basis ? '判断依据：' + conv.basis.slice(0, 120) : '');
  $('convOverall').hidden = !conv.overall;
  $('convOverall').textContent = conv.overall || '';

  $('convChapters').innerHTML = chapters.map(function (c) {
    var rs = (typeof c.readiness === 'number') ? c.readiness : null;
    var bcls = rs === null ? '' : (rs >= 80 ? 'ok' : (rs >= 40 ? 'warn' : ''));
    function dl(k, v, cls) {
      if (!v) { return ''; }
      return '<dt>' + k + '</dt><dd class="' + (cls || '') + '">' + esc(v) + '</dd>';
    }
    return '<div class="chap"><div class="ch"><b>' + esc(c.title) + '</b>' +
      (rs === null ? '' : bar(rs, 100, bcls) + '<span class="pct">' + rs + '%</span>') +
      '</div><dl>' +
      dl('来源', c.sources) + dl('已有', c.have) +
      dl('缺失', c.missing, c.missing && c.missing !== '无' ? 'miss' : '') +
      dl('理由', c.reason, 'why') + '</dl></div>';
  }).join('');

  $('convActions').hidden = !actions.length;
  $('convActions').innerHTML = actions.length
    ? '<div class="al">下一批动作（按优先级）</div><ol>' +
      actions.map(function (a) { return '<li>' + esc(a) + '</li>'; }).join('') + '</ol>'
    : '';
}

/* ------------------------------------------------------------ 数据加载 */
function applyState(d) {
  STATE = d;
  renderTopbar(d);
  if (d.overview) {
    renderWork(d.overview);
    renderScope('statRows', d.overview.stat || []);
    renderScope('shapeRows', d.overview.shape || []);
    renderLanes(d.overview);
    renderStageTable(d.overview);
    renderConvergence(d.convergence);
    if (document.activeElement !== $('rawDesign')) {
      $('rawDesign').value = d.overview.raw_design || '';
    }
  } else {
    $('rawDesign').value = '';
    $('stageRail').innerHTML = '<div class="empty">还没有课题，点右上「新建」。</div>';
    $('wDetail').innerHTML = '';
    $('wActions').innerHTML = '';
    $('statRows').innerHTML = '<div class="empty">还没有课题。</div>';
    $('shapeRows').innerHTML = '<div class="empty">还没有课题。</div>';
    $('laneBox').innerHTML = '';
    $('digestBox').innerHTML = '';
    $('projMeta').innerHTML = '';
    $('ovStages').querySelector('tbody').innerHTML = '';
    $('finalDoc').textContent = '（还没有生成）';
    $('finalExtra').innerHTML = '';
    renderConvergence({});
  }
  $('footLeft').textContent = '服务端 ' + d.app + ' v' + d.version +
    '　·　课题文件：' + (d.current_file || '—');
  $('footRight').textContent = '数据文件与桌面版共用 · 同一课题请勿两端同时编辑';
  setBusy(BUSY);
}

function loadState(keepView) {
  var q = STATE && STATE.current ? STATE.current : (QQ.get('project') || '');
  return fetch(API + '/state?project=' + encodeURIComponent(q), { cache: 'no-store' })
    .then(function (r) { return r.json(); })
    .then(function (d) {
      applyState(d);
      if (!keepView) { showView(VIEW); }
      return d;
    })
    .catch(function (e) {
      toast('加载失败：' + e.message);
      $('footLeft').textContent = '加载失败：' + e.message;
    });
}

/* ------------------------------------------------------------ 项目管理 */
function post(url, body) {
  return fetch(url, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body || {})
  }).then(function (r) {
    return r.json().then(function (j) {
      if (!r.ok || j.ok === false) { throw new Error(j.error || ('HTTP ' + r.status)); }
      return j;
    });
  });
}

function bindProjects() {
  $('projSel').addEventListener('change', function () {
    if (BUSY) { return; }
    var name = $('projSel').value;
    QQ.set('project', name);
    history.replaceState(null, '', '?project=' + encodeURIComponent(name));
    if (STATE) { STATE.current = name; }
    loadState(true);
  });

  $('btnNew').addEventListener('click', function () {
    var name = window.prompt('新建课题的名字：', '未命名课题');
    if (name === null) { return; }
    post(API + '/project/new', { name: name }).then(function (j) {
      QQ.set('project', j.project);
      history.replaceState(null, '', '?project=' + encodeURIComponent(j.project));
      toast('已新建：' + j.project);
      return loadState(true).then(function () { showView('work'); });
    }).catch(function (e) { toast('新建失败：' + e.message); });
  });

  $('btnRename').addEventListener('click', function () {
    if (!STATE || !STATE.current) { return; }
    var name = window.prompt('把「' + STATE.current + '」改名为：', STATE.current);
    if (name === null || name === STATE.current) { return; }
    post(API + '/project/rename', { project: STATE.current, name: name }).then(function (j) {
      QQ.set('project', j.project);
      history.replaceState(null, '', '?project=' + encodeURIComponent(j.project));
      toast('已改名：' + j.project);
      return loadState(true);
    }).catch(function (e) { toast('改名失败：' + e.message); });
  });

  $('btnDelete').addEventListener('click', function () {
    if (!STATE || !STATE.current) { return; }
    var ok = window.confirm('确定删除课题「' + STATE.current + '」？\n该项目的 json 文件会被删除，不可恢复。');
    if (!ok) { return; }
    post(API + '/project/delete', { project: STATE.current }).then(function () {
      toast('已删除');
      QQ.delete('project');
      history.replaceState(null, '', location.pathname);
      if (STATE) { STATE.current = ''; }
      return loadState(true);
    }).catch(function (e) { toast('删除失败：' + e.message); });
  });
}

/* ------------------------------------------------------ 流式调用（SSE） */
var STREAM = { target: 'ov', box: 'convText', live: 'convLive' };
var PENDING_DONE = null;        // 流结束后的后续动作（例如速读完成→自动开始追问），
                                // 必须等 setBusy(false) 之后再跑，否则会被"忙碌中"挡掉

function liveAppend(kind, text) {
  var box = $(STREAM.box);
  if (kind === 'status') {
    liveAppend._rz = null;
    box.appendChild(document.createTextNode('\n· ' + text + '\n'));
  } else if (kind === 'reasoning') {
    if (!liveAppend._rz) {
      liveAppend._rz = document.createElement('span');
      liveAppend._rz.className = 'rz';
      box.appendChild(liveAppend._rz);
    }
    liveAppend._rz.appendChild(document.createTextNode(text));
  } else {
    liveAppend._rz = null;
    box.appendChild(document.createTextNode(text));
  }
  box.scrollTop = box.scrollHeight;
}

function streamAction(url, payload, target, onDone) {
  if (!STATE || !STATE.current) { toast('先选择或新建一个课题'); return; }
  if (BUSY) { toast('上一步还在进行中'); return; }
  STREAM.target = target || 'ov';
  STREAM.box = STREAM.target === 'work' ? 'wText' : 'convText';
  STREAM.live = STREAM.target === 'work' ? 'wLive' : 'convLive';
  var box = $(STREAM.box);
  box.textContent = '';
  liveAppend._rz = null;
  $(STREAM.live).hidden = false;
  setBusy(true);
  ABORT = ('AbortController' in window) ? new AbortController() : null;

  var opts = {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload || {})
  };
  if (ABORT) { opts.signal = ABORT.signal; }

  return fetch(url, opts).then(function (res) {
    if (!res.ok) {
      return res.json().then(function (j) {
        throw new Error(j.error || ('HTTP ' + res.status));
      });
    }
    if (!res.body || !res.body.getReader) { throw new Error('浏览器不支持流式读取'); }
    var reader = res.body.getReader();
    var dec = new TextDecoder('utf-8');
    var buf = '';
    function pump() {
      return reader.read().then(function (r) {
        if (r.done) { return null; }
        buf += dec.decode(r.value, { stream: true });
        var i;
        while ((i = buf.indexOf('\n\n')) >= 0) {
          var raw = buf.slice(0, i);
          buf = buf.slice(i + 2);
          raw.split('\n').forEach(function (line) {
            if (line.indexOf('data:') !== 0) { return; }
            var obj;
            try { obj = JSON.parse(line.slice(5).trim()); } catch (e) { return; }
            handleEvent(obj, onDone);
          });
        }
        return pump();
      });
    }
    return pump();
  }).catch(function (e) {
    if (e && e.name === 'AbortError') {
      liveAppend('status', '已停止接收（服务端仍会完成本次调用并落盘）');
      return;
    }
    liveAppend('status', '出错：' + e.message);
    toast('失败：' + e.message, 6000);
  }).then(function () {
    ABORT = null;
    setBusy(false);
    if (PENDING_DONE) {
      var f = PENDING_DONE;
      PENDING_DONE = null;
      f();
    }
  });
}

function handleEvent(obj, onDone) {
  if (obj.type === 'status') {
    liveAppend('status', obj.text || '');
  } else if (obj.type === 'reasoning' || obj.type === 'content') {
    liveAppend(obj.type, obj.text || '');
  } else if (obj.type === 'error') {
    liveAppend('status', '错误：' + (obj.text || ''));
    toast('失败：' + (obj.text || '').slice(0, 120), 7000);
  } else if (obj.type === 'done') {
    if (!obj.ok) { return; }
    if (obj.kind === 'finalize') {
      LAST_FINAL = { todo: obj.todo_list || '', selfcheck: obj.selfcheck || '' };
    }
    if (obj.state) { applyState(obj.state); }
    var msg = { ask: '追问完成：' + (obj.questions || 0) + ' 条问题',
                rewrite: '改写完成：' + (obj.draft_len || 0) + ' 字 · 检查表 ' +
                         (obj.checks || 0) + ' 条',
                finalize: '已生成完整草案：' + (obj.final_len || 0) + ' 字',
                convergence: '收敛推理完成：' + (obj.chapters || 0) + ' 章' }[obj.kind] ||
              '完成';
    var u = obj.usage || {};
    liveAppend('status', msg + (u.total_tokens ? ' · ' + u.total_tokens + ' tokens' : '') +
      (obj.saved === false ? '　[落盘失败：' + (obj.save_error || '') + ']' : '　已落盘'));
    toast(msg);
    if (onDone) { PENDING_DONE = function () { onDone(obj); }; }
  }
}

/* -------------------------------------------------------- 工作台的动作 */
function bindWork() {
  $('btnRawSave').addEventListener('click', function () {
    post(API + '/stage/save', {
      project: STATE.current, sid: WORK_SID, raw_design: $('rawDesign').value
    }).then(function (j) {
      applyState(j.state);
      toast('已保存研究设想');
    }).catch(function (e) { toast('保存失败：' + e.message); });
  });

  $('btnKickoff').addEventListener('click', function () {
    if (!$('rawDesign').value.trim()) { toast('先把研究设想贴进来'); return; }
    streamAction(API + '/kickoff', {
      project: STATE.current, raw_design: $('rawDesign').value
    }, 'work', function () {
      WORK_SID = 1;
      actAsk();                      // 与桌面版一致：速读之后直接进入第一阶段追问
    });
  });

  $('btnFinalize').addEventListener('click', function () {
    streamAction(API + '/finalize', { project: STATE.current }, 'work');
  });

  $('wActions').addEventListener('click', function (ev) {
    var b = ev.target.closest ? ev.target.closest('button[data-act]') : null;
    if (!b || BUSY) { return; }
    var act = b.getAttribute('data-act');
    var proj = STATE.current;
    if (act === 'ask') {
      actAsk();
    } else if (act === 'rewrite') {
      streamAction(API + '/stage/rewrite',
                   { project: proj, sid: WORK_SID, answers: readAnswers() }, 'work');
    } else if (act === 'saveAnswers') {
      post(API + '/stage/answers',
           { project: proj, sid: WORK_SID, answers: readAnswers() })
        .then(function (j) { applyState(j.state); toast('已保存回答'); })
        .catch(function (e) { toast('保存失败：' + e.message); });
    } else if (act === 'accept') {
      post(API + '/stage/save',
           { project: proj, sid: WORK_SID, accept: true, final: boxText('draftBox'),
             answers: readAnswers() })
        .then(function (j) {
          applyState(j.state);
          toast('已收录阶段 ' + pad2(WORK_SID) + ' 定稿');
          var nxt = WORK_SID + 1;
          if (nxt <= 10 && confirm('已收录。是否立刻开始第 ' + pad2(nxt) + ' 阶段的追问？')) {
            WORK_SID = nxt;
            try { localStorage.setItem('pcl-sid', String(nxt)); } catch (e) { /* ignore */ }
            renderWork(STATE.overview);
            actAsk();
          }
        }).catch(function (e) { toast('采纳失败：' + e.message); });
    } else if (act === 'saveFinal') {
      post(API + '/stage/save',
           { project: proj, sid: WORK_SID, final: boxText('finalBox'),
             answers: readAnswers() })
        .then(function (j) { applyState(j.state); toast('已保存定稿修改'); })
        .catch(function (e) { toast('保存失败：' + e.message); });
    }
  });

  function blobDownload(url, name) {
    fetch(url).then(function (r) {
      if (!r.ok) {
        return r.json().then(function (j) { throw new Error(j.error || ('HTTP ' + r.status)); });
      }
      return r.blob();
    }).then(function (b) {
      var a = document.createElement('a');
      a.href = URL.createObjectURL(b);
      a.download = name;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      setTimeout(function () { URL.revokeObjectURL(a.href); }, 4000);
    }).catch(function (e) { toast('导出失败：' + e.message, 8000); });
  }

  ['dlMd', 'dlDocx'].forEach(function (id) {
    $(id).addEventListener('click', function (ev) {
      ev.preventDefault();
      if (!STATE || !STATE.current) { toast('先选择课题'); return; }
      var fmt = (id === 'dlMd') ? 'md' : 'docx';
      blobDownload(API + '/export?project=' + encodeURIComponent(STATE.current) + '&fmt=' + fmt,
                   '研究设计_' + STATE.current + '.' + fmt);
    });
  });
}

function actAsk() {
  streamAction(API + '/stage/ask', { project: STATE.current, sid: WORK_SID }, 'work');
}

/* ------------------------------------------------------------ 收敛推理 */
function bindConvergence() {
  $('btnConv').addEventListener('click', function () {
    streamAction(API + '/convergence', { project: STATE.current }, 'ov');
  });
  $('btnConvStop').addEventListener('click', function () { if (ABORT) { ABORT.abort(); } });
  $('btnWorkStop').addEventListener('click', function () { if (ABORT) { ABORT.abort(); } });
}

/* ------------------------------------------------------------------ 启动 */
function boot() {
  initTheme();
  checkCompat();
  try {
    var s = parseInt(localStorage.getItem('pcl-sid') || '1', 10);
    if (s >= 1 && s <= 10) { WORK_SID = s; }
  } catch (e) { /* ignore */ }
  var s0 = parseInt(QQ.get('sid') || '', 10);      // 深链接：?sid=3 直接打开第三阶段
  if (s0 >= 1 && s0 <= 10) { WORK_SID = s0; }
  $('btnTheme').addEventListener('click', function () {
    applyTheme(document.documentElement.getAttribute('data-theme') === 'dark' ? 'light' : 'dark');
  });
  bindProjects();
  bindWork();
  bindConvergence();
  showView(QQ.get('view') || 'ov');
  loadState(true);
}

if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', boot);
} else {
  boot();
}
