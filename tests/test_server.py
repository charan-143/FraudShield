import functools
import json
import io
import sys
import threading
import urllib.error
import urllib.request
from http.server import ThreadingHTTPServer
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pandas as pd
import pytest
from sklearn.dummy import DummyClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from fraudshield.data import RAW_FEATURES, model_input
from fraudshield.server import Handler, load_champion
from fraudshield.training import calibration_input


@pytest.fixture
def server(tmp_path):
    (tmp_path / 'web').mkdir()
    (tmp_path / 'web' / 'index.html').write_text('FraudShield')
    X = model_input(pd.DataFrame(np.zeros((4,29)),columns=RAW_FEATURES))
    estimator = DummyClassifier().fit(X,[0,0,1,0])
    calibrator = make_pipeline(StandardScaler(),LogisticRegression()).fit(calibration_input([.1,.2,.8,.9]),[0,0,1,1])
    bundle = {'model':estimator,'calibrator':calibrator,'anomaly':False,'threshold':.5,'name':'test model'}
    from fraudshield.reviews import ReviewStore
    factory = functools.partial(Handler,root=tmp_path,bundle=bundle,run={'run_id':'test'},score_lock=threading.Lock(),review_store=ReviewStore(tmp_path/'reviews.sqlite','a'*64,'test'),valid_cases={'ULB-000001'})
    class MemoryConnection:
        def __init__(self, request):
            self.input = io.BytesIO(request)
            self.output = bytearray()
        def makefile(self, *args, **kwargs):
            return self.input
        def sendall(self, data):
            self.output.extend(data)
    def client(path, body, headers):
        encoded = b'' if body is None else json.dumps(body).encode()
        values = {'Host':'127.0.0.1:8765','Content-Type':'application/json',**(headers or {})}
        values['Content-Length'] = str(len(encoded))
        method = 'GET' if body is None else 'POST'
        wire = (f'{method} {path} HTTP/1.0\r\n'+''.join(f'{k}: {v}\r\n' for k,v in values.items())+'\r\n').encode()+encoded
        connection = MemoryConnection(wire)
        factory(connection, ('127.0.0.1',0), SimpleNamespace(server_port=8765))
        head, payload = bytes(connection.output).split(b'\r\n\r\n',1)
        status = int(head.split()[1])
        return status, json.loads(payload) if b'Content-Type: application/json' in head else payload.decode()
    return client


def request(base,path='/api/score',body=None,headers=None):
    return base(path, body, headers)


def test_scoring_and_health(server):
    assert request(server,'/api/health')[1]['ready']
    row = dict.fromkeys(RAW_FEATURES,0)
    status,result=request(server,body={'transactions':[row]})
    assert status==200 and result['model']=='test model'
    assert 0 <= result['results'][0]['risk_probability'] <= 1
    assert request(server,'/')[0]==200
    assert request(server,'/../artifacts/run.json')[0]==404


@pytest.mark.parametrize('body',[
    {'transactions':[]},{'transactions':[{}]}, {'transactions':[dict.fromkeys(RAW_FEATURES,0)]*501},
    {'transactions':[dict.fromkeys(RAW_FEATURES,'0')]},
    {'transactions':[{**dict.fromkeys(RAW_FEATURES,0),'Amount':-1}]},
    {'transactions':[{**dict.fromkeys(RAW_FEATURES,0),'V1':float('nan')}]},
    {'transactions':[{**dict.fromkeys(RAW_FEATURES,0),'email':'personal@example.com'}]},
    {'transactions':[{**dict.fromkeys(RAW_FEATURES,0),'V1':True}]},
    {'transactions':[{**dict.fromkeys(RAW_FEATURES,0),'Time':{}}]},
    {'transactions':[{**dict.fromkeys(RAW_FEATURES,0),'Time':float('inf')}]},
    {'transactions':[{**dict.fromkeys(RAW_FEATURES,0),'Time':-1}]},
    {'transactions':None},[],
])
def test_invalid_scoring_payloads(server,body):
    assert request(server,body=body)[0]==400


def test_origin_host_and_media_type(server):
    body={'transactions':[dict.fromkeys(RAW_FEATURES,0)]}
    assert request(server,body=body,headers={'Origin':'https://evil.example'})[0]==403
    assert request(server,body=body,headers={'Host':'evil.example'})[0]==403
    assert request(server,body=body,headers={'Content-Type':'text/plain'})[0]==415


def test_model_hash_rejects_modified_pickle(tmp_path):
    out=tmp_path/'artifacts'
    out.mkdir()
    (out/'run.json').write_text(json.dumps({'champion_id':'model-0'}))
    (out/'model_hashes.json').write_text(json.dumps({'model-0.joblib':'invalid'}))
    (out/'model-0.joblib').write_bytes(b'not a trusted pickle')
    with pytest.raises(ValueError,match='integrity'):
        load_champion(tmp_path)


def test_research_review_endpoint_records_and_lists_without_payment_action(server):
    payload={'event_id':'ULB-000001','actor':'reviewer-01','disposition':'inconclusive','reason':'Need more evidence for this research review.'}
    status,value=request(server,'/api/reviews',body=payload)
    assert status==201 and value['event']['disposition']=='inconclusive'
    status,value=request(server,'/api/reviews?event_id=ULB-000001')
    assert status==200 and value['integrity']['valid'] and len(value['events'])==1
    assert request(server,'/api/reviews',body={**payload,'event_id':'ULB-999999'})[0]==400
    assert request(server,'/api/reviews',body=payload,headers={'Origin':'https://evil.example'})[0]==403
