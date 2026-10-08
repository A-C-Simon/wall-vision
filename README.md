# Wall Vision

Wi-Fi CSI motion sensing tools and research.

**Current hardware cannot supply CSI through an identified supported tool. Live through-wall detection has not been demonstrated.** This computer has a Realtek RTL8821CE adapter. The research and compatibility findings are in [docs/research.md](docs/research.md).

The software reads recordings and fits a motion threshold from a separate still baseline. It does not change router settings, Wi-Fi channels, interface modes, drivers, or power settings. It does not inject frames or generate probe traffic. Motion output indicates channel changes, not a person's identity or position.

The repository is inside `wall-vision/` because the workspace root has a protected `.git` directory.

Usage and verification instructions will be added with the implementation.
