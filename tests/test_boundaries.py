"""Population overlap on a small invented grid where the answers are known."""

import sys
from pathlib import Path

import geopandas as gpd
import numpy as np
import pytest
import rasterio
from shapely.geometry import box

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
import boundaries as bd
import chim

# 4 x 1 cells of 1 km. People: 100, 300, 0, 50. Top-left corner (0, 1000).
POP = np.array([[100.0, 300.0, 0.0, 50.0]])
T = rasterio.Affine(1000, 0, 0, 0, -1000, 1000)
FUAS = gpd.GeoDataFrame(geometry=[box(1000, 0, 2000, 1000)], crs=bd.GRID_CRS)


def units(*boxes):
    return gpd.GeoDataFrame(geometry=[box(*b) for b in boxes], crs=bd.GRID_CRS)


def test_whole_cells():
    t = bd.population_by_fua(units((0, 0, 2000, 1000), (2000, 0, 4000, 1000)), FUAS, POP, T)
    assert t == pytest.approx(np.array([[100, 300], [50, 0]]))
    share, best = bd.best_fua(t)
    assert share == pytest.approx([0.75, 0])


def test_cell_split_between_units_by_land():
    t = bd.population_by_fua(units((0, 0, 1500, 1000), (1500, 0, 4000, 1000)), FUAS, POP, T)
    assert t == pytest.approx(np.array([[100, 150], [50, 150]]))


def test_people_in_partly_sea_cell_stay_on_land():
    t = bd.population_by_fua(units((0, 0, 1500, 1000)), FUAS, POP, T)
    assert t.sum() == pytest.approx(400)


def test_area_and_population_can_disagree():
    """One quarter of the land but two thirds of the people lie in the FUA."""
    t = bd.population_by_fua(units((0, 0, 4000, 1000)), FUAS, POP, T)
    assert bd.best_fua(t)[0] == pytest.approx([300 / 450])


def test_unpopulated_unit_has_no_fua():
    t = bd.population_by_fua(units((2000, 0, 3000, 1000)), FUAS, POP, T)
    share, best = bd.best_fua(t)
    assert share[0] == 0 and best[0] == -1


@pytest.mark.skipif(not (chim.CHIM / "gis").exists(), reason="raw data not downloaded")
def test_real_boundaries_follow_metadata_order():
    gdf = bd.read_boundaries()
    assert list(gdf.index) == list(chim.read_metadata().code)
    assert gdf.is_valid.all() and gdf.crs.to_epsg() == 32719


@pytest.mark.skipif(not (chim.CHIM / "gis").exists(), reason="raw data not downloaded")
def test_crs_label_change_moves_nothing():
    import geopandas
    raw = geopandas.read_file(chim.CHIM / "gis" / "Harmonised_municipalities.shp")
    raw = raw.set_index("C_MUN").loc[chim.read_metadata().code]
    assert (raw.total_bounds == bd.read_boundaries(repair=False).total_bounds).all()
