@AGENTS.md

## Claude-specific notes

- `AGENTS.md` is the single source of project instructions. Put shared rules
  there, not here.
- Before you change a view, re-read `docs/PLAN.md` §5. Before you change a
  data rule, re-read `docs/decisions.md`.
- Never run a scraper, or the full `make data`, without being asked. Both
  take a long time and hit external sites.
- To read a course PDF, use the text version in `materials/is_export/*.txt`.
