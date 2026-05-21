#!/usr/bin/env python3
"""My-Claude: render an interactive HTML view of the user's Claude installation."""
import json, os, html, re
from pathlib import Path
from datetime import datetime

HOME = Path.home()
CLAUDE = HOME / ".claude"
OUT = HOME / "Documents" / "My_Claude.html"

CATEGORIES = {
    "skills":      {"label": "Skills",            "color": "#3b82f6", "desc": "Personal skills loaded into every session."},
    "connectors":  {"label": "MCP Connectors",    "color": "#8b5cf6", "desc": "External tools wired in via Model Context Protocol."},
    "plugins":     {"label": "Plugins",           "color": "#06b6d4", "desc": "Marketplaces and installed Claude Code plugins."},
    "sessions":    {"label": "Sessions",          "color": "#f59e0b", "desc": "Full conversation transcripts, stored in plaintext on disk."},
    "config":      {"label": "Config",            "color": "#10b981", "desc": "Settings, CLAUDE.md, slash commands, statusline."},
    "cache":       {"label": "History & Cache",   "color": "#64748b", "desc": "Shell snapshots, paste cache, image cache, history log."},
    "tasks":       {"label": "Tasks & Plans",     "color": "#ec4899", "desc": "Local task lists, plans, todos."},
}

def dir_size(p: Path) -> int:
    if not p.exists(): return 0
    if p.is_file(): return p.stat().st_size
    total = 0
    try:
        for root, _, files in os.walk(p, followlinks=False):
            for f in files:
                fp = os.path.join(root, f)
                try: total += os.lstat(fp).st_size
                except OSError: pass
    except OSError: pass
    return total

def fmt_size(n: int) -> str:
    for u in ["B","KB","MB","GB","TB"]:
        if n < 1024: return f"{n:.1f} {u}" if u != "B" else f"{n} B"
        n /= 1024
    return f"{n:.1f} PB"

def parse_skill_desc(skill_dir: Path) -> str:
    md = skill_dir / "SKILL.md"
    if not md.exists(): return ""
    try:
        text = md.read_text(errors="ignore")[:4000]
        m = re.search(r"^---\s*\n(.*?)\n---", text, re.S | re.M)
        if not m: return ""
        fm = m.group(1)
        d = re.search(r"^description:\s*(.+?)$", fm, re.M)
        if d: return d.group(1).strip().strip('"').strip("'")[:200]
    except Exception: pass
    return ""

def collect_skills():
    sk_dir = CLAUDE / "skills"
    out = []
    if not sk_dir.exists(): return out
    for p in sorted(sk_dir.iterdir()):
        if not p.is_dir(): continue
        out.append({
            "name": p.name,
            "path": str(p),
            "size": dir_size(p),
            "desc": parse_skill_desc(p),
        })
    return out

def collect_mcp():
    servers = {}
    for cfg in [CLAUDE / "settings.json", HOME / ".claude.json"]:
        if not cfg.exists(): continue
        try:
            data = json.loads(cfg.read_text())
            for k, v in (data.get("mcpServers") or {}).items():
                servers[k] = {"name": k, "config": v, "source": cfg.name}
        except Exception: pass
    return list(servers.values())

def collect_plugins():
    out = []
    pdir = CLAUDE / "plugins"
    if not pdir.exists(): return out
    inst = pdir / "installed_plugins.json"
    if inst.exists():
        try:
            data = json.loads(inst.read_text())
            plugins = data.get("plugins") or data
            if isinstance(plugins, dict):
                for k, v in plugins.items():
                    out.append({"name": k, "info": v})
            elif isinstance(plugins, list):
                for v in plugins:
                    out.append({"name": v.get("name", "?"), "info": v})
        except Exception: pass
    mk = pdir / "marketplaces"
    if mk.exists():
        for m in mk.iterdir():
            if m.is_dir():
                out.append({"name": f"marketplace/{m.name}", "info": {"path": str(m), "size": dir_size(m)}})
    return out

def collect_sessions():
    pdir = CLAUDE / "projects"
    out = []
    if not pdir.exists(): return out
    for p in sorted(pdir.iterdir()):
        if not p.is_dir(): continue
        # Decode project path from slug: -Users-chethanbhatbs-foo -> /Users/chethanbhatbs/foo
        slug = p.name
        decoded = slug.replace("-", "/") if slug.startswith("-") else slug
        files = list(p.glob("*.jsonl"))
        out.append({
            "name": slug,
            "decoded": decoded,
            "path": str(p),
            "size": dir_size(p),
            "transcripts": len(files),
        })
    return sorted(out, key=lambda x: -x["size"])

def collect_config():
    items = []
    for f in ["settings.json", "settings.local.json", "CLAUDE.md", ".last-cleanup", "policy-limits.json", "stats-cache.json", "mcp-needs-auth-cache.json"]:
        p = CLAUDE / f
        if p.exists(): items.append({"name": f, "path": str(p), "size": dir_size(p)})
    for d in ["commands"]:
        p = CLAUDE / d
        if p.exists():
            for c in p.iterdir():
                items.append({"name": f"{d}/{c.name}", "path": str(c), "size": dir_size(c)})
    return items

def collect_cache():
    items = []
    for d in ["shell-snapshots", "paste-cache", "file-history", "image-cache", "session-env", "telemetry", "ide", "cache", "downloads", "debug", "backups", "todos"]:
        p = CLAUDE / d
        if p.exists():
            items.append({"name": d, "path": str(p), "size": dir_size(p), "count": len(list(p.iterdir())) if p.is_dir() else 0})
    h = CLAUDE / "history.jsonl"
    if h.exists():
        items.append({"name": "history.jsonl", "path": str(h), "size": h.stat().st_size, "count": 0})
    return items

def collect_tasks():
    items = []
    for d in ["tasks", "plans"]:
        p = CLAUDE / d
        if p.exists():
            items.append({"name": d, "path": str(p), "size": dir_size(p), "count": len(list(p.iterdir()))})
    return items

def main():
    print("Collecting...")
    data = {
        "generated": datetime.now().isoformat(timespec="seconds"),
        "home": str(HOME),
        "claude_root": str(CLAUDE),
        "skills":     collect_skills(),
        "connectors": collect_mcp(),
        "plugins":    collect_plugins(),
        "sessions":   collect_sessions(),
        "config":     collect_config(),
        "cache":      collect_cache(),
        "tasks":      collect_tasks(),
    }
    totals = {k: {"count": len(data[k]), "size": sum(it.get("size",0) for it in data[k])} for k in CATEGORIES}
    grand_total = sum(t["size"] for t in totals.values())
    data["totals"] = totals
    data["grand_total"] = grand_total

    payload = json.dumps(data, default=str)
    cats_json = json.dumps(CATEGORIES)

    html_doc = TEMPLATE.replace("__DATA__", payload).replace("__CATS__", cats_json).replace("__GENERATED__", data["generated"]).replace("__TOTAL__", fmt_size(grand_total))
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(html_doc)
    print(f"WROTE: {OUT}")
    print(f"Skills: {totals['skills']['count']}  Sessions: {totals['sessions']['count']}  Connectors: {totals['connectors']['count']}  Plugins: {totals['plugins']['count']}")
    print(f"Total on disk: {fmt_size(grand_total)}")

TEMPLATE = r"""<!doctype html>
<html lang="en"><head>
<meta charset="utf-8"><title>My Claude</title>
<meta name="viewport" content="width=device-width,initial-scale=1">
<script src="https://d3js.org/d3.v7.min.js"></script>
<style>
:root{--bg:#0b1020;--panel:#121a33;--panel2:#1a2347;--ink:#e8ecff;--mut:#9aa3c9;--bd:#283057;--accent:#6ea8ff;}
[data-theme=light]{--bg:#f6f8fc;--panel:#fff;--panel2:#f1f4fb;--ink:#0f172a;--mut:#475569;--bd:#e2e8f0;--accent:#2563eb;}
*{box-sizing:border-box}
html,body{margin:0;height:100%}
body{font:14px/1.45 -apple-system,BlinkMacSystemFont,"SF Pro Text",system-ui,sans-serif;background:var(--bg);color:var(--ink)}
header{display:flex;align-items:center;justify-content:space-between;padding:18px 24px;border-bottom:1px solid var(--bd);background:var(--panel);position:sticky;top:0;z-index:5}
h1{margin:0;font-size:18px;font-weight:600;letter-spacing:.2px}
.sub{color:var(--mut);font-size:12px;margin-top:2px}
.toolbar{display:flex;gap:8px;align-items:center}
.btn{background:var(--panel2);color:var(--ink);border:1px solid var(--bd);padding:7px 12px;border-radius:8px;font-size:12px;cursor:pointer}
.btn:hover{border-color:var(--accent)}
.btn.active{background:var(--accent);color:#fff;border-color:var(--accent)}
.banner{margin:14px 24px;padding:12px 16px;background:linear-gradient(90deg,#fef3c7,#fde68a);color:#7c2d12;border-radius:10px;font-size:13px}
[data-theme=dark] .banner{background:#3b2710;color:#fbbf24;border:1px solid #78350f}
main{padding:18px 24px 60px}
.kpis{display:grid;grid-template-columns:repeat(auto-fit,minmax(200px,1fr));gap:12px;margin-bottom:18px}
.kpi{background:var(--panel);border:1px solid var(--bd);border-radius:12px;padding:14px;cursor:pointer;transition:transform .12s,border-color .12s}
.kpi:hover{transform:translateY(-2px);border-color:var(--accent)}
.kpi .swatch{width:10px;height:10px;border-radius:3px;display:inline-block;margin-right:8px;vertical-align:middle}
.kpi .label{color:var(--mut);font-size:11px;text-transform:uppercase;letter-spacing:.7px}
.kpi .num{font-size:24px;font-weight:600;margin:6px 0 2px}
.kpi .sz{color:var(--mut);font-size:12px}
.kpi .desc{color:var(--mut);font-size:12px;margin-top:6px;line-height:1.4}
.tabs{display:flex;gap:4px;margin:8px 0 14px;border-bottom:1px solid var(--bd)}
.tab{padding:8px 14px;cursor:pointer;border-bottom:2px solid transparent;color:var(--mut);font-size:13px}
.tab.active{color:var(--ink);border-color:var(--accent)}
.view{display:none}
.view.active{display:block}
#tree{background:var(--panel);border:1px solid var(--bd);border-radius:12px;padding:8px}
.row{display:flex;align-items:center;gap:8px;padding:6px 8px;border-radius:6px}
.row:hover{background:var(--panel2)}
.row .nm{flex:1;font-family:ui-monospace,SFMono-Regular,Menlo,monospace;font-size:13px}
.row .meta{color:var(--mut);font-size:11px;font-family:ui-monospace,monospace}
.row .open{color:var(--accent);text-decoration:none;font-size:11px}
.row .open:hover{text-decoration:underline}
.section{margin:18px 0}
.section h3{font-size:13px;text-transform:uppercase;letter-spacing:.7px;color:var(--mut);margin:14px 0 8px;font-weight:600}
.search{width:100%;padding:9px 12px;border-radius:8px;border:1px solid var(--bd);background:var(--panel2);color:var(--ink);font-size:13px;margin-bottom:12px}
#tm{width:100%;height:680px;background:var(--panel);border:1px solid var(--bd);border-radius:12px;overflow:hidden}
.tile{stroke:var(--bg);stroke-width:1.5;cursor:pointer}
.tile-label{fill:#fff;font-size:11px;font-family:-apple-system,system-ui,sans-serif;pointer-events:none;font-weight:500}
.tile-size{fill:rgba(255,255,255,.75);font-size:10px;pointer-events:none}
.crumbs{padding:10px 14px;color:var(--mut);font-size:12px;border-bottom:1px solid var(--bd);background:var(--panel)}
.crumbs a{color:var(--accent);cursor:pointer}
details{background:var(--panel);border:1px solid var(--bd);border-radius:10px;padding:8px 12px;margin:6px 0}
details summary{cursor:pointer;font-weight:500;padding:4px 0}
.pill{display:inline-block;font-size:10px;padding:2px 8px;border-radius:10px;background:var(--panel2);color:var(--mut);margin-left:6px}
.pill.warn{background:#7c2d12;color:#fbbf24}
[data-theme=light] .pill.warn{background:#fef3c7;color:#92400e}
.skill-card{padding:10px;border-bottom:1px solid var(--bd)}
.skill-card:last-child{border:0}
.skill-card .nm{font-weight:600;font-size:13px}
.skill-card .desc{color:var(--mut);font-size:12px;margin-top:3px;line-height:1.45}
.grid2{display:grid;grid-template-columns:1fr 1fr;gap:12px}
@media (max-width:780px){.grid2{grid-template-columns:1fr}}
</style></head><body data-theme="dark">
<header>
  <div><h1>My Claude</h1><div class="sub">Generated __GENERATED__ — total on disk: <b>__TOTAL__</b></div></div>
  <div class="toolbar">
    <input id="q" class="search" placeholder="Search…" style="width:220px;margin:0">
    <button class="btn" onclick="toggleTheme()">Theme</button>
  </div>
</header>

<div class="banner">⚠️ <b>Privacy:</b> Your <code>~/.claude/projects/</code> sessions store full conversation transcripts in plaintext. Anyone with access to your laptop can read them. Don't share screenshots of this view without redacting.</div>

<main>
  <div id="kpis" class="kpis"></div>

  <div class="tabs">
    <div class="tab active" data-view="dash">Dashboard</div>
    <div class="tab" data-view="tm">Treemap</div>
    <div class="tab" data-view="tree">Tree</div>
  </div>

  <div id="dash" class="view active"></div>
  <div id="tm" class="view"></div>
  <div id="tree-view" class="view"><div id="tree"></div></div>
</main>

<script>
const DATA = __DATA__;
const CATS = __CATS__;
const fmtSize = n => { if(!n) return "0 B"; const u=["B","KB","MB","GB","TB"]; let i=0; while(n>=1024 && i<u.length-1){n/=1024;i++} return n.toFixed(1)+" "+u[i]; };
const fileURL = p => "file://" + p.split("/").map(encodeURIComponent).join("/");

function toggleTheme(){const b=document.body;b.dataset.theme = b.dataset.theme==="dark"?"light":"dark"; renderTreemap();}

// KPI cards
const kpis = document.getElementById("kpis");
Object.entries(CATS).forEach(([k, c]) => {
  const t = DATA.totals[k];
  const div = document.createElement("div");
  div.className = "kpi";
  div.innerHTML = `<div class="label"><span class="swatch" style="background:${c.color}"></span>${c.label}</div>
    <div class="num">${t.count}</div><div class="sz">${fmtSize(t.size)}</div>
    <div class="desc">${c.desc}</div>`;
  div.onclick = () => { selectTab("dash"); document.getElementById("sec-"+k).scrollIntoView({behavior:"smooth", block:"start"}); };
  kpis.appendChild(div);
});

// Tabs
function selectTab(v){
  document.querySelectorAll(".tab").forEach(t=>t.classList.toggle("active", t.dataset.view===v));
  document.querySelectorAll(".view").forEach(x=>x.classList.remove("active"));
  if(v==="dash") document.getElementById("dash").classList.add("active");
  if(v==="tm"){ document.getElementById("tm").classList.add("active"); renderTreemap(); }
  if(v==="tree") document.getElementById("tree-view").classList.add("active");
}
document.querySelectorAll(".tab").forEach(t=>t.onclick=()=>selectTab(t.dataset.view));

// Dashboard sections
const dash = document.getElementById("dash");
function section(id, title, count, color, body){
  const el = document.createElement("div");
  el.className = "section"; el.id = "sec-"+id;
  el.innerHTML = `<h3 style="color:${color}">${title} <span class="pill">${count}</span></h3>` + body;
  dash.appendChild(el);
}

// Skills
{
  const items = DATA.skills.map(s => `<details class="skill-card"><summary><span class="nm">${s.name}</span><span class="pill">${fmtSize(s.size)}</span></summary>
    <div class="desc">${s.desc ? s.desc.replace(/</g,'&lt;') : '<i>(no description)</i>'}</div>
    <div style="margin-top:6px"><a class="open" href="${fileURL(s.path)}">Open in Finder →</a></div></details>`).join("");
  section("skills","Skills",DATA.skills.length,CATS.skills.color,
    `<div style="background:var(--panel);border:1px solid var(--bd);border-radius:12px;padding:8px;max-height:480px;overflow:auto">${items}</div>`);
}

// MCP Connectors
{
  const items = DATA.connectors.length ? DATA.connectors.map(c => `<details><summary><b>${c.name}</b> <span class="pill">${c.source||""}</span></summary>
    <pre style="font-size:11px;color:var(--mut);white-space:pre-wrap;margin:6px 0 0">${JSON.stringify(c.config,null,2).replace(/</g,'&lt;')}</pre></details>`).join("")
    : `<div style="color:var(--mut);padding:12px">No MCP connectors configured. Add via <code>claude mcp add</code>.</div>`;
  section("connectors","MCP Connectors",DATA.connectors.length,CATS.connectors.color, items);
}

// Plugins
{
  const items = DATA.plugins.length ? DATA.plugins.map(p => `<details><summary>${p.name}</summary>
    <pre style="font-size:11px;color:var(--mut);white-space:pre-wrap;margin:6px 0 0">${JSON.stringify(p.info,null,2).replace(/</g,'&lt;')}</pre></details>`).join("")
    : `<div style="color:var(--mut);padding:12px">No plugins installed.</div>`;
  section("plugins","Plugins",DATA.plugins.length,CATS.plugins.color, items);
}

// Sessions
{
  const items = DATA.sessions.map(s => `<div class="row">
    <div class="nm">${s.decoded}<span class="pill warn">sensitive</span></div>
    <div class="meta">${s.transcripts} transcripts · ${fmtSize(s.size)}</div>
    <a class="open" href="${fileURL(s.path)}">Open</a></div>`).join("");
  section("sessions","Sessions (per-project transcripts)",DATA.sessions.length,CATS.sessions.color,
    `<div style="background:var(--panel);border:1px solid var(--bd);border-radius:12px;padding:6px">${items}</div>`);
}

// Config
{
  const items = DATA.config.map(c => `<div class="row"><div class="nm">${c.name}</div><div class="meta">${fmtSize(c.size)}</div><a class="open" href="${fileURL(c.path)}">Open</a></div>`).join("");
  section("config","Config",DATA.config.length,CATS.config.color,
    `<div style="background:var(--panel);border:1px solid var(--bd);border-radius:12px;padding:6px">${items}</div>`);
}

// Cache
{
  const items = DATA.cache.map(c => `<div class="row"><div class="nm">${c.name}</div><div class="meta">${c.count?c.count+' items · ':''}${fmtSize(c.size)}</div><a class="open" href="${fileURL(c.path)}">Open</a></div>`).join("");
  section("cache","History & Cache",DATA.cache.length,CATS.cache.color,
    `<div style="background:var(--panel);border:1px solid var(--bd);border-radius:12px;padding:6px">${items}</div>`);
}

// Tasks
{
  const items = DATA.tasks.map(c => `<div class="row"><div class="nm">${c.name}</div><div class="meta">${c.count} items · ${fmtSize(c.size)}</div><a class="open" href="${fileURL(c.path)}">Open</a></div>`).join("");
  section("tasks","Tasks & Plans",DATA.tasks.length,CATS.tasks.color,
    `<div style="background:var(--panel);border:1px solid var(--bd);border-radius:12px;padding:6px">${items}</div>`);
}

// ============ TREEMAP ============
function buildTreeData(){
  const root = {name:"My Claude", children:[]};
  Object.entries(CATS).forEach(([k,c])=>{
    const node = {name:c.label, color:c.color, children:[]};
    const items = DATA[k] || [];
    items.forEach(it => {
      node.children.push({
        name: it.name || it.decoded || "?",
        size: it.size || 100,
        path: it.path,
        desc: it.desc || "",
        color: c.color,
      });
    });
    if(!node.children.length) node.children.push({name:"(empty)", size:1, color:c.color});
    root.children.push(node);
  });
  return root;
}

let tmRendered = false;
function renderTreemap(){
  const wrap = document.getElementById("tm");
  wrap.innerHTML = "";
  const W = wrap.clientWidth, H = 680;
  const data = buildTreeData();
  const root = d3.hierarchy(data).sum(d => d.size || 0).sort((a,b)=>b.value-a.value);
  d3.treemap().size([W, H]).paddingTop(22).paddingInner(2).round(true)(root);

  const svg = d3.select(wrap).append("svg").attr("width", W).attr("height", H);

  // Group headers (top-level cats)
  const groups = svg.selectAll("g.grp").data(root.children).enter().append("g").attr("class","grp");
  groups.append("rect")
    .attr("x",d=>d.x0).attr("y",d=>d.y0).attr("width",d=>d.x1-d.x0).attr("height",d=>d.y1-d.y0)
    .attr("fill",d=>d.data.color).attr("opacity",.18).attr("stroke",d=>d.data.color).attr("stroke-width",1);
  groups.append("text").attr("x",d=>d.x0+8).attr("y",d=>d.y0+15)
    .attr("font-size",12).attr("font-weight",600).attr("fill",d=>d.data.color)
    .text(d=>`${d.data.name} · ${fmtSize(d.value)}`);

  // Leaf tiles
  const leaves = root.leaves();
  const cell = svg.selectAll("g.cell").data(leaves).enter().append("g").attr("class","cell");
  cell.append("rect").attr("class","tile")
    .attr("x",d=>d.x0).attr("y",d=>d.y0).attr("width",d=>Math.max(0,d.x1-d.x0)).attr("height",d=>Math.max(0,d.y1-d.y0))
    .attr("fill",d=>d.data.color).attr("opacity",.85)
    .on("click", (e,d)=>{ if(d.data.path) window.location.href = fileURL(d.data.path); })
    .append("title").text(d=>`${d.data.name}\n${fmtSize(d.value)}\n${d.data.path||""}\n${d.data.desc||""}`);
  cell.append("text").attr("class","tile-label")
    .attr("x",d=>d.x0+5).attr("y",d=>d.y0+13)
    .text(d => { const w=d.x1-d.x0, h=d.y1-d.y0; if(w<40||h<18) return ""; const max=Math.floor(w/6.2); return d.data.name.length>max?d.data.name.slice(0,max-1)+"…":d.data.name; });
  cell.append("text").attr("class","tile-size")
    .attr("x",d=>d.x0+5).attr("y",d=>d.y0+25)
    .text(d => { const w=d.x1-d.x0, h=d.y1-d.y0; if(w<60||h<32) return ""; return fmtSize(d.value); });
}

// ============ TREE ============
function renderTree(){
  const t = document.getElementById("tree");
  let h = "";
  Object.entries(CATS).forEach(([k,c])=>{
    const items = DATA[k] || [];
    h += `<details open><summary style="color:${c.color};font-weight:600">${c.label} (${items.length}, ${fmtSize(DATA.totals[k].size)})</summary>`;
    items.slice(0,500).forEach(it => {
      const name = it.name || it.decoded || "?";
      const sz = it.size ? fmtSize(it.size) : "";
      const p = it.path || "";
      h += `<div class="row"><div class="nm">${name}</div><div class="meta">${sz}</div>${p?`<a class="open" href="${fileURL(p)}">Open</a>`:""}</div>`;
    });
    if(items.length>500) h += `<div class="row"><div class="meta">… ${items.length-500} more</div></div>`;
    h += "</details>";
  });
  t.innerHTML = h;
}
renderTree();

// Search
document.getElementById("q").addEventListener("input", e => {
  const q = e.target.value.toLowerCase();
  document.querySelectorAll("#tree .row, #dash .row, #dash .skill-card, #dash details:not(.skill-card)").forEach(r => {
    const txt = r.textContent.toLowerCase();
    r.style.display = (!q || txt.includes(q)) ? "" : "none";
  });
});

window.addEventListener("resize", () => { if(document.getElementById("tm").classList.contains("active")) renderTreemap(); });
</script>
</body></html>
"""

if __name__ == "__main__":
    main()
