"use strict";

// Zählweisen: "ohne" = ohne Nahduplikate (Standard), "alle" = alle Nachrichten inkl. Nahduplikate.
const DEFAULT_MODE = "ohne";
const MODES = ["ohne", "alle"];
const MODE_LABELS = { ohne: "ohne Nahduplikate", alle: "alle Nachrichten" };

function resolveMode(search, stored) {
  if (typeof search === "string" && search) {
    const fromUrl = new URLSearchParams(search).get("zaehlung");
    if (MODES.includes(fromUrl)) return fromUrl;
  }
  if (MODES.includes(stored)) return stored;
  return DEFAULT_MODE;
}

function modeCounts(row, mode) {
  if (mode === "alle") {
    // Ältere Tagesdateien ohne *_all-Felder liefern undefined; das zeigt der Aufrufer als Lücke.
    return {
      positive: row.count_positive_all,
      neutral: row.count_neutral_all,
      negative: row.count_negative_all,
      without: row.count_without_sentiment_all,
      mean: row.sentiment_mean_all,
      total: row.count_unique_url,
    };
  }
  return {
    positive: row.count_positive,
    neutral: row.count_neutral,
    negative: row.count_negative,
    without: row.count_without_sentiment,
    mean: row.sentiment_mean,
    total: row.count_after_near_dup_collapse,
  };
}

function formatNumber(value) {
  const sign = value > 0 ? "+" : value < 0 ? "\u2212" : "";
  const abs = Math.abs(value);
  return sign + abs.toFixed(2).replace(".", ",");
}

function gapLabel(row) {
  if (row.coverage !== "gap") return "";
  return row.gap_reason === "source_missing" ? "Quelle fehlt (GDELT)" : "unvollständig";
}

function formatTooltip(row, mode) {
  const label = gapLabel(row);
  const gapPrefix = label ? label + " — " : "";
  const counts = modeCounts(row, mode);
  let text = gapPrefix + row.count_unique_url + " Nachrichten";
  if (mode === "alle") {
    // Klassen und Stimmung beziehen sich auf alle Nachrichten inkl. Nahduplikate.
    text += " inkl. Nahduplikate";
    if (row.count_after_near_dup_collapse !== undefined) {
      text += " (" + row.count_after_near_dup_collapse + " ohne)";
    }
  } else if (row.count_after_near_dup_collapse !== undefined) {
    // Klassen und Stimmung beziehen sich auf die Meldungen ohne Nahduplikate.
    text += ", " + row.count_after_near_dup_collapse + " ohne Nahduplikate";
  }
  if (counts.positive === undefined) {
    return text + ": Werte für diese Zählweise fehlen";
  }
  text +=
    ": " +
    counts.positive +
    " positiv, " +
    counts.neutral +
    " neutral, " +
    counts.negative +
    " negativ";
  text += ", Stimmung " + formatSentiment(counts.mean);
  if (counts.without > 0) {
    text += ", " + counts.without + " ohne Wert";
  }
  return text;
}

function formatSentiment(value) {
  if (value === null || value === undefined) return "—";
  return formatNumber(value);
}

function formatDayHeading(date, row, mode) {
  let text = "Schlagzeilen " + date;
  if (!row) return text;
  const label = gapLabel(row);
  if (label) text += " (" + label + ")";
  text +=
    " — " +
    row.count_unique_url +
    " Nachrichten, " +
    row.count_after_near_dup_collapse +
    " ohne Nahduplikate";
  if (MODE_LABELS[mode]) text += " (Ansicht: " + MODE_LABELS[mode] + ")";
  return text;
}

function toBarSeries(days, mode) {
  const up = [];
  const down = [];
  for (const day of days) {
    const counts = modeCounts(day, mode);
    if (day.coverage === "gap" || counts.positive === undefined || counts.negative === undefined) {
      // Ohne value erkennt Lightweight Charts den Tag als Lücke (Whitespace), nicht als 0.
      up.push({ time: day.date });
      down.push({ time: day.date });
      continue;
    }
    up.push({ time: day.date, value: counts.positive });
    down.push({ time: day.date, value: -counts.negative });
  }
  return { up, down };
}

function signColor(value) {
  return value >= 0 ? "#26a69a" : "#ef5350";
}

function toLineSeries(days, mode) {
  const points = days.map((day) => {
    const mean = modeCounts(day, mode).mean;
    if (day.coverage === "gap" || mean === null || mean === undefined) {
      return { time: day.date, value: null, color: "#8b949e" };
    }
    return { time: day.date, value: mean, color: signColor(mean) };
  });
  // Lightweight Charts färbt den Abschnitt i→i+1 mit der Farbe von Punkt i. Damit sich jeder
  // Abschnitt nach seinem Endpunkt richtet, übernimmt Punkt i die Farbe des Folgepunkts.
  // Vor einer Lücke und am Ende gibt es keinen Abschnitt; dort bleibt die eigene Farbe.
  for (let i = 0; i < points.length - 1; i += 1) {
    const next = points[i + 1];
    if (points[i].value !== null && next.value !== null) points[i].color = signColor(next.value);
  }
  return points;
}

function pad(value) {
  return String(value).padStart(2, "0");
}

function shiftDate(iso, months, years) {
  const [year, month, day] = iso.split("-").map(Number);
  const date = new Date(Date.UTC(year + years, month - 1 + months, 1));
  const lastDay = new Date(
    Date.UTC(date.getUTCFullYear(), date.getUTCMonth() + 1, 0)
  ).getUTCDate();
  date.setUTCDate(Math.min(day, lastDay));
  return (
    date.getUTCFullYear() +
    "-" +
    pad(date.getUTCMonth() + 1) +
    "-" +
    pad(date.getUTCDate())
  );
}

function safeHref(url) {
  if (typeof url !== "string") return null;
  const trimmed = url.trim();
  if (/^https?:/i.test(trimmed)) return trimmed;
  return null;
}

// Ab dieser Länge (Tage ohne vollständige Daten) gilt eine Lücke als Sammelpause, z. B. ein später nachzuholender Bereich.
const LONG_GAP_DAYS = 90;

function initialRange(days, minGapDays = LONG_GAP_DAYS) {
  // Startansicht: nach der letzten langen Lücke bis zum letzten vollständigen Tag; sonst null (alles zeigen).
  let run = 0;
  let from = null;
  let to = null;
  for (const day of days) {
    if (day.coverage === "complete") {
      if (run >= minGapDays) from = day.date;
      run = 0;
      to = day.date;
    } else {
      run += 1;
    }
  }
  if (!from || !to) return null;
  return { from, to };
}

function rangeStart(endDate, rangeKey) {
  if (rangeKey === "1M") return shiftDate(endDate, -1, 0);
  if (rangeKey === "3M") return shiftDate(endDate, -3, 0);
  if (rangeKey === "1J") return shiftDate(endDate, 0, -1);
  if (rangeKey === "5J") return shiftDate(endDate, 0, -5);
  return null;
}

if (typeof module !== "undefined" && module.exports) {
  module.exports = { initialRange, DEFAULT_MODE, MODE_LABELS, resolveMode, modeCounts, formatTooltip, gapLabel, formatSentiment, formatDayHeading, toBarSeries, toLineSeries, rangeStart, safeHref };
}
