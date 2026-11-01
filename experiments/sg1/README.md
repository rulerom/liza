# SG1: reactor worker integration

Experimental C composition of the notification protocol and SG0 lifecycle with
real loopback UDP readiness. The worker creates, binds, services and closes its
own UDP socket. Its minimal reactor uses one `poll` / `WSAPoll` over UDP, data
notification and an independent shutdown control socket. This is not a call to
Liza's production Reactor implementation and makes no production API changes.

Run `python -m unittest discover -s experiments/sg1 -v` (Clang, native loopback
sockets required). CI covers Linux, macOS and Windows. Each scenario runs in an
isolated child with a 12-second external bound; the owner's 5-second guard is
process escalation, not a successful shutdown.

## Wait and ownership

Before each wait, `take_or_arm` drains old notification state, inspects FIFO and
arms under the protocol mutex. Network dispatch always returns to that check.
The wait has timeout **-1**: no periodic worker timeout checks shutdown. A
separate control pair wakes the worker even when data notification fails. An
expired lifecycle/delivery obligation is observed by the supervisor/owner;
it does not require waking a stuck worker through the failed data path.

The owner requests stop, then the worker closes admission under the protocol
mutex and drains accepted commands. The worker closes its own network socket
before returning. Shared FIFO, notification/control sockets and synchronization
remain alive until worker and supervisor join receipts are confirmed. The
fixed journal checks `network_close -> worker_exit -> worker_join` and
`supervisor_join -> stopped -> destroy`. Worker-local close by its owner is
not premature group destruction.

## Scenarios and negative controls

The twelve SG0 scenarios are retained against the new wait loop: normal command,
idle, notification fault, mutex stall, supervisor stall, first/second startup
failure, stale Idle delivery, publication/shutdown admission race, unavailable
snapshot, snapshot consistency, and process abort. Network-only and simultaneous
network/command scenarios bring the total to fourteen. In the simultaneous
case, a gate keeps the worker before poll until both sources have been posted;
this deliberately tests persistent readiness as well as the FIFO recheck.

Three separately compiled mutations must fail with a specific assertion:

| Mutation | Reproducible rejection |
| --- | --- |
| `SG1_DROP_SHUTDOWN` | Idle worker receives no control wake; shutdown deadline yields `Unresponsive` |
| `SG1_SKIP_RECHECK` | After network dispatch, drain notification and skip FIFO inspection; pending command exceeds delivery deadline |
| `SG_BROKEN_RELEASE` | Permit destruction while gated worker remains alive; release guard rejects before any unsafe free |

No mutation is accepted merely because the child timed out. Notification failure
is injected after FIFO publication; the value is drained through the independent
shutdown path and sticky fault rejects subsequent publications. This does not
cover all OS/socket failures or prove every concurrent schedule.

## Idle measurements

The idle test observes at least 750 ms after the first wait call was entered:
exactly one call, **zero returns before shutdown**, then one return after control
wake. The test reports monotonic wall time, worker-thread CPU time and process
CPU time (GetThreadTimes/GetProcessTimes on Windows; thread/process clocks on
POSIX). Worker measurements cover its loop through shutdown, excluding socket
setup and destruction. Process measurement covers the owner observation period.

CPU numbers are observations, not a noisy cross-platform pass/fail threshold.
The structural idle criterion is the absence of returns/repeated waits; low CPU
alone would not establish that. POSIX EINTR retries are supported but not injected
by the idle scenario. The journal and counters instrument the selected execution;
there is no claim that a counter immediately before poll proves the thread is
already blocked inside the kernel.

Supervisor still scans every 2 ms and owner observes every 1 ms, as in SG0.
Process CPU includes this monitoring overhead; it must not be described as
zero-wakeup process idle. Controlled test gates also use short sleeps.

## Retained bounds

One offered command is in flight; the FIFO has two u32 slots and a 1024-byte
allocation budget. This is not general per-message deadline accounting. Network
traffic is one real UDP datagram; no throughput or p99 claim is made. The network
socket is nonblocking and the selected dispatch reads one datagram.

Lifecycle code is an intentionally frozen copy of SG0 with its integration
changes; `status.h`, notification protocol and platform helpers are shared.
SG0 itself is unchanged. Its detached join-service is unchanged: static
process-lifetime metadata, copied native handles, no group pointer, real joins
and receipts, one group per child. It is not a reusable production join service.
The 128-event journal, group/status records, two TCP pairs, UDP socket, native
stacks and OS buffers are outside the FIFO budget. Thread or group reuse,
control-path recovery, scheduling guarantees, production reactor adapters,
Semantic IR and public Liza API remain separate work.
