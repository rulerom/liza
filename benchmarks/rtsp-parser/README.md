# RTSP parser field-borrow experiment

Compare the merged #99 O2 binary with the field-borrow candidate against the
same live RTSP camera and ordinary VG account. No media capture or workload
generator is used. Camera pacing and scene complexity remain uncontrolled;
this is whole-process diagnostics, not a capacity or delivery benchmark.

```sh
python3 benchmarks/rtsp-parser/paired.py \
  --baseline /absolute/path/baseline \
  --candidate /absolute/path/candidate \
  --config /private/path/rtsp.json \
  --output /absolute/path/new-results-directory \
  --duration-ms 60000 --pairs 3
```

The harness requires macOS `/usr/bin/time -l`. It runs AB, BA, AB for three
pairs, with identical configuration except the fixed run duration. Each
process completes teardown before the next starts. Binary SHA-256 is checked
before and after each trial. Credentials stay in a temporary 0600 config and
are not copied into the report. Source/binaries must remain unchanged; do not
run compilers, tests or another publisher concurrently with measurements.

`results.json` records per-run input PPS, local-send counters, total CPU,
CPU per observed input packet and maximum RSS, with per-variant medians.
Startup, first-IDR gating, RTSP/WSS control and shutdown are included in CPU.
The input counter starts when the VG binding is ready, so CPU/input is a
normalization of the whole run, not isolated packet-processing latency.
Packet loss, delivery latency and the number of copied bytes are not measured.

The candidate changes only field-borrow handling and RTSP parser use. RTP
bridge, H.264 rules, VG signaling, OS adapters and Reactor are unchanged.
Structural acceptance checks the actual application IR: no parser snapshots,
no loop-carried large Event, and a loan of the existing parser field. The RTP
payload-byte helper and Wire mutation helper contain no copy calls at O0/O2.
A completed RTSP header still creates one independent snapshot for parsing;
packet/response events and per-step owners still have ordinary value semantics.

## Apple M4 result

[`results-macos-m4.json`](results-macos-m4.json) preserves all six final trials,
binary/source hashes, compiler version and separate stack-sampling counts.
The baseline is merged #99; both programs were built at O2. Three 60-second
pairs ran in AB, BA, AB order without concurrent builds/tests. Preliminary
candidate runs and an interrupted initial trial are excluded.

| Median | Baseline | Field-borrow candidate |
| --- | ---: | ---: |
| CPU cores, whole process | 0.728 | 0.238 |
| CPU µs / observed input | 3497.9 | 1152.0 |
| Observed input packets/s | 208.17 | 207.89 |
| Maximum RSS, MiB | 14.94 | 14.86 |

CPU per observed packet decreased by approximately 3.04×. No capacity gain is
claimed: the live camera offered a similar rate, not an increasing load. All
six runs exited normally, had no input sequence discontinuities, and every
attempted local send was accepted by the OS. RSS is effectively unchanged.

Separate 10-second samples at 1 ms during 30-second sessions showed memmove
at 77.1% → 28.0% and poll at 21.8% → 69.0% of main-thread samples. These are
wall-clock samples, not exact CPU percentages. Remaining copies mainly appear
in VG socket/owner steps; this change leaves those paths untouched.
