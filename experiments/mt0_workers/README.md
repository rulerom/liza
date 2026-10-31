# MT0 native worker bridge — experiment

This experiment executes a compiled Liza function on 1–8 native OS threads.
It is a test harness, not an available Liza thread API or a Gateway worker
implementation. It does not transfer sockets, regions, borrows, references,
or mutable state across threads. Each call gets a scalar ID and returns a
scalar result; all Liza state is local to the call. It uses pthreads on POSIX
and Windows threads on Windows.

The launcher creates all workers behind a gate, then starts the Liza functions
only if every thread was created. On partial creation failure it releases the
gate in cancel mode and joins every started thread. The injected failure index
exercises each partial-start position; it does not simulate an OS join failure.
Successful calls also join before their result storage goes out of scope.
A trap or a worker that never returns is outside the cleanup guarantee.

The Python builder invokes the actual compiler to produce LLVM, renames its C
entry point, and adds a scalar wrapper around the generated worker symbol before
linking the launcher. This trusted, diagnostic-only LLVM adaptation is not a
language feature or a stable ABI. Nothing enforces isolation for arbitrary
functions invoked through the bridge: its use is confined to the included pure
worker. In particular, existing process-global runtime behavior, network
ownership, Windows behavior, inter-worker communication and scheduler fairness
are not established by this experiment.

```sh
python3 experiments/mt0_workers/build.py -O 2 -o /tmp/liza-mt0
/tmp/liza-mt0 4 -1
python3 -m unittest discover -s experiments/mt0_workers -v
```

A negative second argument disables fault injection; otherwise it is the worker
creation index at which to inject failure. Values are bounded to 1–8 workers.
The test builds O0 and O2 and checks every partial-start boundary as well as
invalid configuration. The next step is to define and implement a checked
Liza-facing worker entry and join contract, audit runtime global state, then
integrate worker-owned network resources and bounded communication. No claims
about media throughput or automatic trap cleanup follow from this probe.
