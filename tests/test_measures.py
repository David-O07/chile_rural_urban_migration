"""Populations, ranks and rates: hand-worked examples, edge cases, then the real data."""

import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
import boundaries as bd
import chim
import geography as geo
import measures as ms

IDS = ["Ra", "Rb", "Fc", "Fd", "Ui"]
FLOWS = pd.DataFrame(np.array([
    [80, 5, 10, 5, 0],
    [2, 40, 5, 3, 0],
    [4, 1, 500, 45, 0],
    [6, 4, 40, 950, 0],
    [0, 0, 3, 2, 5]]), index=IDS, columns=IDS)
TABLE = pd.DataFrame({
    "settlement_id": IDS, "settlement_name": IDS,
    "type": [geo.RURAL, geo.RURAL, geo.CITY, geo.CITY, geo.UNCLASSIFIED],
    "n_municipalities": 1, "ranked": [True] * 4 + [False], "spatial_model": [True] * 4 + [False],
    "area_km2": [100.0, 10.0, 5.0, 8.0, np.nan]})


def one(flows=FLOWS, table=TABLE):
    return ms.measure(table, {2002: flows}).set_index("settlement_id")


# --- populations and denominators ---

def test_populations_by_hand():
    p = one().loc["Ra"]
    assert (p.origin_pop, p.destination_pop, p.avg_pop) == (100, 92, 96)
    assert (p.departures, p.arrivals, p.stayers) == (20, 12, 80)


def test_each_rate_uses_its_own_denominator():
    r = one().loc["Ra"]
    assert r.out_rate == 20 / 100        # origin population
    assert r.in_rate == 12 / 96          # average population
    assert r.out_rate_avg == 20 / 96     # average population
    assert r.in_rate_dest == 12 / 92     # destination population


def test_rates_are_five_year_not_annual():
    """Nothing is divided by five: rate times denominator returns the migrants."""
    d = one()
    assert np.allclose(d.out_rate * d.origin_pop, d.departures)
    assert np.allclose(d.in_rate * d.avg_pop, d.arrivals)


def test_direction():
    """People leaving a for c are departures of a and arrivals of c, never the reverse."""
    more = FLOWS.copy()
    more.loc["Ra", "Fc"] += 100
    before, after = one(), one(more)
    assert after.departures["Ra"] - before.departures["Ra"] == 100
    assert after.arrivals["Fc"] - before.arrivals["Fc"] == 100
    assert after.arrivals["Ra"] == before.arrivals["Ra"]
    assert after.departures["Fc"] == before.departures["Fc"]


def test_moves_with_unranked_islands_count_for_mainland():
    d = one()
    assert d.arrivals["Fc"] == 10 + 5 + 40 + 3   # the last 3 come from the island
    assert d.arrivals.sum() == d.departures.sum()


# --- zero and missing ---

def test_zero_denominator_is_missing_and_flagged():
    f = FLOWS.copy()
    f.loc["Ra"] = 0                      # nobody lived there at the start
    d = one(f)
    assert np.isnan(d.out_rate["Ra"]) and "out_rate missing" in d["notes"]["Ra"]
    assert d.in_rate["Ra"] == 2.0 and d.in_rate_dest["Ra"] == 1.0
    assert "in_rate above 100%" in d["notes"]["Ra"]


def test_empty_settlement_has_no_rates_but_a_rank():
    f = FLOWS.copy()
    f.loc["Ra"] = 0
    f["Ra"] = 0
    d = one(f)
    assert d.loc["Ra", list(ms.RATES)].isna().all()
    assert d.position["Ra"] == 0.25


def test_zero_migrants_is_a_rate_of_zero_not_missing():
    d = one(pd.DataFrame(np.diag([10, 20, 30, 40, 5]), index=IDS, columns=IDS))
    assert (d[list(ms.RATES)] == 0).all().all()


@pytest.mark.parametrize("damage", [
    lambda f: f.astype(float).mask(f == 80),        # missing value
    lambda f: f.replace(80, -80),
    lambda f: f[IDS[::-1]],                         # columns in another order
    lambda f: f.iloc[1:, 1:],                       # a settlement lost
])
def test_bad_matrices_are_rejected(damage):
    with pytest.raises(ms.MeasureError):
        one(damage(FLOWS))


# --- ranks ---

def test_rank_order_by_hand():
    d = one()
    # Densities: Ra 96/100 < Rb 50/10. Cities: Fc 554 < Fd 1002.5.
    assert d.position[IDS[:4]].tolist() == [0.25, 0.5, 0.75, 1.0]
    assert np.isnan(d.position["Ui"])


def test_rural_uses_density_and_cities_use_population():
    t = TABLE.copy()
    t["area_km2"] = [1.0, 1000.0, 50000.0, 1.0, np.nan]   # Ra now denser; Fc very sparse
    assert one(table=t).position[IDS[:4]].tolist() == [0.5, 0.25, 0.75, 1.0]


def test_small_cities_rank_with_cities():
    t = TABLE.assign(type=[geo.RURAL, geo.SMALL_CITY, geo.CITY, geo.CITY, geo.UNCLASSIFIED])
    assert one(table=t).position[IDS[:4]].tolist() == [0.25, 0.5, 0.75, 1.0]


def test_alternative_ranks_use_their_own_population():
    f = pd.DataFrame(np.diag([50, 50, 500, 500, 5]), index=IDS, columns=IDS)
    f.loc["Fc", "Fd"] = 100              # c larger at the start, d larger at the end
    d = one(f)
    assert d.position_origin["Fc"] == 1 and d.position_destination["Fd"] == 1
    assert d.position["Fc"] == d.position["Fd"] == 0.875   # equal averages share the rank


def test_ties_share_the_average_rank():
    f = pd.DataFrame(np.diag([100, 10, 300, 300, 5]), index=IDS, columns=IDS)
    assert one(f).position[IDS[:4]].tolist() == [0.375, 0.375, 0.875, 0.875]


def test_unclassified_settlements_do_not_count_in_the_number_ranked():
    assert one().position.max() == 1 and one().position.notna().sum() == 4


def test_rural_without_area_stops():
    with pytest.raises(ms.MeasureError, match="area"):
        one(table=TABLE.assign(area_km2=[np.nan, 10, 5, 8, np.nan]))


@pytest.mark.parametrize("column, value, message", [
    ("position", 0.9, "normalized|above a city"), ("departures", 1, "reconcile"),
    ("out_rate", 0.5, "numerator"), ("origin_pop", 7, "reconcile")])
def test_validation_catches_tampering(column, value, message):
    d = one()
    d.loc["Ra", column] = value
    with pytest.raises(ms.MeasureError, match=message):
        ms.validate(d, FLOWS)


# --- periods ---

def test_normalized_within_each_period():
    later = FLOWS * 3
    later.loc["Fc", "Fc"] = 9000         # c overtakes d
    d = ms.measure(TABLE, {1992: FLOWS, 2002: later})
    for _, g in d.groupby("year"):
        assert g.position.max() == 1 and g.position.sum() == 2.5
    p = d.pivot(index="settlement_id", columns="year", values="position")
    assert p.loc["Fc"].tolist() == [0.75, 1.0]


@pytest.mark.parametrize("change", [
    lambda d: d.iloc[1:],
    lambda d: pd.concat([d, d.iloc[[0]]]),
    lambda d: d.assign(type=d.type.where(d.index != 0, geo.CITY)),
    lambda d: d.assign(area_km2=d.area_km2.where(d.index != 0, 1.0))])
def test_inconsistent_periods_are_rejected(change):
    d = ms.measure(TABLE, {1992: FLOWS, 2002: FLOWS})
    with pytest.raises(ms.MeasureError):
        ms.validate_periods(change(d))


# --- flags ---

def test_unusual_values_are_flagged_not_clipped():
    f = FLOWS.copy()
    f.loc["Ra", "Ra"], f.loc["Fd", "Ra"] = 1, 400
    d = one(f)
    assert d.in_rate["Ra"] > 1
    assert "above 100%" in d["notes"]["Ra"] and "large population change" in d["notes"]["Ra"]


def test_small_population_flag():
    d = one()
    assert "small population" in d["notes"]["Ra"] and "small population" not in d["notes"]["Fd"]


# --- real data ---

real = pytest.mark.skipif(not (bd.RAW / "ghs_smod").exists(), reason="raw data not downloaded")
NAMES = [s.name for s in geo.SCENARIOS]


@pytest.fixture(scope="module")
def built():
    ev = geo.load_evidence()
    flows = {y: chim.read_flows(y) for y in chim.YEARS}
    out = {}
    for s in geo.SCENARIOS:
        g = geo.build(ev, s, flows)
        out[s.name] = (g, ms.measure(g.settlements, g.flows))
    return out


@real
@pytest.mark.parametrize("name", NAMES)
def test_real_totals_reconcile_with_accounts(built, name):
    g, d = built[name]
    for y, t in d.groupby("year"):
        a = g.accounts[y]
        assert t.origin_pop.sum() == t.destination_pop.sum() == a["people_after"]
        assert t.departures.sum() == t.arrivals.sum() == a["movers_settlement"]
        assert t.stayers.sum() == a["stayers_settlement"]


@real
@pytest.mark.parametrize("name", NAMES)
def test_real_ranks(built, name):
    g, d = built[name]
    for _, t in d.groupby("year"):
        assert t.position.notna().sum() == geo.counts(g)["ranked"]
        top = t.loc[t.position.idxmax()]
        assert top.settlement_name == "Santiago" and top.position == 1


@real
def test_real_islands_and_antartica(built):
    _, d = built["primary"]
    islands = d[d.settlement_name.isin(["Isla de Pascua", "Juan Fernández"])]
    assert len(islands) == 6 and islands.position.isna().all() and islands.out_rate.notna().all()
    assert not d.settlement_id.str.contains(geo.ANTARTICA).any()
    assert not built["no_islands"][1].settlement_name.isin(["Isla de Pascua", "Juan Fernández"]).any()


@real
def test_real_rates_have_no_missing_values(built):
    for _, d in built.values():
        assert d[list(ms.RATES)].notna().all().all()


@real
def test_all_scenarios_cover_all_periods(built):
    for _, d in built.values():
        assert set(d.year) == set(chim.YEARS)


@real
def test_small_city_scenarios_change_positions_but_not_rates(built):
    """Match on constituent settlement name: identifiers change with type."""
    a = built["primary"][1].sort_values(["year", "settlement_name", "origin_pop"])
    b = built["smod_30_23"][1].sort_values(["year", "settlement_name", "origin_pop"])
    for r in ms.RATES:
        assert np.allclose(a[r], b[r])
    assert not np.allclose(a.position.fillna(0), b.position.fillna(0))
