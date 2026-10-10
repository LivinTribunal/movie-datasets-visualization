import json
from pathlib import Path

import httpx
import pytest

from movies import paths
from movies.acquire import download
from movies.acquire.sources import Source

SRC = Source(name="src", description="d", kind="http", version="1")


def make_lock(name: str, files: dict[str, int]) -> dict:
    return {
        name: {
            "version": "1",
            "files": {rel: {"bytes": n, "sha256": "x"} for rel, n in files.items()},
        }
    }


@pytest.fixture
def data_root(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    monkeypatch.setattr(paths, "DATA", tmp_path)
    monkeypatch.setattr(paths, "RAW", tmp_path / "raw")
    monkeypatch.setattr(paths, "LOCK", tmp_path / "sources.lock.json")
    (tmp_path / "raw" / "src").mkdir(parents=True)
    return tmp_path


def test_matching_files_are_skipped(data_root: Path):
    (data_root / "raw/src/a.csv").write_bytes(b"12345")
    lock = make_lock("src", {"raw/src/a.csv": 5})
    assert download.is_up_to_date(lock, SRC, paths.DATA)


def test_size_mismatch_or_missing_file_is_not_skipped(data_root: Path):
    (data_root / "raw/src/a.csv").write_bytes(b"123")
    assert not download.is_up_to_date(make_lock("src", {"raw/src/a.csv": 5}), SRC, paths.DATA)
    assert not download.is_up_to_date(make_lock("src", {"raw/src/b.csv": 3}), SRC, paths.DATA)
    assert not download.is_up_to_date({}, SRC, paths.DATA)


def test_leftover_part_file_does_not_count(data_root: Path):
    (data_root / "raw/src" / download.PART_NAME).write_bytes(b"12345")
    assert not download.is_up_to_date(make_lock("src", {"raw/src/a.csv": 5}), SRC, paths.DATA)


def test_lock_roundtrip_is_sorted(data_root: Path):
    download.save_lock({"b": {"x": 1}, "a": {"y": 2}}, paths.LOCK)
    text = paths.LOCK.read_text()
    assert list(json.loads(text)) == ["a", "b"]
    assert text.index('"a"') < text.index('"b"')


def test_bumped_source_version_is_redownloaded(data_root: Path, monkeypatch: pytest.MonkeyPatch):
    (data_root / "raw/src/a.csv").write_bytes(b"12345")
    download.save_lock(
        {
            "src": {
                "version": "1",
                "url": "https://example.invalid/a.csv",
                "files": {"raw/src/a.csv": {"bytes": 5, "sha256": "x"}},
            }
        },
        paths.LOCK,
    )
    calls: list[str] = []

    def fake_fetch_http(client, src, dest_dir):
        calls.append(src.version)
        f = dest_dir / "a.csv"
        f.write_bytes(b"new-data")
        return [f]

    monkeypatch.setattr(download, "fetch_http", fake_fetch_http)
    src = Source(
        name="src",
        description="d",
        kind="http",
        version="2",
        urls=(("a.csv", "https://example.invalid/a.csv"),),
    )
    download.acquire_source(src)
    assert calls == ["2"], "lock says version 1, registry says 2: must re-download"
    assert download.load_lock(paths.LOCK)["src"]["version"] == "2"


def test_kaggle_single_file_rejects_html_page(tmp_path: Path):
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, content=b"<!DOCTYPE html><html>login</html>")

    client = httpx.Client(transport=httpx.MockTransport(handler))
    src = Source(name="k", description="d", kind="kaggle", ref="o/s", files=("a.csv",), version="1")
    with pytest.raises(RuntimeError, match="returned HTML instead of data"):
        download.fetch_kaggle(client, src, tmp_path)
    assert not (tmp_path / "a.csv").exists()


def test_interrupted_save_lock_keeps_old_lock(data_root: Path, monkeypatch: pytest.MonkeyPatch):
    original = {"a": {"files": {"raw/a.csv": {"bytes": 1, "sha256": "x"}}}}
    download.save_lock(original, paths.LOCK)

    def dying_write_text(self, data, *args, **kwargs):
        with self.open("w") as f:  # process dies mid-write: half the text lands
            f.write(data[: len(data) // 2])
        raise KeyboardInterrupt

    with monkeypatch.context() as m:
        m.setattr(Path, "write_text", dying_write_text)
        with pytest.raises(KeyboardInterrupt):
            download.save_lock({"b": {"files": {}}, "c": {"files": {}}}, paths.LOCK)
    assert download.load_lock(paths.LOCK) == original


def test_request_throttles_per_host(monkeypatch: pytest.MonkeyPatch):
    clock = [100.0]
    sleeps: list[float] = []

    def fake_sleep(seconds: float) -> None:
        sleeps.append(seconds)
        clock[0] += seconds

    monkeypatch.setattr(download.time, "sleep", fake_sleep)
    monkeypatch.setattr(download.time, "monotonic", lambda: clock[0])
    monkeypatch.setattr(download, "_last_request", {})
    client = httpx.Client(
        transport=httpx.MockTransport(lambda r: httpx.Response(200, content=b"x"))
    )

    download.request(client, "GET", "https://a.example/1")
    assert sleeps == []
    download.request(client, "GET", "https://b.example/1")
    assert sleeps == []
    download.request(client, "GET", "https://a.example/2")
    assert sleeps == [pytest.approx(1.0)]
