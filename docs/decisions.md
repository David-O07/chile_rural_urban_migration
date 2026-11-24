# Decision log

| # | Date | Decision | Reason | Status |
|---|---|---|---|---|
| 1 | 2026-11-23 | Study Chile with CHIM | In the paper's sample; three harmonized periods | Agreed |
| 2 | 2026-11-23 | Keep 2017 and 2024 censuses out of the core | Extra crosswalks; 2019-24 spans COVID | Agreed as part of Phase 1 scope |
| 3 | 2026-11-23 | Use GHS-POP R2019A, not R2023A | The FUA file was derived from R2019A | Agreed |
| 4 | 2026-11-23 | Extract only the three `overall` matrices from CHIM | Age, sex and occupation splits are outside the research question | Agreed |
| 5 | 2026-11-23 | Add modelling packages only in Phase 4 | Not needed yet | Proposed |
| 6 | 2026-11-23 | Keep the original CHIM archive locally | Published link is dead; the Box copy could disappear | Agreed |
| 7 | 2026-11-23 | Do not publish or redistribute CHIM data or derived flow tables | No data licence found | Agreed, until resolved |
| 8 | 2026-11-23 | Assign municipality codes by matrix position (metadata order), never by label | Some 1992 labels are attached to the wrong municipality | Agreed |
| 9 | 2026-11-23 | Metadata codes for all joins; metadata names for display only | Flow and boundary names are damaged | Agreed |
| 10 | 2026-11-23 | Origin = `tm5ymun`, destination = `tmhabmun` | docs/chim_interpretation.md | Agreed |
| 11 | 2026-11-23 | Keep CHIM-derived numerical reports in `reports/local/` (not committed) | Licence unresolved | Agreed |
| 12 | 2026-11-23 | Assign EPSG:32719 and repair invalid geometries, in memory only | docs/boundaries.md | Agreed |
| 13 | 2026-11-23 | Exclude Antártica from the main analysis | Tiny, displaced, no usable geometry | Agreed |
| 14 | 2026-11-23 | Never use inset geometries for area, density or neighbours; keep Isla de Pascua and Juan Fernández out of neighbour models unless restored | False positions | Agreed |
| 15 | 2026-11-23 | FUA rule: at least 50% of population; 40% and 60% as sensitivity checks | Paper's rule | Agreed |
| 16 | 2026-11-23 | La Cruz to Quillota; Quillota + La Calera merged as a sensitivity check | 50% rule | Agreed |
| 17 | 2026-11-23 | Our classification is not equivalent to the paper's: units come from CHIM, not IPUMS | Different geography | Agreed |
| 18 | 2026-11-23 | Acquire GHS-SMOD R2019A V2.0, epoch 2015 | Small-city definition | Agreed |
| 19 | 2026-11-23 | Merge the Concepción and Chiguayante FUAs; sensitivity: separate, and Hualqui unmatched | Keeps a centre and its commuter belt together; a departure from the published algorithm | Agreed |
| 20 | 2026-11-23 | Small cities: GHS-SMOD class 30 only (replaces 30 + 23). Main sensitivity: 30 + 23. Broad: 30 + 23 + 22 | 30 + 23 gave far more small cities than the paper reports | Agreed |
| 21 | 2026-11-23 | Keep Isla de Pascua and Juan Fernández in the migration data; unclassified, unranked, not in neighbour models, no area or density assigned; sensitivity: without them | Flows complete, geometry not usable | Agreed |
| 22 | 2026-11-23 | Primary neighbour models use queen contiguity between settlements; units with no neighbour (Puqueldón, Guaitecas) leave them but stay in non-spatial analysis | A unit without neighbours has no spatial lag | Agreed |
| 23 | 2026-11-23 | Rank by period-specific average population; normalize within period; origin- and destination-population ranks as sensitivity (docs/measures.md) | One consistent base for the interval | Agreed |
| 24 | 2026-11-23 | Out-migration denominator: origin population. In-migration: average population. Sensitivity: average for out, destination population for in | docs/measures.md | Agreed |
| 25 | 2026-11-23 | Five-year rates; not annualized | Match the question asked in the census | Agreed |

## Open questions

- Area and classification of the two displaced islands.
- Nearest-neighbour sensitivity for Phase 4 (docs/geography.md).
- Step 3 findings and open questions are in docs/chim_interpretation.md.
- CHIM covers ages 5+ resident in Chile at both dates; its exclusions are not documented.
- No explicit licence found for the CHIM data.
