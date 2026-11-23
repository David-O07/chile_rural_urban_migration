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

## Open questions

- CHIM boundary file declares a Swiss CRS (CH1903). Not yet verified (Step 4).
- CHIM place names have inconsistent accents, so names may not be safe join keys (Step 5).
- CHIM totals are below the census population. They cover ages 5+, living in Chile at
  both dates. How many people were dropped for unknown previous residence is not stated.
- No explicit licence found for the CHIM data.
