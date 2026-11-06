"""Package the measured study without redistributing the raw dataset or vendor wheels."""
import json
from pathlib import Path
import zipfile

ROOT = Path(__file__).resolve().parent


def build():
    from update_presentation import update
    update()
    out = ROOT / 'delivery'
    out.mkdir(exist_ok=True)
    web = ROOT / 'web'
    payload = (web / 'benchmark.json').read_text(encoding='utf-8')
    json.loads(payload)
    html = (web / 'index.html').read_text(encoding='utf-8')
    html = html.replace('<link rel="stylesheet" href="styles.css">', '<style>' + (web / 'styles.css').read_text(encoding='utf-8') + '</style>')
    html = html.replace('<script defer src="app.js"></script>', '')
    html = html.replace('<script defer src="assurance.js"></script>', '')
    html = html.replace('<script defer src="policy.js"></script>', '')
    report = json.dumps((web / 'report.html').read_text(encoding='utf-8')).replace('<', '\\u003c')
    metrics = json.dumps((web / 'model_metrics.csv').read_text(encoding='utf-8')).replace('<', '\\u003c')
    inline = '<script>window.FRAUDSHIELD_DATA=' + payload.replace('<', '\\u003c') + ';window.FRAUDSHIELD_REPORT=' + report + ';window.FRAUDSHIELD_METRICS=' + metrics + ';</script>'
    if (web/'assurance.json').exists():
        assurance=(web/'assurance.json').read_text(encoding='utf-8').replace('<','\\u003c')
        inline += '<script>window.FRAUDSHIELD_ASSURANCE='+assurance+';</script>'
        assurance_report=json.dumps((web/'assurance_report.html').read_text(encoding='utf-8')).replace('<','\\u003c')
        inline += '<script>window.FRAUDSHIELD_ASSURANCE_REPORT='+assurance_report+';</script>'
    app = (web / 'app.js').read_text(encoding='utf-8').replace('</script', '<\\/script')
    app += '\n' + (web/'assurance.js').read_text(encoding='utf-8').replace('</script','<\\/script')
    if (web/'policy.json').exists():
        inline += '<script>window.FRAUDSHIELD_POLICY='+(web/'policy.json').read_text(encoding='utf-8').replace('<','\\u003c')+';</script>'
        app += '\n'+(web/'policy.js').read_text(encoding='utf-8')
    offline = '''document.addEventListener('click',e=>{const a=e.target.closest('a');if(!a)return;const href=a.getAttribute('href');if(href==='report.html'){e.preventDefault();download('FraudShield-benchmark-report.html',window.FRAUDSHIELD_REPORT,'text/html');}if(href==='model_metrics.csv'){e.preventDefault();download('FraudShield-model-metrics.csv',window.FRAUDSHIELD_METRICS,'text/csv');}});'''
    html = html.replace('</body>', inline + '<script>' + app + '\n' + offline + '</script></body>')
    (out / 'FraudShield_dashboard.html').write_text(html, encoding='utf-8')
    (out / 'FraudShield_benchmark_report.html').write_text((web / 'report.html').read_text(encoding='utf-8'), encoding='utf-8')
    allowed_dirs = ['fraudshield', 'tests', 'docs', 'web', 'artifacts']
    files = [ROOT / name for name in ['README.md','DATA_ATTRIBUTION.md','requirements.txt','requirements-lock.txt','run.py','package_delivery.py','finalize_assurance.py','update_presentation.py','evaluate_policy.py','research_notes.md','.gitignore'] if (ROOT / name).exists()]
    for directory in allowed_dirs:
        files.extend(path for path in (ROOT / directory).rglob('*') if path.is_file() and '__pycache__' not in path.parts and '.pytest_cache' not in path.parts)
    archive = out / 'FraudShield_card_fraud_project.zip'
    with zipfile.ZipFile(archive, 'w', compression=zipfile.ZIP_DEFLATED, compresslevel=6) as bundle:
        bundle.write(out / 'FraudShield_dashboard.html', 'FraudShield/FraudShield_dashboard.html')
        for path in sorted(files):
            bundle.write(path, 'FraudShield/' + str(path.relative_to(ROOT)).replace('\\','/'))
    print(json.dumps({'standalone': str(out / 'FraudShield_dashboard.html'), 'report': str(out / 'FraudShield_benchmark_report.html'), 'project': str(archive), 'archive_bytes': archive.stat().st_size, 'files': len(files)}))


if __name__ == '__main__':
    build()
