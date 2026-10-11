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
        ("¥2.4 billion", 2.4e9, "JPY"),
        ("CN¥100 million", 100e6, "CNY"),
        ("{{Currency|5 million|AUD}}", 5e6, "AUD"),
        ("~$5 million", 5e6, "USD"),
        ("est. $5 million", 5e6, "USD"),
        ("at least $5 million", 5e6, "USD"),
        ("$40–50 million (gross)<br />$30 million (net)", 50e6, "USD"),
        ("* $5 million\n* $6 million", 5e6, "USD"),
        ("Unknown", None, None),
        ("kr 20 million", None, None),
    ],
)
def test_parse_money(text, amount, currency):
    got_amount, got_currency = wp.parse_money(text)
    assert got_currency == currency
    assert got_amount == (pytest.approx(amount) if amount is not None else None)


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
