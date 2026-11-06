"""A separate, explicitly synthetic eight-month account-opening stress test."""
import hashlib
import json
from pathlib import Path
import time

import joblib
import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.preprocessing import OneHotEncoder, StandardScaler
from sklearn.pipeline import make_pipeline
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import average_precision_score, roc_auc_score, brier_score_loss

from .assurance import group_audit, cluster_ap_interval, financial_outcomes, comparison_gate
from .metrics import budget_threshold, top_budget, operating_metrics
from .training import calibration_input, estimator_spec

CATEGORICAL = ['payment_type','employment_status','housing_status','source','device_os']
EXCLUDED = ['fraud_bool','month','customer_age','device_fraud_count']
SOURCE = 'https://www.kaggle.com/datasets/sgpjesus/bank-account-fraud-dataset-neurips-2022'
BAF_COLUMNS = ['fraud_bool','income','name_email_similarity','prev_address_months_count','current_address_months_count','customer_age','days_since_request','intended_balcon_amount','payment_type','zip_count_4w','velocity_6h','velocity_24h','velocity_4w','bank_branch_count_8w','date_of_birth_distinct_emails_4w','employment_status','credit_risk_score','email_is_free','housing_status','phone_home_valid','phone_mobile_valid','bank_months_count','has_other_cards','proposed_credit_limit','foreign_request','source','session_length_in_minutes','device_os','keep_alive_session','device_distinct_emails_8w','device_fraud_count','month']


def validate_baf_schema(frame):
    if set(frame.columns) != set(BAF_COLUMNS) or len(frame.columns) != len(BAF_COLUMNS) or frame.empty:
        raise ValueError('Exact original 32-column BAF Base.csv schema required; unexpected fields are not permitted predictors.')
    return frame[BAF_COLUMNS]


def encode_tree(train,other,features):
    result, mappings = {}, {}
    for name in features:
        if name in CATEGORICAL:
            mappings[name] = {value:i for i,value in enumerate(sorted(train[name].astype(str).unique()))}
    for key,frame in other.items():
        X = frame[features].copy()
        for name,mapping in mappings.items():
            X[name] = X[name].astype(str).map(mapping).fillna(-1).astype('int32')
        result[key] = X
    return result,mappings


def run_baf(path,root):
    from lightgbm import LGBMClassifier
    from threadpoolctl import threadpool_limits
    threadpool_limits(4)
    root=Path(root)
    out=root/'artifacts'/'baf'
    out.mkdir(exist_ok=True)
    frame=pd.read_csv(path)
    frame=validate_baf_schema(frame)
    if not frame.fraud_bool.isin([0,1]).all() or set(frame.month.unique())!=set(range(8)):
        raise ValueError('Expected binary labels and all eight months 0–7.')
    if frame.isna().any().any() or frame.duplicated().any():
        raise ValueError('Unexpected null or duplicate records; investigate rather than changing the protocol.')
    features=[name for name in BAF_COLUMNS if name not in EXCLUDED]
    numeric=[name for name in features if name not in CATEGORICAL]
    if not np.isfinite(frame[numeric].to_numpy()).all():
        raise ValueError('Nonfinite numeric features.')
    with Path(path).open('rb') as file:
        fingerprint=hashlib.file_digest(file,'sha256').hexdigest()
    folds, all_cases, final_bundle=[],[],None
    for test_month in [5,6,7]:
        parts={'train':frame[frame.month<=test_month-3], 'tune':frame[frame.month==test_month-2],
               'calibration':frame[frame.month==test_month-1], 'test':frame[frame.month==test_month]}
        if any(part.fraud_bool.nunique()!=2 for part in parts.values()):
            raise ValueError('Each fixed month cohort must contain both outcome classes.')
        X,mappings=encode_tree(parts['train'],parts,features)
        transforms=ColumnTransformer([('numeric',StandardScaler(),numeric),('categorical',OneHotEncoder(handle_unknown='ignore',sparse_output=True),CATEGORICAL)],sparse_threshold=1.0)
        candidates=[('Logistic baseline',make_pipeline(transforms,LogisticRegression(C=1,class_weight='balanced',max_iter=600,random_state=42))),
                    ('LightGBM',LGBMClassifier(n_estimators=250,num_leaves=15,learning_rate=.05,min_child_samples=80,reg_lambda=3,n_jobs=4,random_state=42,verbosity=-1)),
                    ('LightGBM weighted',LGBMClassifier(n_estimators=250,num_leaves=15,learning_rate=.05,min_child_samples=80,reg_lambda=3,n_jobs=4,random_state=42,verbosity=-1,class_weight='balanced'))]
        models=[]
        best=None
        print(f'BAF forward test month {test_month}',flush=True)
        for name,model in candidates:
            logistic=name=='Logistic baseline'
            input_data={key:parts[key][features] for key in parts} if logistic else X
            started=time.perf_counter()
            if logistic:
                model.fit(input_data['train'],parts['train'].fraud_bool)
            else:
                model.fit(input_data['train'],parts['train'].fraud_bool,categorical_feature=CATEGORICAL)
            train_seconds=time.perf_counter()-started
            tune_ap=float(average_precision_score(parts['tune'].fraud_bool,model.predict_proba(input_data['tune'])[:,1]))
            cal_raw=model.predict_proba(input_data['calibration'])[:,1]
            calibrator=make_pipeline(StandardScaler(),LogisticRegression(C=1,max_iter=500,random_state=42))
            calibrator.fit(calibration_input(cal_raw),parts['calibration'].fraud_bool)
            cal=calibrator.predict_proba(calibration_input(cal_raw))[:,1]
            threshold=budget_threshold(cal,.05)
            score=calibrator.predict_proba(calibration_input(model.predict_proba(input_data['test'])[:,1]))[:,1]
            y=parts['test'].fraud_bool.to_numpy()
            op=operating_metrics(y,score,np.zeros(len(y)),threshold)
            op.pop('captured_exposure');op.pop('missed_exposure')
            metrics={'name':name,'tune_ap':tune_ap,'test_ap':float(average_precision_score(y,score)),
                     'roc_auc':float(roc_auc_score(y,score)),'brier':float(brier_score_loss(y,score)),
                     'top_1pct':top_budget(y,score),'top_5pct':top_budget(y,score,.05),
                     'threshold':threshold,'operating':op,'training_seconds':train_seconds,'estimator_spec':estimator_spec(model)}
            models.append(metrics)
            if best is None or tune_ap>best['metrics']['tune_ap']:
                best={'metrics':metrics,'model':model,'calibrator':calibrator,'logistic':logistic,'scores':score,'mappings':mappings,'features':features}
            print(f'  {name}: tune AP {tune_ap:.4f}; test AP {metrics["test_ap"]:.4f}',flush=True)
        y=parts['test'].fraud_bool.to_numpy()
        groups=np.where(parts['test'].customer_age.to_numpy()>=50,'age 50+','age under 50')
        fairness=group_audit(y,best['scores'],groups,best['metrics']['threshold'])
        uncertainty=cluster_ap_interval(y,best['scores'],parts['test'].month.to_numpy())
        fold={'test_month':test_month,'split':{key:{'months':sorted(int(v) for v in part.month.unique()),'rows':len(part),'frauds':int(part.fraud_bool.sum())} for key,part in parts.items()},
              'models':models,'champion':best['metrics']['name'],'selection':'earlier tune-period AP only','age_audit':fairness,'ap_uncertainty':uncertainty}
        folds.append(fold)
        # Explain a tree challenger even if a linear baseline wins; name it explicitly.
        tree_name,tree=next((name,model) for name,model in candidates if name=='LightGBM')
        tree_raw=tree.predict_proba(X['test'])[:,1]
        selected=np.argsort(-tree_raw,kind='stable')[:8]
        contributions=tree.booster_.predict(X['test'].iloc[selected],pred_contrib=True)
        raw_margin=tree.booster_.predict(X['test'].iloc[selected],raw_score=True)
        if not np.allclose(contributions.sum(axis=1),raw_margin,atol=1e-6):
            raise ValueError('TreeSHAP additivity check failed.')
        for j,pos in enumerate(selected):
            source_row=parts['test'].iloc[pos]
            ranked=np.argsort(-np.abs(contributions[j,:-1]))[:6]
            all_cases.append({'case_id':f'BAF-m{test_month}-{int(parts["test"].index[pos])}', 'test_month':test_month,'explained_model':tree_name,
                              'historical_label':int(y[pos]),'raw_probability':float(tree_raw[pos]),'raw_margin':float(raw_margin[j]),'baseline_margin':float(contributions[j,-1]),
                              'all_contributions_sum':float(contributions[j,:-1].sum()),
                              'top_contributions':[{'feature':features[i],'value':str(source_row[features[i]]),'margin_contribution':float(contributions[j,i])} for i in ranked],
                              'interpretation':'Exact TreeSHAP contributions to this named tree model raw margin; not calibrated probabilities, causal reasons, criminal intent or necessarily the fold champion.'})
        final_bundle={key:value for key,value in best.items() if key not in ['scores','metrics']}
        final_bundle['threshold']=best['metrics']['threshold']
        final_bundle['name']=best['metrics']['name']
        if test_month==7:
            joblib.dump(final_bundle,out/'champion.joblib')
    period_ap=[next(m for m in fold['models'] if m['name']==fold['champion'])['test_ap'] for fold in folds]
    protocol={'dataset_sha256':fingerprint,'task':'account-opening-fraud','population':'BAF Base synthetic, derived from anonymized real data','deduplication':'none; duplicates rejected',
              'split_fingerprint':hashlib.sha256(json.dumps([fold['split'] for fold in folds],sort_keys=True).encode()).hexdigest(),
              'feature_manifest_sha256':hashlib.sha256(json.dumps(features).encode()).hexdigest(),'label_policy':'provided retrospective labels; actual delay unknown',
              'metric_definition':'sklearn average_precision_score','search_budget':'3 predeclared estimators per month; no random hyperparameter search','seed_policy':'42'}
    result={'schema_version':1,'dataset':{'name':'Feedzai BAF Base','kind':'synthetic account-opening data; not real card/UPI transactions','rows':len(frame),'frauds':int(frame.fraud_bool.sum()),'months':8,'sha256':fingerprint,'source':SOURCE},
            'protocol':protocol,'excluded_features':EXCLUDED,'features':features,'folds':folds,'explanation_cases':all_cases,
            'temporal_summary':{'test_months':[5,6,7],'ap_min':min(period_ap),'ap_max':max(period_ap),'ap_mean':float(np.mean(period_ap)),'interpretation':'Three forward-period observations, not a confidence interval or independent replications. Training windows overlap.'},
            'financial_outcomes':financial_outcomes(frame),'published_comparison':comparison_gate(protocol,{}),
            'limits':['Synthetic account-opening task does not validate real card/UPI or current Indian bank performance.',
                      'Month is the only time resolution. Original entities, label availability and generation provenance remain outside this experiment.',
                      'Age is excluded from prediction, not proof of fairness; other features can act as proxies.',
                      'Age-group Wilson intervals assume independent applications. No demographic fairness claim applies to ULB.',
                      'One test-month cluster per fold is insufficient for dependence-aware AP confidence intervals; no such interval is reported.',
                      'Source precomputed velocities are supplied synthetic features; their original point-in-time production provenance is not independently verified.']}
    (root/'web'/'assurance.json').write_text(json.dumps(result,separators=(',',':'),allow_nan=False),encoding='utf-8')
    (out/'run.json').write_text(json.dumps(result,indent=2,allow_nan=False),encoding='utf-8')
    (out/'model_hash.json').write_text(json.dumps({'champion.joblib':hashlib.sha256((out/'champion.joblib').read_bytes()).hexdigest()}),encoding='utf-8')
    print('BAF stress test complete; results remain separate from the real card experiment.',flush=True)
    return result
