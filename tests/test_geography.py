"""Settlement geography: an invented five-municipality country, then the real data."""

import sys
from dataclasses import replace
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
import boundaries as bd
import chim
import geography as geo

# a, b: city 1. c: city 2. d: dense but unmatched. e: rural. f: to be excluded.
CODES = list("abcdef")
FLOWS = pd.DataFrame(np.array([
    [90, 4, 3, 2, 1, 1],
    [6, 50, 2, 1, 0, 0],
    [5, 1, 70, 0, 2, 0],
    [3, 0, 4, 30, 1, 2],
    [2, 2, 1, 5, 20, 0],
    [1, 0, 0, 0, 1, 7]]), index=CODES, columns=CODES)
RULES = geo.Scenario("toy", "", merges=(), dense=(30, 23), exclude=("f",))


@pytest.fixture
def ev():
    by_fua = np.array([[10, 90, 0], [40, 60, 0], [30, 0, 70], [100, 0, 0],
                       [80, 20, 0], [5, 0, 0]], dtype=float)
    by_class = np.zeros((6, len(geo.SMOD_CLASSES)))
    col = geo.SMOD_CLASSES.index
    by_class[:, col(11)] = [10, 40, 30, 20, 95, 5]
    by_class[[0, 1, 2], col(30)] = [90, 60, 70]
    by_class[3, col(23)] = 60
    by_class[3, col(22)] = 20
    by_class[4, col(22)] = 5
    return geo.Evidence(
        meta=pd.DataFrame({"code": CODES, "name": [c.upper() for c in CODES]}),
        fuas=pd.DataFrame({"fua_id": [1, 2], "fua_name": ["One", "Two"],
                           "people": [170.0, 70.0], "published": [170.0, 70.0]}),
        by_fua=by_fua, by_class=by_class,
        area_km2=pd.Series([1.0, 2, 3, 4, 5, 6], CODES),
        census=pd.DataFrame({y: [100, 90, 80, 70, 60, 10] for y in chim.YEARS}, index=CODES),
        contacts=frozenset({("a", "b"), ("b", "a"), ("b", "c"), ("c", "d"), ("d", "f"), ("e", "f")}))


def ids(ev, sc):
    return geo.build_crosswalk(ev, sc).set_index("code").settlement_id


# --- classification ---

def test_types_and_ids(ev):
    cw = geo.build_crosswalk(ev, RULES).set_index("code")
    assert cw.settlement_id[:5].tolist() == ["F1", "F1", "F2", "Sd", "Re"]
    assert cw.type[:5].tolist() == [geo.CITY] * 3 + [geo.SMALL_CITY, geo.RURAL]
    assert cw.excluded["f"] and pd.isna(cw.settlement_id["f"])


@pytest.mark.parametrize("threshold, expected", [(0.6, "F1"), (0.61, "Sb")])
def test_threshold_is_inclusive(ev, threshold, expected):
    assert ids(ev, replace(RULES, threshold=threshold))["b"] == expected


def test_exactly_half_qualifies(ev):
    ev.by_fua[4] = [50, 50, 0]
    assert ids(ev, RULES)["e"] == "F1"


def test_exact_tie_stops(ev):
    ev.by_fua[4] = [0, 50, 50]
    with pytest.raises(geo.GeographyError, match="tie"):
        ids(ev, RULES)


def test_merge_makes_one_settlement(ev):
    got = ids(ev, replace(RULES, merges=(frozenset({1, 2}),)))
    assert set(got[["a", "b", "c"]]) == {"F1+2"}


@pytest.mark.parametrize("merges, message", [
    ((frozenset({1, 9}),), "unknown FUAs"),
    ((frozenset({1, 2}), frozenset({2})), "two merges"),
])
def test_bad_merges_stop(ev, merges, message):
    with pytest.raises(geo.GeographyError, match=message):
        geo.build_crosswalk(ev, replace(RULES, merges=merges))


def test_unmatched_municipality_is_retested_as_small_city(ev):
    assert ids(ev, replace(RULES, unmatch=("b",)))["b"] == "Sb"


@pytest.mark.parametrize("dense, expected", [((30,), "Rd"), ((30, 23), "Sd"), ((22,), "Rd"), ((30, 23, 22), "Sd")])
def test_dense_classes(ev, dense, expected):
    assert ids(ev, replace(RULES, dense=dense))["d"] == expected


def test_fua_match_takes_precedence_over_small_city(ev):
    assert ids(ev, RULES)["a"] == "F1"


def test_municipality_without_people_is_never_a_city(ev):
    ev.by_fua[4] = 0
    ev.by_class[4] = 0
    assert ids(ev, RULES)["e"] == "Re"


# --- historical groups ---

def test_linked_groups_follow_chains():
    got = geo.linked_groups([("a", "b"), ("c", "d"), ("b", "e"), ("x", "y"), ("d", "e")])
    assert set(got) == {frozenset("abcde"), frozenset("xy")}


def test_historical_group_is_one_rural_settlement(ev):
    sc = replace(RULES, historical=(frozenset({"d", "e"}),), dense=(30,))
    cw = geo.build_crosswalk(ev, sc)
    geo.validate_crosswalk(cw, CODES, sc)
    row = cw.set_index("code").loc[["d", "e"]]
    assert set(row.settlement_id) == {"Hd+e"} and set(row.type) == {geo.RURAL}
    out, acc = geo.aggregate_flows(FLOWS, cw)
    assert out.loc["Hd+e", "Hd+e"] == 30 + 1 + 5 + 20
    assert acc["people_after"] + acc["dropped_excluded_origin_or_destination"] == FLOWS.to_numpy().sum()
    table = geo.settlements(ev, cw).set_index("settlement_id").loc["Hd+e"]
    assert table.area_km2 == 9 and table.municipalities == "d;e" and table.census_2002 == 130


def test_historical_group_type_uses_combined_people(ev):
    sc = replace(RULES, historical=(frozenset({"d", "e"}),))   # 60 dense people of 200
    assert set(geo.build_crosswalk(ev, sc).set_index("code").type[["d", "e"]]) == {geo.RURAL}


@pytest.mark.parametrize("groups, message", [
    ((frozenset({"a", "d"}),), "cannot be grouped"),         # a is in a city
    ((frozenset({"e", "f"}),), "cannot be grouped"),         # f is excluded
    ((frozenset({"d", "z"}),), "unknown"),
    ((frozenset({"d", "e"}), frozenset({"e"})), "two historical"),
])
def test_bad_historical_groups_stop(ev, groups, message):
    with pytest.raises(geo.GeographyError, match=message):
        geo.build_crosswalk(ev, replace(RULES, historical=groups))


# --- assignment validation ---

@pytest.mark.parametrize("damage", [
    lambda cw: pd.concat([cw, cw.iloc[[0]]]),                               # duplicate
    lambda cw: cw.iloc[1:],                                                 # missing
    lambda cw: cw.assign(settlement_id=cw.settlement_id.where(cw.code != "a", None)),
    lambda cw: cw.assign(type=cw.type.where(cw.code != "a", geo.RURAL)),    # mixed types
    lambda cw: cw.assign(excluded=False),
    lambda cw: cw.assign(settlement_id=cw.settlement_id.replace("Re", "Sd"),
                         settlement_name=cw.settlement_name.replace("E", "D"),
                         type=cw.type.replace(geo.RURAL, geo.SMALL_CITY)),  # shared non-city
    lambda cw: cw.assign(matched_fua=None),
])
def test_damaged_crosswalk_is_rejected(ev, damage):
    cw = geo.build_crosswalk(ev, RULES)
    geo.validate_crosswalk(cw, CODES, RULES)
    with pytest.raises(geo.GeographyError):
        geo.validate_crosswalk(damage(cw), CODES, RULES)


def test_settlements_trace_back_and_conserve_population(ev):
    cw = geo.build_crosswalk(ev, RULES)
    table = geo.settlements(ev, cw)
    geo.validate_settlements(table, cw, ev)
    row = table.set_index("settlement_id").loc["F1"]
    assert row.municipalities == "a;b" and row.area_km2 == 3 and row.census_2002 == 190
    with pytest.raises(geo.GeographyError, match="trace"):
        geo.validate_settlements(table.iloc[1:], cw, ev)
    with pytest.raises(geo.GeographyError, match="population"):
        geo.validate_settlements(table.assign(census_1992=table.census_1992 + 1), cw, ev)


def test_unknown_area_is_not_treated_as_zero(ev):
    ev.area_km2["b"] = np.nan
    table = geo.settlements(ev, geo.build_crosswalk(ev, RULES)).set_index("settlement_id")
    assert np.isnan(table.area_km2["F1"])


def test_neighbours_are_between_settlements(ev):
    cw = geo.build_crosswalk(ev, RULES)
    near = geo.neighbours(ev, cw)
    assert near["F1"] == {"F2"}              # a-b contact is internal to F1
    assert near["F2"] == {"F1", "Sd"}        # and contacts are symmetric
    assert near["Re"] == set()               # its only contact is an excluded unit
    table = geo.settlements(ev, cw).set_index("settlement_id")
    assert not table.spatial_model["Re"] and table.ranked["Re"]
    assert table.spatial_model[["F1", "F2", "Sd"]].all()


def test_merging_can_leave_a_settlement_without_neighbours(ev):
    ev2 = replace(ev, contacts=frozenset({("a", "b"), ("c", "d")}))
    table = geo.settlements(ev2, geo.build_crosswalk(ev2, RULES)).set_index("settlement_id")
    assert table.n_neighbours["F1"] == 0 and not table.spatial_model["F1"]


def test_ranked_settlement_needs_an_area(ev):
    ev.area_km2["e"] = np.nan
    cw = geo.build_crosswalk(ev, RULES)
    with pytest.raises(geo.GeographyError, match="no area"):
        geo.validate_settlements(geo.settlements(ev, cw), cw, ev)


# --- aggregation ---

def test_aggregation_by_hand(ev):
    out, acc = geo.aggregate_flows(FLOWS, geo.build_crosswalk(ev, RULES))
    assert out.loc["F1", "F1"] == 90 + 4 + 6 + 50     # moves a<->b are now internal
    assert out.loc["F1", "F2"] == 3 + 2               # origin city 1, destination city 2
    assert out.loc["F2", "F1"] == 5 + 1               # direction is kept
    assert acc["moves_now_internal"] == 4 + 6
    assert acc["dropped_excluded_origin_or_destination"] == (1 + 0 + 0 + 2 + 0) + (1 + 0 + 0 + 0 + 1 + 7)


def test_people_conserved_and_accounted(ev):
    out, acc = geo.aggregate_flows(FLOWS, geo.build_crosswalk(ev, RULES))
    assert acc["people_after"] + acc["dropped_excluded_origin_or_destination"] == FLOWS.to_numpy().sum()
    assert acc["movers_settlement"] + acc["stayers_settlement"] == out.to_numpy().sum()


def test_arrivals_equal_departures(ev):
    out, acc = geo.aggregate_flows(FLOWS, geo.build_crosswalk(ev, RULES))
    d = np.diag(out)
    assert (out.sum(axis=0) - d).sum() == (out.sum(axis=1) - d).sum() == acc["movers_settlement"]


def test_no_merging_leaves_matrix_unchanged(ev):
    ev.by_fua[:, 1:] = 0
    ev.by_fua[:, 0] = 1
    out, acc = geo.aggregate_flows(FLOWS, geo.build_crosswalk(ev, replace(RULES, exclude=())))
    assert sorted(out.to_numpy().ravel()) == sorted(FLOWS.to_numpy().ravel())
    assert acc["moves_now_internal"] == 0


def test_misordered_flows_are_rejected(ev):
    with pytest.raises(geo.GeographyError, match="order"):
        geo.aggregate_flows(FLOWS.iloc[::-1], geo.build_crosswalk(ev, RULES))


@pytest.mark.parametrize("change", [
    lambda o: o.T,                                     # direction reversed
    lambda o: o + np.eye(len(o), dtype=int),           # people created
])
def test_wrong_aggregates_are_rejected(ev, change):
    cw = geo.build_crosswalk(ev, RULES)
    out, acc = geo.aggregate_flows(FLOWS, cw)
    with pytest.raises(geo.GeographyError, match="not conserved"):
        geo.validate_aggregation(FLOWS, cw, change(out), acc)


# --- real data ---

real = pytest.mark.skipif(not (bd.RAW / "ghs_smod").exists(), reason="raw data not downloaded")


@pytest.fixture(scope="module")
def built():
    evidence = geo.load_evidence()
    flows = {y: chim.read_flows(y) for y in chim.YEARS}
    return evidence, flows, {s.name: geo.build(evidence, s, flows) for s in geo.SCENARIOS}


@real
def test_scenario_names_unique_and_start_from_primary(built):
    names = [s.name for s in geo.SCENARIOS]
    assert len(set(names)) == len(names) and names[0] == "primary"


@real
@pytest.mark.parametrize("name", [s.name for s in geo.SCENARIOS])
def test_real_assignment_complete(built, name):
    evidence, _, geos = built
    cw = geos[name].crosswalk
    assert len(cw) == chim.N and cw.code.is_unique
    assert set(cw.code[cw.settlement_id.isna()]) == set(geos[name].scenario.exclude)


@real
@pytest.mark.parametrize("name", [s.name for s in geo.SCENARIOS])
def test_real_flows_match_independent_aggregation(built, name):
    """Recompute every cell by a different route: long format and groupby."""
    _, flows, geos = built
    key = geos[name].crosswalk.set_index("code").settlement_id
    for y, f in flows.items():
        long = f.stack().rename("n").reset_index()
        long["o"], long["d"] = long.origin.map(key), long.destination.map(key)
        expected = long.dropna().groupby(["o", "d"]).n.sum().unstack()
        assert (expected.to_numpy() == geos[name].flows[y].to_numpy()).all()


@real
@pytest.mark.parametrize("name", [s.name for s in geo.SCENARIOS])
def test_same_settlements_every_period(built, name):
    g = built[2][name]
    for f in g.flows.values():
        assert list(f.index) == list(f.columns) == list(g.settlements.settlement_id)


@real
def test_real_evidence_is_consistent(built):
    evidence = built[0]
    assert np.allclose(evidence.by_fua.sum(axis=1), evidence.by_class.sum(axis=1))
    assert evidence.by_fua[:, 1:].sum() == pytest.approx(evidence.fuas.people.sum(), rel=1e-3)
    assert evidence.fuas.people.sum() == pytest.approx(evidence.fuas.published.sum(), rel=1e-3)


@real
def test_agreed_exceptions(built):
    cw = {n: g.crosswalk.set_index("code") for n, g in built[2].items()}
    p = cw["primary"]
    joint = f"F{geo.CONCEPCION}+{geo.CHIGUAYANTE}"
    assert p.settlement_id["08101"] == p.settlement_id[geo.HUALQUI] == joint
    assert p.settlement_id["05504"] == f"F{geo.QUILLOTA}"
    assert p.excluded[geo.ANTARTICA]
    assert cw["separate_concepcion"].settlement_id[geo.HUALQUI] == f"F{geo.CHIGUAYANTE}"
    assert cw["hualqui_unmatched"].type[geo.HUALQUI] != geo.CITY
    assert cw["merge_quillota_calera"].settlement_id["05504"] == f"F{geo.LA_CALERA}+{geo.QUILLOTA}"
    assert cw["no_islands"].excluded[list(geo.ISLANDS)].all()


@real
def test_islands_flagged_not_guessed(built):
    g = built[2]["primary"]
    cw = g.crosswalk.set_index("code").loc[list(geo.ISLANDS)]
    assert (cw.type == geo.UNCLASSIFIED).all() and cw.area_km2.isna().all()
    table = g.settlements.set_index("settlement_id")
    assert not table.ranked[cw.settlement_id].any()
    assert not table.spatial_model[cw.settlement_id].any()
    assert table.drop(cw.settlement_id).ranked.all()
    for f in g.flows.values():   # kept in the migration data
        assert set(cw.settlement_id) <= set(f.index)


@real
def test_units_without_contact_stay_ranked_but_leave_contiguity_models(built):
    table = built[2]["primary"].settlements.set_index("settlement_name")
    for name in ("Puqueldón", "Guaitecas"):
        row = table.loc[name]
        assert row.ranked and row.n_neighbours == 0 and not row.spatial_model
    lost = table.index[~table.spatial_model]
    assert set(lost) == {"Puqueldón", "Guaitecas", "Isla de Pascua", "Juan Fernández"}


@real
def test_small_city_definitions(built):
    sc = {n: g.scenario.dense for n, g in built[2].items()}
    assert sc["primary"] == (30,) and sc["smod_30_23"] == (30, 23) and sc["smod_30_23_22"] == (30, 23, 22)
    c = {n: geo.counts(g)["small_cities"] for n, g in built[2].items()}
    assert c["primary"] == 0   # every populated class-30 cell lies inside an FUA
    assert 0 < c["smod_30_23"] < c["smod_30_23_22"]


@real
def test_small_city_definition_changes_types_not_flows(built):
    """Reclassifying changes identifiers only: the same municipalities stand alone."""
    _, _, geos = built
    for name in ("smod_30_23", "smod_30_23_22"):
        a, b = geos["primary"], geos[name]
        assert sorted(a.settlements.municipalities) == sorted(b.settlements.municipalities)
        assert a.accounts == b.accounts


@real
def test_historical_scenario_groups_exactly_the_documented_municipalities(built):
    cw = {n: built[2][n].crosswalk.set_index("code") for n in ("primary", "historical_boundaries")}
    changed = cw["primary"].index[cw["primary"].settlement_id.fillna("") != cw["historical_boundaries"].settlement_id.fillna("")]
    assert set(changed) == {c for pair in geo.DL2868_PAIRS for c in pair}
    assert {frozenset(m.split(";")) for m in built[2]["historical_boundaries"].settlements.query("n_municipalities > 1 and type == 'rural'").municipalities} \
        == {frozenset({"09102", "09110", "09114", "09115"}), frozenset({"10103", "10105", "10107"}),
            frozenset({"09103", "09105"}), frozenset({"10205", "10209"}), frozenset({"10207", "10208"})}


@real
def test_historical_scenario_conserves_people_and_only_internalizes_moves(built):
    _, flows, geos = built
    a, b = geos["primary"], geos["historical_boundaries"]
    cw = a.crosswalk.set_index("code")
    for y, f in flows.items():
        assert a.accounts[y]["people_after"] == b.accounts[y]["people_after"]
        inside = sum(int(f.loc[o, d]) for g in b.scenario.historical for o in g for d in g if o != d)
        assert a.accounts[y]["movers_settlement"] - b.accounts[y]["movers_settlement"] == inside
    assert len(a.settlements) - len(b.settlements) == 13 - 5


@real
def test_threshold_sensitivity_is_monotonic(built):
    c = {n: geo.counts(g)["municipalities_in_fua_cities"] for n, g in built[2].items()}
    assert c["threshold_60"] <= c["primary"] <= c["threshold_40"]


@real
def test_written_files_round_trip(built, tmp_path):
    g = built[2]["primary"]
    geo.write(g, tmp_path)
    cw = pd.read_csv(tmp_path / "primary" / "crosswalk.csv", dtype={"code": str})
    assert list(cw.code) == list(g.crosswalk.code)
    f = pd.read_csv(tmp_path / "primary" / "flows_1992.csv", index_col=0)
    assert (f.to_numpy() == g.flows[1992].to_numpy()).all() and list(f.index) == list(f.columns)
