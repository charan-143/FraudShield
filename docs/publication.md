# Publication layout

## Publication status, November 6, 2026

- GitHub: https://github.com/charan-143/FraudShield . Private repository; making it public requires owner approval.
- LinkedIn article: https://www.linkedin.com/pulse/fraudshield-finding-trade-off-between-fraud-capture-charan-tej-xu6rf . Published with an accompanying feed announcement.
- LinkedIn feed post: https://www.linkedin.com/feed/update/urn:li:ugcPost:7524406982942810112/ .
- Hugging Face: two upload bundles prepared, covering eight ULB card bundles and the final BAF LightGBM champion. Upload is pending account login; no live model URL is claimed.
- Verified locally: 52 Python tests and both dashboard logic suites. GitHub-hosted CI has not been verified.

GitHub contains source, tests, research documentation, model cards and measured reports. Raw datasets, local reviews, dependency wheels and private credentials must not be committed. Trained binary models are intended for separately documented Hugging Face repositories.

`models/ulb-card/README.md` documents all eight card bundles; `models/baf-account-opening/README.md` documents the synthetic BAF champion and its separate usage conditions. `artifacts/run.json` and hash manifests identify the original training run. Never load joblib files from an untrusted source.

The full `web/benchmark.json` contains held-out research records and is a generated dashboard export. Regenerate with `python run.py train` after obtaining the attributed source dataset, or use the complete delivery archive. Source-only GitHub installs need the generated benchmark export and compatible trained artifacts before the measured dashboard/API can run.

The project blog is in `docs/blog.md`; the short LinkedIn announcement is in `docs/linkedin_post.txt`. Publication must not imply that the simulated tiers perform actual authentication or that measured exposure equals savings.

BAF-derived models, reports, explanations and examples retain CC BY-NC-SA 4.0 attribution and conditions. The repository does not grant a blanket permissive license over third-party data or derived artifacts. ULB terms remain those of the original data owner, referenced in DATA_ATTRIBUTION.md.
