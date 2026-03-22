#!/usr/bin/env node
/**
 * Tests for pure functions exported from docs/dashboard.js.
 */

'use strict';

var assert = require('assert');
var path = require('path');
var fns = require(path.join(__dirname, '..', 'docs', 'dashboard.js'));

var gradeColor = fns.gradeColor;
var heatCellColor = fns.heatCellColor;
var chartScaleDefaults = fns.chartScaleDefaults;

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

// --- gradeColor (returns v-good/v-warn/v-bad for hero metrics) ---

test('gradeColor returns v-good for >= 80', function() {
  assert.strictEqual(gradeColor(80), 'v-good');
  assert.strictEqual(gradeColor(100), 'v-good');
  assert.strictEqual(gradeColor(95), 'v-good');
});

test('gradeColor returns v-warn for 60-79', function() {
  assert.strictEqual(gradeColor(60), 'v-warn');
  assert.strictEqual(gradeColor(79), 'v-warn');
  assert.strictEqual(gradeColor(70), 'v-warn');
});

test('gradeColor returns v-bad for < 60', function() {
  assert.strictEqual(gradeColor(59), 'v-bad');
  assert.strictEqual(gradeColor(0), 'v-bad');
  assert.strictEqual(gradeColor(30), 'v-bad');
});

// --- heatCellColor (updated palette) ---

test('heatCellColor returns darkest green for >= 95', function() {
  assert.strictEqual(heatCellColor(95), '#166534');
  assert.strictEqual(heatCellColor(100), '#166534');
});

test('heatCellColor returns green for 80-94', function() {
  assert.strictEqual(heatCellColor(80), '#15803d');
  assert.strictEqual(heatCellColor(94), '#15803d');
});

test('heatCellColor returns amber for 60-79', function() {
  assert.strictEqual(heatCellColor(60), '#854d0e');
  assert.strictEqual(heatCellColor(79), '#854d0e');
});

test('heatCellColor returns orange for 40-59', function() {
  assert.strictEqual(heatCellColor(40), '#9a3412');
  assert.strictEqual(heatCellColor(59), '#9a3412');
});

test('heatCellColor returns red for < 40', function() {
  assert.strictEqual(heatCellColor(39), '#991b1b');
  assert.strictEqual(heatCellColor(0), '#991b1b');
});

// --- chartScaleDefaults ---

test('chartScaleDefaults returns correct structure', function() {
  var result = chartScaleDefaults(0, 100);
  assert.strictEqual(result.y.min, 0);
  assert.strictEqual(result.y.max, 100);
  assert.ok(result.y.grid);
  assert.ok(result.y.ticks);
  assert.ok(result.x.grid);
  assert.ok(result.x.ticks);
});

test('chartScaleDefaults passes through min/max', function() {
  var result = chartScaleDefaults(10, 50);
  assert.strictEqual(result.y.min, 10);
  assert.strictEqual(result.y.max, 50);
});

test('chartScaleDefaults handles undefined max', function() {
  var result = chartScaleDefaults(0, undefined);
  assert.strictEqual(result.y.min, 0);
  assert.strictEqual(result.y.max, undefined);
});

// --- Summary ---

console.log('\n' + passed + ' passed, ' + failed + ' failed');
if (failed > 0) {
  process.exit(1);
}
