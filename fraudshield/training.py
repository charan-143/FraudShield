import hashlib
import importlib.metadata
import json
import os
import platform
import time
from datetime import datetime, timezone
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.dummy import DummyClassifier
from sklearn.ensemble import ExtraTreesClassifier, RandomForestClassifier, HistGradientBoostingClassifier, IsolationForest
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.inspection import permutation_importance
from sklearn.metrics import average_precision_score

from .data import load_card, model_input, temporal_splits, FEATURES
from .metrics import evaluate, budget_threshold, psi

SEED = 42


def estimator_spec(value):
    if isinstance(value, float) and not np.isfinite(value):
        return {'special_float': str(value)}
    if hasattr(value, 'get_params'):
        return {'class': type(value).__module__ + '.' + type(value).__name__, 'parameters': estimator_spec(value.get_params(deep=False))}
    if isinstance(value, dict):
        return {key: estimator_spec(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [estimator_spec(item) for item in value]
    if value is None or isinstance(value, (str, bool, int, float)):
        return value
    return str(value)


def candidates():
    yield 'Prevalence baseline', [DummyClassifier(strategy='prior')], False
    yield 'Logistic regression', [make_pipeline(StandardScaler(), LogisticRegression(C=c, class_weight='balanced', max_iter=700, random_state=SEED)) for c in [0.1, 1.0]], False
    yield 'Random forest', [RandomForestClassifier(n_estimators=140, max_depth=14, min_samples_leaf=3, class_weight='balanced_subsample', max_samples=0.7, n_jobs=4, random_state=SEED)], False
    yield 'Extra trees', [ExtraTreesClassifier(n_estimators=160, max_depth=18, min_samples_leaf=3, class_weight='balanced', n_jobs=4, random_state=SEED)], False
    yield 'Histogram boosting', [HistGradientBoostingClassifier(max_iter=180, max_leaf_nodes=15, learning_rate=0.06, l2_regularization=2, class_weight=w, early_stopping=False, random_state=SEED) for w in [None, 'balanced']], False
    yield 'Isolation forest', [IsolationForest(n_estimators=160, max_samples=2048, n_jobs=4, random_state=SEED)], True
    try:
        from lightgbm import LGBMClassifier
        yield 'LightGBM', [LGBMClassifier(n_estimators=350, num_leaves=leaves, learning_rate=0.04, min_child_samples=40, reg_lambda=2, verbosity=-1, n_jobs=4, random_state=SEED, class_weight=weight) for leaves, weight in [(15, None), (15, 'balanced'), (31, None)]], False
    except ImportError:
        print('LightGBM unavailable; recording it as skipped.', flush=True)
    try:
        from xgboost import XGBClassifier
        yield 'XGBoost', [XGBClassifier(n_estimators=300, max_depth=4, learning_rate=0.05, min_child_weight=5, reg_lambda=3, subsample=0.85, colsample_bytree=0.9, scale_pos_weight=w, tree_method='hist', eval_metric='logloss', n_jobs=4, random_state=SEED) for w in [1, 20]], False
    except ImportError:
        print('XGBoost unavailable; recording it as skipped.', flush=True)


def raw_scores(model, X, anomaly=False):
    if anomaly:
        return -model.decision_function(X)
    return model.predict_proba(X)[:, 1]


def calibration_input(raw, anomaly=False):
    raw = np.asarray(raw)
    return (raw if anomaly else np.log(np.clip(raw, 1e-8, 1-1e-8) / (1-np.clip(raw, 1e-8, 1-1e-8)))).reshape(-1, 1)


def predict_bundle(bundle, frame):
    X = model_input(frame)
    raw = raw_scores(bundle['model'], X, bundle['anomaly'])
    return bundle['calibrator'].predict_proba(calibration_input(raw, bundle['anomaly']))[:, 1]


def train(data_path, root, bootstrap_repeats=150):
    from threadpoolctl import threadpool_limits
    threadpool_limits(limits=4)
    root = Path(root)
    out, web = root / 'artifacts', root / 'web'
    out.mkdir(exist_ok=True)
    web.mkdir(exist_ok=True)
    frame, dataset = load_card(data_path)
    parts = temporal_splits(frame)
    inputs = {name: model_input(part) for name, part in parts.items()}
    split_summary = {name: {'rows': len(part), 'frauds': int(part.Class.sum()), 'prevalence': float(part.Class.mean()), 'time_min': float(part.Time.min()), 'time_max': float(part.Time.max())} for name, part in parts.items()}
    print(json.dumps({'dataset': dataset, 'splits': split_summary}), flush=True)
    rows, bundles, score_arrays, trials = [], {}, {}, []
    y_tune = parts['tune'].Class.to_numpy()
    for number, (name, variants, anomaly) in enumerate(candidates()):
        print(f'Training {name} ({len(variants)} configuration(s))', flush=True)
        best = None
        total_seconds = 0
        for variant, model in enumerate(variants):
            start = time.perf_counter()
            if anomaly:
                # Fit the unsupervised baseline without accessing training labels.
                model.fit(inputs['train'])
            else:
                model.fit(inputs['train'], parts['train'].Class)
            seconds = time.perf_counter() - start
            total_seconds += seconds
            ap = float(average_precision_score(y_tune, raw_scores(model, inputs['tune'], anomaly)))
            trials.append({'model': name, 'configuration': variant, 'tune_ap': ap, 'training_seconds': seconds, 'parameters': str(model), 'estimator_spec': estimator_spec(model)})
            if best is None or ap > best[0]:
                best = (ap, model, variant)
        tune_ap, model, selected_variant = best
        cal_raw = raw_scores(model, inputs['calibration'], anomaly)
        calibrator = make_pipeline(StandardScaler(), LogisticRegression(C=1.0, max_iter=500, random_state=SEED))
        calibrator.fit(calibration_input(cal_raw, anomaly), parts['calibration'].Class)
        bundle = {'model': model, 'calibrator': calibrator, 'anomaly': anomaly, 'features': FEATURES, 'name': name}
        cal_scores = calibrator.predict_proba(calibration_input(cal_raw, anomaly))[:, 1]
        threshold = budget_threshold(cal_scores, 0.01)
        bundle['threshold'] = threshold
        test_scores = predict_bundle(bundle, parts['test'])
        result = evaluate(parts['test'].Class, test_scores, parts['test'].Amount, threshold, uncertainty=False)
        from .metrics import block_bootstrap_ap
        result['ap_ci95'] = block_bootstrap_ap(parts['test'].Class, test_scores, repeats=bootstrap_repeats)
        latency = []
        batch = parts['test'].iloc[:256]
        predict_bundle(bundle, batch)
        for _ in range(12):
            start = time.perf_counter()
            predict_bundle(bundle, batch)
            latency.append((time.perf_counter()-start) * 1000)
        slug = f'model-{number}'
        result.update(id=slug, name=name, tune_ap=tune_ap, chosen_configuration=selected_variant,
                      training_seconds=total_seconds, batch_256_ms_median=float(np.median(latency)), batch_256_ms_p95=float(np.quantile(latency, .95)),
                      calibrator_standardized_coefficient=float(calibrator[-1].coef_[0, 0]))
        rows.append(result)
        bundles[slug] = bundle
        score_arrays[slug] = test_scores.tolist()
        joblib.dump(bundle, out / f'{slug}.joblib')
        print(f'  tune AP={tune_ap:.4f}; final test AP={result["average_precision"]:.4f}; {total_seconds:.1f}s', flush=True)
    # Selection is based only on the earlier tune period, never final test performance.
    champion = max((row for row in rows if row['name'] != 'Prevalence baseline'), key=lambda row: row['tune_ap'])
    bundle = bundles[champion['id']]
    validation = inputs['tune']
    # Fixed subset selected without labels to keep permutation cost bounded.
    subset = np.random.default_rng(SEED).choice(len(validation), min(15000, len(validation)), replace=False)
    if np.unique(y_tune[subset]).size == 2:
        scorer = lambda estimator, X, y: average_precision_score(y, raw_scores(estimator, X, bundle['anomaly']))
        importance = permutation_importance(bundle['model'], validation.iloc[subset], y_tune[subset], scoring=scorer, n_repeats=3, random_state=SEED, n_jobs=1)
        influence = sorted([{'feature': name, 'ap_drop': float(value), 'std': float(std)} for name, value, std in zip(FEATURES, importance.importances_mean, importance.importances_std)], key=lambda x: -x['ap_drop'])
    else:
        influence = []
    drift = [{'feature': name, 'psi': psi(inputs['train'][name], inputs['test'][name])} for name in FEATURES]
    drift.sort(key=lambda x: -x['psi'])
    case_positions = set()
    for scores in score_arrays.values():
        case_positions.update(np.argsort(-np.asarray(scores), kind='stable')[:35].tolist())
    cases = {}
    for pos in sorted(case_positions):
        row = parts['test'].iloc[pos]
        cases[row.transaction_id] = {feature: float(row[feature]) for feature in ['Time', 'Amount'] + [f'V{i}' for i in range(1, 29)]}
    versions = {}
    for name in ['numpy', 'pandas', 'scikit-learn', 'lightgbm', 'xgboost', 'joblib']:
        try:
            versions[name] = importlib.metadata.version(name)
        except importlib.metadata.PackageNotFoundError:
            versions[name] = 'not installed'
    source_hashes = {str(path.relative_to(root)).replace('\\', '/'): hashlib.sha256(path.read_bytes()).hexdigest() for path in sorted((root / 'fraudshield').glob('*.py'))}
    run = {
        'schema_version': 1, 'run_id': datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ'),
        'dataset': dataset, 'splits': split_summary, 'seed': SEED, 'models': rows,
        'champion_id': champion['id'], 'selection_rule': 'Highest uncalibrated average precision on tune period; no final-test-based selection.',
        'trials': trials, 'feature_importance': influence, 'drift': drift,
        'environment': {'python': platform.python_version(), 'platform': platform.platform(), 'machine': platform.machine(), 'cpu_count': os.cpu_count(), 'training_threads': 4, 'packages': versions},
        'source_hashes': source_hashes,
        'benchmark_protocol': {'split': 'Ordered time quantiles: train 50%, tune 15%, calibration 15%, test 20%; tied timestamps kept together.', 'calibration': 'Sigmoid fit on independent calibration period. Threshold from same period targets 1% alerts; actual test alert rate can differ.', 'uncertainty': f'{bootstrap_repeats} fixed non-overlapping-block resamples (40 contiguous blocks), percentile 95% AP interval; conditional on this fitted model.', 'latency': '12 local repetitions of a 256-row batch; includes feature validation and calibration; excludes network and disk.', 'average_precision': 'scikit-learn average_precision_score; step-weighted AP, not trapezoidal PR area.'},
        'limitations': [
            'Two days of European transactions from 2013 do not establish current bank or Indian payment performance.',
            'Original PCA fitting provenance is outside this experiment; entity identifiers and label delay are unavailable.',
            'PCA components cannot be translated into merchant, device, customer or behavioral explanations.',
            'Fraud labels are historical outcomes, not proof of criminal intent; scores require human review.',
            'Exposure is the sum of historical fraud transaction amounts; it is not realized savings or recoverable loss.',
            'Local results are not directly comparable to published random-split or Kaggle hidden-test scores.',
            'Block bootstrap intervals describe this short test period only; few frauds and dependent events limit precision.',
            'Protected attributes are unavailable; demographic fairness cannot be measured on this dataset.',
        ],
        'roadmap': [
            {'name': 'Card transactions', 'status': 'Measured in this run', 'dataset': 'ULB / Worldline'},
            {'name': 'Online payments', 'status': 'Next: rule acceptance and dataset acquisition required', 'dataset': 'IEEE-CIS / Vesta'},
            {'name': 'Account opening', 'status': 'Next: separate task and fairness protocol', 'dataset': 'Feedzai BAF (synthetic, derived from real data)'},
        ],
    }
    test = parts['test']
    payload = {'run': run, 'transactions': {'id': test.transaction_id.tolist(), 'time': test.Time.tolist(), 'amount': test.Amount.tolist(), 'label': test.Class.astype(int).tolist(), 'scores': score_arrays}, 'case_features': cases}
    serialized = json.dumps(payload, separators=(',', ':'), allow_nan=False)
    temporary = web / 'benchmark.tmp'
    temporary.write_text(serialized, encoding='utf-8')
    temporary.replace(web / 'benchmark.json')
    (out / 'run.json').write_text(json.dumps(run, indent=2, allow_nan=False), encoding='utf-8')
    pd.DataFrame(trials).to_csv(out / 'trials.csv', index=False)
    flat = pd.DataFrame([{k: value for k, value in row.items() if not isinstance(value, (dict, list))} for row in rows])
    flat.to_csv(web / 'model_metrics.csv', index=False)
    write_report(run, web / 'report.html')
    artifacts = {path.name: hashlib.sha256(path.read_bytes()).hexdigest() for path in out.glob('model-*.joblib')}
    (out / 'model_hashes.json').write_text(json.dumps(artifacts, indent=2), encoding='utf-8')
    print(f'Completed. Champion selected on tune: {champion["name"]}. Dashboard data: {len(serialized):,} bytes.', flush=True)
    return run


def write_report(run, path):
    from html import escape
    champion = next(m for m in run['models'] if m['id'] == run['champion_id'])
    table = ''.join(f'<tr><td>{escape(m["name"])}</td><td>{m["tune_ap"]:.4f}</td><td>{m["average_precision"]:.4f}</td><td>{m["roc_auc"]:.4f}</td><td>{m["top_1pct"]["recall"]:.1%}</td><td>{m["operating"]["precision"]:.1%}</td><td>{m["training_seconds"]:.1f}</td></tr>' for m in run['models'])
    splits = ''.join(f'<tr><td>{k}</td><td>{v["rows"]:,}</td><td>{v["frauds"]}</td><td>{v["time_min"]:,.0f}–{v["time_max"]:,.0f}</td></tr>' for k, v in run['splits'].items())
    notes = ''.join('<li>'+escape(x)+'</li>' for x in run['limitations'])
    protocol = ''.join(f'<p><b>{escape(k)}:</b> {escape(v)}</p>' for k, v in run['benchmark_protocol'].items())
    html = f'''<!doctype html><html lang="en"><meta charset="utf-8"><title>FraudShield benchmark report</title><style>body{{font:16px/1.6 system-ui;max-width:1100px;margin:50px auto;padding:0 25px;color:#182b35}}h1{{font-size:40px}}h2{{margin-top:40px}}table{{border-collapse:collapse;width:100%;font-size:14px}}td,th{{padding:10px;text-align:left;border-bottom:1px solid #d5dfe0}}.tag{{color:#087366}}@media print{{button{{display:none}}body{{margin:0}}}}</style><button onclick="window.print()">Print / save PDF</button><p class="tag">FRAUDSHIELD · MEASURED RESEARCH REPORT</p><h1>Card fraud, measured honestly.</h1><p>Run {escape(run['run_id'])}. Real anonymized ULB / Worldline transactions. {run['dataset']['raw_rows']:,} original rows; {run['dataset']['duplicates_removed']:,} exact duplicate rows removed.</p><h2>Decision brief</h2><p>{escape(champion['name'])} was selected using the tune period. On the final held-out test it achieved AP {champion['average_precision']:.4f}, with a conditional 95% block-bootstrap interval {champion['ap_ci95'][0]:.4f}–{champion['ap_ci95'][1]:.4f}. At a top-1% review budget its recall was {champion['top_1pct']['recall']:.1%}. This is a retrospective research benchmark, not approval for deployment.</p><h2>Data boundaries</h2><table><tr><th>Period</th><th>Rows</th><th>Frauds</th><th>Elapsed seconds</th></tr>{splits}</table><h2>Model benchmark</h2><p>Threshold precision uses the threshold set on calibration data. Top-1% recall ranks final-test transactions with a fixed review budget and is a different operating rule.</p><table><tr><th>Model</th><th>Tune AP</th><th>Test AP</th><th>ROC-AUC</th><th>Recall @ top 1%</th><th>Threshold precision</th><th>Train seconds</th></tr>{table}</table><h2>Protocol</h2>{protocol}<h2>Limits and decisions</h2><ul>{notes}</ul><h2>Reproducibility</h2><p>Seed: {run['seed']}. SHA-256: <code>{run['dataset']['sha256']}</code>.</p><pre>{escape(json.dumps(run['environment'], indent=2))}</pre><h2>Next datasets</h2><p>IEEE-CIS online payments requires competition-rule acceptance. Feedzai BAF is a separate synthetic account-opening task with its own temporal and fairness protocol. Neither is reported as measured here.</p><h2>Sources</h2><ul><li><a href="https://www.kaggle.com/datasets/mlg-ulb/creditcardfraud">ULB dataset owner data card</a></li><li><a href="https://www.tensorflow.org/tutorials/structured_data/imbalanced_data">TensorFlow public data mirror</a></li><li><a href="https://fraud-detection-handbook.github.io/fraud-detection-handbook/Chapter_5_ModelValidationAndSelection/ValidationStrategies.html">Fraud Detection Handbook: validation</a></li><li><a href="https://www.amazon.science/code-and-datasets/fdb-fraud-dataset-benchmark">Amazon Fraud Dataset Benchmark</a></li></ul></html>'''
    Path(path).write_text(html, encoding='utf-8')
