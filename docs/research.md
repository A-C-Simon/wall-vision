# Wi-Fi sensing: findings and implementation decision

Research checked on 2026-10-08. Links point to research groups, papers, tool authors, and driver source. Results in a paper describe its experiment, not this computer.

## What the radio measures

An OFDM receiver estimates a complex channel coefficient for each subcarrier and antenna pair. A simplified model is `H(k,t) = sum_l a_l(t) exp(-j 2 pi f_k tau_l(t)) + noise`. Movement changes the amplitudes and path delays of reflected signals. CSI records those frequency-dependent changes. RSSI compresses received power into a scalar and discards most of this structure. Ping latency measures network delay, not channel coefficients. Neither ping times nor ordinary signal-strength readings reconstruct missing CSI. The distinction and hardware interfaces are explained in the [Tsinghua tutorial](https://tns.thss.tsinghua.edu.cn/wst/docs/tools/) and the [Intel CSI tool](https://dhalperi.github.io/linux-80211n-csitool/).

A receiver estimating CSI internally does not imply that its operating-system driver exports CSI. Monitor mode alone does not provide it. Radio paths can traverse some walls, but metal, reinforced concrete, distance, antenna placement, and unrelated movement affect the result. One radio link measures aggregate changes across its propagation paths. It does not inherently identify a person, locate the changing reflector in a particular room, or produce an image.

## Research that established the field

| Work | What was demonstrated | Why it does not run unchanged on this laptop |
| --- | --- | --- |
| [Wi-Vi, SIGCOMM 2013](https://people.csail.mit.edu/fadel/papers/wivi-paper.pdf) | Moving people behind walls, with interference nulling and motion-based angular processing | Prototype used USRP software radios and coordinated transmit antennas. It was not a stock laptop driver application. |
| [WiSee, MobiCom 2013](https://ubicomplab.cs.washington.edu/pdfs/whole-home-gesture.pdf) | Gesture recognition from small Doppler shifts, including through-wall cases | Proof of concept used a software-radio receiver. Its reported accuracy is for a specific gesture experiment. |
| [Widar2.0 and Widar3.0](https://tns.thss.tsinghua.edu.cn/widar3.0/) | Passive tracking and cross-domain gesture recognition using richer CSI-derived features | Requires CSI recordings, antenna information, geometry, and suitable training or processing. Widar3 recordings include six receivers. |
| [FarSense, 2019](https://arxiv.org/abs/1907.03994) | Respiration sensing with improved range, including a transceiver in another room | Uses the complex CSI ratio of two receiving antennas to suppress shared hardware errors. A single RSSI stream cannot substitute for that measurement. |
| [RF-Pose, CVPR 2018](https://rfpose.csail.mit.edu/) | Through-wall pose estimation using cross-modal training | Uses a specialized radio sensing system, with visual supervision during training. Operating near Wi-Fi frequencies is not the same as using ordinary Wi-Fi channel reports. |
| [DensePose From WiFi, 2023](https://arxiv.org/html/2301.00250v1) | Learned mapping from Wi-Fi CSI to dense body correspondence | Uses 3 transmitting and 3 receiving antennas, 30 subcarrier measurements at 100 Hz, and supervised training. No such input or local trained model exists here. |

The practical first milestone is detecting a change consistent with motion, followed by a controlled experiment to determine whether it tracks a person behind the chosen wall. Identity, head count, silhouettes, precise position, and stationary occupancy are separate tasks. A quiet output is not evidence that a room is empty.

## Extraction options

| Tool | Documented hardware | Implications for the existing network |
| --- | --- | --- |
| [Linux 802.11n CSI Tool](https://dhalperi.github.io/linux-80211n-csitool/) | Intel Wi-Fi Link 5300 | Custom firmware and driver. The project's [FAQ](https://dhalperi.github.io/linux-80211n-csitool/faq.html) says other Intel devices do not work with that firmware. Installing it on the active connection could interrupt service. |
| [PicoScenes](https://ps.zpj.io/) | Intel AX200/AX210, QCA9300, IWL5300 and supported SDRs | Offers associated-AP capture and passive capture on supported devices. Driver installation and monitor-mode configuration are distinct from the sensing algorithm and are excluded from this implementation. Consult current compatibility and licensing before installation. |
| [FeitCSI](https://feitcsi.kuskosoft.com/) | Intel AX200 and AX210 | Open-source CSI extraction, with modified Intel support. It is not a Realtek extractor. Installing drivers or changing the active radio is outside the allowed procedure here. |
| [Nexmon CSI](https://github.com/seemoo-lab/nexmon_csi) | Broadcom bcm4339, bcm43455c0, bcm4358, bcm4365/4366c0 | Firmware patches for particular chips and firmware versions. The existing Realtek chip is not in its supported list. |
| [Espressif ESP-CSI](https://github.com/espressif/esp-csi) | CSI-capable ESP32 boards | Can use an ordinary router and one additional ESP32 receiver. Its router example uses ping replies as received packets. This adds hardware and traffic, so it is a possible next step, not a claim that the current equipment is sufficient. |

Espressif documents dependence on router protocol and placement. Its examples that change channels or use extra transmitters are not appropriate for the requested unchanged-network setup. A USB serial connection can export CSI without sending the measurements over the shared network. Ordinary client association and bounded probe traffic still need to be planned; this repository neither flashes firmware nor starts such traffic.

## This computer

Read-only inspection found PCI `10ec:c821`, Realtek RTL8821CE, using `rtw_8821ce`, and kernel `6.8.0-138-generic`. The interface is visible in sysfs. The execution environment denies generic netlink sockets, and `/proc/net/wireless` contains no measurement rows here. These restrictions also prevent testing a useful live RSSI stream from this session.

The [Linux 6.8 rtw88 debug interface](https://raw.githubusercontent.com/torvalds/linux/v6.8/drivers/net/wireless/realtek/rtw88/debug.c) does not expose a CSI recording endpoint. The [chip driver](https://github.com/torvalds/linux/blob/v6.8/drivers/net/wireless/realtek/rtw88/rtw8821c.c) contains beamforming-related CSI rate configuration; that symbol is not an API that exports subcarrier measurements. Based on those interfaces and the documented hardware lists above, there is no established supported extraction path identified for this adapter. This is a compatibility finding, not a proof that reverse engineering the firmware could never work.

Reverse engineering a new Realtek CSI exporter would be a separate driver/firmware research project, require hardware experiments, and likely interrupt the current Wi-Fi connection. It cannot honestly be promised as a software-only installation under the present constraints.

## Implementation

The local program accepts timestamped complex CSI, checks sample quality, removes null subcarriers and packet-wide amplitude gain, clips isolated amplitude outliers, resamples short timing irregularities, and estimates temporal energy in a configurable motion band using Welch spectra. A frozen threshold is fitted from a separate still recording. Every output window contains a quality status. Gaps and insufficient sampling yield `unknown`, not `still`. Calibration, feature selection, and decision thresholds use only the baseline recording.

The amplitude approach avoids treating unstable raw packet phase as motion. It can miss movement that changes all subcarriers by the same factor, and it cannot distinguish a person from a moving door, fan, pet, or radio. Phase ratios could improve sensitivity with suitable multi-antenna data, but are not fabricated from single-antenna measurements. This is an initial detector, not a reproduction of FarSense or DensePose.

Tests use synthetic CSI with known perturbations to check mechanics and failure handling. A public capture, if accessible, can validate parsing and processing but cannot establish through-wall accuracy without wall and motion ground truth. No simulation score should be interpreted as measured human detection accuracy.

The implementation was also checked against three numeric HT20 captures from the [ESPectre dataset](https://github.com/francescopace/espectre/tree/12fce9354d3506290e70a853a4f22866f0e987ef/data). Its catalog labels stationary presence, motion, and empty-room recordings separately. The numeric files preserve receiver timestamps. The selected replay result is in [results.md](results.md); raw captures remain outside this repository. The initial spectral detector misses many motion-labeled windows, which limits claims about its sensitivity.

## Experiment needed before calling it successful

Keep the router and receiving computer fixed. Record at least 30 seconds of still baseline, then a separate session with alternating still and walking intervals behind the wall. Repeat at different times and include controls: motion on the near side, a door moving, and normal network use. Record wall material, distances, orientation, session labels, and any unexpected events. Keep packet payloads, credentials, SSIDs, and addresses out of the public repository.

Use a held-out session, not overlapping windows randomly split between training and test. Report recall on walking intervals, false alarms on still intervals, unknown coverage, and boundary exclusions. As an initial acceptance target, seek at least 90% recall and at most 5% false positives on fully contained windows, with at least 90% valid coverage over three sessions. These are proposed criteria, not achieved results. Inspect false alarms before changing thresholds, then re-test on a new session.

## Decision

Build and verify the processing software now. Preserve the existing network and driver. Live through-wall motion detection remains blocked by the lack of an exposed CSI source. If hardware may later be added, first examine a CSI-capable ESP32 receiver connected by USB; alternatively use a separate supported Intel adapter with an extractor. Confirm compatibility, traffic requirements, and geometry before buying or changing anything.
