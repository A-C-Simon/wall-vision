"""Metrics exclude windows crossing label boundaries and count abstentions."""

import math


def evaluate(rows, intervals, time_origin=0., guard_seconds=0.):
    if not math.isfinite(guard_seconds) or guard_seconds < 0:
        raise ValueError('Guard time must be finite and nonnegative')
    intervals = sorted(intervals, key=lambda x: x['start'])
    previous_end = -math.inf
    for interval in intervals:
        start, end = float(interval['start']), float(interval['end'])
        if not math.isfinite(start + end) or start < previous_end or end <= start:
            raise ValueError('Ground-truth intervals must be finite, ordered and nonoverlapping')
        if interval['label'] not in ('still', 'motion'):
            raise ValueError('Ground-truth labels must be still or motion')
        previous_end = end
    counts = dict(tp=0, tn=0, fp=0, fn=0, unknown_motion=0, unknown_still=0, excluded=0)
    for row in rows:
        start, end = row['start'] - time_origin, row['end'] - time_origin
        match = next((x for x in intervals if start >= x['start'] + guard_seconds - 1e-8
                      and end <= x['end'] - guard_seconds + 1e-8), None)
        if match is None:
            counts['excluded'] += 1
            continue
        actual, predicted = match['label'], row['state']
        if predicted == 'unknown':
            counts['unknown_' + actual] += 1
        elif predicted not in ('still', 'motion'):
            raise ValueError('Unknown prediction state')
        elif actual == 'motion':
            counts['tp' if predicted == 'motion' else 'fn'] += 1
        else:
            counts['fp' if predicted == 'motion' else 'tn'] += 1
    valid = sum(counts[x] for x in ('tp', 'tn', 'fp', 'fn'))
    eligible = valid + counts['unknown_motion'] + counts['unknown_still']

    def divide(n, d):
        return n / d if d else None

    return {**counts, 'eligible_windows': eligible, 'valid_windows': valid,
            'valid_coverage': divide(valid, eligible),
            'motion_recall_on_valid': divide(counts['tp'], counts['tp'] + counts['fn']),
            'motion_recall_including_unknown': divide(counts['tp'], counts['tp'] + counts['fn'] + counts['unknown_motion']),
            'false_positive_rate_on_valid': divide(counts['fp'], counts['fp'] + counts['tn']),
            'note': 'Overlapping windows are correlated; these are descriptive window metrics, not independent trials'}
