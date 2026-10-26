# P3 — Guard & CFG Investigation

Research only. No changes to Core, production backend, JSON source, runtime or CI.
A pure by-value field read crosses aggregate phi nodes; updates of other fields
hide its equality to the original parameter from LLVM. Forwarding the read exposes
the existing `position != U64_MAX` guard to standard Clang O2. Checked arithmetic
is retained in raw LLVM, and LLVM removes the redundant overflow branch.

The policy in `forward.py` has no library/function/field names. It accepts only
copyable flat scalar structs (at most 64 fields, matching by-value backend layout),
value parameters and pure functions. Every phi input must trace to the same root
through updates of other fields. Cycles, differing roots, updated target fields,
resources and mutable/readonly parameters fail closed. This is a deliberately
small experiment, not a production optimizer or a general range analysis.

## Reproduce

Run from the repository root with Python, LLVM/Clang 23, Rust and the Z3 executable
available. The saved macOS run uses Clang 23.1.4, Rust 1.99.1 / LLVM 23.1.3, Z3 5.3.1.
The snapshot is unchanged compiler/stdlib `899855a`; the runner checks that fresh
unmodified LLVM emission exactly matches that frozen reference before timing.

```sh
export PATH=/opt/homebrew/opt/llvm/bin:$PATH
export PYTHONPATH=.
python3 benchmarks/mutable/run.py --candidate 899855a4833dd43e32398eed65401888bb7883c8 --output /tmp/p3-reference --check-only
python3 benchmarks/guards/test_forward.py
python3 benchmarks/guards/run.py --reference /tmp/p3-reference --output /tmp/p3-results
python3 benchmarks/guards/check.py --results /tmp/p3-results
python3 benchmarks/guards/controls.py --results /tmp/p3-results
python3 benchmarks/guards/regressions.py --output /tmp/p3-results/regressions-network
python3 benchmarks/guards/verify_results.py /tmp/p3-results
```

Use fresh output directories. Regression tests require permission to open local
TCP sockets. Run other CPU-intensive work outside timing. The reference runner
requires hardware discovery via sysctl on macOS. Mach-O text inspection in controls
is macOS-specific; no Linux/Windows results are claimed.

The timed variants are default, forwarded fields and Rust. Ten randomized series
of six ~256 KiB documents, 2048-byte chunks, ~16 MiB/sample; same shared C ABI without
LTO, allocation/input reading outside timing. Independent expected outcomes and
absolute error offsets are checked on 6785 partition cases per executable at O0/O2
before timing; 738 CLI checks. Counters reuse P2 instrumentation, compiled at O0
and never timed; their full partition probes must agree with ordinary executables.

`conditional_transfers` and `overflow_intrinsics` count executed optimized LLVM
operations, not hardware branches/mispredictions. State access spans include
padding and are not memory traffic. Rust's zero overflow intrinsics does not imply
zero checks. Raw IR, optimized IR, assembly, binaries and counter outputs are saved.

## Independent check and limits

`symbolic.py` independently interprets the selected original Semantic IR and raw
candidate LLVM into unsigned bitvector/Bool constraints. It handles flat structs,
acyclic CFG, phi, scalar fields, checked add/sub and traps, and rejects unsupported
operations. It does not import the transformation, use its certificates as axioms,
or trust `may_trap`/storage summaries. Z3 checks output equality, trap equality and
path coverage for all input bit patterns, including malformed UTF-8 states.

This establishes the selected raw-IR translation under the interpreter semantics,
not universal soundness of this pass, LLVM optimizations or machine execution.
The interpreters/solver, frontend and tools remain trust boundaries. No Verified
status or `end_to_end_verified` claim changes.

Two negative controls are satisfiable and replayed by independently compiled native
O0/O2 executables: forwarding a field changed on one incoming path, and bypassing
an unconditional increment's mandatory overflow trap. Inputs are explicitly pinned
counterexample witnesses (not claimed solver-discovered models). Multiple live
snapshots across branches are also tested natively. Existing trap/effect/snapshot,
RTP and relay suites run with the transform injected into each LLVM emission.

RTP and relay have zero sites and identical text hashes, so this demonstrates
noninterference, not acceleration of networking. R0/VN0 remain the project priority.
