from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
import hashlib
import json
import math
import threading
from urllib.parse import urlparse, parse_qs

import joblib
import numpy as np
import pandas as pd

from .training import predict_bundle


def load_champion(root):
    root = Path(root)
    run = json.loads((root / 'artifacts' / 'run.json').read_text(encoding='utf-8'))
    name = run['champion_id'] + '.joblib'
    path = root / 'artifacts' / name
    hashes = json.loads((root / 'artifacts' / 'model_hashes.json').read_text(encoding='utf-8'))
    if hashlib.sha256(path.read_bytes()).hexdigest() != hashes.get(name):
        raise ValueError('Model integrity check failed. Retrain before serving.')
    # Only load artifacts created locally by this pipeline; hashes do not make untrusted pickle safe.
    return joblib.load(path), run


class Handler(SimpleHTTPRequestHandler):
    def __init__(self, *args, root, bundle, run, score_lock, review_store=None, valid_cases=None, **kwargs):
        self.bundle, self.run, self.score_lock = bundle, run, score_lock
        self.review_store, self.valid_cases = review_store, valid_cases or set()
        super().__init__(*args, directory=str(Path(root) / 'web'), **kwargs)

    def end_headers(self):
        self.send_header('X-Content-Type-Options', 'nosniff')
        self.send_header('X-Frame-Options', 'DENY')
        self.send_header('Referrer-Policy', 'no-referrer')
        self.send_header('Cache-Control', 'no-cache')
        super().end_headers()

    def list_directory(self, path):
        self.send_error(404)
        return None

    def json_response(self, status, value):
        encoded = json.dumps(value, allow_nan=False).encode()
        self.send_response(status)
        self.send_header('Content-Type', 'application/json; charset=utf-8')
        self.send_header('Content-Length', str(len(encoded)))
        self.end_headers()
        self.wfile.write(encoded)

    def trusted_host(self):
        return self.headers.get('Host') in {f'localhost:{self.server.server_port}', f'127.0.0.1:{self.server.server_port}'}

    def do_GET(self):
        if not self.trusted_host():
            return self.json_response(403, {'error': 'Loopback Host header required.'})
        if urlparse(self.path).path == '/api/health':
            return self.json_response(200, {'ready': True, 'model': self.bundle['name'], 'run_id': self.run['run_id'], 'max_rows': 500, 'reviews_available': self.review_store is not None})
        if urlparse(self.path).path == '/api/reviews':
            if self.review_store is None:
                return self.json_response(503, {'error':'Local review store unavailable.'})
            event_id=parse_qs(urlparse(self.path).query).get('event_id',[''])[0]
            if event_id not in self.valid_cases:
                return self.json_response(400, {'error':'Choose a transaction in the current held-out study.'})
            return self.json_response(200, {'events':self.review_store.history(event_id),'integrity':self.review_store.verify()})
        super().do_GET()

    def do_POST(self):
        if not self.trusted_host():
            return self.json_response(403, {'error': 'Loopback Host header required.'})
        if self.path not in {'/api/score','/api/reviews'}:
            return self.json_response(404, {'error': 'Unknown endpoint.'})
        origin = self.headers.get('Origin')
        if origin and origin not in {f'http://localhost:{self.server.server_port}', f'http://127.0.0.1:{self.server.server_port}'}:
            return self.json_response(403, {'error': 'Only same-origin local scoring is allowed.'})
        try:
            if self.headers.get('Content-Type', '').split(';')[0].strip() != 'application/json':
                return self.json_response(415, {'error': 'Expected application/json.'})
            try:
                length = int(self.headers.get('Content-Length', '0'))
            except ValueError:
                return self.json_response(413, {'error': 'Content-Length must be a valid integer.'})
            if not 0 < length <= 1_000_000:
                return self.json_response(413, {'error': 'Body must be between 1 byte and 1 MB.'})
            value = json.loads(self.rfile.read(length))
            if self.path == '/api/reviews':
                if self.review_store is None:
                    return self.json_response(503, {'error':'Local review store unavailable.'})
                if not isinstance(value,dict) or set(value) != {'event_id','actor','disposition','reason'}:
                    raise ValueError('Expected event_id, actor, disposition and reason only.')
                if value['event_id'] not in self.valid_cases:
                    raise ValueError('Choose a transaction in the current held-out study.')
                event=self.review_store.append(**value)
                return self.json_response(201, {'event':event,'meaning':'Research disposition recorded; no payment action or criminal finding.'})
            if not isinstance(value, dict) or set(value) != {'transactions'}:
                raise ValueError('Expected one transactions array.')
            records = value['transactions']
            if not isinstance(records, list) or not 1 <= len(records) <= 500 or not all(isinstance(row, dict) for row in records):
                raise ValueError('Send 1–500 transaction objects.')
            frame = pd.DataFrame(records)
            from .data import RAW_FEATURES
            if not set(frame).issubset(set(RAW_FEATURES) | {'Time'}):
                raise ValueError('Only V1–V28, Amount and optional Time are accepted. Do not send personal information.')
            if any(not isinstance(v, (int, float)) or isinstance(v, bool) or not math.isfinite(v) for row in records for v in row.values()):
                raise ValueError('Every accepted field must be a finite JSON number.')
            if any(row.get('Time', 0) < 0 for row in records):
                raise ValueError('Optional Time must be non-negative.')
            with self.score_lock:
                probabilities = predict_bundle(self.bundle, frame)
            self.json_response(200, {'model': self.bundle['name'], 'run_id': self.run['run_id'], 'threshold': self.bundle['threshold'], 'results': [{'row': i, 'risk_probability': float(p), 'review': bool(p >= self.bundle['threshold'])} for i, p in enumerate(probabilities)], 'warning': 'Research model trained on anonymized 2013 European card transactions. Out-of-distribution scoring is not validated.'})
        except (ValueError, TypeError, KeyError, UnicodeDecodeError, OverflowError) as exc:
            self.json_response(400, {'error': str(exc)})

    def do_HEAD(self):
        if not self.trusted_host():
            self.send_error(403, 'Loopback Host header required.')
            return
        super().do_HEAD()


def serve(root, port=8765):
    bundle, run = load_champion(root)
    from .reviews import ReviewStore
    payload=json.loads((Path(root)/'web'/'benchmark.json').read_text(encoding='utf-8'))
    valid_cases=set(payload['transactions']['id'])
    del payload
    store=ReviewStore(Path(root)/'local-state'/'reviews'/run['dataset']['sha256']/(run['run_id']+'.sqlite'),run['dataset']['sha256'],run['run_id'])
    if not store.verify()['valid']:
        raise ValueError('Review audit integrity check failed.')
    factory = partial(Handler, root=root, bundle=bundle, run=run, score_lock=threading.Lock(),review_store=store,valid_cases=valid_cases)
    server = ThreadingHTTPServer(('127.0.0.1', port), factory)
    print(f'FraudShield: http://127.0.0.1:{port} | {bundle["name"]} | loopback only', flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
