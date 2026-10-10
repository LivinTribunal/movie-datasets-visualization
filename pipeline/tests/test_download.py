import json
from pathlib import Path

import pytest

from movies import paths
from movies.acquire import download


def make_lock(name: str, files: dict[str, int]) -> dict:
    return {name: {"files": {rel: {"bytes": n, "sha256": "x"} for rel, n in files.items()}}}


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
    assert download.is_up_to_date(lock, "src", paths.DATA)


def test_size_mismatch_or_missing_file_is_not_skipped(data_root: Path):
    (data_root / "raw/src/a.csv").write_bytes(b"123")
    assert not download.is_up_to_date(make_lock("src", {"raw/src/a.csv": 5}), "src", paths.DATA)
    assert not download.is_up_to_date(make_lock("src", {"raw/src/b.csv": 3}), "src", paths.DATA)
    assert not download.is_up_to_date({}, "src", paths.DATA)


def test_leftover_part_file_does_not_count(data_root: Path):
    (data_root / "raw/src" / download.PART_NAME).write_bytes(b"12345")
    assert not download.is_up_to_date(make_lock("src", {"raw/src/a.csv": 5}), "src", paths.DATA)


def test_lock_roundtrip_is_sorted(data_root: Path):
    download.save_lock({"b": {"x": 1}, "a": {"y": 2}}, paths.LOCK)
    text = paths.LOCK.read_text()
    assert list(json.loads(text)) == ["a", "b"]
    assert text.index('"a"') < text.index('"b"')
