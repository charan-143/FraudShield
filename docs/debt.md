# Bounded implementation decisions

| Decision | Current limit | Upgrade trigger |
| --- | --- | --- |
| Single local training run and model directory | Generated artifacts are not a multi-file transaction | Add run-specific immutable directories and promotion when concurrent or scheduled retraining is required |
| Loopback Python HTTP server | No authentication, TLS or bounded worker pool; only local run-bound research review persistence | Replace with a production API and access controls before remote/multi-user use |
| Static evidence export | Entire 56,744-row test slice loads into browser memory (~12 MB JSON) | Add paginated APIs when exporting millions of transactions |
| Raw PCA card features | No merchant, device or identity explanation; no entity-aware temporal aggregates | Add a dataset with known feature meanings and event history |
| Short historical data | Two days, 74 final-test frauds, no delayed labels or demographic fields | Require bank-specific temporal backtesting, calibration, delayed outcomes and fairness review before deployment |

No speculative distributed pipeline, LLM risk rationale, graph network, paid service, or production payment action was added. Those would not improve the validity of this first measured study.
