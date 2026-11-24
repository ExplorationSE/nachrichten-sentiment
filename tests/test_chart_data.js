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
  DEFAULT_VIEW,
  resolveView,
  toCandleSeries,
  formatCandle,
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

test("line segment color follows the END point of each segment in both modes", () => {
  // Lightweight Charts färbt den Abschnitt von Punkt i nach i+1 mit der Farbe von Punkt i;
  // deshalb trägt Punkt i die Farbe seines Endpunkts i+1.
  const mk = (date, ohne, alle, coverage = "complete") => ({
    date, coverage, sentiment_mean: ohne, sentiment_mean_all: alle,
    count_positive: 0, count_negative: 0, count_positive_all: 0, count_negative_all: 0,
  });
  const days = [
    mk("2019-09-23", 0.112, -0.031),
    mk("2019-09-24", 0.125, 0.092),
    mk("2019-09-25", -0.2, 0.036),
    mk("2019-09-26", 0.0, -0.116),
    mk("2019-09-27", null, null, "gap"),
    mk("2019-09-28", -0.3, 0.064),
  ];
  const G = "#26a69a";
  const R = "#ef5350";
  const alle = toLineSeries(days, "alle");
  assert.deepEqual(alle.map((p) => p.value), [-0.031, 0.092, 0.036, -0.116, null, 0.064]);
  // 23→24 endet bei +0,092 → grün; 24→25 grün; 25→26 endet negativ → rot;
  // 26 vor einer Lücke und der letzte Punkt behalten ihre eigene Farbe.
  assert.deepEqual(alle.map((p) => p.color), [G, G, R, R, "#8b949e", G]);
  const ohne = toLineSeries(days, "ohne");
  // 24→25 endet bei −0,2 → rot; 25→26 endet bei 0 → grün (>= 0).
  assert.deepEqual(ohne.map((p) => p.color), [G, R, G, G, "#8b949e", R]);
});

const CANDLE_DAY = {
  date: "2019-09-26",
  coverage: "complete",
  count_unique_url: 143,
  count_after_near_dup_collapse: 71,
  ohlc: [0.1, 0.3, -0.2, 0.05, 40],
  ohlc_all: [0.2, 0.25, -0.4, -0.1, 52],
};

test("default chart view is the line, URL parameter beats storage", () => {
  assert.equal(DEFAULT_VIEW, "linie");
  assert.equal(resolveView("", null), "linie");
  assert.equal(resolveView("?ansicht=kerzen", "linie"), "kerzen");
  assert.equal(resolveView("?ansicht=linie", "kerzen"), "linie");
  assert.equal(resolveView("", "kerzen"), "kerzen");
  assert.equal(resolveView("?ansicht=quatsch&zaehlung=alle", "kaputt"), "linie");
  assert.equal(resolveView(undefined, undefined), "linie");
});

test("candles per mode: green when close >= open, red otherwise", () => {
  const G = "#26a69a";
  const R = "#ef5350";
  const ohne = toCandleSeries([CANDLE_DAY], "ohne")[0];
  assert.deepEqual(ohne, {
    time: "2019-09-26", open: 0.1, high: 0.3, low: -0.2, close: 0.05, color: R, borderColor: R, wickColor: R,
  });
  const alle = toCandleSeries([CANDLE_DAY], "alle")[0];
  assert.equal(alle.open, 0.2);
  assert.equal(alle.close, -0.1);
  assert.equal(alle.color, R);
  const up = toCandleSeries([{ ...CANDLE_DAY, ohlc: [-0.1, 0.2, -0.3, 0.1, 3] }], "ohne")[0];
  assert.equal(up.color, G);
  const flat = toCandleSeries([{ ...CANDLE_DAY, ohlc: [0.3, 0.3, 0.3, 0.3, 1] }], "ohne")[0];
  assert.equal(flat.color, G); // Close = Open zählt als grün
  assert.equal(toCandleSeries([CANDLE_DAY]).length, 1);
  assert.equal(toCandleSeries([CANDLE_DAY])[0].open, 0.1); // Standard "ohne"
});

test("candle gaps and days without values are whitespace (no OHLC keys)", () => {
  const gap = { ...CANDLE_DAY, date: "2019-09-27", coverage: "gap", gap_reason: "source_missing" };
  const empty = { ...CANDLE_DAY, date: "2019-09-28", ohlc: null, ohlc_all: null };
  const old = { date: "2019-09-29", coverage: "complete" }; // ältere Tagesdatei ohne ohlc
  for (const mode of ["ohne", "alle"]) {
    const series = toCandleSeries([gap, empty, old], mode);
    assert.deepEqual(series, [{ time: "2019-09-27" }, { time: "2019-09-28" }, { time: "2019-09-29" }]);
  }
});

test("candle tooltip lists O/H/L/C, batches and messages for the mode", () => {
  assert.equal(
    formatCandle(CANDLE_DAY, "ohne"),
    "Kerze O +0,10 H +0,30 L \u22120,20 C +0,05 (40 Sätze, 71 Nachrichten)"
  );
  assert.equal(
    formatCandle(CANDLE_DAY, "alle"),
    "Kerze O +0,20 H +0,25 L \u22120,40 C \u22120,10 (52 Sätze, 143 Nachrichten)"
  );
  assert.equal(formatCandle({ ...CANDLE_DAY, ohlc: [0.3, 0.3, 0.3, 0.3, 1] }, "ohne"),
    "Kerze O +0,30 H +0,30 L +0,30 C +0,30 (1 Satz, 71 Nachrichten)");
  assert.equal(formatCandle({ ...CANDLE_DAY, ohlc: null }, "ohne"), "Kerze —");
  assert.equal(formatCandle({ ...CANDLE_DAY, coverage: "gap" }, "ohne"), "Kerze —");
});
