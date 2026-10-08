"""Baseline-calibrated amplitude motion score with explicit abstention."""

from dataclasses import asdict, dataclass

import numpy as np
from scipy.ndimage import median_filter
from scipy.signal import welch

from .data import Recording


@dataclass
class Config:
    window_seconds: float = 2.0
    hop_seconds: float = 0.5
    sample_rate: float = 50.0
    low_hz: float = 0.7
    high_hz: float = 8.0
    min_rate: float = 20.0
    max_gap: float = 0.25
    min_coverage: float = 0.7

    def __post_init__(self):
        if not all(np.isfinite(v) and v > 0 for v in asdict(self).values()):
            raise ValueError('All detector parameters must be positive and finite')
        if not self.low_hz < self.high_hz < self.sample_rate / 2:
            raise ValueError('Motion band must be below the resampling Nyquist frequency')
        if self.min_rate <= 2 * self.high_hz:
            raise ValueError('Minimum input rate must exceed twice the motion band limit')
        if self.min_coverage > 1 or self.window_seconds * self.sample_rate < 32:
            raise ValueError('Invalid coverage or insufficient samples per window')
        if self.window_seconds * (self.high_hz - self.low_hz) < 1:
            raise ValueError('Window is too short to resolve the motion band')


def signature(recording):
    return {key: recording.metadata.get(key) for key in
            ('source', 'link_id', 'extractor', 'channel', 'geometry', 'radio_format')}


def window_features(recording, mask, config):
    t, h = recording.timestamps, recording.csi
    start, last = float(t[0]), float(t[-1])
    count = int(np.floor((last - start - config.window_seconds + 1e-8) / config.hop_seconds)) + 1
    for idx in range(max(0, count)):
        left = start + idx * config.hop_seconds
        right = left + config.window_seconds
        a = np.searchsorted(t, left - 1e-8)
        b = np.searchsorted(t, right + 1e-8, side='right')
        tw, hw = t[a:b], h[a:b]
        row = {'start': left, 'end': right, 'state': 'unknown', 'score': None,
               'quality': 'insufficient_samples', 'frames': len(tw)}
        if len(tw) < 4:
            yield row
            continue
        dt = np.diff(tw)
        rate = float(1 / np.median(dt))
        gap = max(float(dt.max()), float(tw[0] - left), float(right - tw[-1]))
        coverage = min(1.0, float(len(tw) / (rate * config.window_seconds)))
        row.update(rate_hz=rate, max_gap_seconds=gap, coverage=coverage)
        if rate < config.min_rate:
            row['quality'] = 'low_sample_rate'
        elif gap > config.max_gap:
            row['quality'] = 'packet_gap'
        elif coverage < config.min_coverage:
            row['quality'] = 'packet_loss'
        elif np.any(np.mean(np.abs(hw[:, mask]) < 1e-10, axis=0) > 0.1):
            row['quality'] = 'missing_subcarriers'
        else:
            amplitude = np.log(np.maximum(np.abs(hw[:, mask]), 1e-10))
            # Remove packet-wide gain. This intentionally sacrifices common-mode motion.
            amplitude -= np.median(amplitude, axis=1, keepdims=True)
            med = median_filter(amplitude, size=(5, 1), mode='nearest')
            dev = np.abs(amplitude - med)
            mad = median_filter(dev, size=(5, 1), mode='nearest')
            cleaned = np.where(dev > 6 * np.maximum(1.4826 * mad, 1e-4), med, amplitude)
            grid = np.arange(round(config.window_seconds * config.sample_rate)) / config.sample_rate + left
            uniform = np.column_stack([np.interp(grid, tw, col) for col in cleaned.T])
            f, psd = welch(uniform, fs=config.sample_rate, nperseg=len(grid),
                           axis=0, detrend='linear')
            band = (f >= config.low_hz) & (f <= config.high_hz)
            energy = np.sum(psd[band], axis=0) * (f[1] - f[0])
            row.update(score=float(np.quantile(np.sqrt(energy), .75)), quality='ok')
        yield row


def calibrate(recording: Recording, config=None):
    config = config or Config()
    if recording.timestamps[-1] - recording.timestamps[0] < 15:
        raise ValueError('Provide at least 15 seconds of still baseline, preferably 30 or more')
    amplitude = np.abs(recording.csi)
    mask = (np.median(amplitude, axis=0) > 1e-8) & (np.mean(amplitude < 1e-10, axis=0) < .01)
    if mask.sum() < 8:
        raise ValueError('Too few consistently active subcarriers')
    rows = list(window_features(recording, mask, config))
    scores = np.array([row['score'] for row in rows if row['quality'] == 'ok'])
    if len(scores) < 20 or len(scores) < .9 * len(rows):
        raise ValueError('Baseline has insufficient valid windows or poor packet quality')
    center = float(np.median(scores))
    mad = float(1.4826 * np.median(np.abs(scores - center)))
    threshold = max(center + 8 * mad, float(np.quantile(scores, .995)) * 1.5, 1e-3)
    return {'version': 1, 'config': asdict(config), 'signature': signature(recording),
            'subcarriers': recording.csi.shape[1], 'mask': mask.tolist(),
            'threshold': threshold, 'baseline_windows': len(scores),
            'baseline_median': center, 'baseline_mad': mad,
            'claim': 'Channel-change detector; human or through-wall accuracy unverified'}


def analyze(recording, model):
    if model.get('version') != 1:
        raise ValueError('Unknown detector model version')
    if signature(recording) != model['signature']:
        raise ValueError('Calibration and recording source, link or radio geometry differ')
    if recording.csi.shape[1] != model['subcarriers']:
        raise ValueError('Subcarrier count differs from calibration')
    mask = np.asarray(model['mask'], dtype=bool)
    if mask.shape != (model['subcarriers'],) or mask.sum() < 8:
        raise ValueError('Invalid model subcarrier mask')
    threshold = float(model['threshold'])
    if not np.isfinite(threshold) or threshold <= 0:
        raise ValueError('Invalid model threshold')
    rows = list(window_features(recording, mask, Config(**model['config'])))
    if not rows:
        raise ValueError('Recording is shorter than the analysis window')
    for row in rows:
        row['threshold'] = threshold
        if row['quality'] == 'ok':
            row['state'] = 'motion' if row['score'] > threshold else 'still'
    return rows
