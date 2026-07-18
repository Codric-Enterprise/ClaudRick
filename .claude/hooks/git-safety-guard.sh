#!/bin/bash
# PreToolUse hook (matcher: Bash). One job: hard-block destructive/history-
# rewriting git commands before they run, as a technical backstop for the
# Git Safety Protocol described in CLAUDE.md/system instructions. It does not
# replace judgment — it only stops the highest-blast-radius commands from
# executing without a human in the loop.
#
# Every check requires an actual `git <verb>` invocation on the SAME line as
# the dangerous pattern, not just the pattern appearing anywhere in the
# command string — otherwise a commit message that *describes* --no-verify
# (like this hook's own commit) would trip the guard on prose, not code.
set -euo pipefail

input="$(cat)"
tool_name="$(printf '%s' "$input" | jq -r '.tool_name // empty')"
[ "$tool_name" = "Bash" ] || exit 0

command="$(printf '%s' "$input" | jq -r '.tool_input.command // empty')"
[ -n "$command" ] || exit 0

reason=""

while IFS= read -r line; do
  [ -n "$reason" ] && break

  if echo "$line" | grep -qE '\bgit[[:space:]]+push\b' \
    && echo "$line" | grep -qE -- '(--force\b|(^|[[:space:]])-f([[:space:]]|$))' \
    && ! echo "$line" | grep -qE -- '--force-with-lease'; then
    reason="git push --force (without --force-with-lease) can overwrite remote history other people rely on"
  elif echo "$line" | grep -qE '\bgit[[:space:]]+reset[[:space:]]+--hard\b'; then
    reason="git reset --hard discards uncommitted work irreversibly"
  elif echo "$line" | grep -qE '\bgit[[:space:]]+clean[[:space:]]+-[a-zA-Z]*f'; then
    reason="git clean -f permanently deletes untracked files"
  elif echo "$line" | grep -qE '\bgit[[:space:]]+branch[[:space:]]+-D\b'; then
    reason="git branch -D force-deletes a branch, losing unmerged commits"
  elif echo "$line" | grep -qE '\bgit[[:space:]]+(checkout|restore)[[:space:]]+(--[[:space:]]+)?\.([[:space:]]|$)'; then
    reason="this discards all uncommitted changes in the working tree"
  elif echo "$line" | grep -qE '\bgit[[:space:]]+(commit|push)\b' \
    && echo "$line" | grep -qE -- '--no-verify\b|--no-gpg-sign\b'; then
    reason="this skips a commit hook or signature check"
  elif echo "$line" | grep -qE '\bgit[[:space:]]+commit\b' \
    && echo "$line" | grep -qE -- '-c[[:space:]]+commit\.gpgsign=false'; then
    reason="this disables commit signing via a config override"
  fi
done <<< "$command"

if [ -n "$reason" ]; then
  echo "git-safety-guard blocked this command: $reason. Confirm explicitly with the user before running it, then execute it yourself in a terminal outside Claude Code if they approve." >&2
  exit 2
fi

exit 0
