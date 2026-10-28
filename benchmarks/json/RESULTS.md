# JSON performance — M0 + field forwarding

The headline result is the saved six-workload series for mutable JSON with field
forwarding, the optimization subsequently integrated into the production backend:
**183.8–329.6 MiB/s**, including **215.9 MiB/s on ASCII**.

Median **core MiB/s**, all six workloads from the same run (higher is faster):

| Workload | Liza M0 + field forwarding | Rust |
| --- | ---: | ---: |
| ASCII | 215.9 | 400.2 |
| Unicode | 234.7 | 500.9 |
| Escapes | 238.7 | 456.0 |
| Numbers | 264.3 | 399.8 |
| Long string | 329.6 | 540.5 |
| Depth 64 | 183.8 | 280.0 |

Apple M4, macOS, Clang 23.1.4; Rust 1.99.1 / LLVM 23.1.3. O2, generic CPU,
shared C ABI without LTO; ~256 KiB documents, 2048-byte chunks, ~16 MiB/sample,
ten shuffled series. Rust uses overflow checks. Both implement scalar streaming
validation; specialized SIMD JSON libraries are outside this comparison.

These are **P3 measurements**, not a newly timed run of today's HEAD. P3-P
subsequently produced byte-identical raw LLVM and identical Mach-O text for the
saved target. It did not repeat throughput timing. This is the strongest saved
series tied to the shipped field-forwarding implementation, not a selection of
per-workload maxima across experiments. Forced `alwaysinline` and oversized
inline-budget ablations are not production results.

Before timing, O0/O2 variants passed 6,785 partition cases each and 738 CLI checks.
Input loading and driver allocation are outside the core timer. Results describe
one machine and this corpus, not general language performance or CLI throughput.

## Evidence and reproduction

- [P3 report, all raw samples and tool versions](https://github.com/rulerom/liza/blob/main/benchmarks/guards/results/apple-m4-llvm23/report.json)
- [P3 sources, binaries, IR and assembly](https://github.com/rulerom/liza/blob/main/benchmarks/guards/results/apple-m4-llvm23/evidence.tar.gz)
- [P3 hashes](https://github.com/rulerom/liza/blob/main/benchmarks/guards/results/apple-m4-llvm23/manifest.json)
- [P3 reproduction commands](https://github.com/rulerom/liza/blob/main/benchmarks/guards/README.md#reproduce)
- [Production correspondence report](https://github.com/rulerom/liza/blob/main/benchmarks/guards/results/production-macos/report.json)
- [Production integration and its limits](https://liza.rulerom.com/field-forwarding.html)

## Historical baseline

The [original A0 series](https://github.com/rulerom/liza/blob/main/benchmarks/json/results/apple-m4/README.md) is pinned to `b320611`, before
mutable JSON and the later lowering improvements. It is retained to reproduce
the investigation, with original reports, raw samples and IR unchanged. It must
not be cited as the current compiler's throughput. The runner in this directory
still reproduces that fixed baseline; use the P3 instructions above for this table.
