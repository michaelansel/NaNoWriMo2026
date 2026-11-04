#!/bin/bash
# Move the Actions-written state in ai/ between a workspace and the ai-state branch (ADR-028).
# This is the only code that fetches or pushes that state.
#
#   scripts/ai-state.sh [--repo <dir>] fetch
#       Fetch the tip of origin/ai-state, check it holds ai/, check it out as a detached
#       worktree <repo>/.ai-state and make <repo>/ai a link into it. Safe to re-run on a
#       reused workspace. Prints "ai/ state: ai-state@<sha7>" (and to the step summary).
#   scripts/ai-state.sh [--repo <dir>] push "<commit subject>" [<path under ai/>...]
#       GitHub Actions only, after fetch: commit the named files (default: all of ai/) in
#       .ai-state and push them to ai-state. A rejected push is rebased once and retried;
#       a second rejection exits 1. Nothing changed: says so and pushes nothing.
#
# <repo> defaults to the repository this script is in. Every failure prints ::error:: and
# exits non-zero; nothing here falls back to another copy of the state.

set -euo pipefail

BRANCH=ai-state
WORKTREE=.ai-state

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO="$(cd "$SCRIPT_DIR/.." && pwd)"

fail() {
  echo "::error::ai/ state: $1"
  if [ -n "${GITHUB_STEP_SUMMARY:-}" ]; then
    echo "ai/ state: $1" >> "$GITHUB_STEP_SUMMARY"
  fi
  exit 1
}

note() {
  echo "$1"
  if [ -n "${GITHUB_STEP_SUMMARY:-}" ]; then
    echo "$1" >> "$GITHUB_STEP_SUMMARY"
  fi
}

usage() {
  echo "usage: $0 [--repo <dir>] fetch | push \"<commit subject>\" [<path under ai/>...]" >&2
  exit 2
}

fetch_state() {
  cd "$REPO"
  if ! git fetch --no-tags --depth=1 origin "+refs/heads/$BRANCH:refs/remotes/origin/$BRANCH"; then
    fail "could not fetch the $BRANCH branch from origin; nothing that reads ai/ can run without it"
  fi
  if ! git cat-file -e "refs/remotes/origin/$BRANCH:ai" 2>/dev/null; then
    fail "origin/$BRANCH has no ai/ directory; nothing that reads ai/ can run without it"
  fi
  local sha
  sha="$(git rev-parse "refs/remotes/origin/$BRANCH")"

  if [ -d ai ] && [ ! -L ai ] && [ "${GITHUB_ACTIONS:-}" != true ]; then
    # Locally, a real ai/ directory is someone's copy; never delete it from under them.
    fail "$REPO/ai is a directory, not the link this script makes; move it away (the state's home is the $BRANCH branch) and run fetch again"
  fi

  # A reused workspace may hold an earlier worktree, or metadata for one that was cleaned.
  rm -rf "$WORKTREE"
  git worktree prune
  git worktree add --detach --quiet "$WORKTREE" "$sha"

  # In CI the checkout may track ai/ (a branch made before ADR-028); the link replaces it.
  rm -rf ai
  ln -s "$WORKTREE/ai" ai
  if [ ! -d ai ]; then
    fail "$REPO/ai does not resolve to $WORKTREE/ai"
  fi
  note "ai/ state: $BRANCH@${sha::7}"
}

push_state() {
  if [ "$#" -eq 0 ] || [ -z "$1" ]; then
    usage
  fi
  local subject="$1"
  shift
  if [ "${GITHUB_ACTIONS:-}" != true ]; then
    fail "push runs only in GitHub Actions; never push to $BRANCH by hand"
  fi
  if [ ! -d "$REPO/$WORKTREE/ai" ]; then
    fail "$REPO/$WORKTREE is missing; run fetch before push"
  fi
  local paths=("$@")
  if [ "${#paths[@]}" -eq 0 ]; then
    paths=(ai)
  fi
  local path
  for path in "${paths[@]}"; do
    case "$path" in
      ai | ai/*) ;;
      *) fail "push takes paths under ai/, not '$path'" ;;
    esac
  done

  cd "$REPO/$WORKTREE"
  git add -A -- "${paths[@]}"
  if git diff --cached --quiet; then
    note "ai/ state: ${paths[*]} unchanged; nothing pushed to $BRANCH."
    return 0
  fi
  git -c user.name="github-actions[bot]" \
    -c user.email="41898282+github-actions[bot]@users.noreply.github.com" \
    commit --quiet -m "$subject"
  if ! git push origin "HEAD:refs/heads/$BRANCH"; then
    echo "Push to $BRANCH rejected; rebasing once onto its new tip"
    if ! git fetch --no-tags origin "+refs/heads/$BRANCH:refs/remotes/origin/$BRANCH"; then
      fail "the push to $BRANCH was rejected and the branch could not be fetched again; nothing was saved"
    fi
    if ! git -c user.name="github-actions[bot]" \
      -c user.email="41898282+github-actions[bot]@users.noreply.github.com" \
      rebase --quiet "refs/remotes/origin/$BRANCH"; then
      git rebase --abort
      fail "the push to $BRANCH was rejected and \"$subject\" does not rebase onto its new tip; nothing was saved"
    fi
    if ! git push origin "HEAD:refs/heads/$BRANCH"; then
      fail "the push to $BRANCH was rejected twice; nothing was saved"
    fi
  fi
  note "ai/ state: pushed \"$subject\" to $BRANCH@$(git rev-parse --short=7 HEAD)."
}

if [ "${1:-}" = --repo ]; then
  [ -n "${2:-}" ] || usage
  REPO="$(cd "$2" && pwd)"
  shift 2
fi

case "${1:-}" in
  fetch)
    [ "$#" -eq 1 ] || usage
    fetch_state
    ;;
  push)
    shift
    push_state "$@"
    ;;
  *) usage ;;
esac
