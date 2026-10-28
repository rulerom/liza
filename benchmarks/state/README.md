# P2 — State Representation & Alias Analysis

Diagnostic only. No production backend, Core, runtime or JSON algorithm changes.
The primary run uses Homebrew Clang 23.1.4 for Liza and the shared driver. Rust
1.99.1 reports LLVM 23.1.3: same major version, not identical compiler/pass pipelines.
An Apple Clang 21 control is measured in the same randomized timing series.

```sh
python3 benchmarks/mutable/run.py --candidate 899855a4833dd43e32398eed65401888bb7883c8 --output /tmp/p2-clang21 --check-only
PATH=/opt/homebrew/opt/llvm/bin:$PATH python3 benchmarks/mutable/run.py --candidate 899855a4833dd43e32398eed65401888bb7883c8 --output /tmp/p2-clang23 --check-only
PATH=/opt/homebrew/opt/llvm/bin:$PATH python3 -m unittest discover -s tests -v
PATH=/opt/homebrew/opt/llvm/bin:$PATH python3 benchmarks/state/test_controls.py
PATH=/opt/homebrew/opt/llvm/bin:$PATH python3 benchmarks/state/regressions.py --output /tmp/p2-regressions
PATH=/opt/homebrew/opt/llvm/bin:$PATH python3 benchmarks/state/run.py --reference /tmp/p2-clang23 --control-reference /tmp/p2-clang21 --output /tmp/p2-results
```

Select Apple Clang explicitly through PATH for the first reference if the shell
already defaults to LLVM 23. Use fresh directories. Finish correctness tests before
starting timing. The existing runner requires sysctl access to record hardware.

## Experiments

- Default: unchanged emitted IR and the selected Clang O2 pipeline.
- Scalar: split nonvolatile loads/stores of integer-only named structs into typed
  field GEPs, loads, extractvalue/insertvalue and stores. No resource/pointer fields,
  volatile or atomic accesses are transformed. Padding is not a logical field.
- Alias: `noalias` only on the state parameter of the C benchmark `stream_feed`
  boundary. The driver allocates live input and state independently. This is a
  sufficient closed-harness precondition, not a theorem about all mutable borrows.
- Staged: the same Clang runs O1 to IR, then the requested O0/O2 pipeline. This
  tests standard pass ordering, not a custom invariant-based check elimination.
  Its O0 result has already undergone O1; it is not an unoptimized source baseline.
- Cost400 and scalar/alias + cost400: explicit P1 controls to separate call-boundary
  effects from state representation. No source-function-name selection.

All variants pass independent expected JSON outcomes/offsets at O0/O2 before
measurement. Traps, snapshot and effect tests run through scalar/staged wrappers.
Alias tests include separate inputs, overlapping inputs routed to an unannotated
fallback and a deliberately incorrect noalias call. The latter is LLVM UB and is
only a negative control: its different optimized result demonstrates why an
attribute cannot be attached without proving its precondition.

## Traffic measurement

Instrument **already optimized IR**, compile counters at O0 and never time them.
During `stream_feed`, record loads/stores whose entire accessed allocation span is
inside the known state allocation; record starting byte offsets as physical
locations, not a cross-language logical-field mapping. Locals, input and bulk
intrinsics are not included in these state-access counts. Counters also record
executed conditional IR transfers and overflow intrinsics during feed and callees.

Aggregate access spans include padding; splitting an aggregate can reduce counted
span bytes without reducing real CPU traffic. A vector or aggregate load counts as
one IR operation. These are neither hardware load/store instructions nor cache
traffic/cycles. Rust can express overflow checks using comparisons and branches;
zero overflow-intrinsic executions does not mean zero overflow checks. Branch
counts likewise do not identify which guards are redundant.

Counter builds drop conflicting memory/capture/alias annotations introduced before
instrumentation, preserving intrinsic identifiers. Their outputs are checked on
the complete partitioned probe and all six workloads. Native fixture tests check
known counts and a regression ensures `llvm.experimental.noalias.scope.decl` is
not mistaken for a parameter attribute.

Rust's optimized IR uses newer lifetime-intrinsic signatures; its untimed counter
build uses `--rust-counter-clang` (default Homebrew LLVM path). Timed Rust is always
the original rustc binary. Timing builds never contain counter instrumentation.

Ten randomized series, six ~256 KiB workloads, 2048-byte chunks, ~16 MiB per sample,
shared C ABI without LTO. Input allocation/file reading outside timing; init/feed/
finish inside. Raw samples, IR, assembly, binaries, source snapshots, counters,
tool versions and hashes are retained. No performance threshold/new CI workflow.
