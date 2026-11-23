"use strict";

function formatNumber(value) {
  const sign = value > 0 ? "+" : value < 0 ? "\u2212" : "";
  const abs = Math.abs(value);
  return sign + abs.toFixed(2).replace(".", ",");
}

function formatTooltip(row) {
  const gapPrefix = row.coverage === "gap" ? "unvollständig — " : "";
  let text =
    gapPrefix +
    row.count_unique_url +
    " Nachrichten: " +
    row.count_positive +
    " positiv, " +
    row.count_neutral +
    " neutral, " +
    row.count_negative +
    " negativ";
  if (row.sentiment_mean === null || row.sentiment_mean === undefined) {
    text += ", Stimmung —";
  } else {
    const formatted =
      row.sentiment_mean > 0
        ? "+" + row.sentiment_mean.toFixed(2).replace(".", ",")
        : formatNumber(row.sentiment_mean);
    text += ", Stimmung " + formatted;
  }
  if (row.count_without_sentiment > 0) {
    text += ", " + row.count_without_sentiment + " ohne Wert";
  }
  if (row.count_after_near_dup_collapse !== undefined) {
    text += " (" + row.count_after_near_dup_collapse + " ohne Nahduplikate)";
  }
  return text;
}

function toBarSeries(days) {
  const up = [];
  const down = [];
  for (const day of days) {
    const gap = day.coverage === "gap";
    up.push({ time: day.date, value: gap ? null : day.count_positive });
    down.push({ time: day.date, value: gap ? null : -day.count_negative });
  }
  return { up, down };
}

function toLineSeries(days) {
  return days.map((day) => {
    if (day.coverage === "gap" || day.sentiment_mean === null || day.sentiment_mean === undefined) {
      return { time: day.date, value: null, color: "#8b949e" };
    }
    return {
      time: day.date,
      value: day.sentiment_mean,
      color: day.sentiment_mean >= 0 ? "#26a69a" : "#ef5350",
    };
  });
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

function rangeStart(endDate, rangeKey) {
  if (rangeKey === "1M") return shiftDate(endDate, -1, 0);
  if (rangeKey === "3M") return shiftDate(endDate, -3, 0);
  if (rangeKey === "1J") return shiftDate(endDate, 0, -1);
  if (rangeKey === "5J") return shiftDate(endDate, 0, -5);
  return null;
}

if (typeof module !== "undefined" && module.exports) {
  module.exports = { formatTooltip, toBarSeries, toLineSeries, rangeStart, safeHref };
}
