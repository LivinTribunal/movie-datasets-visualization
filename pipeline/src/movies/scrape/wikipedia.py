"""English Wikipedia: budget and gross from the Infobox film of every notable film's article.

`https://en.wikipedia.org/wiki/{title}?action=raw` returns the raw wikitext (robots.txt disallows
/w/, so not api.php, but allows article URLs); at most 1 request per second per host. A
`#REDIRECT [[Target]]` is followed once, and the target's text is cached under the film's own id.
Every article is cached gzipped in data/cache/wikipedia/<imdb_id>.txt.gz (a 404 as an empty
<imdb_id>.missing) and the parser reads only from that cache, so an interrupted run resumes and a
re-run makes no request for a film it has already seen. Any other HTTP error raises.

The parsed amounts are as written on the article (nominal, in the stated currency): `wp_*_text`
keeps the cleaned field text so the parser can be audited.
"""

import gzip
import re
from pathlib import Path
from urllib.parse import quote

import httpx
import polars as pl

from movies import paths
from movies.acquire.download import get_following, make_client

URL = "https://en.wikipedia.org/wiki/{}?action=raw"
OUT = "wikipedia.parquet"
CACHE_DIR = paths.CACHE / "wikipedia"
PROGRESS_EVERY = 500
TEXT_MAX = 200

SCHEMA = {
    "imdb_id": pl.String,
    "enwiki_title": pl.String,
    "wp_budget": pl.Float64,
    "wp_budget_currency": pl.String,
    "wp_budget_text": pl.String,
    "wp_gross": pl.Float64,
    "wp_gross_currency": pl.String,
    "wp_gross_text": pl.String,
}
FIELDS = [k for k in SCHEMA if k not in ("imdb_id", "enwiki_title")]

REDIRECT = re.compile(r"\s*#redirect\s*:?\s*\[\[([^\]|#]+)", re.I)
INFOBOX = re.compile(r"\{\{\s*infobox film", re.I)
BRACES = re.compile(r"\{\{|\}\}")
COMMENT = re.compile(r"<!--.*?-->", re.S)
REF_SELF = re.compile(r"<ref\b[^>]*?/>", re.I)
REF = re.compile(r"<ref\b[^>]*>.*?</ref>", re.I | re.S)
NOTE_TEMPLATE = re.compile(r"\{\{\s*(?:efn|refn|sfn|sfnp)\b", re.I)
WRAPPER_TEMPLATE = re.compile(
    r"\{\{\s*(?:nowrap|small|plainlist|ubl|unbulleted list|flatlist|hlist)\s*\|", re.I
)
LINK = re.compile(r"\[\[(?:[^\]|]*\|)?([^\]]*)\]\]")

# a list item is split off on these; template pipes are removed first
ITEM_SPLIT = re.compile(r"<br\s*/?>|\n|\|", re.I)
CODE_TEMPLATE = re.compile(
    r"\{\{\s*(US\$|USD|GBP|EUR|INR|CN¥|CNY|JPY|KRW)\s*\|\s*([^{}|]*?)\s*(?:\|[^{}]*)?\}\}", re.I
)
CURRENCY_TEMPLATE = re.compile(
    r"\{\{\s*currency\s*\|\s*([^{}|]*?)\s*\|\s*([A-Za-z]{3})\s*[^{}]*\}\}", re.I
)
TEMPLATE_CODES = {"US$": "USD", "CN¥": "CNY"}

SYMBOLS = {
    "US$": "USD", "USD": "USD", "$": "USD",
    "£": "GBP", "GBP": "GBP",
    "€": "EUR", "EUR": "EUR",
    "₹": "INR", "Rs.": "INR", "Rs": "INR", "INR": "INR",
    "CN¥": "CNY", "RMB": "CNY", "CNY": "CNY",
    "JP¥": "JPY", "¥": "JPY", "JPY": "JPY",
    "₩": "KRW", "KRW": "KRW",
    "A$": "AUD", "AU$": "AUD", "AUD": "AUD",
    "C$": "CAD", "CA$": "CAD", "CAD": "CAD",
    "HK$": "HKD", "HKD": "HKD",
    "R$": "BRL", "BRL": "BRL",
}  # fmt: skip
CURRENCY = re.compile(
    "("
    + "|".join(re.escape(s) for s in sorted(SYMBOLS, key=len, reverse=True))
    + r")(?![A-Za-z])\s*"
)
HEDGE = re.compile(
    r"(?:~|≈|approx(?:imately)?\.?|about|around|circa|c\.|est(?:imated)?\.?|over|under"
    r"|at least|less than)\s*",
    re.I,
)
SCALES = {
    "thousand": 1e3, "million": 1e6, "mil": 1e6, "m": 1e6, "billion": 1e9, "bn": 1e9,
    "lakh crore": 1e12, "lakh": 1e5, "crore": 1e7,
}  # fmt: skip
NUMBER = re.compile(
    r"(\d+(?:,\d{3})*(?:\.\d+)?)\s*"
    r"(lakh crore|thousand|million|mil\.?|billion|bn|lakh|crore|m(?![A-Za-z]))?(?![A-Za-z])",
    re.I,
)
RANGE_SEP = re.compile(r"\s*(?:[–—-]|to)\s*", re.I)


def _match_end(text: str, start: int) -> int:
    """Index just after the `}}` that closes the `{{` at `start`, or -1 if it never closes."""
    depth = 0
    for token in BRACES.finditer(text, start):
        depth += 1 if token.group() == "{{" else -1
        if depth == 0:
            return token.end()
    return -1


def _remove_templates(text: str, opener: re.Pattern[str]) -> str:
    while match := opener.search(text):
        end = _match_end(text, match.start())
        text = text[: match.start()] + (text[end:] if end > 0 else text[match.end() :])
    return text


def _unwrap_templates(text: str, opener: re.Pattern[str]) -> str:
    while match := opener.search(text):
        end = _match_end(text, match.start())
        if end > 0:
            text = text[: match.start()] + text[match.end() : end - 2] + text[end:]
        else:
            text = text[: match.start()] + text[match.end() :]
    return text


def _clean(text: str) -> str:
    text = COMMENT.sub("", text)
    text = REF_SELF.sub("", REF.sub("", text))
    text = _remove_templates(text, NOTE_TEMPLATE)
    text = _unwrap_templates(text, WRAPPER_TEMPLATE)
    text = LINK.sub(r"\1", text)
    text = text.replace("&nbsp;", " ").replace("&#160;", " ")
    lines = (re.sub(r"[ \t ]+", " ", line).strip() for line in text.split("\n"))
    return "\n".join(line for line in lines if line)


def field_text(wikitext: str, name: str) -> str | None:
    """Cleaned value of the Infobox film parameter `name`, or None if absent or empty."""
    start = INFOBOX.search(wikitext)
    if not start:
        return None
    end = _match_end(wikitext, start.start())
    # leave out the infobox's own closing braces, then only its parameters remain
    box = wikitext[start.start() : end - 2 if end > 0 else len(wikitext)]
    param = re.compile(rf"^\s*\|\s*{re.escape(name)}\s*=(.*)$", re.I)
    lines = box.split("\n")
    for i, line in enumerate(lines):
        match = param.match(line)
        if not match:
            continue
        value = [match.group(1)]
        depth = line.count("{{") - line.count("}}")
        for nxt in lines[i + 1 :]:
            if depth <= 0 and re.match(r"\s*(\||\}\})", nxt):
                break
            value.append(nxt)
            depth += nxt.count("{{") - nxt.count("}}")
        return _clean("\n".join(value)) or None
    return None


def _scaled(number: str, scale: str | None, default: float) -> float:
    factor = SCALES[scale.lower().rstrip(".")] if scale else default
    return float(number.replace(",", "")) * factor


def parse_money(text: str) -> tuple[float | None, str | None]:
    """First item of an infobox money value as (amount, ISO currency); (None, None) if unclear."""
    text = CODE_TEMPLATE.sub(lambda m: f"{TEMPLATE_CODES.get(m[1], m[1]).upper()} {m[2]}", text)
    text = CURRENCY_TEMPLATE.sub(lambda m: f"{m[2].upper()} {m[1]}", text)
    piece = next((p.strip(" *\t") for p in ITEM_SPLIT.split(text) if p.strip(" *\t")), "")
    while hedge := HEDGE.match(piece):
        piece = piece[hedge.end() :]
    currency = CURRENCY.match(piece)
    if not currency:
        return None, None
    piece = piece[currency.end() :]
    first = NUMBER.match(piece)
    if not first:
        return None, None
    low_scale, high_scale = first[2], first[2]
    amount = _scaled(first[1], first[2], 1.0)
    sep = RANGE_SEP.match(piece, first.end())
    if sep:
        rest = piece[sep.end() :]
        again = CURRENCY.match(rest)
        rest_start = again.end() if again else 0
        second = NUMBER.match(rest, rest_start)
        if second:
            high_scale = second[2]
            # a range gives the upper bound, with one scale word covering both ends;
            # consistent with derive/money.py's Wikidata pick, which keeps the largest amount
            low = _scaled(first[1], low_scale or high_scale, 1.0)
            high = _scaled(second[1], high_scale or low_scale, 1.0)
            amount = max(low, high)
    return amount, SYMBOLS[currency[1]]


def _get(client: httpx.Client, title: str) -> str:
    return get_following(client, URL.format(quote(title.replace(" ", "_"), safe=""))).text


def fetch(items: list[tuple[str, str]], cache_dir: Path, client: httpx.Client) -> None:
    """GET every (imdb_id, title) that is not cached yet; a 404 is cached as `.missing`."""
    cache_dir.mkdir(parents=True, exist_ok=True)
    for n, (imdb_id, title) in enumerate(items, 1):
        target = cache_dir / f"{imdb_id}.txt.gz"
        missing = cache_dir / f"{imdb_id}.missing"
        if not target.exists() and not missing.exists():
            try:
                text = _get(client, title)
                redirect = REDIRECT.match(text)
                if redirect:
                    text = _get(client, redirect.group(1).strip())
            except httpx.HTTPStatusError as err:
                # a 404, or a redirect with nowhere to go, is a page that is not there
                if err.response.status_code != 404 and not err.response.is_redirect:
                    raise
                missing.write_bytes(b"")
            else:
                part = target.with_suffix(".part")
                part.write_bytes(gzip.compress(text.encode()))
                part.replace(target)
        if n % PROGRESS_EVERY == 0 or n == len(items):
            print(f"  {n}/{len(items)}", flush=True)


def parse(text: str) -> dict:
    out: dict = dict.fromkeys(FIELDS)
    for key in ("budget", "gross"):
        value = field_text(text, key)
        if value is None:
            continue
        out[f"wp_{key}_text"] = value[:TEXT_MAX]
        out[f"wp_{key}"], out[f"wp_{key}_currency"] = parse_money(value)
    return out


def build() -> Path:
    films = paths.INTERIM / "films.parquet"
    if not films.exists():
        raise RuntimeError(f"{films} is missing; run `movies join` first")
    # ponytail: notable subset only (~12.9k articles, ~3.6 h at 1 req/s); films that already
    # have money are included on purpose, the values cross-check wrong TMDB ones
    items_df = (
        pl.read_parquet(films, columns=["imdb_id", "notable", "enwiki_title"])
        .filter(pl.col("notable") & pl.col("enwiki_title").is_not_null())
        .select("imdb_id", "enwiki_title")
        .unique("imdb_id")
        .sort("imdb_id")
    )
    items = list(items_df.iter_rows())
    print(f"  {len(items):,} notable films to fetch", flush=True)
    with make_client() as client:
        fetch(items, CACHE_DIR, client)

    rows, n_missing = [], 0
    for imdb_id, title in items:
        page = CACHE_DIR / f"{imdb_id}.txt.gz"
        if page.exists():
            fields = parse(gzip.decompress(page.read_bytes()).decode())
        else:
            fields, n_missing = dict.fromkeys(FIELDS), n_missing + 1
        rows.append({"imdb_id": imdb_id, "enwiki_title": title, **fields})
    out_df = pl.DataFrame(rows, schema=SCHEMA).sort("imdb_id")
    paths.SCRAPED.mkdir(parents=True, exist_ok=True)
    out = paths.SCRAPED / OUT
    out_df.write_parquet(out)

    print(f"  {OUT}: {out_df.height:,} rows, {n_missing:,} missing (404)")
    for field in FIELDS:
        print(f"    {field}: {out_df[field].is_not_null().sum():,}")
    for field in ("wp_budget_currency", "wp_gross_currency"):
        counts = out_df[field].drop_nulls().value_counts(sort=True)
        print(f"    {field}: {dict(counts.iter_rows())}")
    return out
