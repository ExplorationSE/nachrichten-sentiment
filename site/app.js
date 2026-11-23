"use strict";

async function loadDaily() {
  const response = await fetch("data/nvda-daily.json");
  return response.json();
}

function lastCompleteDate(days) {
  for (let i = days.length - 1; i >= 0; i -= 1) {
    if (days[i].coverage === "complete") return days[i].date;
  }
  return days.length ? days[days.length - 1].date : null;
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
  const payload = await fetch("data/nvda/" + month + ".json").then((r) => r.json());
  const items = payload[date] || [];
  const stems = items.filter((item) => !item.is_near_duplicate);
  const dups = items.filter((item) => item.is_near_duplicate);
  const grouped = stems.map((stem) => {
    const children = dups.filter((item) => item.near_duplicate_of === stem.gkg_record_id);
    return { stem, children };
  });
  const note = row && row.coverage === "gap" ? " (unvollständig)" : "";
  root.innerHTML = "<h2>Schlagzeilen " + date + note + "</h2>" + grouped.map((group) => {
    const title = group.stem.title || "Titel nicht verfügbar";
    const value = group.stem.sentiment === null || group.stem.sentiment === undefined
      ? "—"
      : String(group.stem.sentiment);
    const main = '<div><a href="' + group.stem.url + '" target="_blank" rel="noopener">' + title + "</a> " + value + "</div>";
    const extra = group.children.map((child) => {
      const ct = child.title || "Titel nicht verfügbar";
      return '<div class="dup"><a href="' + child.url + '" target="_blank" rel="noopener">' + ct + "</a></div>";
    }).join("");
    return main + extra;
  }).join("");
}

loadDaily().then((payload) => attachCharts(payload.days || []));
