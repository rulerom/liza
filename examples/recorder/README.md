# Native Recorder with confirmed Storage publication

This slice runs the existing native VideoGrace Recorder as a child process from
Liza. Existing Python workers are unchanged. One Reactor services CAN, the
Recorder lifecycle, and a separate authenticated HTTPS Storage connection.

Configuration requires an absolute `output_dir` (at most 96 UTF-8 bytes).
`local_only` defaults to false: media must be uploaded and acknowledged before
completion. An explicit `local_only: true` enables lifecycle diagnostics and
rejects jobs requiring Storage before spawning. Local completion explicitly
reports `published: false`.

The executable path and server authority come from local configuration, not job
payload. The assignment's media credential is passed through a child-only
`VG_ACCESS_TOKEN` override, never through argv. Output is kept under
`output_dir/job_id/assignment_id`; existing output files are not overwritten.

One Reactor services CAN and heartbeat while the child is observed with
`try_wait`. Stop/cancel/disconnect requests create the native stop marker, then
escalate through terminate and kill if necessary. Ownership is retained until a
wait receipt permits closing the child. Reconnection follows child cleanup;
results from the old connection are not replayed. Local media files are retained.

Local WSS tests use an independent native lifecycle fixture. Its 32-byte output
is deliberately not a playable MP4 and is not evidence of real media recording.

Live attempt on `demo.videograce.ru`, conference `radio`: UI job
`1a1e1318664eb8` reached `liza-recorder-acceptance` and was rejected with
`storage_required` before spawning. That attempt produced no media file.

After rebuilding the native Recorder (the previous binary was rejected with
`UpdateRequired`), live job `1a1e137f424ebd`, assignment `1a1e137f424ebe`,
completed with exit 0 and a retained 2,115,440-byte local MP4. Independent
`ffprobe` inspection found H.264 1920x1080 video and AAC 48 kHz stereo audio,
container duration 9.024 seconds. The requested 10-second job limit includes
connection/startup time. The native log confirms stop-marker handling and normal
termination; the marker was removed after reaping. The CAN result explicitly
reported `local_only: true` and `published: false`. This verifies local media
capture, not Storage publication.
Full video/audio decoding with `ffmpeg -v error -i output.mp4 -f null -`
also completed successfully without reported errors.

Live Storage job `1a1e2f399fded4` completed with server-confirmed `artifact_ready`.
Its initial 2 KiB PUT implementation took 203 seconds for 3,446,043 bytes and was
replaced. The final implementation sends up to 64 KiB per PUT (respecting the
server limit), reuses TLS, and parses up to 256 response bytes per step. Live job
`1a1e2f94ec5ee6` published 4,350,563 bytes in 14.381 seconds measured between
the agent's `finalizing` and `completed` events. These are acceptance observations,
not a throughput benchmark or a comparison against Python.

Publication order is `finalizing` -> matching positive ACK -> Storage create /
PUT chunks / complete -> `artifact_ready` -> matching positive ACK -> `completed`.
The upload credential is separate from the native child's media credential.
Every accepted offset must equal the exact amount sent. HTTP errors, redirects,
Transfer-Encoding, ambiguous/missing length and replies over 4 KiB are rejected.
No shell, curl backend, worker threads or insecure TLS fallback is used.

ACK timeout is `ack_ms` (default 15000, range 100..60000). HTTPS requests have a
15-second deadline; upload has a 10-minute deadline. Files are retained on both
failure and success. A lost ACK does not become successful publication. This
slice uploads one MP4/M4A; Python's report/manifest/JSONL uploads, local SHA-256,
automatic deletion, resumable uploads and durable restart recovery are not
implemented. No crash-time process-tree cleanup is claimed.

See [Recorder documentation](../../docs/recorder-agent.md) for build and launch.
