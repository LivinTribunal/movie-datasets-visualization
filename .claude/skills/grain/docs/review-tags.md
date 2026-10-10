# The two review passes

Two passes over a finished diff, with fixed tags. The tags are what make findings
comparable across reviewers and across agents: a finding is a tag, a location, a
one-line claim and a pointer to the pattern that should have been followed.

Run **structure first**. The order is a rule, not a preference, and the last
section says why.

---

## Pass 1: structure (the grain pass)

One question: **does this code go with the grain of what already exists, or does
it invent a second way to do something already done?** The best outcome is not a
shorter diff, it is a diff indistinguishable from the code already in those files.

For each finding, name the **existing exemplar** the code should have followed. A
finding without a "here is the pattern you already have" pointer is an opinion.
Do not emit it. The exemplar does not have to live in another file: the
most-missed findings are intra-module, where the diff adds a second way to do
something the same file or the callee itself already owns.

- `diverge:` does the same kind of thing as a sibling, but shaped differently
  (naming, injection style, file layout, error or response type). Name the
  dominant sibling pattern and an exemplar path.
- `duplicate:` re-implements a helper, component, service or util that already
  exists. Name the existing one to call instead. Before concluding there is no
  duplicate, grep the whole tree for the diff's distinctive expressions, the
  exact transformation rather than the concept. The copy often lives in another
  bounded context the diff never touches. A third copy is always a finding:
  hoist to a shared module both already import.
- `layer:` an import crosses a forbidden boundary. Name the layer it should route
  through.
- `misplaced:` right code, wrong folder for its kind or its bounded context. Name
  where it belongs.
- `reach-in:` touches another bounded context's internals instead of going
  through that context's public entry point. Name the service to call.
- `inconsistent:` introduces a second convention for an operation the module
  already does one way. Name which convention is dominant and align to it. The
  second-entrance variant: a new optional parameter that makes a function bypass
  construction logic an existing builder in the same module already owns is a
  second entrance to the same operation. Extend the builder instead of tunneling
  past it.
- `own:` a call site branches on the kind of a collaborator to pick between
  implementations, when the callee, its factory or its registry already dispatches
  on that same distinction, or is the information expert that should.
  Responsibility belongs with whoever owns the data the decision reads. This is
  the one tag that needs no pre-existing pattern pointer when the code is
  first-of-its-kind, because "who should own this decision" is answerable from
  the dependency direction alone.
- `chain:` skips a hop the canonical request path uses. Name the canonical chain
  and its exemplar. A whole slice doing this uniformly is still a divergence, not
  a second style.

Format: `<file>:L<line>: <tag> <what diverges>. follows: <existing pattern @ exemplar path>.`

Example:

```
controllers/chatbot.py:L40: layer: controller imports infrastructure.chatbot.repository directly.
  follows: inject ChatbotApplicationService like controllers/branding.py:L13.
```

**Altitude: compare to the canonical exemplar, not just the neighbours.** The
trap is checking the changed code against the other functions in the same file,
seeing they match, and calling it clean. A whole slice can be uniformly diverged.
Before any "goes with the grain" verdict: identify the canonical exemplar for this
kind of slice and its full call chain, check the changed code against that, and if
the slice diverges as a whole, say so. Distinguish local grain (matches its
siblings) from repo grain (the siblings themselves diverge). A new line that
merely conforms to a diverged slice inherits that slice's debt. Name it.

**In-code justification does not exempt structure.** A comment arguing for a
placement explains the author's intent. It does not settle where the
responsibility belongs. Evaluate the finding on the dependency direction and the
information-expert test, then cite the justification so the resolution addresses
it. An escape hatch nothing uses, sitting next to such a justification, is
evidence the placement is unsettled.

Only divergences this change **introduces** should block. Pre-existing debt gets
named, not blocked on.

---

## Pass 2: cuts (the over-engineering pass)

Report-only. One line per finding: location, what to cut, what replaces it.

- `delete:` dead code, unused flexibility, speculative feature. Replacement:
  nothing.
- `stdlib:` hand-rolled thing the standard library ships. Name the function.
- `native:` a dependency or code doing what the platform already does. Name the
  feature.
- `yagni:` an abstraction with one implementation, config nobody sets, a layer
  with one caller.
- `shrink:` same logic, fewer lines. Show the shorter form.

Format: `<file>:L<line>: <tag> <what>. <replacement>.`

Example:

```
validators.py:L12-38: stdlib: 27-line email validator class.
  "@" in the string, one line; real validation is the confirmation mail.
```

---

## Consistency beats cuts

The two passes disagree on purpose.

Cuts says: a thin wrapper with one caller, inline it, thirteen lines gone.
Structure says: if that wrapper matches a row of sibling wrappers in the same
module, it is the grain, and inlining it creates an inconsistency.

**For shared or convention-bearing code, consistency wins over brevity.** A cut
that would break an established local convention is overruled with
`keep: matches <N> siblings @ <path>`. For genuinely novel one-off code with no
sibling, minimalism wins.

Run structure first and the cuts pass only touches code that already matches.
