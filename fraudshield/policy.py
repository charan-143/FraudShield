"""Calibration-only threshold selection; tier labels are simulation, not payment actions."""
import numpy as np
from sklearn.metrics import precision_recall_curve


def select_threshold(labels,scores,min_recall=.8,review_cost=3,missed_fraud_cost=100):
    y,p=np.asarray(labels),np.asarray(scores,float)
    if not len(y) or len(y)!=len(p) or set(np.unique(y))!={0,1} or not np.isfinite(p).all() or np.any((p<0)|(p>1)):
        raise ValueError('Both binary classes and aligned finite probabilities are required.')
    if not 0<min_recall<=1 or not np.isfinite([review_cost,missed_fraud_cost]).all() or min(review_cost,missed_fraud_cost)<0:
        raise ValueError('Recall and nonnegative finite costs required.')
    precision,recall,thresholds=precision_recall_curve(y,p)
    # Evaluate complete tied-score groups, never selecting individual tied rows using labels.
    order=np.argsort(-p,kind='stable')
    unique_ends=np.r_[np.flatnonzero(np.diff(p[order])!=0),len(p)-1]
    tp=np.cumsum(y[order])[unique_ends]
    alerts=unique_ends+1
    fn=y.sum()-tp
    eligible=np.flatnonzero(tp/y.sum()>=min_recall)
    costs=alerts*review_cost+fn*missed_fraud_cost
    chosen=min(eligible,key=lambda i:(costs[i],alerts[i]))
    return {'threshold':float(p[order][unique_ends[chosen]]),'calibration_recall':float(tp[chosen]/y.sum()),
            'calibration_precision':float(tp[chosen]/alerts[chosen]),'calibration_alerts':int(alerts[chosen]),
            'calibration_assumed_cost':float(costs[chosen]),'min_calibration_recall':min_recall,
            'assumptions':{'eur_per_review':review_cost,'eur_per_missed_fraud':missed_fraud_cost},
            'selection':'Minimum empirical assumed cost subject to calibration recall floor; ties prefer fewer alerts. No test labels used.'}


def tier_counts(scores,low,high):
    p=np.asarray(scores,float)
    if not 0<=low<=high<=1 or not np.isfinite(p).all() or np.any((p<0)|(p>1)):
        raise ValueError('Ordered probability cutoffs and finite probabilities required.')
    return {'low_risk':int((p<low).sum()),'step_up_candidate':int(((p>=low)&(p<high)).sum()),'analyst_review_candidate':int((p>=high).sum())}


def customer_frontier(labels, scores, recall_targets=(.7,.8,.85,.9,.95), max_fpr=.005):
    """Minimum-interruption cutoffs at recall floors; calibration data only.

    FPR is a transaction-level friction proxy, not customer satisfaction.
    Complete score ties are included; infeasible targets remain explicit.
    """
    # Reuse the input contract without making its cost-selected policy our choice.
    select_threshold(labels, scores)
    if not np.isfinite(max_fpr) or not 0 <= max_fpr <= 1:
        raise ValueError('FPR cap must be between zero and one.')
    y,p=np.asarray(labels),np.asarray(scores,float)
    order=np.argsort(-p,kind='stable')
    ends=np.r_[np.flatnonzero(np.diff(p[order])!=0),len(p)-1]
    tp=np.cumsum(y[order])[ends]; alerts=ends+1; fp=alerts-tp
    rows=[]
    for target in recall_targets:
        if not np.isfinite(target) or not 0 < target <= 1:
            raise ValueError('Recall targets must be in (0,1].')
        i=int(np.flatnonzero(tp/y.sum()>=target)[0])
        rows.append({'recall_target':float(target),'threshold':float(p[order][ends[i]]),
                     'recall':float(tp[i]/y.sum()),'precision':float(tp[i]/alerts[i]),
                     'tp':int(tp[i]),'fp':int(fp[i]),'alerts':int(alerts[i]),
                     'fpr':float(fp[i]/(len(y)-y.sum())),
                     'legitimate_interruptions_per_10000':float(10000*fp[i]/(len(y)-y.sum())),
                     'within_friction_cap':bool(fp[i]/(len(y)-y.sum())<=max_fpr)})
    return {'selection_data':'calibration only','max_fpr':max_fpr,'rows':rows,
            'interpretation':'Each row minimizes flagged transactions at its recall floor, including complete score ties. All flagged legitimate transactions count as interruptions, including simulated step-up. Customer satisfaction and authentication outcomes are unmeasured.'}
