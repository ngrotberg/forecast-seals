# Sample reports

Two free sample reports and the catalog of items a report can forecast, prepared by Nate
Grotberg. Every figure in them is a model-generated prediction, not a measurement. Never
describe one as a poll or a survey result.

| Folder | What it forecasts | Next waves |
|---|---|---|
| `health/` | Uninsured adults and disability (NHIS: the nation, its regions and 21 national groups), and adults who could not see a doctor because of cost (BRFSS: every state and DC, and the groups) | NHIS 2026, BRFSS 2026 |
| `household-finance/` | Covering a $400 emergency with cash or its equivalent (SHED), household SNAP receipt and poverty (CPS ASEC): every state and DC, and the groups | SHED 2026, CPS ASEC 2027 |
| `catalog.pdf` | The federal survey items a report can forecast, by source, with the waves on hand | |

Each report folder holds `report.pdf` (the report), `states.csv` and `groups.csv` (every
printed figure, with its 80% and 95% intervals and the last measured share), and the seal
files: `seal-<source>.json` over every forecast row behind the report, `raw-seal-<source>.json`
over each row's raw distribution, and an OpenTimestamps proof (`.ots`) beside each.

## Checking a sample's seal

```
python verify.py samples/health/seal-nhis.json
```

That checks the seal file's structure and its proof, and with `--online` the Bitcoin block
header behind the proof. A seal holds a digest, not the rows: the forecast rows behind a sample
are not published here, so the seal dates the forecasts but a reader cannot yet recompute it.
The sample forecasts are separate from the survey-wave seals in `seals/`, which cover the
engine's whole forecast of each wave, and `verify.py --all` reads `seals/` only, not these
samples.

`verify.py` checks the `seal-<source>.json` files only. The `raw-seal-<source>.json` files use
a different format (`raw-supplement-1`) that it does not read and reports as malformed; check
their proofs with the OpenTimestamps client instead (`ots verify raw-seal-nhis.json.ots`).

## Using a figure

In public, with the label "model-generated prediction, not a measurement" and the report's
citation line on every use. Never in paid political ads or candidate campaign material.

## Data sources

The forecasts are built from public-use data of the National Center for Health Statistics, the
Centers for Disease Control and Prevention, the Federal Reserve Board, the Census Bureau and the
Bureau of Labor Statistics, each cited in full in its report. The forecasts, analyses and
conclusions are the author's alone; the agencies are responsible only for the source data, and
their use here implies no endorsement by any of them or by the U.S. Government. The public-use
data are available at no charge from each agency's website.
