# Settlement geography

Method only. Counts derived from CHIM are kept locally (decision 7). Code: `src/geography.py`.

## Rules, in order

1. Excluded municipalities (Antártica) are removed. Flows that start or end there are dropped
   and counted.
2. Municipalities drawn at false positions (Isla de Pascua, Juan Fernández) cannot be tested
   against the grids: `unclassified`, with no area and not for neighbour models.
3. At least 50% of people in one FUA: `fua_city`. An exact tie stops the run.
4. Listed FUAs are merged (Concepción and Chiguayante).
5. Unmatched, with at least 50% of people in dense GHS-SMOD cells: `small_city`.
6. Otherwise `rural`. Small cities and rural units are single municipalities.

## Small cities

Dense cells are GHS-SMOD class 30 (urban centre) in the primary scenario, 30 + 23 in the main
sensitivity check (`smod_30_23`) and 30 + 23 + 22 in the broad check (`smod_30_23_22`).

**The primary definition adds no small cities in our data**, because every populated class-30
cell in Chile already lies inside an FUA. All our cities are therefore FUA cities. The paper's
Chilean count combines FUAs and small cities over different, coarser units (IPUMS), so the
two counts are **not directly comparable**, and similar totals would not show that the
classifications agree. The paper does not list the classes it uses; class 30 is our reading.

## Identifiers

One geography is used for all three censuses. Identifiers: `F` + FUA ids, `S`, `R` or `U` +
municipality code. Scenarios each change one rule.

## Traceability

`crosswalk.csv` has one row per municipality, with its settlement and the evidence for it.
`settlements.csv` lists every constituent municipality. Flows are built from the crosswalk only.

## Aggregation

With M the 304 x 304 matrix (origins in rows) and A the 304 x S membership matrix of zeros
and ones, settlement flows are A' M A. The diagonal then includes moves between two
municipalities of one settlement. Toy example, A and B merged:

|  | A | B | C |
|---|---|---|---|
| **A** | 90 | 8 | 2 |
| **B** | 5 | 40 | 5 |
| **C** | 10 | 0 | 20 |

becomes AB->AB = 90+8+5+40 = 143, AB->C = 7, C->AB = 10, C->C = 20. Still 180 people; migrants fall
from 30 to 17 because 13 moves are now internal.

Checked on every run: total people; origin and destination totals; every municipality assigned
once or excluded; one type per settlement; populations. Areas are equal-area (World Mollweide).

## Neighbours

Queen contiguity: settlements are neighbours if their boundaries share an edge or a point.
It is computed **after** merging, between settlements. Contacts with excluded or displaced units
do not count. `spatial_model` is true for settlements with a usable position and at least one
neighbour. The primary contiguity models leave out:

- Isla de Pascua and Juan Fernández (false positions; also unranked);
- Puqueldón and Guaitecas (correct positions, no contact). They stay in non-spatial analysis.

The remaining settlements do not form one connected map: Chiloé, Quinchao with Curaco de
Vélez, and Tierra del Fuego with Cabo de Hornos are separate groups.

**Sensitivity option for later (not implemented).** k-nearest neighbours on every settlement
with a usable position, including Puqueldón and Guaitecas: geodesic distance between
representative points, k = 4 (the median number of contiguous neighbours) with k = 6 as a check,
row-standardized. Every unit then has neighbours and the map is more connected, but
neighbours may be across water or far away. k-nearest relations are not symmetric.

## Not resolved

- **Juan Fernández area.** The inset seems to cover one of its main islands; the reference
  shape also holds a second large island and a distant group. No area is assigned.
- **Isla de Pascua.** The reference map gives a usable shape, but the grid places nearly all
  its people in "very low density" cells. It stays unclassified.
