# Reactor wakeup — platform probe

This is a bounded C experiment, **not an integration into the Liza reactor** or
an API. The consumer owns a loop around `poll` / `WSAPoll`. A separate producer
publishes ordered `u32` commands into the existing bounded SPSC C core and then
signals a pollable wake source. A second loopback UDP socket supplies an
independent network-readiness event. The worker drains the queue in FIFO order
and observes both network and command readiness before exit; channel memory is
freed after join. The source queue is the authority, not the number of wake
bytes or eventfd counter values.

The test covers a command signaled before the worker starts and a command sent
after it has handled the preposted network event and announced a second poll.
The announcement occurs just before the system call: it does **not** prove the
worker is already asleep. Each case transfers 256 commands through eight slots,
checks every value and the network byte, and reports timeouts. Intentionally
suppressing notifications or failing the notification call must fail the test
rather than silently claim success. In the latter case a queue item may already
be published: the probe exits with an error and does not claim send atomicity.

## Mechanisms investigated

| Platform | Probe | Other candidate / limitation |
| --- | --- | --- |
| Linux | Loopback TCP socket in `poll`, and nonblocking `eventfd` in `poll` | `eventfd` is a counter; its readable and overflow/EAGAIN behavior must be included in a production protocol ([Linux manual](https://man7.org/linux/man-pages/man2/eventfd.2.html)). |
| macOS | Loopback TCP socket in `poll` | `kqueue` is a different event API; filters and event aggregation need a separate probe, not assumed equivalent to the existing poll reactor ([Apple manual](https://developer.apple.com/library/archive/documentation/System/Conceptual/ManPages_iPhoneOS/man2/kqueue.2.html)). |
| Windows | Loopback TCP socket in `WSAPoll` | `WSAPoll` monitors sockets, not a general list of event handles ([Microsoft](https://learn.microsoft.com/en-us/windows/win32/api/winsock2/nf-winsock2-wsapoll)); `WSAEventSelect`/`WSAWaitForMultipleEvents` would be a different design with its own limits ([Microsoft](https://learn.microsoft.com/en-us/windows/win32/api/winsock2/nf-winsock2-wsawaitformultipleevents)). |

The socket source uses an explicitly created local TCP pair, not a network
service protocol. The OS owns socket buffers and related memory outside the
bounded user queue. Notification send is nonblocking; any error, including
`WouldBlock`, is a reported probe failure, not an assumption that a wake was
safely coalesced. Producer retries a full queue with `yield`; the probe targets
consumer wakeup and does not solve bounded producer waiting. Wake draining is
capped per poll pass to avoid an unbounded drain loop.

```sh
python3 -m unittest discover -s experiments/reactor_wakeup -v
```

Tests use a finite 5-second poll and test-process timeout to expose missing
notifications. That timeout is a test guard, not a hard deadline guarantee.
There is no independent interleaving proof, byte/descriptor fault-injection
matrix, shutdown race model, latency/CPU benchmark, real network load,
production security boundary or claim about kqueue. TCP notification and
`eventfd` are not declared winners. In particular, a successful wake test does
not establish how to handle a failed signal after message publication, safe
coalescing, or the lifetime of endpoints across shutdown. Those must be solved
before integration with the reactor or Liza's public channel API.
