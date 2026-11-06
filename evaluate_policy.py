from pathlib import Path
import json
import sys
ROOT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT/'.vendor'))
from fraudshield.data import load_card,temporal_splits
from fraudshield.server import load_champion
from fraudshield.training import predict_bundle
from fraudshield.metrics import operating_metrics
from fraudshield.policy import select_threshold,tier_counts,customer_frontier

def evaluate():
    bundle,run=load_champion(ROOT)
    frame,meta=load_card(ROOT/'data'/'creditcard.csv')
    if meta['sha256']!=run['dataset']['sha256']:raise ValueError('Dataset fingerprint mismatch.')
    parts=temporal_splits(frame)
    cal=parts['calibration'];test=parts['test']
    cp=predict_bundle(bundle,cal);tp=predict_bundle(bundle,test)
    policy=select_threshold(cal.Class,cp)
    frontier=customer_frontier(cal.Class,cp)
    # Research target fixed before this run; never relax constraints using test labels.
    balanced=next(r for r in frontier['rows'] if r['recall_target']==.8)
    frontier['research_target_recall']=.8
    frontier['status']='feasible_on_calibration' if balanced['within_friction_cap'] else 'infeasible_on_calibration'
    frontier['target_test_diagnostic']=operating_metrics(test.Class,tp,test.Amount,balanced['threshold'])
    frontier['promotion']='Not promoted. Previously inspected test is retrospective; new forward data and measured customer friction are required.'
    old=operating_metrics(test.Class,tp,test.Amount,bundle['threshold'])
    new=operating_metrics(test.Class,tp,test.Amount,policy['threshold'])
    low=min(bundle['threshold'],policy['threshold']);high=max(bundle['threshold'],policy['threshold'])
    result={'model':bundle['name'],'dataset_sha256':meta['sha256'],'run_id':run['run_id'],
        'policy':policy,'customer_balance':frontier,'baseline_test':old,'candidate_test':new,
        'false_positive_change':new['fp']-old['fp'],'fraud_captured_change':new['tp']-old['tp'],
        'tiers':{'low_cutoff':low,'high_cutoff':high,'counts':tier_counts(tp,low,high),
                 'meaning':'Simulated recommendations only. Step-up success, abandonment and fraud prevention are unmeasured. No authentication or payment action is integrated.'},
        'limits':['The existing test has already been inspected in earlier development; this is a retrospective policy comparison, not new independent validation.',
                  'Recall floor applies to calibration, not a guarantee on future/test transactions.',
                  'Costs are explicit scenario assumptions, not observed losses or realized savings.',
                  'Threshold changes do not improve probability ranking or AP. No model retraining is claimed.',
                  'ULB lacks merchant/category/device/entity histories. Existing bank-data adapter can compute point-in-time context only when authorized data provides it.']}
    (ROOT/'web'/'policy.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
    print(json.dumps(result,indent=2))
    return result

if __name__=='__main__':evaluate()
