# Data sources

Status: **acquired and verified 2026-11-23** by `src/acquire.py`. "Verified" means exact
size, SHA-256, zip integrity and expected contents. It does not mean the data are correct.

| | CHIM | GHS-FUA | GHS-POP |
|---|---|---|---|
| Contents | Flow matrices, populations at risk, boundaries, metadata | Functional Urban Area polygons | Estimated residents per grid cell |
| Version | Box copy, files dated 2017 | R2019A V1.0 | R2019A V1.0, epoch 2015 |
| Provider | GeoDa Center / F. Rowe | European Commission JRC | European Commission JRC |
| Format | Zip of zips: CSV-named text, shapefile, xlsx, rtf | Zip: GeoPackage, PDF | Zip: GeoTIFF (36,082 x 18,000), PDF |
| Download size (bytes) | 731,174,792 | 3,059,037 | 137,934,966 |
| Coverage | Chile, 304 harmonized municipalities | World; 31 FUAs coded Chile | World, 1 km cells |
| Period | 1977-82, 1987-92, 1997-2002 | 2015 | 2015 |
| Coordinate system | Declared CH1903, **suspect** | World Mollweide (ESRI:54009) | World Mollweide (ESRI:54009) |
| Licence | No data licence found; GeoDa says "as is". The describing article is CC BY | CC BY 4.0 | CC BY 4.0 |
| Redistribute? | No, until clarified | Allowed with credit; not committed | Allowed with credit; not committed |
| Checked | Verified; matches Phase 1 copy | Verified; matches Phase 1 copy | Verified; first copy |

## Download locations

- CHIM: https://uchicago.box.com/s/yqc97nq23hoeeqo5lkc2grlg98skokgk
  - The address in the CHIM article (s3.amazonaws.com/geoda/data/CHIM.zip) returns 404.
  - https://geodacenter.github.io/data-and-lab/data/CHIM.zip (48,566,027 bytes) works
    but **omits the flow matrices**. Do not use it.
- GHS-FUA: https://jeodpp.jrc.ec.europa.eu/ftp/jrc-opendata/GHSL/GHS_FUA_UCDB2015_GLOBE_R2019A/V1-0/GHS_FUA_UCDB2015_GLOBE_R2019A_54009_1K_V1_0.zip
- GHS-POP: https://jeodpp.jrc.ec.europa.eu/ftp/jrc-opendata/GHSL/GHS_POP_MT_GLOBE_R2019A/GHS_POP_E2015_GLOBE_R2019A_54009_1K/V1-0/GHS_POP_E2015_GLOBE_R2019A_54009_1K_V1_0.zip
- GHS-SMOD: https://jeodpp.jrc.ec.europa.eu/ftp/jrc-opendata/GHSL/GHS_SMOD_POP_GLOBE_R2019A/GHS_SMOD_POP2015_GLOBE_R2019A_54009_1K/V2-0/GHS_SMOD_POP2015_GLOBE_R2019A_54009_1K_V2_0.zip
  (14,072,420 bytes; settlement class per 1 km cell; 2015; World Mollweide; CC BY 4.0).
  JRC marks the R2019A grids as old releases. They are used to match GHS-FUA R2019A.
- GHSL licence: https://jeodpp.jrc.ec.europa.eu/ftp/jrc-opendata/GHSL/copyright.txt

## SHA-256 checksums

These record what we downloaded. The providers publish no checksum that we found, so
they detect later changes but do not prove authenticity.

- CHIM zip: `cf315e541993aef04b56dd77e5da470f0363ea3cbd543403cec277c8f01eeb8b`
- GHS-FUA zip: `d54de59b82b8c4d64a710f90ccd554975a3be92233f14115ac154094c3549979`
- GHS-POP zip: `8cda2bfd1dbdc7b2bc0fd9a08afa92efc202d37092d09e7bf1779c42fbe29559`
- GHS-SMOD zip: `30b0a04d2218b942b36e4619e575f78bc1600147daf0ea9787595eeb7198b914`

## Files we need from CHIM

- `Matrices.zip` -> `Matrices/{1982,1992,2002}/overall/overall_{year}.csv` (about 4.3 MB each)
- `Population.zip` -> `Population/{year}/overall/overall_{year}.csv`
- `GIS files.zip` -> `GIS files/Harmonised Municipalities/` (shapefile)
- `Documentation/`

`Matrices.zip` expands to about 8.4 GB, so it must not be extracted in full.

## What the `overall` matrices contain

- Counts of people by municipality now (`tmhabmun`) and five years before (`tm5ymun`),
  one row per pair, 304 x 304 = 92,416 rows per census, including same-municipality pairs.
- Verified: summing all 34 sex-by-age files reproduces `overall` in every cell, in all
  three years. So do the education files (170, 164 and 164).
- Universe: ages 5+ (age groups 2-18). No abroad or unknown category, so international
  arrivals are excluded. CHIM does not say how many unknown origins were dropped.
- One date comparison per person: intermediate moves, returns within the interval,
  deaths and emigrants are not observed.

## Licensing and redistribution (CHIM)

We found no licence covering the data. The readme has none and GeoDa offers it "as is";
the CC BY licence of the REGION article covers the article. Until this is resolved:

- The original archive is kept only in `data/raw/chim/CHIM.zip` (local, read-only).
- Neither CHIM files nor tables derived from its flows are published or redistributed.

## Citations

- Rowe, F. (2017). The CHilean Internal Migration (CHIM) database. *REGION*, 4(3), R1-R6.
  https://doi.org/10.18335/region.v4i3.198
- GHSL citations: to be copied from the product pages at download.
