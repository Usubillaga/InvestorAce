# Consistent publication when main advances

**Goal:** Fix the rejected history push from run 40081849857 without overwriting remote commits or publishing a report built from stale source/data.

**Cause:** PR74's build started at d21ab49; PR73 advanced main to 6297b73 during the build. The Pages concurrency group does not lock PR merges. The build succeeded, but its unconditional push failed before Pages deployment.

**Architecture:** A stdlib publisher builds in an owned detached temporary worktree of the fetched main. It runs the existing install/test/build commands, commits only generated history/comparison, and attempts an ordinary fast-forward push. If main advanced, it discards only that owned attempt and rebuilds from the new head, at most three times. Other push failures stop with their error. Only the accepted attempt's public directory is made available to Pages.

**Constraints:** No force push, no rebase of stale generated output, no changes to the score/valuation framework, no reset of a user's checkout, no deployment on failed/exhausted publication. Existing report/evidence verification stays enabled. Human merges and non-Pages writers remain supported.

**Review focus:** Race after fetch/build, source changes during retry, remote rejection without advancement, finite retry exhaustion, failed builds, existing output protection, accepted-but-lost push response, and ownership of temporary worktrees/artifacts. Preserve every concurrent commit and bind the artifact to the accepted generation.

## Task 1: Publisher and deployment integration

Files: `publish_build.py`, `test_publish_build.py`, `.github/workflows/deploy.yml`, `README.md`.

Interfaces: workflow → publisher → existing build commands → git history push → accepted public artifact → existing Pages upload/deploy.

- [x] Add real-Git regression fixtures with a bare remote and concurrent writer. Run RED before implementation.
- [x] Implement bounded fresh-worktree rebuild/publication; integrate it into the deployment job.
- [x] Run publisher tests, full offline tests, lint, JS contracts and workbook reproduction; inspect the diff and obtain one fresh whole-branch review.
- [ ] Open a tested PR for the user to merge. Do not merge or retry the old SHA-based failed run as a substitute for the fix.

## Progress

- Evidence: the failed job completed Build successfully; Commit history failed; all upload/deploy steps were skipped. PR73 changed only the dated Claude briefing, but a future collision could change model code, so a plain rebase is insufficient.

- RED: missing publisher reproduced the absent feature; permission-while-main-advanced regression then failed with two builds instead of one.
- Mutation: removing the retry caused the real concurrent-writer regression to fail; restored implementation passes all nine publisher tests.
- Full validation: 363 Python tests passed (29.968s), 19 JavaScript contracts passed, lint/diff checks passed and WACC workbook reproduced. No financial/model source changed.
- Independent whole-branch review: no critical, important or minor findings; declined-to-judge list empty. Current checkout@v6 credential support for temporary worktrees was checked against the official action source/changelog. Live deployment will occur only after the user merges the PR.
