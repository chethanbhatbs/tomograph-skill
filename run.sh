#!/usr/bin/env bash
# Launch the My-Claude Streamlit app, localhost-only, no telemetry.
set -e
SKILL_DIR="$(cd "$(dirname "$0")" && pwd)"
VENV="$SKILL_DIR/.venv"

if [ ! -x "$VENV/bin/streamlit" ]; then
  echo "Setting up venv (one-time)…"
  python3 -m venv "$VENV"
  "$VENV/bin/pip" install --quiet --upgrade pip
  "$VENV/bin/pip" install --quiet streamlit pandas plotly
fi

# Disable Streamlit's anonymous usage telemetry
mkdir -p "$HOME/.streamlit"
if ! grep -q "gatherUsageStats" "$HOME/.streamlit/config.toml" 2>/dev/null; then
  cat >> "$HOME/.streamlit/config.toml" <<EOF
[browser]
gatherUsageStats = false
EOF
fi

echo "Starting My-Claude on http://127.0.0.1:8765 (localhost only, Ctrl+C to stop)…"
exec "$VENV/bin/streamlit" run "$SKILL_DIR/app.py" \
  --server.address 127.0.0.1 \
  --server.port 8765 \
  --server.headless true \
  --browser.gatherUsageStats false
