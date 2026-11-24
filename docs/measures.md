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

1. **Boundary changes of 1979.** Some large one-way flows between adjacent rural municipalities in
   1977-82 may come from changes of municipal territory rather than moves. Not resolved here.
2. **Similar names in 1997-2002.** Florida (Biobío) and La Florida (Santiago); San Pedro (near Melipilla)
   and San Pedro de la Paz (created 1995, inside the Concepción unit). The flows look like earlier
   residences assigned to the wrong place. **Possible, not confirmed.** Both stay in the primary analysis.

If so, both inflate out-rates of the named origin, and the first also inflates in-rates of the
receiving municipality. Very small southern units with military, mining or farm workers also have extreme rates,
which may be real.
