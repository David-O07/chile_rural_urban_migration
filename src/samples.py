"""Regression samples and weights for Phase 4 (docs/measures.md). No model is fitted here.

A specification chooses rows and weights from the measures table. It never changes a flow,
a denominator, a rate or a rank.
"""

from dataclasses import dataclass

import numpy as np
import pandas as pd

import chim
import geography as geo
import measures as ms

FLORIDA, SAN_PEDRO, SANTIAGO = "R08103", "R13505", "F2072"
EXPECTED_NAMES = {FLORIDA: "Florida", SAN_PEDRO: "San Pedro", SANTIAGO: "Santiago"}
WEIGHTS = ("avg_pop", "log_avg_pop")
ROLES = ("primary", "sensitivity", "supplementary")


class SampleError(Exception):
    """A specification does not fit the measures table."""


@dataclass(frozen=True)
class Spec:
    name: str
    description: str
    role: str = "sensitivity"
    drop: tuple[str, ...] = ()                 # settlement ids left out
    drop_years: tuple[int, ...] = chim.YEARS   # in these periods
    min_population: float = 0                  # average population, in each period
    weight: str | None = None                  # one of WEIGHTS


# Fixed before any model is fitted. Every specification is reported, whatever it shows.
SPECS = (
    Spec("unweighted", "All ranked settlements, equal weight", role="primary"),
    Spec("no_florida_san_pedro", "Without Florida and San Pedro in every period (main sample check)",
         drop=(FLORIDA, SAN_PEDRO)),
    Spec("no_florida_san_pedro_2002", "Without Florida and San Pedro in 2002 only (additional check)",
         drop=(FLORIDA, SAN_PEDRO), drop_years=(2002,)),
    Spec("min_500", "Average population of at least 500 in that period",
         min_population=ms.SMALL_POPULATION),
    Spec("no_santiago", "Without Santiago in every period", drop=(SANTIAGO,)),
    Spec("weighted", "Weighted by average population: a different question",
         role="supplementary", weight="avg_pop"),
    Spec("log_weighted", "Weighted by the natural log of average population: a different question",
         role="supplementary", weight="log_avg_pop"),
)


def select(d: pd.DataFrame, spec: Spec) -> pd.DataFrame:
    """Rows of the measures table in the sample, with a weight column."""
    for sid in spec.drop:
        names = set(d.settlement_name[d.settlement_id == sid])
        if names != {EXPECTED_NAMES[sid]}:
            raise SampleError(f"{sid} is not {EXPECTED_NAMES[sid]} in this geography")
    keep = d.ranked & (d.avg_pop >= spec.min_population)
    keep &= ~(d.settlement_id.isin(spec.drop) & d.year.isin(spec.drop_years))
    out = d[keep].copy()
    out["log_avg_pop"] = np.log(out.avg_pop)
    if spec.weight not in (None, *WEIGHTS):
        raise SampleError(f"unknown weight {spec.weight}")
    out["weight"] = out[spec.weight] if spec.weight else 1.0
    if out.empty or not (out.weight > 0).all():
        raise SampleError("empty sample or non-positive weight")
    if out[["position", "out_rate", "in_rate"]].isna().any().any():
        raise SampleError("a sampled settlement lacks a rank or rate")
    return out


def effective_size(w: pd.Series) -> float:
    """Kish effective sample size: how many equal weights carry the same information."""
    return float(w.sum() ** 2 / (w ** 2).sum())


def sizes(d: pd.DataFrame, geography: str) -> pd.DataFrame:
    rows = []
    for spec in SPECS:
        for year, g in select(d, spec).groupby("year"):
            rows.append({"geography": geography, "spec": spec.name, "role": spec.role, "year": year, "n": len(g),
                         "cities": int(g.type.isin(ms.URBAN).sum()),
                         "rural": int((g.type == geo.RURAL).sum()),
                         "contiguity_n": int(g.spatial_model.sum()),
                         "effective_n": round(effective_size(g.weight), 1),
                         "largest_weight": round(g.weight.max() / g.weight.sum(), 3)})
    return pd.DataFrame(rows)
