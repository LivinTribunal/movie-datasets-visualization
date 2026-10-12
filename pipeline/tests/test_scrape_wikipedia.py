import gzip

import httpx
import pytest

from movies.acquire import download
from movies.scrape import wikipedia as wp

INCEPTION = """{{Infobox film
| name           = Inception
| budget         = $160 million<ref name="Mojo">{{cite Box Office Mojo|id=1375666 |title=Inception
 |access-date=July 7, 2022}}</ref>
| gross          = $839 million<ref name="Mojo" />
}}
'''Inception''' is a 2010 film."""


@pytest.fixture(autouse=True)
def no_sleep(monkeypatch):
    monkeypatch.setattr(download, "MIN_INTERVAL", 0)


@pytest.mark.parametrize(
    ("text", "amount", "currency"),
    [
        ("$160 million", 160e6, "USD"),
        ("US$12.5 million", 12.5e6, "USD"),
        ("{{US$|12,500,000}}", 12.5e6, "USD"),
        ("$839,030,630", 839030630, "USD"),
        ("$1.2 billion", 1.2e9, "USD"),
        ("$5–7 million", 7e6, "USD"),
        ("$5-7 million", 7e6, "USD"),
        ("$5 to 7 million", 7e6, "USD"),
        ("$5 million–$7 million", 7e6, "USD"),
        ("£3.5 million", 3.5e6, "GBP"),
        ("€10 million", 10e6, "EUR"),
        ("₹150 crore", 1.5e9, "INR"),
        ("₹50 lakh", 5e6, "INR"),
        ("{{INR|150 crore}}", 1.5e9, "INR"),
        ("CN¥100 million", 100e6, "CNY"),
        ("{{Currency|5 million|AUD}}", 5e6, "AUD"),
        ("~$5 million", 5e6, "USD"),
        ("est. $5 million", 5e6, "USD"),
        ("$40–50 million (gross)<br />$30 million (net)", 50e6, "USD"),
        ("* $5 million\n* $6 million", 5e6, "USD"),
        ("Unknown", None, None),
        ("kr 20 million", None, None),
        # A: trailing letters after the number must be a known scale
        ("$250K", 250e3, "USD"),
        ("$1.2B", 1.2e9, "USD"),
        ("₹100 crores", 1e9, "INR"),
        ("$5 millions", 5e6, "USD"),
        ("$14.4 mn", 14.4e6, "USD"),
        ("$2.5 mln", 2.5e6, "USD"),
        ("$5 millionaire", None, None),
        ("$5 foo", None, None),
        ("₹1 lakh crore", 1e12, "INR"),
        # C: range scale inheritance
        ("$800,000 – 1 million", 1e6, "USD"),
        ("$750,000-1.2 million", 1.2e6, "USD"),
        ("$5 million – 2009", 5e6, "USD"),
        ("$5 million to 2009", 5e6, "USD"),
        # D: Indian grouping
        ("₹1,50,00,000", 1.5e7, "INR"),
        ("Rs. 10,00,000", 1e6, "INR"),
        # E: space as thousands separator
        ("$500 000", None, None),
        ("$ 1 000 000", None, None),
        # G: bare yen sign is ambiguous
        ("¥2.4 billion", None, None),
        ("JP¥2.4 billion", 2.4e9, "JPY"),
        ("{{JPY|2.4 billion}}", 2.4e9, "JPY"),
        ("RMB 100 million", 100e6, "CNY"),
        ("{{CN¥|100 million}}", 100e6, "CNY"),
        ("300 million yen", 3e8, "JPY"),
        ("50 million yuan", 5e7, "CNY"),
        # H: bounds are not values
        ("over $5 million", None, None),
        ("Under $5 million", None, None),
        ("less than $5 million", None, None),
        ("at least $5 million", None, None),
        ("more than $5 million", None, None),
        ("> $5 million", None, None),
        ("≤$5 million", None, None),
        ("circa $5 million", 5e6, "USD"),
        ("approx. $5 million", 5e6, "USD"),
        # I: ISO prefix, suffix words
        ("SEK 2 million", 2e6, "SEK"),
        ("FRF 10 million", 10e6, "FRF"),
        ("UK £12,000", 12000, "GBP"),
        ("₣5 million", 5e6, "FRF"),
        ("FF 5 million", 5e6, "FRF"),
        ("DM 5 million", 5e6, "DEM"),
        ("1 million francs", 1e6, "FRF"),
        ("56 million Lire", 5.6e7, "ITL"),
        ("5,500,500 francs", 5500500, "FRF"),
        ("3 million Swiss francs", 3e6, "CHF"),
        ("3 million Belgian francs", 3e6, "BEF"),
        ("2 million pesetas", 2e6, "ESP"),
        ("4 million Deutsche Marks", 4e6, "DEM"),
        ("4 million marks", 4e6, "DEM"),
        ("10 million rupees", 1e7, "INR"),
        ("10 million roubles", 1e7, "RUB"),
        ("10 million rubles", 1e7, "RUB"),
        ("10 million kronor", 1e7, "SEK"),
        ("10 million kroner", None, None),
        ("TBA 5 million", None, None),
        # round 2: words after whitespace are not scales
        ("$700,000 or $765,000", 7e5, "USD"),
        ("$1,242,000 or $995,000", 1.242e6, "USD"),
        ("$5 milion", None, None),
        ("$5 millions", 5e6, "USD"),
        ("$5x", None, None),
        ("{{¥|62.9 million}}", 6.29e7, "JPY"),
        ("¥62.9 million", None, None),
        ("MX$5 million", 5e6, "MXN"),
        ("NZ$5 million", 5e6, "NZD"),
        ("S$5 million", 5e6, "SGD"),
        ("NT$5 million", 5e6, "TWD"),
        ("5.4 million DM", 5.4e6, "DEM"),
        ("{{Estimation}} {{INR|6 million}}", 6e6, "INR"),
        # round 3
        ("{{INR}}24 crore", 24e7, "INR"),
        ("{{INR}} 150 million", 150e6, "INR"),
        ("{{HKD}}30 million ({{US$|3.9 million|link=yes}})", 30e6, "HKD"),
        ("{{AUD}}12 million", 12e6, "AUD"),
        ("{{RUB}}690 million", 690e6, "RUB"),
        ("{{TBA}}5 million", None, None),
        ("{{INRConvert|31.6|c|year=1999}}", 31.6e7, "INR"),
        ("{{INRConvert|5|l}}", 5e5, "INR"),
        ("{{INRConvert|2|lc}}", 2e12, "INR"),
        ("{{INRConvert|40|m|year=2010}}", 40e6, "INR"),
        ("{{INRConvert|1.5|b}}", 1.5e9, "INR"),
        ("{{INRConvert|300|k}}", 300e3, "INR"),
        ("{{INRConvert|31.6|year=1999}}", 31.6, "INR"),
        ("{{INRConvert|100|150|c}}", None, None),
        ("{{INRConvert|31.6|x}}", None, None),
        ("CAD$5.9 million", 5.9e6, "CAD"),
        ("₽190 million<br />(~US$2.6 million)", 190e6, "RUB"),
        ("{{£|17 million|long=no|link=yes}} or {{US$|14.5 million|long=no|link=yes}}", 17e6, "GBP"),
        ("{{Euro|3,800,000|link=yes}}", 3.8e6, "EUR"),
        ("{{€|2 million}}", 2e6, "EUR"),
    ],
)
def test_parse_money(text, amount, currency):
    got_amount, got_currency = wp.parse_money(text)
    assert got_currency == currency
    assert got_amount == (pytest.approx(amount) if amount is not None else None)


@pytest.mark.parametrize(
    ("text", "amount", "currency"),
    [
        ("$3.8 million (US and Canada rentals)", None, None),
        ("$77,982 (2001 re-release)", None, None),
        ("$2.15 million (U.S. and Canada rentals)|$4 million (worldwide)", 4e6, "USD"),
        ("$600,000 (U.S.) or $1.25 million", 1.25e6, "USD"),
        ("$839 million", 8.39e8, "USD"),
        ("$3.2 million (worldwide est.)", 3.2e6, "USD"),
        ("4,768,505 admissions (France)", None, None),
        ("$29 million ({{estimation}})", 2.9e7, "USD"),
        (
            "$30.6 million<small>(equivalent to ${{Inflation|US|30.6|1957|2024}} million in 2024)"
            "</small>",
            3.06e7,
            "USD",
        ),
        ("$5.6 million {{USDCY|5638000|1945}}", 5.6e6, "USD"),
        # round 3
        ("$5.45 million{{Better source needed|date=August 2026}}", 5.45e6, "USD"),
        ("$3 million{{dubious|date=May 2026}}", 3e6, "USD"),
        ("HK$34.7 million (US$4.4 million)", 34.7e6, "HKD"),
        ("$4.4 million (US)", None, None),
        ("$3.2 million (U.S. rentals)", None, None),
    ],
)
def test_parse_gross(text, amount, currency):
    got_amount, got_currency = wp.parse_gross(text)
    assert got_currency == currency
    assert got_amount == (pytest.approx(amount) if amount is not None else None)


@pytest.mark.parametrize(
    ("raw", "amount"),
    [
        ("$30&ndash;35 million", 3.5e7),
        ("$30{{ndash}}35 million", 3.5e7),
        ("$30&mdash;35 million", 3.5e7),
        ("{{INR}}125{{endash}}130 crore", 1.3e9),
        ("$30{{emdash}}35 million", 3.5e7),
        ("$5{{nbsp}}million", 5e6),
        ("$5&thinsp;million", 5e6),
    ],
)
def test_clean_entities_then_parse(raw, amount):
    assert wp.parse_money(wp._clean(raw))[0] == pytest.approx(amount)


def test_field_text_ignores_commented_out_param():
    text = "{{Infobox film\n<!--\n| budget = $5 million\n-->\n| gross = $7 million\n}}"
    assert wp.field_text(text, "budget") is None
    text = "{{Infobox film\n<!--\n| budget = $5 million\n-->\n| budget = $9 million\n}}"
    assert wp.field_text(text, "budget") == "$9 million"


def test_field_text_inception():
    assert wp.field_text(INCEPTION, "budget") == "$160 million"
    assert wp.field_text(INCEPTION, "gross") == "$839 million"


def test_field_text_plainlist_spans_lines():
    text = (
        "{{Infobox film\n| gross = {{plainlist|\n* $5 million\n* $6 million\n}}\n| language = x\n}}"
    )
    assert wp.field_text(text, "gross") == "* $5 million\n* $6 million"


def test_field_text_ignores_later_template():
    text = "{{Infobox film\n| name = X\n}}\n{{Other\n| gross = $9 million\n}}"
    assert wp.field_text(text, "gross") is None


def test_field_text_cleans_links_and_nbsp():
    text = (
        "{{Infobox film\n"
        "| budget = [[United States dollar|US$]]&nbsp;5 million{{efn|note}}<!-- x -->\n}}"
    )
    assert wp.field_text(text, "budget") == "US$ 5 million"


def test_field_text_missing_and_empty():
    assert wp.field_text(INCEPTION, "runtime") is None
    assert wp.field_text("{{Infobox film\n| budget = <ref>x</ref>\n}}", "budget") is None


def test_parse_inception():
    assert wp.parse(INCEPTION) == {
        "wp_budget": 160e6,
        "wp_budget_currency": "USD",
        "wp_budget_text": "$160 million",
        "wp_gross": 839e6,
        "wp_gross_currency": "USD",
        "wp_gross_text": "$839 million",
    }


def test_parse_no_infobox():
    assert set(wp.parse("'''X''' is a film.").values()) == {None}


def test_fetch_caches_and_skips(tmp_path):
    calls = []

    def handler(req: httpx.Request) -> httpx.Response:
        calls.append(req.url.path)
        if req.url.path == "/wiki/Inception":
            assert req.url.params["action"] == "raw"
            return httpx.Response(200, text=INCEPTION)
        return httpx.Response(404)

    items = [("tt1", "Inception"), ("tt2", "Nope")]
    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        wp.fetch(items, tmp_path, client)
        assert calls == ["/wiki/Inception", "/wiki/Nope"]
        assert gzip.decompress((tmp_path / "tt1.txt.gz").read_bytes()).decode() == INCEPTION
        assert (tmp_path / "tt2.missing").exists()
        wp.fetch(items, tmp_path, client)
    assert len(calls) == 2


def test_fetch_follows_redirect_once(tmp_path):
    calls = []

    def handler(req: httpx.Request) -> httpx.Response:
        calls.append((req.url.path, req.url.params["action"]))
        if req.url.path == "/wiki/Old_title":
            return httpx.Response(200, text="#REDIRECT [[Target#Section]]")
        return httpx.Response(200, text=INCEPTION)

    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        wp.fetch([("tt1", "Old title")], tmp_path, client)
    assert calls == [("/wiki/Old_title", "raw"), ("/wiki/Target", "raw")]
    assert gzip.decompress((tmp_path / "tt1.txt.gz").read_bytes()).decode() == INCEPTION
