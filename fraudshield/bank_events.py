"""Point-in-time validation for authorized pseudonymous bank event extracts."""
from collections import defaultdict, deque, Counter
from datetime import datetime
from fractions import Fraction
from pathlib import Path
import hashlib
import json
import math

import pandas as pd

REQUIRED = ['event_id','event_time','entity_id','device_id','merchant_id','amount','currency','channel','country','confirmed_fraud','label_available_at']
MANIFEST_FIELDS = ['source_system','population','collection_start','collection_end','license_or_authority','feature_provenance','label_policy']


def aware_timestamp(value):
    if not isinstance(value,str) or not value:
        raise ValueError('Timestamps need ISO8601 text with an explicit timezone.')
    try:
        parsed = datetime.fromisoformat(value.replace('Z','+00:00'))
    except ValueError as exc:
        raise ValueError('Invalid ISO8601 timestamp.') from exc
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValueError('Timestamp timezone is required.')
    return pd.Timestamp(parsed).tz_convert('UTC')


def validate_events(frame):
    if set(REQUIRED)-set(frame) or frame.empty:
        raise ValueError('Nonempty bank event data with the documented required columns is required.')
    frame = frame.copy()
    if frame.event_id.isna().any() or frame.event_id.astype(str).duplicated().any():
        raise ValueError('Unique nonmissing event IDs are required.')
    for field in ['event_id','entity_id','device_id','merchant_id','channel','country','currency']:
        if frame[field].isna().any() or frame[field].astype(str).str.strip().eq('').any():
            raise ValueError(f'{field} must be nonempty.')
    if not frame.currency.astype(str).str.fullmatch(r'[A-Z]{3}').all():
        raise ValueError('Currency must be an uppercase three-letter code on every event.')
    frame['event_time'] = pd.to_datetime([aware_timestamp(value) for value in frame.event_time],utc=True)
    frame['label_available_at'] = pd.to_datetime([pd.NaT if pd.isna(value) or value=='' else aware_timestamp(value) for value in frame.label_available_at],utc=True)
    frame['amount'] = pd.to_numeric(frame.amount,errors='raise')
    if any(not math.isfinite(value) or value<0 for value in frame.amount):
        raise ValueError('Amount must be finite and nonnegative.')
    known = frame.confirmed_fraud.notna()
    if not frame.loc[known,'confirmed_fraud'].isin([0,1]).all():
        raise ValueError('Known outcomes must be binary 0/1.')
    if (known != frame.label_available_at.notna()).any():
        raise ValueError('Known label and label_available_at must be provided together; unknown outcomes remain missing.')
    if (frame.loc[known,'label_available_at'] < frame.loc[known,'event_time']).any():
        raise ValueError('Labels cannot be available before their event.')
    return frame.sort_values(['event_time','event_id'],kind='stable').reset_index(drop=True)


def behavioral_features(validated):
    histories = defaultdict(lambda:{'day':deque(),'hour':deque(),'total':Fraction(0),'devices':Counter(),'merchants':Counter()})
    output = []
    for timestamp,batch in validated.groupby('event_time',sort=True):
        for row in batch.itertuples():
            state = histories[(row.entity_id,row.currency)]
            history=state['day']
            while history and history[0][0] < timestamp-pd.Timedelta(hours=24):
                _,amount,device,merchant=history.popleft()
                state['total']-=Fraction(str(amount))
                for field,key in [('devices',device),('merchants',merchant)]:
                    state[field][key]-=1
                    if state[field][key]==0:del state[field][key]
            while state['hour'] and state['hour'][0]<timestamp-pd.Timedelta(hours=1):
                state['hour'].popleft()
            if not history:state['total']=Fraction(0)
            exact_mean=state['total']/len(history) if history else None
            try:
                total=float(state['total'])
                mean=float(exact_mean) if exact_mean is not None else None
                ratio=float(Fraction(str(row.amount))/exact_mean) if exact_mean and exact_mean>0 else None
            except OverflowError as exc:
                raise ValueError('Behavioral numeric aggregation overflow; inspect amount units and bounds.') from exc
            if not math.isfinite(total) or ratio is not None and not math.isfinite(ratio):
                raise ValueError('Behavioral numeric aggregation overflow; inspect amount units and bounds.')
            output.append({'event_id':row.event_id,'prior_transactions_1h':len(state['hour']),'prior_transactions_24h':len(history),
                           'prior_amount_24h':total,'prior_mean_amount_24h':mean,
                           'amount_to_prior_mean':ratio,
                           'new_device_in_24h':int(row.device_id not in state['devices']),
                           'new_merchant_in_24h':int(row.merchant_id not in state['merchants'])})
        # Only publish current batch to history after all simultaneous rows are scored.
        for row in batch.itertuples():
            state=histories[(row.entity_id,row.currency)]
            state['day'].append((timestamp,row.amount,row.device_id,row.merchant_id))
            state['hour'].append(timestamp)
            state['total']+=Fraction(str(row.amount))
            state['devices'][row.device_id]+=1
            state['merchants'][row.merchant_id]+=1
    return pd.DataFrame(output)


def matured_cohort(validated,start,end,labels_as_of):
    start,end,labels_as_of = map(aware_timestamp,[start,end,labels_as_of])
    if start>=end or labels_as_of<end:
        raise ValueError('Cohort must be a forward interval and labels_as_of cannot precede its end.')
    period = validated[(validated.event_time>=start)&(validated.event_time<end)]
    mature = period.label_available_at.notna() & (period.label_available_at<=labels_as_of)
    selected = period.loc[mature].copy()
    return selected, {'events':len(period),'mature_labels':len(selected),'excluded_unknown_or_delayed':int((~mature).sum()),
                      'start':start.isoformat(),'end':end.isoformat(),'labels_as_of':labels_as_of.isoformat()}


def validate_bank_file(path,manifest_path,output,period=None):
    manifest = json.loads(Path(manifest_path).read_text(encoding='utf-8'))
    if any(not isinstance(manifest.get(field),str) or not manifest[field].strip() for field in MANIFEST_FIELDS):
        raise ValueError('Provenance manifest fields must be populated; see bank_data_contract.md.')
    frame = validate_events(pd.read_csv(path,dtype={'event_id':str,'entity_id':str,'device_id':str,'merchant_id':str,'actual_loss':'string','recovered_amount':'string','review_cost':'string'}))
    declared_start,declared_end=aware_timestamp(manifest['collection_start']),aware_timestamp(manifest['collection_end'])
    if declared_start>frame.event_time.min() or declared_end<frame.event_time.max() or declared_start>declared_end:
        raise ValueError('Provenance collection window must cover every event timestamp.')
    features = behavioral_features(frame)
    from .assurance import financial_outcomes
    result = {'dataset_sha256':hashlib.sha256(Path(path).read_bytes()).hexdigest(),'manifest':manifest,'provenance_status':'user asserted, not independently verified',
              'performance_validation':'Not performed: contract, chronology and accounting validation only. No current-bank, Indian-payment or demographic-fairness performance claim.',
              'rows':len(frame),'entities':int(frame.entity_id.nunique()),'event_start':frame.event_time.min().isoformat(),'event_end':frame.event_time.max().isoformat(),
              'unknown_labels':int(frame.confirmed_fraud.isna().sum()),'financial_outcomes':financial_outcomes(frame),
              'feature_contract':'Earlier events only, same-timestamp exclusion; histories segregated by entity and currency.',
              'feature_examples':features.head(10).where(features.notna(),None).to_dict('records')}
    if period:
        _,result['maturity'] = matured_cohort(frame,period['start'],period['end'],period['labels_as_of'])
    # Normalization converts pandas NaN in optional example features to JSON null.
    def clean(value):
        if isinstance(value,float) and not math.isfinite(value): return None
        if isinstance(value,dict): return {key:clean(item) for key,item in value.items()}
        if isinstance(value,list): return [clean(item) for item in value]
        return value
    target=Path(output)
    if target.exists():
        raise FileExistsError('Validation output already exists; choose a new path.')
    target.write_text(json.dumps(clean(result),indent=2,allow_nan=False),encoding='utf-8')
    return clean(result)
