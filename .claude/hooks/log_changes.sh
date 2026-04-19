#!/bin/bash
# Reads PostToolUse JSON from stdin, logs change, flags src changes for doc updates.

INPUT=$(cat)
TOOL=$(echo "$INPUT" | python3 -c "
import sys, json
d = json.load(sys.stdin)
print(d.get('tool_name', 'unknown'))
" 2>/dev/null || echo "unknown")

FILE=$(echo "$INPUT" | python3 -c "
import sys, json
d = json.load(sys.stdin)
inp = d.get('tool_input', {})
print(inp.get('file_path', inp.get('path', 'unknown')))
" 2>/dev/null || echo "unknown")

TIMESTAMP=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
LOG_DIR="$(dirname "$0")/../../working"
mkdir -p "$LOG_DIR"

echo "[$TIMESTAMP] $TOOL: $FILE" >> "$LOG_DIR/session_changes.log"

# Flag src Python changes as needing doc review
if echo "$FILE" | grep -qE "src/.*\.py$"; then
  echo "[$TIMESTAMP] PENDING: review docs/TODO.md + README.md after changes to $FILE" >> "$LOG_DIR/pending_doc_updates.md"
fi
