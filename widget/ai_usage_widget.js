// Combined Claude Pro + ChatGPT Plus widget for Scriptable.
// Replace these placeholders only in your private Scriptable copy.
const CONFIG = {
  baseUrl: "https://YOUR-PRIVATE-HOST",
  apiKey: "PASTE-YOUR-API-KEY",
  refreshMinutes: 30,
};

const COLORS = {
  bg: new Color("#1a1a1a"),
  muted: new Color("#999999"),
  claude: new Color("#DA7756"),
  chatgpt: new Color("#10A37F"),
};

function color(pct) {
  return new Color(pct < 50 ? "#34c759" : pct < 75 ? "#ffcc00" : pct < 90 ? "#ff9500" : "#ff3b30");
}

function circle(fill) {
  const ctx = new DrawContext();
  ctx.size = new Size(10, 10);
  ctx.opaque = false;
  ctx.setFillColor(fill);
  const path = new Path();
  path.addEllipse(new Rect(0, 0, 10, 10));
  ctx.addPath(path);
  ctx.fillPath();
  return ctx.getImage();
}

function header(parent, name, brand) {
  const stack = parent.addStack();
  stack.layoutHorizontally();
  stack.centerAlignContent();
  const image = stack.addImage(circle(brand));
  image.imageSize = new Size(10, 10);
  stack.addSpacer(6);
  const text = stack.addText(name);
  text.font = Font.boldSystemFont(14);
  text.textColor = Color.white();
}

function bar(pct, width) {
  const value = Math.max(0, Math.min(100, pct ?? 0));
  const ctx = new DrawContext();
  ctx.size = new Size(width, 8);
  ctx.opaque = false;
  ctx.setFillColor(new Color("#353535"));
  ctx.fillRoundedRect(new Rect(0, 0, width, 8), 4, 4);
  ctx.setFillColor(color(value));
  ctx.fillRoundedRect(new Rect(0, 0, Math.max(8, width * value / 100), 8), 4, 4);
  return ctx.getImage();
}

function row(parent, label, pct, width) {
  const stack = parent.addStack();
  stack.layoutHorizontally();
  stack.centerAlignContent();
  const name = stack.addText(label);
  name.font = Font.boldSystemFont(12);
  name.textColor = COLORS.muted;
  stack.addSpacer(6);
  if (typeof pct !== "number") {
    const missing = stack.addText("—");
    missing.textColor = COLORS.muted;
    return;
  }
  const image = stack.addImage(bar(pct, width));
  image.imageSize = new Size(width, 8);
  stack.addSpacer(6);
  const value = stack.addText(`${Math.round(pct)}%`);
  value.font = Font.boldSystemFont(12);
  value.textColor = color(pct);
}

function formatDateTime(value) {
  if (!value) return "—";
  const date = new Date(value);
  if (isNaN(date.getTime())) return "—";
  const months = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];
  const day = String(date.getDate()).padStart(2, "0");
  const hour = String(date.getHours()).padStart(2, "0");
  const minute = String(date.getMinutes()).padStart(2, "0");
  return `${day} ${months[date.getMonth()]} ${hour}:${minute}`;
}

function sessionReset(value) {
  if (!value) return "Not started yet";
  const date = new Date(value);
  if (isNaN(date.getTime()) || date.getTime() <= Date.now()) return "Not started yet";
  return formatDateTime(value);
}

function sessionResetLine(parent, resetAt) {
  const text = parent.addText(`5h reset: ${sessionReset(resetAt)}`);
  text.font = Font.systemFont(10);
  text.textColor = COLORS.muted;
  text.lineLimit = 1;
}

function weeklyProjection(parent, resetAt, projection) {
  const projected = projection?.projected_pct_at_reset;
  const suffix = typeof projected === "number" ? ` · ~${projected}% weekly` : "";
  const reset = parent.addText(`Reset ${formatDateTime(resetAt)}${suffix}`);
  reset.font = Font.boldSystemFont(10);
  reset.textColor = projection?.safe_until_reset === false ? new Color("#ff9500") : new Color("#999999");
  reset.lineLimit = 1;

  if (typeof projection?.safe_until_reset === "boolean") {
    parent.addSpacer(2);
    const status = parent.addText(projection.safe_until_reset ? "✅ Aman sampai reset" : "⚠️ Tidak aman sebelum reset");
    status.font = Font.boldSystemFont(10);
    status.textColor = projection.safe_until_reset ? new Color("#34c759") : new Color("#ff9500");
    status.lineLimit = 1;
  }
}

function sortedWindows(windows) {
  return [...(windows || [])].sort((a, b) => {
    const aDuration = a.window_duration_minutes ?? (a.window_hours ? a.window_hours * 60 : String(a.label).toLowerCase().includes("week") ? 10080 : 300);
    const bDuration = b.window_duration_minutes ?? (b.window_hours ? b.window_hours * 60 : String(b.label).toLowerCase().includes("week") ? 10080 : 300);
    return aDuration - bDuration;
  });
}

function findWindow(windows, duration, keyword) {
  return windows.find(item => item.window_duration_minutes === duration || item.window_hours * 60 === duration || String(item.label).toLowerCase().includes(keyword));
}

function claudeSection(parent, data, width, compact = false) {
  const session = data.session || {};
  const weekly = data.weekly || {};
  const projection = data.projection || {};
  header(parent, "Claude Pro", COLORS.claude);
  parent.addSpacer(5);
  row(parent, compact ? "5h" : "5 hour", session.pct_actual, width);
  if (!compact) {
    parent.addSpacer(2);
    sessionResetLine(parent, session.resets_at || session.reset_at);
  }
  parent.addSpacer(4);
  row(parent, compact ? "Wk" : "Weekly", weekly.pct_actual, width);
  if (!compact) {
    parent.addSpacer(6);
    weeklyProjection(parent, weekly.resets_at || weekly.reset_at || projection.reset_at, projection.status === "ok" ? projection : null);
  }
}

function chatgptSection(parent, data, width, compact = false) {
  const windows = sortedWindows(data.windows);
  const session = findWindow(windows, 300, "5 hour") || findWindow(windows, 300, "session") || {};
  const weekly = findWindow(windows, 10080, "week") || {};
  const projection = (data.projections || []).find(item => String(item.label).toLowerCase().includes("week"));
  header(parent, "ChatGPT Plus", COLORS.chatgpt);
  parent.addSpacer(5);
  row(parent, compact ? "5h" : "5 hour", session.used_percent, width);
  if (!compact) {
    parent.addSpacer(2);
    sessionResetLine(parent, session.reset_at);
  }
  parent.addSpacer(4);
  row(parent, compact ? "Wk" : "Weekly", weekly.used_percent, width);
  if (!compact) {
    parent.addSpacer(6);
    weeklyProjection(parent, weekly.reset_at || projection?.reset_at, projection);
  }
}

async function get(path) {
  const request = new Request(CONFIG.baseUrl + path);
  request.headers = { "X-API-Key": CONFIG.apiKey };
  request.timeoutInterval = 15;
  return request.loadJSON();
}

const fm = FileManager.local();
const cache = fm.joinPath(fm.documentsDirectory(), "ai_usage_widget_cache.json");

async function load() {
  const cached = fm.fileExists(cache) ? JSON.parse(fm.readString(cache)) : {};
  const [claude, chatgpt] = await Promise.all([
    get("/api/claude-usage").catch(() => cached.claude),
    get("/api/chatgpt-usage").catch(() => cached.chatgpt),
  ]);
  if (!claude && !chatgpt) throw new Error("offline");
  const data = { claude, chatgpt, updatedAt: new Date().toISOString() };
  fm.writeString(cache, JSON.stringify(data));
  return data;
}

const widget = new ListWidget();
widget.backgroundColor = COLORS.bg;
widget.setPadding(12, 14, 12, 14);

try {
  const data = await load();
  if (config.widgetFamily === "medium") {
    const columns = widget.addStack();
    columns.layoutHorizontally();
    const claude = columns.addStack();
    claude.layoutVertically();
    claudeSection(claude, data.claude || {}, 60, true);
    columns.addSpacer(16);
    const chatgpt = columns.addStack();
    chatgpt.layoutVertically();
    chatgptSection(chatgpt, data.chatgpt || {}, 60, true);
  } else if (config.widgetFamily === "small") {
    claudeSection(widget, data.claude || {}, 70, true);
    widget.addSpacer(8);
    chatgptSection(widget, data.chatgpt || {}, 70, true);
  } else {
    const title = widget.addText("AI Usage");
    title.font = Font.boldSystemFont(17);
    title.textColor = Color.white();
    widget.addSpacer(10);
    claudeSection(widget, data.claude || {}, 130);
    widget.addSpacer(14);
    chatgptSection(widget, data.chatgpt || {}, 130);
  }
} catch (error) {
  const title = widget.addText("AI Usage unavailable");
  title.font = Font.boldSystemFont(14);
  title.textColor = Color.white();
  const detail = widget.addText(String(error).includes("401") ? "Check API key" : "Check server connection");
  detail.textColor = COLORS.muted;
}

widget.refreshAfterDate = new Date(Date.now() + CONFIG.refreshMinutes * 60 * 1000);
Script.setWidget(widget);
Script.complete();
