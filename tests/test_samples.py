import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
import geography as geo
import samples as sp


@pytest.fixture
def d():
    base = pd.DataFrame({
        "settlement_id": [sp.FLORIDA, sp.SAN_PEDRO, "R1", sp.SANTIAGO, "U1"],
        "settlement_name": ["Florida", "San Pedro", "One", "Santiago", "Island"],
        "type": [geo.RURAL] * 3 + [geo.CITY, geo.UNCLASSIFIED],
        "ranked": [True] * 4 + [False], "spatial_model": [True] * 4 + [False],
        "avg_pop": [1000.0, 2000.0, 499.5, 6000.0, 900.0],
        "position": [.25, .5, .75, 1, np.nan], "out_rate": .1, "in_rate": .2})
    later = base.assign(avg_pop=[1000.0, 2000.0, 500.0, 6000.0, 900.0])
    return pd.concat([base.assign(year=1982), base.assign(year=1992), later.assign(year=2002)], ignore_index=True)


def spec(name):
    return next(s for s in sp.SPECS if s.name == name)


def count(d, name):
    return sp.select(d, spec(name)).groupby("year").size().tolist()


def test_primary_keeps_every_ranked_settlement(d):
    out = sp.select(d, spec("unweighted"))
    assert len(out) == d.ranked.sum() and (out.weight == 1).all()


def test_population_threshold_applies_period_by_period_and_is_inclusive(d):
    assert count(d, "min_500") == [3, 3, 4]


def test_florida_and_san_pedro(d):
    assert count(d, "no_florida_san_pedro") == [2, 2, 2]
    assert count(d, "no_florida_san_pedro_2002") == [4, 4, 2]


def test_weights_are_period_specific_average_population(d):
    out = sp.select(d, spec("weighted"))
    assert (out.weight == out.avg_pop).all()
    assert set(out.loc[out.settlement_id == "R1", "weight"]) == {499.5, 500.0}


@pytest.mark.parametrize("name", [s.name for s in sp.SPECS])
def test_selection_never_changes_measures(d, name):
    before = d.copy()
    out = sp.select(d, spec(name))
    pd.testing.assert_frame_equal(d, before)
    pd.testing.assert_frame_equal(out[d.columns], d.loc[out.index])


def test_log_weights(d):
    out = sp.select(d, spec("log_weighted"))
    assert np.allclose(out.weight, np.log(out.avg_pop)) and len(out) == d.ranked.sum()


def test_log_weights_are_far_less_concentrated(d):
    one = d[d.year == 1982]
    plain = sp.select(one, spec("weighted")).weight
    logged = sp.select(one, spec("log_weighted")).weight
    assert sp.effective_size(logged) > sp.effective_size(plain)
    assert logged.max() / logged.sum() < plain.max() / plain.sum()


def test_population_of_one_has_no_usable_log_weight(d):
    with pytest.raises(sp.SampleError, match="weight"):
        sp.select(d.assign(avg_pop=1.0), spec("log_weighted"))


def test_leave_santiago_out(d):
    out = sp.select(d, spec("no_santiago"))
    assert sp.SANTIAGO not in set(out.settlement_id) and count(d, "no_santiago") == [3, 3, 3]
    assert (out.weight == 1).all()


def test_roles():
    roles = {s.name: s.role for s in sp.SPECS}
    assert [n for n, x in roles.items() if x == "primary"] == ["unweighted"]
    assert {n for n, x in roles.items() if x == "supplementary"} == {"weighted", "log_weighted"}
    assert set(roles.values()) == set(sp.ROLES) and len(roles) == len(sp.SPECS)


def test_unknown_weight_stops(d):
    with pytest.raises(sp.SampleError, match="unknown weight"):
        sp.select(d, sp.Spec("x", "", weight="origin_pop"))


def test_unranked_islands_never_selected(d):
    for s in sp.SPECS:
        assert "U1" not in set(sp.select(d, s).settlement_id)


def test_effective_size():
    assert sp.effective_size(pd.Series([1.0] * 10)) == pytest.approx(10)
    assert sp.effective_size(pd.Series([1e9, 1, 1])) == pytest.approx(1)


@pytest.mark.parametrize("damage", [
    lambda d: d.assign(settlement_name="Other"),
    lambda d: d.assign(out_rate=np.nan)])
def test_bad_tables_stop(d, damage):
    with pytest.raises(sp.SampleError):
        sp.select(damage(d), spec("no_florida_san_pedro"))


def test_zero_weight_stops(d):
    with pytest.raises(sp.SampleError, match="weight"):
        sp.select(d.assign(avg_pop=0.0), spec("weighted"))
