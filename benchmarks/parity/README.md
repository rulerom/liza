# Performance Parity P0 — JSON ARM64 Investigation

Diagnostic-only inlining ablations on fixed-size, copyable M0 parser state.
No Core, runtime, source algorithm, checked arithmetic or production backend changes.
`alwaysinline` names in this harness select experiments, not a proposed compiler policy.

Requires macOS ARM64, Python 3, Clang and Rust. Use one otherwise idle machine.
Do not run timing and profiling simultaneously. The baseline driver has no LTO;
Rust uses `overflow-checks=yes`, `panic=abort`, generic CPU, O2.

```sh
python3 benchmarks/mutable/run.py --candidate 899855a4833dd43e32398eed65401888bb7883c8 --output /tmp/parity-reference --check-only
python3 benchmarks/parity/test_instrumentation.py
python3 benchmarks/parity/run.py --reference /tmp/parity-reference --output /tmp/parity-p0
python3 benchmarks/parity/profile.py --results /tmp/parity-p0
```

Output directories must be fresh. The first command pins source snapshots and
runs the existing independent expected-results barrier. The second harness checks
reference hashes and Clang version, compiles every ablation at O0 and O2, compares
6785 chunk-partition cases and error offsets per executable, and runs CLI checks
before timing. Each timed workload is separately checked by every executable.

Six ~256 KiB workloads, chunks of 2048 bytes, one untimed warmup per invocation,
ten randomized series, ~16 MiB per timed sample. This is longer than the historical
M0 run's ~4 MiB sample, so use the simultaneous M0/Rust controls, not historical
numbers, to calculate speedups. Init/feed/finish and checksum consumption are
included. File reading and allocation of input/state are outside the timer.

Ablations independently force UTF-8 helper, JSON step or completion helper inline;
`combined` forces all three. The transformation rejects changes beyond inline
attributes. Inlining also changes register allocation and layout; the isolated
speedups cannot be added or treated as exact percentages of call overhead.

Untimed instrumented optimized IR counts function entries, including warmup.
These are not executed ARM64 instruction counts, cache misses, or CPU cycles.
`sample` collects five seconds at 1 ms on ASCII in a separate run; its benchmark
measurements must not be included in throughput summaries. Raw profiles remain
statistical evidence, not cycle-accurate attribution.

`results/apple-m4/report.json` records all 360 samples and command lines.
The compressed evidence contains source snapshots, binaries, LLVM IR, assembly,
stack usage, counter builds, corpus, probes and separate sample profiles.
`manifest.json` hashes every archived file, report and archive. Original baseline
reports are unchanged. No performance threshold or heavy new workflow is added.

The investigation identifies three hot regions and tests their inlining boundaries.
It does not yet prove three independent largest causes of the remaining Rust gap.
See [the report](../../docs/performance-parity.md) for findings and limitations.
