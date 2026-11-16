## Implementation brief: Q smoke test, size budgets and Pages deploy

Goal: CI proves the built app works in a browser and stays inside its size budgets, and
every push to `main` publishes `app/dist` to GitHub Pages.

Context:
- Read spec `docs/superpowers/specs/2026-11-16-movie-explorer-app-design.md` **§7 and
  §8**.
- `app/package.json` scripts today: `dev`, `build` (`tsc -b && vite build`), `preview`,
  `lint`, `typecheck`, `test` (`vitest run`). `.github/workflows/ci.yml` has the jobs
  `pipeline` and `app`. `Makefile` and the "Commands" and "CI" sections of `AGENTS.md`
  list them.
- The app is one page. Panels are `<section>`s with the classes `area-a` (map),
  `area-b` (timeline), `area-c` (scatter), `area-d` (franchise), `area-e` (table),
  `area-g` (card); the filter bar is `area-f`. Each panel has a `.panel-note` line.
  Useful hooks that exist: genre chips are `button[role="radio"]` with the family name
  as text; the map legend text contains `share of <family>`; the scatter brush overlay
  is `.area-c .overlay` (d3-brush, mouse events); the table note reads
  `… films pass the filters` or `… films inside the scatter brush`; table rows are
  `.area-e [role="row"]` (the first is the header); the card shows the hint
  "Hover a point or a table row to see a film. Click to pin it." until a film is
  chosen; a pinned film puts `film=tt…` in the URL hash within 300 ms.
- The card loads a poster from `https://image.tmdb.org`. Tests must not hit the
  network: fulfil that route with a 1×1 PNG.
- Vite `base` is `./` and data URLs are relative, so the build works under
  `/<repo>/` on Pages with no change. Do not add a `base` for Pages.

Files (yours only):
- `app/scripts/budget.mjs` (new)
- `app/e2e/smoke.spec.ts`, `app/playwright.config.ts` (new)
- `app/package.json`, `app/package-lock.json`, `app/vite.config.ts`, `app/tsconfig*.json`,
  `app/eslint.config.js` (only what the new files need)
- `.github/workflows/ci.yml`, `.github/workflows/deploy.yml` (new)
- `.gitignore`, `Makefile`, `AGENTS.md` (Commands and CI sections, layout line for
  `.github/workflows/`)

Design:
1. `scripts/budget.mjs` (Node stdlib only): gzip every `dist/assets/*.js` and `*.css`
   with `zlib.gzipSync` and sum per type; sum the bytes of `dist/data/*`. Limits: JS
   200 KB, CSS 20 KB (1 KB = 1,000 bytes, gzipped), data 8 MB. Print one line per
   budget (`js 127.2 KB / 200 KB ok`) and exit 1 when one is over or `dist` is missing.
   Script `"budget": "node scripts/budget.mjs"`.
2. Playwright: dev dependency `@playwright/test` (the only new dependency).
   `playwright.config.ts`: `testDir: 'e2e'`, Chromium only, `baseURL`
   `http://localhost:4174`, `webServer` = `npm run preview -- --port 4174 --strictPort`
   (it serves the existing build; `reuseExistingServer: !process.env.CI`), retries 1 on
   CI, reporter `list`. Script `"e2e": "playwright test"`.
3. `e2e/smoke.spec.ts`, one test file, viewport 1440 × 900:
   - collects `console` errors and `pageerror`s for the whole test and asserts none at
     the end;
   - the seven areas are visible and the scatter canvas exists;
   - clicking the "Horror" chip makes the map legend contain "Horror";
   - dragging on the scatter overlay (`page.mouse` down, move in steps, up) changes the
     table note to "inside the scatter brush";
   - clicking the first data row of the table replaces the card's hint with a title,
     and the URL hash then contains `film=tt`;
   - opening the same URL in a new page shows the same film in the card (the hash
     restores the state).
4. Vitest must not pick up `e2e/`: set `test.include` to `['src/**/*.test.ts']` in
   `vite.config.ts`. TypeScript and ESLint must cover `e2e/` and
   `playwright.config.ts` (add them to the node tsconfig's `include`; lint them with
   the same rules as the rest).
5. `.gitignore`: `app/test-results/`, `app/playwright-report/`.
6. `ci.yml`: the `app` job runs `npm run budget` after the build. A new job `e2e`
   (ubuntu-latest, working directory `app`): checkout, setup-node 22 with the npm
   cache, `npm ci`, `npx playwright install --with-deps chromium`, `npm run build`,
   `npm run e2e`.
7. `deploy.yml`, name `deploy`: on push to `main` and `workflow_dispatch`.
   `permissions: { contents: read, pages: write, id-token: write }`, `concurrency:
   { group: pages, cancel-in-progress: false }`. Job `build`: checkout, setup-node 22,
   `npm ci` and `npm run build` in `app`, `actions/configure-pages@v5`,
   `actions/upload-pages-artifact@v3` with `path: app/dist`. Job `deploy` (needs
   `build`, environment `github-pages` with `url: ${{ steps.deployment.outputs.page_url }}`):
   `actions/deploy-pages@v4` with id `deployment`.
8. `Makefile`: targets `budget` (build, then budget) and `e2e` (build, then e2e), in
   `.PHONY`. `AGENTS.md`: add both to Commands; the CI section lists the three jobs
   and says the deploy runs on `main` through `deploy.yml`; drop the word "Planned."
   and "(optional)" where they describe things that now exist.

Constraints: no secrets, no host-specific code in the app, scrapers and the pipeline
are untouched. YAML mirrors the style of the existing `ci.yml`.

Out of scope: `app/src/` (if a test needs a hook that does not exist, report it and
use the closest existing selector), `pipeline/`, enabling Pages in the repo settings
(the architect does it).

Verify (from `app/`; this slice may build):
- `npm run build && npm run budget` → three "ok" lines
- `npx playwright install chromium` once, then `npm run e2e` → 1 passed
- `npm run lint && npm run typecheck && npm test` → pass, and Vitest lists no `e2e` file
