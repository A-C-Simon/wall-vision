# Wall Vision

Wi-Fi CSI motion sensing tools and research.

**Current hardware cannot supply CSI through an identified supported tool. Live through-wall detection has not been demonstrated.** This computer has a Realtek RTL8821CE adapter. The research and compatibility findings are in [docs/research.md](docs/research.md).

The software reads recordings and fits a motion threshold from a separate still baseline. It does not change router settings, Wi-Fi channels, interface modes, drivers, or power settings. It does not inject frames or generate probe traffic. Motion output indicates channel changes, not a person's identity or position.

The repository is inside `wall-vision/` because the workspace root has a protected `.git` directory.

```bash
cd /home/ac/Wall_vision/wall-vision
./run.sh doctor
./run.sh demo
python3 -m unittest discover -s tests -v
```

The demo writes generated data and an offline report to `runs/demo/report.html`. It is explicitly synthetic.

Recorded-data replay detected **97/176 motion windows (55.1%)**, with **0/462 false positives** in selected stationary and empty-room windows. This is below the proposed sensitivity target. The public recordings do not establish performance through a wall in this home.

- [Research and hardware compatibility](docs/research.md)
- [Recording formats and commands](docs/recordings.md)
- [Results and remaining work](docs/results.md)
- [Public replay report](reports/public-benchmark.html)

All capture files and local runs are ignored by Git. Only derived public benchmark results are committed. Firmware installation and radio configuration are outside the implemented workflow.
