# Municipal boundary changes of 1979

This supports a **historical-boundary sensitivity**. It is **not a reconstruction of exact 1977
boundaries**: whole municipalities are grouped, while the decree moved parts of them.

Method and legal evidence only. Numbers derived from CHIM are kept locally (decision 7).

## Source

Decreto Ley 2868, signed 21 September and published 26 October 1979, "Divide las provincias que
señala del país en las comunas que indica", Biblioteca del Congreso Nacional,
https://www.bcn.cl/leychile/Navegar?idNorma=7020. Local copy `data/raw/reference/DL-2868-1979.xml`,
SHA-256 `33a97fba485ba75976b55307a5f9875f13ce84ac4be54bc03215e2257edcb8ca`.

**Version caveat.** The consolidated text was read. Its articles carry a version date of June 1988,
and the original 1979 version could not be retrieved. The passages describe transfers from
"la actual comuna" and cite Decreto Ley 2867 of 1979, which fits 1979, but a later amendment of a
passage cannot be excluded.

The 1982 census asked about residence in 1977, before the decree. People living in transferred
territory may have named the municipality it belonged to in 1977 without having moved. The decree
proves the transfer of territory. That respondents answered this way is inferred.

## The eight pairs

| Flow 1977-82 | Article | Territory moved from the first to the second | Class |
|---|---|---|---|
| Saavedra to Teodoro Schmidt | 33, no. 15 d-g; no. 16 a, c | District 9 Puculón; parts of 7 Puerto Domínguez, 8 Molco, 10 Chelle | Confirmed |
| Saavedra to Carahue | 33, no. 17 d-e; no. 16 a-b | Districts 2 Nehuentúe, 3 Trovolhue, 4 Yupehue, 5 Pellahuén (part elsewhere); parts of 7, 8 | Confirmed |
| Nueva Imperial to Teodoro Schmidt | 33, no. 15 b-c; no. 18 a-b | District 12 Huilío; part of 11 Nohualhue | Confirmed |
| Maullín to Los Muermos | 36, no. 6 a-c; no. 5 b-d | District 3 Cululil; parts of 2 Quenuir, 4 Lolcura | Confirmed |
| Fresia to Los Muermos | 36, no. 6 d; no. 7 | Part of district 5 Río Frío | Confirmed |
| Freire to Cunco | 33, no. 5 c-e; no. 10 b-c | District 8 Los Laureles; parts of 7 Maile, 9 Longlong, 10 Colico, 11 Huilipilún | Confirmed |
| Queilén to Quellón | 37, no. 10 b; no. 9 | Districts 4 Chadmo, 5 Compu | Confirmed |
| Quinchao to Dalcahue | 37, no. 3 c; no. 6 | Districts 7 Mechuque, 8 Buta Chauques, 9 Tac, from Achao (Quinchao) to **Quemchi** | Confirmed, **indirect** |

"Confirmed" means the decree moves territory between those municipalities in that direction. It does not
mean every recorded move is false: some are real. No pair is left as plausible or unexplained.

**Dalcahue + Quinchao is indirect.** The territory went to Quemchi, not Dalcahue. Dalcahue municipality received nothing from Quinchao and gave Tenaún to
Quemchi. CHIM's broader Dalcahue unit also contains Quemchi (checked against a 2020 map), so the transfer
crosses the same CHIM boundary.

Asymmetric 1982 flows **without** a matching transfer, for example Sierra Gorda to Antofagasta, are not
grouped. The decree also moved territory between many other municipalities. The eight pairs
were the ones first noticed in the flows, so the scenario does not remove every possible effect.

## Teodoro Schmidt

| Date | Event |
|---|---|
| 26 October 1979 | Commune created: DL 2868 published (signed 21 September). It composes the commune from districts of Toltén, Nueva Imperial and Saavedra |
| 15 October 1980 | Municipal administration established: DFL 1-2868 of 1980 published |
| 12 January 1981 | Municipality formally installed (Resolución 5, Gobernación de Cautín) |

The 1980 and 1981 dates are as given by the municipality
(https://muniteodoro.cl/portal/comuna/); those instruments were not read. Some sources give other
days for the 1979-80 acts. A 1967 record is reported to be a legislative proposal; it is not evidence of
legal creation.

## Sensitivity scenario `historical_boundaries`

Municipalities linked by the pairs are grouped, directly or through one another:

1. Carahue + Nueva Imperial + Saavedra + Teodoro Schmidt
2. Fresia + Los Muermos + Maullín
3. Cunco + Freire
4. Dalcahue + Quinchao (**indirect**, through Quemchi)
5. Queilén + Quellón

All were rural in the primary geography, and each group is one rural settlement (`H...`) in all three
periods. Moves inside a group are no longer migration. Some pairs inside a group have no transfer of
their own among the eight (Fresia and Maullín); they are joined because both gave land
to the same municipality.

Limits: real moves inside the groups disappear too, in every period; groups are larger and vary
less, which lowers rural rates mechanically; densities and ranks change.

The primary geography and rates are unchanged.
