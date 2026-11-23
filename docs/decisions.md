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
| 12 | 2026-11-23 | Treat boundary coordinates as EPSG:32719 | docs/boundaries.md | Proposed |

## Open questions

- Denominators for in- and out-rates (docs/chim_interpretation.md).
- FUA conglomerates, small cities, displaced units (docs/boundaries.md).
- Step 3 findings and open questions are in docs/chim_interpretation.md.
- CHIM covers ages 5+ resident in Chile at both dates; its exclusions are not documented.
- No explicit licence found for the CHIM data.
