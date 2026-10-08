#!/usr/bin/env python3
"""Replay pinned public CSI captures. Downloads do not configure Wi-Fi."""

import argparse
import hashlib
import json
import sys
import time
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from wallvision.data import Recording, import_espectre_npz
from wallvision.detector import analyze, calibrate
from wallvision.evaluation import evaluate
from wallvision.report import write_report

REVISION = '12fce9354d3506290e70a853a4f22866f0e987ef'
ROOT = f'https://raw.githubusercontent.com/francescopace/espectre/{REVISION}/data/'
FILES = {
    'static': ('static_presence/static_presence_esp32_64sc_dev5566279062754e5b_20261004_115304_525665_0001.npz',
               '3c6606b6848b82b7f3379f8d262c46b30bc8136dca44a7589c8929d5f17993ff'),
    'motion': ('motion/motion_esp32_64sc_dev5566279062754e5b_20261004_115617_146302_0001.npz',
               'ef6c7eba40729cbeaf1138e21874b4e08361760d16ffd64bcf6e551cad7b3845'),
    'empty': ('empty/empty_esp32_64sc_dev5566279062754e5b_20261004_172849_747914_0001.npz',
              '191ae0e31f33d1fd7d8b8350827d1767dcf3135711bef6e6dbf6fc1233461977'),
}


def subset(recording, start, end):
    keep = (recording.timestamps >= start) & (recording.timestamps <= end)
    return Recording(recording.timestamps[keep], recording.csi[keep], recording.metadata)


def download(url, path):
    # Bound download throughput and size. Never touch the router or radio settings.
    count, started = 0, time.monotonic()
    partial = path.with_suffix('.part')
    try:
        with urllib.request.urlopen(url, timeout=30) as response, partial.open('wb') as out:
            while chunk := response.read(32768):
                count += len(chunk)
                if count > 5_000_000:
                    raise ValueError('Capture exceeds expected size limit')
                out.write(chunk)
                time.sleep(max(0, count / 262144 - (time.monotonic() - started)))
        partial.replace(path)
    finally:
        partial.unlink(missing_ok=True)


def run(directory, output, no_download=False):
    directory.mkdir(parents=True, exist_ok=True)
    recordings, sources = {}, {}
    for name, (filename, digest) in FILES.items():
        path = directory / f'{name}.npz'
        if not path.exists():
            if no_download:
                raise ValueError(f'Missing capture: {path}')
            download(ROOT + filename, path)
        if hashlib.sha256(path.read_bytes()).hexdigest() != digest:
            raise ValueError(f'Capture checksum mismatch: {path}')
        recordings[name] = import_espectre_npz(path)
        sources[name] = {'url': ROOT + filename, 'sha256': digest,
                         'frames': len(recordings[name].timestamps)}
    baseline = subset(recordings['static'], 0, 60)
    model = calibrate(baseline)
    tests = [('Stationary person, held-out tail', subset(recordings['static'], 65, 180), 'still'),
             ('Moving person, separate recording', recordings['motion'], 'motion'),
             ('Empty room, later recording', recordings['empty'], 'still')]
    sessions = []
    for name, recording, label in tests:
        rows = analyze(recording, model)
        metrics = evaluate(rows, [{'start': float(recording.timestamps[0]),
                                   'end': float(recording.timestamps[-1]), 'label': label}])
        sessions.append({'name': name, 'source': 'measured', 'metrics': metrics, 'windows': rows})
    note = ('Offline public ESP32 data, not measurements from this computer. '
            'Calibration: first 60 seconds of stationary recording; test tail starts at 65 seconds. '
            'Labels apply to whole recordings, so short pauses in motion are not individually annotated. '
            'Through-wall conditions and human detection in the local room remain unverified.')
    output.mkdir(parents=True, exist_ok=True)
    result = {'revision': REVISION, 'sources': sources, 'note': note, 'model': model,
              'sessions': [{k: v for k, v in s.items() if k != 'windows'} for s in sessions]}
    (output / 'public-benchmark.json').write_text(json.dumps(result, indent=2, allow_nan=False) + '\n')
    write_report(output / 'public-benchmark.html', sessions, 'Public CSI replay benchmark', note)
    print(json.dumps(result['sessions'], indent=2))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--directory', type=Path, default=Path('data/public'))
    parser.add_argument('--output', type=Path, default=Path('reports'))
    parser.add_argument('--no-download', action='store_true')
    args = parser.parse_args()
    run(args.directory, args.output, args.no_download)
