#!/usr/bin/env node
/**
 * Tests for pure functions exported from docs/dashboard.js.
 *
 * This is a lightweight GitHub Pages dashboard — no build tooling or test
 * framework installed. Tests use Node's built-in assert module.
 */

'use strict';

var assert = require('assert');
var path = require('path');
var fns = require(path.join(__dirname, '..', 'docs', 'dashboard.js'));

var gradeColor = fns.gradeColor;
var heatCellColor = fns.heatCellColor;
var chartScaleDefaults = fns.chartScaleDefaults;
var cardHtml = fns.cardHtml;

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

// --- gradeColor ---

test('gradeColor returns good for >= 80', function() {
  assert.strictEqual(gradeColor(80), 'good');
  assert.strictEqual(gradeColor(100), 'good');
  assert.strictEqual(gradeColor(95), 'good');
});

test('gradeColor returns warn for 60-79', function() {
  assert.strictEqual(gradeColor(60), 'warn');
  assert.strictEqual(gradeColor(79), 'warn');
  assert.strictEqual(gradeColor(70), 'warn');
});

test('gradeColor returns bad for < 60', function() {
  assert.strictEqual(gradeColor(59), 'bad');
  assert.strictEqual(gradeColor(0), 'bad');
  assert.strictEqual(gradeColor(30), 'bad');
});

// --- heatCellColor ---

test('heatCellColor returns darkest green for >= 95', function() {
  assert.strictEqual(heatCellColor(95), '#238636');
  assert.strictEqual(heatCellColor(100), '#238636');
});

test('heatCellColor returns green for 80-94', function() {
  assert.strictEqual(heatCellColor(80), '#2ea043');
  assert.strictEqual(heatCellColor(94), '#2ea043');
});

test('heatCellColor returns yellow for 60-79', function() {
  assert.strictEqual(heatCellColor(60), '#9e6a03');
  assert.strictEqual(heatCellColor(79), '#9e6a03');
});

test('heatCellColor returns orange for 40-59', function() {
  assert.strictEqual(heatCellColor(40), '#bd561d');
  assert.strictEqual(heatCellColor(59), '#bd561d');
});

test('heatCellColor returns red for < 40', function() {
  assert.strictEqual(heatCellColor(39), '#da3633');
  assert.strictEqual(heatCellColor(0), '#da3633');
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

// --- cardHtml ---

test('cardHtml generates correct markup', function() {
  var html = cardHtml('Total', 42, 'good');
  assert.ok(html.indexOf('Total') !== -1);
  assert.ok(html.indexOf('42') !== -1);
  assert.ok(html.indexOf('good') !== -1);
  assert.ok(html.indexOf('<div class="card">') !== -1);
});

test('cardHtml handles empty class', function() {
  var html = cardHtml('Count', 0, '');
  assert.ok(html.indexOf('Count') !== -1);
  assert.ok(html.indexOf('value ') !== -1);
});

// --- Summary ---

console.log('\n' + passed + ' passed, ' + failed + ' failed');
if (failed > 0) {
  process.exit(1);
}
