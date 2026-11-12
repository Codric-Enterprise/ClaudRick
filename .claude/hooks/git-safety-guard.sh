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
#
# Two things keep that line-based matching honest:
#   * Each line is normalised first, so `git -C dir push`, `git -c k=v reset
#     --hard` and `git --no-pager clean -f` read as `git push`, `git reset
#     --hard`, … — global options between `git` and the verb used to slip past.
#   * Short flags are matched as clusters (`-fu`, `-nm`), long flags exactly
#     (`--force` is not `--force-with-lease`), and every check runs
#     independently, so `git push ok && git reset --hard` is still caught.
set -euo pipefail

input="$(cat)"

# Fail closed for git commands when jq is absent: without it the command can't
# be read, and a silent exit 0 would turn the whole guard off. Non-git commands
# pass, so a missing jq doesn't brick every Bash call.
if ! command -v jq >/dev/null 2>&1; then
  if printf '%s' "$input" | grep -q 'git'; then
    echo "git-safety-guard blocked this command: jq is not installed, so the command cannot be inspected. Install jq (apt-get install jq) and retry." >&2
    exit 2
  fi
  exit 0
fi

tool_name="$(printf '%s' "$input" | jq -r '.tool_name // empty')"
[ "$tool_name" = "Bash" ] || exit 0

command="$(printf '%s' "$input" | jq -r '.tool_input.command // empty')"
[ -n "$command" ] || exit 0

# Join backslash-continued lines, so `git push \<newline> --force` is one command.
command="$(printf '%s' "$command" | sed -e ':a' -e '/\\$/N; s/\\\n//; ta')"

# Global options git accepts before the verb; value-taking ones consume the next word.
GIT_GLOBAL_OPTS='(-[Cc][[:space:]]+[^[:space:]]+|--(git-dir|work-tree|namespace|exec-path|super-prefix)(=|[[:space:]]+)[^[:space:]]+|--(no-pager|paginate|bare|no-replace-objects|literal-pathspecs|no-optional-locks|no-advice)|-p|-P)'

# has_short <line> <letter>: a short-flag cluster containing <letter> (-f, -fu, -nf).
has_short() { printf '%s' "$1" | grep -qE -- "(^|[[:space:]])-[a-zA-Z]*$2[a-zA-Z]*([[:space:]]|\$)"; }
# has_long <line> <flag>: the exact long flag, with or without =value (so
# --force does not match --force-with-lease).
has_long() { printf '%s' "$1" | grep -qE -- "(^|[[:space:]])--$2([[:space:]=]|\$)"; }
# is_git <line> <verb-regex>
is_git() { printf '%s' "$1" | grep -qE -- "\\bgit[[:space:]]+($2)\\b"; }

reason=""

# check_line <raw-line>: sets $reason (and returns) at the first dangerous pattern.
check_line() {
  local raw="$1" line
  line="$(printf '%s' "$raw" | sed -E "s/\\bgit(([[:space:]]+${GIT_GLOBAL_OPTS})+)[[:space:]]+/git /g")"

  if is_git "$line" push; then
    if has_long "$line" force || has_short "$line" f; then
      reason="git push --force (even alongside --force-with-lease) can overwrite remote history other people rely on"
      return
    fi
    if has_long "$line" mirror; then
      reason="git push --mirror overwrites or deletes every ref on the remote"
      return
    fi
    if has_long "$line" delete || has_short "$line" d \
      || printf '%s' "$line" | grep -qE -- '(^|[[:space:]]):[^[:space:]]'; then
      reason="this deletes a remote branch or tag"
      return
    fi
    if printf '%s' "$line" | grep -qE -- '(^|[[:space:]])\+[^[:space:]]' \
      && ! has_long "$line" force-with-lease; then
      reason="a +refspec force-pushes that ref without --force-with-lease"
      return
    fi
    if has_long "$line" no-verify; then
      reason="this skips a pre-push hook"
      return
    fi
  fi

  if is_git "$line" reset && has_long "$line" hard; then
    reason="git reset --hard discards uncommitted work irreversibly"
    return
  fi

  if is_git "$line" clean && { has_short "$line" f || has_long "$line" force; }; then
    reason="git clean -f permanently deletes untracked files"
    return
  fi

  if is_git "$line" branch \
    && { has_short "$line" D \
      || { { has_short "$line" d || has_long "$line" delete; } \
        && { has_short "$line" f || has_long "$line" force; }; }; }; then
    reason="git branch -D (or -d with --force) deletes a branch, losing unmerged commits"
    return
  fi

  if is_git "$line" checkout && { has_short "$line" f || has_long "$line" force; }; then
    reason="git checkout -f discards local modifications"
    return
  fi

  # Pathspec "." discards the whole tree. `git restore --staged .` only unstages, so allow it.
  if is_git "$line" 'checkout|restore' \
    && printf '%s' "$line" | grep -qE -- '(^|[[:space:]])\.([[:space:]]|$)' \
    && ! { is_git "$line" restore && has_long "$line" staged \
      && ! has_long "$line" worktree && ! has_short "$line" W; }; then
    reason="this discards all uncommitted changes in the working tree"
    return
  fi

  if is_git "$line" 'commit|merge|rebase|cherry-pick' && has_long "$line" no-verify; then
    reason="this skips a commit hook"
    return
  fi

  if is_git "$line" commit && has_short "$line" n; then
    reason="git commit -n is --no-verify and skips the commit hooks"
    return
  fi

  if is_git "$line" 'commit|push' && has_long "$line" no-gpg-sign; then
    reason="this skips a signature check"
    return
  fi

  if is_git "$line" commit \
    && printf '%s' "$raw" | grep -qE -- '-c[[:space:]]+commit\.gpgsign=false'; then
    reason="this disables commit signing via a config override"
    return
  fi
}

while IFS= read -r raw_line; do
  check_line "$raw_line"
  [ -z "$reason" ] || break
done <<< "$command"

if [ -n "$reason" ]; then
  echo "git-safety-guard blocked this command: $reason. Confirm explicitly with the user before running it, then execute it yourself in a terminal outside Claude Code if they approve." >&2
  exit 2
fi

exit 0
