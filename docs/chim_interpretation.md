# Interpreting the CHIM migration data

Method only. Numerical findings derived from CHIM are kept locally (decision 7).

## Meaning of a record

A row says: *this many people lived in B five years ago and live in A now*. If A = B they
are "stayers". Two dates are compared, so the data does not see moves in between, people who
left and returned (counted as stayers), moves inside a municipality, children under 5, people
who died or emigrated, or arrivals from abroad. These are **migrants**, not migration events.

## Flow direction (agreed)

**Origin = `tm5ymun`. Destination = `tmhabmun`.**

Tested with documentation (populations at risk are origin totals), census-date populations,
growth between censuses, and regional balances published separately by INE. Variable names
were not relied on. `src/validate_raw.py` repeats every test.

## Toy matrix (invented numbers)

| Lived here 5 years ago | Now A | Now B | Now C | Row sum |
|---|---|---|---|---|
| A | **90** | 8 | 2 | 100 |
| B | 5 | **40** | 5 | 50 |
| C | 10 | 0 | **20** | 30 |
| Column sum | 105 | 48 | 27 | 180 |

Diagonal: stayers. Departures = row sum - diagonal (A: 10). Arrivals = column sum - diagonal
(A: 15). Total departures always equal total arrivals (30).

## Municipality codes (agreed)

The flow files contain labels but no codes. Codes are assigned **by matrix position**, using
metadata code order. Labels are never used to join, because a run of 1992 labels is attached
to the wrong municipalities: read by label, resident counts are implausible against census
populations; read by position, they are plausible in all three years. This corrects our
interpretation. The raw files are unchanged.

Both matrix axes shift together, so row sums, column sums and totals still balance. Only a
comparison with data from outside the matrix reveals the error.

Safeguards in `src/chim.py`, run on every read: 304 unique codes; matrix dimensions and regular
row order; pinned SHA-256 of the code sequence and of each year's label sequence; population
files equal origin totals; resident/census ratios within bounds (tests). The original labels
are written beside the assigned codes to `reports/local/label_audit_{year}.csv`.

## Denominators: the candidates

| Candidate | What it counts | Out-migration | In-migration |
|---|---|---|---|
| Row sum (CHIM population file) | Later-enumerated people who lived there at the start | Natural: everyone who could have left; rate at most 1 | Not the group arrivals come from; can exceed 1 where few lived before |
| Column sum | People counted there at the end | Mixes in arrivals who were never at risk of leaving | Share of current residents who arrived; at most 1 |
| Mean of both | Average of start and end | Compromise | Compromise; same base for both rates |
| Census population | Everyone, all ages | Includes under-5s and unknown origins, who cannot be in the numerator | Same; bias varies with age structure |

Lerch, Du and Beckendorff (2026) divide departures "by the sending population" and arrivals
"by the destination population" without stating a date. Their appendix describes a "population
at risk (average, over 5 years before last census)", which suggests a period average, but the
exact construction is not given. The choice made is in docs/measures.md.
