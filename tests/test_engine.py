import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest
from sklearn.metrics import average_precision_score

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
if (ROOT / '.vendor').exists():
    sys.path.insert(0, str(ROOT / '.vendor'))
from fraudshield.data import RAW_FEATURES, model_input, temporal_splits, load_card
from fraudshield.metrics import operating_metrics, top_budget, budget_threshold, evaluate, psi


def frame(n=1000):
    values = pd.DataFrame(np.zeros((n, len(RAW_FEATURES))), columns=RAW_FEATURES)
    values['Time'] = np.arange(n)
    values['Class'] = (np.arange(n) % 7 == 0).astype(int)
    return values


def test_temporal_split_keeps_ties_and_prevents_future_overlap():
    values = frame()
    values['Time'] = np.arange(len(values)) // 3
    parts = temporal_splits(values)
    assert sum(map(len, parts.values())) == len(values)
    assert all(a.Time.max() < b.Time.min() for a, b in zip(list(parts.values()), list(parts.values())[1:]))
    assert all(set(part.Time).isdisjoint(other.Time) for i, part in enumerate(parts.values()) for j, other in enumerate(parts.values()) if i != j)


def test_loader_deduplicates_and_fingerprints(tmp_path):
    values = frame()
    values = pd.concat([values, values.iloc[[4]]])
    path = tmp_path / 'card.csv'
    values.to_csv(path, index=False)
    result, meta = load_card(path)
    assert len(result) == 1000 and meta['duplicates_removed'] == 1
    assert len(meta['sha256']) == 64


@pytest.mark.parametrize('bad', [np.nan, np.inf, -np.inf, -1])
def test_invalid_amount_rejected(bad):
    values = frame(1)
    values.loc[0, 'Amount'] = bad
    with pytest.raises(ValueError):
        model_input(values)


def test_feature_transform_has_no_label_or_absolute_time():
    values = frame(2)
    values['Amount'] = [0, 99]
    result = model_input(values)
    assert result.columns.tolist() == [f'V{i}' for i in range(1,29)] + ['LogAmount']
    assert result.LogAmount.iloc[1] == pytest.approx(np.log(100))
    with pytest.raises(ValueError, match='Missing'):
        model_input(values.drop(columns='V5'))


def test_confusion_exposure_and_boundary_equal_threshold():
    result = operating_metrics([1,0,1,0], [.8,.6,.2,.1], [100,50,70,20], .6)
    assert (result['tp'],result['fp'],result['fn'],result['tn']) == (1,1,1,1)
    assert result['captured_exposure'] == 100 and result['missed_exposure'] == 70
    assert result['precision'] == .5 and result['recall'] == .5


def test_top_budget_ties_do_not_use_labels():
    result = top_budget([0,1,1,1], [.5,.5,.5,.5], .25)
    assert result == {'k':1,'precision':0,'recall':0}
    assert budget_threshold([.5,.5,.5,.5], .25) == .5
    assert operating_metrics([0,1,1,1], [.5]*4, [1]*4, .5)['alerts'] == 4


def test_metrics_match_reference_and_shift_identity():
    y, scores = [0,1,0,1], [.1,.7,.2,.8]
    result = evaluate(y, scores, [1]*4, .5, uncertainty=False)
    assert result['average_precision'] == average_precision_score(y,scores)
    assert result['roc_auc'] == 1
    assert psi(np.arange(100), np.arange(100)) == pytest.approx(0)


def test_constant_predictor_keeps_calibration_evidence():
    result = evaluate([0,0,0,1], [.25]*4, [1]*4, .5, uncertainty=False)
    assert result['calibration'] == [{'predicted':.25,'observed':.25,'n':4}]


def test_estimator_spec_encodes_nonfinite_library_defaults():
    from fraudshield.training import estimator_spec
    assert json.dumps(estimator_spec({'missing':np.nan}), allow_nan=False) == '{"missing": {"special_float": "nan"}}'


def test_measured_export_is_aligned_and_selection_uses_tune():
    path = ROOT / 'web' / 'benchmark.json'
    if not path.exists():
        pytest.skip('Train real data to validate exported evidence.')
    payload = json.loads(path.read_text(encoding='utf-8'))
    run, tx = payload['run'], payload['transactions']
    n = run['splits']['test']['rows']
    assert len(tx['id']) == len(tx['label']) == len(tx['time']) == len(tx['amount']) == n
    assert sum(tx['label']) == run['splits']['test']['frauds']
    chosen = max((m for m in run['models'] if m['name'] != 'Prevalence baseline'), key=lambda m:m['tune_ap'])
    assert chosen['id'] == run['champion_id']
    for m in run['models']:
        assert len(tx['scores'][m['id']]) == n
        assert m['average_precision'] == pytest.approx(average_precision_score(tx['label'],tx['scores'][m['id']]))
        expected = operating_metrics(tx['label'],tx['scores'][m['id']],tx['amount'],m['threshold'])
        assert expected == m['operating']
