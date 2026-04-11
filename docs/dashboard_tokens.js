/* rq-metrics — token cost dashboard renderers */

/* ── Number formatting helpers ─────────────────────────────────── */
function fmtTokens(n) {
  if (n == null) return '—';
  if (n >= 1e9) return (n / 1e9).toFixed(2) + 'B';
  if (n >= 1e6) return (n / 1e6).toFixed(2) + 'M';
  if (n >= 1e3) return (n / 1e3).toFixed(1) + 'K';
  return String(n);
}

function fmtCost(n) {
  if (n == null) return '$—';
  if (n >= 10000) return '$' + Math.round(n).toLocaleString();
  if (n >= 100) return '$' + n.toFixed(0);
  return '$' + n.toFixed(2);
}

function fmtPct(ratio) {
  if (ratio == null) return '—';
  return (ratio * 100).toFixed(1) + '%';
}

/* ── Hero strip ─────────────────────────────────────────────────── */
function renderTokenHero(summary) {
  var el = document.getElementById('token-hero-strip');
  if (!el) return;
  var s = summary || {};
  var unpricedNote = s.unpriced_sessions
    ? ' · ' + s.unpriced_sessions + ' unpriced'
    : '';
  el.innerHTML =
    '<div class="hero-metric primary">' +
      '<div class="label">Total Cost</div>' +
      '<div class="value v-neutral">' + fmtCost(s.total_cost_usd) + '</div>' +
      '<div class="sub">across ' + (s.session_count || 0) + ' sessions' + unpricedNote + '</div>' +
    '</div>' +
    '<div class="hero-metric">' +
      '<div class="label">Total Tokens</div>' +
      '<div class="value v-neutral">' + fmtTokens(s.total_tokens) + '</div>' +
    '</div>' +
    '<div class="hero-metric">' +
      '<div class="label">Cache Share</div>' +
      '<div class="value v-good">' + fmtPct(s.cache_ratio) + '</div>' +
      '<div class="sub">of all tokens</div>' +
    '</div>' +
    '<div class="hero-metric">' +
      '<div class="label">Sessions</div>' +
      '<div class="value v-neutral">' + (s.session_count || 0) + '</div>' +
    '</div>';
}

/* ── Cost leaderboard ──────────────────────────────────────────── */
function renderTokenLeaderboard(leaderboard) {
  var tbody = document.querySelector('#token-leaderboard-table tbody');
  var badge = document.getElementById('token-leaderboard-count');
  if (badge) badge.textContent = (leaderboard || []).length + ' users';
  if (!tbody) return;
  if (!leaderboard || leaderboard.length === 0) {
    tbody.innerHTML = '<tr><td colspan="5" class="empty">No token data yet.</td></tr>';
    return;
  }
  tbody.innerHTML = leaderboard.map(function(e) {
    return '<tr>' +
      '<td style="color:var(--accent);font-weight:500">' + e.rank + '</td>' +
      '<td>' + escapeHtml(e.display_name || e.user || '') + '</td>' +
      '<td>' + (e.session_count || 0) + '</td>' +
      '<td>' + fmtTokens(e.total_tokens) + '</td>' +
      '<td>' + fmtCost(e.total_cost_usd) + '</td>' +
    '</tr>';
  }).join('');
}

/* ── Top expensive sessions ───────────────────────────────────── */
function renderTokenTopSessions(topSessions) {
  var tbody = document.querySelector('#token-top-sessions-table tbody');
  var badge = document.getElementById('token-top-sessions-count');
  if (badge) badge.textContent = (topSessions || []).length + ' sessions';
  if (!tbody) return;
  if (!topSessions || topSessions.length === 0) {
    tbody.innerHTML = '<tr><td colspan="4" class="empty">No session data.</td></tr>';
    return;
  }
  tbody.innerHTML = topSessions.map(function(s) {
    var label = escapeHtml((s.repo || '') + ' / ' + (s.branch || ''));
    if (s.pr_number) {
      label += ' <span class="badge">#' + s.pr_number + '</span>';
    }
    return '<tr>' +
      '<td>' + label + '</td>' +
      '<td>' + escapeHtml(s.user || '') + '</td>' +
      '<td>' + fmtTokens(s.total_tokens) + '</td>' +
      '<td>' + fmtCost(s.total_cost_usd) + '</td>' +
    '</tr>';
  }).join('');
}

/* ── Cost by group (repo, branch, PR) ─────────────────────────── */
function renderTokenGroupTable(tableSelector, badgeId, groupMap, labelFn) {
  var tbody = document.querySelector(tableSelector + ' tbody');
  var badge = document.getElementById(badgeId);
  if (!tbody) return;
  var entries = Object.keys(groupMap || {}).map(function(k) {
    var v = groupMap[k];
    return {
      key: k,
      label: labelFn ? labelFn(k, v) : (v.display_name || k),
      sessions: v.session_count || 0,
      tokens: v.total_tokens || 0,
      cost: v.total_cost_usd,
    };
  });
  entries.sort(function(a, b) {
    // Priced entries before unpriced; then by cost desc
    var ca = a.cost == null ? -1 : a.cost;
    var cb = b.cost == null ? -1 : b.cost;
    return cb - ca;
  });
  if (badge) badge.textContent = entries.length;
  if (entries.length === 0) {
    tbody.innerHTML = '<tr><td colspan="4" class="empty">No data.</td></tr>';
    return;
  }
  tbody.innerHTML = entries.map(function(e) {
    return '<tr>' +
      '<td>' + escapeHtml(e.label) + '</td>' +
      '<td>' + e.sessions + '</td>' +
      '<td>' + fmtTokens(e.tokens) + '</td>' +
      '<td>' + fmtCost(e.cost) + '</td>' +
    '</tr>';
  }).join('');
}

function renderTokenPerRepo(perRepo) {
  renderTokenGroupTable('#token-per-repo-table', 'token-per-repo-count', perRepo);
}

function renderTokenPerBranch(perBranch) {
  renderTokenGroupTable('#token-per-branch-table', 'token-per-branch-count', perBranch);
}

function renderTokenPerPr(perPr) {
  renderTokenGroupTable('#token-per-pr-table', 'token-per-pr-count', perPr, function(k, v) {
    return '#' + k;
  });
}

/* ── Daily cost trend chart ───────────────────────────────────── */
function renderTokenCostTrend(trends) {
  var canvas = document.getElementById('token-cost-trend-chart');
  if (!canvas || typeof Chart === 'undefined') return;
  if (!trends || trends.length === 0) {
    var ctx = canvas.getContext('2d');
    ctx.clearRect(0, 0, canvas.width, canvas.height);
    ctx.fillStyle = TEXT_COLOR || '#7a8ba4';
    ctx.font = "11px 'DM Mono', monospace";
    ctx.fillText('No cost trend data yet.', 10, 20);
    return;
  }
  var labels = trends.map(function(t) { return t.date; });
  var costs = trends.map(function(t) { return t.cost_usd || 0; });
  return new Chart(canvas, {
    type: 'line',
    data: {
      labels: labels,
      datasets: [{
        label: 'Daily cost (USD)',
        data: costs,
        borderColor: CHART_COLORS.cyan,
        backgroundColor: CHART_COLORS.cyan + '33',
        tension: 0.25,
        fill: true,
      }]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      scales: {
        x: { ticks: { color: LABEL_COLOR }, grid: { color: DARK_GRID } },
        y: {
          ticks: {
            color: LABEL_COLOR,
            callback: function(v) { return '$' + v; },
          },
          grid: { color: DARK_GRID },
        },
      },
      plugins: { legend: { display: false } },
    }
  });
}

/* ── Entry point: render all token panels from data.tokens ───── */
function renderTokenDashboard(tokenPayload) {
  var t = tokenPayload || {};
  renderTokenHero(t.summary || {});
  renderTokenLeaderboard(t.leaderboard || []);
  renderTokenTopSessions(t.top_sessions || []);
  renderTokenPerRepo(t.per_repo || {});
  renderTokenPerBranch(t.per_branch || {});
  renderTokenPerPr(t.per_pr || {});
  renderTokenCostTrend(t.cost_trends || []);
}

/* Export for Node test harness */
if (typeof module !== 'undefined' && module.exports) {
  module.exports = {
    fmtTokens: fmtTokens,
    fmtCost: fmtCost,
    fmtPct: fmtPct,
    renderTokenDashboard: renderTokenDashboard,
  };
}
