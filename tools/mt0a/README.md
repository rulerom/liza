# MT0-A socket distribution probe

Exploratory Python/OS probe, **not** Liza threads, the Liza reactor, a gateway
implementation, or a formal ownership proof. It checks one shared listener
with bounded per-worker `queue.Queue` ownership transfer, and independent
listeners using `SO_REUSEPORT` on supported POSIX hosts. A queued socket has
one responsibility: the dispatcher closes it on Full, the queue owns it after
publication, the worker closes it after dequeue; shutdown closes queued sockets.

```sh
python3 -m unittest discover -s tools/mt0a -p test_probe.py -v
python3 tools/mt0a/probe.py --workers 4 --connections 64 --output /tmp/mt0a.json
```

Use a fresh output file. Windows: replace `/tmp/mt0a.json` with a fresh path.
The report includes OS, Python version, counts, dropped connections and explicit
unsupported status. `SO_REUSEADDR` on Windows is deliberately not treated as
`SO_REUSEPORT`. A failure after workers start is an error, not unsupported.

Connections are sequential and loopback-only; this is a functional probe rather
than a balancing or performance benchmark. CPython threads are native threads,
but the GIL and Python's socket wrappers do not model Liza runtime scheduling or
ownership. The tests cover full queue and cancellation cleanup; platform-specific
fault injection, process signal handling, worker-creation failure, load and
transfer into the actual Liza reactor remain open. No MT0-A completion claim.

On macOS 26.4.1 ARM64, Python 3.9.6, 4 workers / 64 sequential clients: shared
listener 16/16/16/16, SO_REUSEPORT 0/0/0/64. On Windows 10 x86-64 with Python
3.13.5: shared listener 16/16/16/16, reuseport marked unsupported by policy.
These observations apply to that probe only; neither proves OS fairness or
behavior of a future Gateway. Linux still requires an independent run.
