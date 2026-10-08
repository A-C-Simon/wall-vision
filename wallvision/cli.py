"""CLI entry point. No command configures Wi-Fi or sends network packets."""

import argparse
import hashlib
import json
import sys
from pathlib import Path

from .data import import_esp_csv, import_espectre_npz, load_recording, save_recording
from .detector import analyze, calibrate
from .doctor import diagnose
from .evaluation import evaluate
from .report import write_report


def write_json(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, allow_nan=False) + '\n')


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest='command', required=True)
    doctor = commands.add_parser('doctor', help='Read-only hardware and access checks')
    doctor.add_argument('--output')
    imp = commands.add_parser('import-esp', help='Import classic signed-byte ESP32 CSI CSV')
    imp.add_argument('input')
    imp.add_argument('output')
    imp.add_argument('--link-id', default='router-link')
    npz = commands.add_parser('import-espectre', help='Import a numeric ESPectre 1.2 HT20 recording')
    npz.add_argument('input')
    npz.add_argument('output')
    cal = commands.add_parser('calibrate', help='Fit a frozen threshold using a still recording')
    cal.add_argument('input')
    cal.add_argument('--model', required=True)
    replay = commands.add_parser('analyze', help='Analyze a separate recording')
    replay.add_argument('input')
    replay.add_argument('--model', required=True)
    replay.add_argument('--output', required=True)
    replay.add_argument('--html', help='Write a standalone offline score viewer')
    replay.add_argument('--labels', help='JSON array of still/motion intervals in elapsed seconds')
    replay.add_argument('--guard-seconds', type=float, default=0.)
    demo = commands.add_parser('demo', help='Generate and analyze clearly marked synthetic CSI')
    demo.add_argument('--output', default='runs/demo')
    args = parser.parse_args(argv)
    try:
        if args.command == 'doctor':
            result = diagnose()
            if args.output:
                write_json(args.output, result)
            print(json.dumps(result, indent=2))
        elif args.command == 'import-esp':
            recording = import_esp_csv(args.input, args.link_id)
            save_recording(recording, args.output)
            print(f'Imported {len(recording.timestamps)} measured frames')
        elif args.command == 'import-espectre':
            recording = import_espectre_npz(args.input)
            save_recording(recording, args.output)
            print(f'Imported {len(recording.timestamps)} measured frames')
        elif args.command == 'calibrate':
            model = calibrate(load_recording(args.input))
            model['calibration_sha256'] = hashlib.sha256(Path(args.input).read_bytes()).hexdigest()
            write_json(args.model, model)
            print(f"Threshold {model['threshold']:.6f} from {model['baseline_windows']} baseline windows")
        elif args.command == 'analyze':
            recording = load_recording(args.input)
            model = json.loads(Path(args.model).read_text())
            if args.labels and model.get('calibration_sha256') == hashlib.sha256(Path(args.input).read_bytes()).hexdigest():
                raise ValueError('Ground-truth evaluation requires a recording separate from calibration')
            rows = analyze(recording, model)
            metrics = None
            if args.labels:
                metrics = evaluate(rows, json.loads(Path(args.labels).read_text()),
                                   time_origin=float(recording.timestamps[0]), guard_seconds=args.guard_seconds)
            result = {'metadata': recording.metadata, 'windows': rows, 'metrics': metrics,
                      'claim': 'Motion indicates channel changes, not identified human bodies'}
            write_json(args.output, result)
            if args.html:
                write_report(args.html, [{'name': 'CSI recording', 'windows': rows, 'metrics': metrics}],
                             note=f"Source: {recording.metadata['source']}. Human and local through-wall accuracy unverified.")
            print(json.dumps({state: sum(row['state'] == state for row in rows)
                              for state in ('still', 'motion', 'unknown')}))
        elif args.command == 'demo':
            from .synthetic import generate
            output = Path(args.output)
            baseline = generate(seed=100, duration=30)
            recording = generate(seed=200, intervals=[(10, 20), (30, 40)])
            model = calibrate(baseline)
            rows = analyze(recording, model)
            intervals = [{'start': 0, 'end': 10, 'label': 'still'},
                         {'start': 10, 'end': 20, 'label': 'motion'},
                         {'start': 20, 'end': 30, 'label': 'still'},
                         {'start': 30, 'end': 40, 'label': 'motion'}]
            metrics = evaluate(rows, intervals)
            save_recording(baseline, output / 'baseline.jsonl')
            save_recording(recording, output / 'test.jsonl')
            write_json(output / 'model.json', model)
            write_json(output / 'labels.json', intervals)
            write_json(output / 'result.json', {'source': 'synthetic', 'windows': rows, 'metrics': metrics})
            write_report(output / 'report.html', [{'name': 'Synthetic CSI', 'windows': rows, 'metrics': metrics}],
                         'Synthetic pipeline check', 'Generated signals only. No real radio, person, wall, or room was measured.')
            print(f'Synthetic pipeline check written to {output / "report.html"}')
    except (OSError, ValueError, KeyError, TypeError, StopIteration) as exc:
        print(f'Error: {exc}', file=sys.stderr)
        return 2
    return 0
