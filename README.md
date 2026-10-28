# Forecast seals

This repository holds the seals for a set of model forecasts of two 2026 surveys, the
General Social Survey (GSS) and the Cooperative Election Study (CES), with their
OpenTimestamps proofs and a script, `verify.py`, that checks a seal against the published
forecast rows. It also holds forward seals: predictions of the next published reading of
recurring Gallup, Marquette, Pew, Ipsos and Federal Reserve survey items, each made and
timestamped before that reading was published, and series seals of official statistics:
Census Bureau American Community Survey estimates and eight monthly federal series (sections
below).

Every figure in these forecasts is a model-generated prediction, not a measurement.

## What a seal is

A seal is one sha256 digest over every forecast row made for one survey wave, taken at a
stated moment (`sealed_at`), with counts beside it. The seal file is written once and never
rewritten.

The digest covers seven fields of each row: `prediction_id`, `question_id`, `method_id`,
`cut`, `distribution`, `made_at` and `commit_hash`. Changing any of those fields in any
row, removing a row, or adding a row that claims to have been made before `sealed_at`
changes the digest. Rows made after `sealed_at` fall outside the seal and cannot break it.
`verify.py` counts them separately.

What the digest does not cover:

- a row's status, which changes when the wave resolves;
- its provenance and diagnostics;
- `population_version` (the population frame) and `trained_through` (the last survey wave
  the method learned from).

A seal therefore shows which forecast distributions existed at the time. It does not show
which frame or training cutoff produced them. `code_commit` names the commit of the code
that made the forecasts. That code is in a private repository, so the commit cannot be
checked from outside.

`sealed_at` was written by our own machine, so it is not independent evidence of the date.
The independent date comes from the OpenTimestamps proof beside each seal file, which ties
the file's sha256 to a Bitcoin block.

## What is sealed

2,310 question-by-cut cells sealed (GSS 1,364; CES 946); 2,090 served-model forecasts, each sealed beside its
baselines, made by `ensemble_mean` 0.3.0.

A cell is one survey question for one population cut, such as all adults or adults aged
18-29. Each cell was forecast by two baselines, and 2,090 of them by the served model as well (220 CES cells carry baselines only):
`carry_forward` (the last wave's weighted share) and `demographics_only` (a model with no
time term). The seals also hold the served model's two members, `gbm_pooled` and
`mrp_numpyro`. The service now runs `ensemble_mean` 0.4.0, so today's defaults do not
reproduce the sealed rows.

| Seal file | Survey wave | Items | Served forecasts (`ensemble_mean` 0.3.0) | Baseline rows (each baseline) | Forecasts made | `sealed_at` (UTC) | Digest (`predictions_sha256`) |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `seals/gss-2026.json` | GSS 2026 | 62 | 1,364 | 1,367 | 2026-09-02 and 2026-09-06 | 2026-09-07 17:53:15 | `a90d3004ebd7c584077658e22a42be55a47701a0616c24d384788a64ddba37a6` |
| `seals/ces-2026.json` | CES 2026 | 43 | 726 | 946 | 2026-09-06 | 2026-09-07 17:53:16 | `3456fede015f87ab5b89baba5ef707644d799165dc39d3416df327d77455d202` |

- In GSS, 9 rows are smoke-test rows from the first build on 2026-09-02, covering 3 cells
  with 3 methods each. They were voided on 2026-09-06, when the full forecast replaced them.
  They are sealed like every other row and carry a void status.
- In CES, 220 cells have baseline forecasts but no served forecast.
- Each seal file lists its full per-method counts under `methods`.

### Second set, r2 (sealed 2026-10-06)

On 2026-10-06 the same cells were forecast again by `ensemble_mean` 0.4.0, the model served
today, with the first two errata below fixed (the third, on presidential approval, applies to it too): 2,090 new rows (GSS 1,364; CES 726). Each r2 seal covers
every public row of its wave at its time, so it re-covers the first set unchanged and adds the
new rows; the first seals still verify, and report the new rows as made after them. Both sets
are scored when the waves resolve. Neither replaces the other.

| Seal file | Survey wave | Rows covered | New `ensemble_mean` 0.4.0 rows | `sealed_at` (UTC) | Digest (`predictions_sha256`) |
| --- | --- | --- | --- | --- | --- |
| `seals/gss-2026-r2.json` | GSS 2026 | 8,193 | 1,364 | 2026-10-06 22:42:02 | `ad5efea9d3f50a2bdc8a784a35478696d3e7f9fa41c45f5378d1efb86c296011` |
| `seals/ces-2026-r2.json` | CES 2026 | 4,796 | 726 | 2026-10-06 22:42:06 | `2a9932b6866d1c25994397485ffdffff22df1a37d04f8914d32395edb7a01142` |

## Dating

- **Sealed (by our machine):** 2026-09-07, as `sealed_at` in each file.
- **Independently timestamped:** both seal files are anchored in Bitcoin block 968355, mined
  2026-09-24 04:50:51 UTC (merkle root 3295406e8c595afa1f26eb3f787eb35933a6bf6ad56a7f3dd8c788acfc477eef),
  and again in block 968357 (2026-09-24 04:59:42 UTC). They were submitted to the OpenTimestamps
  calendars on 2026-09-23 at 21:30 US Pacific time (2026-09-24 04:30 UTC). The proofs in `seals/`
  are complete: `ots verify` checks them against a Bitcoin node, and `verify.py` prints the block
  height and merkle root so you can compare them with any block explorer.
- **GSS 2026:** sealed before the data were public. GSS 2026 interviewing ran from April
  through summer 2026 (https://gss.norc.org/faq.html), so these forecasts were made after
  interviewing began. They were sealed and timestamped before any GSS 2026 data were
  released.
- **CES 2026:** independently timestamped 2026-09-24, before the earliest pre-election start in
  any CES Guide since 2018 (09-27). The CES 2026 Guide has not published its own start date yet.
- **The r2 set:** sealed 2026-10-06 and anchored in Bitcoin block 970247, mined 2026-10-06
  23:00:31 UTC. That is after CES 2026 interviewing could have begun, so for r2 the claim for
  both waves is "sealed before the data were public", never "before fieldwork".

## How to verify

You need Python 3.12 (standard library only) and the OpenTimestamps client
(`pip install opentimestamps-client`). For each seal, run two commands:

```
python verify.py seals/gss-2026.json path/to/ledger.json
ots verify seals/gss-2026.json.ots
```

The first command recomputes the digest from the published rows. It prints `ok` or the
first mismatch, plus the number of rows made after `sealed_at`. It accepts `ledger.json`
with its per-wave files in the same folder, a single per-wave file such as
`ledger-gss-2026.json`, or the public event log `public-events.jsonl`.

The second command checks the proof against Bitcoin. According to the client's
documentation, it needs a local Bitcoin Core node (a pruned node is fine). Without one,
`verify.py` prints the block height and merkle root the proof commits to, which you can
compare with that block in a block explorer.

**The row-level check needs the published rows, which are not public yet.** They will be
published with the public ledger page at [LEDGER PAGE URL, pending], as `ledger.json` plus
one file per wave, and archived with a tagged release of this repository. Until then,
`python verify.py seals/gss-2026.json` checks only two things: the structure of the seal
file, and whether the proof beside it commits to that file. It does not check any forecast.

The tests run with `python -m unittest test_verify.py`.

## Errata

Three errata to the 2026 forecasts, dated 2026-09-19 (the first two) and 2026-09-25 (the third), will be published with the ledger
page ([ERRATA URL, pending]). No seal was changed. Each correction sits beside the seal
it concerns, dated, instead of replacing it.

1. **Interval width.** The 80% and 95% intervals on every open 2026 forecast are narrower
   than they should be, by up to about 29%. The cause was a horizon calculation that used a
   one-year gap where the true gap is two years. The predicted shares are not affected. The
   bug was fixed in the served code on 2026-09-15.
2. **A point outside its own interval.** Calibration adjusted some predicted shares without
   moving their bands. 82 label shares at the 80% level (in 66 rows) and 8 at the 95% level
   (in 7 rows) lie outside the band published beside them. For `ensemble_mean`, that is 14
   labels at 80% and 4 at 95%. The largest gap is 1.7 percentage points. The shares are what
   will be scored. The bug was fixed in the served code on 2026-09-16.

3. **Presidential approval follows the previous president.** The CES item asks about the
   sitting president. Every sealed forecast of it was trained through CES 2024, which asked
   about Biden, for a 2026 wave that asks about Trump. Across the one earlier change of
   president (CES 2022 predicted from 2018 and 2020), forecasts for groups missed the share
   strongly disapproving by 13.3 points on average and 59.1 at worst, while all adults missed
   by 2.9. These rows are scored as made.

The sealed rows keep the first two defects. Their scores will be published with these errata beside
them.


## Forward seal: Gallup, October 2026

`seals/gallup-2026-10-seal.json` holds predictions for three items Gallup asks every October:
legalizing marijuana, the death penalty for murder, and fear of walking alone at night near home.
National total only; Gallup's age bands cannot be built from our decade bands. It was made
2026-09-24 13:13 UTC, before Gallup fields the 2026 wave, and stamped with OpenTimestamps
(`seals/gallup-2026-10-seal.json.ots`, Bitcoin block 968402, 2026-09-24 14:36:13 UTC). The file
states in advance the differences in mode and wording from the GSS items the model learned
from, the expected house effect, and two baselines it will be scored against: repeating the
last GSS wave (2024) and Gallup's own October 2025 reading. It is scored when Gallup publishes;
in 2024 and 2025 these items came out on 10-29 and 10-30.

Check it with `shasum -a 256 seals/gallup-2026-10-seal.json`
(db8c86dbebfb0124b7558ad2ff8e0a0aaf4a456519b722a2d42cb6e198413944) and `ots verify
seals/gallup-2026-10-seal.json.ots`. `verify.py` covers the ledger seals only.

## Forward seal: Marquette Law School national poll, next wave

`seals/marquette-national-2026-11-seal.json` holds predictions for one item that Marquette asks on
every national wave: "Generally speaking, would you say that most people can be trusted, or most
people can't be trusted?" It covers the national total and 12 crosstab groups: sex, age 18-29,
five education levels and four race and ethnicity groups. The model learns from the GSS, whose
version of the question reads about 20 points lower, so each prediction is the model's share plus
one offset learned from Marquette's published history (32 waves, Sept 2021 to Sept 2026). The
seal file holds that history, the offset, an out-of-time test of the recipe on every past wave,
and two baselines it will be scored against: Marquette's last wave (fielded Sept 2-9 2026) and
its 32-wave average. It also states in advance that the test tied the first baseline on the
groups and lost to the second.

The predictions were made 2026-10-23 17:07 UTC and stamped with OpenTimestamps
(`seals/marquette-national-2026-11-seal.json.ots`, Bitcoin block 972804, 2026-10-23 17:18:21 UTC).
They are scored on the first national adult wave Marquette releases after that block. The claim is
"sealed before fieldwork" only if that wave's published fieldwork start is later than the block
time; otherwise it is "sealed before publication".

Check it with `shasum -a 256 seals/marquette-national-2026-11-seal.json`
(5ae9d2d820b6918b70f4891dee15d6c87fffce9590c618a3b4d6811d61d5bc3d) and `ots verify
seals/marquette-national-2026-11-seal.json.ots`.

## Forward seal: Gallup November 2026, physical health

`seals/gallup-health-2026-11-seal.json` holds predictions for Gallup's November Health and Healthcare item: "How would you describe your own physical health at this time? Would you say your physical health is -- excellent, good, only fair, or poor?" It covers the national total, men, women and some college, plus White adults, which are reported but left out of the group mean because Gallup's White mapping is inferred. Each prediction is the model's share of "excellent or good" plus one offset learned from Gallup's own 2019-2025 readings. The file states the expected result in advance: a tie with repeating Gallup's last reading on the total, and a likely miss on women.

The predictions were made 2026-10-26 22:08 UTC and stamped with OpenTimestamps (`seals/gallup-health-2026-11-seal.json.ots`, Bitcoin block 973299, 2026-10-26 22:15:57 UTC). Gallup has started this survey in early November every year since 2018.

Check it with `shasum -a 256 seals/gallup-health-2026-11-seal.json`
(5ef347dc0087992034227d860495ec8fb9b7d09b9c3d8d26ee44953bafda8493) and `ots verify
seals/gallup-health-2026-11-seal.json.ots`.

## Forward seals: seven survey readings, sealed 2026-10-27

Seven seal files, each holding predictions for the next published reading of one recurring survey
item. Each prediction is the model's share plus one offset learned from that survey's own published
history, the same recipe as the Marquette and Gallup health seals. Each file holds the item's
wording, the history it learned from, an out-of-time test of the recipe on every past wave, and two
baselines it will be scored against: repeating the survey's last reading, and the average of its
earlier readings. All figures are percentages of U.S. adults.

| Seal file | Survey and item | Cells | Forecast, total (80% band) | Repeat last reading | Average of earlier readings | Expected release (our estimate) | Digest (sha256 of the file) |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `seals/pew-trust-scientists-2026-seal.json` | Pew Research Center: confidence in scientists to act in the public's best interests, a great deal or a fair amount | 4 | 76.26 (70.46-82.06) | 77 (Oct 2025) | 79.55 (11 waves) | 2026-11-12 or later | `5948b75430338f0324a39ecc8505d16e3e2f90b9e084b52d2c21227d3d47c0e4` |
| `seals/ipsos-happiness-2027-seal.json` | Ipsos Happiness Index 2027: very or rather happy | 1 | 70.82 (62.55-79.09) | 73 (Jan 2026) | 82.32 (47 readings) | ~2027-03-15 | `6d5f4b2a054dc89716a65a7ae15a5de85642585141df9115c0a5e2f8cc12297c` |
| `seals/fed-shed-2026-seal.json` | Federal Reserve SHED 2026: much or somewhat worse off than 12 months ago | 8 | 33.76 (25.15-42.37) | 28 (2025) | 22.17 (12 waves) | ~2027-05-19 | `f5425c9c0ebe07bf7a9e5d2689e2668a721b917f06141f2a4dbbb2f0d35df9fc` |
| `seals/gallup-income-tax-2027-seal.json` | Gallup March 2027: federal income tax too high | 5 | 63.57 (57.43-69.71) | 59 (Mar 2026) | 55.38 (53 readings) | ~2027-04-09 | `d72bc4626dd097868f9e197ed263e8b9e8ec281af7d8a5b087121084fa5df40c` |
| `seals/gallup-finances-better-2027-seal.json` | Gallup April 2027: personal financial situation getting better | 5 | 34.59 (22.54-46.64) | 34 (Apr 2026) | 46.26 (43 readings) | ~2027-04-28 | `089d2e571603e279a9093c93a568e923483523d1bd34e11b901c620dc5a1af2e` |
| `seals/gallup-moral-acceptability-2027-seal.json` | Gallup May 2027: sex between an unmarried man and woman morally acceptable | 5 | 69.98 (64.22-75.74) | 65 (May 2026) | 64.0 (26 readings) | ~2027-06-10 | `9997e2dd4a644f83d8a4b2315bf06c4538d412f981bb28ef642b522fec6fbfa0` |
| `seals/gallup-confidence-institutions-2027-seal.json` | Gallup June 2027: confidence in the medical system, a great deal or quite a lot | 7 | 29.87 (21.84-37.90) | 28 (Jun 2026) | 38.12 (34 readings) | ~2027-07-13 | `ee406e98c6b3dfba146446eeaab9fe1ce5227bf1d6d081c7b08ca4f2c6d1d1ff` |

The predictions were made between 2026-10-27 00:14 and 01:00 UTC and stamped with
OpenTimestamps. All seven proofs are anchored in Bitcoin block 973320, mined 2026-10-27 01:18:59
UTC. Cells beyond the total are the groups each survey publishes that the model's population frame
can build; each file lists the groups it leaves out and why. Each file also states its void rules:
a seal is void if the item is not asked, is reworded, is published before the block time, or is not
published by the file's `void_after` date.

The claim for Pew and the Federal Reserve is "sealed before publication": their fieldwork may have
begun before the block. For the five others it is "sealed before fieldwork", which holds only if
the published fieldwork start is later than the block time.

Check each with `shasum -a 256 seals/<file>` against the digest above and `ots verify
seals/<file>.ots`.

## Series seal: ACS 2025 1-year estimates, sealed 2026-10-27

One seal file holding forecasts of six headline indicators from the Census Bureau's American
Community Survey 2025 1-year estimates, for every state, DC and the US (52 geographies, 312
cells). Each indicator's method was chosen by a rule stated in the file before sealing: serve the
method with the lowest out-of-time error over past years, or the ensemble where its gap to that
method cannot be told from zero, and do not seal an indicator where repeating last year's value
wins. Two indicators failed that test and are not sealed: the uninsured rate and work from home.
Each forecast will be scored by absolute error against the value Census first publishes, beside
two baselines: repeating the 2024 value (`random_walk`) and a straight-line trend (`drift`).

| Indicator | US 2024 | US forecast, 2025 (80% band) | Method served |
| --- | --- | --- | --- |
| Households with a broadband subscription, % | 93.2 | 93.97 (93.31-94.64) | `ensemble_mean` |
| Median household income, nominal $ | 81,604 | 85,098 (82,199-88,100) | `drift` |
| People below the poverty level, % | 12.1 | 11.97 (11.40-12.54) | `ensemble_mean` |
| Adults 25+ with a bachelor's degree or higher, % | 36.8 | 37.22 (36.84-37.60) | `ensemble_mean` |
| Population born outside the US, % | 14.8 | 14.90 (14.46-15.34) | `ensemble_mean` |
| Median gross rent, nominal $ | 1,487 | 1,558 (1,460-1,662) | `drift` |

| Seal file | Release (announced by Census) | Digest (sha256 of the file) |
| --- | --- | --- |
| `seals/acs-2025-seal.json` | 2026-10-29 | `f06878108f0101d5c7781202df647daf07afbd7a535775765551bbbc989e216f` |

The forecasts were sealed at 2026-10-27 21:18 UTC and the proof is anchored in Bitcoin block
973461, mined 2026-10-27 21:27:06 UTC, two days before the release. The claim is "sealed before
publication"; the file states that the seal is void if the block time is on or after the release.
The file also lists its caveats, including the October-November 2025 federal shutdown during
collection and the 2024 change to the contract-rent cap.

Check it with `shasum -a 256 seals/acs-2025-seal.json` against the digest above and `ots verify
seals/acs-2025-seal.json.ots`.

## Series seals: eight official statistics, sealed 2026-10-28

Eight seal files, each a forecast of the next first print of one official statistic, made from
the publisher's own series and nothing else. Each target's method was chosen by a rule stated in
its spec before any result: serve the method with the lowest out-of-time error over past
releases, or the ensemble where its gap to that method cannot be told from zero, and do not seal
a target where repeating the last value wins. The unemployment rate, the egg price and the
personal saving rate failed that test and are not sealed. Every forecast is one step ahead: no
new print of any of these series is due between the seal and its release. Each will be scored
by absolute error against the first print, beside the methods it beat.

| Seal file | Series and period | Last value | Forecast (80% band) | Method served | Release | Digest (sha256 of the file) |
| --- | --- | --- | --- | --- | --- | --- |
| `seals/bls-payrolls-2026-10-seal.json` | All employees, total nonfarm (PAYEMS, U.S. Bureau of Labor Statistics), 2026-10; thousands of persons | 159,044 (2026-09) | 159,144.1 (158,918.6-159,369.9) | `drift` | 2026-11-06 (announced) | `1c294b5818b4296b978bb2f7795ada80b5426fe875fdace93115b65c7dcd870b` |
| `seals/bls-cpi-2026-10-seal.json` | Consumer Price Index for All Urban Consumers: all items in U.S. city average (CPIAUCSL, U.S. Bureau of Labor Statistics), 2026-10; index 1982-1984=100 | 336.298 (2026-09) | 337.1918 (336.0211-338.3666) | `ets` | 2026-11-10 (announced) | `c311004376047811fb1daeb053dedb3f409e86abfd973811aa82f7151c7fb22c` |
| `seals/bls-cpi-admissions-2026-10-seal.json` | CPI-U: admission to movies, theaters, and concerts in U.S. city average (CUUR0000SS62031, U.S. Bureau of Labor Statistics), 2026-10; index December 1997=100 | 238.383 (2026-09) | 238.8877 (236.7282-241.0669) | `drift` | 2026-11-10 (announced) | `ea9697abbbc2328757d6afe3d2fec92c619984911f917650cae263e3daa31773` |
| `seals/bls-electricity-price-2026-10-seal.json` | Average price: electricity per kilowatt-hour in U.S. city average (APU000072610, U.S. Bureau of Labor Statistics), 2026-10; U.S. dollars per kilowatt-hour | 0.196 (2026-09) | 0.1941 (0.1882-0.2001) | `ensemble_mean` | 2026-11-10 (announced) | `e7c5ca05466c3dd91353f1a73d506dba8f44c9a156c3f444187324e7c059cdbc` |
| `seals/census-retail-sales-2026-10-seal.json` | Advance retail sales: retail trade and food services (RSAFS, U.S. Census Bureau), 2026-10; millions of dollars (not adjusted for prices) | 745,021 (2026-09) | 746,271.1 (736,342.4-756,333.6) | `ensemble_mean` | 2026-11-17 (announced) | `c9b9a1940b0a18e7303078f439286423d6ef0d237e81b443de61b1c2838c1d15` |
| `seals/census-housing-starts-2026-10-seal.json` | New privately-owned housing units started: total units (HOUST, U.S. Census Bureau (with HUD)), 2026-10; thousands of units, seasonally adjusted annual rate | 1,221 (2026-09) | 1,265.2 (1,149.2-1,393.0) | `ets` | 2026-11-18 (announced) | `e8348ac194ca82b10623a346983619ae515e0ffedd657afa02099c68960b19d5` |
| `seals/nchs-overdose-deaths-2026-06-seal.json` | Provisional drug overdose deaths, 12-month-ending, United States (predicted value, adjusted for reporting delays) (xkb8-kh2a:US:predicted_value, CDC National Center for Health Statistics), 2026-06; deaths in the 12 months ending in the period | 66,478 (2026-05) | 65,780.9 (65,202.3-66,364.7) | `ets` | 2026-11-18 (inferred) | `db2dff0a7c6824080f60335cb409b7374ec02bbce6654737cd2ab068d08ce302` |
| `seals/census-new-home-sales-2026-10-seal.json` | New one-family houses sold: United States (HSN1F, U.S. Census Bureau (with HUD)), 2026-10; thousands, seasonally adjusted annual rate | 676 (2026-09) | 675.6 (604.1-755.5) | `ensemble_mean` | 2026-11-25 (announced) | `444afec380a24761f8ca2b3ebae303e2a8071257767ca1ef55bb9512c6e67c32` |

The forecasts were sealed between 2026-10-28 21:17:08 and 21:17:14 UTC and stamped with
OpenTimestamps. All eight proofs are anchored in Bitcoin block 973603, mined 2026-10-28 22:05:29
UTC, eight days before the first of these releases. The claim for each is "sealed before
publication", and each file states that its seal is void if the block time is on or after the
release. The overdose release date is our inference from NCHS's monthly cadence, not an announced
date. The other seven are announced. Each file states its scoring plan: the first print, read
from the publisher's series on release day, scored by absolute error for the served method and
for every other method it was chosen over, including repeating the last value.

Check each with `shasum -a 256 seals/<file>` against the digest above and `ots verify
seals/<file>.ots`.

## When the waves resolve

We expect GSS 2026 and CES 2026 data to be released in spring 2027. That is our own
estimate, not a date either survey has announced. When a wave's data are released, every
sealed forecast for that wave will be scored against the data and the scores will be
published, misses included.

## Licence

`verify.py` is released under the MIT licence (`LICENSE-verify.txt`). The seal files and
their `.ots` proofs are published as records. No licence is granted for them or for any
other file in this repository.
