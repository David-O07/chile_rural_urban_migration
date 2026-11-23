"""Structure checks on synthetic matrices, plus checks on the real files if present."""

import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
import chim

real = pytest.mark.skipif(not (chim.CHIM / "flows").exists(), reason="raw data not downloaded")


def toy():
    labels = ["A", "B", "C"]
    return pd.DataFrame({"tmhabmun": labels * 3, "tm5ymun": np.repeat(labels, 3),
                         "freq": [90, 8, 2, 5, 40, 5, 10, 0, 20]})


def test_layout_accepts_regular_matrix():
    assert chim.check_layout(toy(), 3) == ["A", "B", "C"]


@pytest.mark.parametrize("damage, message", [
    (lambda d: d.iloc[:-1], "rows"),
    (lambda d: d.iloc[[1, 0, *range(2, 9)]], "order"),
    (lambda d: d.assign(freq=-d.freq), "non-negative"),
    (lambda d: d.assign(freq=d.freq / 2), "integers"),
    (lambda d: d.rename(columns={"tm5ymun": "x"}), "columns"),
    (lambda d: d.assign(tmhabmun=["A", "A", "C"] * 3), "repeat"),
])
def test_layout_rejects_damage(damage, message):
    with pytest.raises(chim.ChimError, match=message):
        chim.check_layout(damage(toy()), 3)


def test_census_check_catches_swapped_codes():
    codes = ["1", "2"]
    flows = pd.DataFrame([[90, 0], [0, 900]], index=codes, columns=codes)
    chim.check_against_census(flows, pd.Series([100, 1000], codes))
    with pytest.raises(chim.ChimError, match="implausible"):
        chim.check_against_census(flows, pd.Series([1000, 100], codes))
    with pytest.raises(chim.ChimError, match="order"):
        chim.check_against_census(flows, pd.Series([1000, 100], codes[::-1]))


def test_changed_label_order_is_detected():
    assert chim.fingerprint(["a", "b"]) != chim.fingerprint(["b", "a"])


@real
@pytest.mark.parametrize("year", chim.YEARS)
def test_real_flows_pass_every_check(year):
    from boundaries import read_boundaries
    flows = chim.read_flows(year)
    assert flows.shape == (chim.N, chim.N)
    assert list(flows.index) == list(flows.columns) == list(chim.read_metadata().code)
    chim.check_against_census(flows, read_boundaries(repair=False)[f"Pop_{year}"])


@real
@pytest.mark.parametrize("year", chim.YEARS)
def test_changed_order_stops_the_read(year, monkeypatch):
    monkeypatch.setitem(chim.LABELS_SHA256, year, "something else")
    with pytest.raises(chim.ChimError, match="sequence has changed"):
        chim.read_flows(year)
