# CHIM data dictionary

Raw files as downloaded. "Verified" means checked by `src/validate_raw.py`; "documented"
means stated by CHIM (readme, workbook or Rowe 2017); "inferred" means our reading.

## Flows: `flows/overall_{1982,1992,2002}.csv`

Tab-separated despite the `.csv` name. Mac Roman encoding. 92,416 rows = 304 x 304.
**No geographic code column.** Unit: one ordered pair of municipalities.

| Field | Type | Meaning | Basis |
|---|---|---|---|
| `tmhabmun` | text, padded with spaces | **Destination**: municipality of usual residence at the census | Verified |
| `tm5ymun` | text, padded with spaces | **Origin**: municipality of usual residence five years earlier | Verified |
| `freq` | integer, >= 0 | Number of people (not a rate), ages 5+ | Verified; ages documented |

Row order: `tm5ymun` changes every 304 rows; `tmhabmun` cycles within it. The order of
municipalities is the metadata code order in all three years (verified).

## Populations at risk: `population/overall_{1982,1992,2002}.csv`

Same format. 304 rows.

| Field | Type | Meaning | Basis |
|---|---|---|---|
| `tm5ymun` | text | Municipality of usual residence five years earlier | Verified |
| `freq` | integer | Sum of `flows.freq` over all destinations, stayers included | Verified exactly |

It adds no information beyond the flows. It is not the census population, and not the true
population at the start of the interval: it counts only those later enumerated in Chile,
in scope and with a known origin.

## Boundaries: `gis/Harmonised_municipalities.*`

Shapefile, 304 polygons. Row order is **not** the flow order. Join on code only.

| Field | Type | Meaning | Basis |
|---|---|---|---|
| `IDN_1` | number | Row identifier; not a municipality code | Documented |
| `C_REG`, `REG` | text | Region code (2 digits), name | Documented; prefix verified |
| `C_PROV`, `PROV` | text | Province code (3 digits), name | Documented; prefix verified |
| `C_MUN` | text | **Municipality code (5 digits, keep leading zero)** | Verified unique; equals metadata |
| `MUN` | text | Name, damaged accents | Verified |
| `Pop_1982/1992/2002` | number | Census population, all ages | Documented |

Coordinate system: EPSG:32719; the declared CH1903 is wrong (docs/boundaries.md).

## Metadata: `documentation/Variable listing and metadata.xlsx`, sheet `CHIM Geography`

| Field | Meaning |
|---|---|
| Temporal Municipality code | Stored as a number, so the leading zero must be restored |
| Temporal Municipality name | Correctly accented: use for display |
| Region and province codes | Spreadsheet formulas derived from the municipality code |

"Temporal Municipality" is CHIM's term for a harmonized unit, sometimes a merger. The name
is meant to be that of the largest member in 1992 (documented).
