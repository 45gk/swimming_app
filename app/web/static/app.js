const $ = (selector) => document.querySelector(selector);
const formatNumber = (value, digits = 0) => value == null ? "—" : new Intl.NumberFormat("ru-RU", { maximumFractionDigits: digits }).format(value);
const formatPace = (seconds) => {
  if (seconds == null || !Number.isFinite(seconds)) return "—";
  const rounded = Math.round(seconds);
  return `${Math.floor(rounded / 60)}:${String(rounded % 60).padStart(2, "0")}`;
};
const formatDuration = (seconds) => {
  if (seconds == null || !Number.isFinite(seconds)) return "—";
  const rounded = Math.round(seconds);
  const hours = Math.floor(rounded / 3600);
  const minutes = Math.floor((rounded % 3600) / 60);
  const rest = rounded % 60;
  return hours ? `${hours} ч ${minutes} мин` : `${minutes}:${String(rest).padStart(2, "0")}`;
};
const formatDate = (value, options = { day: "numeric", month: "short" }) => {
  if (!value) return "—";
  return new Intl.DateTimeFormat("ru-RU", options).format(new Date(value));
};
const escapeHtml = (value) => String(value ?? "").replace(/[&<>"']/g, (char) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[char]);

let toastTimer;
function notify(message, isError = false) {
  const toast = $("#toast");
  toast.textContent = message;
  toast.classList.toggle("error", isError);
  toast.classList.add("show");
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => toast.classList.remove("show"), 4200);
}

function renderWeeklyChart(weeks) {
  const root = $("#weekly-chart");
  if (!weeks?.length) {
    root.innerHTML = '<div class="chart-empty">Здесь появится график объёма</div>';
    return;
  }
  const width = 640, height = 188, left = 40, right = 10, top = 8, bottom = 31;
  const chartHeight = height - top - bottom;
  const max = Math.max(100, ...weeks.map((week) => week.distance_m));
  const slot = (width - left - right) / weeks.length;
  const barWidth = Math.min(38, slot * .47);
  let svg = `<svg viewBox="0 0 ${width} ${height}" role="img" aria-label="Недельный объём плавания">`;
  for (let line = 0; line <= 3; line++) {
    const y = top + chartHeight * line / 3;
    const value = Math.round(max * (1 - line / 3));
    svg += `<line x1="${left}" y1="${y}" x2="${width - right}" y2="${y}" stroke="#edf1ed" stroke-width="1"/><text x="0" y="${y + 3}" fill="#a4afae" font-size="8" font-family="DM Mono,monospace">${formatNumber(value)}</text>`;
  }
  weeks.forEach((week, index) => {
    const x = left + index * slot + (slot - barWidth) / 2;
    const barHeight = week.distance_m ? Math.max(3, chartHeight * week.distance_m / max) : 0;
    const y = top + chartHeight - barHeight;
    const date = new Date(`${week.week_start}T12:00:00`);
    const label = new Intl.DateTimeFormat("ru-RU", { day: "numeric", month: "short" }).format(date).replace(".", "");
    svg += `<rect x="${x}" y="${y}" width="${barWidth}" height="${barHeight}" rx="5" fill="${index === weeks.length - 1 ? "#4eac9e" : "#9ad8c9"}"/>`;
    if (week.distance_m) svg += `<text x="${x + barWidth / 2}" y="${Math.max(10, y - 6)}" text-anchor="middle" fill="#66817f" font-size="8" font-family="DM Mono,monospace">${formatNumber(week.distance_m)}</text>`;
    svg += `<text x="${x + barWidth / 2}" y="${height - 8}" text-anchor="middle" fill="#9aa7a6" font-size="8" font-family="DM Mono,monospace">${escapeHtml(label)}</text>`;
  });
  root.innerHTML = svg + "</svg>";
  const total = weeks.reduce((sum, week) => sum + week.distance_m, 0);
  $("#week-summary").textContent = `${formatNumber(total)} м за ${weeks.length} ${weeks.length === 1 ? "неделю" : "нед."}`;
}

function renderSplitChart(session) {
  const root = $("#split-chart");
  const lengths = (session?.length_series || []).filter((row) => row.duration_seconds > 0);
  if (!lengths.length) {
    root.innerHTML = '<div class="chart-empty">Для этой тренировки нет записей по длинам</div>';
    $("#split-range").textContent = "—";
    return;
  }
  const width = 640, height = 177, left = 24, right = 14, top = 18, bottom = 24;
  const min = Math.min(...lengths.map((row) => row.duration_seconds));
  const max = Math.max(...lengths.map((row) => row.duration_seconds));
  const range = Math.max(max - min, 1);
  const innerWidth = width - left - right, innerHeight = height - top - bottom;
  const points = lengths.map((row, index) => ({
    x: left + (lengths.length === 1 ? innerWidth / 2 : innerWidth * index / (lengths.length - 1)),
    y: top + innerHeight * (1 - (row.duration_seconds - min) / range),
    row,
  }));
  const path = points.map((point, index) => `${index ? "L" : "M"}${point.x},${point.y}`).join(" ");
  const area = `${path} L${points.at(-1).x},${height - bottom} L${points[0].x},${height - bottom} Z`;
  const grid = [0, 1, 2].map((i) => {
    const y = top + innerHeight * i / 2;
    return `<line x1="${left}" y1="${y}" x2="${width - right}" y2="${y}" stroke="#eef1ee"/><text x="0" y="${y + 3}" fill="#a4afae" font-size="8" font-family="DM Mono,monospace">${(max - range * i / 2).toFixed(0)}с</text>`;
  }).join("");
  const circles = points.map((point, index) => `<circle cx="${point.x}" cy="${point.y}" r="${index === points.length - 1 ? 3.5 : 2.3}" fill="${index === points.length - 1 ? "#e98970" : "#fff"}" stroke="#e98970" stroke-width="1.5"><title>${point.row.length_index}-я длина: ${point.row.duration_seconds} с${point.row.stroke_count == null ? "" : `, ${point.row.stroke_count} гребков`}</title></circle>`).join("");
  root.innerHTML = `<svg viewBox="0 0 ${width} ${height}" role="img" aria-label="Время прохождения каждого отрезка"><defs><linearGradient id="splitFill" x1="0" x2="0" y1="0" y2="1"><stop offset="0" stop-color="#ef9a80" stop-opacity=".2"/><stop offset="1" stop-color="#ef9a80" stop-opacity="0"/></linearGradient></defs>${grid}<path d="${area}" fill="url(#splitFill)"/><path d="${path}" fill="none" stroke="#e98970" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>${circles}<text x="${left}" y="${height - 4}" fill="#9aa7a6" font-size="8" font-family="DM Mono,monospace">1</text><text x="${width - right}" y="${height - 4}" text-anchor="end" fill="#9aa7a6" font-size="8" font-family="DM Mono,monospace">${lengths.length}</text></svg>`;
  $("#split-caption").textContent = `${formatNumber(session.pool_length_m)} м · ${lengths.length} отрезков`;
  $("#split-range").textContent = `${formatNumber(min, 1)}–${formatNumber(max, 1)} с`;
}

function localizeInsight(insight, session, count) {
  const evidence = insight.evidence || {};
  if (insight.kind === "within_session_pace_fade") {
    const quarter = Math.max(2, Math.floor(evidence.length_count / 4));
    return { icon: "↘", title: "К финишу отрезки стали медленнее", detail: `Последние ${quarter} длин заняли в среднем ${formatNumber(evidence.last_quarter_avg_seconds, 1)} с против ${formatNumber(evidence.first_quarter_avg_seconds, 1)} с в начале.` };
  }
  if (insight.kind === "within_session_stroke_increase") {
    return { icon: "≋", title: "Больше гребков к концу", detail: `В последней четверти — ${formatNumber(evidence.last_quarter_avg_strokes, 1)} на длину против ${formatNumber(evidence.first_quarter_avg_strokes, 1)} в первой. Это наблюдение только по одной тренировке.` };
  }
  if (insight.kind === "within_session_heart_rate_shift") {
    const direction = evidence.early_late_change_bpm > 0 ? "выше" : "ниже";
    return { icon: "♡", title: "Пульс менялся по ходу заплыва", detail: `Среднее в заключительной части на ${formatNumber(Math.abs(evidence.early_late_change_bpm), 1)} уд/мин ${direction}, чем в начале.` };
  }
  if (insight.kind === "personal_best_distance") {
    return { icon: "↗", title: count === 1 ? "Первая отметка" : "Самый длинный заплыв", detail: `${formatNumber(evidence.distance_m || session?.distance_m)} м. С новыми тренировками появится сравнение рекордов.` };
  }
  if (insight.kind === "training_frequency") {
    return { icon: "◷", title: "Ритм тренировок", detail: `Медианный перерыв между заплывами — ${formatNumber(evidence.median_gap_days)} дн.` };
  }
  if (insight.kind === "recent_pace_change") {
    const direction = evidence.change_percent > 0 ? "медленнее" : "быстрее";
    return { icon: "≈", title: "Изменение темпа", detail: `Последние четыре сессии в среднем на ${formatNumber(Math.abs(evidence.change_percent), 1)}% ${direction} предыдущих четырёх.` };
  }
  return { icon: "✳", title: insight.title, detail: insight.detail };
}

function renderInsights(insights, session, sessionCount) {
  const list = $("#insight-list");
  const cards = (insights || []).map((insight) => localizeInsight(insight, session, sessionCount));
  if (sessionCount === 1) cards.push({ icon: "◎", title: "Начало личной статистики", detail: "Это первая тренировка в журнале. После следующих заплывов станет видна динамика по неделям и темпу." });
  if (!cards.length) {
    list.innerHTML = '<div class="insight-placeholder">Пока недостаточно сессий для наблюдений.</div>';
    return;
  }
  list.innerHTML = cards.map((card) => `<article class="insight-card"><span class="insight-symbol">${escapeHtml(card.icon)}</span><div><div class="insight-title">${escapeHtml(card.title)}</div><div class="insight-detail">${escapeHtml(card.detail)}</div></div></article>`).join("");
}

function renderSessions(sessions) {
  const body = $("#session-rows");
  $("#history-count").textContent = `${sessions.length} ${sessions.length === 1 ? "сессия" : "сессий"}`;
  if (!sessions.length) {
    body.innerHTML = '<tr class="empty-row"><td colspan="6">Импортируй экспорт Apple Health, чтобы увидеть историю.</td></tr>';
    return;
  }
  body.innerHTML = [...sessions].reverse().map((session) => `<tr><td>${escapeHtml(formatDate(session.started_at, { day: "numeric", month: "short", year: "numeric" }))}</td><td><span class="distance-pill">${formatNumber(session.distance_m)} м</span></td><td>${formatDuration(session.duration_seconds)}</td><td>${formatPace(session.pace_seconds_per_100m)}</td><td>${session.average_heart_rate_bpm == null ? "—" : `${formatNumber(session.average_heart_rate_bpm)} уд/мин`}</td><td>${formatNumber(session.stroke_count)}</td></tr>`).join("");
}

function renderDashboard(analysis, summary) {
  const sessions = analysis.sessions || [];
  const latest = sessions.at(-1);
  $("#metric-sessions").textContent = formatNumber(analysis.session_count);
  $("#metric-sessions-foot").textContent = analysis.session_count === 1 ? "Первая тренировка" : "Всего сессий";
  $("#metric-distance").textContent = formatNumber(summary.total_distance_m);
  $("#metric-pace").textContent = formatPace(summary.average_pace_seconds_per_100m);
  const hrPoints = sessions.filter((session) => session.average_heart_rate_bpm != null && session.heart_rate_samples > 0);
  const weightedHr = hrPoints.length ? hrPoints.reduce((sum, session) => sum + session.average_heart_rate_bpm * session.heart_rate_samples, 0) / hrPoints.reduce((sum, session) => sum + session.heart_rate_samples, 0) : null;
  $("#metric-heart").textContent = weightedHr == null ? "—" : formatNumber(weightedHr);
  if (latest) {
    $("#hero-last-distance").textContent = `${formatNumber(latest.distance_m)} м`;
    $("#hero-last-date").textContent = formatDate(latest.started_at, { day: "numeric", month: "long", year: "numeric" });
    $("#latest-date").textContent = formatDate(latest.started_at, { weekday: "long", day: "numeric", month: "long" });
    $("#latest-distance").textContent = formatNumber(latest.distance_m);
    $("#latest-pace").textContent = `${formatPace(latest.pace_seconds_per_100m)} / 100 м`;
    $("#latest-moving-pace").textContent = latest.estimated_moving_pace_seconds_per_100m == null ? "—" : `${formatPace(latest.estimated_moving_pace_seconds_per_100m)} / 100 м`;
    $("#latest-duration").textContent = formatDuration(latest.duration_seconds);
    $("#latest-heart").textContent = latest.average_heart_rate_bpm == null ? "—" : `${formatNumber(latest.average_heart_rate_bpm)} уд/мин`;
    $("#latest-strokes").textContent = latest.average_strokes_per_length == null ? "—" : formatNumber(latest.average_strokes_per_length, 1);
    $("#latest-swolf").textContent = latest.average_swolf == null ? "—" : formatNumber(latest.average_swolf, 1);
    $("#latest-footnote").textContent = latest.recorded_moving_time_seconds == null ? "Общий темп включает время между записанными отрезками." : `По отрезкам зафиксировано ${formatDuration(latest.recorded_moving_time_seconds)} движения; оба темпа рассчитаны по разным временным интервалам.`;
  }
  renderWeeklyChart(analysis.weekly_training);
  renderSplitChart(latest);
  renderInsights(analysis.insights, latest, analysis.session_count);
  renderSessions(sessions);
}

async function loadDashboard() {
  document.body.classList.add("loading");
  try {
    const [analysisResponse, summaryResponse] = await Promise.all([fetch("/api/analysis"), fetch("/api/summary")]);
    if (!analysisResponse.ok || !summaryResponse.ok) throw new Error("Не удалось загрузить аналитику. Проверь, запущен ли сервер и доступна ли база данных.");
    const [analysis, summary] = await Promise.all([analysisResponse.json(), summaryResponse.json()]);
    renderDashboard(analysis, summary);
  } catch (error) {
    notify(error.message || "Не удалось загрузить данные.", true);
  } finally {
    document.body.classList.remove("loading");
  }
}

function triggerFilePicker() { $("#file-input").click(); }

async function importFile(file) {
  if (!file) return;
  const valid = /\.(zip|xml)$/i.test(file.name);
  if (!valid) { notify("Выбери ZIP-архив или export.xml.", true); return; }
  $("#upload-title").textContent = "Импортирую файл…";
  $("#upload-subtitle").textContent = "Большой архив может обрабатываться несколько секунд";
  try {
    const response = await fetch(`/api/import?filename=${encodeURIComponent(file.name)}`, {
      method: "POST",
      headers: { "Content-Type": "application/octet-stream" },
      body: file,
    });
    const result = await response.json();
    if (!response.ok) throw new Error(result.detail || "Импорт не удался.");
    notify(`Импортировано: ${result.swimming_workouts_found} тренировок, ${formatNumber(result.measurements_found)} измерений.`);
    await loadDashboard();
  } catch (error) {
    notify(error.message || "Ошибка импорта. Попробуй ещё раз.", true);
  } finally {
    $("#upload-title").textContent = "Перетащи файл сюда";
    $("#upload-subtitle").textContent = "или нажми, чтобы выбрать ZIP / XML";
    $("#file-input").value = "";
  }
}

$("#top-import").addEventListener("click", triggerFilePicker);
$("#drop-zone").addEventListener("click", triggerFilePicker);
$("#file-input").addEventListener("change", (event) => importFile(event.target.files[0]));
const dropZone = $("#drop-zone");
for (const eventName of ["dragenter", "dragover"]) dropZone.addEventListener(eventName, (event) => { event.preventDefault(); dropZone.classList.add("dragging"); });
for (const eventName of ["dragleave", "drop"]) dropZone.addEventListener(eventName, (event) => { event.preventDefault(); dropZone.classList.remove("dragging"); });
dropZone.addEventListener("drop", (event) => importFile(event.dataTransfer.files[0]));

const navLinks = [...document.querySelectorAll(".main-nav a")];
const sections = navLinks.map((link) => document.querySelector(link.getAttribute("href"))).filter(Boolean);
if ("IntersectionObserver" in window) {
  const observer = new IntersectionObserver((entries) => entries.forEach((entry) => {
    if (entry.isIntersecting) navLinks.forEach((link) => link.classList.toggle("active", link.hash === `#${entry.target.id}`));
  }), { rootMargin: "-25% 0px -65% 0px" });
  sections.forEach((section) => observer.observe(section));
}

loadDashboard();
