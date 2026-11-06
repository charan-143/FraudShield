"""Explicit evidence boundaries for fairness, uncertainty, comparisons and money."""
from decimal import Decimal, InvalidOperation
import math

import numpy as np
import pandas as pd
from sklearn.metrics import average_precision_score


def wilson(successes, total, z=1.95996398454):
    if total == 0:
        return None
    p = successes / total
    center = (p + z*z/(2*total)) / (1+z*z/total)
    half = z * math.sqrt(p*(1-p)/total + z*z/(4*total*total)) / (1+z*z/total)
    return [max(0.0, center-half), min(1.0, center+half)]


def group_audit(labels, scores, groups, threshold, min_class_count=30):
    labels, scores, groups = np.asarray(labels), np.asarray(scores, float), np.asarray(groups, str)
    if not (len(labels) == len(scores) == len(groups)) or not len(labels):
        raise ValueError('Aligned nonempty labels, scores and groups are required.')
    if not np.isin(labels, [0, 1]).all() or not np.isfinite(scores).all() or not 0 <= threshold <= 1:
        raise ValueError('Binary labels, finite scores and threshold in [0,1] are required.')
    rows = []
    for group in sorted(np.unique(groups)):
        mask = groups == group
        y, alert = labels[mask], scores[mask] >= threshold
        positive, negative = int(np.sum(y == 1)), int(np.sum(y == 0))
        tp, fp = int(np.sum(alert & (y == 1))), int(np.sum(alert & (y == 0)))
        rows.append({'group': group, 'n': int(mask.sum()), 'frauds': positive, 'legitimate': negative,
                     'alerts': int(alert.sum()), 'tp': tp, 'fp': fp,
                     'recall': tp/positive if positive else None, 'fpr': fp/negative if negative else None,
                     'recall_ci95': wilson(tp, positive), 'fpr_ci95': wilson(fp, negative),
                     'sufficient_class_counts': positive >= min_class_count and negative >= min_class_count})
    eligible = [r for r in rows if r['sufficient_class_counts']]
    return {'groups': rows, 'min_class_count': min_class_count,
            'recall_gap': max(r['recall'] for r in eligible)-min(r['recall'] for r in eligible) if len(eligible)>1 else None,
            'fpr_gap': max(r['fpr'] for r in eligible)-min(r['fpr'] for r in eligible) if len(eligible)>1 else None,
            'interpretation': 'Descriptive group error rates, not a fairness pass/fail decision. Wilson intervals assume independent records; dependence and label bias can invalidate that assumption. Small groups are retained but excluded from gap summaries.'}


COMPARISON_FIELDS = ['dataset_sha256', 'task', 'population', 'deduplication', 'split_fingerprint', 'feature_manifest_sha256', 'label_policy', 'metric_definition', 'search_budget', 'seed_policy']


def comparison_gate(local, reference):
    differences = []
    for field in COMPARISON_FIELDS:
        if field not in local or field not in reference or local[field] is None or reference[field] is None:
            differences.append({'field': field, 'reason': 'missing evidence'})
        elif local[field] != reference[field]:
            differences.append({'field': field, 'reason': 'protocol differs'})
    return {'comparable': not differences, 'differences': differences,
            'meaning': 'Matching asserted protocol fields only; not independent verification of dataset authenticity or published-score reproduction.'}


def cluster_ap_interval(labels, scores, clusters, repeats=300, min_clusters=20, seed=42):
    labels, scores, clusters = np.asarray(labels), np.asarray(scores,float), np.asarray(clusters,str)
    if not len(labels) or not (len(labels)==len(scores)==len(clusters)):
        raise ValueError('Aligned nonempty arrays required.')
    if not np.isin(labels,[0,1]).all() or not np.isfinite(scores).all():
        raise ValueError('Binary labels and finite scores required.')
    units = np.unique(clusters)
    if len(units) < min_clusters:
        return {'ci95': None, 'clusters': len(units), 'valid_resamples': 0, 'status': 'insufficient independent clusters; no interval reported'}
    lookup = {unit: np.flatnonzero(clusters==unit) for unit in units}
    rng, values = np.random.default_rng(seed), []
    for _ in range(repeats):
        indices = np.concatenate([lookup[unit] for unit in rng.choice(units, len(units), replace=True)])
        if len(np.unique(labels[indices]))==2:
            values.append(float(average_precision_score(labels[indices],scores[indices])))
    if len(values) < max(20, repeats//2):
        return {'ci95': None, 'clusters':len(units), 'valid_resamples':len(values), 'status':'insufficient valid resamples; no interval reported'}
    return {'ci95':np.quantile(values,[.025,.975]).tolist(),'clusters':len(units),'valid_resamples':len(values),'status':'conditional cluster bootstrap; assumes supplied units capture dependence'}


def financial_outcomes(records):
    required = {'currency','actual_loss','recovered_amount','review_cost','outcome_status'}
    if not required <= set(records):
        return {'status':'unavailable','reason':'Observed loss, recovery, review expense, currency and closed-outcome records are required. Transaction exposure is not a substitute.','currencies':[]}
    totals, closed, pending = {}, 0, 0
    for row in records.to_dict('records'):
        if row['outcome_status'] != 'closed':
            pending += 1
            continue
        currency = row['currency']
        if not isinstance(currency,str) or len(currency)!=3 or not currency.isalpha() or currency!=currency.upper():
            raise ValueError('Currency must be an uppercase three-letter code.')
        amounts = []
        for field in ['actual_loss','recovered_amount','review_cost']:
            try:
                value = Decimal(str(row[field]))
            except InvalidOperation as exc:
                raise ValueError(f'{field} must be a valid monetary value.') from exc
            if not value.is_finite() or value < 0:
                raise ValueError('Observed monetary values must be finite and nonnegative.')
            amounts.append(value)
        loss,recovered,cost = amounts
        if recovered > loss:
            raise ValueError('Recovered amount cannot exceed recorded actual loss.')
        total = totals.setdefault(currency,[Decimal(0),Decimal(0),Decimal(0)])
        for i,value in enumerate(amounts):
            total[i] += value
        closed += 1
    return {'status':'observed_closed_outcomes' if closed else 'no_closed_outcomes', 'closed_records':closed,'pending_records':pending,
            'currencies':[{'currency':currency,'actual_loss':str(values[0]),'recovered_amount':str(values[1]),'review_cost':str(values[2]),'net_realized_loss':str(values[0]-values[1]+values[2])} for currency,values in sorted(totals.items())],
            'interpretation':'Observed accounting only; no avoided-loss, causal savings, currency conversion or counterfactual benefit claim.'}
