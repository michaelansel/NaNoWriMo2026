# ADR-028: `main` is protected by a ruleset, and `ai/` state lives on the `ai-state` branch

Status: Accepted

Supersedes: ADR-014 in part (`ai/` and its writers on `main`), ADR-020 in part (the cache committed to `main` and read from the checkout or the merge ref), ADR-022 in part (dismissals and outcomes appended on `main`), ADR-025 in part (the `ai/` writers' target branch) and ADR-026 in part (the preview's cache taken from the merge ref).

## Context

A writer saved a prose file straight to `main` from the web UI, so it got no `format` job, no
Build comment and no AI review. The repository had no ruleset. On a personal-account repository
GitHub refuses the GitHub Actions app as a ruleset bypass actor, so a ruleset that requires pull
requests on `main` would also refuse `bible-extract` and `/dismiss`, which push `ai/` to `main`
with `GITHUB_TOKEN`. ADR-014 and ADR-020 already named the answer: move `ai/` to a data branch.
The season is live, so the move must not break a pull request or a merge at any point.

## Decision

### The `main` ruleset

One repository ruleset on `~DEFAULT_BRANCH`, enforcement `active`:

- **Rules:** `deletion`; `non_fast_forward`; `pull_request` with 0 approvals, every merge method,
  and no stale-review, code-owner, last-push or thread-resolution requirement;
  `required_status_checks`, `strict_required_status_checks_policy: false`.
- **Required checks**, each pinned to the GitHub Actions app (integration 15368): `build` and
  `test` (`build-and-deploy.yml`) and `intent` (`intent.yml`). They run on every pull request to
  `main` and on the format commit's head through the ADR-025 dispatch. `build` never reports
  skipped on a PR head: a failed `context` fails it (ADR-025).
- **Not required:** `format`, `Structure` (report-only, ADR-018), `ai-review`,
  `ai-review-not-run`, the editor and `Story Bible preview` checks (inference-dependent).
- **Not strict:** a strict policy would make every open PR out of date after every merge.
- **Bypass:** only the repository admin role (RepositoryRole 5), mode `always`. No automation
  bypasses it, so any workflow push to `main` is refused and fails red.
- **Check names are unique across workflows.** A job that does not produce a required check is
  not named `build`, `test` or `intent` (`build (command)`, `build (check-all)`).
- The ruleset lives in repository settings; this ADR is its record.

### The `ai-state` branch

- **Shape.** An orphan branch `ai-state` whose tree is only `ai/` (`story-bible-cache.json`,
  `dismissals.jsonl`, `outcomes.jsonl`; same file formats and schemas). It is the only home of
  that state. `main` tracks no `ai/`; `.gitignore` lists `/ai/` and `/.ai-state/`.
- **Its own ruleset:** `deletion` and `non_fast_forward` on `ai-state`, admin bypass only. Actions
  pushes are fast-forward, so they need no bypass.
- **One fetch, one push.** `scripts/ai-state.sh` is the only code that moves state:
  - `fetch`: `git fetch --depth=1 origin ai-state`, fail unless `origin/ai-state:ai` exists, then
    replace `<repo>/ai` with a link into a detached worktree `<repo>/.ai-state` (idempotent on a
    reused self-hosted workspace), and print `ai/ state: ai-state@<sha7>` to the log and summary.
  - `push "<subject>"` (only under `GITHUB_ACTIONS`): commit the changed files in `.ai-state`,
    push `HEAD:ai-state`; on rejection `git pull --rebase` once and push again, else exit 1.
  - `.github/actions/ai-state` wraps `fetch`; every CI job that reads or writes `ai/` calls it
    right after its checkout. A job whose workspace is pull-request code (`build (command)`)
    takes the action from a default-branch copy, so branches older than the move work.
- **nanoif does not change.** It keeps reading and writing `<repo>/ai/...`. A missing cache still
  renders the placeholder and a missing dismissals file still means none: true on a fresh
  season, in tests and in eval scratch repositories. Loudness lives in the fetch: an unreachable
  branch or a branch without `ai/` fails the step with `::error::`, and `build-story` and
  `ai-review` fail when `.ai-state` is absent in CI, so a forgotten fetch cannot render an empty
  Bible or resurface dismissed findings.
- **Readers:** `build` (PR and `main`), `ai-review` (dismissals and the preview's cache), deploy
  (when there is no `bible-cache` artifact), `/check-continuity` (`build (command)`,
  `ai-review`), `/extract-story-bible` (cache from `ai-state`, not the merge ref), `build
  (check-all)` and `check-all`. Local development runs `scripts/ai-state.sh fetch` once.
- **Writers** (`contents: write`, pushing only to `ai-state`): `bible-extract`
  (`chore: update story bible cache`, still in the `pages` group, still reading `src/` from
  `main` HEAD), `/dismiss` (group `ai-state-main`), and `pr-closed` when built. A push rejected
  twice fails the job; `/dismiss` then replies on the PR.
- **Migration**, once, by the admin, before the writers move: a commit on `ai-state` whose `ai/`
  tree is byte-identical to `main`'s (`git commit-tree` of `origin/main:ai`). The PR that moves
  readers and writers also removes `ai/` from `main`; it merges only when no `main` run or
  `/dismiss` is in flight, after re-syncing any `ai/` change on `main` since the snapshot.

## Consequences

### Positive

- Every prose change reaches `main` through a PR, and no automation can write `main`.
- Every reader sees the newest state, not the copy its branch or merge ref happened to carry.
- `ai/` commits no longer interleave with prose history on `main`.

### Negative

- Every reading job depends on one more fetch; when it fails, the PR's `build` is red and merges
  wait. That is loud, and the branch ruleset makes deletion the admin's act only.
- `ai/` history before the move stays in `main`'s log; `ai-state` starts at the snapshot.
- An admin push to `main` skips every check; the `push` runs on `main` are its only signal.
- If the format job's dispatch fails, the new head's required checks wait as "Expected" until the
  next push (ADR-025).

## Alternatives Considered

1. **Actions as bypass actor**: rejected by GitHub on a personal-account repository (422).
2. **Deploy-key bypass for the `ai/` writers**: works, but adds a secret against ADR-014's "no
   secrets"; the fallback if the data branch hits a wall.
3. **Readers fall back to `main`'s `ai/`**: two homes, and the fallback is stale by design.
4. **Teach nanoif to fetch the branch**: puts git remotes in library code; a workspace link keeps
   nanoif and its tests unchanged.
5. **Require `Structure` or the AI checks**: an exe or spend-cap outage would block every merge.

## References

- ADR-014, ADR-018, ADR-020, ADR-021, ADR-022, ADR-025, ADR-026
- `.github/workflows/{build-and-deploy,intent,ai-command,ai-maintenance}.yml`, `.github/actions/`
