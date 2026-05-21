# my-claude

Claude Code skill: see everything Claude has on your machine — skills, MCP connectors, plugins, sessions, config, history, tasks — as an interactive HTML dashboard with a D3 zoomable treemap.

## Install

```bash
gh repo clone chethanbhatbs/my-claude-skill ~/.claude/skills/my-claude
```

## Use

Invoke from Claude Code with `/my-claude` (or say "show my claude").

Output is written to `~/Documents/My_Claude.html` — open it in any browser. It shows:

- **Dashboard** — KPI cards per category with counts and disk sizes
- **Treemap** — D3 zoomable, proportional to disk usage; click a tile to reveal in Finder
- **Tree** — collapsible file tree with search filter

## Categories

Every entry in `~/.claude/` is bucketed into one of:

| Bucket | What's in it |
|---|---|
| Skills | `~/.claude/skills/*` — your installed skills |
| MCP Connectors | from `settings.json` + `~/.claude.json` `mcpServers` |
| Plugins | `~/.claude/plugins/` |
| Sessions | `~/.claude/projects/*` — full transcripts (flagged sensitive) |
| Config | `settings.json`, `CLAUDE.md`, `commands/`, statusline |
| History & Cache | `history.jsonl`, `shell-snapshots/`, `paste-cache/`, etc. |
| Tasks & Plans | `todos/`, `tasks/`, `plans/` |

## Privacy

No network calls. All data stays local. The output HTML includes a banner highlighting that `~/.claude/projects/` stores full transcripts in plaintext.
