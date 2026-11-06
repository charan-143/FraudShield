# FraudShield research and benchmark matrix

Research date: 2026-11-06. Scope agreed: card transactions first, then online payments and bank account opening. The first release is local research and stakeholder decision support, not an automated payment blocking product.

## Dataset decisions

| Task | Dataset | Evidence | Access and caveats | Current state |
| --- | --- | --- | --- | --- |
| Card fraud | ULB / Worldline 2013 | Real anonymized card transactions, 284,807 raw rows and 492 fraud labels over two days | PCA features obscure business explanations; old European population; dataset licensing and citation obligations still apply to derived work | Downloaded from the mirror used in TensorFlow's official tutorial; eight families measured |
| Online transaction fraud | IEEE-CIS / Vesta | Transaction table plus optional identity table; join by TransactionID | Kaggle competition rules require account acceptance; hidden-test labels not available locally; TransactionDT is a reference timedelta | Planned separate pipeline after authorized data access |
| Account opening fraud | Feedzai BAF suite | Generated from anonymized real account-opening data; designed for temporal dynamics, imbalance and bias evaluation | Synthetic, not raw real-world observations; separate task with protected-attribute evaluation | Measured separate BAF Base study: three forward test months, age audits and named-model contributions; not current-bank validation |
| Behavioral simulation | Fraud Detection Handbook | Reproducible histories and temporal validation examples | Synthetic; useful to test feature engineering and delayed-label protocols, not to claim real-bank performance | Reference only |

The raw ULB file SHA-256 is `76274b691b16a6c49d3f159c883398e03ccd6d1ee12d9d8ee38f4b4b98551a89`. The pipeline removes 1,081 exact duplicate rows (including repeated fraud records), retaining 283,726 transactions and 473 fraud labels. Deduplication changes the benchmark population and must be declared in any comparison.

## What is benchmarked

| Dimension | Implemented evidence | Interpretation |
| --- | --- | --- |
| Ranking | AP, ROC-AUC, recall and precision at top 0.5%/1% review | Native class imbalance is preserved in evaluation |
| Operational threshold | Confusion counts and rates at calibration-set threshold | Test workload can differ from the calibration target |
| Rare false alerts | Descriptive recall at FPR <=0.1% | Does not authorize choosing a deployment threshold on test labels |
| Probability quality | Brier score and calibration bins | Few calibration frauds; Brier reflects more than calibration |
| Uncertainty | 150 block bootstrap replicates, conditional 95% AP interval | Short history and event dependence limit confidence |
| Compute | All-configuration train time; 256-row batch median and p95 inference | Local measurements, not service response-time guarantees |
| Interpretability | Tune-period permutation AP drop | Global association; no fabricated descriptions of PCA components |
| Input shift | Train-to-test PSI | No automatic drift-triggered retraining or proof of performance degradation |
| Economic scenario | Recovery fraction × flagged historical fraud amount minus review cost | User assumptions; not actual savings or expected calibrated economic utility |

Eight families span simple baselines, linear learning, bagged trees, modern boosted trees and unsupervised anomalies. Neural and graph models were not added without suitable temporal history or entity/edge data. “State of the art tools” does not justify misrepresenting this tabular dataset as a graph problem. Modern LightGBM and XGBoost are evaluated alongside simpler challengers; the measured evidence determines selection.

## Published benchmark comparability

Amazon FDB provides standardized loaders and splits across fraud and abuse tasks; it is a reference for a future exact-protocol reproduction. This implementation does not claim to reproduce FDB scores. A valid comparison requires matching source version, deduplication, feature definitions, splits, tuning budget, metric integration and label policy. Published random-split ULB scores and IEEE-CIS leaderboard AUC are not directly comparable to this deduplicated chronological ULB test.

## Next-track acceptance conditions

For IEEE-CIS, obtain the original transaction and identity CSVs under the competition rules. Validate join cardinality, missing identity handling and ordering. Separate train, tune, calibration and final local test by TransactionDT. Exclude TransactionID as a predictive numerical feature. Build categorical encoders only on training. Entity aggregates must use earlier events only. Hidden competition test data is inference-only, with no fabricated local metrics.

For Feedzai BAF, retain the dataset's synthetic designation and suite variant identity. Order by month, fit categorical handling on training months, and keep account-opening outcomes distinct from card fraud. Report group recall/FPR with counts and uncertainty where protected-attribute documentation permits. Never infer demographic fairness for ULB, which lacks those attributes.

## Primary sources

1. Dataset owner card and recommended evaluation context: https://www.kaggle.com/datasets/mlg-ulb/creditcardfraud
2. Official TensorFlow imbalanced classification tutorial and public mirror: https://www.tensorflow.org/tutorials/structured_data/imbalanced_data
3. Fraud Detection Handbook, validation strategies: https://fraud-detection-handbook.github.io/fraud-detection-handbook/Chapter_5_ModelValidationAndSelection/ValidationStrategies.html
4. Amazon Science FDB overview: https://www.amazon.science/code-and-datasets/fdb-fraud-dataset-benchmark
5. FDB paper: https://arxiv.org/abs/2208.14417
6. IEEE-CIS competition data documentation: https://www.kaggle.com/competitions/ieee-fraud-detection/data
7. Feedzai BAF research publication: https://research.feedzai.com/publication/turning-the-tables-biased-imbalanced-dynamic-tabular-datasets-for-ml-evaluation/
8. scikit-learn average precision: https://scikit-learn.org/stable/modules/generated/sklearn.metrics.average_precision_score.html
9. scikit-learn calibration: https://scikit-learn.org/stable/modules/calibration.html
10. LightGBM parameters and probability caution for class weighting: https://lightgbm.readthedocs.io/en/latest/Parameters.html

These sources justify dataset and metric choices; measured model outputs come exclusively from the local experiment.
