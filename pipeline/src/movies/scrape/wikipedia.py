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
# annotations that are not part of the value
NOISE_TEMPLATE = re.compile(
    r"\{\{\s*(?:estimation|circa|increase|decrease|steady|usdcy|inflation(?:-year)?"
    r"|citation needed|cn|better source needed|better source|dubious|clarify"
    r"|failed verification|according to whom|update needed|when)\s*(?=[|}])",
    re.I,
)
SMALL_TAG = re.compile(r"</?small\b[^>]*>", re.I)
WRAPPER_TEMPLATE = re.compile(
    r"\{\{\s*(?:nowrap|small|plainlist|ubl|unbulleted list|flatlist|hlist)\s*\|", re.I
)
LINK = re.compile(r"\[\[(?:[^\]|]*\|)?([^\]]*)\]\]")

# a list item is split off on these; template pipes are removed first
ITEM_SPLIT = re.compile(r"<br\s*/?>|\n|\|", re.I)
GROSS_SPLIT = re.compile(ITEM_SPLIT.pattern + r"|\s+or\s+", re.I)
CODE_TEMPLATE = re.compile(
    r"\{\{\s*(US\$|USD|GBP|EUR|INR|CN¥|¥|CNY|JPY|KRW|£|€|Euro)\s*\|\s*([^{}|]*?)\s*(?:\|[^{}]*)?\}\}",
    re.I,
)
CURRENCY_TEMPLATE = re.compile(
    r"\{\{\s*currency\s*\|\s*([^{}|]*?)\s*\|\s*([A-Za-z]{3})\s*[^{}]*\}\}", re.I
)
TEMPLATE_CODES = {"US$": "USD", "CN¥": "CNY", "¥": "JPY", "£": "GBP", "€": "EUR", "EURO": "EUR"}
# {{XXX}} is a bare currency code glued to the amount
CODE_ONLY = re.compile(r"\{\{\s*([A-Z]{3})\s*\}\}")
# {{INRConvert|31.6|c}}: the 2nd param is the scale; a number there is a range, left alone
INR_CONVERT = re.compile(
    r"\{\{\s*INRConvert\s*\|\s*(\d[\d,.]*)\s*(?:\|\s*(lc|[clmbk])\s*(?=[|}]))?"
    r"(?:\|\s*[a-z]+\s*=[^{}|]*)*\}\}",
    re.I,
)
INR_SCALES = {
    "c": " crore", "l": " lakh", "lc": " lakh crore", "m": " million", "b": " billion",
    "k": " thousand",
}  # fmt: skip
DASH = re.compile(r"&[nm]dash;|\{\{\s*e?[nm]\s?dash\s*\}\}", re.I)
SPACE = re.compile(r"&nbsp;|&#160;|&thinsp;|\{\{\s*nbsp\s*\}\}", re.I)

# a bare ¥ is left out: Chinese articles use it for yuan, so it is ambiguous
SYMBOLS = {
    "US$": "USD", "USD": "USD", "$": "USD",
    "£": "GBP", "GBP": "GBP",
    "€": "EUR", "EUR": "EUR",
    "₹": "INR", "Rs.": "INR", "Rs": "INR", "INR": "INR",
    "CN¥": "CNY", "RMB": "CNY", "CNY": "CNY",
    "JP¥": "JPY", "JPY": "JPY",
    "₩": "KRW", "KRW": "KRW",
    "A$": "AUD", "AU$": "AUD", "AUD": "AUD",
    "C$": "CAD", "CA$": "CAD", "CAD$": "CAD", "CAD": "CAD",
    "HK$": "HKD", "HKD": "HKD",
    "R$": "BRL", "BRL": "BRL",
    "MX$": "MXN", "NZ$": "NZD", "S$": "SGD", "NT$": "TWD",
    "₽": "RUB", "₣": "FRF", "FF": "FRF", "DM": "DEM",
}  # fmt: skip
CURRENCY = re.compile(
    "("
    + "|".join(re.escape(s) for s in sorted(SYMBOLS, key=len, reverse=True))
    + r")(?![A-Za-z])\s*"
)
ISO_CODE = re.compile(r"([A-Z]{3})(?=[\s\d])\s*")
NOT_CODES = {"TBA", "TBD", "USA", "EST", "APX", "UNK"}
UK = re.compile(r"UK\s+")
# a bound is not a value
BOUND = re.compile(r"(?:(?:over|under|less than|at least|more than)\b|[<>≥≤])", re.I)
HEDGE = re.compile(
    r"(?:~|≈|approx(?:imately)?\.?|about\b|around\b|circa\b|c\.|est(?:imated)?\.?)\s*", re.I
)
SCALES = {
    "k": 1e3, "thousand": 1e3,
    "m": 1e6, "mn": 1e6, "mln": 1e6, "mil": 1e6, "million": 1e6, "millions": 1e6,
    "b": 1e9, "bn": 1e9, "billion": 1e9, "billions": 1e9,
    "lakh": 1e5, "lakhs": 1e5, "crore": 1e7, "crores": 1e7,
}  # fmt: skip
UNITS = {
    "swiss franc": "CHF", "belgian franc": "BEF", "franc": "FRF", "lira": "ITL", "lire": "ITL",
    "peseta": "ESP", "deutsche mark": "DEM", "mark": "DEM", "rupee": "INR", "rouble": "RUB",
    "ruble": "RUB", "kronor": "SEK", "yen": "JPY", "yuan": "CNY", "dm": "DEM",
}  # fmt: skip
UNIT = re.compile(r"\s*(" + "|".join(sorted(UNITS, key=len, reverse=True)) + r")s?\b", re.I)
# Indian grouping (1,50,00,000) has groups of two
NUMBER = re.compile(r"\d+(?:,\d{2,3})*(?:\.\d+)?")
WORD = re.compile(r"\s*([A-Za-z]+)")
LAKH_CRORE = re.compile(r"\s*crores?\b", re.I)
RANGE_SEP = re.compile(r"\s*(?:[–—-]|to)\s*", re.I)
# what may follow a gross amount without making it partial (a territory, rentals, a re-release)
GROSS_NOTES = re.compile(
    r"\b(?:original release|box office|worldwide|world|global|total|gross|lifetime|theatrical"
    r"|estimated|approx|est)\b"
)


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


def _strip_noise(text: str) -> str:
    return SMALL_TAG.sub("", _remove_templates(text, NOISE_TEMPLATE))


def _clean(text: str) -> str:
    text = COMMENT.sub("", text)
    text = REF_SELF.sub("", REF.sub("", text))
    text = _strip_noise(_remove_templates(text, NOTE_TEMPLATE))
    text = _unwrap_templates(text, WRAPPER_TEMPLATE)
    text = LINK.sub(r"\1", text)
    text = SPACE.sub(" ", DASH.sub("–", text))
    lines = (re.sub(r"[ \t ]+", " ", line).strip() for line in text.split("\n"))
    return "\n".join(line for line in lines if line)


def field_text(wikitext: str, name: str) -> str | None:
    """Cleaned value of the Infobox film parameter `name`, or None if absent or empty."""
    wikitext = COMMENT.sub("", wikitext)
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


def _amount_at(piece: str, pos: int) -> tuple[str, float | None, str | None, int] | None:
    """(digits, scale factor, currency from a unit word, end) at `pos`; None if unclear."""
    num = NUMBER.match(piece, pos)
    # "500 000": a space as thousands separator is not read
    if not num or re.match(r"\s+\d", piece[num.end() :]):
        return None
    end, factor = num.end(), None
    word = WORD.match(piece, end)
    if word and word[1].lower() in SCALES:
        factor, end = SCALES[word[1].lower()], word.end()
        if word[1].lower() in ("lakh", "lakhs") and (crore := LAKH_CRORE.match(piece, end)):
            factor, end = 1e12, crore.end()
        if word[1].lower() == "mil" and piece[end : end + 1] == ".":
            end += 1
    elif word and word[1].lower() != "to" and not UNIT.match(piece, end):
        # "250K", "5x": letters on the number must be a scale; "5 milion" is a typo, but
        # "$700,000 or $765,000" is an amount followed by a word
        if word.start(1) == end or float(num[0].replace(",", "")) < 1000:
            return None
    unit = UNIT.match(piece, end)
    if not unit:
        return num[0], factor, None, end
    key = " ".join(unit[1].lower().split())
    return num[0], factor, UNITS[key], unit.end()


def _inherits(digits: str) -> bool:
    return "," not in digits and float(digits) < 1000


def _range_values(
    n1: str, f1: float | None, n2: str, f2: float | None
) -> tuple[float, float] | None:
    """Both ends of a range, a bare end taking the other's scale; None if it is no range."""
    if f1 is not None and f2 is None and not _inherits(n2):
        return None  # "$5 million – 2009"
    low = f1 if f1 is not None else (f2 if f2 is not None and _inherits(n1) else 1.0)
    high = f2 if f2 is not None else (f1 if f1 is not None else 1.0)
    return float(n1.replace(",", "")) * low, float(n2.replace(",", "")) * high


def _parse_item(piece: str) -> tuple[float | None, str | None, str]:
    """(amount, ISO currency, text after the amount) of one list item."""
    none = (None, None, "")
    if BOUND.match(piece):
        return none
    while hedge := HEDGE.match(piece):
        piece = piece[hedge.end() :]
    piece = piece[len("UK") :].lstrip() if UK.match(piece) else piece
    prefix = CURRENCY.match(piece)
    code = None
    if prefix:
        code = SYMBOLS[prefix[1]]
    elif (iso := ISO_CODE.match(piece)) and iso[1] not in NOT_CODES:
        code, prefix = iso[1], iso
    first = _amount_at(piece, prefix.end() if prefix else 0)
    if not first:
        return none
    n1, f1, unit, end = first
    amount = float(n1.replace(",", "")) * (f1 or 1.0)
    sep = RANGE_SEP.match(piece, end)
    if sep:
        again = CURRENCY.match(piece, sep.end())
        second = _amount_at(piece, again.end() if again else sep.end())
        values = _range_values(n1, f1, second[0], second[1]) if second else None
        if second and values:
            # a range gives the upper bound, with one scale word covering both ends;
            # consistent with derive/money.py's Wikidata pick, which keeps the largest amount
            amount, unit, end = max(values), unit or second[2], second[3]
    if code and unit:
        return none  # a prefix and a unit word together: not sure which is meant
    currency = code or unit
    if currency is None:
        return none
    return amount, currency, piece[end:].strip()


def _normalise(text: str) -> str:
    text = _strip_noise(text)
    text = CODE_ONLY.sub(r"\1 ", text)
    text = INR_CONVERT.sub(lambda m: f"INR {m[1]}{INR_SCALES.get((m[2] or '').lower(), '')}", text)
    text = CODE_TEMPLATE.sub(
        lambda m: f"{TEMPLATE_CODES.get(m[1].upper(), m[1].upper())} {m[2]}", text
    )
    return CURRENCY_TEMPLATE.sub(lambda m: f"{m[2].upper()} {m[1]}", text)


def _items(text: str, split: re.Pattern[str]) -> list[str]:
    pieces = (p.strip(" *\t") for p in split.split(_normalise(text)))
    return [p for p in pieces if p]


def parse_money(text: str) -> tuple[float | None, str | None]:
    """First item of an infobox money value as (amount, ISO currency); (None, None) if unclear."""
    items = _items(text, ITEM_SPLIT)
    amount, currency, _ = _parse_item(items[0]) if items else (None, None, "")
    return amount, currency


def parse_gross(text: str) -> tuple[float | None, str | None]:
    """First item that is the whole gross: no territory, rentals or re-release qualifier."""
    for item in _items(text, GROSS_SPLIT):
        amount, currency, rest = _parse_item(item)
        # "HK$34.7 million (US$4.4 million)": a converted amount is no qualifier
        paren = re.fullmatch(r"\((.*)\)", rest)
        if paren and (conv := _parse_item(paren[1]))[0] is not None and not conv[2]:
            rest = ""
        words = re.sub(r"[^a-z]+", " ", rest.lower()).strip()
        if amount is not None and (
            words.startswith("equivalent to") or not GROSS_NOTES.sub("", words).strip()
        ):
            return amount, currency
    return None, None


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
    for key, parser in (("budget", parse_money), ("gross", parse_gross)):
        value = field_text(text, key)
        if value is None:
            continue
        out[f"wp_{key}_text"] = value[:TEXT_MAX]
        out[f"wp_{key}"], out[f"wp_{key}_currency"] = parser(value)
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
