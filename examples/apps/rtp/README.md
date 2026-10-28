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
1..65535. The process handles exactly that many received datagrams: invalid RTP,
wrong SSRC and datagrams larger than 2048 bytes are consumed and ignored.
A receive error other than truncation ends processing with exit 3. A send error
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
