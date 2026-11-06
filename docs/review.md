# Review and verification

Date: 2026-11-06. Scope: card transaction research application and measured ULB experiment. Expected use: one researcher or stakeholder on a local machine, not a public multi-user production server.

## Independent review

Two fresh-context reviewers read their supplied code-audit persona and reimplementation standard, the architecture contract, and the relevant full implementation files. One focused on data, metrics, training, source claims and scientific validity. The other focused on the dashboard, inference API, trust boundaries and user-visible behavior. Reviews ran as supporting implementation checks after the owner chose implementation; the earlier section-by-section design approval workflow was not represented as completed.

| Finding | Resolution |
| --- | --- |
| Constant-score model omitted from calibration bins | Added a one-bin constant-predictor case and regression test |
| Optional Time could accept nonnumeric/nonfinite data | All accepted API values now require finite JSON numbers; optional Time also rejects negative values; added tests |
| Async scoring callbacks could access a view after navigation | Health checks use view-version guards; scoring state is retained across views; added late-response check |
| Model-family count was hardcoded | Uses the actual model count in the run |
| Skip link changed the selected view | Prevents hash navigation and focuses main directly |
| Bootstrap protocol name suggested moving windows | Renamed to fixed non-overlapping-block resampling |
| Sigmoid coefficient could be mistaken for a calibration diagnostic | Renamed to calibrator_standardized_coefficient and documented |
| Estimator defaults and interface details were incomplete | Added exact recursive estimator specifications, explicit overrides, metric schemas, case/export/UI contracts |
| Nonnumeric Content-Length returned a different documented status | Explicit 413 branch now covers invalid integer lengths |
| HEAD did not enforce Host validation | Added the same loopback Host rule for HEAD |

The scientific reviewer found no direct leakage in the inspected train/tune/calibration/test path. This does not establish validation for deployment or any other population.

## Executed checks

Python checks cover temporal boundary isolation, exact duplicate removal, input transforms, invalid/missing inputs, confusion counts and exposure, stable top-budget tie rules, constant-predictor calibration, reference-metric parity, exported-model selection, serialized-model integrity, and scoring HTTP handler success/errors.

JavaScript checks cover all six view renders with the real exported evidence, browser/Python confusion-matrix parity, top-budget counts, CSV parsing failures and a late health response after navigation. JavaScript syntax is also checked.

Original release check result: 29 Python tests passed; the dashboard logic check and JavaScript syntax check passed. The independent reviewers re-read the repaired code; the remaining dynamic-count subtitle and Origin-scope wording nits were also fixed. No additional meaningful code defect was reported in the supporting follow-up. The final artifacts were regenerated with the same predeclared model configurations after metadata/reporting repairs; models were not tuned using the observed final test results.

The live Python server starts on loopback, but outgoing loopback sockets from the sandbox are blocked. Both native preview attempts and a separate client could not reach it. HTTP handler tests therefore use the real request parser over in-memory connections; they are not reported as successful browser or live-network testing. The standalone dashboard embeds its evidence and needs no local HTTP connection to explore the measured study.

## Remaining limits

- Browser layout, accessibility and end-to-end file downloads have not been visually verified in this environment.
- No load test, TLS/auth integration or production monitoring is claimed.
- No exact reproduction of an external leaderboard is claimed.
- IEEE-CIS remains unmeasured. A later separate synthetic BAF assurance study is now measured; see assurance_review.md.
- Raw data is not included in the delivery archive. The documented official mirror and fingerprint support reacquisition.

The code and reports retain these limits. Do not interpret a passing unit/handler check as a production-readiness or bank-model approval.
