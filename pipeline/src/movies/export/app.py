"""Export stage: the app's data files, written to app/public/data/.

Pure functions build the frames; the `write_*` functions turn them into `MXP1` packs (see
`pack.py`), `to_columns` into columnar JSON for the small reference tables. Only `run()` reads
data/interim. Output is deterministic (sorted, no timestamps) so a re-run gives no diff.
"""

import json
import math
import shutil
from pathlib import Path

import polars as pl

from movies import paths
from movies.derive.extras import DETAIL_COLUMNS
from movies.export.pack import Col, dict_col, list_col, num, str_col, write_pack
from movies.validate.app import SCHEMA

NOTES = [
    "Money is converted at release-year World Bank rates and inflated with CPI to 2025 USD.",
    "Films before 1913 have no 2025 USD value (the CPI series starts in 1913), and neither do"
    " non-USD amounts from a year without a World Bank rate.",
    "Budgets under $1,000 and revenues under $10,000 are dropped as unreliable.",
    "Money comes from The Numbers, else TMDB, else Wikidata, else the Wikipedia infobox"
    " (budget_src, revenue_src); a few amounts checked by hand as wrong are skipped.",
    "Fuzzy title matches to The Numbers are flagged (money_fuzzy, numbers_fuzzy).",
    "Genre shares use 1/n weights: a film with n genres counts 1/n in each.",
    "The TMDB average is null under 50 votes.",
    "Rotten Tomatoes scores of films from 2023 on come from the RT pages (October 2026), older"
    " ones from the April 2023 Clapper dump; newer audience scores are often RT's verified score.",
    "Netflix shares cover only matched titles; see the coverage column.",
    "The IMDb series on the genre timeline counts every feature film on IMDb (non-commercial"
    " dataset, 2026-11-17), and short films before 1920; IMDb genres are mapped to TMDB genres"
    " (Sci-Fi → Science Fiction, Musical → Music, Film-Noir → Crime, Biography → History),"
    " Sport, News and Short are dropped.",
    "Scores are on 0–100: IMDb, TMDB and Metacritic users ×10, Letterboxd ×20. "
    "The Metacritic user score is null under 10 user ratings.",
]
EXTRA_NOTES = [
    "Opening weekend (US only) and estimated home-video sales are inflated with CPI to 2025 USD;"
    " both come from The Numbers.",
    "Home-video sales are The Numbers' estimates.",
    "Story source comes from The Numbers, else from the first TMDB keyword that names one"
    " (story_source_src); a film with neither has none.",
    "Studio is the group of the first production company that is one of eight major groups,"
    " else independent.",
    "Oscar nominations and wins are counted from Wikidata award statements, one per nomination.",
]
CINEMA_NOTES = [
    "Cinema genre shares come from LUMIERE admissions of notable films only; UK and Ireland "
    "admissions are LUMIERE estimates, and the combined UK+Ireland market counts as the UK.",
]
ATTRIBUTION = [
    "This product uses the TMDB API but is not endorsed or certified by TMDB.",
    "IMDb ratings and votes come from IMDb data via the TMDB+IMDb Kaggle dataset;"
    " non-commercial use.",
    "Information courtesy of IMDb (https://www.imdb.com). Used with permission.",
    "Wikidata (CC0), Wikipedia (CC BY-SA 4.0), World Bank (CC BY 4.0), Natural Earth (public"
    " domain), FRED / BLS (public domain), Netflix Top 10, Rotten Tomatoes, Metacritic,"
    " Letterboxd, The Numbers, LUMIERE (European Audiovisual Observatory).",
]
SOURCES = {
    "netflix": "Netflix Top 10 chart scores for 94 countries, 2021 to 2026, counted only for"
    " titles matched to a film; it says nothing about what people watch outside Netflix.",
    "cinema": "Cinema admissions for 36 European markets from LUMIERE (1996 to 2025, notable"
    " films only) and The Numbers domestic gross for the US (1980 to 2024); it leaves out every"
    " other market, and a market-year needs at least 20 films to be shown.",
    "production": "Genre weight of each film made in a country, 1900 to 2026, for films with"
    " at least 1,000 IMDb votes; it shows what a country makes, not what its audience watches,"
    " and a co-production counts in each of its countries.",
}
MONEY_COLUMNS = ["budget_usd", "budget_usd2025", "revenue_usd", "revenue_usd2025", "roi"]
MONEY_SOURCES = ["numbers", "tmdb", "wikidata", "wikipedia"]
FLAG_COLUMNS = [
    "budget_converted",
    "revenue_converted",
    "budget_disagree",
    "revenue_disagree",
    "money_fuzzy",
    "numbers_fuzzy",
]
STORY_SOURCES = ["original", "book", "comic", "true_story", "stage", "screen", "other"]
STORY_ORIGINS = ["numbers", "tmdb"]
AGE_RATINGS = ["G", "PG", "PG-13", "R", "NC-17", "NR"]
STUDIOS = [
    "disney",
    "warner",
    "universal",
    "sony",
    "paramount",
    "fox",
    "lionsgate",
    "mgm",
    "independent",
]
EXTRA_F32 = ["opening_usd", "opening_usd2025", "legs", "video_usd2025"]
DETAIL_SHARD = 1000
RATING_COLUMNS = [
    "imdb_100",
    "tmdb_100",
    "tomatometer_100",
    "audience_100",
    "metascore_100",
    "mc_user_100",
    "letterboxd_100",
]
FILM_COLUMNS = [
    "imdb_id",
    "tmdb_id",
    "title",
    "director",
    "poster",
    "notable",
    "year",
    "runtime",
    "imdb_votes",
    "genres",
    "families",
    "countries",
    *MONEY_COLUMNS,
    "budget_src",
    "revenue_src",
    *FLAG_COLUMNS,
    *RATING_COLUMNS,
    "gap",
    "mc_critic_reviews",
    "collection_id",
    "installment",
    "story_source",
    "story_source_src",
    "age_rating",
    "studio",
    *EXTRA_F32,
    "theaters",
    "oscar_wins",
    "oscar_noms",
]
FRANCHISE_RATINGS = ["imdb_100", "tomatometer_100", "audience_100"]
FRANCHISE_COLUMNS = [
    "collection_id",
    "collection_name",
    "installment",
    "n_released",
    "tmdb_id",
    "film_row",
    "year",
    "family_mask",
    *FRANCHISE_RATINGS,
    "imdb_100_vs_first",
    "revenue_usd2025",
    "revenue_vs_first",
    "title",
]
MEASURES = ["chart_score", "admissions", "gross_usd", "films"]
U8_NULL, U16_NULL, U32_NULL, I16_NULL = 255, 65535, 2**32 - 1, -32768
REMOVED = ["films.json", "genre_year.json", "country_genre.json", "franchises.json"]


def _converted(name: str, currency: str) -> pl.Expr:
    return (
        (pl.col(currency).is_not_null() & (pl.col(currency) != "USD")).fill_null(False).alias(name)
    )


def films_table(
    films: pl.DataFrame,
    money: pl.DataFrame,
    ratings: pl.DataFrame,
    film_genres: pl.DataFrame,
    franchises: pl.DataFrame,
    extras: pl.DataFrame,
) -> pl.DataFrame:
    """Every film, most voted first, in logical form (lists and booleans, not yet bit-packed)."""
    genres = film_genres.group_by("imdb_id", maintain_order=True).agg(
        genres=pl.col("genre"), families=pl.col("family").unique(maintain_order=True)
    )
    parts = (
        franchises.drop_nulls("imdb_id")
        .sort("collection_id", "installment")
        .unique("imdb_id", keep="first", maintain_order=True)
        .select("imdb_id", "collection_id", "installment")
    )
    return (
        films.drop("genres", strict=False)  # the raw TMDB list, still with "TV Movie"
        .join(money, on="imdb_id", how="left")
        .join(ratings, on="imdb_id", how="left")
        .join(genres, on="imdb_id", how="left")
        .join(parts, on="imdb_id", how="left")
        .join(extras.drop(DETAIL_COLUMNS), on="imdb_id", how="left")
        .with_columns(
            pl.col("genres").fill_null([]),
            pl.col("families").fill_null([]),
            _converted("budget_converted", "budget_currency"),
            _converted("revenue_converted", "revenue_currency"),
            pl.col("budget_disagree").fill_null(False),
            pl.col("revenue_disagree").fill_null(False),
            pl.col("numbers_fuzzy").fill_null(False),
            money_fuzzy=(
                (pl.col("numbers_match") == "fuzzy")
                & ((pl.col("budget_src") == "numbers") | (pl.col("revenue_src") == "numbers"))
            ).fill_null(False),
            countries=pl.col("production_countries").fill_null([]),
            poster=pl.col("poster_path"),
        )
        .select(FILM_COLUMNS)
        .sort(["imdb_votes", "imdb_id"], descending=[True, False])
    )


def _mask(lists: pl.Series, order: list[str]) -> pl.Series:
    bit = {name: 1 << i for i, name in enumerate(order)}
    return pl.Series([sum(bit[v] for v in set(items or [])) for items in lists.to_list()])


def write_films(
    df: pl.DataFrame,
    genres: list[str],
    families: list[str],
    countries: list[str],
    core_path: Path,
    text_path: Path,
    poster_path: Path,
) -> None:
    """Write films.pack (numbers, masks, flags), films_text.pack and films_poster.pack."""
    flags = pl.sum_horizontal(
        pl.col(c).cast(pl.UInt8) * (1 << i) for i, c in enumerate(FLAG_COLUMNS)
    )
    flag_series = df.select(flags.alias("flags"))["flags"]
    imdb = df["imdb_id"].str.slice(2).cast(pl.UInt32)
    cols = [
        num("imdb", imdb, "u32"),
        num("tmdb_id", df["tmdb_id"], "u32", null=U32_NULL),
        num("year", df["year"], "u16"),
        num("runtime", df["runtime"], "u16", null=U16_NULL),
        num("imdb_votes", df["imdb_votes"], "u32"),
        num("genre_mask", _mask(df["genres"], genres), "u32"),
        num("family_mask", _mask(df["families"], families), "u8"),
        list_col("countries", df["countries"], sorted(countries)),
        *(num(c, df[c], "f32") for c in MONEY_COLUMNS),
        dict_col("budget_src", df["budget_src"], MONEY_SOURCES, null=U8_NULL),
        dict_col("revenue_src", df["revenue_src"], MONEY_SOURCES, null=U8_NULL),
        num("flags", flag_series, "u8"),
        *(num(c, df[c], "u16", scale=0.1, null=U16_NULL) for c in RATING_COLUMNS),
        num("gap", df["gap"], "i16", scale=0.1, null=I16_NULL),
        num("mc_critic_reviews", df["mc_critic_reviews"], "u16", null=U16_NULL),
        num("collection_id", df["collection_id"], "u32", null=U32_NULL),
        num("installment", df["installment"], "u8", null=U8_NULL),
        dict_col("story_source", df["story_source"], STORY_SOURCES, null=U8_NULL),
        dict_col("story_source_src", df["story_source_src"], STORY_ORIGINS, null=U8_NULL),
        dict_col("age_rating", df["age_rating"], AGE_RATINGS, null=U8_NULL),
        dict_col("studio", df["studio"], STUDIOS, null=U8_NULL),
        *(num(c, df[c], "f32") for c in EXTRA_F32),
        num("theaters", df["theaters"], "u16", null=U16_NULL),
        num("oscar_wins", df["oscar_wins"], "u8", null=U8_NULL),
        num("oscar_noms", df["oscar_noms"], "u8", null=U8_NULL),
    ]
    meta = {"notable": int(df["notable"].sum()), "genres": genres, "families": families}
    write_pack(core_path, df.height, meta, cols)
    write_pack(text_path, df.height, {}, [str_col(c, df[c]) for c in ("title", "director")])
    write_pack(poster_path, df.height, {}, [str_col("poster", df["poster"])])


def write_detail(df: pl.DataFrame, notable: int, out_dir: Path) -> int:
    """Write films_detail_{k}.pack for the first `notable` rows, `DETAIL_SHARD` rows each.

    Stale films_detail_*.pack files are deleted first. Returns the number of shards.
    """
    for stale in out_dir.glob("films_detail_*.pack"):
        stale.unlink()
    shards = math.ceil(notable / DETAIL_SHARD)
    for k in range(shards):
        start = k * DETAIL_SHARD
        part = df.slice(start, min(start + DETAIL_SHARD, notable) - start)
        cols = [str_col(c, part[c]) for c in DETAIL_COLUMNS]
        write_pack(out_dir / f"films_detail_{k}.pack", part.height, {}, cols)
    return shards


def country_tables(
    sources: list[tuple[str, str, pl.DataFrame]], genres: list[str]
) -> tuple[pl.DataFrame, pl.DataFrame]:
    """The `country_genre` and `country_year` frames from (source, measure, frame) triples."""
    index = {g: i for i, g in enumerate(genres)}
    long = pl.concat(
        [
            df.select(
                source=pl.lit(source),
                measure=pl.lit(measure),
                country=pl.col("country_iso2"),
                year=pl.col("year").cast(pl.Int16),
                genre=pl.col("genre").replace_strict(index, return_dtype=pl.UInt8),
                score=pl.col("score").cast(pl.Float64),
                entries=pl.col("entries").cast(pl.UInt32),
                coverage=pl.col("coverage").cast(pl.Float64),
                fuzzy_share=pl.col("fuzzy_share").cast(pl.Float64),
                estimated_share=pl.col("estimated_share").cast(pl.Float64),
            )
            for source, measure, df in sources
        ]
    )
    country_genre = long.select("source", "country", "year", "genre", "score").sort(
        "source", "country", "year", "genre"
    )
    country_year = (
        long.group_by("source", "measure", "country", "year")
        .agg(
            entries=pl.col("entries").max(),
            coverage=pl.col("coverage").first(),
            fuzzy_share=pl.col("fuzzy_share").first(),
            estimated_share=pl.col("estimated_share").first(),
        )
        .select(
            "source",
            "country",
            "year",
            "entries",
            "coverage",
            "fuzzy_share",
            "estimated_share",
            "measure",
        )
        .sort("source", "country", "year")
    )
    return country_genre, country_year


def write_country_tables(
    country_genre: pl.DataFrame,
    country_year: pl.DataFrame,
    genres: list[str],
    countries: list[str],
    genre_path: Path,
    year_path: Path,
) -> None:
    sources = sorted(country_genre["source"].unique())
    codes = sorted(countries)
    width = 1 if len(codes) <= 256 else 2

    def keys(df: pl.DataFrame) -> list[Col]:
        return [
            dict_col("source", df["source"], sources),
            dict_col("country", df["country"], codes, width=width),
            num("year", df["year"], "u16"),
        ]

    meta = {"genres": genres}
    cols = [*keys(country_genre), num("genre", country_genre["genre"], "u8")]
    cols.append(num("score", country_genre["score"], "f32"))
    write_pack(genre_path, country_genre.height, meta, cols)
    cols = [
        *keys(country_year),
        num("entries", country_year["entries"], "u32"),
        *(num(c, country_year[c], "f32") for c in ("coverage", "fuzzy_share", "estimated_share")),
        dict_col("measure", country_year["measure"], MEASURES),
    ]
    write_pack(year_path, country_year.height, {}, cols)


def franchises_table(
    franchises: pl.DataFrame,
    films_out: pl.DataFrame,
    film_genres: pl.DataFrame,
    families: list[str],
) -> pl.DataFrame:
    """Franchise parts with their `films.pack` row, year and the first part's family mask."""
    rows = films_out.with_row_index("film_row").select("imdb_id", "film_row")
    part_families = dict(film_genres.group_by("imdb_id").agg(pl.col("family").unique()).iter_rows())
    ordered = franchises.sort("collection_id", "installment")
    first_mask: dict[int, int] = {}
    for collection_id, imdb_id in ordered.select("collection_id", "imdb_id").iter_rows():
        if collection_id not in first_mask and imdb_id in part_families:
            first_mask[collection_id] = sum(1 << families.index(f) for f in part_families[imdb_id])
    return (
        ordered.join(rows, on="imdb_id", how="left")
        .with_columns(
            year=pl.col("release_date").dt.year(),
            family_mask=pl.col("collection_id").map_elements(
                lambda c: first_mask.get(c, 0), return_dtype=pl.Int64
            ),
        )
        .select(FRANCHISE_COLUMNS)
    )


def write_franchises(df: pl.DataFrame, path: Path) -> None:
    names = df.unique("collection_id").sort("collection_id")
    meta = {
        "collections": [[i, n] for i, n in names.select("collection_id", "collection_name").rows()]
    }
    cols = [
        num("collection_id", df["collection_id"], "u32"),
        num("installment", df["installment"], "u8"),
        num("n_released", df["n_released"], "u8"),
        num("tmdb_id", df["tmdb_id"], "u32"),
        num("film_row", df["film_row"], "u32", null=U32_NULL),
        num("year", df["year"], "u16"),
        num("family_mask", df["family_mask"], "u8"),
        *(num(c, df[c], "u16", scale=0.1, null=U16_NULL) for c in FRANCHISE_RATINGS),
        num("imdb_100_vs_first", df["imdb_100_vs_first"], "i16", scale=0.1, null=I16_NULL),
        num("revenue_usd2025", df["revenue_usd2025"], "f32"),
        num("revenue_vs_first", df["revenue_vs_first"], "f32"),
        str_col("title", df["title"]),
    ]
    write_pack(path, df.height, meta, cols)


def to_columns(df: pl.DataFrame) -> dict[str, list]:
    return {c: df[c].to_list() for c in df.columns}


def _write(path: Path, obj: dict) -> None:
    path.write_text(json.dumps(obj, separators=(",", ":"), ensure_ascii=False))
    print(f"{path.name}: {path.stat().st_size / 1e6:.2f} MB")


def _write_table(name: str, df: pl.DataFrame) -> None:
    _write(paths.APP_DATA / name, {"columns": to_columns(df)})


def run() -> None:
    interim = paths.INTERIM
    films = pl.read_parquet(interim / "films.parquet")
    money = pl.read_parquet(interim / "money.parquet")
    ratings = pl.read_parquet(interim / "ratings.parquet")
    fg = pl.read_parquet(interim / "film_genres.parquet")
    franchises = pl.read_parquet(interim / "franchises.parquet")
    extras = pl.read_parquet(interim / "extras.parquet")
    paths.APP_DATA.mkdir(parents=True, exist_ok=True)
    for name in REMOVED:
        (paths.APP_DATA / name).unlink(missing_ok=True)

    countries = pl.read_csv(
        paths.REFERENCE / "countries.csv", schema_overrides={"iso_numeric": pl.String}
    )
    families = pl.read_csv(paths.REFERENCE / "genre_families.csv")
    genres = families["genre"].to_list()
    family_names = families.unique("family").sort("family_order")["family"].to_list()
    _write_table("countries.json", countries.select(SCHEMA["countries.json"]))
    _write_table("genre_families.json", families.select(SCHEMA["genre_families.json"]))

    films_out = films_table(films, money, ratings, fg, franchises, extras)
    write_films(
        films_out,
        genres,
        family_names,
        countries["iso2"].to_list(),
        paths.APP_DATA / "films.pack",
        paths.APP_DATA / "films_text.pack",
        paths.APP_DATA / "films_poster.pack",
    )

    inputs = [
        ("netflix", "chart_score", "country_genre_netflix"),
        ("cinema", "admissions", "country_genre_lumiere"),
        ("cinema", "gross_usd", "country_genre_us"),
        ("production", "films", "country_genre_production"),
    ]
    sources = []
    for source, measure, stem in inputs:
        path = interim / f"{stem}.parquet"
        if path.exists():
            sources.append((source, measure, pl.read_parquet(path)))
        else:
            print(f"{stem} skipped: file not found, run `movies derive`")
    country_genre, country_year = country_tables(sources, genres)
    write_country_tables(
        country_genre,
        country_year,
        genres,
        countries["iso2"].to_list(),
        paths.APP_DATA / "country_genre.pack",
        paths.APP_DATA / "country_year.pack",
    )

    imdb_path = interim / "imdb_genre_year.parquet"
    imdb = pl.read_parquet(imdb_path) if imdb_path.exists() else None
    if imdb is not None:
        per_year = imdb.unique("year")
        write_pack(
            paths.APP_DATA / "imdb_genre_year.pack",
            imdb.height,
            {"genres": genres},
            [
                num("year", imdb["year"], "u16"),
                num(
                    "genre",
                    imdb["genre"].replace_strict(genres, range(len(genres)), return_dtype=pl.UInt8),
                    "u8",
                ),
                num("score", imdb["score"], "f32"),
                num("entries", imdb["entries"], "u32"),
                num("shorts", imdb["shorts"], "u32"),
            ],
        )
    else:
        print("imdb_genre_year skipped: file not found, run `movies derive`")

    notable = int(films_out["notable"].sum())
    detail = films_out.select("imdb_id").join(
        extras.select("imdb_id", *DETAIL_COLUMNS), on="imdb_id", how="left"
    )
    shards = write_detail(detail, notable, paths.APP_DATA)
    detail_mb = sum(f.stat().st_size for f in paths.APP_DATA.glob("films_detail_*.pack")) / 1e6
    print(f"films_detail_*.pack: {shards} shards, {detail_mb:.2f} MB")

    franchises_out = franchises_table(franchises, films_out, fg, family_names)
    write_franchises(franchises_out, paths.APP_DATA / "franchises.pack")
    for name in (
        "films.pack",
        "films_text.pack",
        "films_poster.pack",
        "country_genre.pack",
        "country_year.pack",
        "franchises.pack",
        "imdb_genre_year.pack",
    ):
        if not (paths.APP_DATA / name).exists():
            continue
        print(f"{name}: {(paths.APP_DATA / name).stat().st_size / 1e6:.2f} MB")

    shutil.copyfile(
        paths.RAW / "world_atlas" / "countries-50m.json", paths.APP_DATA / "countries.topo.json"
    )

    def n_countries(source: str) -> int:
        return country_year.filter(pl.col("source") == source)["country"].n_unique()

    has_cinema = n_countries("cinema") > 0
    _write(
        paths.APP_DATA / "meta.json",
        {
            "snapshots": {"tmdb_imdb": "2026-10-01", "netflix": "2026-09-27", "imdb": "2026-11-17"},
            "base_year": 2025,
            "counts": {
                "films": films_out.height,
                "notable": notable,
                "with_budget": films_out["budget_usd2025"].count(),
                "with_revenue": films_out["revenue_usd2025"].count(),
                "with_gap": films_out["gap"].count(),
                "with_opening": films_out["opening_usd"].count(),
                "with_story_source": films_out["story_source"].count(),
                "with_oscars": int((films_out["oscar_noms"] > 0).sum()),
                "netflix_countries": n_countries("netflix"),
                "cinema_markets": n_countries("cinema"),
                "production_countries": n_countries("production"),
                "franchises": franchises_out["collection_id"].n_unique(),
                "imdb_films": int(per_year["entries"].sum()) if imdb is not None else 0,
                "imdb_shorts": int(per_year["shorts"].sum()) if imdb is not None else 0,
            },
            "detail": {"shard_size": DETAIL_SHARD, "shards": shards},
            "notes": NOTES + EXTRA_NOTES + (CINEMA_NOTES if has_cinema else []),
            "attribution": ATTRIBUTION,
            "sources": SOURCES,
        },
    )
