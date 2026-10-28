# L4 TCP relay benchmark — exploratory loopback pilot

Builds the current Liza `liza_proxy_ops.liza` and a small C poll relay at O2,
then uses the same Python clients and echo server for both. One and eight
simultaneous pairs; 1 MiB each way for throughput, and 100 sequential 64-byte
round trips per connection for latency. Every received byte is checked; both
ends must observe EOF after half-close. Each case starts a fresh proxy. Cases
are shuffled with a recorded deterministic seed and repeated five times.

```sh
python3 benchmarks/network/run.py --output /tmp/liza-network.json --repeats 5
```

The destination must not exist. Requires Python, Clang and POSIX loopback.
Report includes every sample, command, compiler version, commit, dirty-tree
status and SHA-256 of benchmark sources and binaries. Throughput is bytes in
**one direction** divided by total wall time including connection setup and
cleanup; echo traffic carries the same bytes in the other direction. The timing
includes client threading and server costs. Latencies are application round trips;
there are 500 samples at one client or 4000 at eight across five repeats.

This is **not yet an equivalent production service comparison**: C has the same
pair and queue bounds and FIN-after-drain rule, but lacks Liza's connect and idle
deadlines, bounded shutdown, counters and exact error handling. It also does not
replicate every reactor scheduling detail. No fair overhead attribution or NIC
throughput claims can be made from it. The 1 MiB test is short and sensitive to
scheduler and process startup; the eight-client run is a shared-machine Python
load generator, not a controlled open-loop latency experiment. CPU, RSS, syscall
counts and slow-reader cases are not measured. Neither runtime nor external
network is isolated. Do not publish p99 as a service-level latency guarantee.

Next: validate equivalent lifecycle semantics and negative cases, longer steady
state, slow clients/backpressure, per-process CPU/RSS, and a separate load
machine before treating results as a comparative L4 baseline.
