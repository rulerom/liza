# SG0 C prototype

Experimental execution of the [SG0 contract](../../docs/sg0-lifecycle-contract.md),
not a Liza API or production reactor change. Each test launches a fresh child
process with one worker, one supervisor and an owner; the admission-race case
adds one producer. Existing bounded FIFO and TCP wake helpers are reused.

## Status and observation

Single-writer status records use seq_cst atomic fields and an even/odd version.
A reader makes at most eight attempts and returns unavailable on an unstable
record. The supervisor marks prolonged unavailability separately from an
expired Busy obligation. All status fields are atomic, including those read
in intentionally broken snapshot tests. Version, epoch and obligation limits
are checked before wrap; the group records a fault on write failure. Version
atomics must be lock-free on the test platform (checked at startup).

Idle carries no work deadline. Pending delivery has a separate atomic deadline
until the single offered command is received, so stale Idle cannot hide it.
Worker progress increments on consumed commands. Supervisor epochs count
completed scans; each scan is a new supervisor obligation. Worker epochs do not
extend its deadline. The fault code is sticky and independent of protocol mutex.
Supervisor reads it and reports observation to owner. Neither observer acquires
that mutex. Absence of observation is not a diagnosis of deadlock.

## Admission and shutdown

The shutdown flag is set by owner without taking the protocol lock. A sender
checks it while holding that lock; that load is the admission point. A command
admitted before shutdown may commit afterward. Worker closes the FIFO under
the same lock, then drains accepted values. The test holds producer between
admission and commit while owner requests shutdown, proving this chosen order.
Only one command is in flight in this prototype; the delivery tracker is not
a general multi-command accounting mechanism.

Shutdown has one absolute deadline, never extended by repeated requests. A
separate control socket wakes a worker whose data notification failed. Worker
poll has a 100 ms timeout as a fallback for checking shutdown; supervisor scans
every 2 ms, owner every 1 ms. These are configured polling intervals, not
hard real-time bounds or a production idle-CPU benchmark. Gates are test-only.

## Join service and lifetime

Windows supports waiting on thread handles, but portable POSIX timed join is
not available across these targets. This prototype uses one detached native
**join-service thread** with static process-lifetime storage. It receives only
copies of participant handles, never a group/FIFO/socket/status pointer. It
performs real blocking system joins and publishes completion receipts. Owner
never waits in those joins and can escalate if a join fails to complete.

The join service is not the supervisor and does not access group resources.
Its receipt slots and journal are intentionally retained until process exit;
they cannot be reused for another group in this prototype. Its OS thread is
detached, not claimed joined. Group destruction requires actual join receipts
for every created **group resource user**, including producer and supervisor.
The service logs a join before publishing its receipt. The fixed journal lives
outside the group; its atomic slots are printed only after joins, or at the
controlled process-abort point. Overflow is fatal to the test.

This is a deliberate extra process-lifetime resource, not a free timed-join
primitive: sizeof(group), fixed 128 event slots, join-service metadata, two
socket pairs, FIFO allocation and native thread stacks must be budgeted.
Kernel socket buffers and OS thread overhead are outside the FIFO budget.
Integrating a reusable join service and its lifetime into production is separate
work. A functioning owner, clocks, native atomics and process termination are
assumptions; there is no third observer for owner failure.

## Scenarios and limits

`normal`, `idle`, `fault`, `mutex_stall`, `supervisor_stall`, `startup_fail`,
`startup_fail_first`, `stale_idle`, `admission_race`, `snapshot_stall`, `snapshot`
and `abort` run in isolated child processes. Startup failure is deterministic
injection at a thread-creation boundary. Callback execution remains gated until
all required threads exist. Notification failure is injected after publication;
the original command is still received and later sends are rejected.

For stalled worker/supervisor cases the owner reports Unresponsive and checks
that release is forbidden and free_count remains zero. After a test-controlled
release, actual joins precede Stopped and destruction. `abort` keeps worker
alive, exits the process with code 86, and produces neither Stopped nor destroy.
This uses `_Exit`, deliberately bypassing normal cleanup. Child process timeout
is an additional test harness safeguard, not the mechanism of expected failure.

Three negative controls fail with explicit assertions: accepting a mixed
snapshot (false deadline classification), permitting release at Unresponsive,
and declaring Stopped before joins. They stop before actually freeing live
memory. The journal and free counter are trusted instrumentation, not an
independent proof of every allocator operation. No exhaustive C memory-model
proof, arbitrary callback cancellation, reusable runtime group API, true reactor
integration, or performance claim is made.

```sh
python3 -m unittest discover -s experiments/sg0 -v
```
