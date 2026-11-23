const assert = require("node:assert/strict");
const test = require("node:test");
const {
  formatTooltip,
  toBarSeries,
  toLineSeries,
  rangeStart,
  safeHref,
} = require("../site/chart_data.js");

test("tooltip lists counts and German sentiment", () => {
  const text = formatTooltip({
    count_unique_url: 120,
    count_positive: 45,
    count_neutral: 50,
    count_negative: 25,
    count_without_sentiment: 0,
    count_after_near_dup_collapse: 110,
    sentiment_mean: 0.18,
    coverage: "complete",
  });
  assert.equal(
    text,
    "120 Nachrichten: 45 positiv, 50 neutral, 25 negativ, Stimmung +0,18 (110 ohne Nahduplikate)"
  );
});

test("tooltip mentions missing scores and dashes sentiment", () => {
  const text = formatTooltip({
    count_unique_url: 5,
    count_positive: 0,
    count_neutral: 0,
    count_negative: 0,
    count_without_sentiment: 5,
    count_after_near_dup_collapse: 5,
    sentiment_mean: null,
    coverage: "complete",
  });
  assert.match(text, /5 ohne Wert/);
  assert.match(text, /Stimmung —/);
});

test("gap tooltip is marked incomplete and not a complete zero day", () => {
  const emptyGap = formatTooltip({
    count_unique_url: 0,
    count_positive: 0,
    count_neutral: 0,
    count_negative: 0,
    count_without_sentiment: 0,
    count_after_near_dup_collapse: 0,
    sentiment_mean: null,
    coverage: "gap",
  });
  assert.match(emptyGap, /^unvollständig — /);
  assert.doesNotMatch(emptyGap, /^0 Nachrichten/);
  const partialGap = formatTooltip({
    count_unique_url: 2,
    count_positive: 1,
    count_neutral: 0,
    count_negative: 1,
    count_without_sentiment: 0,
    count_after_near_dup_collapse: 2,
    sentiment_mean: 0.1,
    coverage: "gap",
  });
  assert.match(partialGap, /^unvollständig — /);
  assert.match(partialGap, /2 Nachrichten/);
});

test("bars go up green and down red, gaps are null not zero", () => {
  const days = [
    {
      date: "2019-09-23",
      count_positive: 2,
      count_negative: 3,
      sentiment_mean: -0.1,
      coverage: "complete",
    },
    {
      date: "2019-09-24",
      count_positive: 0,
      count_negative: 0,
      sentiment_mean: null,
      coverage: "gap",
    },
  ];
  const bars = toBarSeries(days);
  assert.equal(bars.up[0].value, 2);
  assert.equal(bars.down[0].value, -3);
  assert.equal(bars.up[1].value, null);
  assert.equal(bars.down[1].value, null);
  const line = toLineSeries(days);
  assert.equal(line[0].value, -0.1);
  assert.equal(line[0].color, "#ef5350");
  assert.equal(line[1].value, null);
});

test("range chips use Berlin calendar days", () => {
  assert.equal(rangeStart("2026-11-22", "1M"), "2026-10-22");
  assert.equal(rangeStart("2026-11-22", "3M"), "2026-08-22");
  assert.equal(rangeStart("2026-11-22", "1J"), "2025-11-22");
  assert.equal(rangeStart("2026-11-22", "5J"), "2021-11-22");
  assert.equal(rangeStart("2026-11-22", "max"), null);
});

test("safeHref allows only http and https URLs", () => {
  assert.equal(safeHref("http://example.com/a"), "http://example.com/a");
  assert.equal(safeHref("https://example.com/a"), "https://example.com/a");
  assert.equal(safeHref("javascript:alert(1)"), null);
  assert.equal(safeHref("data:text/html,hi"), null);
  assert.equal(safeHref(""), null);
});

test("range chips clamp to last day of shorter months", () => {
  assert.equal(rangeStart("2026-03-31", "1M"), "2026-02-28");
  assert.equal(rangeStart("2024-03-31", "1M"), "2024-02-29");
});
