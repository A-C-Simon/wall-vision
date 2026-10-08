"""Deterministic signal fixtures. These are never live Wi-Fi measurements."""

import numpy as np

from .data import Recording


def generate(seed=1, duration=40., rate=50., intervals=(), gain=False):
    rng = np.random.default_rng(seed)
    t = np.arange(round(duration * rate) + 1) / rate
    k = np.linspace(-np.pi, np.pi, 64)
    shape = np.sin(2 * k) + .4 * np.cos(5 * k)
    logamp = np.log(20 + 5 * np.cos(k))[None, :] + rng.normal(0, .002, (len(t), len(k)))
    for start, end in intervals:
        moving = ((t >= start) & (t < end)).astype(float)
        logamp += .16 * moving[:, None] * np.sin(2 * np.pi * 2.3 * t)[:, None] * shape
    if gain:
        logamp += (.5 * np.sin(2 * np.pi * 3 * t) + .1 * (t > duration / 2))[:, None]
    phase = rng.uniform(-np.pi, np.pi, (len(t), 1))
    return Recording(t, np.exp(logamp + 1j * phase), {
        'source': 'synthetic', 'link_id': 'synthetic-link', 'geometry': '64 bins',
        'provenance': 'Generated amplitude perturbations; no wall or person measured',
    })
