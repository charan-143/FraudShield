# Current institution validation: required evidence

This is an executable validation contract, not a claim that bank data has been obtained or that a current-bank model has been approved. Use authorized, minimized, pseudonymous data. Do not send account numbers, names, addresses, contact details or other direct identifiers.

## Files and invocation

```powershell
python run.py validate-bank --data events.csv --manifest provenance.json --output validation.json --period period.json
```

The output path must not exist. `--period` is optional. Validation emits evidence only; it does not fit a model or authorize a transaction decision.

## Events schema

| Column | Contract |
| --- | --- |
| event_id | Unique nonmissing pseudonymous identifier |
| event_time | ISO8601 timestamp with explicit timezone; normalized to UTC |
| entity_id / device_id / merchant_id | Nonempty pseudonyms; not predictive numeric IDs |
| amount | Finite nonnegative numerical transaction amount in its stated currency |
| currency | Uppercase three-letter currency code; no FX conversion inferred |
| channel / country | Nonempty decision-time source fields |
| confirmed_fraud | 0 or 1 for known operational outcome, otherwise empty; not proof of criminal intent |
| label_available_at | Explicit-timezone timestamp paired with each known label, not earlier than the event; empty for unknown outcomes |
| protected_group | Optional authorized supplied group, never inferred from identities; validation does not automatically run a bank fairness audit |
| actual_loss / recovered_amount / review_cost | Optional observed accounting values; CSV strings are preserved before Decimal arithmetic |
| outcome_status | Financial aggregation uses only records explicitly marked `closed`; other records are counted as pending |

The three observed monetary fields must be finite, nonnegative and recovered_amount cannot exceed actual_loss. Currency totals are never pooled. Net realized loss is actual_loss minus recovered_amount plus review_cost. This does not measure avoided losses, causal savings or model-attributable benefit. Transaction amount is never a substitute for realized loss.

## Provenance manifest

```json
{
  "source_system": "AUTHORIZED_SOURCE_NAME",
  "population": "INSTITUTION_CHANNEL_COUNTRY_AND_COVERAGE",
  "collection_start": "2026-01-01T00:00:00Z",
  "collection_end": "2026-10-01T00:00:00Z",
  "license_or_authority": "DOCUMENTED_ACCESS_AND_USE_AUTHORITY",
  "feature_provenance": "WHEN_AND_HOW_DECISION_TIME_FIELDS_WERE_OBSERVED",
  "label_policy": "CONFIRMATION_CRITERIA_AND_WHEN_LABELS_BECAME_KNOWN"
}
```

All seven fields must be nonempty strings; the collection dates must be timezone-aware and cover the actual input events. The pipeline validates the contract, not the truth of a claimed source or legal authority. Timestamp ordering assumes records were observable in event-time order; late-arriving event provenance must be investigated before production replay claims.

## Cohort maturity

`period.json` contains `start`, `end`, `labels_as_of`, each an explicit-timezone ISO8601 timestamp. Events in [start,end) are eligible only when the label is known and label_available_at <= labels_as_of. Unknown/delayed counts are reported. labels_as_of must be at least end. For a future training workflow, set each historical training/tuning/calibration label cutoff to the next decision stage; do not use labels learned later.

## Behavior features

The validator computes prior 1-hour and 24-hour counts, prior 24-hour amount and mean, amount-to-prior-mean ratio, and device/merchant novelty in the previous 24 hours. Windows include the lower boundary and exclude the current timestamp. All equal-time events are scored before any enter history. Histories are separated by entity and currency. Deques and counters provide amortized linear history maintenance; output memory is proportional to the extract. Rolling totals use exact rational sums of the validated numeric representations to avoid cancellation when large expired amounts leave small retained transactions. Reported feature values are floats. First-history mean and ratio are unavailable, not fabricated zero baselines. Numeric aggregation overflow raises an error.

## What is still needed

Current Indian payments evidence requires authentic representative institution data, properly matured outcomes, leakage review and validation over an adequate period. A synthetic dataset and a contract alone cannot establish performance, fairness, intervention success or realized savings. Institution-specific training, protected-group assessment, long-horizon/entity-aware validation and controlled operational evaluation remain separate tasks after authorized data is supplied.
