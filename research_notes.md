# FraudShield: initial research and scope

Date: 2026-11-06. Historical intake notes, superseded by `docs/research.md`, `docs/architecture.md`, and the measured run exported in `web/benchmark.json`. The card transaction implementation now trains eight model families on real ULB data and includes a stakeholder dashboard, local scoring API and reports. Online payments and account opening remain unmeasured planned tracks.

## Working hypothesis

Build a reproducible fraud risk research application that helps risk managers understand losses and review capacity, analysts inspect alerts, and data scientists compare models. Scores support investigation; they do not prove fraud. Intended deployment and fraud domain require owner input before the design is fixed.

## Dataset shortlist

| Dataset | Evidence and purpose | Limits |
| --- | --- | --- |
| ULB / Worldline credit card transactions | Real anonymized European transactions; 284,807 rows and 492 frauds over two days in 2013. Useful first reproducible card-fraud benchmark. | Old, only two days; V1–V28 are PCA components. Cannot invent merchant or customer explanations from them. Preserve native imbalance. |
| IEEE-CIS / Vesta | Online transaction fraud; transaction and optional identity tables joined by TransactionID. Useful broader feature engineering benchmark. | Kaggle sign-in and competition-rule acceptance required. Hidden test labels prevent independent claims about competition performance. |
| Feedzai Bank Account Fraud suite | Generated from anonymized real bank account opening data; designed to test time dynamics, imbalance and bias. | Synthetic, not raw real transactions; account opening is a different prediction task. Report independently from card fraud. |
| Fraud Detection Handbook simulator | Reproducible transaction histories for demonstrating behavioral features, time splits and drift. | Simulation results cannot substantiate performance on real bank data. |

## Candidate modeling and evaluation

Start with prevalence and simple rules, then regularized logistic regression, random forest, gradient boosted trees (LightGBM / XGBoost / CatBoost after environment verification), and an isolation forest anomaly baseline. Consider a neural tabular challenger only with a defined compute budget and a strong tree baseline. The goal is measured usefulness, not a list of tools.

Use ordered train / validation / final test periods with all preprocessing fitted on training data only. Select hyperparameters, probability calibration and operating thresholds without inspecting the final test labels. Record dataset hashes, versions, seeds, split boundaries, training cost and hardware. For richer histories, account for delayed labels and entity leakage explicitly.

Report average precision (with its exact implementation), ROC-AUC, precision and recall at a fixed review budget, recall at specified false positive rates, confusion counts, calibration, inference latency and an assumed cost model. Include uncertainty and fraud counts. Never present accuracy as the headline. Monetary estimates must distinguish transaction exposure from recoverable loss and disclose all assumptions.

Published scores are comparable only with matching data versions, preprocessing, splits and metric definitions. A local temporal test is not a reproduction of a random-split leaderboard. “All benchmarks” requires a bounded benchmark matrix rather than a claim of exhaustive coverage.

## Dashboard and report hypothesis

An executive overview explains fraud exposure, alerts, review load and missed cases in plain language. A threshold explorer shows the impact of changing review capacity and costs. An analyst table supports filtering and individual case inspection. A model comparison view shows held-out results and uncertainty. Data health views show missingness and distribution shifts; drift alone is not proof of degraded model quality. Export a run-specific report and machine-readable metrics. Demo data and measured results must be visibly distinguished.

## Open boundaries

- Which initial fraud domain and intended deployment should anchor the project?
- What compute resources and dataset credentials are available?
- Which stakeholder workflow and review capacity should define the primary operating metric?

## Sources inspected

- ULB dataset owner data card: https://www.kaggle.com/mlg-ulb/creditcardfraud/data
- IEEE-CIS competition data description and access conditions: https://www.kaggle.com/competitions/ieee-fraud-detection/data
- Feedzai research publication: https://research.feedzai.com/publication/turning-the-tables-biased-imbalanced-dynamic-tabular-datasets-for-ml-evaluation/
- Amazon FDB research overview: https://www.amazon.science/code-and-datasets/fdb-fraud-dataset-benchmark
- Handbook validation strategies: https://fraud-detection-handbook.github.io/fraud-detection-handbook/Chapter_5_ModelValidationAndSelection/ValidationStrategies.html

## Workflow status

Card transaction implementation, real-data training and two independent supporting reviews are complete. Concrete review findings were repaired and checked. The owner chose implementation over the gated design-only workflow; the full original EGM stage/approval protocol is not claimed as completed. Python tests and JavaScript logic checks pass. Live browser/network preview remains blocked in this environment, and visual verification is not claimed. Current evidence and limits are in `docs/review.md`. No state-of-the-art performance or external leaderboard reproduction claim is made.
