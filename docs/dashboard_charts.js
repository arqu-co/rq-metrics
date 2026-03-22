/* rq Metrics Dashboard — Findings chart renderers */

/* In Node.js, pull shared constants from dashboard.js.
   In the browser, dashboard.js loads first and these are already global.
   IIFE prevents var hoisting from conflicting with const in dashboard.js. */
(function() {
  if (typeof require === 'undefined') return;
  var _dash = require('./dashboard.js');
  if (typeof CHART_COLORS === 'undefined') { CHART_COLORS = _dash.CHART_COLORS; }
  if (typeof DARK_GRID === 'undefined') { DARK_GRID = _dash.DARK_GRID; }
  if (typeof LABEL_COLOR === 'undefined') { LABEL_COLOR = _dash.LABEL_COLOR; }
  if (typeof TEXT_COLOR === 'undefined') { TEXT_COLOR = _dash.TEXT_COLOR; }
})();

function findingsCardHtml(label, value, subtitle) {
  return '<div class="hero-metric"><div class="label">' + label +
    '</div><div class="value v-neutral">' + value +
    '</div><div class="sub">' + (subtitle || '') + '</div></div>';
}

function renderFindingsCards(data) {
  /* Findings cards removed — data now shown in hero strip and charts */
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
        label: 'Findings',
        data: names.map(function(n) { return byGate[n]; }),
        backgroundColor: CHART_COLORS.blue + '99',
        borderColor: CHART_COLORS.blue,
        borderWidth: 1, borderRadius: 3
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
        backgroundColor: CHART_COLORS.orange + '99',
        borderColor: CHART_COLORS.orange,
        borderWidth: 1, borderRadius: 3
      }]
    },
    options: {
      indexAxis: 'y',
      scales: {
        x: { grid: { color: DARK_GRID }, ticks: { color: LABEL_COLOR } },
        y: { grid: { display: false }, ticks: { color: TEXT_COLOR, font: { size: 9 } } }
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
    if (n === 1) return CHART_COLORS.green + '99';
    if (n === 2) return CHART_COLORS.yellow + '99';
    return CHART_COLORS.red + '99';
  });
  var borders = keys.map(function(k) {
    var n = parseInt(k, 10);
    if (n === 1) return CHART_COLORS.green;
    if (n === 2) return CHART_COLORS.yellow;
    return CHART_COLORS.red;
  });
  new Chart(ctx.getContext('2d'), {
    type: 'bar',
    data: {
      labels: keys.map(function(k) { return k + (k === '1' ? ' run' : ' runs'); }),
      datasets: [{
        data: keys.map(function(k) { return dist[k]; }),
        backgroundColor: colors,
        borderColor: borders,
        borderWidth: 1, borderRadius: 3
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
  var names = Object.keys(byGate).sort(function(a, b) {
    return (byGate[b].avg_ms || 0) - (byGate[a].avg_ms || 0);
  });
  names = names.filter(function(n) { return (byGate[n].avg_ms || 0) > 0; });
  if (names.length === 0) return;
  new Chart(ctx.getContext('2d'), {
    type: 'bar',
    data: {
      labels: names,
      datasets: [{
        label: 'Avg (ms)',
        data: names.map(function(n) { return Math.round(byGate[n].avg_ms || 0); }),
        backgroundColor: CHART_COLORS.cyan + '99',
        borderColor: CHART_COLORS.cyan,
        borderWidth: 1, borderRadius: 3
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
          backgroundColor: CHART_COLORS.blue + '99',
          borderColor: CHART_COLORS.blue,
          borderWidth: 1, borderRadius: 3
        },
        {
          label: 'Failures',
          data: phases.map(function(p) { return phaseBreakdown[p].failures; }),
          backgroundColor: CHART_COLORS.red + '99',
          borderColor: CHART_COLORS.red,
          borderWidth: 1, borderRadius: 3
        }
      ]
    },
    options: {
      scales: {
        x: { grid: { color: DARK_GRID }, ticks: { color: LABEL_COLOR } },
        y: { grid: { color: DARK_GRID }, ticks: { color: LABEL_COLOR } }
      },
      plugins: { legend: { labels: { color: TEXT_COLOR, boxWidth: 8, padding: 12, font: { size: 9 } } } }
    }
  });
}

function formatViolationText(v) {
  return (v.type || v.rule || '') + (v.file ? ' (' + v.file + ')' : '');
}

function formatTimestamp(ts) {
  if (!ts) return '--';
  var d = ts.replace('T', ' ').replace('Z', '');
  return d.substring(5, 16);
}

function renderRecentFailuresTable(failures) {
  var tbody = document.querySelector('#recent-failures-table tbody');
  var badge = document.getElementById('failure-count');
  if (badge) badge.textContent = (failures || []).length + ' recent';
  if (!tbody || !failures || failures.length === 0) {
    if (tbody) tbody.innerHTML = '<tr><td colspan="4" class="empty">No recent failures.</td></tr>';
    return;
  }
  tbody.innerHTML = failures.map(function(f) {
    var violationText = (f.violations || []).slice(0, 2).map(formatViolationText).join(', ') || '--';
    if ((f.violations || []).length > 2) violationText += ' +' + (f.violations.length - 2);
    var ts = formatTimestamp(f.timestamp);
    return '<tr><td>' + ts + '</td><td>' + f.repo +
      '</td><td>' + f.gate + '</td><td>' + violationText + '</td></tr>';
  }).join('');
}

function initNewCharts(data) {
  try { renderFindingsByGate(data.findings_summary || { by_gate: {} }); } catch(e) { console.error('findings-gate:', e); }
  try { renderTopViolationTypes(data.top_violations || []); } catch(e) { console.error('top-violations:', e); }
  try { renderFixCyclesChart(data.fix_cycles || { distribution: {} }); } catch(e) { console.error('fix-cycles:', e); }
  try { renderGateTimingChart(data.timing_stats || { by_gate: {} }); } catch(e) { console.error('gate-timing:', e); }
  try { renderPhaseBreakdownChart(data.phase_breakdown || {}); } catch(e) { console.error('phase-breakdown:', e); }
  try { renderRecentFailuresTable(data.recent_failures || []); } catch(e) { console.error('recent-failures:', e); }
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
