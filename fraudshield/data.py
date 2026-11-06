from pathlib import Path
import hashlib
import urllib.request

import numpy as np
import pandas as pd

SOURCE_URL = 'https://storage.googleapis.com/download.tensorflow.org/data/creditcard.csv'
RAW_FEATURES = [f'V{i}' for i in range(1, 29)] + ['Amount']
FEATURES = [f'V{i}' for i in range(1, 29)] + ['LogAmount']


def validate_features(frame):
    missing = set(RAW_FEATURES) - set(frame.columns)
    if missing:
        raise ValueError('Missing required columns: ' + ', '.join(sorted(missing)))
    try:
        values = frame[RAW_FEATURES].astype(float)
    except (ValueError, TypeError) as exc:
        raise ValueError('All input features must be numeric.') from exc
    if not np.isfinite(values.to_numpy()).all():
        raise ValueError('Features must be finite; missing values are not accepted.')
    if (values['Amount'] < 0).any():
        raise ValueError('Amount must be non-negative.')
    return values


def model_input(frame):
    values = validate_features(frame).copy()
    values['LogAmount'] = np.log1p(values.pop('Amount'))
    return values[FEATURES]


def load_card(path):
    path = Path(path)
    frame = pd.read_csv(path)
    validate_features(frame)
    if not {'Class', 'Time'} <= set(frame):
        raise ValueError('Card benchmark requires Class and Time columns.')
    if not frame['Class'].isin([0, 1]).all() or frame['Class'].nunique() != 2:
        raise ValueError('Class must contain both 0 and 1 only.')
    if not np.isfinite(frame['Time']).all() or (frame['Time'] < 0).any():
        raise ValueError('Time must be finite and non-negative.')
    duplicates = int(frame.duplicated().sum())
    frame = frame.drop_duplicates().sort_values('Time', kind='stable').reset_index(drop=True)
    frame['transaction_id'] = [f'ULB-{i:06d}' for i in range(len(frame))]
    with path.open('rb') as source:
        fingerprint = hashlib.file_digest(source, 'sha256').hexdigest()
    return frame, {
        'name': 'ULB / Worldline card transactions (2013)', 'kind': 'real, anonymized',
        'source_url': SOURCE_URL, 'source_card': 'https://www.kaggle.com/mlg-ulb/creditcardfraud/data',
        'sha256': fingerprint,
        'raw_rows': len(frame) + duplicates, 'rows': len(frame), 'duplicates_removed': duplicates,
        'frauds': int(frame.Class.sum()), 'prevalence': float(frame.Class.mean()),
        'currency': 'EUR', 'time_unit': 'Seconds since first observed transaction; not a calendar date',
    }


def temporal_splits(frame):
    cuts = frame.Time.quantile([0.50, 0.65, 0.80]).to_numpy()
    groups = np.searchsorted(cuts, frame.Time.to_numpy(), side='left')
    parts = {name: frame.loc[groups == i].copy() for i, name in enumerate(['train', 'tune', 'calibration', 'test'])}
    for name, part in parts.items():
        if len(part) < 100 or part.Class.nunique() < 2:
            raise ValueError(f'{name} needs at least 100 transactions and both classes.')
    for left, right in zip(list(parts.values()), list(parts.values())[1:]):
        if left.Time.max() >= right.Time.min():
            raise ValueError('Time boundary overlap detected.')
    return parts


def download(path):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        raise FileExistsError(f'{path} already exists; refusing to replace data.')
    temporary = path.with_suffix('.partial')
    try:
        with urllib.request.urlopen(SOURCE_URL, timeout=90) as response, temporary.open('wb') as out:
            import shutil
            shutil.copyfileobj(response, out)
        load_card(temporary)
        temporary.replace(path)
    finally:
        temporary.unlink(missing_ok=True)
