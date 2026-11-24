# Ranking and rates

Agreed definitions (decisions 23-27), implemented in `src/measures.py`.
All quantities are per settlement and per period, from the aggregated flow matrix.

## Populations

- **Origin population** P0: row sum. People counted who lived there five years earlier.
- **Destination population** P1: column sum. People counted who live there at the census.
- **Average population** P = (P0 + P1) / 2.

The average is an **approximation** of the population during the five years. It assumes steady
change between the two dates, covers only people aged 5+ at the census who lived in Chile at both
dates, and is not person-years of exposure.

Toy (docs/chim_interpretation.md): A has P0 = 100, P1 = 105, P = 102.5.

## Who is counted

- **Antártica** is removed from all three matrices before anything is calculated. People who
  moved to or from it, or stayed there, are in no population, departure or arrival. The raw
  matrices are unchanged.
- **Isla de Pascua and Juan Fernández** stay in the matrices. Moves between them and the mainland are
  ordinary departures and arrivals. They have rates but no rank. Check: `no_islands`.

## Position on the rural-urban continuum

1. Rural settlements in ascending order of density, P / area.
2. Then cities (FUA cities, and small cities where a scenario has them) in ascending order of P.
3. Position = rank / number of ranked settlements **in that period**: just above 0 for the
   sparsest rural settlement, 1 for the largest city.

Every city ranks above every rural settlement, as in the paper. Isla de Pascua and
Juan Fernández are unranked and not counted in the number. Sensitivity: the same with P0, and
with P1. Because ranks use period-specific populations, a settlement's position can change between
periods although its boundaries do not.

## Five-year rates

| | Primary | Sensitivity |
|---|---|---|
| Out-migration | departures / P0 | departures / P |
| In-migration | arrivals / P | arrivals / P1 |

Departures = row sum - diagonal. Arrivals = column sum - diagonal. Rates are for five years and
are not annualized. Toy: A has 10 departures and 15 arrivals, so out 10/100 = 10.0%
and in 15/102.5 = 14.6%.

## Edge cases

- Zero denominator: the rate is missing and flagged, never zero or infinite.
- Ties: settlements share the average rank.
- Nothing is clipped or removed. The `notes` column flags, per period: a missing rate; any rate above
  100%; average population under 500; destination/origin population outside 2/3 to 3/2; a
  primary rate more than 3 interquartile ranges beyond the quartiles of ranked settlements.
  These thresholds were set before looking at the results.

## Consequences to keep in mind

- The primary out- and in-rates have **different denominators**, so their difference is not a net
  migration rate. The average-denominator versions share one base and can be compared.
- departures / P0 and arrivals / P1 cannot exceed 100%. Rates on the average, for either flow, can (below
  200%, or exactly 200% when one of the two populations is zero).
- Population enters both the denominator and the rank, so some correlation between rate and
  position is built in. The alternative ranks and denominators show how much it matters.
- Rates are conditional on survival, presence in Chile and a known previous residence.
- The paper gives no formula. A related paper by the same group (Beckendorff et al. 2026,
  https://doi.org/10.1186/s40878-026-00535-6) uses the population five years earlier for
  out-migration. Our in-migration denominator is our own choice.

## Suspected artefacts in the source data

Tracing flagged settlements suggests that some recorded moves are not moves. None is corrected.

1. **Boundary changes of 1979.** Eight large one-way flows in 1977-82 match transfers of territory in
   Decreto Ley 2868. People may have named the former municipality without moving. Evidence and
   sensitivity scenario: docs/historical_boundaries.md.
2. **Similar names in 1997-2002.** Florida (Biobío) and La Florida (Santiago); San Pedro (near Melipilla)
   and San Pedro de la Paz (created 1995, inside the Concepción unit). The flows look like earlier
   residences assigned to the wrong place. **Possible, not confirmed.** Both stay in the primary analysis.

If so, both inflate out-rates of the named origin, and the first also inflates in-rates of the
receiving municipality. Very small southern units with military, mining or farm workers also have extreme rates,
which may be real.

## Regression samples (`src/samples.py`)

Specifications choose rows and weights. They never change a flow, denominator, rate or rank, and
settlements are not re-ranked, so any difference comes from the sample alone.

| Specification | Role | Rows | Weight |
|---|---|---|---|
| `unweighted` | **Primary** | All ranked settlements | 1 |
| `no_florida_san_pedro` | Sensitivity (main sample check) | Without both, in every period | 1 |
| `no_florida_san_pedro_2002` | Sensitivity (additional) | Without both, in 2002 only | 1 |
| `min_500` | Sensitivity | Average population at least 500 in that period | 1 |
| `no_santiago` | Sensitivity | Without Santiago, in every period | 1 |
| `weighted` | Supplementary | All ranked settlements | Average population of that period |
| `log_weighted` | Supplementary | All ranked settlements | Natural log of that average population |

The list was fixed before any model was fitted. **No specification is chosen or dropped because of
its result; all are reported.**

**Florida and San Pedro.** This tests **sample influence**: whether the result depends on these two
observations. It does **not** correct potentially misassigned flows. Their flows stay in the matrices
unchanged, so departures, arrivals and populations of every other settlement are the same, as are
their own measures in the files. If some of their departures are misassigned, the matching arrivals
elsewhere remain. The every-period version keeps the sample constant, so changes between periods
are not caused by its composition.

**Santiago.** Leaving it out removes it as an observation only. Its flows and everyone's rank
stay, so the largest remaining position is below 1.

**Weights.** Weighted fits are supplementary. They ask about the settlement of the average person, or a
compromise with it, while the unweighted fit asks about the average settlement. Disagreement
does not refute the primary result, and agreement does not confirm it. Under population weights the largest city
dominates. Log weights depend on the unit of measurement (people) and have no sampling
interpretation; they only reduce concentration. The effective sample size
(sum of weights)^2 / (sum of squared weights) and the largest weight are reported beside every weighted fit.

**Contiguity.** Dropping settlements can leave others without neighbours. Neighbours must be recomputed
for each sample in Phase 4.
