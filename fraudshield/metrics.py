import numpy as np
from sklearn.metrics import average_precision_score, roc_auc_score, brier_score_loss, precision_recall_curve, roc_curve


def operating_metrics(y, scores, amounts, threshold):
    y, scores, amounts = np.asarray(y, int), np.asarray(scores, float), np.asarray(amounts, float)
    if not (len(y) == len(scores) == len(amounts)) or not len(y):
        raise ValueError('Non-empty aligned labels, scores and amounts are required.')
    if not 0 <= threshold <= 1 or not np.isfinite(scores).all() or not np.isfinite(amounts).all():
        raise ValueError('Scores and amounts must be finite and threshold must be in [0,1].')
    alert = scores >= threshold
    tp = int(np.sum(alert & (y == 1)))
    fp = int(np.sum(alert & (y == 0)))
    fn = int(np.sum(~alert & (y == 1)))
    tn = int(np.sum(~alert & (y == 0)))
    return dict(tp=tp, fp=fp, fn=fn, tn=tn, alerts=tp + fp,
                precision=tp / max(tp + fp, 1), recall=tp / max(tp + fn, 1),
                fpr=fp / max(fp + tn, 1), alert_rate=(tp + fp) / len(y),
                captured_exposure=float(amounts[alert & (y == 1)].sum()),
                missed_exposure=float(amounts[~alert & (y == 1)].sum()))


def budget_threshold(scores, budget=0.01):
    # Ties may exceed the nominal review budget; report the actual alert count.
    scores = np.asarray(scores, float)
    if not len(scores) or not 0 < budget <= 1 or not np.isfinite(scores).all():
        raise ValueError('Budget must be in (0,1] and scores finite and non-empty.')
    k = max(1, int(np.ceil(len(scores) * budget)))
    return float(np.sort(scores)[-k])


def top_budget(y, scores, budget=0.01):
    # Stable index breaks tied scores deterministically; no labels in ranking.
    k = max(1, int(np.ceil(len(y) * budget)))
    selected = np.argsort(-np.asarray(scores), kind='stable')[:k]
    caught = int(np.asarray(y)[selected].sum())
    return {'k': k, 'precision': caught / k, 'recall': caught / max(int(np.sum(y)), 1)}


def block_bootstrap_ap(y, scores, repeats=150, seed=42):
    # Contiguous blocks preserve some temporal dependence, but two days cannot establish long-term uncertainty.
    y, scores = np.asarray(y), np.asarray(scores)
    blocks = np.array_split(np.arange(len(y)), min(40, len(y)))
    rng, values = np.random.default_rng(seed), []
    for _ in range(repeats):
        idx = np.concatenate([blocks[i] for i in rng.integers(0, len(blocks), len(blocks))])
        if np.unique(y[idx]).size == 2:
            values.append(float(average_precision_score(y[idx], scores[idx])))
    return np.quantile(values, [0.025, 0.975]).tolist() if values else [None, None]


def evaluate(y, scores, amounts, threshold, uncertainty=True):
    y, scores = np.asarray(y), np.asarray(scores)
    p, r, _ = precision_recall_curve(y, scores)
    fpr, tpr, _ = roc_curve(y, scores)
    def downsample(x, z, limit=180):
        idx = np.unique(np.linspace(0, len(x) - 1, min(limit, len(x))).astype(int))
        return [[float(x[i]), float(z[i])] for i in idx]
    calibration = []
    edges = np.unique(np.quantile(scores, np.linspace(0, 1, 11)))
    if len(edges) == 1:
        calibration.append({'predicted': float(scores.mean()), 'observed': float(y.mean()), 'n': len(y)})
    for i in range(len(edges) - 1):
        mask = (scores >= edges[i]) & ((scores <= edges[i+1]) if i == len(edges)-2 else (scores < edges[i+1]))
        if mask.any():
            calibration.append({'predicted': float(scores[mask].mean()), 'observed': float(y[mask].mean()), 'n': int(mask.sum())})
    return {
        'average_precision': float(average_precision_score(y, scores)),
        'ap_ci95': block_bootstrap_ap(y, scores) if uncertainty else [None, None],
        'roc_auc': float(roc_auc_score(y, scores)), 'brier': float(brier_score_loss(y, scores)),
        'top_1pct': top_budget(y, scores), 'top_05pct': top_budget(y, scores, 0.005),
        'recall_at_fpr_001': float(tpr[fpr <= 0.001].max(initial=0)),
        'threshold': threshold, 'operating': operating_metrics(y, scores, amounts, threshold),
        'pr_curve': downsample(r, p), 'roc_curve': downsample(fpr, tpr), 'calibration': calibration,
    }


def psi(reference, current):
    reference, current = np.asarray(reference), np.asarray(current)
    edges = np.unique(np.quantile(reference, np.linspace(0, 1, 11)))
    if len(edges) < 2:
        return 0.0
    edges[0], edges[-1] = -np.inf, np.inf
    a = np.maximum(np.histogram(reference, edges)[0] / len(reference), 1e-6)
    b = np.maximum(np.histogram(current, edges)[0] / len(current), 1e-6)
    return float(np.sum((b - a) * np.log(b / a)))
