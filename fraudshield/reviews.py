"""Append-only research review history; no automatic payment or legal decisions."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import sqlite3

DISPOSITIONS = {'cleared_for_study','escalate_for_review','inconclusive'}


class ReviewStore:
    def __init__(self,path,dataset_sha256,run_id):
        if not re.fullmatch(r'[a-f0-9]{64}',dataset_sha256) or not re.fullmatch(r'[A-Za-z0-9_-]{1,80}',run_id):
            raise ValueError('Valid dataset fingerprint and run identifier are required for review identity.')
        self.dataset_sha256,self.run_id=dataset_sha256,run_id
        self.path=Path(path)
        self.path.parent.mkdir(parents=True,exist_ok=True)
        with self.connect() as db:
            db.execute('CREATE TABLE IF NOT EXISTS review_events (sequence INTEGER PRIMARY KEY, event_id TEXT NOT NULL, payload TEXT NOT NULL, previous_hash TEXT NOT NULL, event_hash TEXT NOT NULL)')
            db.execute('CREATE TABLE IF NOT EXISTS review_context (key TEXT PRIMARY KEY,value TEXT NOT NULL)')
            stored=dict(db.execute('SELECT key,value FROM review_context').fetchall())
            expected={'dataset_sha256':dataset_sha256,'run_id':run_id}
            if stored and stored!=expected:
                raise ValueError('Review store belongs to another dataset or run. Do not reuse positional case identities.')
            if not stored:
                if db.execute('SELECT COUNT(*) FROM review_events').fetchone()[0]:
                    raise ValueError('Unbound legacy review history cannot be assigned to a new dataset.')
                db.executemany('INSERT INTO review_context VALUES (?,?)',expected.items())
            db.execute("CREATE TRIGGER IF NOT EXISTS immutable_update BEFORE UPDATE ON review_events BEGIN SELECT RAISE(ABORT,'review events are append only'); END")
            db.execute("CREATE TRIGGER IF NOT EXISTS immutable_delete BEFORE DELETE ON review_events BEGIN SELECT RAISE(ABORT,'review events are append only'); END")

    def connect(self):
        return sqlite3.connect(self.path,timeout=5)

    def append(self,event_id,actor,disposition,reason):
        if not isinstance(event_id,str) or not re.fullmatch(r'ULB-[0-9]{6}',event_id):
            raise ValueError('A generated ULB event identifier is required.')
        if not isinstance(actor,str) or not re.fullmatch(r'[A-Za-z0-9_-]{3,40}',actor):
            raise ValueError('Use a pseudonymous reviewer ID of 3–40 letters, digits, underscores or hyphens.')
        if disposition not in DISPOSITIONS:
            raise ValueError('Choose a research review disposition, not a criminal or payment decision.')
        if not isinstance(reason,str) or not 5<=len(reason.strip())<=500 or any(ord(c)<32 and c not in '\n\t' for c in reason):
            raise ValueError('A reason of 5–500 printable characters is required; do not enter personal information.')
        with self.connect() as db:
            db.execute('BEGIN IMMEDIATE')
            if not self.verify()['valid']:
                raise ValueError('Review integrity check failed; refusing to append.')
            prior=db.execute('SELECT sequence,event_hash FROM review_events ORDER BY sequence DESC LIMIT 1').fetchone()
            sequence,previous=(prior[0]+1,prior[1]) if prior else (1,'0'*64)
            value={'sequence':sequence,'event_id':event_id,'dataset_sha256':self.dataset_sha256,'run_id':self.run_id,'actor':actor,'disposition':disposition,'reason':reason.strip(),'created_at':datetime.now(timezone.utc).isoformat()}
            payload=json.dumps(value,sort_keys=True,separators=(',',':'))
            digest=hashlib.sha256((previous+payload).encode()).hexdigest()
            db.execute('INSERT INTO review_events VALUES (?,?,?,?,?)',(sequence,event_id,payload,previous,digest))
        return {**value,'previous_hash':previous,'event_hash':digest}

    def history(self,event_id):
        with self.connect() as db:
            rows=db.execute('SELECT payload,previous_hash,event_hash FROM review_events WHERE event_id=? ORDER BY sequence',(event_id,)).fetchall()
        return [{**json.loads(payload),'previous_hash':prior,'event_hash':digest} for payload,prior,digest in rows]

    def verify(self):
        previous='0'*64
        with self.connect() as db:
            rows=db.execute('SELECT sequence,event_id,payload,previous_hash,event_hash FROM review_events ORDER BY sequence').fetchall()
        for expected,(sequence,event_id,payload,prior,digest) in enumerate(rows,1):
            value=json.loads(payload)
            if sequence!=expected or value.get('sequence')!=sequence or value.get('event_id')!=event_id or value.get('dataset_sha256')!=self.dataset_sha256 or value.get('run_id')!=self.run_id or prior!=previous or hashlib.sha256((prior+payload).encode()).hexdigest()!=digest:
                return {'valid':False,'events':len(rows),'failed_sequence':sequence}
            previous=digest
        return {'valid':True,'events':len(rows),'head_hash':previous,'qualification':'Local integrity chain, not authenticated identity or externally anchored tamper proof.'}
