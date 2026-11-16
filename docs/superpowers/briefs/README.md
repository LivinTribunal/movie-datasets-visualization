# Implementation briefs

One brief per slice of the app build. The design is in
`../specs/2026-11-16-movie-explorer-app-design.md`; §10 there lists the waves.
A brief is self-contained: an implementer reads its brief and the files it
names, not the whole spec.

Rules for every brief:

- Do not commit, push or switch branches. The architect does that.
- Stay inside **Files**. If something outside must change, stop and report.
- Run only the commands under **Verify**, never a whole test suite.
- End with the report format of `.claude/agents/sonnet-implementer.md`.

| Wave | Brief | Status |
|---|---|---|
| 1 | `p1-country-sources.md` | ready |
| 1 | `p2a-pack-export.md` | ready |
| 1 | `p2b-validate.md` | written after P2a lands |
| 2 | `a1-data-layer.md` | ready |
| 2 | `a2-shell.md` | written after A1 lands |
| 3 | `va-map.md`, `vb-timeline.md`, `vc-scatter.md`, `vd-franchise.md` | written after A2 lands |
| 4 | `ve-table.md`, `vg-card-about.md`, `vf-search-hash.md` | written after wave 3 |
| 5 | `q-e2e-budgets-deploy.md` | written after wave 4 |

Later briefs are written when the code they build on exists, so their
anchors point at real files.
