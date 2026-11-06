# FraudShield

Read the [project blog](docs/blog.md), [card model card](models/ulb-card/README.md), [synthetic BAF model card](models/baf-account-opening/README.md) and [publication layout](docs/publication.md). This source repository excludes raw data and binary trained models. Obtain compatible model artifacts separately or retrain. The full generated dashboard evidence is in the complete delivery archive; regenerate it with `python run.py train` for a fresh checkout.

Published on LinkedIn: [FraudShield: finding the trade-off between fraud capture and customer friction](https://www.linkedin.com/pulse/fraudshield-finding-trade-off-between-fraud-capture-charan-tej-xu6rf).

An executable card fraud research engine with eight model families, a stakeholder dashboard, local inference, and reproducible reports. Built on real anonymized ULB / Worldline data, with no invented transactions or benchmark scores.

The assurance extension adds a **separate synthetic eight-month BAF account-opening study**, age-group audits, named-feature TreeSHAP examples, label-maturity/bank-data validation, protocol comparison guards, observed financial accounting and a local research review history. It does not convert the 2013 card study into evidence for current Indian payments. See [the eight-limit response](docs/assurance_design.md), [bank data contract](docs/bank_data_contract.md), and [dataset attribution and permissions](DATA_ATTRIBUTION.md).

## Run

This build was measured with Python 3.14.7. Use the exact versions in `requirements-lock.txt` with the bundled trained artifacts. On a different Python or library version, retrain rather than loading serialized models created with an incompatible environment. Exact measured versions are also in `artifacts/run.json` and the dashboard.

```powershell
python -m pip install -r requirements-lock.txt
python run.py download
python run.py train
python run.py serve
```

Open http://127.0.0.1:8765. If `data/creditcard.csv` already exists, skip download: the downloader refuses to overwrite it. An official TensorFlow tutorial hosts the public mirror used here. Download it manually if your Python runtime cannot reach the network: https://storage.googleapis.com/download.tensorflow.org/data/creditcard.csv

This checkout has optional LightGBM and XGBoost wheels installed in `.vendor`; `run.py` adds that directory to the import path. A fresh installation should use `requirements.txt`. Missing optional tree libraries are logged and skipped; the dashboard reflects only the models actually evaluated. The first measured run contains all eight families.

The delivery archive includes a ready-to-open `FraudShield_dashboard.html` with embedded measured evidence. Open that file to explore results without installing Python or running a server. It exports its embedded report and metrics locally; new inference still requires the local engine. If you only want inference with the included compatible model environment, skip download and train and run `python run.py serve` after dependency installation.

## What you can do

- Compare prevalence baseline, logistic regression, random forest, Extra Trees, histogram boosting, isolation forest, LightGBM, and XGBoost.
- Change the review budget and cost assumptions to see the workload, false alerts, missed cases, and historical exposure.
- Inspect and export held-out cases. Labels are retrospective outcomes; generated transaction IDs do not identify customers.
- Inspect precision-recall, ROC and calibration curves, AP uncertainty, feature importance and input distribution shift.
- Export the measured report, model metrics, run evidence and an interactive scenario report.
- Score up to 500 anonymized transactions in the browser through the local API, or score a CSV with the CLI.
- Open Evidence & safeguards to inspect three measured forward BAF test months, age-group error rates, exact named-model contributions, the limitation response matrix and its printable report.
- Record append-only local research dispositions from a card case dialog. Records are bound to the exact dataset fingerprint and measured run; they do not block payments or establish criminal intent.

```powershell
python run.py score data/new_transactions.csv --output predictions.csv
python -m pytest -q
```

CLI scoring requires numeric `V1` through `V28` and non-negative `Amount`; `Time` is optional and not used by the model. Existing output files are never overwritten. Probabilities apply only to the original feature representation, not arbitrary PCA vectors from another business.

## Evidence boundaries

After removing 1,081 exact duplicate rows, the measured dataset has 283,726 rows and 473 fraud labels. Four chronological partitions serve distinct roles: 50% training, 15% tuning, 15% calibration and 20% final testing. Timestamps are never split between periods. Models train only on the first partition; no oversampling or class rebalancing touches test data. Training-only class weighting is tested where appropriate.

Hyperparameters and the champion are selected by uncalibrated tuning-period average precision. A sigmoid calibrator is then fitted independently to each model on the calibration period. That same calibration period sets a threshold targeting 1% reviews. The final test reports actual workload at that threshold; the top-1% ranking metric is a separate rule with deterministic index tie breaks. Exploring test thresholds in the dashboard is explicitly retrospective and does not change the selected model or saved threshold.

Average precision uses scikit-learn's step-weighted definition. A 150-resample block bootstrap over 40 contiguous test blocks provides a conditional 95% AP interval. The dataset spans only two days; intervals cannot describe longer-term drift. Brier score is probability error, not a pure calibration metric. Input PSI is not proof of performance degradation. Feature importance is a tune-period permutation measurement, not a causal or per-case explanation.

No published leaderboard result is claimed as reproduced. No experiment on current Indian payments or online payments is claimed. Account-opening evidence exists only for the explicitly synthetic BAF Base task. The original ULB run and its source fingerprints remain historical records; current extension fingerprints are in `web/assurance.json`. See [research and roadmap](docs/research.md).

## Additional evidence commands

```powershell
python run.py train-baf --data data/baf/Base.csv
python finalize_assurance.py
python run.py validate-bank --data authorized_events.csv --manifest provenance.json --output validation.json --period period.json
node tests/test_dashboard.cjs
node tests/test_assurance_ui.cjs
python package_delivery.py
```

BAF Base.csv is available from the [dataset owner's distribution](https://www.kaggle.com/datasets/sgpjesus/bank-account-fraud-dataset-neurips-2022), release 2, under **CC BY-NC-SA 4.0**. It is not bundled as raw data. The BAF-derived model/reports/examples retain the noncommercial/share-alike conditions. Exact original 32-column schema is required; unexpected outcome fields cannot silently become predictors. `finalize_assurance.py` enriches measured exports and creates `web/assurance_report.html` without altering card-model results.

## Interface and boundaries

- [CLI](run.py): `download [--data PATH]`, `train [--data PATH] [--bootstrap N]`, `serve [--port 8765]`, `score INPUT --output OUTPUT`.
- [Engine contracts](fraudshield/README.md): loading, chronological partitions, metrics, training artifacts and scoring API.
- [Dashboard contracts](web/README.md): static evidence explorer and local scoring integration.
- [Architecture](docs/architecture.md): data flow, validation, artifact schema, operational limits.
- [Research](docs/research.md): primary sources, benchmark matrix, pending datasets.

## Invariants

- Final-test labels never select a model, calibrator, hyperparameter, or saved threshold.
- Raw data and model artifacts stay outside the web root. No personal data is needed or accepted by the browser scoring API.
- Scores support investigation. They do not authorize payment rejection or prove fraud.
- The dashboard uses the actual exported benchmark. It shows an actionable error if that evidence is missing.

## Side effects

`download` makes one network request and writes `data/creditcard.csv`. `train` uses local data, prints run progress, writes model artifacts and replaces generated benchmark/report exports. `serve` binds loopback only and processes scoring requests in memory. User-entered research review events persist in run-scoped SQLite under ignored `local-state/reviews/`; they are excluded from delivered archives. `score` creates a new CSV. No telemetry or external model calls occur during dashboard use or inference. Browser downloads are user initiated.

## Verification

`python -m pytest -q` checks metrics, split boundaries, input validation, model integrity, HTTP handler behavior through an in-memory connection, and exported evidence when present. `node --check web/app.js` and `node tests/test_dashboard.cjs` check JavaScript syntax and dashboard logic. See `docs/review.md` for executed checks and limitations.

This is a local research application. Model artifacts use joblib/pickle: load only artifacts you created and trust. Hash checks detect accidental modification but do not make untrusted serialized models safe. The loopback HTTP server has no user authentication, TLS or production infrastructure.
