"""Refresh stakeholder entry points from existing measured evidence."""
from pathlib import Path
import json
import re

ROOT=Path(__file__).resolve().parent

def update():
    web=ROOT/'web'
    card=json.loads((web/'benchmark.json').read_text(encoding='utf-8'))['run']
    a=json.loads((web/'assurance.json').read_text(encoding='utf-8'))
    from fraudshield.training import write_report
    write_report(card,web/'card_report.html')
    baseline=(web/'card_report.html').read_text(encoding='utf-8')
    assurance=(web/'assurance_report.html').read_text(encoding='utf-8')
    body=assurance[assurance.index('<h1>'):assurance.rindex('</html>')]
    baseline=baseline.replace('Card fraud, measured honestly.','FraudShield: consolidated evidence report.')
    baseline=baseline.replace('with a conditional 95% block-bootstrap interval','with an exploratory fixed-block resampling interval')
    baseline=re.sub(r'<h2>Next datasets</h2>.*?<h2>Sources</h2>','<h2>Sources for the card study</h2>',baseline,flags=re.S)
    baseline=baseline.replace('</html>','<hr><section id="assurance"><p class="tag">SEPARATE SYNTHETIC ACCOUNT-OPENING STUDY</p>'+body+'</section></html>')
    if (web/'policy.json').exists():
        policy=json.loads((web/'policy.json').read_text(encoding='utf-8'))
        rows=''.join(f'<tr><td>{name}</td><td>{value["fp"]}</td><td>{value["tp"]}</td><td>{value["precision"]:.1%}</td><td>{value["recall"]:.1%}</td><td>{value["alerts"]}</td></tr>' for name,value in [('Original threshold',policy['baseline_test']),('Calibration-selected candidate',policy['candidate_test'])])
        section='<h2>Calibration-only policy experiment</h2><p>Retrospective comparison; previously inspected test data is not new independent validation. Assumed cost: EUR 3 per review and EUR 100 per missed fraud. Calibration recall floor: 80%. No guarantee of future recall, realized savings, authentication success or actual payment decisions.</p><table><tr><th>Policy</th><th>False alerts</th><th>Frauds captured</th><th>Precision</th><th>Recall</th><th>Reviews</th></tr>'+rows+'</table><p>Behavioral/merchant context cannot be invented for PCA-only ULB data. Risk tiers are simulated routing candidates, not approval, authentication or decline integrations.</p>'
        baseline=baseline.replace('</html>',section+'</html>')
        if 'customer_balance' in policy:
            f=policy['customer_balance']
            rows=''.join(f'<tr><td>{r["recall_target"]:.0%}</td><td>{r["recall"]:.1%}</td><td>{r["precision"]:.1%}</td><td>{r["legitimate_interruptions_per_10000"]:.1f}</td></tr>' for r in f['rows'])
            section='<h2>Balancing fraud capture and customer interruption</h2><p>Calibration-only frontier. Illustrative research objective: at least 80% recall, with at most 50 legitimate interruptions per 10,000 legitimate transactions. The current model cannot satisfy both on calibration data. No new policy is promoted. Only 49 calibration fraud cases support these estimates.</p><table><tr><th>Recall floor</th><th>Calibration recall</th><th>Precision</th><th>Legitimate interruptions / 10,000</th></tr>'+rows+'</table><p>These are transaction counts, not unique customers or measured satisfaction. Step-up candidates count as interruptions. Authentication completion, abandonment, latency, repeated challenges per customer and later confirmed fraud must be measured on new forward data before deployment. Routing tiers alone do not establish additional prevention or improved customer experience.</p>'
            baseline=baseline.replace('</html>',section+'</html>')
    (web/'report.html').write_text(baseline,encoding='utf-8')
    js=web/'assurance.js'
    source=js.read_text(encoding='utf-8')
    marker='// Consolidated overview evidence summary'
    if marker not in source:
        source+='''
// Consolidated overview evidence summary
const cardOverview=overview;
overview=function(){
 const original=cardOverview();if(!assuranceData)return original;
 const a=assuranceData,last=a.folds[a.folds.length-1],g=last.age_audit.groups;
 const summary=`<section class="panel" style="margin-bottom:22px"><div class="panel-head"><div><span class="eyebrow">CURRENT EVIDENCE / RESEARCH ONLY</span><h2>Two studies. Separate conclusions.</h2></div><a class="button secondary" href="#assurance">Inspect safeguards</a></div><div class="grid equal"><div><h3>Real card transactions</h3><p>${nf.format(run.dataset.raw_rows)} original ULB records, two days in 2013. ${run.splits.test.frauds} final-test fraud outcomes.</p></div><div><h3>Synthetic account opening</h3><p>${nf.format(a.dataset.rows)} BAF applications across eight months. Three forward tests; AP ${dec(a.temporal_summary.ap_min,3)} to ${dec(a.temporal_summary.ap_max,3)}. These results are not pooled with card fraud.</p></div></div><div class="warning"><b>Fairness finding:</b> final-month false-positive rates are ${g.map(x=>esc(x.group)+': '+pct(x.fpr,2)).join(' versus ')}. This audit identifies a disparity; it does not certify fairness.</div><p class="chart-note">Current Indian-bank performance and realized savings remain unmeasured. Dependence-supported AP intervals are withheld where clusters are insufficient. Local reviews record research dispositions only.</p></section>`;
 const at=original.indexOf('<div class="controls">');return at<0?summary+original:original.slice(0,at)+summary+original.slice(at);
};
if(data)render();
'''
    source=source.replace("if(location.hash==='#assurance'||location.hash==='#reports')render();","if(data)render();")
    js.write_text(source,encoding='utf-8')
    print('Updated overview and consolidated primary report from measured results.')

if __name__=='__main__':update()
