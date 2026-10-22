# Forecast seals

This repository holds the seals for a set of model forecasts of two 2026 surveys, the
General Social Survey (GSS) and the Cooperative Election Study (CES), with their
OpenTimestamps proofs and a script, `verify.py`, that checks a seal against the published
forecast rows.

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

## When the waves resolve

We expect GSS 2026 and CES 2026 data to be released in spring 2027. That is our own
estimate, not a date either survey has announced. When a wave's data are released, every
sealed forecast for that wave will be scored against the data and the scores will be
published, misses included.

## Licence

`verify.py` is released under the MIT licence (`LICENSE-verify.txt`). The seal files and
their `.ots` proofs are published as records. No licence is granted for them or for any
other file in this repository.
