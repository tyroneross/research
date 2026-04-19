#!/usr/bin/env bash
# Silent PostToolUse hook: if the Write/Edit touched the configured content
# root's topics/*.md tree, re-ingest that entry into the SQLite index and
# rebuild markdown indexes.
# Never blocks Claude on failure.

set -e

# Read hook payload from stdin
payload=$(cat 2>/dev/null || true)
[ -z "$payload" ] && exit 0

# Extract file path via jq if available, else python
if command -v jq >/dev/null 2>&1; then
  file_path=$(printf '%s' "$payload" | jq -r '.tool_input.file_path // empty' 2>/dev/null || true)
else
  file_path=$(printf '%s' "$payload" | python3 -c 'import sys,json
try:
    d=json.load(sys.stdin)
    print(d.get("tool_input",{}).get("file_path",""))
except: pass' 2>/dev/null || true)
fi

[ -z "$file_path" ] && exit 0

# Resolve the content root. RESEARCH_BASE_DIR is preserved as a compatibility alias.
content_root="${RESEARCH_CONTENT_DIR:-${RESEARCH_BASE_DIR:-$HOME/research}}"
case "$content_root" in
  "~"/*) content_root="$HOME/${content_root#~/}" ;;
esac

# Only fire for research entries under <content-root>/topics/**.md
case "$file_path" in
  "$content_root"/topics/*/*.md)
    python3 "${CLAUDE_PLUGIN_ROOT}/research.py" save --file "$file_path" --skip-symlink >/dev/null 2>&1 || true
    ;;
  *)
    ;;
esac

exit 0
