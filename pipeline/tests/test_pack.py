import gzip
import math
import struct

import polars as pl
import pytest

from movies.export.pack import dict_col, list_col, num, read_pack, str_col, write_pack


def _roundtrip(tmp_path, col, rows):
    path = tmp_path / "t.pack"
    write_pack(path, rows, {"k": 1}, [col])
    return read_pack(path)


def test_u8_and_u32_roundtrip(tmp_path):
    pack = _roundtrip(tmp_path, num("a", pl.Series([0, 255]), "u8"), 2)
    assert pack.columns["a"] == [0, 255]
    assert pack.meta == {"k": 1} and pack.rows == 2
    pack = _roundtrip(tmp_path, num("a", pl.Series([0, 2**32 - 1]), "u32"), 2)
    assert pack.columns["a"] == [0, 2**32 - 1]


def test_u16_scale_and_null(tmp_path):
    col = num("a", pl.Series([70.04, None, 100.0]), "u16", scale=0.1, null=65535)
    assert col.header["scale"] == 0.1 and col.header["null"] == 65535
    assert _roundtrip(tmp_path, col, 3).columns["a"] == [70.0, None, 100.0]


def test_i16_scale_and_null(tmp_path):
    col = num("a", pl.Series([-5.0, None, 5.04]), "i16", scale=0.1, null=-32768)
    assert _roundtrip(tmp_path, col, 3).columns["a"] == [-5.0, None, 5.0]


def test_f32_nan_is_null(tmp_path):
    col = num("a", pl.Series([1.5, None, 2.0], dtype=pl.Float64), "f32")
    assert _roundtrip(tmp_path, col, 3).columns["a"] == [1.5, None, 2.0]
    assert math.isnan(struct.unpack_from("<f", col.data, 4)[0])


def test_dict_with_null(tmp_path):
    col = dict_col("a", pl.Series(["x", None, "y"]), ["x", "y"], null=255)
    assert _roundtrip(tmp_path, col, 3).columns["a"] == ["x", None, "y"]


def test_list_with_empty_list(tmp_path):
    series = pl.Series([["x", "y"], [], None, ["y"]], dtype=pl.List(pl.String))
    col = list_col("a", series, ["x", "y"])
    assert _roundtrip(tmp_path, col, 4).columns["a"] == [["x", "y"], [], [], ["y"]]


def test_str_null_and_non_ascii(tmp_path):
    col = str_col("a", pl.Series(["Amélie", None, "千と千尋"]))
    assert _roundtrip(tmp_path, col, 3).columns["a"] == ["Amélie", None, "千と千尋"]


def test_offsets_are_multiples_of_eight_and_output_is_deterministic(tmp_path):
    cols = [
        num("a", pl.Series([1, 2, 3]), "u8"),
        str_col("b", pl.Series(["a", "bb", "ccc"])),
        num("c", pl.Series([1, 2, 3]), "u16"),
    ]
    first, second = tmp_path / "1.pack", tmp_path / "2.pack"
    write_pack(first, 3, {}, cols)
    write_pack(second, 3, {}, cols)
    assert first.read_bytes() == second.read_bytes()
    raw = gzip.decompress(first.read_bytes())
    assert raw[:4] == b"MXP1"
    assert (8 + struct.unpack_from("<I", raw, 4)[0]) % 8 == 0
    header = read_pack(first).header
    assert all(c["offset"] % 8 == 0 for c in header["columns"])


def test_num_rejects_null_without_sentinel_and_out_of_range():
    with pytest.raises(ValueError, match="a"):
        num("a", pl.Series([1, None]), "u16")
    with pytest.raises(ValueError, match="a"):
        num("a", pl.Series([300]), "u8")
    with pytest.raises(ValueError, match="a"):
        num("a", pl.Series([65535]), "u16", null=65535)


def test_dict_col_rejects_unknown_value():
    with pytest.raises(ValueError, match="a"):
        dict_col("a", pl.Series(["z"]), ["x"])
