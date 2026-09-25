/* 组学研究设计工作台 · Web 预览版 —— 前端逻辑
   Phase 0：四个视图全部可看；「总览」的收敛推理可跑（SSE 流式 + reason 模式）。
   业务判断全部在服务端（复用桌面版同一套代码），这里只负责显示与交互。 */
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
var QQ = new URLSearchParams(location.search);

function $(id) { return document.getElementById(id); }

function esc(s) {
  return String(s === null || s === undefined ? '' : s)
    .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;');
}

function toast(msg, ms) {
  var t = $('toast');
  t.textContent = msg;
  t.hidden = false;
  clearTimeout(toast._t);
  toast._t = setTimeout(function () { t.hidden = true; }, ms || 3200);
}

function pct(a, b) { return Math.round(100 * a / Math.max(1, b)); }

function bar(done, total, cls) {
  var p = pct(done, total);
  var k = cls || (p >= 100 ? 'ok' : (p > 0 ? 'warn' : ''));
  return '<div class="bar ' + k + '" title="' + done + '/' + total + '"><i style="width:' + p + '%"></i></div>';
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
           document.documentElement.classList && window.Promise;
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

/* -------------------------------------------------------------- 顶栏渲染 */
function renderTopbar(d) {
  $('verLine').textContent = 'Web 预览版 v' + d.version + ' · Python ' + d.python +
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
  var dis = !d.current;
  $('btnRename').disabled = dis;
  $('btnDelete').disabled = dis;
  $('btnConv').disabled = dis || !(window.fetch && window.TextDecoder);
}

/* ------------------------------------------------------------ 工作台视图 */
function renderWork(ov) {
  $('rawDesign').textContent = (ov.raw_design || '').trim() || '（空）';
  $('workStages').innerHTML = (ov.stages || []).map(function (s) {
    var det = [];
    if (s.body_len) { det.push((s.is_final ? '已定稿 ' : '草稿 ') + s.body_len + ' 字'); }
    if (s.questions) { det.push('追问 ' + s.questions + (s.answers ? '/' + s.answers + ' 已答' : '')); }
    if (s.checks) { det.push('检查项 ' + s.checks); }
    return '<div class="srow">' +
      '<div class="num">' + s.id + '</div>' +
      '<div class="body"><b>' + esc(s.title) + '</b><span class="spec">' + esc(s.spec) + '</span>' +
      '<div class="desc">' + esc(det.join(' · ') || s.goal || '（尚未开始）') + '</div></div>' +
      '<div class="side"><span class="state ' + s.status + '">' + esc(s.label) + '</span></div>' +
      '</div>';
  }).join('');
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
      '<div class="body"><b>' + esc(r.title) + '</b><span class="spec">' + esc(r.spec) + '</span>' +
      '<div class="desc">' + esc(r.desc || '') + (extra.length ? '　｜　' + esc(extra.join(' · ')) : '') + '</div></div>' +
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
    '<span>统计 ' + (t.stat_done || 0) + '/' + (ov.stat || []).length + ' 环节（进行中 ' + (t.stat_doing || 0) +
    '）· 自检 ' + (t.stat_ticks || 0) + '/' + (t.stat_checks || 0) + '</span>' +
    '<span>SCI ' + (t.shape_done || 0) + '/' + (ov.shape || []).length + ' 章（进行中 ' + (t.shape_doing || 0) +
    '）· 自检 ' + (t.shape_ticks || 0) + '/' + (t.shape_checks || 0) + '</span>';
}

function renderStageTable(ov) {
  var rows = ov.stages || [];
  $('ovStages').querySelector('tbody').innerHTML = rows.map(function (s) {
    return '<tr><td class="num">' + s.id + '</td><td>' + esc(s.title) + '</td>' +
      '<td class="dim">' + esc(s.spec) + '</td>' +
      '<td><span class="state ' + s.status + '">' + esc(s.label) + '</span></td>' +
      '<td class="center">' + (s.is_final ? '✅ ' + s.body_len + ' 字' : (s.body_len ? '◐ 草稿' : '—')) + '</td>' +
      '<td class="center">' + (s.questions || '—') + '</td>' +
      '<td class="center">' + (s.checks || '—') + '</td></tr>';
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
function loadState(keepView) {
  var q = STATE && STATE.current ? STATE.current : (QQ.get('project') || '');
  return fetch(API + '/state?project=' + encodeURIComponent(q), { cache: 'no-store' })
    .then(function (r) { return r.json(); })
    .then(function (d) {
      STATE = d;
      renderTopbar(d);
      if (d.overview) {
        renderWork(d.overview);
        renderScope('statRows', d.overview.stat || []);
        renderScope('shapeRows', d.overview.shape || []);
        renderLanes(d.overview);
        renderStageTable(d.overview);
        renderConvergence(d.convergence);
      } else {
        $('rawDesign').textContent = '（还没有课题，点右上「新建」）';
        $('workStages').innerHTML = '<div class="empty">还没有课题。</div>';
        $('statRows').innerHTML = '<div class="empty">还没有课题。</div>';
        $('shapeRows').innerHTML = '<div class="empty">还没有课题。</div>';
        $('laneBox').innerHTML = '';
        $('digestBox').innerHTML = '';
        $('projMeta').innerHTML = '';
        $('ovStages').querySelector('tbody').innerHTML = '';
        renderConvergence({});
      }
      $('footLeft').textContent = '服务端 ' + d.app + ' v' + d.version +
        '　·　课题目录：' + (d.current_file || '—');
      $('footRight').textContent = '本页为只读预览（收敛推理除外）· 数据文件与桌面版共用';
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
      return loadState(true);
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

/* ------------------------------------------------------------ 收敛推理 */
function liveAppend(kind, text) {
  var box = $('convText');
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

function bindConvergence() {
  $('btnConv').addEventListener('click', runConvergence);
  $('btnConvStop').addEventListener('click', function () {
    if (ABORT) { ABORT.abort(); }
  });
}

function runConvergence() {
  if (!STATE || !STATE.current) { toast('先选择或新建一个课题'); return; }
  var box = $('convText');
  box.textContent = '';
  liveAppend._rz = null;
  $('convLive').hidden = false;
  $('btnConv').disabled = true;
  $('btnConv').textContent = '推理中…';
  $('btnConvStop').hidden = false;
  ABORT = ('AbortController' in window) ? new AbortController() : null;
  $('convState').textContent = '正在推理…';
  $('convState').className = 'tag warn';

  var opts = {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ project: STATE.current })
  };
  if (ABORT) { opts.signal = ABORT.signal; }

  fetch(API + '/convergence', opts).then(function (res) {
    if (!res.ok) {
      return res.json().then(function (j) { throw new Error(j.error || ('HTTP ' + res.status)); });
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
            handleEvent(obj, box);
          });
        }
        return pump();
      });
    }
    return pump();
  }).catch(function (e) {
    if (e && e.name === 'AbortError') {
      liveAppend('status', '已停止接收（服务端仍会完成本次推理并落盘）');
      return;
    }
    liveAppend('status', '出错：' + e.message);
    toast('推理失败：' + e.message);
    $('convState').textContent = '推理失败';
    $('convState').className = 'tag bad';
  }).then(function () {
    ABORT = null;
    $('btnConv').disabled = false;
    $('btnConv').textContent = '重新推理';
    $('btnConvStop').hidden = true;
  });
}

function handleEvent(obj, box) {
  if (obj.type === 'status') {
    liveAppend('status', obj.text || '');
  } else if (obj.type === 'reasoning' || obj.type === 'content') {
    liveAppend(obj.type, obj.text || '');
  } else if (obj.type === 'error') {
    liveAppend('status', '错误：' + (obj.text || ''));
    toast('推理失败：' + (obj.text || '').slice(0, 90));
    $('convState').textContent = '推理失败';
    $('convState').className = 'tag bad';
  } else if (obj.type === 'done') {
    if (!obj.ok) { return; }
    renderConvergence(obj.convergence || {});
    var u = obj.usage || {};
    liveAppend('status', '完成：' + (obj.chapters || 0) + ' 章 · ' + (obj.actions || 0) +
      ' 条动作' + (u.total_tokens ? ' · ' + u.total_tokens + ' tokens' : '') +
      (obj.saved === false ? '　[落盘失败：' + (obj.save_error || '') + ']' : '　已落盘'));
    toast('收敛推理完成：' + (obj.chapters || 0) + ' 章');
    loadState(true);
  }
}

/* ------------------------------------------------------------------ 启动 */
function boot() {
  initTheme();
  checkCompat();
  $('btnTheme').addEventListener('click', function () {
    applyTheme(document.documentElement.getAttribute('data-theme') === 'dark' ? 'light' : 'dark');
  });
  bindProjects();
  bindConvergence();
  showView(QQ.get('view') || 'ov');
  loadState(true);
}

if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', boot);
} else {
  boot();
}
