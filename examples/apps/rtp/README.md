# UDP RTP fanout — first executable slice

`rtp_fanout.liza` receives IPv4 UDP packets on a loopback socket, validates RTP
v2 fixed/CSRC/extension/padding fields and forwards packets whose SSRC matches
one configured author to 1–64 loopback receiver ports. It reads packet headers
through a local readonly view and passes that same view to every UDP send.
There is one reusable 2048-byte regional input buffer and no explicit payload
copy in the Liza application. Kernel copies and generated machine-code costs
have not been measured.

```sh
python3 -m liza build examples/apps/rtp_fanout.liza -O 2 -o /tmp/liza-rtp-fanout
/tmp/liza-rtp-fanout PACKET_COUNT EXPECTED_SSRC RECEIVER_PORT [RECEIVER_PORT ...]
```

The first stdout line is the assigned loopback port. `PACKET_COUNT` must be
1..2147483647; `EXPECTED_SSRC` is a decimal u32; each destination port is
1..65535. The process handles up to that many received datagrams: invalid RTP,
wrong SSRC and datagrams larger than 2048 bytes are consumed and ignored.
The exact 8-byte loopback datagram `LZSTOP01` also requests normal stop; it is
a benchmark-only, unauthenticated control message and must not be exposed as a
service protocol. A receive error other than truncation ends processing with exit 3. A send error
allows the remaining destinations of that packet to be attempted, then exits 3.
Invalid CLI configuration exits 2 before opening a socket. Normal completion
returns 0. No delivery guarantee is implied by a successful send.

Receiver entries are registered once at startup, are worker-local and use the
bounded table in `receivers.liza`. Only loopback IPv4 and fixed destinations
are supported. There is no authentication, control API, RTCP forwarding,
nonblocking reactor, signal-driven shutdown or multi-worker scheduling. This is
not VideoGrace wire compatibility or a production media server. Future control
updates, NAT rebinding, fanout failure policy and concurrency need separate
contracts.

The real socket regression runs O0 and O2:

```sh
python3 -m unittest discover -s tests -p test_rtp_fanout.py -v
```

## Counters and stop

At exit the application writes `received`, `accepted_valid`, `invalid`,
`wrong_ssrc`, `truncated`, `send_attempted`, `send_succeeded`, `send_failed`,
and `stop_reason` as `key=value` lines on stderr. `received` excludes the stop
marker but includes truncated datagrams; reason 0 is count limit, 1 is the
marker, and 2 is an I/O error. A successful send reports local OS acceptance,
not remote delivery. Counters describe this single worker and are not concurrent.
The stop marker is only a local test mechanism; UDP delivery and packet ordering
are not guaranteed. The external harness supplies drain time and bounds retries;
a marker lost or stuck behind traffic may require forced termination.

---

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
