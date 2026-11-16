"""`MXP1` pack files: typed column buffers behind a JSON header, gzipped.

Layout (little-endian, before gzip): `MXP1`, u32 header length H, the JSON header padded with
spaces so that 8 + H is a multiple of 8, then the column buffers in header order, each
zero-padded to start at a multiple of 8. Format spec: docs/superpowers/specs
/2026-11-16-movie-explorer-app-design.md §2.1. Stdlib only; output is byte-for-byte
deterministic (gzip mtime 0, no file name).
"""

import gzip
import json
import math
import struct
from dataclasses import dataclass
from pathlib import Path

import polars as pl

MAGIC = b"MXP1"
# type -> (struct format, byte width, lowest raw value, highest raw value)
_NUM = {
    "u8": ("B", 1, 0, 2**8 - 1),
    "u16": ("H", 2, 0, 2**16 - 1),
    "i16": ("h", 2, -(2**15), 2**15 - 1),
    "u32": ("I", 4, 0, 2**32 - 1),
}
_WIDTH = {1: "B", 2: "H"}


@dataclass(frozen=True)
class Col:
    header: dict
    data: bytes


@dataclass(frozen=True)
class Pack:
    rows: int
    meta: dict
    header: dict
    columns: dict[str, list]


def _pack(fmt: str, values: list) -> bytes:
    return struct.pack(f"<{len(values)}{fmt}", *values)


def _missing(value: object) -> bool:
    return value is None or (isinstance(value, float) and math.isnan(value))


def num(
    name: str,
    series: pl.Series,
    type: str,
    *,
    scale: float | None = None,
    null: int | None = None,
) -> Col:
    header: dict = {"name": name, "type": type}
    if scale is not None:
        header["scale"] = scale
    if type == "f32":
        raw = [
            math.nan if _missing(v) else (v / scale if scale is not None else float(v))
            for v in series.to_list()
        ]
        return Col(header, _pack("f", raw))
    fmt, _, lo, hi = _NUM[type]
    if null is not None:
        header["null"] = null
    raw = []
    for v in series.to_list():
        if _missing(v):
            if null is None:
                raise ValueError(f"{name}: null value but no null sentinel")
            raw.append(null)
            continue
        r = round(v / scale) if scale is not None else int(v)
        if not lo <= r <= hi:
            raise ValueError(f"{name}: value {v} does not fit {type}")
        if r == null:
            raise ValueError(f"{name}: value {v} equals the null sentinel {null}")
        raw.append(r)
    return Col(header, _pack(fmt, raw))


def dict_col(
    name: str, series: pl.Series, values: list[str], *, width: int = 1, null: int | None = None
) -> Col:
    index = {v: i for i, v in enumerate(values)}
    codes = []
    for v in series.to_list():
        if v is None:
            if null is None:
                raise ValueError(f"{name}: null value but no null sentinel")
            codes.append(null)
        elif v in index:
            codes.append(index[v])
        else:
            raise ValueError(f"{name}: value {v!r} is not in the dictionary")
    header: dict = {"name": name, "type": "dict", "width": width, "values": values}
    if null is not None:
        header["null"] = null
    return Col(header, _pack(_WIDTH[width], codes))


def list_col(name: str, series: pl.Series, values: list[str]) -> Col:
    index = {v: i for i, v in enumerate(values)}
    offsets, codes = [0], []
    for items in series.to_list():
        for v in items or []:
            if v not in index:
                raise ValueError(f"{name}: value {v!r} is not in the dictionary")
            codes.append(index[v])
        offsets.append(len(codes))
    header = {"name": name, "type": "list", "values": values}
    return Col(header, _pack("I", offsets) + _pack("H", codes))


def str_col(name: str, series: pl.Series) -> Col:
    offsets, blob = [0], bytearray()
    for v in series.to_list():
        blob += (v or "").encode("utf-8")
        offsets.append(len(blob))
    return Col({"name": name, "type": "str"}, _pack("I", offsets) + bytes(blob))


def _pad(n: int) -> int:
    return -n % 8


def write_pack(path: Path, rows: int, meta: dict, cols: list[Col]) -> None:
    body = bytearray()
    headers = []
    for col in cols:
        body += bytes(_pad(len(body)))
        headers.append({**col.header, "offset": len(body), "length": len(col.data)})
        body += col.data
    head = json.dumps(
        {"rows": rows, "meta": meta, "columns": headers}, separators=(",", ":"), ensure_ascii=False
    ).encode("utf-8")
    head += b" " * _pad(8 + len(head))
    raw = MAGIC + struct.pack("<I", len(head)) + head + bytes(body)
    path.write_bytes(gzip.compress(raw, compresslevel=9, mtime=0))


def _decode(col: dict, buf: bytes, rows: int) -> list:
    kind, start = col["type"], col["offset"]
    if kind in _NUM or kind == "f32":
        fmt = "f" if kind == "f32" else _NUM[kind][0]
        raw = struct.unpack_from(f"<{rows}{fmt}", buf, start)
        scale, null = col.get("scale"), col.get("null")
        if kind == "f32":
            return [None if math.isnan(v) else (v * scale if scale else v) for v in raw]
        return [None if v == null else (round(v * scale, 6) if scale else v) for v in raw]
    if kind == "dict":
        raw = struct.unpack_from(f"<{rows}{_WIDTH[col['width']]}", buf, start)
        return [None if v == col.get("null") else col["values"][v] for v in raw]
    offsets = struct.unpack_from(f"<{rows + 1}I", buf, start)
    body = start + 4 * (rows + 1)
    if kind == "list":
        codes = struct.unpack_from(f"<{offsets[-1]}H", buf, body)
        return [
            [col["values"][c] for c in codes[a:b]]
            for a, b in zip(offsets, offsets[1:], strict=False)
        ]
    blob = buf[body : body + offsets[-1]]
    return [blob[a:b].decode("utf-8") or None for a, b in zip(offsets, offsets[1:], strict=False)]


def read_pack(path: Path) -> Pack:
    raw = gzip.decompress(path.read_bytes())
    if raw[:4] != MAGIC:
        raise ValueError(f"{path.name}: not an MXP1 pack")
    (n,) = struct.unpack_from("<I", raw, 4)
    header = json.loads(raw[8 : 8 + n])
    data = raw[8 + n :]
    rows = header["rows"]
    columns = {c["name"]: _decode(c, data, rows) for c in header["columns"]}
    return Pack(rows, header["meta"], header, columns)
