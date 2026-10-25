# First JSON baseline: Apple M4

One machine, 16 GiB RAM, macOS; Apple Clang 21.0.0 and Rust 1.99.1.
Pinned Liza source: `b3206117a225f6f852cec5bef18928fe1bd43856`.
Explicit host target and generic CPU, O2; Rust overflow checks enabled.
Ten samples per cell, ~256 KiB documents, 2048-byte chunks. Core samples repeat
whole documents to target 4 MiB. These are warm, scalar measurements, not a
cross-machine language ranking. All 6,785 partitioned cases and 615 CLI checks
passed before measurement.

Median **core MiB/s** (higher is faster):

| Workload | Liza | C++ by-value | C++ in-place | Rust |
| --- | ---: | ---: | ---: | ---: |
| ascii | 42.79 | 70.04 | 445.13 | 418.70 |
| depth64 | 29.98 | 69.50 | 305.75 | 283.17 |
| escaped | 55.23 | 68.51 | 529.88 | 471.97 |
| long-string | 65.19 | 70.86 | 632.88 | 589.21 |
| numbers | 39.48 | 70.26 | 436.62 | 423.02 |
| unicode | 55.74 | 71.33 | 539.64 | 522.41 |

State size: Liza/C++ **184 bytes**, Rust **176 bytes**. State layout is measured,
not assumed identical. Clang stack diagnostics for Liza report **4480 bytes** for
`liza___liza_json_step`, **608 bytes** for `liza_json.feed`, and **224 bytes** for
the driver bridge `stream_feed`. These are individual frame sizes, not a sum or
peak call-chain measurement. C++ stack records and all optimized IR/assembly are
included for inspection.

The by-value C++ variant is materially slower than the in-place variant on this
machine. This makes state update/copying a concrete optimization candidate. It
does not by itself establish that every Liza slowdown comes from copying, or
that these speeds generalize beyond the corpus. Static memcpy sites are not
executed copy counts. No compiler optimization is included in this PR.

Raw timings, min/max, CLI results, commands, source/binary hashes and tool versions
are in `results/apple-m4/report.json` and `samples.json`. CLI results include
startup and filesystem costs: C++/Rust share a C I/O driver, while Liza runs its
actual CLI/runtime. They must not be read as isolated parser measurements.
Negative inputs are correctness-only in this initial baseline.
