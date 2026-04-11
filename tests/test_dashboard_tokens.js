#!/usr/bin/env node
/**
 * Tests for pure functions exported from docs/dashboard_tokens.js.
 */

'use strict';

var assert = require('assert');
var path = require('path');
var fns = require(path.join(__dirname, '..', 'docs', 'dashboard_tokens.js'));

var fmtTokens = fns.fmtTokens;
var fmtCost = fns.fmtCost;
var fmtPct = fns.fmtPct;

var passed = 0;
var failed = 0;

function test(name, fn) {
  try {
    fn();
    passed++;
    console.log('  ok   ' + name);
  } catch (e) {
    failed++;
    console.log('  FAIL ' + name + ': ' + e.message);
  }
}

console.log('dashboard_tokens.js tests');

test('fmtTokens null returns em-dash', function() {
  assert.strictEqual(fmtTokens(null), '—');
});
test('fmtTokens small integer passes through', function() {
  assert.strictEqual(fmtTokens(42), '42');
});
test('fmtTokens thousands formatted with K', function() {
  assert.strictEqual(fmtTokens(1500), '1.5K');
});
test('fmtTokens millions formatted with M', function() {
  assert.strictEqual(fmtTokens(2_500_000), '2.50M');
});
test('fmtTokens billions formatted with B', function() {
  assert.strictEqual(fmtTokens(1_100_000_000), '1.10B');
});

test('fmtCost null returns $—', function() {
  assert.strictEqual(fmtCost(null), '$—');
});
test('fmtCost under 100 shows two decimals', function() {
  assert.strictEqual(fmtCost(12.34), '$12.34');
});
test('fmtCost over 100 shows no decimals', function() {
  assert.strictEqual(fmtCost(125.67), '$126');
});
test('fmtCost over 10000 uses thousands separator', function() {
  assert.strictEqual(fmtCost(12345.67), '$12,346');
});

test('fmtPct null returns em-dash', function() {
  assert.strictEqual(fmtPct(null), '—');
});
test('fmtPct converts ratio to percent', function() {
  assert.strictEqual(fmtPct(0.75), '75.0%');
});
test('fmtPct handles zero', function() {
  assert.strictEqual(fmtPct(0), '0.0%');
});

console.log('\n' + passed + ' passed, ' + failed + ' failed');
process.exit(failed === 0 ? 0 : 1);
