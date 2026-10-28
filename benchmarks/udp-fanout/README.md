# Single-thread RTP fanout: Liza and C

This first real-UDP comparison runs the **same single-thread application
contract** on C and Liza: one IPv4 loopback socket, 1–64 static IPv4 loopback
receiver addresses, a 2048-byte receive buffer, RTP v2 header/CSRC/extension/
padding validation, one configured author SSRC and delivery of the unchanged
packet to each receiver. Both do O2 native builds, use one bounded packet buffer,
scan the active receiver slots and send sequentially. SSRC is a full u32; the
packet limit is 1..2147483647. No generated payload is copied to a second user
buffer by fanout. Kernel copying, compiler-generated copies and allocations
are **not instrumented**.

Both consume exactly the requested number of incoming datagrams in normal
operation. A malformed, nonmatching SSRC or truncated datagram counts toward the
input limit but is not forwarded. On receive error both exit status 3 immediately;
on send error they attempt remaining destinations for that packet and then exit
3. Bad command-line arguments exit 2. These runtime failure paths have **not yet
been verified with fault injection**. This is not the VideoGrace Translator:
it has no live receiver registration, NAT rebinding, RTCP handling, encryption,
HTTP or multithreading. The C reference currently uses POSIX sockets and is not
built on Windows.

## Run

Requires Python, Clang and POSIX socket support. All sockets are loopback and
nothing is sent over the physical network. Run from repository root:

```sh
python3 benchmarks/udp-fanout/run.py --output /tmp/fanout-check.json --check-only
python3 benchmarks/udp-fanout/run.py --output /tmp/fanout-pilot.json --receivers 16 --packets 100 --pps 100 --repeats 3
```

Use fresh output paths. Before any timed runs, the same independent gate is run
on both binaries, checking full 32-bit SSRC and a mix of valid/invalid RTP,
CSRC, extension, padding, oversized and empty datagrams. It verifies recipient
bytes and source port and rejects missing, duplicate or unexpected deliveries.
Normal samples also require every expected output; a lossy run is rejected, not
reported as faster. Variant ordering is deterministically shuffled each repeat.
Raw per-datagram latency, flags, tool versions and hashes are saved in JSON.

A sample measures paced input and collection with a Python client/collector on
the same host. `elapsed_including_drain_s` includes deliberate pacing and drain;
**it is not throughput**. Latencies include scheduler, network stack and Python
collector. One host, low packet rate, limited repetitions and the Python GIL
preclude a performance-parity conclusion. These samples are useful to validate
the setup, not to claim maximum capacity or tail-latency guarantees. Separate
load generator, independent network, offered/accepted/delivered packet rates,
CPU by process, syscall counts, loss accounting and broader repeated workloads
are required for a benchmark; the 100-Mbit LAN would cap results.
