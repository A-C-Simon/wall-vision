"""CLI entry point. No command configures Wi-Fi or sends network packets."""

import argparse
import json
import sys
from pathlib import Path

from .data import import_esp_csv, load_recording, save_recording
from .detector import analyze, calibrate
from .doctor import diagnose


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
    cal = commands.add_parser('calibrate', help='Fit a frozen threshold using a still recording')
    cal.add_argument('input')
    cal.add_argument('--model', required=True)
    replay = commands.add_parser('analyze', help='Analyze a separate recording')
    replay.add_argument('input')
    replay.add_argument('--model', required=True)
    replay.add_argument('--output', required=True)
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
        elif args.command == 'calibrate':
            model = calibrate(load_recording(args.input))
            write_json(args.model, model)
            print(f"Threshold {model['threshold']:.6f} from {model['baseline_windows']} baseline windows")
        elif args.command == 'analyze':
            recording = load_recording(args.input)
            rows = analyze(recording, json.loads(Path(args.model).read_text()))
            write_json(args.output, {'metadata': recording.metadata, 'windows': rows,
                                     'claim': 'Motion indicates channel changes, not identified human bodies'})
            print(json.dumps({state: sum(row['state'] == state for row in rows)
                              for state in ('still', 'motion', 'unknown')}))
    except (OSError, ValueError, KeyError, TypeError, StopIteration) as exc:
        print(f'Error: {exc}', file=sys.stderr)
        return 2
    return 0
