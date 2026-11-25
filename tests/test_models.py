import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
import models

X = np.array([0.2, 0.4, 0.6, 0.8, 1.0])
Y = np.array([0.15, 0.11, 0.13, 0.08, 0.09])


def test_matches_hand_calculation():
    r = models.fit(pd.DataFrame({"position": X, "out_rate": Y}), "out_rate")
    A = np.c_[np.ones(5), X]
    inv = np.linalg.inv(A.T @ A)
    b = inv @ A.T @ Y
    e = Y - A @ b
    h = np.diag(A @ inv @ A.T)
    v = inv @ (A.T * (e / (1 - h)) ** 2) @ A @ inv
    se = np.sqrt(v[1, 1])
    t = 3.182446   # 97.5% point of t with n - 2 = 3 degrees of freedom
    assert r["slope"] == pytest.approx(b[1]) and r["intercept"] == pytest.approx(b[0])
    assert r["se"] == pytest.approx(se)
    assert r["ci_low"] == pytest.approx(b[1] - t * se) and r["ci_high"] == pytest.approx(b[1] + t * se)
    assert r["r2"] == pytest.approx(1 - (e @ e) / ((Y - Y.mean()) ** 2).sum())
    assert r["n"] == 5


def test_exact_line_gives_the_slope_back():
    d = pd.DataFrame({"position": X, "in_rate": 0.2 - 0.04 * X})
    assert models.fit(d, "in_rate")["slope"] == pytest.approx(-0.04)


@pytest.mark.skipif(not (models.geo.OUT / "primary" / "measures.csv").exists(), reason="no data")
@pytest.mark.parametrize("geography, sample, n", [("primary", "unweighted", 236),
                         ("historical_boundaries", "unweighted", 228),
                         ("primary", "no_florida_san_pedro", 234)])
def test_samples_and_no_islands(geography, sample, n):
    d = models.load(geography, sample)
    assert (d.groupby("year").size() == n).all() and d.year.nunique() == 3
    assert not (d.type == "unclassified").any()


def test_tenths_hold_every_settlement_once():
    n = 20
    d = pd.DataFrame({"position": np.arange(1, n + 1) / n, "year": 1982,
                      "out_rate": np.arange(1, n + 1) / 100, "in_rate": 0.1})
    t = models.by_tenth(d)
    assert (t.n == 2).all() and len(t) == 10
    assert t.out_rate.iloc[0] == pytest.approx(1.5) and t.out_rate.iloc[-1] == pytest.approx(19.5)
