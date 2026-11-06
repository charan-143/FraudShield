---
language: en
tags:
  - tabular-classification
  - fraud-detection
  - sklearn
  - research
metrics:
  - average_precision
  - roc_auc
---

# FraudShield ULB card model collection

Eight research model bundles trained for historical card-fraud outcome ranking. Extra Trees (`model-3.joblib`) is the champion selected on tuning average precision. Other bundles are comparator models, not recommended deployment substitutes.

## Data and evaluation

ULB / Worldline: two days of European transactions from 2013. 284,807 original rows; 283,726 after exact deduplication; 473 fraud outcomes. Original CSV SHA-256: `76274b691b16a6c49d3f159c883398e03ccd6d1ee12d9d8ee38f4b4b98551a89`.

Chronological train/tune/calibration/test proportions: 50/15/15/20, with timestamp groups intact. Hyperparameters and champion use tuning data. Sigmoid calibration and saved thresholds use calibration data. The final period has 56,744 transactions and 74 fraud labels. Later policy analyses on that already-inspected period are retrospective.

Extra Trees final-test AP: **0.789812**; ROC-AUC: **0.955905**. Top-1% ranked reviews: 568, capturing 62 frauds (83.8% recall, 10.9% precision). Saved threshold `0.0034456687360667235`: 605 reviews, 62 frauds, 543 false alerts. Top-k ranking and numerical thresholds are distinct policies. Local chronological scores are not comparable to random-split or hidden-test leaderboards without matched protocols.

## Files and loading

`model-0` prevalence baseline; `model-1` logistic regression; `model-2` Random Forest; `model-3` Extra Trees; `model-4` histogram boosting; `model-5` Isolation Forest; `model-6` LightGBM; `model-7` XGBoost. All have `.joblib` suffixes. `run.json`, `model_hashes.json`, `trials.csv`, and `requirements-lock.txt` describe provenance and compatibility.

Use the FraudShield repository's `fraudshield.training.predict_bundle` and `fraudshield.server.load_champion` with artifacts in its `artifacts/` directory. Install the exact locked environment first. Bundle objects include calibration and transforms; loading the underlying classifier alone does not reproduce exported probabilities.

```python
from pathlib import Path
import joblib
import pandas as pd
from fraudshield.training import predict_bundle

# Load only trusted artifacts after checking the published hashes.
bundle = joblib.load(Path('artifacts/model-3.joblib'))
rows = pd.read_csv('authorized_ulb_format_transactions.csv')
scores = predict_bundle(bundle, rows)
```

The inference schema requires original numeric `V1` to `V28` and nonnegative `Amount`. Optional `Time` is validated but not used as a predictor. Arbitrary PCA vectors from another bank are not compatible with this feature space. The CLI/API validate inputs; callers using internal functions must follow the data contract.

Measured environment: Python 3.14.7, numpy 2.5.4, pandas 3.1.0, scikit-learn 1.9.1, LightGBM 4.7.0, XGBoost 3.4.1, joblib 1.6.0. Model-version compatibility is not guaranteed outside that environment. Pickle/joblib may execute code: never load untrusted files. Hash verification is not a security sandbox.

## Intended use and limits

Educational research, reproducibility and retrospective policy exploration. No live payment decisions or authentication integration. Scores require human review; labels do not establish criminal intent. Historical amounts are exposure, not savings. No present-day Indian-bank performance, customer satisfaction, demographic fairness or merchant/device explanations can be established from these data. Entity identifiers, label delay and original PCA-fitting provenance are unavailable. Bootstrap intervals describe this short historical period and are not deployment assurances.

## Attribution and terms

Source: https://www.kaggle.com/datasets/mlg-ulb/creditcardfraud ; mirror documentation: https://www.tensorflow.org/tutorials/structured_data/imbalanced_data . Consult the source owner's data terms (Database: Open Database; Contents: Database Contents) and DATA_ATTRIBUTION.md. No blanket MIT/Apache license or ownership of the source data is claimed. Raw data is not redistributed. Model redistribution does not confer permission for production or commercial use beyond applicable source terms.

Training run: `20261106T070211Z`. Repository: https://github.com/charan-143/FraudShield . This card describes that run, not a later retrained model.
