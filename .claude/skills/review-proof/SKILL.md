---
name: review-proof
description: >
  Review a PR (or the current branch diff), prove each correctness finding with
  a real failing test or runnable reproduction, drop every finding that will
  not reproduce, run a grain pass for excess and structural fit, then fix
  everything that survived and keep each proof as a regression test. Pass
  --report-only to change nothing, or --comment to post the report on the PR.
  Use when reviewing a teammate's PR or your own branch and you want findings
  you can trust, fixed. Triggers: "/review-proof", "review and prove", "review
  the PR with tests", "review and fix", "proven review".
---

# Review-proof

A reviewer that does not trust itself, and then fixes what it proved. Every
correctness finding has to reproduce as a failing test or a runnable script, or
it is dropped as a false positive. That is what makes the fix step safe to
automate: a finding exists only because a test went red, and it counts as fixed
only when the same test goes green.

This is the proving complement to the built-in `/code-review`, which finds
issues but does not prove them.

## Arguments

- `review-proof`: auto-detect the target (Phase 0).
- `review-proof <PR#>`: review that PR.
- `--diff`: review the local branch diff even if an open PR exists.
- `--report-only`: stop after Phase 3 and report. Changes nothing.
- `--comment`: post the report to the PR (PR targets only).

Make a todo list first.

## Phase 0: resolve the target

1. A `<PR#>` argument wins.
2. Else `gh pr view --json number,state,isDraft,url,headRefName` for the
   current branch. An open PR is the target (unless `--diff`); get its diff with
   `gh pr diff <num>`.
3. Else the target is the local branch: `git diff $(git merge-base HEAD main)...HEAD`
   plus `git diff` and `git diff --cached`.

The diff is the review scope. Findings must sit on lines this change touched.

Read the intended contract before reviewing the code: the PR body, the linked
issue, and the parts of `docs/PLAN.md`, `docs/decisions.md` and `AGENTS.md` the
change touches. Write down what must be true when the change works,
independently of how the diff does it. Phase 2 proves against that. Without it
the review can only check the code against itself.

## Phase 1: correctness review

Launch three Sonnet agents in one message, in the foreground, and wait for all
of them. Each returns a list of issues with the reason each was flagged.

- **a. Bug scan.** Read only the diff. Real bugs only, no nitpicks.
- **b. Context.** Read the code around the change, `git log`/`git blame` of the
  touched lines, and the comments in the touched files. Flag changes that
  contradict them.
- **c. Integration.** For every call into something the diff does not define
  (a polars expression on another stage's output, a parquet another stage
  writes, the zustand store, a D3 scale, an external site), open the other side
  and check the assumption holds. Is it the right file, column or store slice?
  Does it behave as assumed (nulls, dtypes, sort order, units, time zones)?
  This lens catches the bugs that do not crash.

Then run the deterministic lenses yourself. Each is proven by listing what is
missing, so a finding here joins the proven set directly and never goes to
Phase 2.

- **Data conventions** (`AGENTS.md`). Missing is null, never `0`, `-1` or
  `""`. Money is never imputed and every money column has its `*_src` column.
  Ratings land in `_100` columns. Countries go through
  `data/reference/countries.csv`, never ad-hoc name matching. Genre shares use
  `genre_weight = 1/n`. Name each line that breaks a rule.
- **Transformed data is labelled.** The lecture rule: imputed, converted,
  inflation-adjusted or fuzzy-matched values must be shown as such in the app.
  A new derived value with no flag column, or an app view that renders it
  without saying so, is a finding.
- **Export schema parity.** If the diff changes what `movies export` writes,
  `app/src/lib/types.ts` and the validator must change in the same diff. List
  each field that exists on one side only.
- **Linked views.** Shared filter and selection state lives only in the
  zustand store. A view that reads another view's state directly, or keeps a
  local copy of shared state, is a finding.
- **Scraping rules.** A scraper or downloader must cache first under
  `data/cache/`, parse only from the cache, keep at most one request per second
  per host, send the descriptive User-Agent, and skip IDs already cached.
- **Committed files.** Nothing under `data/raw/`, `data/cache/`,
  `data/interim/`, no `.env`, no course PDFs or IS pages. Never edit
  `app/public/data/` by hand.
- **Private helpers.** List every `_`-prefixed function the diff adds or
  changes, by name. For each: is it reachable, does it have one trivial caller,
  does it swallow distinct outcomes into one (`except: pass`, `or {}`, a
  `None` meaning several things), does a public helper already do it?

Not findings: pre-existing issues, lint and type errors (CI runs ruff, eslint
and tsc), generic "needs more tests", intended behaviour changes the PR is
about, and lines the PR did not touch.

Note scope drift too, but never block on it. What did the PR do that the
issue did not ask for, and what did the issue ask for that the diff does not do?

Structural, placement and duplication findings are not correctness bugs. They
go to Phase 3.

## Phase 2: prove each finding

For each correctness finding, spawn a Sonnet agent with `isolation: "worktree"`,
all in one message, in the foreground. Start a proof as soon as its finding is
flagged. Two lenses reaching the same root cause get one proof, not two.

Each agent makes the bug reproduce or drops it:

- **Pipeline** (`pipeline/`): a pytest test under `pipeline/tests/`, mirroring
  the nearest existing test and using small fixtures in `tests/fixtures/`.
  Run `cd pipeline && uv run pytest <path> -x -q`. No network, no raw data.
- **App** (`app/`): a vitest test next to the nearest existing one. Run
  `cd app && npx vitest run <path>`.
- **Visual behaviour** that a unit test cannot reach: a runnable repro against
  `make dev`. If that is not practical, the finding is not provable here. Drop
  it and name the risk.

A test that mocks the very thing in question and then asserts it was called
proves nothing. When the finding is about how two stages or two views connect,
the proof must run the real other side, or a fixture that reproduces its real
output.

Each agent returns `{finding, file, line, status: proven|dropped, test_path,
test_source, command, output, note}`. Paste the full test source: the worktree
is thrown away and Phase 4 recreates the test from it.

## Phase 3: grain pass

Load the `grain` skill and review the same diff against it. Report what to cut
(the laziest version that works, stdlib or polars or D3 before custom code) and
what diverges from the repo's existing shape, each naming the exemplar to match
or the shorter code that replaces it. A cut that would break consistency with
several siblings stays, and say so, so the next reviewer does not propose it
again.

## Phase 4: fix what survived

Skip with `--report-only`.

Correctness fixes first, then grain fixes. Per correctness finding:

1. Recreate the captured test at its path and run it. It must go red first. If
   it is green, mark the finding `no-change-needed`. Never fix what you could
   not re-break.
2. Fix the code with the smallest change at the root cause.
3. Re-run. Red must now be green. If not, retry once, then escalate.
4. Keep the test as a regression test, folded into the nearest existing test
   file when one covers the unit.

Grain fixes align to the named exemplar or apply the named cut. A grain fix
that turns a test red was not behaviour-neutral. Revert it.

Rules for every fix:

- Never silence a gate: no `# noqa`, `# type: ignore`, `eslint-disable`,
  `@ts-expect-error`, no loosened assertion, no CI edit.
- Escalate instead of guessing when the right behaviour is a design decision
  (a chart encoding, a data rule in `docs/decisions.md`) or the spec is
  ambiguous. Carry the one question a human must answer.
- Re-run the proof tests and the test files covering what you touched. Do not
  run the full suite; CI does that.

Do not commit or push unless asked.

## Phase 5: report

Load `unslop` before drafting. Keep each finding's `file:line`, command and
test path verbatim.

```
### Review-proof: <PR #N | branch <name>>

**Proven (N)**, each reproduced by a test, then fixed:
1. <what is wrong>. <file>:L<line>. fixed | escalated | no-change-needed
   Proof: `<command>` red: <failing result>, green after the fix
   Regression test: <test_path>

**Dropped during proof (M)**, did not reproduce:
- <finding>. <one-line reason>

**Grain**:
- <finding>. fixed (aligned to <exemplar> | <cut applied>) | kept (<why>)

**Escalated (K)**:
- <finding>. <the question to answer>

**Checks:** <scoped tests run and their result>
```

With nothing proven and a clean grain pass, say:
`No reproducible correctness issues; lean and with the grain. Nothing to fix.`

`--comment`: post with `gh pr comment <num> --body-file <file>`, linking each
cited line with a full-SHA permalink. No AI attribution line in review comments.
