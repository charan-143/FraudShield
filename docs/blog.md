# FraudShield: finding the trade-off between fraud capture and customer friction

I started FraudShield with a practical question: how much fraud can a model catch before it interrupts too many legitimate transactions?

That question shaped the project. A useful fraud model needs an operating policy that analysts and product teams can inspect. Average precision helps compare rankings, but customers experience challenges, delayed transactions and false alarms.

## Two studies with different jobs

The card experiment uses the ULB / Worldline dataset: European card transactions from two days in 2013. After removing 1,081 exact duplicate rows, 283,726 transactions remain, including 473 historical fraud labels. This is a research benchmark, not evidence of current Indian-bank performance.

A separate experiment uses one million synthetic BAF account-opening applications across eight months. It supports forward-month evaluation, named-feature contributions and an age-group audit. Its results are kept separate because account opening and card transactions are different tasks. Synthetic BAF records do not establish real bank deployment performance.

## Choosing a model without choosing on the test set

The card pipeline has four chronological periods: training, tuning, calibration and final testing. Timestamp ties stay in one period. Eight families are evaluated: prevalence baseline, logistic regression, Random Forest, Extra Trees, histogram boosting, Isolation Forest, LightGBM and XGBoost.

Tuning-period average precision selects Extra Trees. Calibration fits a sigmoid mapping and sets the saved review threshold. Final-test results are reported after those decisions. Some subsequent policy experiments reuse the now-inspected test period; those comparisons are explicitly retrospective.

The selected Extra Trees model achieved 0.7898 final-test average precision. Under a top-1% ranking budget, reviewing 568 transactions captured 62 of 74 fraud outcomes: 83.8% recall and 10.9% precision. The saved numerical threshold is a different operating rule: it produced 605 alerts, including 543 legitimate transactions, while also capturing 62 frauds. These two policies should not be confused.

## A threshold change that did not deserve promotion

I tested a cost-sensitive policy using an 80% calibration recall floor, EUR 3 per review and EUR 100 per missed fraud. These are scenario assumptions, not measured losses.

On the previously inspected test period, this candidate captured 63 frauds instead of 62, but false alerts increased from 543 to 980. That is 437 additional legitimate alerts for one additional fraud outcome. I kept the original saved threshold.

This was an important result for the project: a policy experiment should make an unfavorable trade-off visible too.

## Looking for the operating sweet spot

The new analysis finds the fewest flagged transactions needed to reach each calibration recall floor. It includes entire tied-score groups and counts legitimate step-up candidates as interruptions too.

| Calibration fraud recall | Legitimate interruptions per 10,000 legitimate transactions |
|---|---:|
| 71.4% | 2.8 |
| 81.6% | 177.1 |
| 85.7% | 292.2 |
| 91.8% | 1,317.9 |

An illustrative target of at least 80% recall and at most 50 legitimate interruptions per 10,000 cannot be met by this model on calibration data. Only 49 calibration fraud outcomes support this analysis, so the estimates are uncertain. The target is a research assumption, not a bank SLA or a guarantee.

Risk tiers can route medium-risk cases to an authentication challenge rather than a review queue. But routing alone does not prove improved prevention or customer experience. FraudShield simulates those tiers; it does not approve, challenge or decline payments. Measuring challenge completion, abandonment, latency and repeated challenges per customer requires operational data that this dataset does not contain.

## Explanations and fairness need the right data

ULB's PCA columns cannot honestly be translated into merchant, device or customer behavior. The bank-data adapter can compute earlier-event behavioral features when authorized extracts supply the relevant identifiers and timestamps. Those features are not claimed as trained improvements on ULB.

BAF provides named features and an age attribute. At the final forward test's shared threshold, the age-50+ group had a 7.64% false-positive rate versus 3.04% for the under-50 group. Age was excluded from predictors, yet the disparity remained. This finding motivates investigation; it does not certify fairness, explain causality or generalize to card transactions.

## Making the evidence inspectable

The Python engine handles validation, time splits, model selection, calibration, metrics and local scoring. The browser dashboard lets stakeholders inspect precision-recall trade-offs, review workload, historical exposure, cases and assurance findings. A standalone export works without a server; new scoring needs the local Python API.

The project includes 52 passing Python tests and two dashboard logic suites. These checks cover software behavior, not production readiness. Visual browser verification remains uncompleted. Serialized model files require a trusted source and a compatible Python/library environment.

Historical fraud amounts are reported as exposure, not realized savings. Labels describe historical outcomes, not proof of criminal intent. Model scores support human review.

## What comes next

The next useful experiment needs longer, current transaction histories with merchant and customer context, label-availability timestamps, and measured authentication outcomes. A new forward evaluation should assess fraud recall alongside legitimate challenges, customer abandonment, analyst capacity and observed financial outcomes.

FraudShield's current contribution is an inspectable research pipeline and an explicit operating trade-off. It makes the gap between a good benchmark score and a useful customer experience visible.

## Project and sources

- Repository: https://github.com/charan-143/FraudShield (initially private)
- ULB / Worldline: https://www.kaggle.com/datasets/mlg-ulb/creditcardfraud
- Public mirror documentation: https://www.tensorflow.org/tutorials/structured_data/imbalanced_data
- BAF documentation: https://github.com/feedzai/bank-account-fraud
- BAF dataset: https://www.kaggle.com/datasets/sgpjesus/bank-account-fraud-dataset-neurips-2022

BAF-derived outputs retain CC BY-NC-SA 4.0 conditions. See DATA_ATTRIBUTION.md for attribution and scope.
