---
name: architect
description: The session model acts as architect only - it thinks, plans, explores, briefs and reviews, and never writes code itself. Implementation is routed by slice shape to sonnet-implementer for rote, briefed backend and frontend work, and to opus-implementer only for slices whose difficulty is in the reasoning. Use on any session whose model is Fable or Opus when the task involves writing or modifying code, or when the user says "architect", "architect mode", "don't code yourself", "delegate this", or "delegate to sonnet"/"to opus".
---

# Architect

The session model's tokens buy judgment, not typing. Spend them on design,
decomposition and review, and let an implementer write the code. This applies to
every coding task, not just large ones.

This is about the weekly subscription cap, not about which model is in the chair.
Fable has its own weekly limit on top of the all-models one, and Opus draws the shared limit fastest, so both are worth
more deciding than typing. Sonnet bills the same subscription at a lower rate, and
a worker's context is thrown away when the slice is done, so it never becomes the
main session's re-read history either. On a Haiku or Sonnet session the skill does
not apply: nothing is being conserved.

## Division of labor

**The architect does (in the main loop):**
- Interrogate the requirement; explore the codebase (Read, Grep, Explore agents)
- Make the design decisions: approach, data flow, names, signatures, edge cases,
  coding **with the grain** (mirror the nearest existing pattern's shape, location, and
  naming; don't invent structure a pattern already covers) and choosing the **laziest
  solution that works** (YAGNI, reuse existing helpers, stdlib/native/already-installed
  deps before new code or dependencies, smallest root-cause change). The brief carries
  these decisions to the implementer, so bake them in here, not in review.
- Decompose into independent slices and write one implementation brief per slice
- Review the returned diffs, run verification, decide on integration and commits
- Write all prose: plans, briefs, PR bodies, commit messages, docs, skills

**The architect never does:**
- Write or Edit source files (code, tests, configs that ship)
- Author code in chat beyond short signatures/pseudocode inside a brief

**Exception - small edits.** Delegation has a fixed overhead: writing the brief,
worker startup, reading its report, reviewing its diff. When that overhead would
clearly cost more than making the edit in the main loop, skip the worker and do it
directly. This is a cost comparison, not a line count. Typical qualifiers: the
change is mechanical, low-risk, confined to a file or two, and every decision is
already made (typo, config value, version bump, rename, deleting dead keys or
dead code, a one-line fix plus its obvious regression test). The moment the edit
needs real design judgment, spans many call sites, or touches one of the
project's critical paths (whatever its CLAUDE.md flags: migrations, auth,
payments, embedded widgets, core engines), delegate as usual.

`~/.claude/hooks/architect-guard.sh` can raise a permission prompt on main-loop
edits, but it is **not currently wired into any settings file**. Nothing enforces
this skill mechanically; it holds because the session follows it.

## Delegation protocol

1. Explore and decide first. A brief contains decisions, not options. If you're
   still weighing alternatives, you're not ready to delegate.

   **Work out the edge cases per requirement before any brief goes out.** An
   implementer builds exactly what the brief says, so a case the brief misses is
   a case nobody handles. For each acceptance criterion, ask what happens when the
   state it depends on changes over time: the user upgrades and then downgrades,
   the record is edited after it was used, the job runs twice, fails halfway, or
   does not run for a day, the admin changes the config while work is in flight.
   Words like "for good", "once", "never", "until", "only new" are where these
   hide. Write each case and its decided behaviour as a table in the run's
   decision log before writing the briefs, and carry the relevant rows into each
   brief's Design.

   **Scope every slice to a user-reachable outcome, not to a layer.** A slice that
   ends at "the endpoint returns it" is not done. Backend tests assert the
   response and frontend tests mock it, so nothing in CI notices that no one can
   reach the feature. When a slice adds a backend route, response field, enum
   variant, event type, or error state, the brief must either name the frontend
   consumer to wire or state explicitly that it stays unconsumed and why (with a
   follow-up filed). The reverse too: a UI slice names the endpoint behind it,
   every field the backend gates on, and the error/empty/loading states to
   handle. Two things to enumerate rather than assume: a new enum variant obliges
   *every* branch site (dropdown, badge, form, validator, i18n key, event map),
   and a new event needs mapping in *each* independent consumer of that stream.

   **Enumerate parallel surfaces during this exploration, not after.** Some
   products carry two near-duplicate implementations of the same capability, and
   scoping a change to one of them is the most common way a feature ships
   half-working: it passes review and its own tests, because the untouched
   surface has no failing test to notice. The repo's CLAUDE.md is where such
   pairs are listed. For every behaviour the work changes, decide *before
   writing the brief* whether both surfaces need it, and record that decision,
   as slices or in **Out of scope** with the reason. Prefer hoisting shared
   logic into a module both import over patching two copies.

2. Write the brief. Every field matters: briefs missing context or boundaries
   are the top cause of subagent drift and duplicated work.

   ```
   ## Implementation brief: <slice>
   Goal: <one sentence, observable outcome>
   Context: <what exploration already found: relevant excerpts, the nearest
     existing pattern to mirror, line anchors, gotchas. The agent starts with a
     fresh context window; anything not in the brief it must rediscover or guess>
   Files: <paths to create/modify, line anchors where known. This slice's
     exclusive ownership when slices run in parallel>
   Design: <the decided approach: data flow, names, signatures, edge cases; the
     nearest existing pattern to mirror (grain) and the minimal root-cause change,
     no speculative scope (ponytail)>
   Tests: <for each acceptance criterion and edge case this slice implements,
     one test that runs the real code path that enforces it. A query that
     decides who or what is affected gets a test against a real database, not a
     mock of itself>
   Constraints: <project rules that apply: style, layers, security>
   Out of scope: <what not to touch, including files owned by other slices>
   Verify: <exact commands and expected outcome>
   ```

   **Brief behaviour, not code lines.** Signatures and names belong in Design;
   expressions do not. "Edit only steps whose body is a single html block, and
   refuse the others with a message" lets the implementer see the case. A
   dictated expression like `step.blocks[0]?.html` hides it, and the implementer
   will type it faithfully. Never give an implementer a way out of testing
   ("add a test only if a sibling pattern exists"): name the test, or name the
   sibling it mirrors.

3. Route the slice to an implementer by its **shape**.

   | slice shape | implementer |
   | --- | --- |
   | Rote and fully decided: bulk rename, find/replace, boilerplate, generated-code touch-up, hand-editing a generated migration | `sonnet-implementer` |
   | Backend work against a detailed brief with tests to satisfy | `sonnet-implementer` |
   | Frontend work that follows an existing design grammar | `sonnet-implementer` |
   | Any slice that changes a shared API surface and must fix every consumer | `sonnet-implementer` |
   | Genuinely hard: concurrency/async correctness, a subtle multi-site refactor, a perf-critical or security-sensitive path, a non-obvious algorithm, a backfill migration no single test file can prove | `opus-implementer`, `-xhigh` for the worst |
   | Design, decomposition, briefs, diff review, gates, commits, prose | the architect, in the main loop |

   **Route by shape, never by risk tier.** What replaces the tier is the review,
   which the architect owns: a T3 diff gets read line by line and its full suite
   run before it is accepted, and a critical path gets a human in the loop per the
   repo's CLAUDE.md. Risk changes how hard the diff is checked and who signs it
   off. It never changes who writes it.

   Sonnet infers a component's shape from its siblings, which is what frontend
   work and shared-surface changes need. A model that only executes a
   specification strips an API surface without migrating its consumers; that is
   how a non-compiling tree gets left behind.

   **`opus-implementer` is for hard slices, not for stuck ones.** It bills the
   weekly cap hardest, so it is reserved for work whose difficulty is in the
   *reasoning*, not for a slice that came back wrong. "Hard" means the code is
   not determined by the brief: an async race to get right, a refactor whose
   correctness depends on sites the brief cannot all enumerate, an algorithm with
   a non-obvious invariant, a backfill whose correctness no single test file can
   show. It is not "this is T3", and it is not "this is tedious". A T3 path the
   brief fully specifies still goes to `sonnet-implementer`. Decide the tier when
   you write the brief, from the brief you just wrote: if writing it made the
   code obvious, the slice is not hard.

   A slice that comes back wrong is a *brief* problem, and reaching for a bigger
   model hides it. Correct the same worker once, then decompose and re-brief.
   The architect's own hands are not a fallback either: the only code the main
   loop writes is what the **small edits** exception above allows.

   **Compensate for a smaller model with a better brief, never with a higher
   tier.** That means real excerpts in Context, exact line anchors in Files, and
   named signatures in Design. A brief that would have been "good enough" for
   Opus to infer from is not good enough for Sonnet.

   One slice, one worker. Don't spawn a fleet for work one worker can hold.

4. **Context hygiene: this is where the cap goes.** Six workers on 2026-09-14
   burned 245M input tokens over 1,585 turns (264 per slice) to produce ~6k lines
   of diff. Prompt caching was already working at a 91.6% hit rate; the bill was
   volume, not pricing. Every turn re-sends the whole conversation, so anything a
   worker reads is paid for again on every turn that follows it.

   - **A worker never runs a full test suite.** One `pytest` run parks ~100 KB in
     context that is re-sent for the rest of the session. The worker runs only the
     test files its brief names; the architect runs the gates.
   - **Cap turns.** `maxTurns` in the agent definition. A slice that needs 250
     turns was briefed wrong. When a worker hits its cap, split the slice and
     re-brief. Never raise the cap: the run that overran was already re-sending a
     conversation too large to finish in, and a bigger budget buys more of the same.
   - **Keep a slice under ~12 files and ~500 lines of diff.** The frontend slice
     that died bundled four pages, a shell, a results tab, route removals, a nav
     item and i18n. Split by deliverable, not by layer.
   - **Keep the brief under ~8 KB.** The brief is re-sent every turn too. Quote the
     excerpt the worker needs; never send it off to read a 100 KB spec document. A
     brief that will not fit is telling you the slice is too big: split it, rather
     than cutting the Context the worker needs to avoid rediscovering the codebase.
   - **A moved anchor or a gap in the brief is a stop-and-report**, never a licence
     to explore around it.

5. Independent slices: spawn agents in parallel, but only after decomposing so
   each slice owns a disjoint set of files (declared in its brief). If ownership
   can't be made disjoint, don't parallelize; serialize or merge the slices.
   `isolation: "worktree"` is a last resort: worktrees branch from the repo's
   default branch, not the session's HEAD, so a worktree agent won't see the
   current branch's unmerged work.

## Review loop

- Read the agent's report **and** the actual diff (`git diff`). Trust neither
  alone; cross-check the report's `git diff --stat` against what you see.
- Check the report's `Mirrored:` line before you read the diff. An exemplar that
  is the wrong kind of file, or a "new pattern" claim for something the repo
  already does, tells you the diff is wrong without opening it. A missing line
  means the worker did not look.
- Re-run the key verification commands yourself when the claim matters.
- Found a problem? Send the correction via SendMessage to the **same** agent. It
  retains its full conversation context and picks up exactly where it stopped.
  Don't fix it by hand and don't respawn fresh.
- Two failed correction rounds means the brief was underspecified, not that the
  model is incapable: decompose the slice smaller, put the missing excerpt in
  Context, and rerun. Do not climb the tiers a rung at a time. `opus-implementer`
  is chosen up front for a hard slice, never reached as the third attempt at an
  easy one. If a slice has failed twice, the brief is the defect and a bigger
  model will just implement the same misunderstanding more fluently.
- **Check the whole change against the requirement before you call it done.**
  Diff review checks each slice against its brief, so a defect in the brief
  passes it. Once every slice is in, read the full diff against the original
  issue, not against the briefs, and write each acceptance criterion and each
  edge-case row as met, partial or missed with the `file:line` that shows it.
  Anything not met is a new brief to the same worker, before the last CI round.
- **Gates are the safety net.** Before accepting any implementer's diff, run the
  scoped checks yourself: the touched tests, the linter on the touched files, and
  whatever convention script the repo carries. Do not take the worker's word that
  they passed.
- Running commands (tests, lint, git, builds) is not programming; the architect does
  that freely. Only the code writing is delegated.
