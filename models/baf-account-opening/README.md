---
language: en
license: cc-by-nc-sa-4.0
tags:
  - tabular-classification
  - fraud-detection
  - synthetic-data
  - fairness
  - research
metrics:
  - average_precision
---

# FraudShield synthetic BAF account-opening champion

LightGBM champion for the final fold of the BAF Base synthetic account-opening task. It is not the card model and is not evidence of current real-bank deployment performance.

## Source and permissions

Bank Account Fraud Dataset Suite (NeurIPS 2022), Base variant, Kaggle release 2. One million synthetic applications across eight months. Original Base.csv SHA-256: `7bf10a37ce07e72e14c1b09e5efee3d27261baff4facc7da767b0474dcf9b809`.

Creators: Sergio Jesus, Jose Pombal, Duarte Alves, Andre Cruz, Pedro Saleiro, Rita P. Ribeiro, Joao Gama, Pedro Bizarro. Paper: *Turning the Tables: Biased, Imbalanced, Dynamic Tabular Datasets for ML Evaluation*, NeurIPS 2022.

Dataset: https://www.kaggle.com/datasets/sgpjesus/bank-account-fraud-dataset-neurips-2022 ; owner documentation: https://github.com/feedzai/bank-account-fraud . The released records are synthetic, derived from anonymized real data. They were not observed in 2026.

BAF-derived model, reports, examples and explanations are shared under **CC BY-NC-SA 4.0**: https://creativecommons.org/licenses/by-nc-sa/4.0/ . Changes include local training, forward splits, exclusion of age/month/device_fraud_count from predictors, probability calibration, group audits and model contributions. No creator endorsement is implied. Raw data is not redistributed.

## Evaluation

Three forward tests, for months 5, 6 and 7, with earlier non-overlapping training, tuning and calibration periods. Each fold's champion is selected on tuning AP. `run.json` preserves exact schemas, split counts, model specifications, metrics, age audits and uncertainty guards. `champion.joblib` is the final-fold bundle; earlier-fold serialized models are not included.

The final test uses 96,843 applications with 1,428 fraud outcomes. At the reported common threshold, age-50+ legitimate applications have a 7.64% false-positive rate versus 3.04% under age 50. Age was excluded from predictors, which did not remove this disparity. This audit is not a fairness certification or causal explanation. Intervals are withheld where independent time clusters are insufficient.

## Loading and schema

Install the compatible FraudShield environment in `requirements-lock.txt`. Use `fraudshield/baf.py` for the exact preprocessing and score extraction contract. `run.json` lists named features; do not silently add columns or labels as predictors. The repository's BAF loader requires the exact original dataset schema.

Only load trusted joblib files and verify `model_hash.json`. Pickle/joblib can execute code. Hashes detect changed bytes; they do not make untrusted models safe. No hosted inference service is included.

## Limits and responsible interpretation

Research use under the stated noncommercial/share-alike terms. Scores support human review and do not prove intent or criminal activity. No actual approve/challenge/decline action is connected. No realized savings, recovery, customer abandonment or successful authentication benefit is measured. Results must not be pooled with the ULB card benchmark. Real deployment requires appropriate current data, permissions and prospective validation.

Repository: https://github.com/charan-143/FraudShield . See DATA_ATTRIBUTION.md and docs/assurance_design.md for details.
