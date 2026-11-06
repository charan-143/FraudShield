# Research engine

## Interface

- `data.load_card(path)`: validated, deduplicated, chronological frame plus dataset fingerprint.
- `data.model_input(frame)`: numeric V1–V28 and log(1+Amount).
- `data.temporal_splits(frame)`: strictly time-separated train, tune, calibration and test frames.
- `metrics.operating_metrics`, `budget_threshold`, `top_budget`, `block_bootstrap_ap`, `evaluate`, `psi`: benchmark and policy statistics.
- `training.train`: bounded candidate search, calibration, final-test evaluation, exports.
- `training.predict_bundle`: identical feature and calibration path for serving and CLI scoring.
- `server.load_champion`, `server.serve`: integrity-checked local model load and loopback dashboard/API.
- `baf.run_baf`: fixed forward synthetic BAF benchmark, age audits and TreeSHAP examples; no cross-task pooling.
- `assurance.group_audit`, `comparison_gate`, `cluster_ap_interval`, `financial_outcomes`: qualified group errors, protocol checks, insufficient-unit guards and observed money accounting.
- `bank_events.validate_bank_file`, `matured_cohort`, `behavioral_features`: authorized event contract and strictly earlier-history validation; no current-bank model claim.
- `reviews.ReviewStore`: append-only local research dispositions bound to dataset fingerprint and run ID.

Full behavioral details, output schemas, limits and errors are in [architecture](../docs/architecture.md).

## Invariants

Test outcomes cannot select models or frozen policy thresholds. Training data alone fits preprocessing inside model pipelines. Scores are calibrated on a separate period. Raw and derived data retain source lineage. Only locally trusted model artifacts are loaded.

## Side Effects

Downloader reads the public mirror and creates a local file. Training writes generated models, JSON, CSV and HTML reports. Server binds a loopback port and handles in-memory inference. Research review history is appended to run-scoped local SQLite. No external service is called during inference. Model artifacts use trusted pickle serialization.

## Verification

Run `python -m pytest -q` from the project root. Full real-data training: `python run.py train`.
