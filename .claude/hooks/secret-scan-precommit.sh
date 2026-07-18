#!/bin/bash
# PreToolUse hook (matcher: Bash). One job: scan staged changes for
# likely-secret patterns before a `git commit` runs, so a key never lands in
# history because a diff wasn't read closely enough.
set -euo pipefail

input="$(cat)"
tool_name="$(printf '%s' "$input" | jq -r '.tool_name // empty')"
[ "$tool_name" = "Bash" ] || exit 0

command="$(printf '%s' "$input" | jq -r '.tool_input.command // empty')"
printf '%s' "$command" | grep -qE '\bgit[[:space:]]+commit\b' || exit 0

cd "${CLAUDE_PROJECT_DIR:-.}"
diff="$(git diff --cached -- . ':!*.lock' ':!package-lock.json' 2>/dev/null || true)"
[ -n "$diff" ] || exit 0

# Anthropic / AWS / GitHub / Slack tokens and PEM private-key blocks.
secret_regex='sk-ant-[A-Za-z0-9_-]{20,}|AKIA[0-9A-Z]{16}|-----BEGIN[A-Z ]*PRIVATE KEY-----|ghp_[A-Za-z0-9]{36}|xox[baprs]-[A-Za-z0-9-]{10,}'

hit="$(printf '%s' "$diff" | grep -nE "$secret_regex" | head -5 || true)"

if [ -n "$hit" ]; then
  echo "secret-scan-precommit blocked this commit: staged changes match a likely-secret pattern (Anthropic/AWS/GitHub/Slack key or a PEM private-key block). Review before committing:" >&2
  echo "$hit" >&2
  exit 2
fi

exit 0
