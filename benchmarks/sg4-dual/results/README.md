# B2 Apple M4 evidence

- `macos-m4.json.gz`: 42 complete trials: two independent stop/fault cases and
  five alternating single/dual pairs at each of four profiles.
- `macos-m4-summary.json.gz`: medians of trial metrics and paired ratios;
  recompute using `../summarize.py` on the decompressed main report.
- `macos-m4-provenance.json.gz`: hardware, run command, source commit verification
  and executable hashes. Application source revision `cfaf8d4` is immutable.

The build began before the git commit completed. Its original baseline commit
is retained, while all 53 repository source hashes were subsequently checked
against `cfaf8d4`; all ten generated source/LLVM/configuration hashes and four
executable hashes also matched. The provenance file makes this distinction
explicit instead of rewriting the build's original revision field.

Raw per-packet records, generator timestamps, generated sources, exact binaries
and manifests are retained locally in the gitignored directory
`/Users/antongolovkov/dev/liza/build/sg4-b2-macos-cfaf8d4` (about 304 MiB), with
an additional original temporary run at `/private/tmp/sg4-b2-macos`. The retained
project directory avoids relying solely on temporary paths. Public Git archives
contain reports and hashes, not the raw packet files or executables; the local
copy is not permanent public artifact hosting.

Read with `json.loads(gzip.decompress(path.read_bytes()))`. CPU totals include
startup/warmup/drain and instrumentation. p99 values are per-trial 100us-bucket
upper bounds, summarized by median; they are not pooled percentiles. Coverage
accompanies latency. Queue count differs between treatments; no physical NIC,
hermetic-host, pure CPU scaling or universal QoS claim is made.
