const assert = require("node:assert/strict");
const test = require("node:test");
const {
  formatTooltip,
  toBarSeries,
  toLineSeries,
  rangeStart,
  safeHref,
  formatSentiment,
  formatDayHeading,
  resolveMode,
  modeCounts,
  DEFAULT_MODE,
} = require("../site/chart_data.js");

test("tooltip lists counts and German sentiment", () => {
  const text = formatTooltip({
    count_unique_url: 120,
    count_positive: 45,
    count_neutral: 50,
    count_negative: 15,
    count_without_sentiment: 0,
    count_after_near_dup_collapse: 110,
    sentiment_mean: 0.18,
    coverage: "complete",
  });
  assert.equal(
    text,
    "120 Nachrichten, 110 ohne Nahduplikate: 45 positiv, 50 neutral, 15 negativ, Stimmung +0,18"
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

test("bars go up green and down red, gaps have no value (whitespace) not zero", () => {
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
  // Lightweight Charts erkennt Lücken nur an fehlendem value (Whitespace-Datenpunkt).
  assert.ok(!("value" in bars.up[1]));
  assert.ok(!("value" in bars.down[1]));
  assert.deepEqual(bars.up[1], { time: "2019-09-24" });
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
  assert.equal(safeHref("HTTPS://Example.com/A"), "HTTPS://Example.com/A");
  assert.equal(safeHref("  https://example.com/a  "), "https://example.com/a");
  assert.equal(safeHref("  javascript:alert(1)"), null);
  assert.equal(safeHref("JavaScript:alert(1)"), null);
  assert.equal(safeHref("\tdata:text/html,hi"), null);
  assert.equal(safeHref(null), null);
});

test("gap tooltip names a missing GDELT source", () => {
  const text = formatTooltip({
    count_unique_url: 0,
    count_positive: 0,
    count_neutral: 0,
    count_negative: 0,
    count_without_sentiment: 0,
    count_after_near_dup_collapse: 0,
    sentiment_mean: null,
    coverage: "gap",
    gap_reason: "source_missing",
  });
  assert.match(text, /^Quelle fehlt \(GDELT\) — /);
  assert.doesNotMatch(text, /^unvollständig/);
});

test("range chips clamp to last day of shorter months", () => {
  assert.equal(rangeStart("2026-03-31", "1M"), "2026-02-28");
  assert.equal(rangeStart("2024-03-31", "1M"), "2024-02-29");
});

test("headline sentiment uses German format with two decimals", () => {
  assert.equal(formatSentiment(0.5), "+0,50");
  assert.equal(formatSentiment(-0.123), "\u22120,12");
  assert.equal(formatSentiment(0), "0,00");
  assert.equal(formatSentiment(null), "—");
  assert.equal(formatSentiment(undefined), "—");
});

test("day heading shows unique and collapsed counts and gap label", () => {
  assert.equal(
    formatDayHeading("2019-09-24", { count_unique_url: 12, count_after_near_dup_collapse: 10, coverage: "complete" }),
    "Schlagzeilen 2019-09-24 — 12 Nachrichten, 10 ohne Nahduplikate"
  );
  assert.equal(
    formatDayHeading("2019-09-23", {
      count_unique_url: 1,
      count_after_near_dup_collapse: 1,
      coverage: "gap",
      gap_reason: "source_missing",
    }),
    "Schlagzeilen 2019-09-23 (Quelle fehlt (GDELT)) — 1 Nachrichten, 1 ohne Nahduplikate"
  );
  assert.equal(formatDayHeading("2019-09-25", undefined), "Schlagzeilen 2019-09-25");
});

const BOTH = {
  date: "2019-09-26",
  count_unique_url: 120,
  count_after_near_dup_collapse: 71,
  count_positive: 18,
  count_neutral: 43,
  count_negative: 10,
  count_without_sentiment: 0,
  sentiment_mean: 0.108,
  count_positive_all: 30,
  count_neutral_all: 70,
  count_negative_all: 19,
  count_without_sentiment_all: 1,
  sentiment_mean_all: -0.05,
  coverage: "complete",
};

test("default counting mode is without near-duplicates", () => {
  assert.equal(DEFAULT_MODE, "ohne");
  assert.equal(resolveMode("", null), "ohne");
});

test("mode comes from URL parameter first, then storage, invalid values fall back", () => {
  assert.equal(resolveMode("?zaehlung=alle", "ohne"), "alle");
  assert.equal(resolveMode("?zaehlung=ohne", "alle"), "ohne");
  assert.equal(resolveMode("", "alle"), "alle");
  assert.equal(resolveMode("?zaehlung=quatsch", "alle"), "alle");
  assert.equal(resolveMode("?zaehlung=quatsch", "kaputt"), "ohne");
  assert.equal(resolveMode(undefined, undefined), "ohne");
});

test("modeCounts picks class counts and mean for the chosen mode", () => {
  assert.deepEqual(modeCounts(BOTH, "ohne"), {
    positive: 18, neutral: 43, negative: 10, without: 0, mean: 0.108, total: 71,
  });
  assert.deepEqual(modeCounts(BOTH, "alle"), {
    positive: 30, neutral: 70, negative: 19, without: 1, mean: -0.05, total: 120,
  });
});

test("bars and line switch with the mode, colors follow the sign", () => {
  const gap = { date: "2019-09-27", count_positive: 0, count_negative: 0, count_positive_all: 0,
    count_negative_all: 0, sentiment_mean: null, sentiment_mean_all: null, coverage: "gap" };
  const ohne = toBarSeries([BOTH, gap], "ohne");
  assert.equal(ohne.up[0].value, 18);
  assert.equal(ohne.down[0].value, -10);
  const alle = toBarSeries([BOTH, gap], "alle");
  assert.equal(alle.up[0].value, 30);
  assert.equal(alle.down[0].value, -19);
  // Lücken bleiben in beiden Modi Whitespace ohne value.
  for (const bars of [ohne, alle]) {
    assert.deepEqual(bars.up[1], { time: "2019-09-27" });
    assert.deepEqual(bars.down[1], { time: "2019-09-27" });
  }
  assert.equal(toLineSeries([BOTH], "ohne")[0].color, "#26a69a");
  const lineAll = toLineSeries([BOTH, gap], "alle");
  assert.equal(lineAll[0].value, -0.05);
  assert.equal(lineAll[0].color, "#ef5350");
  assert.equal(lineAll[1].value, null);
  // Ohne Modusangabe gilt der Standard "ohne".
  assert.equal(toBarSeries([BOTH]).up[0].value, 18);
});

test("all mode on old data without _all fields shows gaps instead of wrong numbers", () => {
  const old = { date: "2019-09-26", count_positive: 5, count_negative: 2, sentiment_mean: 0.1, coverage: "complete" };
  assert.deepEqual(toBarSeries([old], "alle").up[0], { time: "2019-09-26" });
  assert.deepEqual(toBarSeries([old], "alle").down[0], { time: "2019-09-26" });
  assert.equal(toLineSeries([old], "alle")[0].value, null);
});

test("tooltip numbers switch with the mode", () => {
  assert.equal(
    formatTooltip(BOTH, "ohne"),
    "120 Nachrichten, 71 ohne Nahduplikate: 18 positiv, 43 neutral, 10 negativ, Stimmung +0,11"
  );
  assert.equal(
    formatTooltip(BOTH, "alle"),
    "120 Nachrichten inkl. Nahduplikate (71 ohne): 30 positiv, 70 neutral, 19 negativ, Stimmung \u22120,05, 1 ohne Wert"
  );
  assert.equal(formatTooltip(BOTH), formatTooltip(BOTH, "ohne"));
  const gap = { ...BOTH, coverage: "gap", gap_reason: "source_missing" };
  assert.match(formatTooltip(gap, "alle"), /^Quelle fehlt \(GDELT\) — 120 Nachrichten inkl\. Nahduplikate/);
});

test("day heading names the active mode", () => {
  assert.equal(
    formatDayHeading("2019-09-26", BOTH, "alle"),
    "Schlagzeilen 2019-09-26 — 120 Nachrichten, 71 ohne Nahduplikate (Ansicht: alle Nachrichten)"
  );
  assert.equal(
    formatDayHeading("2019-09-26", BOTH, "ohne"),
    "Schlagzeilen 2019-09-26 — 120 Nachrichten, 71 ohne Nahduplikate (Ansicht: ohne Nahduplikate)"
  );
});
