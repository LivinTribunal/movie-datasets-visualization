import gzip

import httpx
import pytest

from movies.acquire import download
from movies.scrape import lumiere

HEAD = (
    '<th class="sticky">Market</th><th>Distributor</th><th class="nowrap">Release date</th>'
    '<th class="nowrap">Total since 1998</th><th>2012</th><th>2013</th><th>2020</th><th>2023</th>'
)


def page(rows: str, note: str = "", head: str = HEAD) -> str:
    return (
        '<html><div class="tab-pane" id="other"><table><tr><td>x</td></tr></table></div>'
        '<div class="tab-pane active" id="admissions"><table class="scrolltable">'
        f"<tr>{head}</tr>{rows}</table>{note}</div></html>"
    )


AT = (
    '<tr><td class="sticky">AT</td><td class="nowrap">Disney</td><td>05/04/2012</td>'
    '<td class="nowrap fw-bold nb">1 513 951 </td><td class="nowrap nb">1 389 000 </td>'
    '<td class="nowrap nb"></td><td class="nb">2&nbsp;500</td><td class="nb">12\xa0000</td></tr>'
)
GB_IE = (
    '<tr><td class="sticky">GB_IE</td><td>Sony</td><td>01/01/2012</td><td class="nb">900 </td>'
    '<td class="nb"></td><td class="nb">900 </td><td class="nb"></td><td class="nb"></td></tr>'
)
IE = (
    '<tr><td class="sticky">IE</td><td>Sony</td><td>01/01/2012</td><td class="nb">5 </td>'
    '<td class="nb">5 </td><td class="nb"></td><td class="nb"></td><td class="nb"></td></tr>'
)


@pytest.fixture(autouse=True)
def no_sleep(monkeypatch):
    monkeypatch.setattr(download, "MIN_INTERVAL", 0)


def test_parse_rows_gaps_separators_and_total_ignored():
    got = lumiere.parse(page(AT + GB_IE))
    assert [(r["market"], r["year"], r["admissions"]) for r in got] == [
        ("AT", 2012, 1389000),
        ("AT", 2020, 2500),
        ("AT", 2023, 12000),
        ("GB_IE", 2013, 900),
    ]
    assert not any(r["estimated"] for r in got)


def test_parse_estimated_markets():
    note = "<p>* Estimated admissions for the following markets: GB_IE, IE</p>"
    got = lumiere.parse(page(AT + GB_IE + IE, note))
    flags = {r["market"]: r["estimated"] for r in got}
    assert flags == {"AT": False, "GB_IE": True, "IE": True}


def test_parse_no_admissions_table():
    assert lumiere.parse("<html><div id='info'><table></table></div></html>") == []


def test_fetch_404_cached_as_missing_cached_skipped_and_200_gzipped(tmp_path):
    (tmp_path / "tt1.html.gz").write_bytes(gzip.compress(b"x"))
    requested = []

    def handler(req: httpx.Request) -> httpx.Response:
        requested.append(req.url.path)
        if req.url.path == "/movie/9":
            return httpx.Response(404)
        return httpx.Response(200, text="<html>ok</html>")

    items = [("tt1", "1"), ("tt2", "9"), ("tt3", "3")]
    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        lumiere.fetch(items, tmp_path, client)
    assert requested == ["/movie/9", "/movie/3"]
    assert (tmp_path / "tt2.missing").exists()
    assert gzip.decompress((tmp_path / "tt3.html.gz").read_bytes()) == b"<html>ok</html>"
