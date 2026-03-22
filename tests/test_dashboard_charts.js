#!/usr/bin/env node
/**
 * Tests for pure functions exported from docs/dashboard_charts.js.
 */

'use strict';

var assert = require('assert');
var path = require('path');
var fns = require(path.join(__dirname, '..', 'docs', 'dashboard_charts.js'));

var findingsCardHtml = fns.findingsCardHtml;
var sumValues = fns.sumValues;
var findSlowestGate = fns.findSlowestGate;
var formatViolationText = fns.formatViolationText;
var formatTimestamp = fns.formatTimestamp;

var passed = 0;
var failed = 0;

function test(name, fn) {
  try {
    fn();
    passed++;
  } catch (err) {
    failed++;
    console.error('FAIL: ' + name);
    console.error('  ' + err.message);
  }
}

// --- findingsCardHtml ---

test('findingsCardHtml generates correct markup', function() {
  var html = findingsCardHtml('Total', 42, 'sub text');
  assert.ok(html.indexOf('Total') !== -1);
  assert.ok(html.indexOf('42') !== -1);
  assert.ok(html.indexOf('sub text') !== -1);
  assert.ok(html.indexOf('<div class="hero-metric">') !== -1);
});

test('findingsCardHtml handles empty subtitle', function() {
  var html = findingsCardHtml('Count', 0, '');
  assert.ok(html.indexOf('Count') !== -1);
  assert.ok(html.indexOf('sub') !== -1);
});

test('findingsCardHtml handles undefined subtitle', function() {
  var html = findingsCardHtml('Count', 0);
  assert.ok(html.indexOf('Count') !== -1);
});

// --- sumValues ---

test('sumValues sums object values', function() {
  assert.strictEqual(sumValues({ a: 3, b: 5 }), 8);
});

test('sumValues returns 0 for empty object', function() {
  assert.strictEqual(sumValues({}), 0);
});

test('sumValues handles null/undefined', function() {
  assert.strictEqual(sumValues(null), 0);
  assert.strictEqual(sumValues(undefined), 0);
});

test('sumValues works for distribution objects (replaces sumDistribution)', function() {
  assert.strictEqual(sumValues({ '1': 10, '2': 5 }), 15);
});

test('sumValues returns 0 for empty distribution', function() {
  assert.strictEqual(sumValues({}), 0);
});

// --- findSlowestGate ---

test('findSlowestGate finds gate with highest avg_ms', function() {
  var byGate = {
    lint: { avg_ms: 100 },
    tests: { avg_ms: 500 },
    filesize: { avg_ms: 50 }
  };
  var result = findSlowestGate(byGate);
  assert.strictEqual(result.name, 'tests');
  assert.strictEqual(result.time, '500ms');
});

test('findSlowestGate returns default for empty', function() {
  var result = findSlowestGate({});
  assert.strictEqual(result.name, '--');
  assert.strictEqual(result.time, '');
});

test('findSlowestGate handles null', function() {
  var result = findSlowestGate(null);
  assert.strictEqual(result.name, '--');
});

test('findSlowestGate handles missing avg_ms', function() {
  var result = findSlowestGate({ lint: {} });
  assert.strictEqual(result.name, '--');
});

// --- formatViolationText ---

test('formatViolationText with type and file', function() {
  var result = formatViolationText({ type: 'complexity', file: 'foo.js' });
  assert.strictEqual(result, 'complexity (foo.js)');
});

test('formatViolationText with rule instead of type', function() {
  var result = formatViolationText({ rule: 'max-lines', file: 'bar.py' });
  assert.strictEqual(result, 'max-lines (bar.py)');
});

test('formatViolationText with no file', function() {
  var result = formatViolationText({ type: 'lint' });
  assert.strictEqual(result, 'lint');
});

test('formatViolationText with empty object', function() {
  var result = formatViolationText({});
  assert.strictEqual(result, '');
});

// --- formatTimestamp ---

test('formatTimestamp formats ISO timestamp', function() {
  assert.strictEqual(formatTimestamp('2026-01-15T14:30:00Z'), '01-15 14:30');
});

test('formatTimestamp handles null', function() {
  assert.strictEqual(formatTimestamp(null), '--');
});

test('formatTimestamp handles undefined', function() {
  assert.strictEqual(formatTimestamp(undefined), '--');
});

test('formatTimestamp handles empty string', function() {
  assert.strictEqual(formatTimestamp(''), '--');
});

// --- Summary ---

console.log('\n' + passed + ' passed, ' + failed + ' failed');
if (failed > 0) {
  process.exit(1);
}
