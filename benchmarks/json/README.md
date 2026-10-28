# JSON benchmarks

**Performance results: [M0 + field forwarding](RESULTS.md), 183.8–329.6 MiB/s
on Apple M4 (ASCII: 215.9 MiB/s).** All six workloads, Rust comparison and
reproducible evidence are linked there.

## Historical baseline harness

The runner below reproduces the original A0 experiment, not current performance.

Equivalent scalar streaming automata, pinned to Liza
`b3206117a225f6f852cec5bef18928fe1bd43856` (before T2-B). This is an experimental
performance baseline, not a general ranking of languages or formal verification.

## Run

Requires Python 3.9+, Git with the pinned commit available, Clang/Clang++, and
Rust. The current driver/build supports macOS and Linux. No package is downloaded
by the runner; missing tools or any result disagreement fail the run.

```sh
python3 -m unittest discover -s benchmarks/json -p test_harness.py -v
python3 benchmarks/json/run.py --check-only -O 0 --output /tmp/json-check-o0
python3 benchmarks/json/run.py --output /tmp/json-baseline --repeats 10
```

Output directories must be new. `--size` selects approximate valid-input size
(default 256 KiB, maximum 8 MiB). Chunk size is 2048 for all timed backends. Each
core sample processes at least one document, targeting 4 MiB total; each sample
includes one untimed warmup. There are at least ten samples per workload/mode/
implementation, scheduled in seeded shuffled order. CLI has a separate warmup.
The input corpus is generated locally with seed 9183 and its hashes are recorded.

## Implementations and agreement gate

- **Liza:** the actual immutable `json.liza` and `utf8_stream.liza` snapshot;
  LLVM bridge only exposes start/feed/status/finish and queries state size.
- **C++ in-place:** explicit scalar port; state updated by reference.
- **C++ by-value:** the same transition body, with state passed/returned by value
  at each JSON/UTF-8 byte update; no artificial `noinline` or forced copy.
- **Rust:** safe scalar parser with checked indexing and overflow checks enabled;
  the small unsafe FFI adapter is exclusively the benchmark driver boundary.

C++ uses checked stack indexing and explicit u64 overflow guards; bounded scalar
arithmetic relies on reachable-state invariants. It does not instrument all
unsigned arithmetic with Liza-style traps. Compiler versions and flags are saved;
Rust uses its own LLVM, not necessarily the same version as Clang. Explicit
host target/ABI and generic CPU flags are used and saved in `liza.target.json`.

All four backends must match expected success/error codes and byte offsets on
123 documents, 6,785 chunk partitions (including bytewise, empty, all single split
positions for small inputs, and seeded variable splits). UTF-8 and escaped
surrogate pairs, depth 64/65, lexical numbers, long tokens and sticky errors are
included. Finish is called between chunks to check it remains a snapshot.

615 CLI cases also check expected exit status and output, including the actual
`liza-json check`. Every timed input is validated by every executable before
measurement. Negative inputs are correctness-only in this first baseline; no
throughput is attributed to unprocessed suffixes of rejected documents. Four
unit controls ensure wrong error kinds, offsets and missing/extra results are
rejected by the agreement gate.

## What is timed

**Core:** shared C driver, preloaded bytes and allocated state, initialization,
chunked feed, pending-status checks, finish and checksum consumption inside a
monotonic timer. No cross-module LTO. File loading, process startup and driver
allocations are outside this timer. Rust/C++/Liza parser paths allocate no dynamic
containers, but allocation counts are not instrumented or claimed as measured.

**CLI:** wall time around a new process, file reading and parser execution, warm
filesystem cache. Liza uses its real application and runtime. C++/Rust use the
same small C file/diagnostic driver, **not independent language-native I/O stacks**.
This intentional asymmetry is reported; CLI measurements cannot isolate parser
cost. CLI startup overhead is substantial for 256 KiB inputs.

RSS is the process high-water mark, including loaded data, driver and runtime;
it is recorded for core processes when supported, not interpreted as parser-only
memory. State byte size comes from each implementation's layout. Static memcpy
and alloca sites in complete optimized IR are diagnostics, not execution counts.
Clang `.su` files give individual function stack frames; they are not peak stack
usage across a call chain. Rust frame sizes are not automatically inferred.

## Evidence and limits

A complete local output retains the source snapshot archive, generated corpus,
probe inputs/results, binaries, LLVM IR, assembly, Clang stack-usage files, raw
samples and `report.json` with commands, tool versions, hashes and machine details.
Reports remain `incomplete` on exceptions; a successful correctness-only run is
`correctness_passed`, never a performance result. CI exercises O0/O2 correctness
on Linux and uploads reports/IR, with no speed threshold on shared runners.

`results/apple-m4/` contains the first fixed-machine report, raw measurements and
IR/assembly diagnostics. Executables and the source archive are not committed;
the report records their hashes and the runner reconstructs them from the pinned
commit. Rebuilding on a different toolchain need not reproduce binary hashes or
absolute timings. This is not a portable proof certificate.

Later M0 and field-forwarding results are reported separately; the runner does
not silently substitute the current working tree for the pinned Liza source.
