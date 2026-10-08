"""Portable CSI recordings and Espressif signed-byte CSV imports."""

import csv
import hashlib
import json
from dataclasses import dataclass
from pathlib import Path

import numpy as np

FORMAT = 'wallvision-csi-v1'


@dataclass
class Recording:
    timestamps: np.ndarray
    csi: np.ndarray
    metadata: dict

    def __post_init__(self):
        self.timestamps = np.asarray(self.timestamps, dtype=float)
        self.csi = np.asarray(self.csi, dtype=complex)
        if self.timestamps.ndim != 1 or self.csi.ndim != 2:
            raise ValueError('Expected timestamps[N] and complex CSI[N, subcarriers]')
        if len(self.timestamps) != len(self.csi) or len(self.timestamps) < 2:
            raise ValueError('A recording requires at least two matching frames')
        if self.csi.shape[1] < 8:
            raise ValueError('At least eight subcarrier measurements are required')
        if not np.isfinite(self.timestamps).all() or not np.isfinite(self.csi).all():
            raise ValueError('Non-finite timestamps or CSI values')
        if np.any(np.diff(self.timestamps) <= 0):
            raise ValueError('Timestamps must strictly increase; split reboots into separate recordings')
        if self.metadata.get('source') not in ('measured', 'synthetic'):
            raise ValueError('Metadata source must be measured or synthetic')
        if not self.metadata.get('link_id'):
            raise ValueError('A consistent, pseudonymous link_id is required')


def save_recording(recording, path):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('w') as stream:
        stream.write(json.dumps({'format': FORMAT, **recording.metadata}, allow_nan=False) + '\n')
        for t, h in zip(recording.timestamps, recording.csi):
            stream.write(json.dumps({'timestamp': float(t), 'real': h.real.tolist(),
                                     'imag': h.imag.tolist()}, allow_nan=False) + '\n')


def load_recording(path):
    timestamps, frames = [], []
    with Path(path).open() as stream:
        metadata = json.loads(next(stream))
        if metadata.pop('format', None) != FORMAT:
            raise ValueError('Unknown recording format')
        for lineno, line in enumerate(stream, 2):
            if not line.strip():
                continue
            try:
                row = json.loads(line)
                real, imag = np.asarray(row['real']), np.asarray(row['imag'])
                if real.ndim != 1 or real.shape != imag.shape:
                    raise ValueError('Mismatched real/imag arrays')
                frames.append(real + 1j * imag)
                timestamps.append(row['timestamp'])
            except (KeyError, TypeError, ValueError) as exc:
                raise ValueError(f'Invalid CSI row {lineno}: {exc}') from exc
    return Recording(timestamps, frames, metadata)


def import_esp_csv(path, link_id='router-link'):
    """Read classic ESP32 LLTF signed-byte output, using the emitted CSV header.

    ESP-IDF documents imaginary then real. Only the first 64 complex LLTF
    entries are retained. The first two entries are always masked, including
    packets where first_word_invalid is false, to preserve fixed geometry.
    New C5/C61 packed encodings and non-byte gain-compensated data are rejected.
    """
    header, timestamps, frames = None, [], []
    signature = None
    previous, offset = None, 0
    with Path(path).open() as stream:
        for lineno, line in enumerate(stream, 1):
            line = line.strip()
            if line.startswith('type,') and line.endswith(',data'):
                header = next(csv.reader([line]))
                continue
            if not line.startswith('CSI_DATA,'):
                continue
            if header is None:
                raise ValueError('CSV header required to determine firmware field layout')
            fields = next(csv.reader([line]))
            if len(fields) != len(header):
                raise ValueError(f'CSV field count mismatch at line {lineno}')
            row = dict(zip(header, fields))
            try:
                values = np.asarray(json.loads(row['data']), dtype=float)
                if values.ndim != 1 or len(values) != int(row['len']):
                    raise ValueError('Declared CSI length does not match payload')
                if len(values) < 128 or len(values) % 2:
                    raise ValueError('Expected at least 128 bytes of classic LLTF CSI')
                if np.any(values < -128) or np.any(values > 127) or np.any(values != np.round(values)):
                    raise ValueError('Only signed-byte ESP32 CSI is supported')
                current = (row.get('mac'), row.get('channel'), row.get('secondary_channel'),
                           row.get('bandwidth'), row.get('ant'), row.get('rx_format', row.get('sig_mode')),
                           len(values))
                if signature is not None and current != signature:
                    raise ValueError('Link, channel, format, antenna or CSI length changed; split the recording')
                signature = current
                raw = int(row['local_timestamp'])
                if not 0 <= raw < 2**32:
                    raise ValueError('Expected a uint32 microsecond local_timestamp')
                if previous is not None and raw < previous:
                    if previous > 0xF0000000 and raw < 0x10000000:
                        offset += 2**32
                    else:
                        raise ValueError('Device clock restarted or packets arrived out of order')
                previous = raw
                h = values[1:128:2] + 1j * values[:128:2]
                h[:2] = 0
                frames.append(h)
                timestamps.append((raw + offset) / 1e6)
            except (KeyError, TypeError, ValueError) as exc:
                raise ValueError(f'Invalid ESP32 CSI at line {lineno}: {exc}') from exc
    return Recording(timestamps, frames, {
        'source': 'measured', 'link_id': link_id, 'extractor': 'esp32-signed-byte-lltf',
        'channel': signature[1] if signature else None,
        'geometry': '64 LLTF bins; first two masked',
        'radio_format': list(signature[2:]) if signature else [],
        'provenance': 'Imported ESP32 CSV; physical conditions require separate ground truth',
    })


def import_espectre_npz(path):
    """Import numeric HT20 captures in ESPectre dataset format 1.2.

    Never enable pickle. Preserve receiver timestamps; no packet-rate-derived
    synthetic time axis is substituted when timestamps are absent.
    """
    with np.load(path, allow_pickle=False) as z:
        if str(z['format_version'].item()) != '1.2':
            raise ValueError('Only ESPectre dataset format 1.2 is supported')
        values = z['csi_data']
        if values.dtype != np.int8 or values.ndim != 2 or values.shape[1] != 128:
            raise ValueError('Expected signed-byte, 64-bin CSI pairs')
        for key, expected in [('phy_mode', 'ht'), ('ltf_type', 'ht-ltf'), ('channel_width', '20')]:
            if not np.all(z[key] == expected):
                raise ValueError(f'Unsupported or changing {key}')
        channel = np.unique(z['channel'])
        if len(channel) != 1:
            raise ValueError('Channel changed during the recording')
        raw_t = z['wifi_rx_ts_us'].astype(np.int64)
        if raw_t.shape != (len(values),):
            raise ValueError('Timestamp and CSI counts differ')
        offsets = np.zeros(len(raw_t), dtype=np.int64)
        for i in range(1, len(raw_t)):
            offsets[i] = offsets[i - 1]
            if raw_t[i] < raw_t[i - 1]:
                if raw_t[i - 1] > 0xF0000000 and raw_t[i] < 0x10000000:
                    offsets[i] += 2**32
                else:
                    raise ValueError('Receiver clock reset or out-of-order packets')
        timestamps = (raw_t + offsets - raw_t[0]) / 1e6
        h = values[:, 1::2].astype(float) + 1j * values[:, ::2].astype(float)
        h[:, :2] = 0
        # Only a pseudonym is exported. No endpoints or network addresses are retained.
        link = hashlib.sha256(str(z['device_id'].item()).encode()).hexdigest()[:16]
        metadata = {'source': 'measured', 'link_id': f'espectre-{link}',
                    'extractor': 'espectre-npz-1.2', 'geometry': '64 HT-LTF bins; first two masked',
                    'channel': int(channel[0]), 'chip': str(z['chip'].item()),
                    'dataset_label': str(z['label'].item()),
                    'provenance': 'Public ESPectre recording; local wall conditions unverified'}
    return Recording(timestamps, h, metadata)
