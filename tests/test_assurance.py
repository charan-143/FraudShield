import json
from pathlib import Path
import sys
import sqlite3

import numpy as np
import pandas as pd
import pytest

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from fraudshield.assurance import group_audit,comparison_gate,cluster_ap_interval,financial_outcomes,COMPARISON_FIELDS
from fraudshield.bank_events import validate_events,behavioral_features,matured_cohort,aware_timestamp
from fraudshield.reviews import ReviewStore


def events():
    return pd.DataFrame([
        {'event_id':'a','event_time':'2026-01-01T00:00:00Z','entity_id':'e1','device_id':'d1','merchant_id':'m1','amount':100,'currency':'INR','channel':'card','country':'IN','confirmed_fraud':1,'label_available_at':'2026-01-05T00:00:00Z'},
        {'event_id':'b','event_time':'2026-01-01T00:00:00Z','entity_id':'e1','device_id':'d2','merchant_id':'m2','amount':50,'currency':'INR','channel':'card','country':'IN','confirmed_fraud':0,'label_available_at':'2026-01-02T00:00:00Z'},
        {'event_id':'c','event_time':'2026-01-01T00:30:00Z','entity_id':'e1','device_id':'d1','merchant_id':'m1','amount':200,'currency':'INR','channel':'card','country':'IN','confirmed_fraud':np.nan,'label_available_at':None},
    ])


def test_simultaneous_events_and_future_events_do_not_leak():
    values=validate_events(events())
    features=behavioral_features(values)
    assert features.prior_transactions_24h.tolist()==[0,0,2]
    assert features.prior_amount_24h.tolist()==[0,0,150]
    assert features.new_device_in_24h.tolist()==[1,1,0]
    extended=pd.concat([events(),events().iloc[[0]].assign(event_id='future',event_time='2026-02-01T00:00:00Z',label_available_at='2026-02-02T00:00:00Z')])
    pd.testing.assert_frame_equal(features,behavioral_features(validate_events(extended)).iloc[:3])


def test_labels_are_selected_by_availability_not_event_time():
    selected,report=matured_cohort(validate_events(events()),'2026-01-01T00:00:00Z','2026-01-02T00:00:00Z','2026-01-03T00:00:00Z')
    assert selected.event_id.tolist()==['b']
    assert report['excluded_unknown_or_delayed']==2


def test_currency_histories_and_entity_histories_separate():
    rows=events()
    rows.loc[1,'currency']='EUR'
    features=behavioral_features(validate_events(rows))
    assert features.prior_amount_24h.iloc[2]==100
    rows.loc[2,'entity_id']='another'
    assert behavioral_features(validate_events(rows)).prior_transactions_24h.iloc[2]==0


def test_small_retained_history_is_not_lost_when_large_amount_expires():
    rows=events()
    rows['confirmed_fraud']=np.nan
    rows['label_available_at']=None
    rows['event_time']=['2026-01-01T00:00:00Z','2026-01-01T01:00:00Z','2026-01-02T00:30:00Z']
    rows['amount']=[1e16,.01,1]
    features=behavioral_features(validate_events(rows))
    assert features.prior_amount_24h.iloc[2]==.01


@pytest.mark.parametrize('bad',['2026-01-01T00:00:00','garbage',''])
def test_explicit_timezone_required(bad):
    with pytest.raises(ValueError):aware_timestamp(bad)


def test_known_labels_need_valid_availability():
    rows=events()
    rows.loc[0,'label_available_at']=None
    with pytest.raises(ValueError,match='provided together'):validate_events(rows)


def test_currency_contract_applies_even_without_closed_losses():
    rows=events()
    rows.loc[0,'currency']='inr'
    with pytest.raises(ValueError,match='Currency'):validate_events(rows)


def test_financial_csv_precision_is_preserved_before_accounting(tmp_path):
    from fraudshield.bank_events import validate_bank_file,MANIFEST_FIELDS
    rows=events().iloc[:1].copy()
    rows['actual_loss']='9007199254740992.01'
    rows['recovered_amount']='0.01'
    rows['review_cost']='0.10'
    rows['outcome_status']='closed'
    source=tmp_path/'bank.csv'
    rows.to_csv(source,index=False)
    manifest=tmp_path/'manifest.json'
    meta=dict.fromkeys(MANIFEST_FIELDS,'test synthetic fixture, not a real bank')
    meta.update(collection_start='2026-01-01T00:00:00Z',collection_end='2026-01-02T00:00:00Z')
    manifest.write_text(json.dumps(meta))
    result=validate_bank_file(source,manifest,tmp_path/'report.json')
    assert result['financial_outcomes']['currencies'][0]['net_realized_loss']=='9007199254740992.10'


def test_baf_schema_rejects_label_derived_or_missing_predictors():
    from fraudshield.baf import BAF_COLUMNS,validate_baf_schema
    source=pd.DataFrame([dict.fromkeys(BAF_COLUMNS,0)])
    assert list(validate_baf_schema(source).columns)==BAF_COLUMNS
    with pytest.raises(ValueError):validate_baf_schema(source.assign(future_fraud=1))
    with pytest.raises(ValueError):validate_baf_schema(source.drop(columns='velocity_6h'))


def test_financial_outcomes_use_decimal_closed_records_and_separate_currency():
    records=pd.DataFrame([
        {'currency':'INR','actual_loss':'0.10','recovered_amount':'0.00','review_cost':'0.20','outcome_status':'closed'},
        {'currency':'INR','actual_loss':'100.00','recovered_amount':'30.00','review_cost':'5.00','outcome_status':'closed'},
        {'currency':'EUR','actual_loss':'200','recovered_amount':'150','review_cost':'2','outcome_status':'closed'},
        {'currency':'INR','actual_loss':None,'recovered_amount':None,'review_cost':None,'outcome_status':'pending'},
    ])
    result=financial_outcomes(records)
    assert result['closed_records']==3 and result['pending_records']==1
    by_currency={row['currency']:row for row in result['currencies']}
    assert by_currency['INR']['net_realized_loss']=='75.30'
    assert by_currency['EUR']['net_realized_loss']=='52'
    assert financial_outcomes(pd.DataFrame({'Amount':[100]}))['status']=='unavailable'
    records.loc[0,'recovered_amount']='2'
    with pytest.raises(ValueError):financial_outcomes(records)


def test_fairness_small_groups_are_not_hidden_or_used_for_gap():
    audit=group_audit([0,1,0,1],[.9,.8,.2,.1],['a','a','b','b'],.5,min_class_count=2)
    assert len(audit['groups'])==2 and audit['recall_gap'] is None
    assert audit['groups'][0]['fpr']==1
    assert audit['groups'][0]['recall_ci95'] is not None


def test_few_clusters_and_one_class_resampling_withhold_interval():
    result=cluster_ap_interval([0,1],[.1,.9],['month7']*2)
    assert result['ci95'] is None
    result=cluster_ap_interval([0]*40,np.zeros(40),list(map(str,range(40))),repeats=30)
    assert result['ci95'] is None and result['valid_resamples']==0


def test_protocol_gate_rejects_missing_and_different_splits():
    protocol=dict.fromkeys(COMPARISON_FIELDS,'same')
    assert comparison_gate(protocol,protocol)['comparable']
    assert not comparison_gate(protocol,{})['comparable']
    assert not comparison_gate(protocol,{**protocol,'split_fingerprint':'different'})['comparable']


def test_review_store_is_append_only_with_verifiable_hash_chain(tmp_path):
    store=ReviewStore(tmp_path/'reviews.sqlite','a'*64,'test')
    store.append('ULB-123456','reviewer-01','inconclusive','Need more account history.')
    store.append('ULB-123456','reviewer-02','escalate_for_review','Refer to a second reviewer.')
    assert store.verify()['valid'] and len(store.history('ULB-123456'))==2
    with store.connect() as db:
        with pytest.raises(sqlite3.IntegrityError):db.execute('DELETE FROM review_events')
    with pytest.raises(ValueError):store.append('ULB-123456','real@email.com','inconclusive','Do not store personal identity.')
    with pytest.raises(ValueError):store.append('ULB-123456','reviewer-01','criminal','Unsupported legal decision.')
    with pytest.raises(ValueError,match='another dataset or run'):ReviewStore(tmp_path/'reviews.sqlite','b'*64,'test')
    with pytest.raises(ValueError,match='another dataset or run'):ReviewStore(tmp_path/'reviews.sqlite','a'*64,'different-run')


def test_baf_export_does_not_pool_tasks_or_invent_uncertainty():
    path=ROOT/'web'/'assurance.json'
    if not path.exists():pytest.skip('Generate the separate BAF study first.')
    run=json.loads(path.read_text(encoding='utf-8'))
    assert run['dataset']['kind'].startswith('synthetic')
    assert run['excluded_features']==['fraud_bool','month','customer_age','device_fraud_count']
    for fold in run['folds']:
        assert fold['champion']==max(fold['models'],key=lambda m:m['tune_ap'])['name']
        assert fold['split']['train']['months'][-1]<fold['split']['tune']['months'][0]<fold['split']['calibration']['months'][0]<fold['test_month']
        assert fold['ap_uncertainty']['ci95'] is None
    assert run['financial_outcomes']['status']=='unavailable'
    for case in run['explanation_cases']:
        assert case['raw_margin']==pytest.approx(case['baseline_margin']+case['all_contributions_sum'],abs=1e-6)
