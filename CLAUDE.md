@AGENTS.md

## Claude-specific notes

- `AGENTS.md` is the single source of project instructions. Put shared rules
  there, not here.
- Before you change a view, re-read `docs/PLAN.md` §5. Before you change a
  data rule, re-read `docs/decisions.md`.
- Never run a scraper, or the full `make data`, without being asked. Both
  take a long time and hit external sites.
- To read a course PDF, use the text version in `materials/is_export/*.txt`.

## Skills and agents

Project skills live in `.claude/skills/`, implementer agents in
`.claude/agents/`.

- `architect`: on an Opus or Fable session, plan and brief, and let
  `sonnet-implementer` (or `opus-implementer` for hard slices) write the code.
  You review the diff and run the gates.
- `grain`: the bar for writing code (mirror the nearest example, ship the
  laziest thing that works).
- `pr-ready`: self-review and scoped checks before `git push`.
- `review-proof`: review a PR, prove each finding with a failing test, fix
  what reproduced.
- `unslop`: load before writing a PR body, a review report or report text.
