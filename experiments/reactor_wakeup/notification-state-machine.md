# Notification state machine: design obligations

This is a proposed model for a future protocol, not a description or proof of
the probe. The FIFO is authoritative; wake tokens do not count messages. A
shared synchronization mechanism must serialize queue inspection, arming, and
the logical notification state. Its exact implementation and memory ordering
are open design questions.

The abstract state consists of a bounded FIFO, endpoint closure, receiver
`Running` or `Armed`, and notification `Idle`, `SignalOwed`, `Signalled`, or
`Fault`. `SignalOwed` includes a producer that has committed a publication but
has not completed the signal operation. `Fault` is sticky and must be exposed
to a supervisor independently of the possibly broken wake source; merely
setting an unread flag does not wake a sleeping receiver.

| Transition | Required behavior |
| --- | --- |
| Publish while running | Commit a complete message; under the same synchronization establish an owed or already durable signal before releasing the lock. |
| Publish while armed | Commit and establish `SignalOwed`; successful notification changes it to `Signalled`, failure to `Fault`. An in-flight signal must not be mistaken for a durable one. |
| Inspect before sleep | Under synchronization inspect queue, closure, fault, and notification state. Sleep only when there is no work, closure, fault, or owed signal and arming is coordinated with subsequent publication. |
| Wake and reset | Reconcile draining the OS wake source and clearing `Signalled` with concurrent publication. Recheck the queue under synchronization before sleeping again; a newer signal must not be erased. |
| Close | Serialize close with publication; arrange a wake or enter observable `Fault`. Drain or discard according to the separate channel contract. |
| Signal failure after publication | Keep the published message accounted for; enter `Fault` and report a post-publication failure through an independent supervision path. Do not report ordinary unsent failure or silently report success. |

The desired property is conditional: once publication is committed, either
the consumer can make progress through a durable wake or active execution, an
in-flight signal is still obligated to complete, or fault is independently
observable. This is not a real-time bound, and a stalled producer or failed
supervisor requires an explicit policy. A single atomic `pending` flag alone
does not establish this property.

## Interleavings to challenge

1. Publication before sleep: queue inspection sees work, or a durable wake
   remains visible when polling starts.
2. Publication after the empty check but before polling: synchronized arming
   ensures the producer owes a wake; it cannot be lost in that gap.
3. Signal failure after publication: retain the message and expose `Fault`;
   a worker asleep on the broken source cannot be the sole fault observer.
4. Close while asleep or while a send is in flight: serialize outcomes, wake
   or report fault, and retain the FIFO close/discard accounting.
5. Producer signals while consumer drains and clears: clearing an older token
   must not erase the only evidence of newer work; recheck under synchronization.

Each needs executable interleaving tests and negative mutations against a
concrete implementation. The present probe tests neither this state machine
nor all these schedules and supplies no proof of liveness or fault delivery.
