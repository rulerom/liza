# Performance Parity P1 — bounded inlining experiments

No production compiler or language changes. Apple Clang 21 / macOS ARM64 only
for this measured slice; LLVM tuning options are version-dependent internal knobs.

```sh
python3 benchmarks/mutable/run.py --candidate 899855a4833dd43e32398eed65401888bb7883c8 --output /tmp/p1-reference --check-only
python3 benchmarks/inlining/test_policy.py
python3 benchmarks/inlining/regressions.py --strategy cost-400 --output /tmp/p1-regressions
python3 benchmarks/inlining/run.py --reference /tmp/p1-reference --output /tmp/p1-results
python3 benchmarks/inlining/verify_results.py /tmp/p1-results
```

Run regressions before timing, not concurrently. The runner verifies that the
current compiler/examples match the reference commit, reference artifact hashes,
and Clang version. Sources and binaries from the original P0 reference are not
modified. The snapshot retains the same checked algorithm and Rust comparator.

Strategies: LLVM default; thresholds 400/600/3000 with `inline-max-stacksize=256`;
small pure acyclic Semantic IR functions receiving an LLVM `inlinehint`; and an
excessive threshold 50000 as a negative control. The default LLVM threshold is
225 in this pinned toolchain. Neither the cost policy nor the guided selector
contains JSON library names. The separately labelled P0 control deliberately
repeats the previous name-selected experiment, solely as a same-session ceiling.

Guidance requires <=160 Semantic IR operations, <=64 blocks, a caller in the
Semantic IR module, no CFG cycle and no recursive call closure. Only inline hints
are added; instruction text must otherwise match. LLVM remains free to decline.
The guided experiment was added after the threshold sweep showed that comparable
P0 gains needed over 100% JSON object text growth. These cutoffs are experimental,
not validated universal choices.

Each candidate object passes an explicit gate relative to default:

- `__TEXT,__text` <=125% of the default object section.
- Every function frame <=max(256 bytes, twice that function's default frame).
- Only static frame records are accepted by this diagnostic harness.

`inline-max-stacksize` is a callee heuristic, not an aggregate stack budget; the
post-codegen frame check is separate. Frames are not whole-program peak stack.
The gate checks object text including retained functions, not I-cache misses or
runtime/library text. Rejected variants copy the **actual default object** into
`selected.o`; `verify_results.py` verifies the bytes, hashes and a disabled-gate
mutation. Raw timings of rejected variants are diagnostic only. Their effective
policy uses default performance. This two-build approach adds compile cost; it is
not yet a production implementation or a hard compilation-time bound.

Builds include full RTP parser, actual relay application and a generated Liza
stress program: 48 callers of a 64-branch pure function. Compile-time measurements
are three warm repetitions per object, excluding source lowering and linking.
Timings are descriptive and not randomized compiler-throughput experiments.

JSON agreement: 6785 partitions per executable, O0/O2 for all six strategies,
Rust and original CLI; all timing documents checked. Ten randomized series of
~16 MiB samples over six workloads, same C driver and 2048-byte chunks as P0.
Core clock includes init/feed/finish; no profile instrumentation. 480 raw samples.

Existing regression suites run through a Clang wrapper that injects the candidate
flags only for O2 compilation of `.ll` inputs. O0 stays unchanged. The wrapper logs
actual injections; the suites cover snapshots, trap/effect order, RTP and real
TCP relay, including fault injection. These tests do not measure RTP/relay speed
or establish new formal guarantees.

The report and archive retain source snapshots, emitted IR, optimized IR,
assembly, object/selected-object hashes, executables, compile times, stack records,
regression logs and raw timing samples. There is no new CI workflow or timing gate.
