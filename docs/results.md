# Verification results

Checked on 2026-10-08.

## Local hardware

The read-only [hardware report](../reports/hardware.json) identifies the Realtek RTL8821CE PCI adapter and `rtw_8821ce` driver. No supported CSI exporter was identified. Generic netlink is inaccessible in this execution environment, and `/proc/net/wireless` provides no measurement rows. No router, interface, driver, power, or network settings were changed.

Live CSI capture, local human detection, and local through-wall sensing are **not verified**. The original hardware-only objective remains unmet.

## Recorded CSI

The [public benchmark](../reports/public-benchmark.json) uses three ESPectre numeric captures at pinned revision `12fce9354d3506290e70a853a4f22866f0e987ef`. Source URLs and hashes are recorded in the report. The [offline viewer](../reports/public-benchmark.html) shows per-window scores and quality states.

The first 60 seconds of a stationary-person recording fit the threshold. The held-out tail begins at 65 seconds, leaving a five-second separation. Moving-person and empty-room recordings are separate files from the same receiver and channel. The selected files are initial development checks, not a broad independent benchmark.

| Recording | Evaluated windows | Motion decisions | False positives | Unknown |
| --- | ---: | ---: | ---: | ---: |
| Stationary person, held-out tail | 226 | 0 | 0 | 0 |
| Moving person, separate recording | 176 | 97 | Not applicable | 0 |
| Empty room, later recording | 236 | 0 | 0 | 0 |

Motion-window recall is **55.1%**, with **0/462 false positives** on the selected still windows and 100% valid coverage. Overlapping windows are correlated. Labels cover entire recordings and do not annotate brief pauses. Wall geometry is not established by these files, so these results are not evidence of local through-wall performance. The 90% recall acceptance target is not met.

The detector threshold and feature settings were fixed before processing these captures. The high-frequency aliasing regression was found and fixed using generated signals, before the recorded-data benchmark.

## Software checks

All 24 unit and CLI tests pass. They cover independent synthetic motion and still recordings, gain changes, random packet phase, aliasing, packet gaps, sparse sampling, null carriers, malformed values, clock reset and wraparound, changing links, unsafe NumPy object arrays, label boundaries, abstentions, and calibration-file evaluation rejection.

The editable package installs in `.venv/` using the existing NumPy 1.26.4, SciPy 1.15.3, and setuptools 59.6.0. The command entry point and launcher run successfully. The environment inherits system packages; `pip check` reports existing version conflicts in `ros2-numpy` and `pipx`. This work does not modify those packages.

The report's JavaScript syntax, recording selector, score rendering calls, and pointer handler are checked with Node and a minimal DOM harness. No browser runtime was downloaded. Browser appearance has not been visually inspected in this session.

Synthetic scores verify implementation mechanics only. They do not validate radio propagation or human detection. The raw public captures can be processed using the benchmark command in [recordings.md](recordings.md).

## What is needed next

A supported source must first provide real CSI. Existing public extraction tools do not support the attached Realtek adapter. A compatible additional receiver or adapter would change the equipment constraint and is not installed or configured here. With such a source available, collect three controlled local sessions with a person behind the wall and evaluate them separately from calibration. Keep the router and existing Wi-Fi connection unchanged.
