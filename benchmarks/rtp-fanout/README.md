# Exploratory UDP fanout prototype

This is a correctness and feasibility probe for the workload of one or two
publishers and many receivers. It is not a benchmark of Liza, VideoGrace or an
RTP implementation. The input is synthetic 1200-byte packets with source,
sequence and monotonic timestamp; no RTP parser or route table is involved.

A POSIX dispatcher receives into one fixed 2048-byte buffer, rejects truncated
datagrams and signals 1/2/4/8 workers. Each worker sends the same immutable
buffer to its fixed subset of receivers through a shared UDP socket. The next
receive waits for every worker: exactly one packet is in flight. A mutex and
condition variables protect publication and completion. This is intentionally
bounded but limits throughput and makes a one-worker case different from a
plain sequential loop. Socket access and mutexes are C/POSIX, not Liza rules.

```sh
python3 benchmarks/rtp-fanout/run.py --output /tmp/rtp-fanout.json --packets 50 --pps 100
```

The output must not exist. Requires POSIX, Python 3 and Clang. The driver uses
loopback and a Python receiver collector on the same host. It measures missing,
duplicated, corrupted and reordered packets, local send successes/errors and
same-clock latency. It fails on corrupted, duplicated or reordered data but
reports missing packets; it cannot attribute where a missing packet was lost.
It does not measure CPU, syscalls or actual copies; it performs only one short
run per case in fixed order. Its p99 is diagnostic and not a reliable service
latency measurement. Publisher count means different synthetic sources sharing
one input socket, not separate physical hosts or independent network interfaces.

The intended benchmark still needs: a plain single-thread reference, Linux
`sendmmsg`, packet pools with multiple in-flight buffers and explicit bounds,
real RTP and VideoGrace control updates, meaningful load and repeats, isolated
load generator and CPU/syscall measurements. Do not infer performance or pick a
production architecture from this prototype.
