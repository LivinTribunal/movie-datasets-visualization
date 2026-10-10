"""HTTP download, unzip and the lock file (data/sources.lock.json)."""

import hashlib
import json
import shutil
import time
import zipfile
from datetime import UTC, datetime
from pathlib import Path

import httpx

from movies import paths
from movies.acquire.sources import KAGGLE_API, REGISTRY, Source, get

USER_AGENT = "PV251-movies-vis/0.1 (academic project; stevko.moravik@gmail.com)"
BROWSER_UA = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/128.0 Safari/537.36"
)
CHUNK = 1024 * 1024
RETRIES = 3
BACKOFF = 5.0  # seconds, doubled per attempt
PART_NAME = ".download.part"
MIN_INTERVAL = 1.0  # seconds between request starts to one host

_last_request: dict[str, float] = {}


def make_client(browser: bool = False, timeout: float = 60.0) -> httpx.Client:
    return httpx.Client(
        follow_redirects=True,
        timeout=timeout,
        headers={"User-Agent": BROWSER_UA if browser else USER_AGENT},
    )


def _retry_after(resp: httpx.Response) -> float | None:
    value = resp.headers.get("Retry-After")
    if value is None:
        return None
    try:
        return max(0.0, float(value))
    except ValueError:
        return None


def request(
    client: httpx.Client, method: str, url: str, *, dest: Path | None = None, **kwargs
) -> httpx.Response:
    """Send a request, retrying 429/5xx/connection errors. Streams the body to `dest` if given."""
    host = httpx.URL(url).host
    for attempt in range(RETRIES + 1):
        delay = BACKOFF * 2**attempt
        wait = MIN_INTERVAL - (time.monotonic() - _last_request.get(host, float("-inf")))
        if wait > 0:
            time.sleep(wait)
        _last_request[host] = time.monotonic()
        try:
            with client.stream(method, url, **kwargs) as resp:
                if resp.status_code == 429 or resp.status_code >= 500:
                    if attempt == RETRIES:
                        resp.raise_for_status()
                    delay = _retry_after(resp) or delay
                else:
                    resp.raise_for_status()
                    if dest is None:
                        resp.read()
                    else:
                        with dest.open("wb") as fh:
                            for chunk in resp.iter_bytes(CHUNK):
                                fh.write(chunk)
                    return resp
        except httpx.TransportError:
            if attempt == RETRIES:
                raise
        print(f"  retry {attempt + 1}/{RETRIES} in {delay:.0f}s: {url}", flush=True)
        time.sleep(delay)
    raise RuntimeError("unreachable")


def sha256_of(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as fh:
        while chunk := fh.read(CHUNK):
            digest.update(chunk)
    return digest.hexdigest()


def describe(files: list[Path], data_root: Path) -> dict[str, dict[str, int | str]]:
    return {
        f.relative_to(data_root).as_posix(): {"bytes": f.stat().st_size, "sha256": sha256_of(f)}
        for f in sorted(files)
    }


def load_lock(path: Path) -> dict:
    return json.loads(path.read_text()) if path.exists() else {}


def save_lock(lock: dict, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    part = path.with_suffix(".json.part")
    part.write_text(json.dumps(lock, indent=2, sort_keys=True) + "\n")
    part.replace(path)


def is_up_to_date(lock: dict, src: Source, data_root: Path) -> bool:
    """True when the lock lists `src` at its registry version and every file exists at its size."""
    entry = lock.get(src.name)
    if not entry or not entry.get("files") or entry.get("version") != src.version:
        return False
    for rel, info in entry["files"].items():
        f = data_root / rel
        if not f.is_file() or f.stat().st_size != info["bytes"]:
            return False
    return True


def _check_not_html(path: Path, url: str) -> None:
    with path.open("rb") as fh:
        head = fh.read(512).lstrip().lower()
    if head.startswith((b"<!doctype", b"<html")):
        raise RuntimeError(f"{url} returned HTML instead of data")


def _extract(zip_path: Path, dest_dir: Path) -> list[Path]:
    """Extract every member via a .part file, so a crash leaves no half-written data file."""
    out: list[Path] = []
    with zipfile.ZipFile(zip_path) as zf:
        for member in zf.infolist():
            if member.is_dir():
                continue
            target = (dest_dir / member.filename).resolve()
            if not target.is_relative_to(dest_dir.resolve()):
                raise RuntimeError(f"unsafe path in zip: {member.filename}")
            target.parent.mkdir(parents=True, exist_ok=True)
            part = target.with_name(PART_NAME + ".extract")
            with zf.open(member) as src, part.open("wb") as dst:
                shutil.copyfileobj(src, dst, CHUNK)
            part.replace(target)
            out.append(target)
    return out


def _fetch_file(client: httpx.Client, url: str, final: Path, **kwargs) -> None:
    part = final.parent / PART_NAME
    request(client, "GET", url, dest=part, **kwargs)
    _check_not_html(part, url)
    part.replace(final)


def _kaggle_urls(src: Source) -> list[tuple[str, str, str]]:
    """(label, url, plain filename if not a zip) for each download of a kaggle source."""
    base = f"{KAGGLE_API}/{src.ref}"
    q = f"?datasetVersionNumber={src.version}"
    if not src.files:
        return [(src.ref, base + q, "")]
    return [(f, f"{base}/{f}{q}", f) for f in src.files]


def fetch_kaggle(client: httpx.Client, src: Source, dest_dir: Path) -> list[Path]:
    out: list[Path] = []
    for label, url, plain in _kaggle_urls(src):
        part = dest_dir / PART_NAME
        print(f"  downloading {label} v{src.version}", flush=True)
        request(client, "GET", url, dest=part)
        if zipfile.is_zipfile(part):
            out += _extract(part, dest_dir)
            part.unlink()
        else:
            if not plain:
                raise RuntimeError(f"{url} did not return a zip")
            _check_not_html(part, url)
            final = dest_dir / plain
            part.replace(final)
            out.append(final)
    return out


def fetch_http(client: httpx.Client, src: Source, dest_dir: Path) -> list[Path]:
    out: list[Path] = []
    for filename, url in src.urls:
        print(f"  downloading {url}", flush=True)
        final = dest_dir / filename
        _fetch_file(client, url, final)
        out.append(final)
    return out


def fetch_fx(client: httpx.Client, src: Source, dest_dir: Path) -> list[Path]:
    """World Bank pages merged into one file shaped like a single page: [meta, rows]."""
    filename, url = src.urls[0]
    rows: list[dict] = []
    page, meta = 1, {}
    while True:
        resp = request(
            client,
            "GET",
            url,
            params={"format": "json", "per_page": 20000, "page": page},
        )
        meta, page_rows = resp.json()
        rows += page_rows or []
        print(f"  fx page {page}/{meta['pages']}: {len(rows)} rows", flush=True)
        if page >= meta["pages"]:
            break
        page += 1
    final = dest_dir / filename
    part = dest_dir / PART_NAME
    part.write_text(json.dumps([{**meta, "page": 1, "pages": 1}, rows]))
    part.replace(final)
    return [final]


def acquire_source(src: Source, *, force: bool = False) -> None:
    lock = load_lock(paths.LOCK)
    if not force and is_up_to_date(lock, src, paths.DATA):
        print(f"[{src.name}] up to date, skipped", flush=True)
        return
    print(f"[{src.name}] {src.description}", flush=True)
    started = datetime.now(UTC)
    if src.kind == "wikidata":
        from movies.acquire import wikidata

        url, files = wikidata.ENDPOINT, wikidata.build()
    else:
        dest_dir = paths.RAW / src.name
        dest_dir.mkdir(parents=True, exist_ok=True)
        with make_client(browser=src.browser_ua) as client:
            if src.kind == "kaggle":
                files = fetch_kaggle(client, src, dest_dir)
                url = f"{KAGGLE_API}/{src.ref}"
            elif src.kind == "fx":
                files = fetch_fx(client, src, dest_dir)
                url = src.urls[0][1]
            else:
                files = fetch_http(client, src, dest_dir)
                url = src.urls[0][1] if len(src.urls) == 1 else "; ".join(u for _, u in src.urls)
    lock = load_lock(paths.LOCK)
    lock[src.name] = {
        "url": url,
        "version": src.version,
        "downloaded_at": started.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "files": describe(files, paths.DATA),
    }
    save_lock(lock, paths.LOCK)
    total = sum(f["bytes"] for f in lock[src.name]["files"].values())
    print(f"[{src.name}] done: {len(files)} file(s), {total:,} bytes", flush=True)


def run(names: list[str], *, force: bool = False) -> None:
    """Acquire the named sources, or every non-optional one; always in registry order."""
    if names:
        wanted = {get(n).name for n in names}
        todo = [s for s in REGISTRY if s.name in wanted]
    else:
        todo = [s for s in REGISTRY if not s.optional]
    for src in todo:
        acquire_source(src, force=force)
