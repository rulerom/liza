# Aggregate lowering: A0–A3

Core-only study on unchanged `json.liza` / `utf8_stream.liza`. The baseline
`b3206117a225f6f852cec5bef18928fe1bd43856` remains immutable.

| Variant | Change |
| --- | --- |
| A0 | Actual original compiler from the pinned baseline |
| A1 | Experimental ABI **annotations** for pointer-free JsonState: readonly/nocapture inputs and noalias sret; the calling convention itself is unchanged |
| A2 | Experimental local update/slot reuse in acyclic functions; immutable call ABI retained |
| A3 | Actual candidate compiler: exclusive whole-value callee variants, composed bottom-up |

A1 and A2 exist only in the study emitter. They are not enabled in the compiler.
The compiler has no JSON-specific optimization or source rewrite. A3 extends
existing storage reuse to acyclic transforms that return the input type directly;
it retains the immutable public version for snapshots and borrowed inputs.

```sh
python3 benchmarks/aggregate/run.py --candidate <commit> --output /tmp/aggregate-study
python3 benchmarks/aggregate/run.py --candidate <commit> --output /tmp/aggregate-check --check-only
```

The output directory must be fresh. The candidate must be a committed snapshot
containing this harness. Clang and Python are required on macOS/Linux; Rust is
not needed for this Liza-only ablation. The source snapshot, explicit target/CPU,
commands and hashes are retained. Parser sources must match the baseline exactly;
Semantic IR must match across all four variants. The common 6,785 partitioned
cases and 615 CLI probes run before any timing, including the candidate's actual
`liza-json` CLI. The earlier C++/Rust baseline stays a separate unchanged report.

Ten seeded, shuffled samples per variant/workload give 240 raw core measurements
on six ~256 KiB documents with 2048-byte chunks. The measurement driver and
warmup follow `benchmarks/json`; no instrumented executable is timed.

## Copy diagnostics

After O2, a separate build inserts a counter immediately before every
`llvm.memcpy` / `llvm.memmove` call in the emitted module. Original transfers,
branches and traps remain. Inferred memory-effect attributes are removed because
the counter writes globals. This diagnostic IR is compiled at O0; its result
must still agree with the expected output. Counts include parser, ABI bridge,
initialization and finish for one warmup plus one complete pass.

These are **dynamically executed optimized-IR bulk-transfer sites and bytes**,
not a count of every physical machine copy. Scalarized loads/stores, register
moves, memcpy lowering choices and other runtime activity are not counted.
Instrumentation changes code generation and timing, hence it is kept separate.
Clang `.su` files report individual frames, not the peak stack across a call chain.

## Recorded evidence

`results/apple-m4/report.json` includes raw samples, commands, correctness,
Semantic IR agreement, per-workload counters and per-function stack records.
`evidence.tar.gz` preserves the four original/optimized/instrumented LLVM modules,
assembly, target metadata and one shared Semantic IR dump. `manifest.json` records
archive and file hashes. Binaries and full source snapshots are retained in the
local run directory, identified by the report; they are not committed.

The recorded candidate is `7c1da5d`; later documentation/CI commits do not change
its compiler. Reproduction is conditional on the recorded OS/toolchain. This is
not a formal proof or a machine-code correctness certificate.
