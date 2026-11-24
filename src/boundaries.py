"""Municipal boundaries, and their population overlap with Functional Urban Areas.

Read-only with respect to data/raw. Nothing here merges municipalities.
"""

from pathlib import Path

import geopandas as gpd
import numpy as np
import rasterio
import shapely
from rasterio.features import rasterize
from rasterio.windows import from_bounds
from rasterio.windows import transform as window_transform

from chim import CHIM, ChimError, read_metadata

RAW = CHIM.parent
CRS = "EPSG:32719"     # WGS 84 / UTM 19S; evidence in docs/boundaries.md
GRID_CRS = "ESRI:54009"
CELL = 1000

# Drawn as map insets at false positions, so location and area are not usable.
DISPLACED = ("05103", "05201", "12202")


def read_boundaries(repair: bool = True) -> gpd.GeoDataFrame:
    """Boundaries in metadata order, indexed by code, with the corrected CRS label.

    set_crs changes only the label. It moves nothing: the coordinates were already UTM.
    """
    path = CHIM / "gis" / "Harmonised_municipalities.shp"
    gdf = gpd.read_file(path).set_crs(CRS, allow_override=True)
    codes = read_metadata().code
    if len(gdf) != len(codes) or set(gdf.C_MUN) != set(codes):
        raise ChimError("boundary codes do not equal metadata codes")
    gdf = gdf.set_index("C_MUN").loc[codes]
    if not gdf.total_bounds[0] > -1e6 or not 3e6 < gdf.total_bounds[1] < gdf.total_bounds[3] < 9e6:
        raise ChimError("coordinates are not in the expected UTM range")
    if repair:
        gdf.geometry = shapely.make_valid(gdf.geometry.values)
    return gdf


def read_fuas() -> gpd.GeoDataFrame:
    path, = (RAW / "ghs_fua").glob("*.gpkg")
    return gpd.read_file(path, where="Cntry_ISO = 'CHL'").reset_index(drop=True)


def read_population(bounds):
    """GHS-POP cells covering the bounds (Mollweide), with nodata as zero."""
    path, = (RAW / "ghs_pop").glob("*.tif")
    x0, y0 = np.floor(np.array(bounds[:2]) / CELL) * CELL
    x1, y1 = np.ceil(np.array(bounds[2:]) / CELL) * CELL
    with rasterio.open(path) as src:
        window = from_bounds(x0, y0, x1, y1, src.transform).round_offsets().round_lengths()
        pop = src.read(1, window=window)
        return np.where(pop == src.nodata, 0, pop), window_transform(window, src.transform)


def population_by_zone(units, zone_id, n_zones, pop, transform, k: int = 10) -> np.ndarray:
    """People in each unit (rows) in each zone (columns 0..n_zones-1) of a cell-level raster.

    Zones follow whole grid cells. Units do not, so each cell is cut into k x k sub-cells
    and its people are divided among units by land share, counting only land that belongs
    to some unit (nobody is placed in the sea).
    """
    size = transform.a
    coverage = np.zeros(pop.shape)
    pieces = []
    for geom in units.geometry:
        x0, y0, x1, y1 = geom.bounds
        c0, c1 = int((x0 - transform.c) // size), int((x1 - transform.c) // size) + 1
        r0, r1 = int((transform.f - y1) // size), int((transform.f - y0) // size) + 1
        c1, r1 = min(c1, pop.shape[1]), min(r1, pop.shape[0])
        fine = rasterio.Affine(size / k, 0, transform.c + c0 * size,
                               0, -size / k, transform.f - r0 * size)
        mask = rasterize([(geom, 1)], out_shape=((r1 - r0) * k, (c1 - c0) * k),
                         transform=fine, fill=0, dtype="uint8")
        share = mask.reshape(r1 - r0, k, c1 - c0, k).sum(axis=(1, 3)) / k**2
        window = (slice(r0, r1), slice(c0, c1))
        coverage[window] += share
        pieces.append((window, share))
    coverage[coverage == 0] = 1
    table = np.zeros((len(units), n_zones))
    for i, (window, share) in enumerate(pieces):
        people = pop[window] * share / coverage[window]
        table[i] = np.bincount(zone_id[window].ravel(), people.ravel(), n_zones)
    return table


def fua_raster(fuas, shape, transform) -> np.ndarray:
    """0 outside any FUA; position in the table + 1 inside one."""
    return rasterize([(g, i + 1) for i, g in enumerate(fuas.geometry)],
                     out_shape=shape, transform=transform, fill=0, dtype="int32")


def population_by_fua(units, fuas, pop, transform, k: int = 10) -> np.ndarray:
    """People in each unit outside any FUA (column 0) and in each FUA (columns 1..)."""
    zones = fua_raster(fuas, pop.shape, transform)
    return population_by_zone(units, zones, len(fuas) + 1, pop, transform, k)


def read_smod(shape, transform) -> np.ndarray:
    """GHS-SMOD settlement class of each cell in the population window."""
    path, = (RAW / "ghs_smod").glob("*.tif")
    height, width = shape
    with rasterio.open(path) as src:
        window = from_bounds(transform.c, transform.f - height * CELL,
                             transform.c + width * CELL, transform.f,
                             src.transform).round_offsets().round_lengths()
        smod = src.read(1, window=window)
    if smod.shape != tuple(shape):
        raise ChimError("settlement grid does not cover the population window")
    return smod


def best_fua(table: np.ndarray):
    """Largest single-FUA share of each unit's people, and that FUA's index (-1 if empty)."""
    total = table.sum(axis=1)
    share = np.divide(table[:, 1:].max(axis=1), total, out=np.zeros(len(table)), where=total > 0)
    return share, np.where(total > 0, table[:, 1:].argmax(axis=1), -1)
