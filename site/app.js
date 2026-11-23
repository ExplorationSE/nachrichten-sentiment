"use strict";

async function loadDaily() {
  const response = await fetch("data/nvda-daily.json");
  if (!response.ok) throw new Error("load failed");
  return response.json();
}

function showLoadError(target) {
  if (target) target.textContent = "Daten konnten nicht geladen werden.";
}

function lastCompleteDate(days) {
  for (let i = days.length - 1; i >= 0; i -= 1) {
    if (days[i].coverage === "complete") return days[i].date;
  }
  return days.length ? days[days.length - 1].date : null;
}

function appendHeadline(container, item, withSentiment, className) {
  const wrap = document.createElement("div");
  if (className) wrap.setAttribute("class", className);
  const title = item.title || "Titel nicht verfügbar";
  const href = safeHref(item.url);
  if (href) {
    const link = document.createElement("a");
    link.setAttribute("href", href);
    link.setAttribute("target", "_blank");
    link.setAttribute("rel", "noopener noreferrer");
    link.textContent = title;
    wrap.appendChild(link);
  } else {
    wrap.appendChild(document.createTextNode(title));
  }
  if (withSentiment) {
    const value = item.sentiment === null || item.sentiment === undefined
      ? "—"
      : String(item.sentiment);
    wrap.appendChild(document.createTextNode(" " + value));
  }
  container.appendChild(wrap);
}

function attachCharts(days) {
  const barHost = document.getElementById("bars");
  const lineHost = document.getElementById("line");
  const tooltip = document.getElementById("tooltip");
  const barChart = LightweightCharts.createChart(barHost, {
    layout: { background: { color: "#161b22" }, textColor: "#e6edf3" },
    grid: { vertLines: { color: "#30363d" }, horzLines: { color: "#30363d" } },
    rightPriceScale: { borderColor: "#30363d" },
    timeScale: { borderColor: "#30363d" },
  });
  const lineChart = LightweightCharts.createChart(lineHost, {
    layout: { background: { color: "#161b22" }, textColor: "#e6edf3" },
    grid: { vertLines: { color: "#30363d" }, horzLines: { color: "#30363d" } },
    rightPriceScale: { borderColor: "#30363d" },
    timeScale: { borderColor: "#30363d" },
  });
  const up = barChart.addHistogramSeries({ color: "#26a69a", priceFormat: { type: "volume" } });
  const down = barChart.addHistogramSeries({ color: "#ef5350", priceFormat: { type: "volume" } });
  const line = lineChart.addLineSeries({ color: "#e6edf3", priceLineVisible: true });
  const bars = toBarSeries(days);
  const linePoints = toLineSeries(days);
  up.setData(bars.up);
  down.setData(bars.down);
  line.setData(
    linePoints.map((p) =>
      p.value === null || p.value === undefined
        ? { time: p.time }
        : { time: p.time, value: p.value, color: p.color }
    )
  );
  const byDate = Object.fromEntries(days.map((d) => [d.date, d]));

  function showTip(date) {
    const row = byDate[date];
    tooltip.textContent = row ? formatTooltip(row) : "";
  }

  barChart.subscribeCrosshairMove((param) => {
    if (param && param.time) showTip(param.time);
  });
  barChart.subscribeClick((param) => {
    if (param && param.time) openDay(param.time, byDate[param.time]);
  });
  document.getElementById("ranges").addEventListener("click", (event) => {
    const button = event.target.closest("button");
    if (!button) return;
    document.querySelectorAll("#ranges button").forEach((el) => el.classList.remove("on"));
    button.classList.add("on");
    const end = lastCompleteDate(days);
    const start = rangeStart(end, button.getAttribute("data-range"));
    if (!start) {
      barChart.timeScale().fitContent();
      lineChart.timeScale().fitContent();
      return;
    }
    barChart.timeScale().setVisibleRange({ from: start, to: end });
    lineChart.timeScale().setVisibleRange({ from: start, to: end });
  });
  barChart.timeScale().fitContent();
  lineChart.timeScale().fitContent();
}

async function openDay(date, row) {
  const root = document.getElementById("headlines");
  const month = date.slice(0, 7);
  let payload;
  try {
    const response = await fetch("data/nvda/" + month + ".json");
    if (!response.ok) throw new Error("load failed");
    payload = await response.json();
  } catch {
    showLoadError(root);
    return;
  }
  const items = payload[date] || [];
  const stems = items.filter((item) => !item.is_near_duplicate);
  const dups = items.filter((item) => item.is_near_duplicate);
  const grouped = stems.map((stem) => {
    const children = dups.filter((item) => item.near_duplicate_of === stem.gkg_record_id);
    return { stem, children };
  });
  root.replaceChildren();
  const heading = document.createElement("h2");
  const note = row && row.coverage === "gap" ? " (" + gapLabel(row) + ")" : "";
  heading.textContent = "Schlagzeilen " + date + note;
  root.appendChild(heading);
  for (const group of grouped) {
    appendHeadline(root, group.stem, true);
    for (const child of group.children) {
      appendHeadline(root, child, false, "dup");
    }
  }
}

loadDaily()
  .then((payload) => attachCharts(payload.days || []))
  .catch(() => showLoadError(document.getElementById("tooltip")));
