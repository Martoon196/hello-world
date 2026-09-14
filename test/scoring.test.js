import { test } from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import { scoreDeal, curvePoints, loadMatrix, deriveFinancials } from "../src/scoring.js";

const fixture = JSON.parse(fs.readFileSync(new URL("./fixtures/mock-extraction.json", import.meta.url)));
const matrix = loadMatrix();

test("curve interpolates and clamps", () => {
  const c = [[0, 0], [10, 50], [20, 100]];
  assert.equal(curvePoints(c, -5), 0);
  assert.equal(curvePoints(c, 5), 25);
  assert.equal(curvePoints(c, 15), 75);
  assert.equal(curvePoints(c, 99), 100);
});

test("derives BRR financials from the fixture", () => {
  const { derived, assumptions } = deriveFinancials(fixture, matrix);
  assert.equal(derived.purchase_price, 95000);
  assert.equal(derived.gross_yield, 10.7);
  assert.equal(derived.discount_to_mv, 20.8);
  assert.ok(derived.money_left_in_pct > 0 && derived.money_left_in_pct < 30);
  assert.ok(assumptions.some((a) => /Purchase costs not stated/.test(a)));
});

test("scores the fixture and lands in a sensible band", () => {
  const s = scoreDeal(fixture, matrix);
  assert.equal(s.strategy, "brr");
  assert.ok(s.score >= 55 && s.score <= 90, `score was ${s.score}`);
  assert.ok(["green", "amber"].includes(s.rating));
  assert.equal(s.coverage, 100);
  assert.equal(s.missing_metrics.length, 0);
});

test("a deal with no numbers is penalised, not crashed", () => {
  const thin = {
    ...fixture,
    strategy: "flip",
    financials: { ...fixture.financials, purchase_price: null, asking_price: null, estimated_market_value: null, end_value: null, monthly_rent: null },
  };
  const s = scoreDeal(thin, matrix);
  assert.ok(s.coverage < 60);
  assert.ok(s.score < 60, `score was ${s.score}`);
  assert.ok(s.missing_metrics.includes("Profit on cost"));
});

test("unknown strategy falls back to 'other'", () => {
  const s = scoreDeal({ ...fixture, strategy: "spaceship" }, matrix);
  assert.equal(s.strategy, "other");
});

test("every strategy's weights sum to 100 and reference known metrics", () => {
  for (const [name, weights] of Object.entries(matrix.strategies)) {
    const sum = Object.values(weights).reduce((a, b) => a + b, 0);
    assert.equal(sum, 100, `${name} weights sum to ${sum}`);
    for (const key of Object.keys(weights)) assert.ok(matrix.metrics[key], `${name} references unknown metric ${key}`);
  }
});
