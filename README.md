# Spatial diffusion of internal migration in Chile

A partial conceptual replication, for one country, of Lerch, Du & Beckendorff (2026),
*The Spatial Diffusion of Internal Migration Across the Rural-Urban Continuum in
Developing Countries* (https://doi.org/10.1007/s10680-026-09774-w).

**Status:** Phase 2, data acquisition and preparation. There are no results yet.

## Research question

How did the urban gradients of out- and in-migration change across Chile between
1977-82, 1987-92 and 1997-2002, and are the estimates robust to spatial dependence?

An *urban gradient* is the slope relating a settlement's migration rate to its position
on a scale from sparse countryside to the largest city.

## Data sources

| Dataset | Used for | Source |
|---|---|---|
| CHIM (Rowe 2017) | Migration flows, populations, municipal boundaries | [GeoDa page](https://geodacenter.github.io/data-and-lab/CHIM/), [paper](https://doi.org/10.18335/region.v4i3.198) |
| GHS-FUA R2019A | Functional Urban Area boundaries | [GHSL](https://human-settlement.emergency.copernicus.eu/ghs_fua.php) |
| GHS-SMOD R2019A, 2015, 1 km | Which cells are dense urban | [GHSL](https://human-settlement.emergency.copernicus.eu/) |
| GHS-POP R2019A, 2015, 1 km | Population overlap between municipalities and FUAs | [GHSL](https://human-settlement.emergency.copernicus.eu/) |

Raw data is not in this repository. See [docs/data_sources.md](docs/data_sources.md)
for locations, sizes, checksums and licences.

## Scope and limits

- This does not reproduce the paper's 41-country result, and its data is not the
  paper's: CHIM replaces the IPUMS samples.
- Three periods in one country can describe change but cannot identify its causes.

Methodological choices are recorded in [docs/decisions.md](docs/decisions.md);
the geography in [docs/geography.md](docs/geography.md) and planned measures in
[docs/measures.md](docs/measures.md).

## Setup

```sh
python3.11 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Layout

```
data/raw/        original downloads, never edited (not committed)
data/processed/  cleaned outputs (not committed)
docs/            data sources, data dictionary, decision log
src/             Python modules
tests/           automated checks
reports/figures/ figures
```
