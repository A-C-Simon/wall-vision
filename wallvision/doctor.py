"""Read hardware information without configuring any interface."""

import platform
import subprocess
from pathlib import Path


def read_text(path):
    try:
        return Path(path).read_text().strip()
    except OSError:
        return None


def command(args):
    try:
        result = subprocess.run(args, capture_output=True, text=True, timeout=5)
        return {"returncode": result.returncode,
                "stdout": result.stdout.strip(), "stderr": result.stderr.strip()}
    except (OSError, subprocess.TimeoutExpired) as exc:
        return {"returncode": None, "stdout": "", "stderr": str(exc)}


def diagnose():
    adapters = []
    for interface in sorted(Path('/sys/class/net').iterdir()):
        if not (interface / 'wireless').exists():
            continue
        device = interface / 'device'
        driver = device / 'driver'
        vendor, product = read_text(device / 'vendor'), read_text(device / 'device')
        is_realtek = vendor == '0x10ec' and product == '0xc821'
        adapters.append({
            "interface": interface.name, "pci_vendor": vendor, "pci_device": product,
            "driver": driver.resolve().name if driver.exists() else None,
            "operstate": read_text(interface / 'operstate'),
            "csi_support": "no supported public extractor identified" if is_realtek
                           else "requires chipset and extractor verification",
        })
    wireless = read_text('/proc/net/wireless')
    rows = [] if wireless is None else [line for line in wireless.splitlines() if ':' in line]
    iw = command(['iw', 'dev'])
    # Do not include iw output, which contains interface MAC addresses, in public reports.
    return {
        "kernel": platform.release(), "adapters": adapters,
        "proc_wireless_measurement_rows": len(rows),
        "iw_readable": iw['returncode'] == 0, "iw_error": iw['stderr'],
        "csi_live_verified": False, "network_configuration_changed": False,
        "status": "CSI source required; this command does not collect CSI",
    }
