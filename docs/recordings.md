# Recordings and local use

## Run the tools

This computer already has compatible NumPy and SciPy versions. From the repository directory:

```bash
./run.sh doctor
./run.sh demo
python3 -m unittest discover -s tests -v
```

The demo writes generated recordings, labels, a fitted model, and an offline plot to `runs/demo/`. It is a software check. It does not measure the Wi-Fi link.

For a separate local Python environment using the installed scientific packages:

```bash
python3 -m venv --system-site-packages .venv
.venv/bin/python -m pip install --no-build-isolation --no-deps -e .
```

The installed command is `.venv/bin/wallvision`. No global Python packages, drivers, services, or network configuration are changed.

## Portable CSI format

JSONL begins with a metadata row:

```json
{"format":"wallvision-csi-v1","source":"measured","link_id":"room-link-1","extractor":"your-extractor","channel":4,"geometry":"64 LLTF bins"}
```

Each subsequent row contains `timestamp` in seconds, `real`, and `imag`. Both arrays must have the same length, at least eight entries, and fixed subcarrier order. They represent complex channel coefficients, not RSSI. The arrays may flatten a fixed antenna layout, but that layout must remain consistent across calibration and test. Use a receiver clock or accurate packet capture timestamps. Do not create timestamps from an assumed packet rate.

Use `source: synthetic` for generated signals. Models calibrated on synthetic data cannot process measured data. Timestamps must strictly increase, and values must be finite. Mixed links, channel changes, reboots, and geometry changes require separate recordings and recalibration. Metadata should use a pseudonymous link name rather than a MAC address or SSID.

## Import a measurement

Classic ESP32 signed-byte CSI CSV:

```bash
./run.sh import-esp data/still.csv data/still.jsonl --link-id room-link-1
./run.sh import-esp data/walking.csv data/walking.jsonl --link-id room-link-1
```

The CSV must contain the header emitted by the firmware. Log lines are ignored. The parser uses `local_timestamp` in microseconds, unwraps a uint32 rollover, checks consistent radio geometry, and keeps the first 64 complex LLTF entries. It masks the first two entries in every packet to avoid the invalid first word described in [Espressif's documentation](https://docs.espressif.com/projects/esp-idf/en/v5.0/esp32/api-guides/wifi.html#wi-fi-channel-state-information). New packed CSI encodings and gain-compensated values outside the signed-byte range are unsupported. Use this importer only for a confirmed classic signed-byte LLTF layout.

For numeric ESPectre format 1.2 HT20 captures:

```bash
./run.sh import-espectre data/static.npz data/still.jsonl
./run.sh import-espectre data/motion.npz data/walking.jsonl
```

This importer preserves `wifi_rx_ts_us`, checks a fixed channel and HT-LTF format, and never enables NumPy pickle loading. It does not contact the endpoint saved in the original capture. Endpoints and network addresses are omitted from exported metadata.

## Fit and evaluate

Record at least 30 seconds of still baseline when possible. The minimum accepted duration is 15 seconds, and at least 90% of baseline windows must be usable. Then analyze a separate recording:

```bash
./run.sh calibrate data/still.jsonl --model runs/room-model.json
./run.sh analyze data/walking.jsonl --model runs/room-model.json \
  --output runs/room-result.json --html runs/room-report.html
```

The default window is 2 seconds, advanced by 0.5 seconds. It uses a 0.7 to 8 Hz motion band, a 50 Hz analysis grid, a minimum input rate of 20 Hz, and a maximum tolerated gap of 0.25 seconds. Packet-wide log-amplitude mean subtraction removes shared gain changes. Polyphase resampling suppresses aliasing before downsampling. The 75th percentile of per-subcarrier band RMS is compared with a frozen baseline threshold. No test labels are used to fit the threshold.

The threshold is the maximum of `median + 8 * scaled_MAD`, `1.5 * baseline_99.5th_percentile`, and `0.001`. It is deliberately conservative. It is a change score, not a probability. Current public-data sensitivity is below the acceptance target. Common-mode normalization also removes real motion that affects all carriers similarly.

Output states are `motion`, `still`, and `unknown`. Missing active subcarriers, poor sampling, or large gaps produce `unknown`. A still decision does not establish absence of a stationary person. Moving objects other than people can trigger the detector.

For a physical experiment, label elapsed seconds from the first frame in the test recording:

```json
[
  {"start":0,"end":30,"label":"still"},
  {"start":30,"end":60,"label":"motion"},
  {"start":60,"end":90,"label":"still"}
]
```

Save this as `data/labels.json` and pass `--labels data/labels.json`. Add `--guard-seconds 1` to exclude a second on both sides of each labeled interval. Windows crossing interval boundaries are excluded. Metrics report valid coverage, recall among valid windows, recall with unknown windows counted as misses, and false-positive rate. Evaluating the exact calibration file against labels is rejected. Use a separate session for an independent final test.

## Public replay benchmark

```bash
python3 scripts/benchmark_public.py
```

The script downloads three pinned public captures at a bounded 256 KiB/s, verifies SHA-256 checksums, and writes `reports/public-benchmark.json` and `reports/public-benchmark.html`. It downloads files from GitHub only. It never contacts a router or a device endpoint.

The captures are already available on this computer in `/tmp/wallvision-datasets/`. To rerun without downloading:

```bash
python3 scripts/benchmark_public.py --directory /tmp/wallvision-datasets --no-download
```

Raw captures are ignored by Git. Public reports contain derived scores, counts, and source links. Review metadata before publishing recordings from your own environment. The public dataset remains at its original source; no third-party firmware or algorithm code is bundled here.
