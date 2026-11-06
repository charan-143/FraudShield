# Supporting implementation review and resolution

Two fresh-context reviewers read the relevant EGM audit persona/standard, the assurance design and complete assigned implementation files. One audited temporal/label logic, source claims, monetary accounting and statistical inference. One audited the review store/API and browser state transitions. This continues the owner-approved implementation workflow; it is not represented as a completed section-by-section design approval protocol.

## Findings resolved

| Concrete finding | Repair and evidence |
| --- | --- |
| CSV float inference could round observed monetary amounts before Decimal | Preserve actual_loss/recovered_amount/review_cost CSV strings; regression covers 9007199254740992.01 |
| Extra BAF outcome fields could silently become predictors | Require exact 32-column schema and fixed predictor list; reject extra/missing fields |
| Currency validation differed across paths | All bank events require uppercase three-letter currency codes |
| Review positional IDs could refer to different transactions after retraining | Dataset fingerprint and run ID bind the store, each hashed payload and filesystem namespace; incompatible stores are rejected |
| Reopened-case callbacks could qualify against a newer same-ID dialog | Monotonic dialog generation and per-dialog pending guards |
| Old save refresh could clear a different case's unsaved reason | Recheck captured dialog generation after awaited refresh; race regression test |
| Large expired amounts could erase small retained behavioral totals | Exact rational rolling totals of validated source numeric representations; regression covers retained .01 after 1e16 expires |

Follow-up reviewers confirmed the material fixes. No additional meaningful scientific or app defect was reported in their final follow-ups. The final rational-total repair was additionally verified with a focused regression.

## Verification scope

Python tests cover measured output contracts, chronology, label availability, same-timestamp exclusion, future-event invariance, entity/currency separation, source window coverage, CSV amount precision, group/cluster insufficiency guards, strict schemas, protocol mismatch blocking, SHAP additivity, run-bound review identity, immutable history, and HTTP handler success/error paths. Node tests render all original six views and the new assurance view from measured data, check metric parity and test both review callback races.

Live-loopback/browser testing remains blocked by the execution environment; a passing in-memory HTTP test or DOM-state logic fixture is not visual or production verification. No current-bank performance, real analyst accuracy, demographic fairness on ULB, causal savings or exact published benchmark reproduction is claimed.

The BAF age audit reports an actual measured disparity rather than calling the model fair. The two original public datasets contain no observed loss/recovery ledger, so no realized savings figure is invented. Bank validation accepts supplied provenance under a schema; it does not independently authenticate that provenance.

Final executed result: 47 Python tests passed. Both Node dashboard suites and JavaScript syntax checks passed. Original ULB results were preserved; BAF measured forward-test APs for tune-selected models were 0.1879, 0.1748 and 0.2174 on source months 5, 6 and 7.
