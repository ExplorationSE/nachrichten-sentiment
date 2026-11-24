"use strict";

const MODE_STORAGE_KEY = "nachrichten-sentiment.zaehlung";
const VIEW_STORAGE_KEY = "nachrichten-sentiment.ansicht";

function readStored(key) {
  try {
    return window.localStorage.getItem(key);
  } catch {
    return null;
  }
}

function remember(key, param, value) {
  try {
    window.localStorage.setItem(key, value);
  } catch {
    // Ohne Speicherzugriff (z. B. privater Modus) bleibt die Auswahl nur in der Adresse erhalten.
  }
  try {
    const url = new URL(window.location.href);
    url.searchParams.set(param, value);
    window.history.replaceState(null, "", url);
  } catch {
    // Manche Umgebungen (z. B. file:// oder Sandbox-iframes) verbieten das Ändern der Adresse.
  }
}

function markButtons(selector, attribute, value) {
  document.querySelectorAll(selector + " button").forEach((el) => {
    const active = el.getAttribute(attribute) === value;
    el.classList.toggle("on", active);
    el.setAttribute("aria-checked", active ? "true" : "false");
  });
}

function markModeButtons(mode) {
  markButtons("#modes", "data-mode", mode);
}

let currentMode = resolveMode(window.location.search, readStored(MODE_STORAGE_KEY));
let currentView = resolveView(window.location.search, readStored(VIEW_STORAGE_KEY));
let openDate = null;

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
    wrap.appendChild(document.createTextNode(" " + formatSentiment(item.sentiment)));
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
  const candles = lineChart.addCandlestickSeries({
    upColor: "#26a69a",
    downColor: "#ef5350",
    borderUpColor: "#26a69a",
    borderDownColor: "#ef5350",
    wickUpColor: "#26a69a",
    wickDownColor: "#ef5350",
    priceLineVisible: false,
    visible: false,
  });
  const byDate = Object.fromEntries(days.map((d) => [d.date, d]));
  let tipDate = null;

  function render(mode) {
    // Lücken bleiben in beiden Zählweisen Whitespace-Punkte ohne value.
    const bars = toBarSeries(days, mode);
    const linePoints = toLineSeries(days, mode);
    up.setData(bars.up);
    down.setData(bars.down);
    line.setData(
      linePoints.map((p) =>
        p.value === null || p.value === undefined
          ? { time: p.time }
          : { time: p.time, value: p.value, color: p.color }
      )
    );
    // Lücken bleiben auch als Kerze Whitespace-Punkte ohne OHLC.
    candles.setData(toCandleSeries(days, mode));
  }

  function showView(view) {
    line.applyOptions({ visible: view === "linie" });
    candles.applyOptions({ visible: view === "kerzen" });
    markButtons("#views", "data-view", view);
  }

  function showTip(date) {
    tipDate = date;
    const row = byDate[date];
    if (!row) {
      tooltip.textContent = "";
      return;
    }
    let text = formatTooltip(row, currentMode);
    if (currentView === "kerzen") text += " · " + formatCandle(row, currentMode);
    tooltip.textContent = text;
  }

  render(currentMode);
  markModeButtons(currentMode);
  showView(currentView);

  document.getElementById("views").addEventListener("click", (event) => {
    const button = event.target.closest("button");
    if (!button) return;
    const view = resolveView("", button.getAttribute("data-view"));
    if (view === currentView) return;
    currentView = view;
    showView(view);
    if (tipDate) showTip(tipDate);
    remember(VIEW_STORAGE_KEY, "ansicht", view);
  });

  document.getElementById("modes").addEventListener("click", (event) => {
    const button = event.target.closest("button");
    if (!button) return;
    const mode = resolveMode("", button.getAttribute("data-mode"));
    if (mode === currentMode) return;
    currentMode = mode;
    markModeButtons(mode);
    // Sichtbaren Zeitraum beim Datenwechsel beibehalten.
    const visible = barChart.timeScale().getVisibleRange();
    render(mode);
    if (visible) {
      barChart.timeScale().setVisibleRange(visible);
      lineChart.timeScale().setVisibleRange(visible);
    }
    if (tipDate) showTip(tipDate);
    if (openDate) updateDayHeading(openDate, byDate[openDate]);
    // Erst nach dem Neuzeichnen merken, damit ein Speicherfehler die Anzeige nicht blockiert.
    remember(MODE_STORAGE_KEY, "zaehlung", mode);
  });

  barChart.subscribeCrosshairMove((param) => {
    if (param && param.time) showTip(param.time);
  });
  lineChart.subscribeCrosshairMove((param) => {
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
  const initial = initialRange(days);
  if (initial) {
    // Nach einer langen Sammelpause (z. B. 2015–2019 noch nicht nachgeholt) mit dem zusammenhängenden Bereich starten;
    // „Maximum“ zeigt weiterhin alles.
    document.querySelectorAll("#ranges button").forEach((el) => el.classList.remove("on"));
    barChart.timeScale().setVisibleRange(initial);
    lineChart.timeScale().setVisibleRange(initial);
  } else {
    barChart.timeScale().fitContent();
    lineChart.timeScale().fitContent();
  }
}

function updateDayHeading(date, row) {
  const heading = document.querySelector("#headlines h2");
  if (heading) heading.textContent = formatDayHeading(date, row, currentMode);
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
  heading.textContent = formatDayHeading(date, row, currentMode);
  root.appendChild(heading);
  openDate = date;
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
