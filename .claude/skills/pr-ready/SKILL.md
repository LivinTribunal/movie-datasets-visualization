---
name: pr-ready
description: >
  Pre-push self-review. Runs the checks CI will run on what you touched, reviews
  your own diff with the grain skill and applies what it finds, re-runs the
  scoped tests to prove those edits changed nothing, checks the repo's data and
  docs rules, then drafts or syncs the PR body. Use before `git push` or `gh pr
  create`, or when the user says "make this PR-ready", "self-review",
  "pr-ready", "before pushing", or "get this merge-ready".
---

# PR-ready

Bring your own diff to the state `review-proof` would have demanded, before
anyone else reads it. Make a todo list first.

The diff is `git diff $(git merge-base HEAD main)...HEAD` plus uncommitted work.

## Phase 1: scoped checks

Run what CI runs, limited to what you touched:

```bash
# pipeline
cd pipeline && uv run ruff check <touched .py files> && uv run ruff format --check <touched .py files>
cd pipeline && uv run pytest <test files covering what you changed> -q
# app
cd app && npx eslint <touched files> && npx tsc --noEmit
cd app && npx vitest run <test files covering what you changed>
```

If the export schema changed, also run `uv run --project pipeline movies validate`.
Do not run the full suite or `make data`. CI runs the suite, and `make data`
hits external sites.

A failing check is fixed at the root. Never silence it (`# noqa`,
`# type: ignore`, `eslint-disable`, `@ts-expect-error`, a loosened assertion).

## Phase 2: review your own diff

Load the `grain` skill and read the diff against it. Every added line has to
justify itself. Before keeping any new function, file or dependency, climb the
ladder and stop at the first rung that holds:

1. Does it need to exist at all?
2. Does something already do it? Grep for the transformation, not the name.
   polars, D3 and the stdlib count.
3. Can an existing function, component or stage be extended?
4. Can it be one line at the call site?
5. Only then: the smallest new thing that works, shaped like its nearest
   sibling.

Minimal never means skipping a test the change needs, dropping the null
handling, or leaving transformed data unlabelled.

Apply what you find.

## Phase 3: re-gate

Re-run the Phase 1 commands for every file Phase 2 edited. A cleanup that
turns a test red was not behaviour-neutral. Revert it.

## Phase 4: repo rules

Check each that applies and fix what is missing:

- `git status --short` shows nothing from `data/raw/`, `data/cache/`,
  `data/interim/`, no `.env`, no course PDFs or IS pages.
- A new or changed data source is reflected in `DATASETS.md`.
- A decision that is not obvious has an entry in `docs/decisions.md`.
- An export schema change updated `app/src/lib/types.ts` and the validator in
  the same diff.
- Transformed values (converted, inflation-adjusted, fuzzy-matched) carry a
  flag the app can show.
- `AGENTS.md` "Commands" still matches the Makefile.

## Phase 5: PR body

Load `unslop` and draft, or sync the open PR's body with
`gh pr edit <num> --body-file <file>`:

```
## Executive summary
<two plain sentences: what changed, why it matters>

## What changed
<per area, the facts a reviewer needs; data counts where they matter>

## Checks
<what you ran and the result>
```

If the change diverges from what the open PR's body says, update the body
before pushing. Commit messages start with a lowercase verb (`add wikidata
crosswalk`).

Report the result in a few lines: checks run, what Phase 2 changed, whether the
PR body was synced.
