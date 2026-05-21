"""My-Claude — interactive dashboard of your Claude installation."""
import io, json, os, re, shutil, subprocess, tempfile, zipfile
from pathlib import Path
from datetime import datetime

import pandas as pd
import plotly.express as px
import streamlit as st
import streamlit.components.v1 as components
from pyvis.network import Network

HOME = Path.home()
CLAUDE = HOME / ".claude"
SKILL_DIR = Path(__file__).resolve().parent
CONFIG_PATH = SKILL_DIR / "config.json"

st.set_page_config(page_title="My Claude", layout="wide", initial_sidebar_state="expanded")

CAT_COLOR = {
    "Skills":"#2563eb","Sessions":"#d97706","Connectors":"#7c3aed",
    "Plugins":"#0891b2","Config":"#059669","Cache":"#475569","Tasks":"#db2777",
}

if "theme_mode" not in st.session_state:
    st.session_state["theme_mode"] = "light"

def inject_theme_css(mode):
    """Claude Desktop–style dark mode: warm near-black bg, sand-orange accent."""
    if mode == "dark":
        st.markdown("""
<style>
:root, .stApp, [data-testid="stAppViewContainer"], [data-testid="stHeader"], [data-testid="stMain"] { background: #1a1a1a !important; color: #ececec !important; }
section[data-testid="stSidebar"] { background: #141414 !important; border-right: 1px solid #2a2a2a !important; }
section[data-testid="stSidebar"] *, .stApp * { color: #ececec !important; }
[data-testid="stTextInput"] input, [data-testid="stNumberInput"] input, [data-testid="stSelectbox"] div[role="combobox"], textarea, select {
  background: #262626 !important; color: #ececec !important; border: 1px solid #3a3a3a !important;
}
[data-testid="stTextInput"] input::placeholder { color: #6b6b6b !important; }
[data-testid="stMarkdownContainer"] code, code, pre { background: #262626 !important; color: #f0d8b8 !important; }
[data-testid="stMetric"], div[data-testid="stExpander"] {
  background: #1f1f1f !important; border: 1px solid #2a2a2a !important;
}
[data-testid="stContainer"] > div, div[data-testid="stVerticalBlockBorderWrapper"] { border-color: #2a2a2a !important; }
.stButton > button { background: #262626 !important; color: #ececec !important; border: 1px solid #3a3a3a !important; }
.stButton > button:hover { background: #303030 !important; border-color: #c89968 !important; color: #ececec !important; }
.stButton > button[kind="primary"] { background: #c89968 !important; border-color: #c89968 !important; color: #1a1a1a !important; }
.stButton > button[kind="primary"]:hover { background: #d4a578 !important; color: #1a1a1a !important; }
.gh-chip { background:#1f2a20 !important; border-color:#2d4a30 !important; color:#a7d7a8 !important; }
.gh-chip.warn { background:#2a1818 !important; border-color:#4a2828 !important; color:#f4a8a8 !important; }
hr, [data-testid="stDivider"] > div { border-color: #2a2a2a !important; background: #2a2a2a !important; }
.tag { background: #2a3340 !important; color: #88aacc !important; }
.tag.plugin { background: #2a3a40 !important; color: #88c8d4 !important; }
.tag.recent { background: #3a3020 !important; color: #e0c088 !important; }
.tag.pushed { background: #1f3025 !important; color: #88c8a0 !important; }
.tag.user { background: #3a2840 !important; color: #c898d4 !important; }
.btn-view button { background: #2a3340 !important; border-color: #3a4555 !important; color: #b8d0e8 !important; }
.btn-push button { background: #1f3025 !important; border-color: #2d4a36 !important; color: #98d4ac !important; }
.btn-share button { background: #3a2840 !important; border-color: #50385a !important; color: #d8b0e0 !important; }
/* Dialog (modal) — Streamlit portals it outside .stApp; target by aria-modal */
[role="dialog"], [aria-modal="true"], div[data-testid="stDialog"] { background: #1a1a1a !important; color: #ececec !important; }
[role="dialog"] *, [aria-modal="true"] *, div[data-testid="stDialog"] * { color: #ececec !important; }
[role="dialog"] [data-testid="stMarkdownContainer"] code, [aria-modal="true"] code { background: #262626 !important; color: #f0d8b8 !important; }
[role="dialog"] .stAlert, [aria-modal="true"] .stAlert { background: #1f2a3a !important; color: #b8d0e8 !important; border-color: #2d4555 !important; }
/* Dataframes */
[data-testid="stDataFrame"], [data-testid="stDataFrame"] * { background: #1f1f1f !important; color: #ececec !important; }
[data-testid="stDataFrame"] [role="columnheader"] { background: #262626 !important; color: #b8b8b8 !important; }
[data-testid="stDataFrame"] [role="row"]:hover { background: #2a2a2a !important; }
/* Toggles / radios */
[data-baseweb="checkbox"] div, [data-baseweb="radio"] div { color: #ececec !important; }
/* Toolbar pencil-ish artifacts on dataframes */
[data-testid="stElementToolbar"] { background: #262626 !important; }
.stRadio [role="radio"] { background: transparent !important; }
/* Page-header theme button */
.theme-btn button { background: #262626 !important; border: 1px solid #3a3a3a !important; color: #ececec !important; min-height: 34px !important; padding: 4px 14px !important; }
</style>""", unsafe_allow_html=True)
    else:
        st.markdown("""
<style>
.btn-view button { background: #f0f7ff !important; border-color: #c5d8ed !important; color: #1d4ed8 !important; }
.btn-push button { background: #f0fdf4 !important; border-color: #bbf2ce !important; color: #15803d !important; }
.btn-share button { background: #faf5ff !important; border-color: #d8c5e8 !important; color: #6d28d9 !important; }
.btn-view button:hover { background: #e0eeff !important; }
.btn-push button:hover { background: #dcfce7 !important; }
.btn-share button:hover { background: #f3e8ff !important; }
.theme-btn button { background: #ffffff !important; border: 1px solid #e2e8f0 !important; color: #0f172a !important; min-height: 34px !important; padding: 4px 14px !important; }
.theme-btn button:hover { background: #f1f5f9 !important; }
</style>""", unsafe_allow_html=True)

# Inject base CSS for layout polish
st.markdown("""
<style>
section[data-testid="stSidebar"] { padding-top: 0.5rem; }
section[data-testid="stSidebar"] .stRadio > label { display: none; }
section[data-testid="stSidebar"] .stRadio [role="radiogroup"] { gap: 2px; }
section[data-testid="stSidebar"] .stRadio label { padding: 4px 0; font-size: 13px; }
.brand-title { font-size: 16px; font-weight: 700; padding: 2px 4px 0; letter-spacing: -0.2px; }
.brand-sub   { font-size: 11px; color: #64748b; padding: 0 4px 8px; font-family: ui-monospace, Menlo, monospace; word-break: break-all; }
.gh-chip     { display: flex; align-items: center; gap: 6px; padding: 6px 10px;
               background: #ecfdf5; border: 1px solid #a7f3d0; border-radius: 8px;
               font-size: 12px; color: #065f46; margin: 0 0 8px; }
.gh-chip.warn{ background: #fef2f2; border-color: #fecaca; color: #991b1b; }
.gh-chip .dot{ width: 6px; height: 6px; border-radius: 50%; background: #10b981; flex: none; }
.gh-chip.warn .dot{ background: #ef4444; }
.foot-cap    { font-size: 11px; color: #94a3b8; padding: 4px 0; }
.search-input input { padding: 10px 14px !important; font-size: 14px !important; border-radius: 8px !important; }
[data-testid="stTextInput"] label { font-size: 12px; font-weight: 600; color: #475569; text-transform: uppercase; letter-spacing: 0.5px; }
.tag { display: inline-block; font-size: 10px; padding: 2px 8px; border-radius: 999px; margin-left: 6px;
       background: #eff6ff; color: #1d4ed8; font-weight: 600; letter-spacing: 0.3px; vertical-align: middle; }
.tag.user   { background: #f5f3ff; color: #6d28d9; }
.tag.plugin { background: #ecfeff; color: #0e7490; }
.tag.recent { background: #fef3c7; color: #92400e; }
.tag.pushed { background: #dcfce7; color: #166534; }
</style>
""", unsafe_allow_html=True)

inject_theme_css(st.session_state["theme_mode"])

# ---------- helpers ----------
def fmt_size(n):
    if not n: return "0 B"
    n = float(n)
    for u in ["B","KB","MB","GB","TB"]:
        if n < 1024: return f"{n:.1f} {u}" if u != "B" else f"{int(n)} B"
        n /= 1024
    return f"{n:.1f} PB"

def fmt_num(n):
    n = float(n or 0)
    sign = "-" if n < 0 else ""
    n = abs(n)
    if n >= 1e12: return f"{sign}{n/1e12:.2f}T"
    if n >= 1e9:  return f"{sign}{n/1e9:.2f}B"
    if n >= 1e6:  return f"{sign}{n/1e6:.2f}M"
    if n >= 1e3:  return f"{sign}{n/1e3:.1f}K"
    return f"{sign}{int(n)}"

def fmt_when(ts):
    try: return datetime.fromtimestamp(ts).strftime("%Y-%m-%d %H:%M")
    except Exception: return ""

@st.cache_data(ttl=120)
def dir_size(p_str):
    p = Path(p_str)
    if not p.exists(): return 0
    if p.is_file(): return p.stat().st_size
    total = 0
    try:
        for root, _, files in os.walk(p, followlinks=False):
            for f in files:
                try: total += os.lstat(os.path.join(root, f)).st_size
                except OSError: pass
    except OSError: pass
    return total

@st.cache_data(ttl=120)
def latest_mtime(p_str):
    p = Path(p_str)
    if not p.exists(): return 0
    if p.is_file(): return p.stat().st_mtime
    latest = 0
    try:
        for root, _, files in os.walk(p, followlinks=False):
            for f in files:
                try:
                    m = os.lstat(os.path.join(root, f)).st_mtime
                    if m > latest: latest = m
                except OSError: pass
    except OSError: pass
    return latest

def open_in_finder(path):
    try: subprocess.run(["open", path], check=False)
    except Exception: pass

def open_in_terminal(path):
    try:
        target = path if os.path.isdir(path) else os.path.dirname(path)
        subprocess.run(["open", "-a", "Terminal", target], check=False)
    except Exception: pass

def terminal_run(cmd, cwd=None):
    """Open a new Terminal window and run a shell command."""
    full = f'cd {json.dumps(cwd or os.getcwd())} && {cmd}'
    script = f'tell application "Terminal" to do script {json.dumps(full)}\ntell application "Terminal" to activate'
    try:
        subprocess.run(["osascript", "-e", script], check=False)
        return True
    except Exception:
        return False

def start_claude_in_project(project_path, resume_id=None):
    cmd = "claude" + (f" --resume {resume_id}" if resume_id else "")
    return terminal_run(cmd, cwd=project_path)

def open_file_default(path):
    try:
        if shutil.which("code"): subprocess.run(["code", path], check=False)
        else: subprocess.run(["open", "-e", path], check=False)
        return True
    except Exception:
        return False

def pbcopy(text):
    try:
        p = subprocess.Popen(["pbcopy"], stdin=subprocess.PIPE)
        p.communicate(text.encode())
        return True
    except Exception:
        return False

def redact_secrets(obj):
    SECRETY = re.compile(r"(token|key|secret|password|pass|auth|bearer|cred)", re.I)
    if isinstance(obj, dict):
        return {k: ("<redacted>" if SECRETY.search(k) and isinstance(v, str) else redact_secrets(v)) for k, v in obj.items()}
    if isinstance(obj, list):
        return [redact_secrets(x) for x in obj]
    return obj

def parse_skill_meta(skill_dir):
    md = skill_dir / "SKILL.md"
    if not md.exists(): return {"description":"", "body":"", "raw":""}
    try:
        text = md.read_text(errors="ignore")
        m = re.search(r"^---\s*\n(.*?)\n---\s*\n?(.*)", text, re.S | re.M)
        if not m: return {"description":"", "body":text, "raw":text}
        fm, body = m.group(1), m.group(2)
        d = re.search(r"^description:\s*(.+?)$", fm, re.M)
        return {
            "description": (d.group(1).strip().strip('"').strip("'") if d else "")[:500],
            "body": body, "raw": text,
        }
    except Exception:
        return {"description":"", "body":"", "raw":""}

@st.cache_data(ttl=300)
def parse_transcript_usage(jsonl_path):
    """Extract per-turn usage records from a JSONL transcript.
    Returns list of dicts: {ts, model, input_tokens, output_tokens, cache_creation, cache_read}.
    """
    records = []
    try:
        with open(jsonl_path, "r", errors="ignore") as f:
            for line in f:
                line = line.strip()
                if not line: continue
                try: obj = json.loads(line)
                except Exception: continue
                msg = obj.get("message") or {}
                usage = msg.get("usage") if isinstance(msg, dict) else None
                if not usage: continue
                model = msg.get("model") or obj.get("model") or ""
                ts = obj.get("timestamp") or obj.get("ts") or ""
                records.append({
                    "ts": ts, "model": model,
                    "input_tokens": int(usage.get("input_tokens") or 0),
                    "output_tokens": int(usage.get("output_tokens") or 0),
                    "cache_creation": int(usage.get("cache_creation_input_tokens") or 0),
                    "cache_read": int(usage.get("cache_read_input_tokens") or 0),
                })
    except Exception: pass
    return records

@st.cache_data(ttl=300)
def aggregate_usage():
    """Walk all project transcripts, return DataFrame of per-turn usage with project/session metadata."""
    rows = []
    pdir = CLAUDE / "projects"
    if not pdir.exists(): return pd.DataFrame()
    for proj in pdir.iterdir():
        if not proj.is_dir(): continue
        decoded = proj.name.replace("-", "/") if proj.name.startswith("-") else proj.name
        for jf in proj.glob("*.jsonl"):
            sid = jf.name.split(".")[0]
            for r in parse_transcript_usage(str(jf)):
                r2 = dict(r); r2["project"] = decoded; r2["session"] = sid
                r2["family"] = model_family(r["model"])
                r2["cost"] = cost_for(r["model"], r["input_tokens"], r["output_tokens"], r["cache_creation"], r["cache_read"])
                # ts → date
                try: r2["date"] = pd.to_datetime(r["ts"]).date()
                except Exception: r2["date"] = None
                rows.append(r2)
    if not rows: return pd.DataFrame()
    return pd.DataFrame(rows)

@st.cache_data(ttl=600)
def transcript_label(jsonl_path):
    try:
        with open(jsonl_path, "r", errors="ignore") as f:
            for line in f:
                if not line.strip(): continue
                try: obj = json.loads(line)
                except Exception: continue
                msg = obj.get("message") or obj
                role = obj.get("type") or msg.get("role") or ""
                if role not in ("user","human"): continue
                content = msg.get("content") if isinstance(msg, dict) else None
                text = ""
                if isinstance(content, str): text = content
                elif isinstance(content, list):
                    for c in content:
                        if isinstance(c, dict) and c.get("type") == "text":
                            text = c.get("text",""); break
                text = re.sub(r"\s+", " ", text).strip()
                if text and not text.startswith("<"):
                    return text[:80] + ("…" if len(text) > 80 else "")
    except Exception: pass
    return ""

# ---------- config ----------
DEFAULT_CONFIG = {"github_owner":"", "default_visibility":"private", "repo_prefix":"claude-skill-",
                  "commit_message_template":"Update {skill} skill", "pushed_skills": {}}

# Anthropic public pricing per 1M tokens (USD). Adjust if rates change.
PRICING = {
    "opus":   {"input": 15.00, "output": 75.00, "cache_write": 18.75, "cache_read": 1.50},
    "sonnet": {"input":  3.00, "output": 15.00, "cache_write":  3.75, "cache_read": 0.30},
    "haiku":  {"input":  1.00, "output":  5.00, "cache_write":  1.25, "cache_read": 0.10},
}
def model_family(model_name):
    n = (model_name or "").lower()
    if "opus" in n: return "opus"
    if "haiku" in n: return "haiku"
    return "sonnet"
def cost_for(model_name, in_tok, out_tok, cw_tok, cr_tok):
    p = PRICING[model_family(model_name)]
    return (in_tok*p["input"] + out_tok*p["output"] + cw_tok*p["cache_write"] + cr_tok*p["cache_read"]) / 1_000_000
def load_config_dict():
    if CONFIG_PATH.exists():
        try: return {**DEFAULT_CONFIG, **json.loads(CONFIG_PATH.read_text())}
        except Exception: pass
    return dict(DEFAULT_CONFIG)
def save_config(cfg): CONFIG_PATH.write_text(json.dumps(cfg, indent=2))

# ---------- gh ----------
def run_cmd(cmd, cwd=None):
    p = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True)
    return p.returncode, p.stdout.strip(), p.stderr.strip()

@st.cache_data(ttl=60)
def gh_auth_status():
    if not shutil.which("gh"):
        return {"logged_in": False, "user": "", "raw": "", "gh_present": False, "host": ""}
    rc, out, err = run_cmd(["gh", "auth", "status"])
    text = (out + "\n" + err).strip()
    logged_in = rc == 0 and "Logged in to" in text
    user = ""; host = ""
    m = re.search(r"account ([A-Za-z0-9_-]+)", text) or re.search(r"as ([A-Za-z0-9_-]+)", text)
    if m: user = m.group(1)
    h = re.search(r"Logged in to ([A-Za-z0-9.\-]+)", text)
    if h: host = h.group(1)
    return {"logged_in": logged_in, "user": user, "raw": text, "gh_present": True, "host": host}

def gh_repo_exists(owner, repo):
    rc, _, _ = run_cmd(["gh", "repo", "view", f"{owner}/{repo}"])
    return rc == 0

def push_skill_to_github(skill_path, owner, repo, visibility):
    log = []
    skill_path = Path(skill_path)
    if not skill_path.exists():
        return False, "", f"Skill path not found: {skill_path}"
    with tempfile.TemporaryDirectory() as td:
        stage = Path(td) / repo
        stage.mkdir()
        ignore = shutil.ignore_patterns(".venv", "__pycache__", ".DS_Store", "*.pyc", ".git")
        for entry in skill_path.iterdir():
            dst = stage / entry.name
            try:
                if entry.is_dir(): shutil.copytree(entry, dst, ignore=ignore, dirs_exist_ok=True)
                else: shutil.copy2(entry, dst)
            except Exception as e: log.append(f"skip {entry.name}: {e}")
        readme = stage / "README.md"
        if not readme.exists():
            meta = parse_skill_meta(skill_path)
            readme.write_text(f"# {skill_path.name}\n\n{meta['description']}\n\n---\n\n{meta['body']}")
        for cmd in [["git","init","-b","main"], ["git","add","-A"], ["git","commit","-m", f"Initial commit of {skill_path.name} skill"]]:
            rc, out, err = run_cmd(cmd, cwd=str(stage))
            log.append(f"$ {' '.join(cmd)}\n{out}\n{err}")
            if rc != 0 and "nothing to commit" not in (out+err):
                return False, "", "\n".join(log)
        full = f"{owner}/{repo}"
        if gh_repo_exists(owner, repo):
            log.append(f"Repo {full} exists — pushing updates.")
            run_cmd(["git","remote","add","origin", f"https://github.com/{full}.git"], cwd=str(stage))
            rc, out, err = run_cmd(["git","push","-u","--force","origin","main"], cwd=str(stage))
            log.append(out + err)
            if rc != 0: return False, "", "\n".join(log)
        else:
            cmd = ["gh","repo","create", full, f"--{visibility}", "--source", str(stage),
                   "--remote","origin","--push","--description", f"Claude skill: {skill_path.name}"]
            rc, out, err = run_cmd(cmd)
            log.append(out + err)
            if rc != 0: return False, "", "\n".join(log)
        return True, f"https://github.com/{full}", "\n".join(log)

def install_skill_from_url(url, custom_name=None):
    """Clone a github repo into ~/.claude/skills/. Returns (ok, name, log)."""
    log = []
    m = re.match(r"https?://github\.com/([^/]+)/([^/.]+)(?:\.git)?/?$", url.strip())
    if not m: return False, "", "URL must be of the form https://github.com/owner/repo"
    owner, repo = m.group(1), m.group(2)
    name = (custom_name or repo).strip()
    name = re.sub(r"[^A-Za-z0-9_.-]", "-", name)
    target = CLAUDE / "skills" / name
    if target.exists():
        return False, name, f"Already exists: {target}"
    rc, out, err = run_cmd(["git","clone","--depth","1", url.strip(), str(target)])
    log.append(out + err)
    if rc != 0: return False, name, "\n".join(log)
    if not (target / "SKILL.md").exists():
        log.append(f"Warning: no SKILL.md in repo root. Skill cloned but Claude won't recognize it as a skill until SKILL.md is added.")
    return True, name, "\n".join(log)

def mcp_check(name, cfg):
    """Lightweight health check for an MCP server config."""
    if not isinstance(cfg, dict): return ("unknown", "config not a dict")
    if "url" in cfg:  # http/sse server
        url = cfg["url"]
        try:
            import urllib.request
            req = urllib.request.Request(url, method="GET")
            with urllib.request.urlopen(req, timeout=2) as resp:
                return ("ok", f"HTTP {resp.status}")
        except Exception as e:
            return ("fail", f"{type(e).__name__}: {str(e)[:80]}")
    cmd = cfg.get("command")
    if cmd:
        if shutil.which(cmd) or os.path.exists(cmd):
            return ("ok", f"command found: {cmd}")
        return ("fail", f"command not found: {cmd}")
    return ("unknown", "no url or command")

def make_skill_zip(skill_path):
    skill_path = Path(skill_path)
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        for root, dirs, files in os.walk(skill_path):
            dirs[:] = [d for d in dirs if d not in (".venv","__pycache__",".git")]
            for f in files:
                if f == ".DS_Store" or f.endswith(".pyc"): continue
                full = Path(root) / f
                zf.write(full, arcname=str(full.relative_to(skill_path.parent)))
    buf.seek(0)
    return buf.read()

# ---------- collectors ----------
@st.cache_data(ttl=120)
def get_plugin_skill_names():
    """Names of skills installed via plugins. Walk ~/.claude/plugins/ for SKILL.md files."""
    names = set()
    pdir = CLAUDE / "plugins"
    if not pdir.exists(): return names
    for root, dirs, files in os.walk(pdir, followlinks=False):
        if "SKILL.md" in files:
            # The skill name is the parent folder of SKILL.md
            names.add(Path(root).name)
    return names

@st.cache_data(ttl=120)
def load_skills():
    sk = CLAUDE / "skills"
    plugin_names = get_plugin_skill_names()
    rows = []
    if not sk.exists(): return pd.DataFrame()
    for p in sorted(sk.iterdir()):
        if not p.is_dir(): continue
        meta = parse_skill_meta(p)
        mtime = latest_mtime(str(p))
        is_plugin = p.name in plugin_names or p.is_symlink()
        rows.append({
            "name": p.name, "description": meta["description"],
            "size": dir_size(str(p)), "path": str(p),
            "mtime": mtime, "source": "plugin" if is_plugin else "user",
        })
    df = pd.DataFrame(rows)
    if not df.empty: df["size_human"] = df["size"].apply(fmt_size)
    return df

@st.cache_data(ttl=120)
def load_connectors():
    out = []
    for cfg in [CLAUDE / "settings.json", HOME / ".claude.json"]:
        if not cfg.exists(): continue
        try:
            data = json.loads(cfg.read_text())
            for k, v in (data.get("mcpServers") or {}).items():
                out.append({"name": k, "source": cfg.name, "config": redact_secrets(v)})
        except Exception: pass
    return out

@st.cache_data(ttl=120)
def load_plugins():
    out = []
    pdir = CLAUDE / "plugins"
    if not pdir.exists(): return out
    inst = pdir / "installed_plugins.json"
    if inst.exists():
        try:
            data = json.loads(inst.read_text())
            plugins = data.get("plugins") or data
            if isinstance(plugins, dict):
                for k, v in plugins.items(): out.append({"name": k, "info": v})
            elif isinstance(plugins, list):
                for v in plugins: out.append({"name": v.get("name","?"), "info": v})
        except Exception: pass
    mk = pdir / "marketplaces"
    if mk.exists():
        for m in mk.iterdir():
            if m.is_dir(): out.append({"name": f"marketplace/{m.name}", "info": {"path": str(m), "size": fmt_size(dir_size(str(m)))}})
    return out

@st.cache_data(ttl=120)
def load_projects():
    pdir = CLAUDE / "projects"
    rows = []
    if not pdir.exists(): return pd.DataFrame()
    for p in sorted(pdir.iterdir()):
        if not p.is_dir(): continue
        slug = p.name
        decoded = slug.replace("-", "/") if slug.startswith("-") else slug
        files = list(p.glob("*.jsonl"))
        rows.append({
            "project": decoded, "slug": slug, "transcripts": len(files),
            "size": dir_size(str(p)), "path": str(p),
            "last_active": max((f.stat().st_mtime for f in files), default=0),
        })
    df = pd.DataFrame(rows)
    if not df.empty:
        df["size_human"] = df["size"].apply(fmt_size)
        df = df.sort_values("last_active", ascending=False)
    return df

def list_project_sessions(project_storage_path):
    p = Path(project_storage_path)
    if not p.exists(): return []
    out = []
    for f in p.glob("*.jsonl"):
        s = f.stat()
        out.append({"name": f.name, "size": s.st_size, "mtime": s.st_mtime, "path": str(f)})
    return sorted(out, key=lambda x: -x["mtime"])

@st.cache_data(ttl=120)
def load_config_files():
    rows = []
    for f in ["settings.json","settings.local.json","CLAUDE.md","policy-limits.json","stats-cache.json","mcp-needs-auth-cache.json",".last-cleanup"]:
        p = CLAUDE / f
        if p.exists(): rows.append({"name": f, "size": dir_size(str(p)), "path": str(p)})
    cdir = CLAUDE / "commands"
    if cdir.exists():
        for c in cdir.iterdir():
            rows.append({"name": f"commands/{c.name}", "size": dir_size(str(c)), "path": str(c)})
    df = pd.DataFrame(rows)
    if not df.empty:
        df["size_human"] = df["size"].apply(fmt_size)
        df = df.sort_values("size", ascending=False)
    return df

@st.cache_data(ttl=120)
def load_cache():
    rows = []
    for d in ["shell-snapshots","paste-cache","file-history","image-cache","session-env","telemetry","ide","cache","downloads","debug","backups","todos"]:
        p = CLAUDE / d
        if p.exists():
            rows.append({"name": d, "items": len(list(p.iterdir())) if p.is_dir() else 0, "size": dir_size(str(p)), "path": str(p)})
    h = CLAUDE / "history.jsonl"
    if h.exists(): rows.append({"name":"history.jsonl","items":0,"size":h.stat().st_size,"path":str(h)})
    df = pd.DataFrame(rows)
    if not df.empty:
        df["size_human"] = df["size"].apply(fmt_size)
        df = df.sort_values("size", ascending=False)
    return df

@st.cache_data(ttl=120)
def load_tasks():
    rows = []
    for d in ["tasks","plans"]:
        p = CLAUDE / d
        if p.exists():
            rows.append({"name": d, "items": len(list(p.iterdir())), "size": dir_size(str(p)), "path": str(p)})
    df = pd.DataFrame(rows)
    if not df.empty: df["size_human"] = df["size"].apply(fmt_size)
    return df

# ---------- dialogs ----------
@st.dialog("Skill details", width="large")
def dialog_view(skill_name, skill_path):
    meta = parse_skill_meta(Path(skill_path))
    st.markdown(f"### {skill_name}")
    st.caption(skill_path)
    if meta["description"]: st.info(meta["description"])
    c1, c2, c3 = st.columns(3)
    if c1.button("Open in Finder", type="primary", width="stretch", key="dv_finder"):
        open_in_finder(skill_path); st.toast(f"Opened {skill_name}")
    if c2.button("Open in Terminal", width="stretch", key="dv_term"):
        open_in_terminal(skill_path); st.toast("Opened Terminal")
    if c3.button("Copy path", width="stretch", key="dv_copy"):
        if pbcopy(skill_path): st.toast("Path copied")
    st.divider()
    st.markdown("#### SKILL.md")
    if meta["body"]: st.markdown(meta["body"])
    else: st.caption("(no content)")

@st.dialog("Push skill to GitHub", width="large")
def dialog_push(skill_name, skill_path):
    cfg = load_config_dict()
    auth = gh_auth_status()
    if not auth["gh_present"]:
        st.error("`gh` CLI not found. Install with: `brew install gh`"); return
    if not auth["logged_in"]:
        st.error("Not signed in to GitHub. Run in a terminal: `gh auth login`"); st.code(auth["raw"][:600]); return
    st.success(f"Authenticated via gh CLI as **{auth['user'] or 'unknown'}** at **{auth['host'] or 'github.com'}**")
    owner = cfg.get("github_owner") or auth["user"] or ""
    if not owner:
        st.warning("Set a default GitHub owner in **Settings** first."); return
    repo_default = (cfg.get("repo_prefix") or "") + skill_name
    c1, c2 = st.columns(2)
    repo = c1.text_input("Repo name", value=repo_default)
    visibility = c2.radio("Visibility", ["private","public"], horizontal=True,
                          index=0 if cfg.get("default_visibility","private")=="private" else 1)
    full = f"{owner}/{repo}"
    exists = gh_repo_exists(owner, repo)
    st.caption(f"Target: **{full}** — " + ("exists, will force-push update" if exists else "will be created"))
    confirm = st.checkbox("I understand this will publish skill files to GitHub", value=False)
    if st.button("Push to GitHub", type="primary", disabled=not confirm, width="stretch"):
        with st.spinner(f"Pushing {full}…"):
            ok, url, log = push_skill_to_github(skill_path, owner, repo, visibility)
        if ok:
            st.session_state[f"pushed_{skill_name}"] = url
            cfg2 = load_config_dict()
            cfg2.setdefault("pushed_skills", {})[skill_name] = url
            save_config(cfg2)
            st.success(f"Pushed: {url}")
            st.link_button("Open repo on GitHub", url)
            if pbcopy(url): st.toast("URL copied")
        else:
            st.error("Push failed.")
        with st.expander("Log"): st.code(log)

@st.dialog("Settings", width="large")
def dialog_settings():
    cfg = load_config_dict()
    auth = gh_auth_status()
    st.caption("This app uses your existing `gh` CLI session — no tokens are stored.")
    if not auth["gh_present"]:
        st.error("`gh` CLI not installed. Install via: `brew install gh`")
    elif auth["logged_in"]:
        st.success(f"Authenticated as **{auth['user'] or 'unknown'}** at **{auth['host'] or 'github.com'}** (via gh CLI)")
    else:
        st.error("Not signed in. Run in a terminal: `gh auth login`")
    with st.expander("gh auth status output"): st.code(auth["raw"] or "(no output)")

    st.markdown("**Push defaults**")
    with st.form("settings_form_dlg"):
        owner = st.text_input("Default GitHub owner / org", value=cfg.get("github_owner",""))
        prefix = st.text_input("Repo name prefix", value=cfg.get("repo_prefix","claude-skill-"))
        vis = st.radio("Default visibility", ["private","public"], horizontal=True,
                       index=0 if cfg.get("default_visibility","private")=="private" else 1)
        commit = st.text_input("Commit message template", value=cfg.get("commit_message_template","Update {skill} skill"))
        if st.form_submit_button("Save", type="primary"):
            cfg2 = load_config_dict()
            cfg2.update({"github_owner": owner.strip(), "repo_prefix": prefix.strip(),
                         "default_visibility": vis, "commit_message_template": commit.strip()})
            save_config(cfg2)
            st.success("Saved.")
            st.cache_data.clear()
    with st.expander("Config file"):
        st.code(str(CONFIG_PATH)); st.json(load_config_dict())

@st.dialog("Install skill from GitHub", width="large")
def dialog_install_skill():
    st.caption("Clone a public GitHub repo into ~/.claude/skills/. The repo should contain a SKILL.md at the root.")
    url = st.text_input("GitHub URL", placeholder="https://github.com/owner/repo")
    custom = st.text_input("Local skill name (optional)", placeholder="defaults to repo name")
    if st.button("Install", type="primary", width="stretch", disabled=not url.strip()):
        with st.spinner("Cloning…"):
            ok, name, log = install_skill_from_url(url, custom or None)
        if ok:
            st.success(f"Installed as `{name}` at ~/.claude/skills/{name}/")
            st.cache_data.clear()
        else:
            st.error("Install failed.")
        with st.expander("Log"): st.code(log)

@st.dialog("Share skill", width="large")
def dialog_share(skill_name, skill_path):
    pushed_url = st.session_state.get(f"pushed_{skill_name}")
    st.markdown(f"**{skill_name}**")
    st.caption(skill_path)
    if pushed_url:
        st.success(f"Last pushed: {pushed_url}")
        c1,c2 = st.columns(2)
        if c1.button("Copy GitHub URL", width="stretch"):
            if pbcopy(pushed_url): st.toast("URL copied")
        c2.link_button("Open on GitHub", pushed_url, width="stretch")
        st.divider()
    meta = parse_skill_meta(Path(skill_path))
    if st.button("Copy SKILL.md to clipboard", width="stretch"):
        if pbcopy(meta["raw"]): st.toast("SKILL.md copied")
    zip_bytes = make_skill_zip(skill_path)
    st.download_button("Download skill as .zip", data=zip_bytes,
                       file_name=f"{skill_name}.zip", mime="application/zip", width="stretch")
    st.caption("The .zip is portable — drop into any `~/.claude/skills/` folder.")

# ---------- sidebar ----------
PAGES = ["Overview","Token Usage","Skills","MCP Connectors","Plugins","Sessions","Search","Cleanup","Config","History & Cache","Tasks & Plans","Sunburst","Graph","Help"]

with st.sidebar:
    st.markdown('<div class="brand-title">My Claude</div>', unsafe_allow_html=True)
    st.markdown(f'<div class="brand-sub">{CLAUDE}</div>', unsafe_allow_html=True)

    auth = gh_auth_status()
    cfg = load_config_dict()
    if auth["gh_present"] and auth["logged_in"]:
        chip = f'<div class="gh-chip"><span class="dot"></span><div style="font-weight:600">{auth["user"] or "GitHub"}</div></div>'
    elif auth["gh_present"]:
        chip = '<div class="gh-chip warn"><span class="dot"></span><div style="font-weight:600">Not signed in</div></div>'
    else:
        chip = '<div class="gh-chip warn"><span class="dot"></span><div style="font-weight:600">gh CLI missing</div></div>'
    st.markdown(chip, unsafe_allow_html=True)

    page = st.radio("nav", PAGES, label_visibility="collapsed", key="nav_page")

    st.divider()
    bc1, bc2 = st.columns(2)
    if bc1.button("Settings", key="settings_btn", width="stretch"):
        dialog_settings()
    if bc2.button("Refresh", key="refresh_btn", width="stretch"):
        st.cache_data.clear(); st.rerun()
    if st.button("Help", key="help_quick", width="stretch"):
        st.session_state["nav_page"] = "Help"; st.rerun()

    st.markdown(f'<div class="foot-cap">Updated {datetime.now().strftime("%H:%M")} · localhost-only</div>', unsafe_allow_html=True)

def page_header(title, caption=None):
    """Render a page title with the theme-toggle button on the right of the same row."""
    cols = st.columns([8, 1])
    with cols[0]:
        st.title(title)
        if caption: st.caption(caption)
    with cols[1]:
        st.markdown('<div class="theme-btn" style="margin-top:8px">', unsafe_allow_html=True)
        other = "dark" if st.session_state["theme_mode"] == "light" else "light"
        label = "Light" if other == "light" else "Dark"
        if st.button(label, key=f"theme_{title}", width="stretch", help="Toggle theme"):
            st.session_state["theme_mode"] = other
            st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)

# ---------- pages ----------
def page_overview():
    page_header("My Claude", "An interactive view of your Claude installation. All data is local.")
    skills=load_skills(); projects=load_projects(); connectors=load_connectors()
    plugins=load_plugins(); cfg_files=load_config_files(); cache=load_cache(); tasks=load_tasks()

    sizes = {
        "Skills": int(skills["size"].sum()) if not skills.empty else 0,
        "Sessions": int(projects["size"].sum()) if not projects.empty else 0,
        "Config": int(cfg_files["size"].sum()) if not cfg_files.empty else 0,
        "Cache": int(cache["size"].sum()) if not cache.empty else 0,
        "Tasks": int(tasks["size"].sum()) if not tasks.empty else 0,
        "Plugins": dir_size(str(CLAUDE / "plugins")),
    }
    total = sum(sizes.values())

    c = st.columns(4)
    c[0].metric("Skills", len(skills), fmt_size(sizes["Skills"]))
    c[1].metric("Projects", len(projects), fmt_size(sizes["Sessions"]))
    c[2].metric("MCP connectors", len(connectors), " ")
    c[3].metric("Plugins", len(plugins), " ")
    c = st.columns(4)
    c[0].metric("Config files", len(cfg_files), " ")
    c[1].metric("Cache buckets", len(cache), " ")
    c[2].metric("Tasks/plans", len(tasks), " ")
    c[3].metric("Total on disk", fmt_size(total), " ")

    st.divider()
    st.warning("Privacy: ~/.claude/projects/ stores full transcripts in plaintext. Don't share screenshots without redacting.")

    st.subheader("Storage breakdown")
    bd = pd.DataFrame([{"Category":k,"Size":v} for k,v in sizes.items() if v>0]).sort_values("Size")
    fig = px.bar(bd, x="Size", y="Category", orientation="h",
                 text=bd["Size"].apply(fmt_size), color="Category", color_discrete_map=CAT_COLOR)
    fig.update_layout(height=320, margin=dict(l=0,r=0,t=10,b=0), showlegend=False,
                      paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)")
    fig.update_traces(textposition="outside")
    st.plotly_chart(fig, width="stretch")

def page_skills():
    page_header("Skills", "Capabilities loaded into Claude. Each is a folder with a SKILL.md describing when Claude should use it.")
    cfg = load_config_dict(); auth = gh_auth_status()
    # hydrate persisted push state
    for sk_name, url in (cfg.get("pushed_skills") or {}).items():
        st.session_state.setdefault(f"pushed_{sk_name}", url)
    df = load_skills()
    if df.empty: st.info("No skills found."); return

    top_row = st.columns([2,1,1,1])
    with top_row[0]:
        if st.button("Install skill from GitHub URL", width="stretch"):
            dialog_install_skill()
    source_filter = top_row[1].selectbox("Source", ["All", "User-created", "Plugin-installed"], label_visibility="collapsed")
    sort = top_row[2].selectbox("Sort", ["Name (A-Z)", "Size (high to low)", "Recently modified"], label_visibility="collapsed")
    recent_only = top_row[3].toggle("Recent (7d)", value=False)

    now = datetime.now().timestamp()
    recent_threshold = now - 7*24*3600

    q = st.text_input("Search by name or description", placeholder="Search by name or description (e.g. testing, security, react)",
                      key="skq", label_visibility="collapsed")

    filtered = df.copy()
    if source_filter == "User-created":      filtered = filtered[filtered["source"] == "user"]
    elif source_filter == "Plugin-installed": filtered = filtered[filtered["source"] == "plugin"]
    if recent_only:                          filtered = filtered[filtered["mtime"] > recent_threshold]
    if q:
        ql = q.lower()
        filtered = filtered[filtered["name"].str.lower().str.contains(ql) | filtered["description"].str.lower().str.contains(ql)]
    if sort == "Name (A-Z)":              filtered = filtered.sort_values("name")
    elif sort == "Size (high to low)":    filtered = filtered.sort_values("size", ascending=False)
    elif sort == "Recently modified":     filtered = filtered.sort_values("mtime", ascending=False)

    st.caption(f"**{len(filtered)} of {len(df)}** skills · {fmt_size(filtered['size'].sum())} · "
               f"User: {len(df[df['source']=='user'])} · Plugin: {len(df[df['source']=='plugin'])}")

    can_push = auth["logged_in"] and bool(cfg.get("github_owner"))
    if not can_push:
        msg = "Push disabled — "
        if not auth["logged_in"]: msg += "run `gh auth login` in a terminal."
        elif not cfg.get("github_owner"): msg += "set a default GitHub owner in Settings."
        st.info(msg)

    PAGE_SIZE = 30
    total_pages = max(1, (len(filtered) + PAGE_SIZE - 1) // PAGE_SIZE)
    page_n = st.number_input(f"Page (1-{total_pages})", 1, total_pages, 1, key="skp") if total_pages > 1 else 1
    chunk = filtered.iloc[(page_n-1)*PAGE_SIZE : page_n*PAGE_SIZE]

    for _, row in chunk.iterrows():
        with st.container(border=True):
            head = st.columns([7,1])
            tags = ""
            if row["source"] == "plugin": tags += '<span class="tag plugin">plugin</span>'
            else: tags += '<span class="tag user">user</span>'
            if row["mtime"] > recent_threshold: tags += '<span class="tag recent">recent</span>'
            pushed = st.session_state.get(f"pushed_{row['name']}")
            if pushed: tags += f'<span class="tag pushed">pushed</span>'
            head[0].markdown(f"<div style='font-size:15px;font-weight:600'>{row['name']}{tags}</div>", unsafe_allow_html=True)
            head[1].markdown(f"<div style='text-align:right;color:#64748b;font-size:12px;padding-top:4px'>{row['size_human']}</div>", unsafe_allow_html=True)
            if row["description"]:
                st.caption(row["description"])
            btns = st.columns([1,1,1,7])
            with btns[0]:
                st.markdown('<div class="btn-view">', unsafe_allow_html=True)
                if st.button("View", key=f"v_{row['name']}", width="stretch"):
                    dialog_view(row["name"], row["path"])
                st.markdown('</div>', unsafe_allow_html=True)
            with btns[1]:
                st.markdown('<div class="btn-push">', unsafe_allow_html=True)
                if st.button("Push", key=f"p_{row['name']}", width="stretch", disabled=not can_push):
                    dialog_push(row["name"], row["path"])
                st.markdown('</div>', unsafe_allow_html=True)
            with btns[2]:
                st.markdown('<div class="btn-share">', unsafe_allow_html=True)
                if st.button("Share", key=f"s_{row['name']}", width="stretch"):
                    dialog_share(row["name"], row["path"])
                st.markdown('</div>', unsafe_allow_html=True)

def page_connectors():
    page_header("MCP Connectors", "External tools wired into Claude via the Model Context Protocol — Notion, Drive, Slack, internal services, etc.")
    items = load_connectors()
    if not items: st.info("No MCP connectors configured. Add via `claude mcp add`."); return
    do_health = st.toggle("Run health check", value=False, help="Reachability test for each connector. HTTP for url-based, command-presence for stdio.")
    st.caption(f"{len(items)} connector(s) · sensitive values redacted")
    q = st.text_input("Search", placeholder="connector name", key="cnq", label_visibility="collapsed").lower()
    for c in items:
        if q and q not in c["name"].lower(): continue
        status_label = ""
        if do_health:
            status, detail = mcp_check(c["name"], c["config"])
            color = {"ok":"#10b981","fail":"#ef4444","unknown":"#94a3b8"}[status]
            status_label = f" — <span style='color:{color};font-weight:600'>{status}</span> <span style='color:#64748b;font-size:11px'>{detail}</span>"
        with st.expander(f"{c['name']} — {c['source']}"):
            if status_label: st.markdown(status_label, unsafe_allow_html=True)
            st.json(c["config"])

def page_plugins():
    page_header("Plugins", "Bundles of skills, slash commands, and config installed from a marketplace via /plugin.")
    items = load_plugins()
    if not items: st.info("No plugins installed."); return
    q = st.text_input("Search", key="pgq", label_visibility="collapsed").lower()
    for p in items:
        if q and q not in p["name"].lower(): continue
        with st.expander(p["name"]):
            st.json(p["info"])

def page_sessions():
    page_header("Sessions", "Each row is a project where you've used Claude Code. Expand to see individual conversation transcripts.")
    st.warning("Sensitive: transcripts are full conversation logs in plaintext. Don't share without redacting.")
    df = load_projects()
    if df.empty: st.info("No projects found."); return
    q = st.text_input("Search by project path", key="ssq", label_visibility="collapsed").lower()
    filtered = df if not q else df[df["project"].str.lower().str.contains(q)]
    st.caption(f"**{len(filtered)} of {len(df)}** projects · {fmt_size(filtered['size'].sum())}")

    editor = "VSCode" if shutil.which("code") else "TextEdit"

    for _, row in filtered.iterrows():
        project_real = row["project"]
        storage_path = row["path"]
        last = fmt_when(row["last_active"]) if row["last_active"] else "—"
        with st.expander(f"{project_real}  ·  {row['transcripts']} transcripts  ·  {row['size_human']}  ·  last active {last}"):
            real_exists = Path(project_real).exists()
            ac = st.columns(5)
            if ac[0].button("Start Claude here", key=f"sc_{row['slug']}", disabled=not real_exists, width="stretch", type="primary"):
                if start_claude_in_project(project_real): st.toast("Launching Claude in Terminal…")
                else: st.error("Failed to launch Terminal")
            if ac[1].button("Open Terminal", key=f"t_{row['slug']}", disabled=not real_exists, width="stretch"):
                open_in_terminal(project_real); st.toast(f"Opened Terminal at {project_real}")
            if ac[2].button("Open in Finder", key=f"f_{row['slug']}", disabled=not real_exists, width="stretch"):
                open_in_finder(project_real); st.toast("Opened in Finder")
            if ac[3].button("Transcripts folder", key=f"tf_{row['slug']}", width="stretch"):
                open_in_finder(storage_path); st.toast("Opened transcripts folder")
            if ac[4].button("Copy path", key=f"cp_{row['slug']}", width="stretch"):
                if pbcopy(project_real): st.toast("Path copied")
            if not real_exists:
                st.caption("Note: original project directory no longer exists on disk — terminal/Finder buttons disabled.")

            sessions = list_project_sessions(storage_path)
            if not sessions:
                st.caption("No transcripts."); continue
            st.markdown("**Transcripts**")
            for s in sessions:
                label = transcript_label(s["path"]) or "(unnamed conversation)"
                short_id = s["name"].split(".")[0][:8]
                with st.container(border=True):
                    head = st.columns([8,1])
                    head[0].markdown(f"**{label}**")
                    head[1].markdown(f"<div style='text-align:right;color:#64748b;font-size:11px;padding-top:3px'>{fmt_size(s['size'])}</div>", unsafe_allow_html=True)
                    st.caption(f"id: `{short_id}…`  ·  {fmt_when(s['mtime'])}")
                    btns = st.columns([2,2,2,2,3])
                    sid_full = s["name"].split(".")[0]
                    if btns[0].button("Resume in Claude", key=f"rs_{row['slug']}_{s['name']}", width="stretch",
                                       type="primary", disabled=not real_exists):
                        if start_claude_in_project(project_real, resume_id=sid_full): st.toast("Resuming in Terminal…")
                        else: st.error("Failed to launch Terminal")
                    if btns[1].button(f"Open in {editor}", key=f"vf_{row['slug']}_{s['name']}", width="stretch"):
                        ok = open_file_default(s["path"])
                        st.toast(f"Opened in {editor}" if ok else "Failed to open")
                    if btns[2].button("Reveal", key=f"rv_{row['slug']}_{s['name']}", width="stretch"):
                        subprocess.run(["open","-R", s["path"]], check=False); st.toast("Revealed")
                    if btns[3].button("Copy id", key=f"ci_{row['slug']}_{s['name']}", width="stretch"):
                        if pbcopy(sid_full): st.toast("Session id copied")

def page_simple_table(title, df, description):
    page_header(title, description)
    if df.empty: st.info("Nothing here."); return
    q = st.text_input("Search", key=f"q_{title}", label_visibility="collapsed").lower()
    filtered = df if not q else df[df["name"].str.lower().str.contains(q)]
    st.caption(f"**{len(filtered)} of {len(df)}** · {fmt_size(filtered['size'].sum())}")
    for _, row in filtered.iterrows():
        with st.container(border=True):
            cols = st.columns([4,2,1,1,1])
            cols[0].markdown(f"**{row['name']}**")
            extra = f"{row.get('items','')} items" if 'items' in row and row.get('items') else ""
            cols[1].caption(extra)
            cols[2].caption(row["size_human"])
            if cols[3].button("Open", key=f"st_{title}_{row['name']}", width="stretch"):
                open_in_finder(row["path"]); st.toast("Opened")
            if cols[4].button("Copy", key=f"sc_{title}_{row['name']}", width="stretch"):
                if pbcopy(row["path"]): st.toast("Path copied")

def page_sunburst():
    page_header("Sunburst", "Hierarchical disk usage. Click any slice to drill in or zoom out.")
    skills=load_skills(); projects=load_projects(); cfg_files=load_config_files()
    cache=load_cache(); tasks=load_tasks()
    rows = []
    for _, r in skills.iterrows():    rows.append(("Skills",   r["name"],    int(r["size"]), r["path"]))
    for _, r in projects.iterrows():  rows.append(("Sessions", r["project"], int(r["size"]), r["path"]))
    for _, r in cfg_files.iterrows(): rows.append(("Config",   r["name"],    int(r["size"]), r["path"]))
    for _, r in cache.iterrows():     rows.append(("Cache",    r["name"],    int(r["size"]), r["path"]))
    for _, r in tasks.iterrows():     rows.append(("Tasks",    r["name"],    int(r["size"]), r["path"]))
    df = pd.DataFrame(rows, columns=["category","name","size","path"])
    df = df[df["size"]>0].copy()
    df["size_human"] = df["size"].apply(fmt_size)

    main, side = st.columns([3,1])
    with main:
        fig = px.sunburst(df, path=[px.Constant("My Claude"),"category","name"], values="size",
                          color="category", color_discrete_map=CAT_COLOR,
                          custom_data=["size_human","path"])
        fig.update_traces(
            hovertemplate="<b>%{label}</b><br>%{customdata[0]}<br>%{customdata[1]}<extra></extra>",
            insidetextorientation="radial",
            marker=dict(line=dict(width=1.5, color="#ffffff" if st.session_state["theme_mode"]=="light" else "#0b1020")),
        )
        fig.update_layout(height=720, margin=dict(l=0,r=0,t=10,b=0),
                          paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)")
        event = st.plotly_chart(fig, width="stretch", on_select="rerun", selection_mode="points", key="sb")
    with side:
        st.markdown("##### Selected")
        if event and event.selection and event.selection.get("points"):
            pt = event.selection["points"][0]
            label = pt.get("label","")
            match = df[df["name"] == label]
            if not match.empty:
                row = match.iloc[0]
                st.markdown(f"**{row['name']}**")
                st.caption(f"{row['category']} · {row['size_human']}")
                st.code(row["path"], language=None)
                if st.button("Open in Finder", type="primary", width="stretch", key="sb_open"):
                    open_in_finder(row["path"]); st.toast("Opened")
                if st.button("Open in Terminal", width="stretch", key="sb_term"):
                    open_in_terminal(row["path"]); st.toast("Opened Terminal")
                if st.button("Copy path", width="stretch", key="sb_copy"):
                    if pbcopy(row["path"]): st.toast("Path copied")
            elif label in {"Skills","Sessions","Config","Cache","Tasks"}:
                cat_total = int(df[df["category"]==label]["size"].sum())
                st.markdown(f"**{label}** category")
                st.caption(f"{len(df[df['category']==label])} items · {fmt_size(cat_total)}")
        else:
            st.caption("Click any slice to see details and actions.")

def page_graph():
    page_header("Graph view", "Network: root → categories → items. Drag, scroll to zoom, hover for details.")
    top_n = st.slider("Items per category", 5, 50, 15)
    is_dark = st.session_state["theme_mode"] == "dark"
    bg = "#0b1020" if is_dark else "#ffffff"
    fg = "#e8ecff" if is_dark else "#0f172a"
    edge_c = "#283057" if is_dark else "#cbd5e1"
    edge_l = "#1f2647" if is_dark else "#e2e8f0"

    net = Network(height="720px", width="100%", bgcolor=bg, font_color=fg, directed=False, cdn_resources="remote")
    net.toggle_physics(True)
    net.barnes_hut(gravity=-12000, central_gravity=0.25, spring_length=120, spring_strength=0.02, damping=0.3)
    net.add_node("ROOT", label="My Claude", color=fg, size=42, shape="dot")

    skills=load_skills(); projects=load_projects(); cfg_files=load_config_files()
    cache=load_cache(); tasks=load_tasks(); plugins=load_plugins(); connectors=load_connectors()

    cat_data = {
        "Skills":   skills.sort_values("size", ascending=False).head(top_n) if not skills.empty else pd.DataFrame(),
        "Sessions": projects.head(top_n) if not projects.empty else pd.DataFrame(),
        "Config":   cfg_files.head(top_n) if not cfg_files.empty else pd.DataFrame(),
        "Cache":    cache.head(top_n) if not cache.empty else pd.DataFrame(),
        "Tasks":    tasks.head(top_n) if not tasks.empty else pd.DataFrame(),
    }
    for cat, dfc in cat_data.items():
        cid = f"CAT_{cat}"
        total = int(dfc["size"].sum()) if not dfc.empty else 0
        net.add_node(cid, label=f"{cat} ({len(dfc)})", color=CAT_COLOR[cat], size=30, shape="dot",
                     title=f"{cat}: {len(dfc)} items · {fmt_size(total)}")
        net.add_edge("ROOT", cid, color=edge_c, width=2)
        for _, r in dfc.iterrows():
            name = r.get("name") or r.get("project") or "?"
            sz = int(r["size"])
            ns = max(8, min(28, 8 + (sz ** 0.25) / 2))
            net.add_node(f"{cat}_{name}", label=name[:32], color=CAT_COLOR[cat], size=ns, shape="dot",
                         title=f"{name}\n{fmt_size(sz)}\n{r['path']}")
            net.add_edge(cid, f"{cat}_{name}", color=edge_l, width=1)

    cid = "CAT_Connectors"
    net.add_node(cid, label=f"Connectors ({len(connectors)})", color=CAT_COLOR["Connectors"], size=26, shape="dot")
    net.add_edge("ROOT", cid, color=edge_c, width=2)
    for c in connectors:
        net.add_node(f"MCP_{c['name']}", label=c["name"], color=CAT_COLOR["Connectors"], size=14, shape="dot", title=c["name"])
        net.add_edge(cid, f"MCP_{c['name']}", color=edge_l, width=1)

    cid = "CAT_Plugins"
    net.add_node(cid, label=f"Plugins ({len(plugins)})", color=CAT_COLOR["Plugins"], size=24, shape="dot")
    net.add_edge("ROOT", cid, color=edge_c, width=2)
    for p in plugins:
        net.add_node(f"PLG_{p['name']}", label=p["name"], color=CAT_COLOR["Plugins"], size=12, shape="dot", title=p["name"])
        net.add_edge(cid, f"PLG_{p['name']}", color=edge_l, width=1)

    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".html", mode="w")
    net.save_graph(tmp.name)
    components.html(Path(tmp.name).read_text(), height=740, scrolling=False)

def page_token_usage():
    page_header("Token Usage", "Parsed from local transcripts. Numbers may differ from Claude Desktop — see notes at bottom.")
    df = aggregate_usage()
    if df.empty:
        st.info("No usage data found in any transcript yet."); return

    df = df.copy()
    # Billable tokens = input (uncached) + cache writes + cache reads + output
    df["billable"] = df["input_tokens"] + df["cache_creation"] + df["cache_read"] + df["output_tokens"]
    # Context tokens = the size of conversation seen by the model (input + output, no cache double-count)
    df["context"] = df["input_tokens"] + df["cache_read"] + df["output_tokens"]

    # Window filter
    win = st.radio("Window", ["All time", "30 days", "7 days"], horizontal=True, index=0, key="tok_win")
    if win != "All time" and df["date"].notna().any():
        days = 30 if win == "30 days" else 7
        cutoff = (datetime.now().date() - pd.Timedelta(days=days)).isoformat() if False else (datetime.now() - pd.Timedelta(days=days)).date()
        df = df[df["date"].apply(lambda d: bool(d) and d >= cutoff)]
    if df.empty:
        st.info("No data in this window."); return

    c = st.columns(4)
    c[0].metric("Billable tokens", fmt_num(df["billable"].sum()), help="Input (uncached) + cache writes + cache reads + output. This is what you pay for.")
    c[1].metric("Context tokens", fmt_num(df["context"].sum()), help="Tokens the model actually saw (input + output). Closest match to Claude Desktop's 'Total tokens'.")
    c[2].metric("Output", fmt_num(df["output_tokens"].sum()))
    c[3].metric("Estimated cost", f"${df['cost'].sum():,.2f}", help="Token counts × public Anthropic pricing.")

    cache_total = int(df["cache_read"].sum() + df["cache_creation"].sum())
    cache_hit = (df["cache_read"].sum() / cache_total * 100) if cache_total else 0
    c2 = st.columns(4)
    c2[0].metric("Cache reads", fmt_num(df["cache_read"].sum()))
    c2[1].metric("Cache writes", fmt_num(df["cache_creation"].sum()))
    c2[2].metric("Cache hit rate", f"{cache_hit:.1f}%")
    c2[3].metric("Turns logged", fmt_num(len(df)))

    st.divider()

    if df["date"].notna().any():
        st.subheader("Billable tokens per day")
        by_day = df.dropna(subset=["date"]).groupby(["date","family"], as_index=False).agg(tokens=("billable","sum"), cost=("cost","sum"))
        fig = px.bar(by_day, x="date", y="tokens", color="family", color_discrete_map={"opus":"#7c3aed","sonnet":"#2563eb","haiku":"#0891b2"})
        fig.update_layout(height=320, margin=dict(l=0,r=0,t=10,b=0), paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)")
        st.plotly_chart(fig, width="stretch")

    st.subheader("Top projects by cost")
    by_proj = df.groupby("project", as_index=False).agg(
        tokens=("billable","sum"), cost=("cost","sum"), turns=("project","count")).sort_values("cost", ascending=False)
    by_proj["cost"] = by_proj["cost"].round(2)
    by_proj["tokens"] = by_proj["tokens"].apply(fmt_num)
    st.dataframe(by_proj, width="stretch", hide_index=True,
                 column_config={"cost": st.column_config.NumberColumn("est cost ($)", format="$%.2f")})

    # By model
    st.subheader("Cost by model")
    by_model = df.groupby("family", as_index=False).agg(tokens=("total","sum"), cost=("cost","sum"))
    fig2 = px.pie(by_model, values="cost", names="family", hole=0.45,
                  color="family", color_discrete_map={"opus":"#7c3aed","sonnet":"#2563eb","haiku":"#0891b2"})
    fig2.update_layout(height=300, margin=dict(l=0,r=0,t=10,b=0), paper_bgcolor="rgba(0,0,0,0)")
    st.plotly_chart(fig2, width="stretch")

    with st.expander("Why does this differ from Claude Desktop?"):
        st.markdown("""
- Claude Desktop's "Total tokens" figure typically reflects **context tokens** (what the model saw — input + output), not the **billable** total. Compare against the second metric here.
- Cache reads count as billable tokens (at ~10% price) but are usually not shown as "new" tokens in Claude Desktop's headline.
- This view aggregates **only Claude Code** transcripts on this machine. Slayzone / web Claude / desktop chats are tracked separately by Anthropic and not reflected here.
- Only completed turns make it to disk. An in-progress session won't show up until it flushes its JSONL.
""")
    with st.expander("Pricing constants (per 1M tokens)"):
        st.json(PRICING)
        st.caption("Override at the top of app.py if your rates differ.")

@st.cache_data(ttl=300)
def search_transcripts(needle, max_hits=200):
    needle_lc = needle.lower()
    out = []
    pdir = CLAUDE / "projects"
    if not pdir.exists(): return out
    for proj in pdir.iterdir():
        if not proj.is_dir(): continue
        decoded = proj.name.replace("-","/") if proj.name.startswith("-") else proj.name
        for jf in proj.glob("*.jsonl"):
            try:
                with open(jf, "r", errors="ignore") as f:
                    for ln, line in enumerate(f, 1):
                        if needle_lc not in line.lower(): continue
                        try: obj = json.loads(line)
                        except Exception:
                            snippet = line.strip()[:200]
                        else:
                            msg = obj.get("message") or obj
                            content = msg.get("content") if isinstance(msg, dict) else None
                            text = ""
                            if isinstance(content, str): text = content
                            elif isinstance(content, list):
                                for c in content:
                                    if isinstance(c, dict) and c.get("type") == "text":
                                        text += c.get("text","") + " "
                            snippet = re.sub(r"\s+", " ", text or line)[:240]
                        out.append({"project": decoded, "session": jf.name.split(".")[0], "line": ln, "snippet": snippet, "path": str(jf)})
                        if len(out) >= max_hits: return out
            except Exception: continue
    return out

def page_search():
    page_header("Search transcripts", "Full-text search across every conversation in ~/.claude/projects/. Plaintext only — keep that in mind.")
    q = st.text_input("Phrase to search", placeholder="e.g. redash key, expo keyboard, eval report", label_visibility="collapsed")
    if not q.strip():
        st.info("Type a phrase above to start."); return
    with st.spinner("Searching…"):
        hits = search_transcripts(q.strip())
    if not hits: st.warning("No matches."); return
    st.caption(f"{len(hits)} hits across {len({h['session'] for h in hits})} sessions")
    by_session = {}
    for h in hits: by_session.setdefault((h["project"], h["session"], h["path"]), []).append(h)
    editor = "VSCode" if shutil.which("code") else "TextEdit"
    for (proj, sid, path), group in by_session.items():
        with st.expander(f"{proj}  ·  session {sid[:8]}…  ·  {len(group)} matches"):
            cols = st.columns(3)
            if cols[0].button(f"Open in {editor}", key=f"se_open_{sid}"):
                open_file_default(path); st.toast("Opening")
            if cols[1].button("Reveal in Finder", key=f"se_rv_{sid}"):
                subprocess.run(["open","-R", path], check=False); st.toast("Revealed")
            if cols[2].button("Resume in Claude", key=f"se_rs_{sid}"):
                if start_claude_in_project(proj, resume_id=sid): st.toast("Resuming…")
            for h in group[:30]:
                st.markdown(f"`line {h['line']}` — {h['snippet']}")
            if len(group) > 30:
                st.caption(f"… {len(group)-30} more matches")

def page_cleanup():
    page_header("Cleanup advisor", "Stale projects and oversized caches. Suggestions only — review before acting.")

    projects = load_projects()
    cache = load_cache()
    now = datetime.now().timestamp()

    if not projects.empty:
        df = projects.copy()
        df["age_days"] = ((now - df["last_active"]) / 86400).round(0).astype(int)
        stale = df[df["age_days"] > 90].sort_values("size", ascending=False)
        st.subheader(f"Stale projects (>90 days inactive) — {len(stale)}")
        if stale.empty:
            st.success("No stale projects.")
        else:
            total_recoverable = int(stale["size"].sum())
            st.caption(f"Reclaimable: **{fmt_size(total_recoverable)}**")
            st.dataframe(stale[["project","transcripts","size_human","age_days"]].rename(columns={"size_human":"size"}),
                         width="stretch", hide_index=True)
            cols = st.columns(2)
            if cols[0].button("Open ~/.claude/projects/ in Finder", width="stretch"):
                open_in_finder(str(CLAUDE / "projects"))
            cols[1].caption("Tip: drag stale folders to Trash from Finder; or back them up first.")

    st.divider()
    st.subheader("Largest cache buckets")
    if cache.empty:
        st.info("No cache data.")
    else:
        big = cache.sort_values("size", ascending=False).head(10)
        st.dataframe(big[["name","items","size_human","path"]].rename(columns={"size_human":"size"}),
                     width="stretch", hide_index=True)
        st.caption("These are safe to clear in most cases (Claude rebuilds them as needed).")

def page_help():
    page_header("Help", "What each section means and where the data lives.")

    sections = [
        ("Overview", "Top-level dashboard with counts and on-disk size for each part of your Claude installation. Storage breakdown chart shows which categories take up the most disk."),
        ("Token Usage", "Tokens and estimated cost across every transcript Claude Code has stored locally. Aggregated from each turn's `usage` block (input/output/cache_creation/cache_read tokens) and your model name. Cost uses Anthropic's public per-million pricing (editable at the top of `app.py`). Updates as new turns get written to disk."),
        ("Skills", "Folders under `~/.claude/skills/`. Each skill is a `SKILL.md` (with frontmatter: name + description) plus optional scripts/templates. Claude searches skill descriptions when deciding what tools to use. Filters: User-created (you wrote them) vs Plugin-installed (came in via /plugin install). Push: snapshots a skill into a fresh GitHub repo. Share: copies SKILL.md or downloads a portable .zip."),
        ("MCP Connectors", "External tool servers wired into Claude via the Model Context Protocol — Notion, Google Drive, Redash, internal services, etc. Configured in `~/.claude/settings.json` or `~/.claude.json` under `mcpServers`. Sensitive values (tokens, keys) are auto-redacted in this view."),
        ("Plugins", "Bundles installed via the `/plugin` slash-command. Plugins can ship multiple skills + slash commands + hooks together. Listed from `~/.claude/plugins/installed_plugins.json`. Marketplaces are the catalogs you install plugins from."),
        ("Search", "Full-text search across every transcript JSONL. Use it when you remember Claude helped with X but can't find which session. Results group by session — open the file or resume the conversation in Claude with one click."),
        ("Cleanup", "Suggestions for what's safe to delete. Lists stale projects (no activity > 90 days) and the largest cache buckets. The cleanup itself is manual — opens Finder so you can review and decide."),
        ("Sessions", "Every project where you've used Claude Code creates a folder under `~/.claude/projects/`. Each `.jsonl` file in there is one conversation transcript — full plaintext, including everything you and Claude said. **Sensitive.** This view shows the project path (decoded from the folder slug) and the first user message of each transcript so you can identify it. Open Terminal launches Terminal.app at the original project directory."),
        ("Config", "Files at the root of `~/.claude/` that drive Claude's behavior: `settings.json` (global), `settings.local.json` (project-specific), `CLAUDE.md` (auto-loaded instructions), and slash command definitions under `commands/`."),
        ("History & Cache", "Caches Claude maintains for performance and continuity: shell snapshots, paste cache, image cache, file-edit history, telemetry, etc. Generally safe to clean up if disk space is tight, but you'll lose context-recall in some cases."),
        ("Tasks & Plans", "Persistent task lists and saved plans Claude has stashed locally during prior sessions."),
        ("Sunburst", "Radial chart of disk usage. Click any slice to drill into that category; click the center to zoom out. Selected slice shows action buttons in the right panel."),
        ("Graph", "Network visualization: root → categories → top items. Drag nodes to reposition, scroll to zoom, hover for details. Top-N slider controls how many items per category."),
        ("Settings (top-right toggle)", "GitHub push defaults: owner, repo prefix, default visibility, commit message template. This app uses your existing `gh` CLI authentication — no tokens are ever stored. To sign in or switch account, run `gh auth login` in a terminal."),
    ]
    for title, body in sections:
        with st.container(border=True):
            st.markdown(f"### {title}")
            st.markdown(body)

    st.divider()
    st.subheader("Privacy & safety")
    st.markdown("""
- This app binds to **127.0.0.1 only** — nobody else on your network can reach it.
- No data leaves your machine. There are no external API calls.
- **Transcripts are stored in plaintext** at `~/.claude/projects/`. Anyone with disk access can read them. Don't share screenshots of the Sessions page without redacting.
- Secrets in MCP configs (any field matching token/key/secret/password/auth/bearer/cred) are auto-redacted.
- GitHub push uses your `gh` CLI session — review the dialog carefully before publishing.
""")

# ---------- router ----------
if   page == "Overview":          page_overview()
elif page == "Token Usage":       page_token_usage()
elif page == "Search":            page_search()
elif page == "Cleanup":           page_cleanup()
elif page == "Skills":            page_skills()
elif page == "MCP Connectors":    page_connectors()
elif page == "Plugins":           page_plugins()
elif page == "Sessions":          page_sessions()
elif page == "Config":            page_simple_table("Config", load_config_files(), "Settings, CLAUDE.md, and slash command definitions at the root of ~/.claude/.")
elif page == "History & Cache":   page_simple_table("History & Cache", load_cache(), "Caches Claude maintains for performance: shell snapshots, paste cache, image cache, file-edit history, telemetry.")
elif page == "Tasks & Plans":     page_simple_table("Tasks & Plans", load_tasks(), "Persistent task lists and saved plans from prior sessions.")
elif page == "Sunburst":          page_sunburst()
elif page == "Graph":             page_graph()
elif page == "Help":              page_help()
