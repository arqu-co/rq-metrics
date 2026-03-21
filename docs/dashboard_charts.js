/* rq Metrics Dashboard — New chart renderers for findings data */

/* In Node.js, pull shared constants from dashboard.js.
   In the browser, dashboard.js loads first and these are already global. */
if (typeof require !== 'undefined') {
  var _dash = require('./dashboard.js');
  if (typeof CHART_COLORS === 'undefined') var CHART_COLORS = _dash.CHART_COLORS;
  if (typeof DARK_GRID === 'undefined') var DARK_GRID = _dash.DARK_GRID;
  if (typeof LABEL_COLOR === 'undefined') var LABEL_COLOR = _dash.LABEL_COLOR;
  if (typeof TEXT_COLOR === 'undefined') var TEXT_COLOR = _dash.TEXT_COLOR;
}

function findingsCardHtml(label, value, subtitle) {
  return '<div class="card"><div class="label">' + label +
    '</div><div class="value">' + value +
    '</div><div class="card-sub">' + (subtitle || '') + '</div></div>';
}

function renderFindingsCards(data) {
  var el = document.getElementById('findings-cards');
  if (!el) return;
  var findings = data.findings_summary || { by_gate: {}, by_rule: {} };
  var cycles = data.fix_cycles || { distribution: {}, avg: 0 };
  var timing = data.timing_stats || { by_gate: {}, by_phase: {} };

  var totalFindings = sumValues(findings.by_gate);
  var totalCycles = sumValues(cycles.distribution);
  var slowestGate = findSlowestGate(timing.by_gate);

  el.innerHTML = [
    findingsCardHtml('Total Findings', totalFindings, 'across all gates'),
    findingsCardHtml('Fix Cycles', totalCycles, 'avg ' + cycles.avg + ' runs'),
    findingsCardHtml('Avg Runs to Green', cycles.avg || '0', ''),
    findingsCardHtml('Slowest Gate', slowestGate.name, slowestGate.time)
  ].join('');
}

function sumValues(obj) {
  var total = 0;
  var keys = Object.keys(obj || {});
  for (var i = 0; i < keys.length; i++) {
    total += obj[keys[i]];
  }
  return total;
}

function findSlowestGate(byGate) {
  var slowest = { name: '--', time: '' };
  var maxAvg = 0;
  var keys = Object.keys(byGate || {});
  for (var i = 0; i < keys.length; i++) {
    var avg = byGate[keys[i]].avg_ms || 0;
    if (avg > maxAvg) {
      maxAvg = avg;
      slowest = { name: keys[i], time: Math.round(avg) + 'ms' };
    }
  }
  return slowest;
}

function renderFindingsByGate(findings) {
  var ctx = document.getElementById('findings-gate-chart');
  if (!ctx) return;
  var byGate = findings.by_gate || {};
  var names = Object.keys(byGate).sort(function(a, b) {
    return byGate[b] - byGate[a];
  });
  if (names.length === 0) return;
  new Chart(ctx.getContext('2d'), {
    type: 'bar',
    data: {
      labels: names,
      datasets: [{
        label: 'Violations',
        data: names.map(function(n) { return byGate[n]; }),
        backgroundColor: CHART_COLORS.blue,
        borderRadius: 3
      }]
    },
    options: {
      indexAxis: 'y',
      scales: {
        x: { grid: { color: DARK_GRID }, ticks: { color: LABEL_COLOR } },
        y: { grid: { display: false }, ticks: { color: TEXT_COLOR } }
      },
      plugins: { legend: { display: false } }
    }
  });
}

function renderTopViolationTypes(topViolations) {
  var ctx = document.getElementById('top-violations-chart');
  if (!ctx || !topViolations || topViolations.length === 0) return;
  var top10 = topViolations.slice(0, 10);
  new Chart(ctx.getContext('2d'), {
    type: 'bar',
    data: {
      labels: top10.map(function(v) { return v.type; }),
      datasets: [{
        label: 'Count',
        data: top10.map(function(v) { return v.count; }),
        backgroundColor: CHART_COLORS.orange,
        borderRadius: 3
      }]
    },
    options: {
      scales: {
        x: { grid: { color: DARK_GRID }, ticks: { color: LABEL_COLOR } },
        y: { grid: { color: DARK_GRID }, ticks: { color: LABEL_COLOR } }
      },
      plugins: { legend: { display: false } }
    }
  });
}

function renderFixCyclesChart(fixCycles) {
  var ctx = document.getElementById('fix-cycles-chart');
  if (!ctx) return;
  var dist = fixCycles.distribution || {};
  var keys = Object.keys(dist).sort();
  if (keys.length === 0) return;
  var colors = keys.map(function(k) {
    var n = parseInt(k, 10);
    if (n === 1) return CHART_COLORS.green;
    if (n === 2) return CHART_COLORS.yellow;
    return CHART_COLORS.red;
  });
  new Chart(ctx.getContext('2d'), {
    type: 'bar',
    data: {
      labels: keys.map(function(k) { return k + ' run' + (k === '1' ? '' : 's'); }),
      datasets: [{
        data: keys.map(function(k) { return dist[k]; }),
        backgroundColor: colors,
        borderRadius: 3
      }]
    },
    options: {
      scales: {
        x: { grid: { color: DARK_GRID }, ticks: { color: LABEL_COLOR } },
        y: { grid: { color: DARK_GRID }, ticks: { color: LABEL_COLOR } }
      },
      plugins: { legend: { display: false } }
    }
  });
}

function renderGateTimingChart(timingStats) {
  var ctx = document.getElementById('gate-timing-chart');
  if (!ctx) return;
  var byGate = timingStats.by_gate || {};
  var names = Object.keys(byGate).sort();
  if (names.length === 0) return;
  new Chart(ctx.getContext('2d'), {
    type: 'bar',
    data: {
      labels: names,
      datasets: [{
        label: 'Avg (ms)',
        data: names.map(function(n) { return byGate[n].avg_ms || 0; }),
        backgroundColor: CHART_COLORS.cyan,
        borderRadius: 3
      }]
    },
    options: {
      indexAxis: 'y',
      scales: {
        x: { grid: { color: DARK_GRID }, ticks: { color: LABEL_COLOR } },
        y: { grid: { display: false }, ticks: { color: TEXT_COLOR } }
      },
      plugins: { legend: { display: false } }
    }
  });
}

function renderPhaseBreakdownChart(phaseBreakdown) {
  var ctx = document.getElementById('phase-breakdown-chart');
  if (!ctx) return;
  var phases = Object.keys(phaseBreakdown).sort();
  if (phases.length === 0) return;
  new Chart(ctx.getContext('2d'), {
    type: 'bar',
    data: {
      labels: phases,
      datasets: [
        {
          label: 'Runs',
          data: phases.map(function(p) { return phaseBreakdown[p].runs; }),
          backgroundColor: CHART_COLORS.blue,
          borderRadius: 3
        },
        {
          label: 'Failures',
          data: phases.map(function(p) { return phaseBreakdown[p].failures; }),
          backgroundColor: CHART_COLORS.red,
          borderRadius: 3
        }
      ]
    },
    options: {
      scales: {
        x: { grid: { color: DARK_GRID }, ticks: { color: LABEL_COLOR } },
        y: { grid: { color: DARK_GRID }, ticks: { color: LABEL_COLOR } }
      },
      plugins: { legend: { labels: { color: TEXT_COLOR } } }
    }
  });
}

function formatViolationText(v) {
  return (v.type || v.rule || '') + (v.file ? ' (' + v.file + ')' : '');
}

function formatTimestamp(ts) {
  return ts ? ts.replace('T', ' ').replace('Z', '') : '--';
}

function renderRecentFailuresTable(failures) {
  var tbody = document.querySelector('#recent-failures-table tbody');
  if (!tbody || !failures || failures.length === 0) {
    if (tbody) tbody.innerHTML = '<tr><td colspan="4" class="empty">No recent failures.</td></tr>';
    return;
  }
  tbody.innerHTML = failures.map(function(f) {
    var violationText = (f.violations || []).map(formatViolationText).join(', ') || '--';
    var ts = formatTimestamp(f.timestamp);
    return '<tr><td>' + ts + '</td><td>' + f.repo +
      '</td><td>' + f.gate + '</td><td>' + violationText + '</td></tr>';
  }).join('');
}

function initNewCharts(data) {
  renderFindingsCards(data);
  renderFindingsByGate(data.findings_summary || { by_gate: {} });
  renderTopViolationTypes(data.top_violations || []);
  renderFixCyclesChart(data.fix_cycles || { distribution: {} });
  renderGateTimingChart(data.timing_stats || { by_gate: {} });
  renderPhaseBreakdownChart(data.phase_breakdown || {});
  renderRecentFailuresTable(data.recent_failures || []);
}

if (typeof module !== 'undefined' && module.exports) {
  module.exports = {
    findingsCardHtml: findingsCardHtml,
    sumValues: sumValues,
    findSlowestGate: findSlowestGate,
    formatViolationText: formatViolationText,
    formatTimestamp: formatTimestamp
  };
}
