# Geographic boundaries and Functional Urban Areas

Method only. Numerical findings are kept locally (decision 7).

## Units

Polygons are CHIM "Temporal Municipalities": 304 units (Rowe 2017) held constant over three
censuses. Some combine several present-day communes. Codes equal the metadata codes, but
**rows are in a different order**, so joins use the code.

## Coordinate reference system

- **Assigning** a CRS changes the label and no coordinates. Right when the label is wrong.
- **Reprojecting** computes new coordinates for the same places. Right when the label is correct.

Reprojecting from a wrong label moves everything to the wrong place. The declared Swiss
CH1903 is wrong: it would put Chile in the Arctic. Coordinates match WGS 84 / UTM 19S
(EPSG:32719). The datum was tested by measuring the distance from boundary vertices to an official-source reference map under each candidate. PSAD56 and SAD69 fit worse. SIRGAS-Chile is
indistinguishable at this precision. `read_boundaries()` assigns EPSG:32719, then reprojects
a copy to World Mollweide for the overlay.

Three units (Juan Fernandez, Isla de Pascua, Antartica) are drawn as map insets at false
positions, so their location, area and neighbours cannot be used.

Reference map: geoBoundaries CHL ADM3 2020, from the Biblioteca del Congreso Nacional and OCHA,
CC BY 3.0 IGO, https://www.geoboundaries.org. Validation only. It probably shares official
ancestry with CHIM's boundaries, so agreement establishes the CRS, not their accuracy.
SHA-256 `f3833ce1965394ae705e3793b50bdd007775b43da604251871deffed04f3bffd`.

## Matching municipalities to FUAs

1. Cut each 1 km GHS-POP cell into 10 x 10 pieces and give its people to units by land share.
   Cells partly at sea keep all their people on land.
2. FUAs follow whole cells, so each cell is inside exactly one FUA or none.
3. Share = people of a unit inside one FUA / all people of the unit.
4. Assign the unit to its largest-share FUA if that share is at least 50%.

The paper uses "at least one half of the resident population". Half means most residents live
in the city, and no unit can qualify for two FUAs (an exact 50/50 split aside).

Population rather than area, because a large unit may be mostly empty with its people in a city.
Toy: land 25% inside, people 67% inside: assigned (`tests/test_boundaries.py`).

Once merged, flows between units of one settlement become non-migration. Merge by adding
rows and columns; the diagonal then includes moves between merged members.

Merged FUAs, small cities and displaced units: docs/geography.md.

2015 city limits and 2015 population are applied to earlier censuses, as in the paper.
