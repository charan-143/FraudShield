"""Publish supporting assurance evidence without changing the historical ULB run."""
from datetime import datetime, timezone
from html import escape
import hashlib
import json
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT/'.vendor'))
from fraudshield.assurance import cluster_ap_interval


def finalize():
    web=ROOT/'web'
    evidence=json.loads((web/'assurance.json').read_text(encoding='utf-8'))
    card=json.loads((web/'benchmark.json').read_text(encoding='utf-8'))
    tx=card['transactions']
    evidence['ulb_dependence_guard']=cluster_ap_interval(tx['label'],tx['scores'][card['run']['champion_id']],[int(t//86400) for t in tx['time']])
    evidence['dataset'].update(license='CC BY-NC-SA 4.0',release_version=2,release_last_updated='2023-11-29T11:32:12.037Z',
                               attribution='Sergio Jesus, Jose Pombal, Duarte Alves, Andre Cruz, Pedro Saleiro, Rita P. Ribeiro, Joao Gama, Pedro Bizarro; Feedzai BAF, NeurIPS 2022',license_url='https://creativecommons.org/licenses/by-nc-sa/4.0/')
    evidence['artifact_notice']='BAF-derived evidence and model artifacts are provided for noncommercial research under CC BY-NC-SA 4.0. This is not licensed current-bank data.'
    evidence['extension_manifest']={'created_at':datetime.now(timezone.utc).isoformat(),
        'scope':'Current assurance extension source files; historical ULB run.source_hashes refer to its original measured implementation and are intentionally preserved.',
        'source_sha256':{str(path.relative_to(ROOT)).replace('\\','/'):hashlib.sha256(path.read_bytes()).hexdigest() for folder in ['fraudshield','web'] for path in sorted((ROOT/folder).glob('*')) if path.suffix in ['.py','.js','.css','.html'] and path.name not in ['report.html','assurance_report.html']},
        'baf_model_sha256':hashlib.sha256((ROOT/'artifacts'/'baf'/'champion.joblib').read_bytes()).hexdigest()}
    for path in [web/'assurance.json',ROOT/'artifacts'/'baf'/'run.json']:
        path.write_text(json.dumps(evidence,indent=2,allow_nan=False),encoding='utf-8')
    mapping=[
        ('Current bank / Indian payment performance','Not established','Measured a separate eight-month synthetic BAF account-opening study; added an authorized bank-event validation contract. Authentic current institution data remains required.'),
        ('PCA fitting provenance, entities and label delays','Partly addressed','New bank contract requires event/label-availability timestamps and pseudonymous entities. Behavior features use only earlier observations. ULB PCA provenance and BAF label delays remain unknown.'),
        ('Uninterpretable PCA features','Addressed for the separate BAF task','Named source features and exact TreeSHAP raw-margin contributions are exported with additivity checks. ULB PCA is not relabeled as merchant/device behavior.'),
        ('Historical fraud labels / criminal intent','Review workflow added','Append-only research dispositions are bound to dataset fingerprint and measured run, with reviewer pseudonym, reason and hash chain. No automatic payment or criminal determination.'),
        ('Exposure versus savings','Accounting contract added; actual data absent','Observed closed-outcome financial accounting preserves CSV monetary strings and uses Decimal, per currency. Realized loss/recovery remain unavailable for ULB and BAF; hypothetical scenarios stay labeled.'),
        ('External benchmark comparability','Protocol gate added','Missing/different source fingerprints, splits, features, population, labels, metric definition, search budget or seed policy blocks comparability. No published result is claimed reproduced.'),
        ('Few independent outcomes / short uncertainty window','More temporal observations; robust interval withheld','Three forward test months are reported separately. Month/day cluster guards withhold intervals with insufficient independent units; original fixed-block ULB intervals are exploratory only.'),
        ('Protected attributes missing','Age audit measured on BAF only','Group recall/FPR, denominators and qualified Wilson intervals are reported. Age excluded from predictors; demographic fairness on ULB/current banks is still unmeasured.')]
    table=''.join(f'<tr><td>{escape(name)}</td><td>{escape(state)}</td><td>{escape(detail)}</td></tr>' for name,state,detail in mapping)
    monthly=''.join(f'<tr><td>{fold["test_month"]}</td><td>{escape(fold["champion"])}</td><td>{fold["split"]["test"]["rows"]:,}</td><td>{fold["split"]["test"]["frauds"]:,}</td><td>{next(m for m in fold["models"] if m["name"]==fold["champion"])["test_ap"]:.4f}</td></tr>' for fold in evidence['folds'])
    final=evidence['folds'][-1]
    fairness=''.join(f'<tr><td>{escape(row["group"])}</td><td>{row["n"]:,}</td><td>{row["frauds"]}</td><td>{row["recall"]:.1%}</td><td>{row["fpr"]:.2%}</td></tr>' for row in final['age_audit']['groups'])
    report=f'''<!doctype html><html lang="en"><meta charset="utf-8"><title>FraudShield limitations and evidence report</title><style>body{{font:15px/1.6 system-ui;color:#183c3a;max-width:1150px;margin:45px auto;padding:20px}}h1{{font:40px Georgia,serif}}h2{{margin-top:35px}}table{{border-collapse:collapse;width:100%;font-size:13px}}td,th{{padding:11px;border-bottom:1px solid #d4ded3;text-align:left;vertical-align:top}}.note{{background:#f3efdf;padding:16px}}code{{overflow-wrap:anywhere}}@media print{{button{{display:none}}}}</style><button onclick="window.print()">Print / save PDF</button><p>FRAUDSHIELD / SUPPORTING EVIDENCE REPORT</p><h1>Eight limitations, with concrete responses.</h1><p class="note">Some limits require external evidence and cannot be removed in software. The original ULB card experiment is preserved. The new measured study is synthetic BAF account opening, not current Indian card/UPI validation.</p><table><tr><th>Original limitation</th><th>State</th><th>Implementation and remaining boundary</th></tr>{table}</table><h2>Measured longer-history stress test</h2><p>BAF Base: {evidence['dataset']['rows']:,} applications, {evidence['dataset']['frauds']:,} fraud labels, eight indexed months. Three predeclared candidates per fold; each champion is selected on an earlier tune month. Independent earlier calibration sets the 5% target review threshold.</p><table><tr><th>Source test month (zero-based)</th><th>Tune-selected model</th><th>Test rows</th><th>Frauds</th><th>Test AP</th></tr>{monthly}</table><p>These are three forward-period observations with overlapping training histories, not independent replications or a confidence interval. Label delay and original feature engineering remain unverified source properties.</p><h2>The audit found a disparity; it did not certify fairness.</h2><table><tr><th>Final-month group</th><th>Rows</th><th>Frauds</th><th>Recall</th><th>False-positive rate</th></tr>{fairness}</table><p>One common calibration-selected threshold. Age excluded from predictors. Other features may proxy age. Full qualified Wilson intervals and counts appear in assurance.json and the dashboard. Their binomial independence assumption does not establish statistical significance under unknown event dependence.</p><h2>Uncertainty guards</h2><p>BAF has one test-month cluster per fold; ULB's final test has {evidence['ulb_dependence_guard']['clusters']} elapsed-day cluster(s). Both fail the default minimum of 20 dependence units. No dependence-supported AP interval is produced. Existing ULB fixed-block resampling intervals remain exploratory historical evidence only.</p><h2>Source and licensing</h2><p>{escape(evidence['dataset']['attribution'])}. Dataset release 2, source metadata updated 2023-11-29. <a href="{escape(evidence['dataset']['source'])}">Original dataset</a>. <a href="https://creativecommons.org/licenses/by-nc-sa/4.0/">CC BY-NC-SA 4.0</a>. BAF-derived reports, examples and trained model are noncommercial research artifacts; this is not permission for commercial bank deployment.</p><p>BAF CSV SHA-256: <code>{evidence['dataset']['sha256']}</code></p><h2>Verification boundary</h2><p>Automated tests cover data and label chronology, review identity/integrity, amount precision and currency separation, protocol gates, model selection, SHAP additivity, HTTP handlers and dashboard logic. Live browser/network and current-bank deployment validation are not claimed.</p></html>'''
    (web/'assurance_report.html').write_text(report,encoding='utf-8')
    print('Finalized assurance evidence and printable eight-limit report.')


if __name__=='__main__':finalize()
