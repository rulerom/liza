# RTP receiver registry

`receivers.liza` is a bounded, worker-local registry for a single translation.
It is application-level Liza code, not a UDP socket, concurrent shared table,
or an implementation of the VideoGrace wire protocol.

The table has 64 slots and stores a receiver SSRC, an IPv4 address as a `u32`,
a `u16` port and whether the endpoint has been learned. `add` reserves a slot
without an endpoint; `learn` updates an existing receiver; `remove` clears the
slot; `destination(table, slot)` returns a copy of the learned endpoint or
`None` for an unoccupied, unlearned or out-of-range slot. An IP value is stored
without interpretation or validation; port zero is rejected.

Mutating functions operate in place through `borrow mut`. Return codes are
`0` success, `1` full, `2` duplicate SSRC, `3` missing SSRC, `4` invalid port.
`add` checks all entries for duplicates before reusing the first empty slot;
failed operations leave the table unchanged. `learn` rejects a zero port before
looking up the SSRC. Removal and reuse do not inherit the old address. The
registry deliberately does not expose stable IDs: a slot index is only valid for
an immediate read and can later identify another receiver.

Each add/learn/remove visits at most 64 slots. `destination` performs a checked
index read; iterating all 64 slots is bounded. No operation requests allocation
or performs I/O; ordinary value copies, including explicit snapshots, have their
normal Liza semantics and may cost proportional to table size. No claim is made
about hardware copies, thread safety or authorization of SSRC/address updates.
A caller must establish who can issue updates. Future UDP integration must define
datagram lifetime, error handling, and actual destination encoding separately.

Run the example and focused regression at O0/O2:

```sh
python3 -m liza run examples/apps/rtp_receivers.liza
python3 -m unittest discover -s tests -p test_rtp_receivers.py -v
```
