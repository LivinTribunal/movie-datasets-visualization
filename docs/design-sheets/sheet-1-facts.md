# Sheet 1 facts: what the data actually shows

Real numbers to draw sheet 1 from, one block per task. They come from the
pipeline's joined tables (`data/interim/`, built 2026-10-12 from the frozen
snapshots). The chart picks are D10 in `docs/decisions.md`; the boards are in
[`sheet-1-canvas/`](sheet-1-canvas/README.md).

Correlations are Spearman's ρ (rank-based, so a few blockbusters cannot drive
them). Money is in 2025 USD. "Notable" means at least 10,000 IMDb votes.

## How much data each view has

| | working subset (56,431 films, 1900–2026) | notable subset (13,080 films) |
|---|---|---|
| budget | 31.6 % | 75.7 % |
| revenue | 32.8 % | 81.4 % |
| ROI (both known) | 23.0 % | 69.6 % |
| tomatometer | 44.1 % | 87.8 % |
| RT audience score | 63.6 % | 92.6 % |
| critic–audience gap | 43.0 % | 87.4 % |
| Metascore | 16.2 % | 70.0 % |
| Letterboxd | 23.1 % | 99.6 % |

Budgets come from TMDB (10,092 films), The Numbers (6,033), Wikidata (1,028)
and Wikipedia (751). The money views should stay on the notable subset and say
how many films have no value.

## T1. Genre taste per country

- **Netflix:** 94 countries, 2021–2026. The median country-year has 99 % of its
  chart weight matched to a TMDB film.
- **Cinema (LUMIERE):** 36 European markets, 1996–2025, notable films only.
- **The top family is nearly the same everywhere.** On Netflix, Drama & Romance
  leads in 70 of 94 countries and Crime & Thriller in 19. In cinemas, Action &
  Adventure leads in 34 of 36 markets.
- **Shares of one family vary a lot between countries:**

  | family (Netflix share) | lowest | highest |
  |---|---|---|
  | Horror | Israel 1.6 % | Indonesia 12.9 % |
  | Family & Animation | Nigeria 2.0 % | Bolivia 12.2 % |
  | Comedy | Japan 9.4 % | Latvia 21.6 % |
  | Action & Adventure | Ireland 14.0 % | Vietnam 25.4 % |

**For the sketch:** a "top family" choropleth would be almost one colour, so
the map should default to "share of the selected family". Cinema leans action
and streaming leans drama, which makes X2 (cinema vs streaming) worth a mode.

## T2. Money vs ratings

- Revenue barely relates to any score. Across ~10,000 notable films with
  revenue, ρ is −0.04 for the tomatometer, −0.04 for the Metascore, +0.09 for
  RT audience and +0.09 for IMDb.
- ROI relates a little more, and more for audiences: ρ = 0.21 (Metascore), 0.24
  (tomatometer), 0.28 (RT audience), 0.29 (IMDb).
- Revenue spans four orders of magnitude: median $35M; 10th–90th percentile
  $1M–$325M. The top value is Gone with the Wind, $9.0B in 2025 USD.

**For the sketch:** the revenue scatter will look like a shapeless cloud; that
is the finding, not a bug. Offer ROI as a y-axis option, and keep the money
axes on a log scale.

## T3. Critic–audience gap

- 24,285 films have both RT scores. The median gap is −3 (critics slightly
  higher). Half of the films sit between −15 and +12; 16.1 % have audiences
  more than 20 points higher, and 16.5 % have critics more than 20 points
  higher.
- **By family**, audiences are harsher than critics on Horror and Documentary
  (median −8) and a bit kinder on Action & Adventure and Family & Animation
  (+1).
- **Over time**, the median gap was −10 in the 1950s, +5 in the 1990s and −7 in
  the 2010s.
- **Crowd pleasers** (notable films): After Ever Happy (critics 0, audience 92),
  Melania (9 vs 99), Home (0 vs 87), Redeeming Love (11 vs 95), Reagan (17 vs
  98).
- **Critic darlings:** Knock Down the House (99 vs 11), Fauci (86 vs 2),
  Unpregnant (92 vs 15), Hannah Gadsby: Nanette (100 vs 26), Cuties (87 vs 15).

**For the sketch:** the extreme outliers are mostly political documentaries and
YA romances. Labels on the scatter will be read, so plan room for 5–10 of them.
The ridgeline should sort families by median gap; Horror and Documentary end
up at one edge.

## T4. Genre popularity over time

Share of each family per decade, working subset, 1/n genre weights:

| family | releases 1950s | releases 2020s | IMDb votes 1950s | IMDb votes 2020s |
|---|---|---|---|---|
| Action & Adventure | 18.2 % | 9.8 % | 14.6 % | 19.8 % |
| Sci-Fi & Fantasy | 6.0 % | 4.5 % | 5.4 % | 10.6 % |
| Documentary | 1.1 % | 6.1 % | 0.3 % | 1.8 % |
| Horror | 4.7 % (peak 11.7 % in the 1970s) | 7.3 % | 2.7 % | 7.6 % |
| Drama & Romance | 37.1 % | 34.4 % | 47.0 % | 25.3 % |
| Crime & Thriller | 14.5 % | 18.6 % | 18.7 % | 20.0 % |

**For the sketch:** the metric switch changes the story. Counted by releases,
Action & Adventure and Sci-Fi shrink. Counted by votes, they grow: fewer films
draw more attention. The stacked area needs the switch visible next to it, not
hidden in a menu.

## T5. Budget vs popularity and ratings

- 9,905 notable films have a budget. Median $25M; 10th–90th percentile
  $3.1M–$114M.
- A bigger budget means more votes (ρ = 0.45 overall) but not better ratings:
  ρ = −0.12 with IMDb, and between −0.14 and −0.37 with the tomatometer in
  every family.
- The votes effect is strongest for Sci-Fi & Fantasy (0.62) and Action &
  Adventure (0.60), and almost absent for Documentary (0.10, only 94 films).

**For the sketch:** in the bubble chart (x budget, y rating, size votes) the
bubbles grow to the right while the y-position stays flat or drops. That is the
picture the task needs. The per-family small multiples show which families
deviate.

## T6. Do sequels get worse?

- 605 franchises with at least 3 released films (median 3, longest 37).
- 83 % of sequels have a lower IMDb rating than the first film. The median drop
  is 6 points for film 2 and 10 points for film 3 (0–100 scale).
- 64 % of sequels earn less than the first film in real dollars. Film 2 earns a
  median 78 % of film 1.
- In 87 % of the 558 franchises with at least 3 rated films, the latest one is
  rated below the first.
- **Exceptions** (latest vs first, IMDb ×10): The Wolverine +16, Attack on
  Titan +12, Naruto +11, Star Trek (original series) +9.
- **Steepest falls:** Home Alone −52, Jaws −50, Ace Ventura −48.

**For the sketch:** with the y-axis as "change vs the first film", most lines
fall below zero, so the median line plus a highlighted exception tells the
story. Franchise names to use in sketches: Home Alone, Jaws and The Wolverine.
