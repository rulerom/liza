#ifndef LIZA_TLS_H
#define LIZA_TLS_H
/* Internal, thread-affine OpenSSL adapter behind the TLS-B linear binding.
 * The caller owns all sockets, polling and time. No borrowed pointer is retained.
 * Peer identity is mandatory; trust is system policy or an explicit CA file.
 * No verification bypass exists. */
#include <stddef.h>
#include <stdint.h>
typedef struct liza_tls liza_tls;
enum { LIZA_TLS_OK=0, LIZA_TLS_WANT=1, LIZA_TLS_CLOSED=2,
       LIZA_TLS_INVALID=3, LIZA_TLS_FAILED=4, LIZA_TLS_TIMEOUT=5,
       LIZA_TLS_WRONG_THREAD=6, LIZA_TLS_NOMEM=7 };
enum { LIZA_TLS_INPUT=1, LIZA_TLS_OUTPUT=2 };
enum { LIZA_TLS_HANDSHAKE=0, LIZA_TLS_OPEN=1, LIZA_TLS_CLOSING=2,
       LIZA_TLS_DONE=3, LIZA_TLS_DEAD=4, LIZA_TLS_UNAVAILABLE=5 };
#define LIZA_TLS_PLAIN_CAP 4096u
#define LIZA_TLS_WIRE_CAP 32768u
/* count is successful plaintext/ciphertext progress only. wants describes
 * encrypted I/O, not a direct poll mask: drain output before waiting for input.
 * ssl_error / verify_error are diagnostics, not user-controlled messages. */
typedef struct {
    uint32_t status, wants, count, state;
    unsigned long ssl_error;
    long verify_error;
} liza_tls_result;
uint32_t liza_tls_create(const char *ca_file,const char *peer,uint64_t now,
                         uint64_t deadline,liza_tls **out);
uint32_t liza_tls_create_system(const char *peer,uint64_t now,uint64_t deadline,liza_tls **out);
liza_tls_result liza_tls_handshake(liza_tls *,uint64_t now);
liza_tls_result liza_tls_write(liza_tls *,const uint8_t *,uint32_t,uint64_t now);
liza_tls_result liza_tls_read(liza_tls *,uint8_t *,uint32_t,uint64_t now);
liza_tls_result liza_tls_shutdown(liza_tls *,uint64_t now);
liza_tls_result liza_tls_feed(liza_tls *,const uint8_t *,uint32_t,uint64_t now);
liza_tls_result liza_tls_drain(liza_tls *,uint8_t *,uint32_t,uint64_t now);
liza_tls_result liza_tls_eof(liza_tls *,uint64_t now);
/* Owner-only destruction is abortive unless shutdown AND ciphertext drain have
 * completed. It never closes the caller's socket. NULL is harmless; using any
 * pointer after successful destroy is forbidden by the internal caller contract. */
uint32_t liza_tls_destroy(liza_tls *);
/* Adapter + fixed BIO ring capacities, excluding OpenSSL internal allocations,
 * certificates, provider state, allocator overhead, OS buffers and stacks. */
size_t liza_tls_managed_bytes(void);
#endif
