# FraudShield evidence and assurance extension

Date: 2026-11-06. Supporting implementation design, continuing the owner's authorized implementation workflow. The original ULB evidence is preserved; its data limitations cannot be repaired by changing prose.

## Goals and evidence boundaries

Address eight limits through measurable additions: more temporal windows on a documented public dataset, meaningful-feature modeling, explicit label-availability controls, human-review recording, observed financial outcomes, protocol comparison gates, dependence-aware uncertainty rules and protected-group audits. No new experiment is a claim of current Indian card/UPI performance. BAF is a synthetic account-opening task and is never pooled with the real ULB card task.

## Implementation

- Create `fraudshield/assurance.py` for group confusion rates with Wilson intervals and denominators, protocol compatibility checks, calendar/entity-cluster uncertainty with insufficient-unit guards, and currency-separated observed financial accounting.
- Create `fraudshield/bank_events.py` for a strict timezone-aware bank event contract, point-in-time behavioral features excluding same-time peers, and training/evaluation cohorts filtered by actual label availability. No unobserved fraud labels or demographics are invented.
- Create `fraudshield/baf.py` for the downloaded original BAF Base.csv: fingerprint raw data; preserve month; exclude customer_age, month and device_fraud_count from prediction; train a scaled logistic baseline and two LightGBM weighting variants. Fixed forward protocols are train months 0–2/tune3/cal4/test5, train0–3/tune4/cal5/test6, and train0–4/tune5/cal6/test7. Each stage selects only on earlier data. No fine-grained label delays or entity histories are claimed for BAF.
- Export per-month results, age-under-50/50+ group rates with uncertainty qualifications, and exact TreeSHAP contributions to raw LightGBM model margin for selected cases. These are associations, not causal explanations or calibrated-probability decompositions. Sensitive age is excluded from predictive features but other proxies can remain. BAF outcomes have no observed loss/recovery ledger, so financial fields remain unavailable.
- Create `fraudshield/reviews.py`: a local SQLite append-only review event store, disposition/reason/actor/time records and a hash chain. Review outcomes are research dispositions, never criminal findings or automatic payment actions. Scope is one local app; no authenticated multi-user workflow is claimed.
- Extend local API and case dialog to save/list research review events. Extend dashboard with an evidence/assurance view, loaded from `assurance.json` or embedded standalone evidence. Distinguish repaired implementation from still-missing external evidence for each limit.
- Extend CLI with `train-baf` and `validate-bank`; produce evidence reports and tests. Package both studies and all supporting source without raw datasets. Preserve the existing Library item's version identity when updating the project archive.

## Bank data contract

Required event fields: event_id, event_time (ISO8601 with explicit timezone), entity_id (pseudonym), device_id, merchant_id (pseudonyms), amount, currency, channel, country, confirmed_fraud (0/1 or unknown), label_available_at (timezone-aware or missing if outcome unknown). Protected_group is optional and must come from authorized data, not inference. Observed financial fields, when available: actual_loss, recovered_amount, review_cost and outcome_status=closed. Data provenance manifest identifies source_system, population, collection_start/end, license_or_authority, feature_provenance and label_policy. User-supplied provenance is asserted evidence, not independently verified certification.

All event-time features use earlier observations only; same-timestamp events cannot influence each other. Cohort selection distinguishes event date from label-availability date. Unmatured labels are excluded and counted, never treated as legitimate. Financial accounting is by currency and closed outcomes only; net loss includes observed loss less recovered funds plus review expense. No avoided-loss counterfactual is claimed.

## Validation and independent review

Test cohort maturity, same-time exclusion, future-event invariance, fraud label unknowns, monetary precision/currency separation, group sample guards, cluster-count guards, protocol mismatch rejection, append-only review chain and escaped UI output. Run measured BAF training. Use fresh-context reviewers to check scientific logic and app/API safety, resolve concrete findings, then update contracts and the drift report. Visual/live-network testing remains environment-dependent and cannot be substituted by logic tests.

## Acceptance boundaries

BAF supplies a longer synthetic stress test and age fairness evidence for that separate task; it cannot validate current banks, reconstruct ULB PCA, prove demographic fairness on ULB, or provide genuine human analyst performance. Exact benchmark reproduction remains blocked unless source, splits, features, search budget and metrics match. Production suitability requires current institution-specific data, mature labels, approved attributes and operational outcomes.
