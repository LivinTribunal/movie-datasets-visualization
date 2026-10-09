# Sheet 1 brainstorm: three chart options per task

Input for HW2 (Five Design Sheets, sheet 1). For each task from
`materials/project.md` there are three chart types from
[data-to-viz.com](https://www.data-to-viz.com). Each comes with the
data-to-viz path that leads to it, how our data maps onto it, and what it is
good and bad at. The pick at the end of each task is a suggestion for the
sheet, not a final decision.

Encoding rules that apply everywhere (`AGENTS.md`): position first, at most
~8 colour categories (genre *families*), no rainbow or red–green palettes,
money on log axes.

---

## T1. Which genres dominate cinemas and streaming in different countries?

*Compare → distribution / similarity.* Data: country × genre share (Netflix
chart weight, box office, admissions). data-to-viz path:
[map with a value per region](https://www.data-to-viz.com/story/RegionWithValue.html)
and [one value per category and subgroup](https://www.data-to-viz.com/story/OneNumSevCatSubgroupOneObsPerGroup.html).

| # | Chart | Encoding | Good at | Weak at |
|---|---|---|---|---|
| A | [**Choropleth map**](https://www.data-to-viz.com/graph/choropleth.html) | Country colour = share of the selected genre (sequential), or the top genre (categorical, families). A switch for Netflix / cinema. | The geographic overview; regional patterns (e.g. anime in East Asia) jump out; a natural entry point for clicking a country | Shows one genre at a time. Large countries dominate visually and small ones vanish. Countries with no data must be hatched. |
| B | [**Heatmap**](https://www.data-to-viz.com/graph/heatmap.html) | Rows = countries (ordered by similarity / clustering), columns = genre families, colour = share. Two side-by-side panels: cinema and streaming. | Shows **all genres for all countries** at once. Similar countries form visible blocks, which directly answers "how do countries differ". | 94 rows is tall, so it needs sorting or a region filter. Colour gives less precise values than position. |
| C | [**Stacked barplot (100 %)**](https://www.data-to-viz.com/graph/barplot.html) | One bar per country, segments = genre families. A cinema bar and a streaming bar next to each other per country. | The exact genre mix for a few selected countries; a good drill-down after clicking on the map | Only the bottom segment is easy to compare across bars; hard to read for more than ~15 countries. See [caveat: order your data](https://www.data-to-viz.com/caveat/order_data.html). |

**Pick for the sheet:** A as the entry view, linked to C for the selected
countries. B is the "analyst" alternative, worth sketching as one of the
three different designs (sheets 2–4).

---

## T2. Are commercially successful films also better rated?

*Discover → correlation.* Data: revenue or ROI (real USD) vs critic and
audience scores, ~13k notable films. data-to-viz path:
[two numeric variables](https://www.data-to-viz.com/story/TwoNum.html) and
[several numeric variables](https://www.data-to-viz.com/story/SeveralNum.html).

| # | Chart | Encoding | Good at | Weak at |
|---|---|---|---|---|
| A | [**Scatter plot**](https://www.data-to-viz.com/graph/scatter.html) | x = worldwide gross (log), y = score; a switch between critics (tomatometer) and audience (RT audience / IMDb). Trend line per score type. | Shows the relationship and individual films; supports brushing, hover and selection for linked views | 13k points [overplot](https://www.data-to-viz.com/caveat/overplotting.html), so it needs transparency, small dots or zoom |
| B | [**2D density / hexbin**](https://www.data-to-viz.com/graph/density2d.html) | Same axes; colour = number of films per hexagon (sequential). Small multiples: critics next to audience. | Solves overplotting and shows where most films are; a fair comparison of the two score types | Loses individual films (no hovering a single film); harder to link to other views |
| C | [**Correlogram**](https://www.data-to-viz.com/graph/correlogram.html) | Matrix of budget, revenue, ROI, tomatometer, metascore, audience score, IMDb, votes; cell = correlation coefficient (diverging) | Answers "critics, audiences or both?" in one glance and compares all metrics | Abstract: one number per pair hides non-linear patterns and outliers. Better as a summary next to A. |

**Pick for the sheet:** A, with B as the zoomed-out mode and C as a small
summary panel.

---

## T3. Where do critics and audiences disagree the most?

*Identify / compare → outliers, distribution (per genre, over time).* Data:
tomatometer, audience score, `gap = audience − critics`, genre, year.
data-to-viz path: [two numeric variables](https://www.data-to-viz.com/story/TwoNum.html)
and [one numeric value, several categories](https://www.data-to-viz.com/story/OneNumOneCatSeveralObs.html).

| # | Chart | Encoding | Good at | Weak at |
|---|---|---|---|---|
| A | [**Scatter plot with a diagonal**](https://www.data-to-viz.com/graph/scatter.html) | x = critics, y = audience, a y = x reference line; colour = gap (diverging, purple ↔ orange); the most extreme films labelled | Outliers are literally far from the line; "critic darlings" and "crowd pleasers" sit in opposite corners | Overplotting in the middle; [labels are hard](https://www.data-to-viz.com/caveat/hard_label.html), so label only the top N |
| B | [**Ridgeline plot**](https://www.data-to-viz.com/graph/ridgeline.html) | One density curve of the gap per genre, sorted by median gap; a line at 0 | Compares the gap distribution across ~19 genres compactly ("Horror: audiences harsher") | Gives no film names; reading the overlaps takes care. [Violin](https://www.data-to-viz.com/graph/violin.html) is the alternative. |
| C | [**Lollipop / dumbbell**](https://www.data-to-viz.com/graph/lollipop.html) | The top 20 films by absolute gap; two dots (critic and audience) joined by a line, sorted by gap | Names the outliers, which is the "identify" part of the task; easy to read | Only shows the extremes; needs a filter (genre, decade) to stay interesting |

The trend over time can be added to any of them: a
[line chart](https://www.data-to-viz.com/graph/line.html) of the median gap
per year, with RT's May 2024 audience-score change marked.

**Pick for the sheet:** A as the main view, B as the per-genre summary, and
C as the detail list for the current filter.

---

## T4. How has the popularity of genres changed over time?

*Discover / compare → trend per category.* Data: year × genre family ×
(number of releases, IMDb votes, real box office, Netflix chart weight).
data-to-viz path: [time series, several groups](https://www.data-to-viz.com/story/TwoNumOrdered.html).

| # | Chart | Encoding | Good at | Weak at |
|---|---|---|---|---|
| A | [**Streamgraph**](https://www.data-to-viz.com/graph/streamgraph.html) | x = year, stream thickness = genre's value, colour = genre family | Engaging and memorable; shows big shifts (e.g. superhero/sci-fi boom) at a glance | Hard to read exact values or compare non-adjacent streams; the wiggle baseline distorts |
| B | [**Stacked area (100 %)**](https://www.data-to-viz.com/graph/stackedarea.html) | x = year, y = share of the total, layers = genre families | Shows *share* (composition) honestly, and a brush on x gives the global year filter | Only the bottom layer has a common baseline, so the upper layers are hard to read ([caveat](https://www.data-to-viz.com/graph/stackedarea.html)) |
| C | [**Line chart, small multiples**](https://www.data-to-viz.com/graph/line.html) | One small panel per genre family with the same x and y; the other genres in grey behind | The most precise for comparing trends; avoids the [spaghetti](https://www.data-to-viz.com/caveat/spaghetti.html) problem ([caveat: small multiples](https://www.data-to-viz.com/caveat/small_multiple.html)) | Takes more space; less of an immediate overview |

**Pick for the sheet:** C for accuracy, with B as the compact overview that
also holds the time brush. A is a good candidate for one of the "different"
designs on sheets 2–4.

---

## T5. Does a higher budget lead to greater popularity and better ratings?

*Discover → correlation, compared across genres.* Data: budget (real USD),
IMDb votes (popularity), ratings, genre. data-to-viz path:
[three numeric variables](https://www.data-to-viz.com/story/ThreeNum.html)
plus a category.

| # | Chart | Encoding | Good at | Weak at |
|---|---|---|---|---|
| A | [**Bubble chart**](https://www.data-to-viz.com/graph/bubble.html) | x = budget (log), y = rating, size = IMDb votes, colour = genre family | Puts all three measures in one view; blockbusters stand out | Sizes are read poorly ([radius vs area](https://www.data-to-viz.com/caveat/radius_or_area.html)); thousands of bubbles overlap |
| B | [**Scatter plot, small multiples per genre**](https://www.data-to-viz.com/graph/scatter.html) | One panel per genre family: x = budget (log), y = rating (or votes, switchable), each with a trend line | Directly answers "does it differ by genre?", since each panel's slope can be compared | Many panels; small multiples need shared axes and enough films per genre |
| C | [**Heatmap**](https://www.data-to-viz.com/graph/heatmap.html) | Rows = genre families, columns = budget deciles, colour = median rating (switch: median votes) | A compact, aggregated answer; clear patterns such as "rating flat but votes rise with budget" | Hides the spread inside each cell; the choice of bins changes the picture ([caveat](https://www.data-to-viz.com/caveat/bin_size.html)) |

**Pick for the sheet:** B. It shares its axes with the T2 scatter, so one
scatter view with a "split by genre" switch can serve both tasks.

---

## T6. How do ratings and earnings change across a film series? Do sequels get worse?

*Browse / compare → trend within a series, outliers.* Data: franchise →
ordered installments, rating, real revenue, budget. data-to-viz path:
[ordered numeric per group](https://www.data-to-viz.com/story/TwoNumOrdered.html).

| # | Chart | Encoding | Good at | Weak at |
|---|---|---|---|---|
| A | [**Line chart (highlighted spaghetti)**](https://www.data-to-viz.com/graph/line.html) | x = installment number, y = rating (or revenue relative to the first film); all franchises in light grey, the selected ones highlighted, the median as a bold line | Shows the general "sequel curve" and lets you pick out individual franchises ([caveat: spaghetti](https://www.data-to-viz.com/caveat/spaghetti.html), solved by highlighting) | Busy without good highlighting; the y-axis has to be relative (Δ vs the first film) to compare franchises fairly |
| B | [**Connected scatter plot**](https://www.data-to-viz.com/graph/connectedscatter.html) | x = real revenue (log), y = rating, points of one franchise connected in installment order with arrows | Shows money and quality *together*: does a franchise lose both, or keep earning while the ratings drop? | Readable only for 1–3 franchises at once; [counter-intuitive](https://www.data-to-viz.com/caveat/counter_intuitive.html) for new users |
| C | [**Heatmap**](https://www.data-to-viz.com/graph/heatmap.html) | Rows = franchises (≥ 3 films), columns = installment 1…n, colour = change vs the first film (diverging) | Browses hundreds of franchises at once; the exceptions (franchises that get better) are easy to spot after sorting | No absolute values; long franchises make the grid sparse |

**Pick for the sheet:** A as the main view, with B as a detail when one
franchise is selected. C is the alternative for a "browse everything" design.

---

## How the picks could link (idea for sheet 5)

| View | Serves | Linked by |
|---|---|---|
| Choropleth + stacked bars | T1 | click a country → filters the other views to its charts |
| Small-multiple lines / stacked area | T4 | brush years → global year filter; hover a genre → highlighted everywhere |
| Scatter (axis presets, split by genre) | T2, T3, T5 | brush films → highlighted in the franchise view and the timeline |
| Highlighted line chart | T6 | pick a franchise → its films are highlighted in the scatter |

That is four linked views; the course asks for 3+.
