// ChatGPT Plus-only Scriptable widget. Replace placeholders only in your private copy.
const CONFIG = { baseUrl: "https://YOUR-PRIVATE-HOST", apiKey: "PASTE-YOUR-API-KEY", refreshMinutes: 30 };
const COLORS = { bg: new Color("#1a1a1a"), muted: new Color("#999999"), brand: new Color("#10A37F") };

function color(p) { return new Color(p < 50 ? "#34c759" : p < 75 ? "#ffcc00" : p < 90 ? "#ff9500" : "#ff3b30"); }
function formatTime(v) { if (!v) return "—"; const d=new Date(v); if(isNaN(d.getTime())) return "—"; return `${String(d.getDate()).padStart(2,"0")} ${["Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"][d.getMonth()]} ${String(d.getHours()).padStart(2,"0")}:${String(d.getMinutes()).padStart(2,"0")}`; }
function sessionReset(v) { const d=v?new Date(v):null; return !d||isNaN(d.getTime())||d.getTime()<=Date.now()?"Not started yet":formatTime(v); }
function duration(x) { return x.window_duration_minutes??(typeof x.window_hours==="number"?x.window_hours*60:String(x.label).toLowerCase().includes("week")?10080:300); }
function findWindow(windows,minutes,keyword) { return windows.find(x=>duration(x)===minutes||String(x.label).toLowerCase().includes(keyword))||{}; }
function dot() { const c=new DrawContext();c.size=new Size(12,12);c.opaque=false;c.setFillColor(COLORS.brand);const p=new Path();p.addEllipse(new Rect(0,0,12,12));c.addPath(p);c.fillPath();return c.getImage(); }
function bar(p,w) { const value=Math.max(0,Math.min(100,p??0));const c=new DrawContext();c.size=new Size(w,8);c.opaque=false;c.setFillColor(new Color("#353535"));c.fillRoundedRect(new Rect(0,0,w,8),4,4);c.setFillColor(color(value));c.fillRoundedRect(new Rect(0,0,Math.max(8,w*value/100),8),4,4);return c.getImage(); }
function row(parent,label,pct,width) { const s=parent.addStack();s.layoutHorizontally();s.centerAlignContent();const l=s.addText(label);l.font=Font.boldSystemFont(12);l.textColor=COLORS.muted;s.addSpacer(6);if(typeof pct!=="number"){const n=s.addText("—");n.textColor=COLORS.muted;return;}const i=s.addImage(bar(pct,width));i.imageSize=new Size(width,8);s.addSpacer(6);const t=s.addText(`${Math.round(pct)}%`);t.font=Font.boldSystemFont(12);t.textColor=color(pct); }
function detail(parent,text) { const t=parent.addText(text);t.font=Font.systemFont(10);t.textColor=COLORS.muted;t.lineLimit=1; }
async function load() { const fm=FileManager.local(),path=fm.joinPath(fm.documentsDirectory(),"chatgpt_usage_widget_cache.json");try{const r=new Request(CONFIG.baseUrl+"/api/chatgpt-usage");r.headers={"X-API-Key":CONFIG.apiKey};const d=await r.loadJSON();fm.writeString(path,JSON.stringify(d));return d;}catch(e){if(fm.fileExists(path))return JSON.parse(fm.readString(path));throw e;} }

const widget=new ListWidget();widget.backgroundColor=COLORS.bg;widget.setPadding(12,14,12,14);
try {
  const data=await load(),windows=data.windows||[],session=findWindow(windows,300,"5 hour"),weekly=findWindow(windows,10080,"week"),projection=(data.projections||[]).find(x=>String(x.label).toLowerCase().includes("week"))||{};
  const h=widget.addStack();h.layoutHorizontally();h.centerAlignContent();const i=h.addImage(dot());i.imageSize=new Size(12,12);h.addSpacer(6);const title=h.addText("ChatGPT Plus");title.font=Font.boldSystemFont(15);title.textColor=Color.white();
  widget.addSpacer(8);row(widget,"5 hour",session.used_percent,150);widget.addSpacer(2);detail(widget,`5h reset: ${sessionReset(session.reset_at)}`);
  widget.addSpacer(6);row(widget,"Weekly",weekly.used_percent,150);widget.addSpacer(6);
  const projected=projection.projected_pct_at_reset;detail(widget,`Reset ${formatTime(weekly.reset_at||projection.reset_at)}${typeof projected==="number"?` · ~${projected}% weekly`:""}`);
  if(typeof projection.safe_until_reset==="boolean"){widget.addSpacer(2);const s=widget.addText(projection.safe_until_reset?"✅ Aman sampai reset":"⚠️ Tidak aman sebelum reset");s.font=Font.boldSystemFont(11);s.textColor=projection.safe_until_reset?new Color("#34c759"):new Color("#ff9500");}
} catch(e) { const t=widget.addText("ChatGPT Usage unavailable");t.textColor=Color.white(); }
widget.refreshAfterDate=new Date(Date.now()+CONFIG.refreshMinutes*60000);Script.setWidget(widget);Script.complete();
