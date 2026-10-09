**Project topic:** Movies: money, ratings and genre taste around the world.

**Team members** Štefan Moravík, Matúš Buzgo, Emma Tomášová

**Data source:**

- **main dataset:** *The Ultimate 1Million Movies Dataset (TMDB + IMDb):* [https://www.kaggle.com/datasets/alanvourch/tmdb-movies-daily-updates](https://www.kaggle.com/datasets/alanvourch/tmdb-movies-daily-updates)

- we also have additional sources that we want to integrate: Rotten Tomatoes and Metacritic for critics’ and audience ratings, The Numbers and Box Office Mojo for budgets and box office data, Netflix Top 10 and LUMIERE for country-level popularity, and Wikidata for linking and enriching data across sources

**Data description:**

·       *Dataset type/s:* 

**-** **table**: items = movies, multidimensional with many quantitative attributes

**-** **temporal**: release dates 1900s–2026; weekly Netflix charts 2021–2026; yearly box office and admissions per country

**-** **geospatial**: production countries; Netflix, Box Office Mojo and LUMIERE markets, shown on a world map

**-** **hierarchy / multi-valued sets**: franchise → films, region → country; each film has several genres and production countries

·       *Attributes + types:* 

- movies: title (categorical/text), release date (temporal), genre (categorical, multi-valued), production country (categorical/geospatial, multi-valued), language (categorical), budget and revenue (quantitative), profit and ROI (quantitative), runtime (quantitative), IMDb/TMDB ratings (quantitative), …

- critics and audience: audience score, user score and Letterboxd rating (quantitative); RT status (ordinal); critic/user review counts (quantitative),….

- country-level: country/market (categorical/geospatial), year (temporal), rank (ordinal), admissions (quantitative), theatres (quantitative), weekly rank (ordinal)

·       *Size:* 

**TMDB + IMDb:** ≈1.25M movies and 30 attributes.
 **- working subset:** ≈56,000 released films with ≥1,000 IMDb votes
 **- notable subset:** ≈13,000 films with ≥10,000 votes

**Rotten Tomatoes:** ≈21,000 films of the working subset have both RT scores from the Clapper scrape (joined via Wikidata RT IDs)….that is 84 % of notable films released before 2023

**-** for 2023+ releases: ≈5,000 films in the subset, 2,754 of them with a known RT ID, to be scraped

**Money:** the Numbers: ≈ 6,518 films (5,258 matched to the subset)

- wikidata: 10.8k films with budget and/or box office

**Netflix:** 510,340 rows (255,170 film rows), 94 countries, 274 weeks (2021-07-04 → 2026-09-27), 8,716 distinct film titles

·       *Quality and problems:* 

- **missing financial data:** In the working subset, TMDB is missing 72% of budgets and 70% of revenue. Coverage is much better for popular films:

≥1K votes: 28% budget / 30% revenue

≥10K votes: 67% / 73%

≥50K votes: 92% / 93%

- **enrichment:** The Numbers, Wikidata, Wikipedia, and Box Office Mojo improve coverage. For the notable subset, estimated final coverage is \~79% for budget and \~88% for revenue.

- **money consistency:** financial data comes in different formats and currencies, so values need cleaning, currency conversion, and inflation adjustment

- **ratings:** Rotten Tomatoes and Metacritic have different coverage and rating methods; small films may have too few reviews.

- **country data:** Netflix covers **94** countries and only its Top 10; Box Office Mojo and LUMIERE also have incomplete geographic coverage.

- **data matching:** Films from different sources need **fuzzy title matching**.

- **multi-valued data:** Films can have multiple genres and production countries, so we need a consistent counting/weighting method.

**Tasks** (at least 4) – for each task list the task/question as well as action-target-data combination:

**T1: Which genres dominate cinemas and streaming in different countries?**

- *Action:*      Compare
- *Target:*      Distribution / similarity
- *Data/Attributes      needed:* Country, genre, Netflix rankings, box office/admissions

**T2:** **Are commercially successful films also better rated?**

- *Action:*      Discover
- *Target:*      Correlation
- *Data/Attributes      needed:* Budget, revenue/ROI, critic scores, audience ratings

**T3:** **Where do critics and audiences disagree the most?**

- *Action:* Identify / Compare
- *Target:* Outliers / distribution
- *Data/Attributes needed:* Critic scores, audience scores, genre, year

**T4:** **How has the popularity of genres changed over time?**

- *Action:* Discover / Compare
- *Target:* Trend
- *Data/Attributes needed:* Year, genre, popularity, box office, Netflix data

**T5:** **Does a higher budget lead to greater popularity and better ratings?**

- *Action:* Discover
- *Target:* Correlation
- *Data/Attributes needed:* Budget, IMDb votes, ratings, genre

**T6:** **How do ratings and earnings change across film series? Do sequels get worse?**

- *Action:* Browse / Compare
- *Target:* Trend / outliers
- *Data/Attributes needed:* Franchise, installment, ratings, revenue, budget