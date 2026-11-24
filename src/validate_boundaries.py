"""Step 4: read-only checks on boundaries, FUAs and the population grid.

    python src/validate_boundaries.py > reports/local/validation_step4.md

Nothing is merged and no analytical units are written. Assignments shown are diagnostic.
Reference map for the CRS test: geoBoundaries CHL ADM3 (CC BY 3.0 IGO), see docs/boundaries.md.
"""

import sys

import geopandas as gpd
import numpy as np
import pandas as pd
import shapely

from boundaries import (DISPLACED, GRID_CRS, RAW, best_fua, population_by_fua, read_boundaries,
                        read_fuas, read_population)
from chim import CHIM, name_key, read_metadata


def row(name, detail):
    print(f"| {name} | {detail} |")


def section(title):
    print(f"\n## {title}\n\n| Check | Result |\n|---|---|")


def main() -> int:
    meta = read_metadata().set_index("code")["name"]
    raw = gpd.read_file(CHIM / "gis" / "Harmonised_municipalities.shp")
    units = read_boundaries()
    geoms = units.geometry.values
    print("# Step 4 validation report (local only)")

    section("Units and attributes")
    row("Boundary and metadata codes equal", set(raw.C_MUN) == set(meta.index))
    row("Boundary row order equals metadata order", list(raw.C_MUN) == list(meta.index))
    row("Missing attribute values", int(raw.drop(columns="geometry").isna().sum().sum()))

    section("Coordinate reference system")
    row("Declared", raw.crs.name)
    inside = raw.to_crs(4326).total_bounds.round(1).tolist()
    row("Bounds if the declaration were true (lon/lat)", inside)
    row("Bounds under UTM 19S (lon/lat)", units.to_crs(4326).total_bounds.round(1).tolist())
    ref = gpd.read_file(RAW / "reference" / "geoBoundaries-CHL-ADM3.geojson").to_crs(32719)
    ref["key"] = ref.shapeName.map(name_key)
    ref = ref[~ref.key.duplicated(keep=False)].set_index("key").geometry
    ref = ref.map(shapely.make_valid).boundary
    sample = [c for c in meta.index if name_key(meta[c]) in ref.index and c not in DISPLACED]
    for label, epsg in [("WGS 84 / UTM 19S", 32719), ("SAD69 / UTM 19S", 29189),
                        ("PSAD56 / UTM 19S", 24879), ("WGS 84 / UTM 18S", 32718)]:
        moved = raw.set_index("C_MUN").set_crs(epsg, allow_override=True).to_crs(32719).geometry
        d = []
        for c in sample:
            xy = shapely.get_coordinates(moved[c])
            xy = xy[::max(1, len(xy) // 60)]
            d.append(np.median(shapely.distance(shapely.points(xy), ref[name_key(meta[c])])))
        row(f"{label}: distance to reference boundaries",
            f"median {np.median(d):.0f} m over {len(sample)} units; within 100 m: {np.mean(np.array(d) < 100):.0%}")
    for c in DISPLACED:
        p = gpd.GeoSeries([units.geometry[c].representative_point()], crs=units.crs).to_crs(4326).iloc[0]
        row(f"Displaced unit {c} {meta[c]}", f"drawn at lon {p.x:.1f}, lat {p.y:.1f}")

    section("Geometry")
    invalid = ~raw.is_valid
    row("Types", raw.geom_type.value_counts().to_dict())
    row("Empty", int(raw.is_empty.sum()))
    row("Invalid", f"{int(invalid.sum())}: {[meta[c] for c in raw.C_MUN[invalid]]}")
    before = shapely.area(raw.set_index("C_MUN").geometry.loc[units.index].values)
    row("Largest area change from repair (m2)", f"{np.abs(before - shapely.area(geoms)).max():.2f}")
    tree = shapely.STRtree(geoms)
    i, j = tree.query(geoms, predicate="intersects")
    keep = i < j
    i, j = i[keep], j[keep]
    contact = shapely.intersection(geoms[i], geoms[j])
    area = shapely.area(contact)
    original = raw.set_index("C_MUN").geometry.loc[units.index].values
    for q in np.where(~shapely.is_valid(original))[0]:
        old, new = original[q], geoms[q]
        near = [x for x in tree.query(shapely.box(*old.bounds)) if x != q]
        edge = shapely.boundary(old)
        touched = {x for x in near if shapely.intersects(edge, geoms[x])}
        now_touched = {x for x in near if shapely.intersects(new, geoms[x])}
        same_vertices = set(map(tuple, shapely.get_coordinates(old))) == set(map(tuple, shapely.get_coordinates(new)))
        row(f"Repair {meta.iloc[q]}", f"{shapely.is_valid_reason(old).split('[')[0]} -> valid {shapely.is_valid(new)}; "
            f"area change {new.area - old.area:+.6f} m2; same vertices {same_vertices}; same neighbours {touched == now_touched}")
    row("Overlaps over 1 m2", f"{int((area > 1).sum())} pairs, {area.sum() / 1e6:.2f} km2 in total, largest {area.max() / 1e6:.2f} km2")
    row("Neighbour pairs / point-only contacts", f"{len(i)} / {int(((shapely.length(contact) == 0) & (area == 0)).sum())}")
    degree = np.bincount(np.r_[i, j], minlength=len(geoms))
    row("Units with no neighbour", [meta.iloc[q] for q in np.where(degree == 0)[0]])

    section("Units holding more than one 2020 commune (over half of each commune)")
    now = gpd.read_file(RAW / "reference" / "geoBoundaries-CHL-ADM3.geojson").to_crs(32719)
    now.geometry = shapely.make_valid(now.geometry.values)
    a, b = shapely.STRtree(now.geometry.values).query(geoms, predicate="intersects")
    share = shapely.area(shapely.intersection(geoms[a], now.geometry.values[b])) / now.geometry.area.values[b]
    parts = pd.DataFrame({"unit": units.index[a], "commune": now.shapeName.values[b]})[share > 0.5]
    for c, names in parts.groupby("unit").commune.apply(list).items():
        if len(names) > 1:
            row(f"{c} {meta[c]}", ", ".join(names))

    section("FUAs and population")
    grid = units.to_crs(GRID_CRS)
    fuas = read_fuas()
    bounds = np.r_[np.minimum(grid.total_bounds[:2], fuas.total_bounds[:2]),
                   np.maximum(grid.total_bounds[2:], fuas.total_bounds[2:])]
    pop, transform = read_population(bounds)
    table = population_by_fua(grid, fuas, pop, transform)
    share, which = best_fua(table)
    row("FUA people located inside units / published FUA population",
        f"{table[:, 1:].sum() / fuas.FUA_p_2015.sum():.4f}")
    row("Units with no people on the grid", [meta.iloc[q] for q in np.where(table.sum(1) == 0)[0]])
    for t in (0.3, 0.4, 0.5, 0.6, 0.7, 0.75):
        row(f"Threshold {t}", f"{int((share >= t).sum())} units in {len(set(which[share >= t]))} FUAs")
    row("Units with share 0.4-0.6", [(meta.iloc[q], round(float(share[q]), 3)) for q in np.where((share > .4) & (share < .6))[0]])
    for q in range(len(units)):
        s = table[q, 1:] / max(table[q].sum(), 1)
        if (s > 0.01).sum() > 1:
            row(f"Several FUAs: {meta.iloc[q]}", [(fuas.eFUA_name[k], round(float(s[k]), 3)) for k in np.where(s > .01)[0]])
    print("\n| FUA | 2015 people | Units at 0.5 | Share of FUA covered | Member people / FUA people |\n|---|---|---|---|---|")
    for k in range(len(fuas)):
        m = np.where((share >= 0.5) & (which == k))[0]
        print(f"| {fuas.eFUA_name[k]} | {fuas.FUA_p_2015[k]:,.0f} | {len(m)} | "
              f"{table[m, k + 1].sum() / fuas.FUA_p_2015[k]:.2f} | {table[m].sum() / fuas.FUA_p_2015[k]:.2f} |")
    ratio = pd.Series(table.sum(1) / units.Pop_2002.to_numpy())
    section("Grid population 2015 / CHIM census 2002")
    row("Quantiles 1, 5, 50, 95, 99%", ratio.quantile([.01, .05, .5, .95, .99]).round(2).tolist())
    return 0


if __name__ == "__main__":
    sys.exit(main())
