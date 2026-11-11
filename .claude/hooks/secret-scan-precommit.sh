#!/bin/bash
# PreToolUse hook (matcher: Bash). One job: scan the changes a `git commit`
# is about to record for likely-secret patterns, so a key never lands in
# history because a diff wasn't read closely enough.
#
# What a commit records depends on its flags: plain `git commit` takes the
# index, but `-a/--all`, `-i/--include` and `-o/--only` also take tracked
# working-tree changes that were never staged. Those are scanned too, so the
# most common form (`git commit -am`) is not a way around the scan.
set -euo pipefail

input="$(cat)"

# Fail closed for commits when jq is absent: a silent exit 0 would turn the scan off.
if ! command -v jq >/dev/null 2>&1; then
  if printf '%s' "$input" | grep -qE 'git.*commit'; then
    echo "secret-scan-precommit blocked this commit: jq is not installed, so the command cannot be inspected. Install jq (apt-get install jq) and retry." >&2
    exit 2
  fi
  exit 0
fi

tool_name="$(printf '%s' "$input" | jq -r '.tool_name // empty')"
[ "$tool_name" = "Bash" ] || exit 0

command="$(printf '%s' "$input" | jq -r '.tool_input.command // empty')"
command="$(printf '%s' "$command" | sed -e ':a' -e '/\\$/N; s/\\\n//; ta')"

# Global options git accepts before the verb (see git-safety-guard.sh), so
# `git -C dir commit` is still seen as a commit.
GIT_GLOBAL_OPTS='(-[Cc][[:space:]]+[^[:space:]]+|--(git-dir|work-tree|namespace|exec-path|super-prefix)(=|[[:space:]]+)[^[:space:]]+|--(no-pager|paginate|bare|no-replace-objects|literal-pathspecs|no-optional-locks|no-advice)|-p|-P)'

include_unstaged=0
is_commit=0
while IFS= read -r raw; do
  line="$(printf '%s' "$raw" | sed -E "s/\\bgit(([[:space:]]+${GIT_GLOBAL_OPTS})+)[[:space:]]+/git /g")"
  printf '%s' "$line" | grep -qE '\bgit[[:space:]]+commit\b' || continue
  is_commit=1
  if printf '%s' "$line" | grep -qE -- '(^|[[:space:]])(-[a-zA-Z]*[aio][a-zA-Z]*|--all|--include|--only)([[:space:]]|$)'; then
    include_unstaged=1
  fi
done <<< "$command"
[ "$is_commit" = 1 ] || exit 0

cd "${CLAUDE_PROJECT_DIR:-.}"
excludes=(-- . ':!*.lock' ':!package-lock.json')
diff="$(git diff --cached "${excludes[@]}" 2>/dev/null || true)"
if [ "$include_unstaged" = 1 ]; then
  # Staged + unstaged tracked changes vs HEAD (fails harmlessly before the first commit).
  diff+=$'\n'"$(git diff HEAD "${excludes[@]}" 2>/dev/null || true)"
fi
[ -n "${diff//[$'\n']/}" ] || exit 0

# Anthropic / OpenAI / AWS / GitHub / Slack / Stripe / Google credentials and PEM private-key blocks.
secret_regex='sk-ant-[A-Za-z0-9_-]{20,}|sk-proj-[A-Za-z0-9_-]{20,}|sk-[A-Za-z0-9]{48}|AKIA[0-9A-Z]{16}|-----BEGIN[A-Z ]*PRIVATE KEY-----|gh[pousr]_[A-Za-z0-9]{36}|github_pat_[A-Za-z0-9_]{22,}|xox[baprs]-[A-Za-z0-9-]{10,}|[sr]k_live_[A-Za-z0-9]{20,}|AIza[0-9A-Za-z_-]{35}'

hit="$(printf '%s' "$diff" | grep -nE "$secret_regex" | head -5 || true)"

if [ -n "$hit" ]; then
  echo "secret-scan-precommit blocked this commit: the changes match a likely-secret pattern (Anthropic/OpenAI/AWS/GitHub/Slack/Stripe/Google key or a PEM private-key block). Review before committing:" >&2
  echo "$hit" >&2
  exit 2
fi

exit 0
