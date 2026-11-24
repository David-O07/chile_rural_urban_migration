"""Group the 304 CHIM municipalities into settlements and aggregate the flow matrices.

    python src/geography.py

Writes to data/processed/geography/<scenario>/ and reports/local/geography_report.md, both
ignored by Git. One geography serves all three censuses. No rates are calculated.

Rules (docs/geography.md, docs/decisions.md):
  1. A municipality with >= 50% of its people in one FUA belongs to that FUA.
  2. Listed FUAs are merged into a conglomerate.
  3. An unmatched municipality with >= 50% of its people in dense GHS-SMOD cells is a small city.
  4. Any other municipality is a rural settlement on its own.
  5. Municipalities with false positions on the map cannot be tested: "unclassified".
     They stay in the flows but are not ranked and not used in neighbour models.
"""

from dataclasses import dataclass, replace
from pathlib import Path

import numpy as np
import pandas as pd
import shapely

import boundaries as bd
import chim

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "processed" / "geography"
REPORT = ROOT / "reports" / "local" / "geography_report.md"

# FUA identifiers (eFUA_ID), with names checked on reading.
CONCEPCION, CHIGUAYANTE, QUILLOTA, LA_CALERA = 1480, 1665, 1381, 1278
EXPECTED_FUA_NAMES = {CONCEPCION: "Concepción", CHIGUAYANTE: "Chiguayante",
                      QUILLOTA: "Quillota", LA_CALERA: "La Calera"}

HUALQUI = "08104"
ANTARTICA = "12202"
ISLANDS = ("05103", "05201")  # Juan Fernandez, Isla de Pascua
# Municipalities linked by a transfer of territory in DL 2868 of 1979 (docs/historical_boundaries.md).
# Used only by the historical_boundaries sensitivity scenario.
DL2868_PAIRS = (("09114", "09115"),   # Saavedra -> Teodoro Schmidt
                ("09114", "09102"),   # Saavedra -> Carahue
                ("09110", "09115"),   # Nueva Imperial -> Teodoro Schmidt
                ("10107", "10105"),   # Maullin -> Los Muermos
                ("10103", "10105"),   # Fresia -> Los Muermos
                ("09105", "09103"),   # Freire -> Cunco
                ("10209", "10205"),   # Quinchao (Achao) -> Dalcahue unit (via Quemchi)
                ("10207", "10208"))   # Queilen -> Quellon
SMOD_CLASSES = (10, 11, 12, 13, 21, 22, 23, 30)

CITY, SMALL_CITY, RURAL, UNCLASSIFIED = "fua_city", "small_city", "rural", "unclassified"


class GeographyError(Exception):
    """The settlement geography is incomplete or inconsistent."""


def linked_groups(pairs) -> tuple[frozenset[str], ...]:
    """Municipalities connected, directly or through others, by the given pairs."""
    groups: list[set[str]] = []
    for pair in pairs:
        joined = set(pair)
        for g in [g for g in groups if g & joined]:
            joined |= g
            groups.remove(g)
        groups.append(joined)
    return tuple(frozenset(g) for g in sorted(groups, key=min))


@dataclass(frozen=True)
class Scenario:
    name: str
    description: str
    threshold: float = 0.5
    merges: tuple[frozenset[int], ...] = (frozenset({CONCEPCION, CHIGUAYANTE}),)
    unmatch: tuple[str, ...] = ()          # municipalities kept out of their FUA
    dense: tuple[int, ...] = (30,)         # GHS-SMOD classes counted as dense urban
    exclude: tuple[str, ...] = (ANTARTICA,)
    historical: tuple[frozenset[str], ...] = ()   # municipalities grouped for past transfers


PRIMARY = Scenario("primary", "Agreed rules")
SCENARIOS = (
    PRIMARY,
    replace(PRIMARY, name="separate_concepcion", merges=(),
            description="Concepción and Chiguayante separate (strict 50% matching)"),
    replace(PRIMARY, name="hualqui_unmatched", merges=(), unmatch=(HUALQUI,),
            description="Hualqui not assigned to any FUA"),
    replace(PRIMARY, name="merge_quillota_calera",
            merges=PRIMARY.merges + (frozenset({QUILLOTA, LA_CALERA}),),
            description="Quillota and La Calera merged"),
    replace(PRIMARY, name="smod_30_23", dense=(30, 23),
            description="Main small-city check: dense urban = classes 30, 23"),
    replace(PRIMARY, name="smod_30_23_22", dense=(30, 23, 22),
            description="Broad small-city check: dense urban = classes 30, 23, 22"),
    replace(PRIMARY, name="threshold_40", threshold=0.4, description="FUA threshold 40%"),
    replace(PRIMARY, name="threshold_60", threshold=0.6, description="FUA threshold 60%"),
    replace(PRIMARY, name="no_islands", exclude=(ANTARTICA, *ISLANDS),
            description="Isla de Pascua and Juan Fernández also excluded"),
    replace(PRIMARY, name="historical_boundaries", historical=linked_groups(DL2868_PAIRS),
            description="Historical-boundary sensitivity (DL 2868); not exact 1977 boundaries"),
)


# --- Evidence: people of each municipality by FUA and by settlement class ------

@dataclass(frozen=True)
class Evidence:
    meta: pd.DataFrame     # code, name; metadata order
    fuas: pd.DataFrame     # fua_id, fua_name, people (grid), published
    by_fua: np.ndarray     # municipality x (outside, FUA 1, FUA 2, ...)
    by_class: np.ndarray   # municipality x SMOD_CLASSES
    area_km2: pd.Series    # equal-area; missing where the geometry is not usable
    census: pd.DataFrame   # code x year
    contacts: frozenset[tuple[str, str]]  # municipalities that touch, edge or point

    def smod_share(self, dense) -> np.ndarray:
        total = self.by_class.sum(axis=1)
        people = self.by_class[:, [SMOD_CLASSES.index(c) for c in dense]].sum(axis=1)
        return np.divide(people, total, out=np.zeros(len(total)), where=total > 0)

    def dense_people(self, dense, rows) -> float:
        """Dense share of several municipalities together."""
        part = self.by_class[rows]
        people = part[:, [SMOD_CLASSES.index(c) for c in dense]].sum()
        return people / part.sum() if part.sum() > 0 else 0.0


def load_evidence() -> Evidence:
    meta = chim.read_metadata()
    units = bd.read_boundaries()
    grid = units.to_crs(bd.GRID_CRS)
    fuas = bd.read_fuas()
    fuas["fua_id"] = fuas.eFUA_ID.astype(int)
    for fua_id, name in EXPECTED_FUA_NAMES.items():
        if fuas.loc[fuas.fua_id == fua_id, "eFUA_name"].tolist() != [name]:
            raise GeographyError(f"FUA {fua_id} is not {name}")
    bounds = np.r_[np.minimum(grid.total_bounds[:2], fuas.total_bounds[:2]),
                   np.maximum(grid.total_bounds[2:], fuas.total_bounds[2:])]
    pop, transform = bd.read_population(bounds)
    zones = bd.fua_raster(fuas, pop.shape, transform)
    smod = bd.read_smod(pop.shape, transform)
    unknown = set(np.unique(smod[pop > 0])) - set(SMOD_CLASSES)
    if unknown:
        raise GeographyError(f"populated cells with unknown settlement class {unknown}")
    class_index = np.zeros(smod.shape, dtype="int32")
    for i, c in enumerate(SMOD_CLASSES):
        class_index[smod == c] = i
    fua_people = np.bincount(zones.ravel(), pop.ravel(), len(fuas) + 1)[1:]
    area = (grid.geometry.area / 1e6).rename("area_km2")
    area[list(bd.DISPLACED)] = np.nan
    geoms = units.geometry.values
    i, j = shapely.STRtree(geoms).query(geoms, predicate="intersects")
    code = units.index
    contacts = frozenset((code[a], code[b]) for a, b in zip(i, j)
                         if a != b and not {code[a], code[b]} & set(bd.DISPLACED))
    return Evidence(
        meta=meta,
        fuas=pd.DataFrame({"fua_id": fuas.fua_id, "fua_name": fuas.eFUA_name,
                           "people": fua_people, "published": fuas.FUA_p_2015}),
        by_fua=bd.population_by_zone(grid, zones, len(fuas) + 1, pop, transform),
        by_class=bd.population_by_zone(grid, class_index, len(SMOD_CLASSES), pop, transform),
        area_km2=area,
        census=units[[f"Pop_{y}" for y in chim.YEARS]].set_axis(chim.YEARS, axis=1),
        contacts=contacts,
    )


# --- Classification -------------------------------------------------------------

def match_fuas(ev: Evidence, threshold: float, unmatch=()) -> pd.Series:
    """FUA id of each municipality, or missing. Stops on an exact tie."""
    total = ev.by_fua.sum(axis=1)
    inside = ev.by_fua[:, 1:]
    share = np.divide(inside, total[:, None], out=np.zeros_like(inside), where=total[:, None] > 0)
    best = share.max(axis=1)
    ok = best >= threshold
    tied = ok & ((share == best[:, None]).sum(axis=1) > 1)
    if tied.any():
        raise GeographyError(f"tie between FUAs: {ev.meta.code[tied].tolist()}")
    ids = pd.Series(ev.fuas.fua_id.to_numpy()[share.argmax(axis=1)], ev.meta.code, dtype="Int64")
    ids[~ok] = pd.NA
    unknown = set(unmatch) - set(ids.index)
    if unknown:
        raise GeographyError(f"unknown municipalities to unmatch: {unknown}")
    ids[list(unmatch)] = pd.NA
    return ids


def build_crosswalk(ev: Evidence, sc: Scenario) -> pd.DataFrame:
    """One row per municipality: its settlement, type and the evidence behind it."""
    if set().union(*sc.merges, set()) and sum(map(len, sc.merges)) != len(set().union(*sc.merges)):
        raise GeographyError("an FUA appears in two merges")
    unknown = set().union(*sc.merges, set()) - set(ev.fuas.fua_id)
    if unknown:
        raise GeographyError(f"unknown FUAs to merge: {unknown}")
    if sum(map(len, sc.historical)) != len(set().union(*sc.historical, set())):
        raise GeographyError("a municipality appears in two historical groups")
    place = {c: q for q, c in enumerate(ev.meta.code)}
    missing = set().union(*sc.historical, set()) - set(place)
    if missing:
        raise GeographyError(f"unknown municipalities in historical groups: {missing}")
    past = {c: tuple(sorted(m)) for m in sc.historical for c in m}
    group = {f: tuple(sorted(m)) for m in sc.merges for f in m}
    names = dict(zip(ev.fuas.fua_id, ev.fuas.fua_name))
    fua = match_fuas(ev, sc.threshold, sc.unmatch)
    dense = ev.smod_share(sc.dense)
    total = ev.by_fua.sum(axis=1)
    fua_share = np.divide(ev.by_fua[:, 1:].max(axis=1), total,
                          out=np.zeros(len(total)), where=total > 0)
    rows = []
    for q, (code, name) in enumerate(zip(ev.meta.code, ev.meta["name"])):
        excluded = code in sc.exclude
        members = ()
        if code in past and (excluded or code in bd.DISPLACED or pd.notna(fua[code])):
            raise GeographyError(f"{name} is in a city, displaced or excluded: cannot be grouped")
        if excluded:
            sid, sname, kind = None, None, None
        elif code in bd.DISPLACED:
            sid, sname, kind = f"U{code}", name, UNCLASSIFIED
        elif pd.notna(fua[code]):
            members = group.get(int(fua[code]), (int(fua[code]),))
            sid = "F" + "+".join(map(str, members))
            sname, kind = " + ".join(names[f] for f in members), CITY
        elif code in past:
            idx = [place[c] for c in past[code]]
            sid = "H" + "+".join(past[code])
            sname = " + ".join(ev.meta["name"].iloc[idx])
            kind = SMALL_CITY if ev.dense_people(sc.dense, idx) >= 0.5 else RURAL
        elif dense[q] >= 0.5:
            sid, sname, kind = f"S{code}", name, SMALL_CITY
        else:
            sid, sname, kind = f"R{code}", name, RURAL
        usable = code not in bd.DISPLACED
        rows.append({
            "code": code, "name": name, "settlement_id": sid, "settlement_name": sname,
            "type": kind, "excluded": excluded,
            "matched_fua": None if excluded or pd.isna(fua[code]) else int(fua[code]),
            "fua_share": fua_share[q] if usable else np.nan,
            "dense_share": dense[q] if usable else np.nan,
            "grid_people_2015": total[q] if usable else np.nan,
            "area_km2": ev.area_km2[code],
            "geometry_usable": usable,
        })
    return pd.DataFrame(rows)


def neighbours(ev: Evidence, cw: pd.DataFrame) -> dict[str, set[str]]:
    """Settlements that touch (queen contiguity), after merging and exclusions."""
    sid = cw[~cw.excluded].set_index("code").settlement_id
    out = {s: set() for s in sid.unique()}
    for a, b in ev.contacts:
        if a in sid.index and b in sid.index and sid[a] != sid[b]:
            out[sid[a]].add(sid[b])
            out[sid[b]].add(sid[a])
    return out


def settlements(ev: Evidence, cw: pd.DataFrame) -> pd.DataFrame:
    """One row per settlement, listing every constituent municipality.

    ranked: takes part in the urban-rural ranking.
    spatial_model: usable position and at least one touching settlement.
    """
    kept = cw[~cw.excluded].copy()
    for y in chim.YEARS:
        kept[f"census_{y}"] = kept.code.map(ev.census[y])
    out = kept.groupby("settlement_id", sort=True).agg(
        settlement_name=("settlement_name", "first"), type=("type", "first"),
        n_municipalities=("code", "size"), municipalities=("code", lambda s: ";".join(s)),
        area_km2=("area_km2", lambda s: s.sum(min_count=len(s))),
        geometry_usable=("geometry_usable", "all"),
        **{f"census_{y}": (f"census_{y}", "sum") for y in chim.YEARS}).reset_index()
    near = neighbours(ev, cw)
    out["n_neighbours"] = [len(near[s]) for s in out.settlement_id]
    out["ranked"] = out.type != UNCLASSIFIED
    out["spatial_model"] = out.geometry_usable & (out.n_neighbours > 0)
    return out


def match_quality(ev: Evidence, sc: Scenario, cw: pd.DataFrame) -> pd.DataFrame:
    """Quality of each settlement's FUA match, after Du et al. (2026).

    high: matched municipalities hold 75-125% of the FUA's people. intermediate: otherwise,
    if some municipality holds over half of the FUA's people. low: neither.
    """
    rows = []
    cities = cw[cw.type == CITY]
    for sid, g in cities.groupby("settlement_id"):
        ids = [int(x) for x in sid[1:].split("+")]
        cols = [ev.fuas.index[ev.fuas.fua_id == f][0] for f in ids]
        m = ev.meta.code.isin(g.code).to_numpy()
        target = ev.fuas.people.iloc[cols].sum()
        ratio = ev.by_fua[m].sum() / target
        inside = ev.by_fua[np.ix_(m, [c + 1 for c in cols])].sum(axis=1)
        quality = "high" if 0.75 <= ratio <= 1.25 else \
            "intermediate" if (inside > 0.5 * target).any() else "low"
        rows.append({"settlement_id": sid, "settlement_name": g.settlement_name.iloc[0],
                     "n_municipalities": len(g), "member_to_fua": ratio,
                     "fua_covered": inside.sum() / target, "quality": quality})
    return pd.DataFrame(rows)


# --- Validation -----------------------------------------------------------------

def validate_crosswalk(cw: pd.DataFrame, codes, sc: Scenario) -> None:
    """Every municipality appears once and is either assigned once or explicitly excluded."""
    if list(cw.code) != list(codes):
        raise GeographyError("crosswalk does not list every municipality once, in order")
    if set(cw.code[cw.excluded]) != set(sc.exclude):
        raise GeographyError("excluded municipalities differ from the scenario")
    kept = cw[~cw.excluded]
    if kept.settlement_id.isna().any() or cw[cw.excluded].settlement_id.notna().any():
        raise GeographyError("a municipality is neither assigned nor excluded, or is both")
    if not kept.type.isin([CITY, SMALL_CITY, RURAL, UNCLASSIFIED]).all():
        raise GeographyError("unknown settlement type")
    per = kept.groupby("settlement_id")
    if (per.type.nunique() != 1).any() or (per.settlement_name.nunique() != 1).any():
        raise GeographyError("a settlement has two types or names")
    single = kept[(kept.type != CITY) & ~kept.settlement_id.str.startswith("H")]
    if single.settlement_id.duplicated().any():
        raise GeographyError("only cities and historical groups may hold several municipalities")
    grouped = kept[kept.settlement_id.str.startswith("H")].groupby("settlement_id").code
    if {frozenset(g) for _, g in grouped} != set(sc.historical):
        raise GeographyError("historical groups differ from the scenario")
    if kept[kept.type == CITY].matched_fua.isna().any():
        raise GeographyError("a city municipality has no FUA")


def validate_settlements(table: pd.DataFrame, cw: pd.DataFrame, ev: Evidence) -> None:
    listed = [c for s in table.municipalities for c in s.split(";")]
    if sorted(listed) != sorted(cw.code[~cw.excluded]):
        raise GeographyError("settlements do not trace back to each municipality exactly once")
    if table.area_km2[table.ranked].isna().any():
        raise GeographyError("a ranked settlement has no area")
    if (table.spatial_model & (~table.ranked | (table.n_neighbours == 0))).any():
        raise GeographyError("a settlement is wrongly marked for neighbour models")
    for y in chim.YEARS:
        expected = ev.census[y].sum() - ev.census.loc[cw.code[cw.excluded], y].sum()
        if table[f"census_{y}"].sum() != expected:
            raise GeographyError(f"{y}: population not conserved")


# --- Aggregation ----------------------------------------------------------------

def aggregate_flows(flows: pd.DataFrame, cw: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    """Sum a municipal matrix into settlements, with an account of every person.

    The diagonal then holds people who stayed in the same settlement, including those who
    moved between two of its municipalities. Flows touching an excluded municipality are
    dropped and counted.
    """
    if list(flows.index) != list(cw.code) or list(flows.columns) != list(cw.code):
        raise GeographyError("flow matrix and crosswalk are not in the same order")
    ids = sorted(cw.settlement_id.dropna().unique())
    member = (cw.settlement_id.to_numpy()[:, None] == np.array(ids)[None, :]).astype("int64")
    m = flows.to_numpy()
    out = pd.DataFrame(member.T @ m @ member, index=pd.Index(ids, name="origin"),
                       columns=pd.Index(ids, name="destination"))
    kept = (~cw.excluded).to_numpy()
    inner = m[np.ix_(kept, kept)]
    account = {
        "people_before": int(m.sum()),
        "dropped_excluded_origin_or_destination": int(m.sum() - inner.sum()),
        "dropped_stayers": int(np.diag(m)[~kept].sum()),
        "stayers_municipal": int(np.trace(inner)),
        "movers_municipal": int(inner.sum() - np.trace(inner)),
        "stayers_settlement": int(np.trace(out.to_numpy())),
        "movers_settlement": int(out.to_numpy().sum() - np.trace(out.to_numpy())),
        "people_after": int(out.to_numpy().sum()),
    }
    account["moves_now_internal"] = account["movers_municipal"] - account["movers_settlement"]
    validate_aggregation(flows, cw, out, account)
    return out, account


def validate_aggregation(flows, cw, out, account) -> None:
    if account["people_before"] != account["people_after"] + account["dropped_excluded_origin_or_destination"]:
        raise GeographyError("people not conserved")
    if account["movers_settlement"] + account["stayers_settlement"] != account["people_after"]:
        raise GeographyError("movers and stayers do not sum to the total")
    if account["moves_now_internal"] < 0:
        raise GeographyError("aggregation created movers")
    kept = cw[~cw.excluded]
    sub = flows.loc[kept.code, kept.code]
    key = kept.set_index("code").settlement_id
    for axis, label in ((1, "origin"), (0, "destination")):
        expected = sub.sum(axis=axis).groupby(key).sum().sort_index()
        if (expected.to_numpy() != out.sum(axis=axis).sort_index().to_numpy()).any():
            raise GeographyError(f"{label} totals not conserved")


# --- Pipeline -------------------------------------------------------------------

@dataclass(frozen=True)
class Geography:
    scenario: Scenario
    crosswalk: pd.DataFrame
    settlements: pd.DataFrame
    quality: pd.DataFrame
    flows: dict[int, pd.DataFrame]
    accounts: dict[int, dict]


def build(ev: Evidence, sc: Scenario, flows: dict[int, pd.DataFrame]) -> Geography:
    cw = build_crosswalk(ev, sc)
    validate_crosswalk(cw, ev.meta.code, sc)
    table = settlements(ev, cw)
    validate_settlements(table, cw, ev)
    matrices, accounts = {}, {}
    for y, f in flows.items():
        matrices[y], accounts[y] = aggregate_flows(f, cw)
        if list(matrices[y].index) != list(table.settlement_id):
            raise GeographyError(f"{y}: settlements differ from the settlement table")
    return Geography(sc, cw, table, match_quality(ev, sc, cw), matrices, accounts)


def write(geo: Geography, folder: Path = OUT) -> None:
    d = folder / geo.scenario.name
    d.mkdir(parents=True, exist_ok=True)
    geo.crosswalk.to_csv(d / "crosswalk.csv", index=False)
    geo.settlements.to_csv(d / "settlements.csv", index=False)
    geo.quality.to_csv(d / "match_quality.csv", index=False)
    for y, f in geo.flows.items():
        f.to_csv(d / f"flows_{y}.csv")


def counts(geo: Geography) -> dict:
    kinds = geo.settlements.type.value_counts()
    cw = geo.crosswalk
    return {"scenario": geo.scenario.name, "settlements": len(geo.settlements),
            "fua_cities": int(kinds.get(CITY, 0)), "small_cities": int(kinds.get(SMALL_CITY, 0)),
            "rural": int(kinds.get(RURAL, 0)), "unclassified": int(kinds.get(UNCLASSIFIED, 0)),
            "municipalities_in_fua_cities": int((cw.type == CITY).sum()),
            "excluded": int(cw.excluded.sum()),
            "ranked": int(geo.settlements.ranked.sum()),
            "for_neighbour_models": int(geo.settlements.spatial_model.sum())}


def report(geos: list[Geography]) -> str:
    base = geos[0]
    out = ["# Geography report (local only)\n", "## Scenario counts\n",
           pd.DataFrame([counts(g) for g in geos]).to_string(index=False), "\n## Changes from primary\n"]
    ref = base.crosswalk.set_index("code")
    for g in geos[1:]:
        cw = g.crosswalk.set_index("code")
        moved = cw[(cw.settlement_id.fillna("") != ref.settlement_id.fillna(""))]
        out.append(f"{g.scenario.name}: {g.scenario.description}")
        out += [f"    {c} {r['name']}: {ref.settlement_id[c]} -> {r.settlement_id}"
                for c, r in moved.iterrows()] or ["    no change"]
    unusual = base.settlements[~base.settlements.spatial_model]
    out += ["\n## Not used in contiguity models (primary)\n",
            unusual[["settlement_id", "settlement_name", "type", "n_neighbours", "ranked"]].to_string(index=False)]
    check = next(g for g in geos if g.scenario.name == "smod_30_23").crosswalk
    out += ["\n## Small cities (smod_30_23)\n",
            check[check.type == SMALL_CITY]
            [["code", "name", "fua_share", "dense_share", "grid_people_2015"]].round(3).to_string(index=False)]
    near = base.crosswalk[(base.crosswalk.type.isin([RURAL, SMALL_CITY]))
                          & base.crosswalk.dense_share.between(0.4, 0.6)]
    out += ["\n## Unmatched municipalities with dense share 0.4-0.6\n",
            near[["code", "name", "type", "dense_share"]].round(3).to_string(index=False),
            "\n## FUA match quality (primary)\n", base.quality.round(3).to_string(index=False),
            "\n## Flow accounts\n",
            pd.DataFrame([{"scenario": g.scenario.name, "year": y, **a}
                          for g in geos for y, a in g.accounts.items()]).to_string(index=False)]
    return "\n".join(out) + "\n"


def main() -> None:
    ev = load_evidence()
    flows = {y: chim.read_flows(y) for y in chim.YEARS}
    geos = [build(ev, sc, flows) for sc in SCENARIOS]
    for g in geos:
        write(g)
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    REPORT.write_text(report(geos))
    print(pd.DataFrame([counts(g) for g in geos]).to_string(index=False))


if __name__ == "__main__":
    main()
