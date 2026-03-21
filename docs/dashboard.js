/* rq Metrics Dashboard — Chart.js rendering logic */

const CHART_COLORS = {
  green: '#3fb950', yellow: '#d29922', red: '#f85149',
  blue: '#58a6ff', purple: '#bc8cff', gray: '#8b949e',
  cyan: '#39d2c0', orange: '#f0883e'
};

const GATE_PALETTE = [
  CHART_COLORS.green, CHART_COLORS.blue, CHART_COLORS.purple,
  CHART_COLORS.yellow, CHART_COLORS.cyan, CHART_COLORS.orange,
  CHART_COLORS.red
];

const DARK_GRID = '#21262d';
const LABEL_COLOR = '#8b949e';
const TEXT_COLOR = '#c9d1d9';

function gradeColor(pct) {
  if (pct >= 80) return 'good';
  if (pct >= 60) return 'warn';
  return 'bad';
}

function heatCellColor(passRate) {
  if (passRate >= 95) return '#238636';
  if (passRate >= 80) return '#2ea043';
  if (passRate >= 60) return '#9e6a03';
  if (passRate >= 40) return '#bd561d';
  return '#da3633';
}

function chartScaleDefaults(yMin, yMax) {
  return {
    y: { min: yMin, max: yMax, grid: { color: DARK_GRID }, ticks: { color: LABEL_COLOR } },
    x: { grid: { color: DARK_GRID }, ticks: { color: LABEL_COLOR } }
  };
}

function renderSummary(s) {
  const el = document.getElementById('summary-cards');
  el.innerHTML = [
    cardHtml('Total Builds', s.total_builds, ''),
    cardHtml('First-Pass Rate', s.first_pass_rate + '%', gradeColor(s.first_pass_rate)),
    cardHtml('Critic Catches', s.critic_catches, 'good'),
    cardHtml('Critic Misses', s.critic_misses, s.critic_misses > 0 ? 'warn' : 'good'),
    cardHtml('Catch Rate', s.catch_rate + '%', gradeColor(s.catch_rate))
  ].join('');
}

function cardHtml(label, value, cls) {
  return '<div class="card"><div class="label">' + label +
    '</div><div class="value ' + cls + '">' + value + '</div></div>';
}

function renderTrend(trends) {
  var ctx = document.getElementById('trend-chart').getContext('2d');
  new Chart(ctx, {
    type: 'line',
    data: {
      labels: trends.map(function(t) { return t.date; }),
      datasets: [{
        label: 'First-Pass Rate %',
        data: trends.map(function(t) { return t.first_pass_rate; }),
        borderColor: CHART_COLORS.green,
        backgroundColor: CHART_COLORS.green + '20',
        fill: true, tension: 0.3, pointRadius: 3
      }, {
        label: 'Catch Rate %',
        data: trends.map(function(t) { return t.catch_rate; }),
        borderColor: CHART_COLORS.blue,
        backgroundColor: CHART_COLORS.blue + '20',
        fill: true, tension: 0.3, pointRadius: 3
      }]
    },
    options: {
      scales: chartScaleDefaults(0, 100),
      plugins: { legend: { labels: { color: TEXT_COLOR } } }
    }
  });
}

function renderGates(gates) {
  var ctx = document.getElementById('gate-chart').getContext('2d');
  var names = Object.keys(gates).sort(function(a, b) {
    return gates[b].miss_rate - gates[a].miss_rate;
  });
  new Chart(ctx, {
    type: 'bar',
    data: {
      labels: names.map(function(n) { return n.replace('gate-', '').replace('.sh', ''); }),
      datasets: [{
        label: 'Miss Rate %',
        data: names.map(function(n) { return gates[n].miss_rate; }),
        backgroundColor: names.map(function(n) {
          return gates[n].miss_rate > 20 ? CHART_COLORS.red : CHART_COLORS.yellow;
        }),
        borderRadius: 3
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

function renderRepos(repos) {
  var tbody = document.querySelector('#repo-table tbody');
  var sorted = Object.entries(repos).sort(function(a, b) {
    return b[1].total_builds - a[1].total_builds;
  });
  tbody.innerHTML = sorted.map(function(entry) {
    var name = entry[0];
    var s = entry[1];
    return '<tr><td>' + name + '</td><td>' + s.total_builds +
      '</td><td class="' + gradeColor(s.first_pass_rate) + '">' + s.first_pass_rate +
      '%</td><td class="' + gradeColor(s.catch_rate) + '">' + s.catch_rate + '%</td></tr>';
  }).join('');
}

function renderHeatmapHeaders(gates) {
  var thead = document.querySelector('#heatmap-table thead tr');
  thead.innerHTML = '<th>Repository</th>' + gates.map(function(g) {
    return '<th>' + g + '</th>';
  }).join('');
}

function renderHeatmap(matrix, gates) {
  var container = document.getElementById('heatmap-body');
  var repos = Object.keys(matrix).sort();
  if (repos.length === 0) {
    var colspan = gates.length + 1;
    container.innerHTML = '<tr><td colspan="' + colspan + '" class="empty">No gate data yet.</td></tr>';
    return;
  }
  container.innerHTML = repos.map(function(repo) {
    var cells = gates.map(function(g) {
      var d = (matrix[repo] || {})[g];
      if (!d || d.runs === 0) return '<td class="heat-cell" style="background:#161b22">--</td>';
      var bg = heatCellColor(d.pass_rate);
      return '<td class="heat-cell" style="background:' + bg + '">' + d.pass_rate + '%</td>';
    }).join('');
    return '<tr><td>' + repo + '</td>' + cells + '</tr>';
  }).join('');
}

function renderGateTrends(perGateStats, violationTrends) {
  if (!violationTrends || violationTrends.length === 0) return;
  var ctx = document.getElementById('gate-trend-chart').getContext('2d');
  var gates = Object.keys(perGateStats);
  var labels = violationTrends.map(function(t) { return t.date; });
  var datasets = gates.map(function(gate, i) {
    return {
      label: gate,
      data: violationTrends.map(function(t) { return (t.violations || {})[gate] || 0; }),
      borderColor: GATE_PALETTE[i % GATE_PALETTE.length],
      backgroundColor: GATE_PALETTE[i % GATE_PALETTE.length] + '20',
      fill: false, tension: 0.3, pointRadius: 2
    };
  });
  new Chart(ctx, {
    type: 'line',
    data: { labels: labels, datasets: datasets },
    options: {
      scales: chartScaleDefaults(0, undefined),
      plugins: { legend: { labels: { color: TEXT_COLOR } } }
    }
  });
}

function renderViolationBars(violationTrends) {
  if (!violationTrends || violationTrends.length === 0) return;
  var ctx = document.getElementById('violation-chart').getContext('2d');
  var allGates = {};
  violationTrends.forEach(function(t) {
    Object.keys(t.violations || {}).forEach(function(g) { allGates[g] = true; });
  });
  var gates = Object.keys(allGates).sort();
  var labels = violationTrends.map(function(t) { return t.date; });
  var datasets = gates.map(function(gate, i) {
    return {
      label: gate,
      data: violationTrends.map(function(t) { return (t.violations || {})[gate] || 0; }),
      backgroundColor: GATE_PALETTE[i % GATE_PALETTE.length],
      borderRadius: 2
    };
  });
  new Chart(ctx, {
    type: 'bar',
    data: { labels: labels, datasets: datasets },
    options: {
      scales: {
        x: { stacked: true, grid: { color: DARK_GRID }, ticks: { color: LABEL_COLOR } },
        y: { stacked: true, grid: { color: DARK_GRID }, ticks: { color: LABEL_COLOR } }
      },
      plugins: { legend: { labels: { color: TEXT_COLOR } } }
    }
  });
}

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
      '</td><td class="' + gradeColor(s.pass_rate) + '">' + s.pass_rate +
      '%</td><td class="' + gradeColor(100 - parseFloat(failRate)) + '">' + failRate +
      '%</td><td>' + s.avg_violations + '</td></tr>';
  }).join('');
}

function initDashboard(data) {
  var gates = data.known_gates || [];
  renderSummary(data.summary);
  renderTrend(data.trends);
  renderGates(data.per_gate);
  renderRepos(data.per_repo);
  renderHeatmapHeaders(gates);
  renderHeatmap(data.per_gate_per_repo || {}, gates);
  renderGateTrends(data.per_gate_stats || {}, data.violation_trends || []);
  renderViolationBars(data.violation_trends || []);
  renderTopOffenders(data.per_gate_stats || {});
  if (typeof initNewCharts === 'function') {
    initNewCharts(data);
  }
}

if (typeof window !== 'undefined') {
  fetch('data.json')
    .then(function(r) { return r.json(); })
    .then(initDashboard)
    .catch(function() {
      document.getElementById('summary-cards').innerHTML =
        '<div class="empty">No data yet. Metrics will appear after the first pair-build run.</div>';
    });
}

if (typeof module !== 'undefined' && module.exports) {
  module.exports = {
    gradeColor: gradeColor, heatCellColor: heatCellColor, chartScaleDefaults: chartScaleDefaults, cardHtml: cardHtml,
    CHART_COLORS: CHART_COLORS, GATE_PALETTE: GATE_PALETTE, DARK_GRID: DARK_GRID, LABEL_COLOR: LABEL_COLOR, TEXT_COLOR: TEXT_COLOR
  };
}
