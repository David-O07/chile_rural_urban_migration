# Ranking and rates

Agreed definitions (decisions 23-25). **Not implemented yet: no rank or rate has been computed.**
All quantities are per settlement and per period, from the aggregated flow matrix.

## Populations

- **Origin population** P0: row sum. People counted who lived there five years earlier.
- **Destination population** P1: column sum. People counted who live there at the census.
- **Average population** P = (P0 + P1) / 2.

The average is an **approximation** of the population during the five years. It assumes steady
change between the two dates, covers only people aged 5+ at the census who lived in Chile at both
dates, and is not person-years of exposure.

Toy (docs/chim_interpretation.md): A has P0 = 100, P1 = 105, P = 102.5.

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

## Consequences to keep in mind

- The primary out- and in-rates have **different denominators**, so their difference is not a net
  migration rate. The average-denominator versions share one base and can be compared.
- departures / P0 and arrivals / P1 cannot exceed 100%. arrivals / P can (at most 200%).
- Population enters both the denominator and the rank, so some correlation between rate and
  position is built in. The alternative ranks and denominators show how much it matters.
- Rates are conditional on survival, presence in Chile and a known previous residence.
- The paper gives no formula. A related paper by the same group (Beckendorff et al. 2026,
  https://doi.org/10.1186/s40878-026-00535-6) uses the population five years earlier for
  out-migration. Our in-migration denominator is our own choice.
