---
name: My-Claude
description: Generate an interactive HTML dashboard of the user's Claude installation — skills, MCP connectors, plugins, sessions, config, history, and tasks — with a D3 zoomable treemap (size-proportional) and clickable category panels. Use when the user asks to "see my Claude", "view my Claude files", "show Claude file structure", "/my-claude", or wants to understand where Claude stores their data on disk.
---

# My-Claude

Generates `~/Documents/My_Claude.html` — an interactive view of everything Claude has on the user's machine, organized by purpose.

## When to invoke
- User says: "show my claude", "my-claude", "/my-claude", "see my claude files", "claude file structure", "where is my claude data".
- User wants to audit on-disk Claude footprint (privacy, cleanup, sharing-safety).

## What it does
Runs `scripts/build.py`. The script:
1. Walks `~/.claude/`, `~/.claude.json`, `~/Library/Application Support/Claude` (if present).
2. Categorizes every top-level entry into one of 7 buckets:
   - **Skills** (`~/.claude/skills/*`) — your installed skills, with description parsed from each `SKILL.md` frontmatter.
   - **MCP Connectors** — pulled from `settings.json` and `~/.claude.json` `mcpServers` blocks.
   - **Plugins** — `~/.claude/plugins/installed_plugins.json` + `marketplaces/`.
   - **Sessions** (`~/.claude/projects/*`) — per-project transcripts, in plaintext. Flagged as **sensitive**.
   - **Config** — `settings.json`, `settings.local.json`, `CLAUDE.md`, `commands/`, `statusline*`.
   - **History & Cache** — `history.jsonl`, `shell-snapshots/`, `paste-cache/`, `file-history/`, `image-cache/`, `session-env/`.
   - **Tasks & Plans** — `todos/`, `tasks/`, `plans/`.
3. Renders a single self-contained HTML with three views:
   - **Dashboard** — KPI cards per category (counts, sizes), click a card to drill in.
   - **Treemap** — D3 zoomable treemap, proportional to disk usage; click any tile to open in Finder.
   - **Tree** — collapsible file tree with search filter.
4. Privacy banner highlighting that `~/.claude/projects/` stores full transcripts in plaintext.

## How to run
```bash
python3 ~/.claude/skills/My-Claude/scripts/build.py
open ~/Documents/My_Claude.html
```

Output is always written to `~/Documents/My_Claude.html`. Surface the path to the user when done.

## Notes
- No external network calls; all data is local.
- `file://` URLs use absolute paths so click-to-open works from `open` and most browsers.
- Skills are listed with their parsed `description` field (first line of frontmatter) for quick scanning.
- Sessions are NOT walked into individual JSONL files (privacy); only directory totals shown.
