# M0 JSON comparison

Run from a committed implementation snapshot:

```
python3 benchmarks/mutable/run.py --candidate HEAD --output /tmp/liza-m0-study
```

Requires Clang, Clang++ and Rust. `--check-only` runs all correctness and diagnostic
checks without timing. The runner archives baseline `b320611`, A3 `b210c9f` and
the candidate commit. Existing baseline files/reports are not modified. Every
variant uses the same scalar algorithm, driver, corpus, chunk size and target.
M0 changes the explicit mutation semantics and its bridge writes directly to the
state; its Semantic IR is intentionally different.

All partitioned probes and CLI/error-offset cases must agree before timing.
Ten randomized samples per implementation/workload are core-only (init/feed/
status/finish included), with ~256 KiB inputs, 2048-byte chunks and a warmup.
Report tools, commits, raw samples and artifact hashes. Counter builds instrument
optimized LLVM memcpy/memmove at O0 and are never timed; scalar/register copies
are not counted. There is no timing threshold or universal performance claim.
