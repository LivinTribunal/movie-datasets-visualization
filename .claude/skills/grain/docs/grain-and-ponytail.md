# Code with the grain, ship the laziest thing that works

Two authoring principles, for humans and for agents. The first says new code
should look like the code already around it. The second says write as little of
it as the problem allows. They pull in the same direction most of the time, and
where they disagree, grain wins.

Written for an agent to read before it starts writing, not after. The point is
that review should never have to undo work you were allowed to generate.

---

## Grain: code with the grain of what already exists

New code should be indistinguishable from the code around it. Before writing
anything, find the nearest existing example of the same kind of thing and mirror
it.

1. **Find the exemplar first.** For a route, service, repository, background
   task, data-fetching hook, store slice or component, locate the closest
   existing one and copy its shape, file location and naming. Do not invent new
   structure when a pattern exists. Name one file, not a concept.
2. **Respect the layers.** Most codebases have a dependency direction, whether
   or not it is written down: presentation depends on application, application on
   domain, infrastructure implements domain. A new import across those lines is a
   finding. If the project has an architecture check, it will fail; if it does
   not, the reader will pay for it instead.
3. **Local grain against repo grain.** Match your siblings. But if the siblings
   themselves diverge from the canonical pattern, follow the canonical pattern
   and note the divergence rather than copying the drift. "It matches the other
   five routes in this file" is not enough if all six skip a layer the canonical
   example uses. You compared too locally.
4. **Reuse the canonical helper.** If a helper, type or pattern already lives in
   the repo, use it. Do not create a second near-alias. Two normalizers force
   every reader to diff both to trust either, and that drift is exactly what a
   canonical helper prevents.
5. **Names carry meaning.** Reuse the domain vocabulary already in the code. A
   new name for an existing concept is a bug waiting for a reader.

Rule of thumb: if a reviewer can tell which lines you wrote purely from their
shape, you fought the grain.

### Picking the exemplar

Pick the **canonical** one, not the nearest one. A good exemplar is small, current,
spans the layers the work touches, and was written after the conventions settled.
Name it in the plan before anyone writes code, and name it again in the report
when the code is done. If your project does not have an obvious one, choose it
once and write it down; every later change gets cheaper.

This repo's table. The layout is in `AGENTS.md`; some folders do not exist yet,
and the first file of each kind becomes the exemplar for the rest.

| Artifact | Lives in | Shape to mirror |
|---|---|---|
| Data source | `pipeline/src/movies/acquire/sources.py` | one `Source(...)` entry in `REGISTRY` |
| Downloader or scraper | `pipeline/src/movies/acquire/`, `scrape/` | cache every response first, parse only from the cache; exemplar `acquire/wikidata.py` |
| Stage module | `pipeline/src/movies/<stage>/<source>.py` | pure functions over polars frames, file I/O only at the edges, paths from `movies.paths` |
| CLI entry | `pipeline/src/movies/cli.py` | an argparse subparser that calls the stage's `run()` |
| Pipeline test | `pipeline/tests/test_<module>.py` + `tests/fixtures/` | small fixture, no network; exemplar `tests/test_wikidata.py` |
| App data types | `app/src/lib/types.ts` | mirrors what `movies export` writes, field for field |
| Scales, palettes, formatters, loaders | `app/src/lib/` | pure helpers, each with a vitest case |
| Shared filter and selection state | `app/src/state/` | one zustand store |
| View | `app/src/views/<View>/` | functional component; reads and writes the store, never another view |

### The canonical call chain

The right folders are not enough; the code also has to take the right hops
between them:

```
pipeline:  cli  ->  stage run()  ->  pure transforms  ->  parquet in data/
app:       lib loader  ->  store  ->  view  ->  store
```

**Anti-pattern: the skipped hop.** A view that fetches its own data file, or
reads another view's local state, collapses the chain. It works. It also means
the store no longer holds the shared state, so linking breaks the next time a
view changes. A stage that downloads inside a transform has the same shape: the
cache-first rule no longer holds for that request.

**Anti-pattern: I/O inside a transform.** Stage logic is pure functions from
frames to frames, and only the stage's `run()` reads and writes files. A
transform that opens a file or makes a request cannot be tested on a fixture
and runs again on every call.

**Anti-pattern: the invented sync collaborator.** Before adding a method to a
client or service interface that a caller will wrap in a thread, check whether a
sibling collaborator of the same kind already exposes that operation natively
async. Inventing a second shape for the same kind of thing is the grain problem;
the correctness trap sits right behind it, because handing an already-async
callable to a thread helper does not run it and does not await it.

**Compare against the canonical exemplar, not just the neighbours.** A whole
slice can be the outlier and read as consistent because you compared too locally.
A few older slices usually drift in naming too. Mirror the convention, not the
outlier.

---

## Ponytail: the laziest solution that actually works

Lazy means efficient, not careless. The best code is the code never written.
Understand the problem fully first, every file the change touches and the real
end-to-end flow, then climb this ladder and stop at the first rung that holds:

1. **Does this need to exist at all?** Speculative need, skip it and say so in
   one line.
2. **Already in this codebase?** A helper, util, type or pattern that already
   lives here: reuse it.
3. **Standard library does it?** Use it.
4. **Native platform feature covers it?** A built-in input type over a picker
   library, CSS over JS, a database constraint over application code.
5. **Already-installed dependency solves it?** Use it. Never add a new dependency
   for what a few lines can do.
6. **Can it be one line?** One line.
7. **Only then:** the minimum code that works.

**Bug fix means root cause, not symptom.** A ticket names a symptom. Grep every
caller of the function you are about to touch: one guard in the shared function
is a smaller diff than a guard in every caller, and patching only the path the
ticket names leaves sibling callers broken. Fix it once, where all callers route
through.

**Keep the diff minimal.** The smallest change that fully solves the problem is
the target, and the diff is what review actually reads. No drive-by refactors, no
renames, no reformatting, no "while I'm here" improvements, no touching files the
task did not require. Each one buries the real change and widens the blast
radius. If the diff is bigger than the problem, cut it back before you ship.
Unrelated improvements you spotted are a follow-up issue, not extra commits on
this branch.

**Do not build:** interfaces with one implementation, factories for one product,
config for a value that never changes, thin wrappers around an existing helper,
scaffolding "for later". Deletion over addition. Boring over clever, because
clever is what someone decodes at 3am.

**When not to be lazy.** Never simplify away input validation at a trust
boundary, error handling that prevents data loss, security measures,
accessibility basics, or anything explicitly requested. And never be lazy about
understanding: the ladder shortens the solution, never the reading. A small diff
in the wrong place is a second bug, not laziness.

**Leave a check.** Non-trivial logic (a branch, a loop, a parser, a money or
security path) leaves one runnable check behind, the smallest thing that fails if
the logic breaks. Trivial one-liners need none; YAGNI applies to tests too.

**Mark the ceiling.** When you take a rung on purpose and know what would push
you off it, say so in the code:

```python
# ponytail: global lock, per-account locks if throughput matters
```

Each one is a decision a future reader would otherwise have to reconstruct, and a
marker for where to look when the ceiling is hit.

---

## Where the rules have to live

A principle in a document is not a behaviour. Across five weeks of agent
transcripts on the repo this came from, the skill was invoked by name zero times
and the closing `mirrored:` line appeared in seven responses. The rules still
landed, because the same text was in three places the agent reads without
choosing to:

- **The project's `CLAUDE.md`**, which is in context from the first turn. One
  paragraph, not the whole doc.
- **The implementer agent's own definition**, as an imperative rule rather than a
  skill to consider.
- **The review step**, whose tags fail a pull request that ignores them. See
  [`review-tags.md`](review-tags.md).

The skill body is the reference all three point at. As a trigger on its own, it
did nothing.
