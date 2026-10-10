---
name: grain
description: >
  The authoring bar for writing or changing code: mirror the nearest existing
  example (grain) and ship the laziest thing that actually works (ponytail).
  Load this BEFORE writing, not after: when implementing a feature or fixing a
  bug; when adding a route, service, repository, background task, data-fetching
  hook, store slice or UI component; when deciding where a new file goes,
  whether a helper already exists, or whether a new dependency is warranted;
  and on "follow our patterns", "keep it minimal", "don't over-engineer",
  "where does this go", "/grain", "/ponytail". Skip for pure docs and config
  edits and one-line typo fixes.
license: MIT
---

# Grain and ponytail

Hold this bar while writing, so review is confirming your work rather than
undoing it.

## Do this

1. **Read [`docs/grain-and-ponytail.md`](docs/grain-and-ponytail.md) now.** It
   has the full ladder, how to pick an exemplar, the anti-patterns and the
   when-not-to-be-lazy list. That doc is the law; this file is only the reflex
   that makes you open it at the right moment.
2. **Find the exemplar before you write.** Locate the nearest existing thing of
   the same kind and mirror its shape, location and naming. Not the concept:
   the actual file.
3. **Match the layer and the call chain.** New code takes the same hops between
   modules that the canonical example takes, each dependency injected the same
   way. A shortcut that skips a hop is a divergence even when it works.
4. **Follow this repo's wiring.** The pipeline is pure functions per stage
   (input files to output files, locations from `movies.paths`), and I/O stays
   at the stage's edges. In the app, views read and write the zustand store and
   never talk to each other. A new piece goes where its siblings are and takes
   the same hops.
5. **Climb the laziness ladder and stop at the first rung that holds.** Does it
   need to exist at all, is it already in the repo, does the standard library do
   it, does a native platform feature do it, does an installed dependency do it,
   can it be one line, and only then the minimum code that works.
6. **Keep the diff minimal.** The smallest change that fully solves the problem
   is the target. No drive-by refactors, no renames, no reformatting, no "while
   I'm here" improvements, no touching files the task did not require. If the
   diff is bigger than the problem, cut it back before you ship.
7. **Fix the root cause, not the named symptom.** Grep every caller before
   patching the one path the ticket mentions.

## Then say what you did

Close with one line, so the reuse is reviewable:

- `mirrored: <exemplar path>. <what you added or extended>.`
- `new pattern: <what>. No existing <kind> because <reason>. Closest sibling: <path>.`

Never silently invent structure. A new top-level folder, a second helper that
does what an existing one does, or a reach into another module's internals each
gets named and justified, or it does not ship. Mark deliberate simplifications
with a `ponytail:` comment naming the ceiling and the upgrade path.

## Boundaries

- Scope is **placement, shape, reuse and size**: where code goes, what shape it
  takes, and how little of it there is. Correctness, security and performance
  are a normal review's job.
- If this skill and the project's own conventions disagree, **the project
  wins**. Fix the skill.
