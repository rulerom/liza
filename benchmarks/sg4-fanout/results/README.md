# Measurement evidence

- `macos-nb1.json.gz`: 30 trials, M4 macOS host loopback, revision `1d26433`.
- `linux-vm-nb1.json.gz`: 30 trials, ARM64 Colima VM loopback, revision `e1a3d20`.
  **Do not interpret its rusage RSS fields as isolated service memory.** Linux
  carries launcher history across exec; see the report and memory follow-up.
- `linux-vm-memory.json.gz`: separate one-repeat 10k follow-up using post-exec
  `/proc/PID/status` VmHWM/VmRSS, revision `381251b`. Not part of the main series.
- `liza-macos-sample.txt.gz`, `c-macos-sample.txt.gz`: separate two-second stack
  profiles of the same macOS binaries at 10k offered input/s, outside main trials.

Read JSON with `json.loads(gzip.decompress(path.read_bytes()))`. Tables in
[the report](../../../docs/sg4-a2-rtp-fanout.md) use medians of each variant/rate's
five samples, not percentiles pooled across trials. Each sample retains delivery
coverage, per-receiver counts, delivery/cycle histograms, timings and resources.

The manifest records SHA-256 of generated source/LLVM, benchmark/runtime inputs
and binaries, exact build commands and generated endpoint configurations. Raw
per-packet timestamps, actual binaries and generated source trees are retained
in the original run directories, not committed (the report includes their hashes):

- `/private/tmp/sg4-macos-nb1`
- `/private/tmp/sg4-linux-nb1`
- `/private/tmp/sg4-linux-memory`
- `/private/tmp/sg4-macos-profile`

These local directories are temporary, not permanent public artifact hosting.
A fresh reproduction generates new endpoint ports, binary hashes and raw records;
within one invocation all repeats reuse one configuration and binary pair.
No 60-second or physical-network result is claimed by these archives.
