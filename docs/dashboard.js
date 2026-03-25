/* rq Metrics Dashboard — Chart.js rendering */

const CHART_COLORS = {
  green: '#34d399', yellow: '#fbbf24', red: '#f87171',
  blue: '#60a5fa', purple: '#a78bfa', gray: '#4a5568',
  cyan: '#22d3ee', orange: '#fb923c'
};

const GATE_PALETTE = [
  CHART_COLORS.cyan, CHART_COLORS.blue, CHART_COLORS.purple,
  CHART_COLORS.green, CHART_COLORS.orange, CHART_COLORS.yellow,
  CHART_COLORS.red
];

/* ── Stable color map: same label → same color everywhere ── */
const LABEL_COLORS_MAP = {
  'filesize': '#34d399',
  'complexity': '#60a5fa',
  'dead-code': '#a78bfa',
  'lint': '#fbbf24',
  'tests': '#22d3ee',
  'test-quality': '#fb923c',
  'coverage': '#f87171',
  'qa': '#818cf8',
  'design-audit': '#2dd4bf',
  'performance': '#c084fc',
  'all': '#60a5fa',
  'build': '#34d399',
  'review': '#fbbf24',
  'ship': '#22d3ee',
};
var _labelColorIdx = 0;
function colorForLabel(label) {
  if (LABEL_COLORS_MAP[label]) return LABEL_COLORS_MAP[label];
  var fallback = GATE_PALETTE[_labelColorIdx % GATE_PALETTE.length];
  _labelColorIdx++;
  LABEL_COLORS_MAP[label] = fallback;
  return fallback;
}
function colorsForLabels(labels) {
  return labels.map(function(l) { return colorForLabel(l); });
}
function bordersForLabels(labels) {
  return labels.map(function(l) { return colorForLabel(l); });
}
function fillsForLabels(labels) {
  return labels.map(function(l) { return colorForLabel(l) + '99'; });
}

const DARK_GRID = 'rgba(255,255,255,0.04)';
const LABEL_COLOR = '#4a5568';
const TEXT_COLOR = '#7a8ba4';

/* ── Chart.js defaults ──────────────────────────── */
if (typeof Chart !== 'undefined') {
  Chart.defaults.font.family = "'DM Mono', 'SF Mono', monospace";
  Chart.defaults.font.size = 10;
  Chart.defaults.color = LABEL_COLOR;
}

function gradeColor(pct) {
  if (pct >= 80) return 'v-good';
  if (pct >= 60) return 'v-warn';
  return 'v-bad';
}

function heatCellColor(passRate) {
  if (passRate >= 95) return '#166534';
  if (passRate >= 80) return '#15803d';
  if (passRate >= 60) return '#854d0e';
  if (passRate >= 40) return '#9a3412';
  return '#991b1b';
}

function chartScaleDefaults(yMin, yMax) {
  return {
    y: { min: yMin, max: yMax, grid: { color: DARK_GRID }, ticks: { color: LABEL_COLOR, font: { size: 9 } } },
    x: { grid: { color: DARK_GRID }, ticks: { color: LABEL_COLOR, font: { size: 9 } } }
  };
}

/* ── Hero strip ──────────────────────────────────── */
function renderHero(s) {
  var el = document.getElementById('hero-strip');
  var fpClass = gradeColor(s.first_pass_rate);
  var crClass = gradeColor(s.catch_rate);

  el.innerHTML =
    '<div class="hero-metric primary">' +
      '<div class="label">First-Pass Rate</div>' +
      '<div class="value ' + fpClass + '">' + s.first_pass_rate + '%</div>' +
      '<div class="sub">' + s.first_pass_count + ' of ' + s.total_builds + ' builds passed first try</div>' +
    '</div>' +
    '<div class="hero-metric">' +
      '<div class="label">Total Builds</div>' +
      '<div class="value v-neutral">' + s.total_builds + '</div>' +
    '</div>' +
    '<div class="hero-metric">' +
      '<div class="label">Critic Catches</div>' +
      '<div class="value v-neutral">' + s.critic_catches + '</div>' +
    '</div>' +
    '<div class="hero-metric">' +
      '<div class="label">Critic Misses</div>' +
      '<div class="value ' + (s.critic_misses > 0 ? 'v-warn' : 'v-good') + '">' + s.critic_misses + '</div>' +
    '</div>' +
    '<div class="hero-metric">' +
      '<div class="label">Catch Rate</div>' +
      '<div class="value ' + crClass + '">' + s.catch_rate + '%</div>' +
    '</div>';
}

/* ── Trend chart ─────────────────────────────────── */
function renderTrend(trends) {
  var ctx = document.getElementById('trend-chart');
  if (!ctx) return;

  var badge = document.getElementById('trend-period');
  if (badge && trends.length > 0) {
    badge.textContent = trends[0].date + ' → ' + trends[trends.length - 1].date;
  }

  new Chart(ctx.getContext('2d'), {
    type: 'line',
    data: {
      labels: trends.map(function(t) { return t.date; }),
      datasets: [{
        label: 'First-Pass %',
        data: trends.map(function(t) { return t.first_pass_rate; }),
        borderColor: CHART_COLORS.green,
        backgroundColor: 'rgba(52, 211, 153, 0.08)',
        fill: true, tension: 0.35, pointRadius: 4,
        pointBackgroundColor: CHART_COLORS.green,
        pointBorderColor: '#0f1319',
        pointBorderWidth: 2, borderWidth: 2
      }, {
        label: 'Catch Rate %',
        data: trends.map(function(t) { return t.catch_rate; }),
        borderColor: CHART_COLORS.cyan,
        backgroundColor: 'rgba(34, 211, 238, 0.05)',
        fill: true, tension: 0.35, pointRadius: 4,
        pointBackgroundColor: CHART_COLORS.cyan,
        pointBorderColor: '#0f1319',
        pointBorderWidth: 2, borderWidth: 2
      }]
    },
    options: {
      scales: chartScaleDefaults(0, 100),
      plugins: {
        legend: { labels: { color: TEXT_COLOR, boxWidth: 8, padding: 16, font: { size: 10 } } }
      }
    }
  });
}

/* ── Critic miss rate by gate ────────────────────── */
function renderGates(gates) {
  var ctx = document.getElementById('gate-chart');
  if (!ctx) return;
  var names = Object.keys(gates).sort(function(a, b) {
    return gates[b].miss_rate - gates[a].miss_rate;
  });
  new Chart(ctx.getContext('2d'), {
    type: 'bar',
    data: {
      labels: names,
      datasets: [{
        label: 'Miss Rate %',
        data: names.map(function(n) { return gates[n].miss_rate; }),
        backgroundColor: fillsForLabels(names),
        borderColor: bordersForLabels(names),
        borderWidth: 1, borderRadius: 3
      }]
    },
    options: {
      indexAxis: 'y',
      scales: {
        x: { min: 0, max: 100, grid: { color: DARK_GRID }, ticks: { color: LABEL_COLOR } },
        y: { grid: { display: false }, ticks: { color: TEXT_COLOR } }
      },
      plugins: { legend: { display: false } }
    }
  });
}

/* ── Leaderboard ────────────────────────────────── */
function escapeHtml(str) {
  var div = document.createElement('div');
  div.appendChild(document.createTextNode(str));
  return div.innerHTML;
}

function displayName(entry) {
  var name = entry.display_name || entry.user || '';
  if (name && name !== 'unknown') return name;
  var email = entry.email || entry.user || '';
  if (email.indexOf('@') !== -1) return email.split('@')[0];
  return name || 'unknown';
}

function renderLeaderboard(leaderboard) {
  var tbody = document.querySelector('#leaderboard-table tbody');
  var badge = document.getElementById('leaderboard-count');
  if (badge) badge.textContent = (leaderboard || []).length + ' users';
  if (!tbody || !leaderboard || leaderboard.length === 0) {
    if (tbody) tbody.innerHTML = '<tr><td colspan="6" class="empty">No user data yet.</td></tr>';
    return;
  }
  tbody.innerHTML = leaderboard.map(function(e) {
    var fpClass = gradeColor(e.first_pass_rate);
    var name = escapeHtml(displayName(e));
    return '<tr>' +
      '<td style="color:var(--accent);font-weight:500">' + e.rank + '</td>' +
      '<td>' + name + '</td>' +
      '<td>' + e.total_builds + '</td>' +
      '<td class="' + fpClass.replace('v-', '') + '">' + e.first_pass_rate + '%</td>' +
      '<td>' + e.avg_violations + '</td>' +
      '<td>' + e.avg_fix_cycles + '</td>' +
      '</tr>';
  }).join('');
}

/* ── Per-repo table ──────────────────────────────── */
function renderRepos(repos) {
  var tbody = document.querySelector('#repo-table tbody');
  var sorted = Object.entries(repos).sort(function(a, b) {
    return b[1].total_builds - a[1].total_builds;
  });
  tbody.innerHTML = sorted.map(function(entry) {
    var name = entry[0];
    var s = entry[1];
    return '<tr><td>' + name + '</td><td>' + s.total_builds +
      '</td><td class="' + gradeColor(s.first_pass_rate).replace('v-', '') + '">' + s.first_pass_rate +
      '%</td><td class="' + gradeColor(s.catch_rate).replace('v-', '') + '">' + s.catch_rate + '%</td></tr>';
  }).join('');
}

/* ── Heatmap ─────────────────────────────────────── */
function renderHeatmapHeaders(gates) {
  var thead = document.querySelector('#heatmap-table thead tr');
  thead.innerHTML = '<th>Repo</th>' + gates.map(function(g) {
    return '<th style="font-size:0.55rem;writing-mode:vertical-lr;text-align:center;padding:0.5rem 0.25rem;">' + g + '</th>';
  }).join('');
}

function renderHeatmap(matrix, gates) {
  var container = document.getElementById('heatmap-body');
  var repos = Object.keys(matrix).sort();
  if (repos.length === 0) {
    container.innerHTML = '<tr><td colspan="' + (gates.length + 1) + '" class="empty">No data.</td></tr>';
    return;
  }
  container.innerHTML = repos.map(function(repo) {
    var cells = gates.map(function(g) {
      var d = (matrix[repo] || {})[g];
      if (!d || d.runs === 0) return '<td class="heat-cell" style="background:var(--bg-raised)">—</td>';
      var bg = heatCellColor(d.pass_rate);
      return '<td class="heat-cell" style="background:' + bg + '">' + d.pass_rate + '%</td>';
    }).join('');
    return '<tr><td>' + repo + '</td>' + cells + '</tr>';
  }).join('');
}

/* ── Violation trends (stacked bar, not spaghetti lines) ── */
function renderViolationBars(violationTrends) {
  if (!violationTrends || violationTrends.length === 0) return;
  var ctx = document.getElementById('violation-chart');
  if (!ctx) return;
  var allGates = {};
  violationTrends.forEach(function(t) {
    Object.keys(t.violations || {}).forEach(function(g) {
      if ((t.violations[g] || 0) > 0) allGates[g] = true;
    });
  });
  var gates = Object.keys(allGates).sort();
  if (gates.length === 0) return;
  var labels = violationTrends.map(function(t) { return t.date; });
  var datasets = gates.map(function(gate) {
    return {
      label: gate,
      data: violationTrends.map(function(t) { return (t.violations || {})[gate] || 0; }),
      backgroundColor: colorForLabel(gate) + '99',
      borderColor: colorForLabel(gate),
      borderWidth: 1, borderRadius: 2
    };
  });
  new Chart(ctx.getContext('2d'), {
    type: 'bar',
    data: { labels: labels, datasets: datasets },
    options: {
      scales: {
        x: { stacked: true, grid: { color: DARK_GRID }, ticks: { color: LABEL_COLOR } },
        y: { stacked: true, grid: { color: DARK_GRID }, ticks: { color: LABEL_COLOR } }
      },
      plugins: { legend: { labels: { color: TEXT_COLOR, boxWidth: 8, padding: 12, font: { size: 9 } } } }
    }
  });
}

/* ── Gate stats table ────────────────────────────── */
function renderTopOffenders(perGateStats) {
  var tbody = document.querySelector('#offenders-table tbody');
  var sorted = Object.entries(perGateStats).sort(function(a, b) {
    return a[1].pass_rate - b[1].pass_rate;
  });
  tbody.innerHTML = sorted.map(function(entry) {
    var gate = entry[0];
    var s = entry[1];
    var failRate = s.runs > 0 ? (100 - s.pass_rate).toFixed(1) : '0.0';
    return '<tr><td>' + gate + '</td><td>' + s.runs +
      '</td><td class="' + gradeColor(s.pass_rate).replace('v-', '') + '">' + s.pass_rate +
      '%</td><td class="' + gradeColor(100 - parseFloat(failRate)).replace('v-', '') + '">' + failRate +
      '%</td><td>' + s.avg_violations + '</td></tr>';
  }).join('');
}

/* ── Meta info ───────────────────────────────────── */
function renderMeta(data) {
  var el = document.getElementById('meta-info');
  if (!el) return;
  var ts = (data.generated_at || '').replace('T', ' ').replace('Z', ' UTC');
  el.textContent = data.total_records + ' records · updated ' + ts;
}

/* ── Chart instance tracking (for destroy on re-render) ── */
var _chartInstances = {};

function destroyCharts() {
  Object.keys(_chartInstances).forEach(function(id) {
    if (_chartInstances[id]) { _chartInstances[id].destroy(); }
  });
  _chartInstances = {};
}

/* Patch Chart constructor to track instances by canvas id */
var _origChart = typeof Chart !== 'undefined' ? Chart : null;
function TrackedChart(ctx, config) {
  var canvas = ctx instanceof HTMLCanvasElement ? ctx : ctx.canvas || ctx;
  var id = canvas.id || canvas.getAttribute('id');
  if (id && _chartInstances[id]) { _chartInstances[id].destroy(); }
  var inst = new _origChart(ctx, config);
  if (id) { _chartInstances[id] = inst; }
  return inst;
}
if (_origChart) {
  TrackedChart.defaults = _origChart.defaults;
  TrackedChart.register = _origChart.register;
}

/* ── Repo filter ─────────────────────────────────── */
var _fullData = null;

function populateRepoFilter(repos) {
  var select = document.getElementById('repo-filter');
  if (!select) return;
  var current = select.value;
  select.innerHTML = '<option value="">All repos</option>';
  (repos || []).forEach(function(repo) {
    var opt = document.createElement('option');
    opt.value = repo;
    opt.textContent = repo;
    if (repo === current) opt.selected = true;
    select.appendChild(opt);
  });
}

function getFilteredData(data, repo) {
  if (!repo) return data;
  var detail = (data.by_repo_detail || {})[repo];
  if (!detail) return data;
  var filtered = {};
  Object.keys(data).forEach(function(k) { filtered[k] = data[k]; });
  Object.keys(detail).forEach(function(k) { filtered[k] = detail[k]; });
  return filtered;
}

/* ── Init ────────────────────────────────────────── */
function renderDashboard(data) {
  destroyCharts();
  var gates = data.known_gates || [];
  renderMeta(data);
  renderHero(data.summary);
  renderLeaderboard(data.leaderboard || []);
  renderTrend(data.trends);
  renderGates(data.per_gate);
  renderRepos(data.per_repo);
  renderHeatmapHeaders(gates);
  renderHeatmap(data.per_gate_per_repo || {}, gates);
  renderViolationBars(data.violation_trends || []);
  renderTopOffenders(data.per_gate_stats || {});
  if (typeof initNewCharts === 'function') {
    initNewCharts(data);
  }
}

function populateUserFilter(users, perUser) {
  var select = document.getElementById('user-filter');
  if (!select) return;
  var current = select.value;
  select.innerHTML = '<option value="">All users</option>';
  (users || []).forEach(function(user) {
    var opt = document.createElement('option');
    opt.value = user;
    var entry = (perUser && perUser[user]) ? perUser[user] : { user: user };
    opt.textContent = displayName(entry);
    if (user === current) opt.selected = true;
    select.appendChild(opt);
  });
}

function getFilteredByUser(data, user) {
  if (!user) return data;
  var detail = (data.by_user_detail || {})[user];
  if (!detail) return data;
  var filtered = {};
  Object.keys(data).forEach(function(k) { filtered[k] = data[k]; });
  Object.keys(detail).forEach(function(k) { filtered[k] = detail[k]; });
  return filtered;
}

var _activeRepo = '';
var _activeUser = '';

function applyFilters() {
  var data = _fullData;
  if (_activeRepo) data = getFilteredData(data, _activeRepo);
  if (_activeUser) data = getFilteredByUser(data, _activeUser);
  renderDashboard(data);
}

function initDashboard(data) {
  _fullData = data;
  populateRepoFilter(data.repos || Object.keys(data.per_repo || {}));
  populateUserFilter(data.users || [], data.per_user || {});
  renderDashboard(data);

  var repoSelect = document.getElementById('repo-filter');
  if (repoSelect) {
    repoSelect.addEventListener('change', function() {
      _activeRepo = this.value;
      applyFilters();
    });
  }

  var userSelect = document.getElementById('user-filter');
  if (userSelect) {
    userSelect.addEventListener('change', function() {
      _activeUser = this.value;
      applyFilters();
    });
  }
}

if (typeof window !== 'undefined') {
  /* Replace Chart with tracked version for re-render support */
  if (_origChart) { Chart = TrackedChart; }

  fetch('data.json')
    .then(function(r) { return r.json(); })
    .then(initDashboard)
    .catch(function(e) {
      console.error('Dashboard load failed:', e);
      document.getElementById('hero-strip').innerHTML =
        '<div class="hero-metric primary"><div class="label">Status</div><div class="value v-warn">No data</div><div class="sub">Metrics will appear after the first build run.</div></div>';
    });
}

if (typeof module !== 'undefined' && module.exports) {
  module.exports = {
    gradeColor: gradeColor, heatCellColor: heatCellColor, chartScaleDefaults: chartScaleDefaults,
    CHART_COLORS: CHART_COLORS, GATE_PALETTE: GATE_PALETTE, DARK_GRID: DARK_GRID, LABEL_COLOR: LABEL_COLOR, TEXT_COLOR: TEXT_COLOR
  };
}
