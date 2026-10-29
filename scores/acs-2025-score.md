# ACS 2025 1-year estimates: eight headline indicators for every state, DC and the US: score

Sealed 2026-10-27T21:18:20Z; attested 2026-10-27T21:27:06Z (Bitcoin block 973,461); release 2026-10-29T04:00:00Z. Model-generated prediction, not a measurement.

Scored against the first print read by the primary route: the 2025 table-based summary file (acsdt1y2025-<table>.dat) fetched on or after 2026-10-29, lines mapped by label from ACS20251YR_Table_Shells.txt, computed and rounded exactly as the history. 7 files, each with its URL, retrieval time, bytes and sha256 in score.json.

Errors are absolute, in each indicator's units. The served method is the headline; repeating 2024 (`random_walk`) and the straight-line trend (`drift`) are the baselines. State figures are means over the 51 states (DC included); the US is scored on its own.

| indicator | served | US forecast (80% band) | US first print | US error | US error, repeat 2024 | US error, drift | 51-state mean error: served / repeat 2024 / drift | states inside the served 80% band |
|---|---|---|---|---|---|---|---|---|
| Percent of households with a broadband Internet subscription | `ensemble_mean` | 93.97 (93.31 to 94.64) | 94.0 | 0.03 | 0.80 | 0.68 | 0.45 / 0.85 / 0.81 | 46 of 51 |
| Median household income (dollars of the survey year) | `drift` | 85,098 (82,199 to 88,100) | 84,780 | 318 | 3,176 | 318 | 1,542 / 3,165 / 1,542 | 49 of 51 |
| Percent of people below the poverty level | `ensemble_mean` | 11.97 (11.40 to 12.54) | 11.8 | 0.17 | 0.30 | 0.04 | 0.52 / 0.58 / 0.51 | 44 of 51 |
| Percent of people 25 and over with a bachelor's degree or higher | `ensemble_mean` | 37.22 (36.84 to 37.60) | 37.4 | 0.18 | 0.60 | 0.07 | 0.58 / 0.68 / 0.60 | 40 of 51 |
| Percent of the population born outside the United States | `ensemble_mean` | 14.90 (14.46 to 15.34) | 14.7 | 0.20 | 0.10 | 0.25 | 0.32 / 0.32 / 0.34 | 45 of 51 |
| Median gross rent (dollars of the survey year) | `drift` | 1,558 (1,460 to 1,662) | 1,557 | 1 | 70 | 1 | 37 / 71 / 37 | 51 of 51 |

On the 51-state mean error the served forecast was closer than repeating 2024 on 6 of 6 indicators and closer than drift on 3 of 4 (an indicator served by that baseline is not compared with it).

Rounding: shares in percent to one decimal and medians in whole dollars, rounded half away from zero, as the data profiles print them.
Not sealed, so not scored: uninsured, work_from_home.
