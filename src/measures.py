"""Settlement populations, ranks and five-year migration rates (docs/measures.md).

    python src/measures.py

Reads the aggregated matrices built by geography.py. Writes measures.csv beside them, and
reports/local/measures_report.md. Nothing is clipped or dropped: unusual values are flagged.
"""

from pathlib import Path

import numpy as np
import pandas as pd

import chim
import geography as geo

REPORT = geo.ROOT / "reports" / "local" / "measures_report.md"
URBAN = (geo.CITY, geo.SMALL_CITY)
RATES = ("out_rate", "in_rate", "out_rate_avg", "in_rate_dest")
POSITIONS = {"position": "avg_pop", "position_origin": "origin_pop",
             "position_destination": "destination_pop"}

SMALL_POPULATION = 500   # average population below this makes rates unstable
CHANGE_RATIO = 1.5       # destination/origin population outside 1/1.5..1.5
EXTREME_IQR = 3.0        # distance beyond the quartiles, in interquartile ranges


class MeasureError(Exception):
    """Populations, flows, ranks or rates do not reconcile."""


def populations(flows: pd.DataFrame) -> pd.DataFrame:
    """Population and migrant counts of each settlement from one aggregated matrix."""
    if list(flows.index) != list(flows.columns):
        raise MeasureError("matrix rows and columns differ")
    m = flows.to_numpy()
    if not np.issubdtype(m.dtype, np.integer) or (m < 0).any():
        raise MeasureError("flows must be non-negative integers without missing values")
    out = pd.DataFrame({"origin_pop": m.sum(axis=1), "destination_pop": m.sum(axis=0),
                        "stayers": np.diag(m)}, index=pd.Index(flows.index, name="settlement_id"))
    out["avg_pop"] = (out.origin_pop + out.destination_pop) / 2
    out["departures"] = out.origin_pop - out.stayers
    out["arrivals"] = out.destination_pop - out.stayers
    return out


def ratio(numerator: pd.Series, denominator: pd.Series) -> pd.Series:
    """Missing where the denominator is zero, rather than zero or infinite."""
    return numerator / denominator.where(denominator > 0)


def rates(p: pd.DataFrame) -> pd.DataFrame:
    """Five-year rates as proportions. Not annualized."""
    return pd.DataFrame({
        "out_rate": ratio(p.departures, p.origin_pop),         # primary
        "in_rate": ratio(p.arrivals, p.avg_pop),               # primary
        "out_rate_avg": ratio(p.departures, p.avg_pop),        # sensitivity
        "in_rate_dest": ratio(p.arrivals, p.destination_pop),  # sensitivity
    })


def position(kind: pd.Series, ranked: pd.Series, area: pd.Series, pop: pd.Series) -> pd.Series:
    """Rural by density, then urban by population; rank / number ranked. Ties share a rank."""
    if not kind[ranked].isin((*URBAN, geo.RURAL)).all():
        raise MeasureError("a ranked settlement is neither urban nor rural")
    rural = ranked & (kind == geo.RURAL)
    urban = ranked & kind.isin(URBAN)
    if not (area[rural] > 0).all():   # also false when missing
        raise MeasureError("a rural settlement has no usable area")
    if pop[ranked].isna().any():
        raise MeasureError("a ranked settlement has no population")
    out = pd.Series(np.nan, index=kind.index)
    out[rural] = (pop[rural] / area[rural]).rank(method="average")
    out[urban] = pop[urban].rank(method="average") + rural.sum()
    return out / ranked.sum()


def flags(d: pd.DataFrame) -> pd.Series:
    """Reasons to look at a settlement, in one period. Empty if none."""
    notes = pd.Series([[] for _ in range(len(d))], index=d.index)

    def add(mask, text):
        for i in d.index[mask.fillna(False)]:
            notes[i].append(text)

    for r in RATES:
        add(d[r].isna(), f"{r} missing")
        add(d[r] > 1, f"{r} above 100%")
    add(d.avg_pop < SMALL_POPULATION, "small population")
    change = ratio(d.destination_pop.astype(float), d.origin_pop)
    add((change > CHANGE_RATIO) | (change < 1 / CHANGE_RATIO), "large population change")
    for r in ("out_rate", "in_rate"):
        q1, q3 = d.loc[d.ranked, r].quantile([0.25, 0.75])  # ranked settlements set the scale
        reach = EXTREME_IQR * (q3 - q1)
        add(d[r] > q3 + reach, f"{r} extreme high")
        add(d[r] < q1 - reach, f"{r} extreme low")
    return notes.map("; ".join)


def measure(settlements: pd.DataFrame, flows: dict[int, pd.DataFrame]) -> pd.DataFrame:
    """One row per settlement and period."""
    base = settlements.set_index("settlement_id")
    tables = []
    for year, f in flows.items():
        if list(f.index) != list(base.index):
            raise MeasureError(f"{year}: matrix and settlement table differ")
        p = populations(f)
        d = base[["settlement_name", "type", "n_municipalities", "ranked", "spatial_model",
                  "area_km2"]].join(p).join(rates(p))
        d.insert(0, "year", year)
        d["density_avg"] = d.avg_pop / d.area_km2
        for column, pop in POSITIONS.items():
            d[column] = position(d.type, d.ranked, d.area_km2, d[pop])
        d["notes"] = flags(d)
        validate(d, f)
        tables.append(d.reset_index())
    out = pd.concat(tables, ignore_index=True)
    validate_periods(out)
    return out


def validate(d: pd.DataFrame, flows: pd.DataFrame) -> None:
    """Reconcile one period with its matrix, and check ranks and rate bounds."""
    total, stay = int(flows.to_numpy().sum()), int(np.trace(flows.to_numpy()))
    for column, expected in [("origin_pop", total), ("destination_pop", total),
                             ("avg_pop", total), ("stayers", stay),
                             ("departures", total - stay), ("arrivals", total - stay)]:
        if d[column].sum() != expected:
            raise MeasureError(f"{column} does not reconcile with the matrix")
    if (d[["departures", "arrivals", "stayers"]] < 0).any().any():
        raise MeasureError("negative count")
    for r, n, q in [("out_rate", "departures", "origin_pop"), ("in_rate", "arrivals", "avg_pop"),
                    ("out_rate_avg", "departures", "avg_pop"),
                    ("in_rate_dest", "arrivals", "destination_pop")]:
        if not np.allclose(d[r].fillna(0) * d[q], d[n]):
            raise MeasureError(f"{r} does not return its numerator")
        if (d[r].isna() != (d[q] == 0)).any():
            raise MeasureError(f"{r} must be missing exactly where its denominator is zero")
    for r, bound in [("out_rate", 1), ("in_rate_dest", 1), ("in_rate", 2), ("out_rate_avg", 2)]:
        if (d[r] > bound).any():
            raise MeasureError(f"{r} above its theoretical maximum {bound}")
    k = d.ranked.sum()
    for column in POSITIONS:
        x = d[column]
        if (x.isna() != ~d.ranked).any():
            raise MeasureError(f"{column}: exactly the ranked settlements need a position")
        if not np.isclose(x.sum(), (k + 1) / 2) or (x[d.ranked] <= 0).any() or (x > 1).any():
            raise MeasureError(f"{column} is not a normalized rank")
        rural, urban = x[d.type == geo.RURAL], x[d.type.isin(URBAN)]
        if len(rural) and len(urban) and rural.max() >= urban.min():
            raise MeasureError(f"{column}: a rural settlement ranks above a city")


def validate_periods(d: pd.DataFrame) -> None:
    """The same settlements, types and areas in every period."""
    if d.duplicated(["settlement_id", "year"]).any():
        raise MeasureError("duplicate settlement and period")
    years = d.year.nunique()
    g = d.groupby("settlement_id")
    if (g.size() != years).any():
        raise MeasureError("a settlement is missing in some period")
    for c in ("type", "ranked", "spatial_model", "n_municipalities"):
        if (g[c].nunique() != 1).any():
            raise MeasureError(f"{c} changes between periods")
    if (g.area_km2.nunique(dropna=False) != 1).any():
        raise MeasureError("area changes between periods")


# --- Report ---------------------------------------------------------------------

def distribution(d: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for (year, kind), g in d[d.ranked].groupby(["year", "type"]):
        for r in RATES:
            q = g[r].quantile([0, .05, .25, .5, .75, .95, 1]) * 100
            rows.append([year, kind, r, len(g), *q.round(1), round(g[r].mean() * 100, 1)])
    return pd.DataFrame(rows, columns=["year", "type", "rate %", "n", "min", "p5", "p25", "median",
                                       "p75", "p95", "max", "mean"])


def report(d: pd.DataFrame, summary: pd.DataFrame) -> str:
    national = d.groupby("year")[["departures", "origin_pop"]].sum()
    show = ["year", "settlement_name", "type", "origin_pop", "destination_pop", "departures",
            "arrivals", "out_rate", "in_rate", "position", "notes"]
    moved = d[d.ranked].pivot(index="settlement_id", columns="year", values="position")
    parts = ["# Measures report (local only)\n", "## Primary: national\n",
             (national.departures / national.origin_pop).round(4).to_string(),
             "\n## Primary: distributions, ranked settlements\n", distribution(d).to_string(index=False),
             "\n## Primary: flagged\n", d.loc[d.notes != "", show].round(3).to_string(index=False),
             "\n## Primary: largest shifts in position between periods\n",
             (moved.max(axis=1) - moved.min(axis=1)).describe().round(4).to_string(),
             "\n## Scenarios\n", summary.to_string(index=False)]
    return "\n".join(parts) + "\n"


def main() -> None:
    ev = geo.load_evidence()
    raw = {y: chim.read_flows(y) for y in chim.YEARS}
    tables, summary = {}, []
    for sc in geo.SCENARIOS:
        g = geo.build(ev, sc, raw)
        geo.write(g)
        d = measure(g.settlements, g.flows)
        d.to_csv(geo.OUT / sc.name / "measures.csv", index=False)
        tables[sc.name] = d
        for y, t in d[d.ranked].groupby("year"):
            summary.append({"scenario": sc.name, "year": y, "ranked": len(t),
                            "out_median": round(t.out_rate.median() * 100, 2),
                            "in_median": round(t.in_rate.median() * 100, 2),
                            "flagged": int((t.notes != "").sum()),
                            "above_100": int((t[list(RATES)] > 1).any(axis=1).sum())})
    REPORT.write_text(report(tables["primary"], pd.DataFrame(summary)))
    print(pd.DataFrame(summary).to_string(index=False))


if __name__ == "__main__":
    main()
