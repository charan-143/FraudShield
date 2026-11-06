"""Run from the project directory. Local optional wheels live in .vendor."""
from pathlib import Path
import argparse
import os
import sys

ROOT = Path(__file__).resolve().parent
if (ROOT / '.vendor').is_dir():
    sys.path.insert(0, str(ROOT / '.vendor'))
os.environ.setdefault('OMP_NUM_THREADS', '4')


def main():
    parser = argparse.ArgumentParser(description='FraudShield card fraud benchmark and dashboard')
    sub = parser.add_subparsers(dest='command', required=True)
    fetch = sub.add_parser('download', help='Download public ULB mirror; never replaces existing data')
    fetch.add_argument('--data', default=str(ROOT / 'data' / 'creditcard.csv'))
    fit = sub.add_parser('train', help='Run time-ordered model selection, calibration and final evaluation')
    fit.add_argument('--data', default=str(ROOT / 'data' / 'creditcard.csv'))
    fit.add_argument('--bootstrap', type=int, default=150)
    serve = sub.add_parser('serve', help='Serve dashboard and local scoring API on loopback')
    serve.add_argument('--port', type=int, default=8765)
    score = sub.add_parser('score', help='Score a CSV using the tune-selected champion')
    score.add_argument('input')
    score.add_argument('--output', required=True)
    baf = sub.add_parser('train-baf', help='Run a separate synthetic eight-month account-opening stress test')
    baf.add_argument('--data', default=str(ROOT / 'data' / 'baf' / 'Base.csv'))
    bank = sub.add_parser('validate-bank', help='Validate authorized pseudonymous bank events, label maturity and outcomes')
    bank.add_argument('--data', required=True)
    bank.add_argument('--manifest', required=True)
    bank.add_argument('--output', required=True)
    bank.add_argument('--period', help='JSON file with start, end and labels_as_of for an optional maturity cohort')
    args = parser.parse_args()
    if args.command == 'train-baf':
        from fraudshield.baf import run_baf
        run_baf(args.data, ROOT)
    elif args.command == 'validate-bank':
        import json
        from fraudshield.bank_events import validate_bank_file
        period = json.loads(Path(args.period).read_text(encoding='utf-8')) if args.period else None
        result = validate_bank_file(args.data,args.manifest,args.output,period)
        print(f'Validated {result["rows"]} bank events; evidence written to {args.output}')
    elif args.command == 'download':
        from fraudshield.data import download
        download(args.data)
    elif args.command == 'train':
        if args.bootstrap < 20:
            parser.error('--bootstrap must be at least 20')
        from fraudshield.training import train
        train(args.data, ROOT, args.bootstrap)
    elif args.command == 'serve':
        from fraudshield.server import serve
        serve(ROOT, args.port)
    elif args.command == 'score':
        import pandas as pd
        from fraudshield.server import load_champion
        from fraudshield.training import predict_bundle
        target = Path(args.output)
        if target.exists():
            parser.error('Output already exists; choose a new file to avoid data loss.')
        model, _ = load_champion(ROOT)
        frame = pd.read_csv(args.input)
        probabilities = predict_bundle(model, frame)
        result = pd.DataFrame({'row': range(len(frame)), 'risk_probability': probabilities, 'review': probabilities >= model['threshold']})
        result.to_csv(target, index=False)
        print(f'Scored {len(result):,} rows -> {target}')


if __name__ == '__main__':
    main()
