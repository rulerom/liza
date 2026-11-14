#include "tls.h"
#include <stdlib.h>
#include <string.h>
#include <openssl/ssl.h>
#include <openssl/err.h>
#include <openssl/x509v3.h>
#if OPENSSL_VERSION_NUMBER < 0x30000000L
#error TLS-A requires OpenSSL 3
#endif
#ifdef _WIN32
#define WIN32_LEAN_AND_MEAN
#include <windows.h>
typedef DWORD tls_thread;
#define TLS_SELF() GetCurrentThreadId()
#define TLS_SAME(a,b) ((a)==(b))
#else
#include <pthread.h>
typedef pthread_t tls_thread;
#define TLS_SELF() pthread_self()
#define TLS_SAME(a,b) pthread_equal(a,b)
#endif
struct liza_tls {
    SSL_CTX *ctx; SSL *ssl; BIO *wire;
    tls_thread owner;
    uint64_t deadline,last_now;
    uint32_t state,failed,eof,pending_write;
    uint8_t write_buffer[LIZA_TLS_PLAIN_CAP],read_buffer[LIZA_TLS_PLAIN_CAP];
};
size_t liza_tls_managed_bytes(void) {return sizeof(liza_tls)+2*LIZA_TLS_WIRE_CAP;}
static liza_tls_result result(liza_tls *t,uint32_t code,uint32_t wants,uint32_t count) {
    liza_tls_result r={code,wants,count,t?t->state:LIZA_TLS_UNAVAILABLE,0,0};
    if(t && t->wire && BIO_ctrl_pending(t->wire))r.wants|=LIZA_TLS_OUTPUT;
    return r;
}
static liza_tls_result denied(liza_tls *t,uint32_t code) {
    liza_tls_result r={code,0,0,LIZA_TLS_UNAVAILABLE,0,0};
    /* A foreign thread must not inspect mutable session state or BIOs. */
    if(t && code!=LIZA_TLS_WRONG_THREAD)r.state=t->state;
    return r;
}
static uint32_t guard(liza_tls *t,uint64_t now) {
    if(!t)return LIZA_TLS_INVALID;
    if(!TLS_SAME(t->owner,TLS_SELF()))return LIZA_TLS_WRONG_THREAD;
    if(t->state==LIZA_TLS_DEAD)return t->failed;
    if(now<t->last_now){t->state=LIZA_TLS_DEAD;return t->failed=LIZA_TLS_INVALID;}
    t->last_now=now;
    if(now>=t->deadline){t->state=LIZA_TLS_DEAD;return t->failed=LIZA_TLS_TIMEOUT;}
    return LIZA_TLS_OK;
}
static liza_tls_result error(liza_tls *t,int ret) {
    /* SSL_get_error must immediately follow the SSL operation on its owner. */
    int code=SSL_get_error(t->ssl,ret);
    if(code==SSL_ERROR_WANT_READ)return result(t,LIZA_TLS_WANT,LIZA_TLS_INPUT,0);
    if(code==SSL_ERROR_WANT_WRITE)return result(t,LIZA_TLS_WANT,LIZA_TLS_OUTPUT,0);
    if(code==SSL_ERROR_ZERO_RETURN){
        t->pending_write=0;OPENSSL_cleanse(t->write_buffer,sizeof(t->write_buffer));
        t->state=LIZA_TLS_CLOSING;return result(t,LIZA_TLS_CLOSED,0,0);
    }
    t->state=LIZA_TLS_DEAD;t->failed=LIZA_TLS_FAILED;
    liza_tls_result r=result(t,LIZA_TLS_FAILED,0,0);
    r.ssl_error=ERR_peek_last_error();r.verify_error=SSL_get_verify_result(t->ssl);
    return r;
}
uint32_t liza_tls_destroy(liza_tls *t) {
    if(!t)return LIZA_TLS_OK;
    if(!TLS_SAME(t->owner,TLS_SELF()))return LIZA_TLS_WRONG_THREAD;
    SSL_free(t->ssl);BIO_free(t->wire);SSL_CTX_free(t->ctx);
    OPENSSL_cleanse(t,sizeof(*t));free(t);return LIZA_TLS_OK;
}
uint32_t liza_tls_create(const char *ca,const char *peer,uint64_t now,uint64_t deadline,liza_tls **out) {
    if(!out)return LIZA_TLS_INVALID;
    *out=NULL;
    if(!ca || !*ca || !peer || !*peer || strlen(peer)>253 || now>=deadline)return LIZA_TLS_INVALID;
    /* ASCII DNS name or literal IP only. No embedded authority/URI components. */
    for(const unsigned char *p=(const unsigned char *)peer;*p;p++)
        if(!((*p>='a'&&*p<='z')||(*p>='A'&&*p<='Z')||(*p>='0'&&*p<='9')||*p=='.'||*p=='-'||*p==':'))return LIZA_TLS_INVALID;
    liza_tls *t=calloc(1,sizeof(*t));if(!t)return LIZA_TLS_NOMEM;
    t->owner=TLS_SELF();t->deadline=deadline;t->last_now=now;
    t->ctx=SSL_CTX_new(TLS_client_method());
    if(!t->ctx){liza_tls_destroy(t);return LIZA_TLS_NOMEM;}
    SSL_CTX_set_verify(t->ctx,SSL_VERIFY_PEER,NULL);
    SSL_CTX_set_verify_depth(t->ctx,8);
    SSL_CTX_set_session_cache_mode(t->ctx,SSL_SESS_CACHE_OFF);
    if(!SSL_CTX_set_min_proto_version(t->ctx,TLS1_2_VERSION) ||
       !SSL_CTX_set_max_proto_version(t->ctx,TLS1_3_VERSION) ||
       !SSL_CTX_load_verify_locations(t->ctx,ca,NULL)) {
        liza_tls_destroy(t);return LIZA_TLS_FAILED;
    }
    t->ssl=SSL_new(t->ctx);if(!t->ssl){liza_tls_destroy(t);return LIZA_TLS_NOMEM;}
    SSL_set_max_cert_list(t->ssl,65536);
    SSL_set_hostflags(t->ssl,X509_CHECK_FLAG_NO_PARTIAL_WILDCARDS|X509_CHECK_FLAG_NEVER_CHECK_SUBJECT);
    ASN1_OCTET_STRING *ip=a2i_IPADDRESS(peer);
    if(ip){
        int valid=X509_VERIFY_PARAM_set1_ip(SSL_get0_param(t->ssl),ASN1_STRING_get0_data(ip),(size_t)ASN1_STRING_length(ip));
        ASN1_OCTET_STRING_free(ip);
        if(!valid){liza_tls_destroy(t);return LIZA_TLS_INVALID;}
    }else if(!SSL_set1_host(t->ssl,peer)||!SSL_set_tlsext_host_name(t->ssl,peer)){
        liza_tls_destroy(t);return LIZA_TLS_FAILED;
    }
    BIO *internal=NULL;
    if(!BIO_new_bio_pair(&internal,LIZA_TLS_WIRE_CAP,&t->wire,LIZA_TLS_WIRE_CAP)) {
        BIO_free(internal);liza_tls_destroy(t);return LIZA_TLS_NOMEM;
    }
    SSL_set_bio(t->ssl,internal,internal);SSL_set_connect_state(t->ssl);
    *out=t;return LIZA_TLS_OK;
}
liza_tls_result liza_tls_handshake(liza_tls *t,uint64_t now) {
    uint32_t code=guard(t,now);if(code)return denied(t,code);
    if(t->state!=LIZA_TLS_HANDSHAKE)return result(t,LIZA_TLS_INVALID,0,0);
    ERR_clear_error();int ret=SSL_do_handshake(t->ssl);
    if(ret!=1)return error(t,ret);
    if(SSL_get_verify_result(t->ssl)!=X509_V_OK){t->state=LIZA_TLS_DEAD;t->failed=LIZA_TLS_FAILED;return result(t,LIZA_TLS_FAILED,0,0);}
    t->state=LIZA_TLS_OPEN;return result(t,LIZA_TLS_OK,0,0);
}
liza_tls_result liza_tls_write(liza_tls *t,const uint8_t *data,uint32_t n,uint64_t now) {
    uint32_t code=guard(t,now);if(code)return denied(t,code);
    if(t->state!=LIZA_TLS_OPEN)return result(t,LIZA_TLS_INVALID,0,0);
    if(n>LIZA_TLS_PLAIN_CAP || (n&&!data))return result(t,LIZA_TLS_INVALID,0,0);
    if(t->pending_write && (n!=t->pending_write || memcmp(t->write_buffer,data,n)))return result(t,LIZA_TLS_INVALID,0,0);
    if(!n)return result(t,LIZA_TLS_OK,0,0);
    if(!t->pending_write){memcpy(t->write_buffer,data,n);t->pending_write=n;}
    size_t written=0;ERR_clear_error();int ret=SSL_write_ex(t->ssl,t->write_buffer,n,&written);
    if(ret!=1)return error(t,ret);
    t->pending_write=0;OPENSSL_cleanse(t->write_buffer,sizeof(t->write_buffer));
    return result(t,LIZA_TLS_OK,0,(uint32_t)written);
}
liza_tls_result liza_tls_read(liza_tls *t,uint8_t *data,uint32_t n,uint64_t now) {
    uint32_t code=guard(t,now);if(code)return denied(t,code);
    if(t->state!=LIZA_TLS_OPEN || t->pending_write || !data || !n || n>LIZA_TLS_PLAIN_CAP)return result(t,LIZA_TLS_INVALID,0,0);
    size_t got=0;ERR_clear_error();int ret=SSL_read_ex(t->ssl,t->read_buffer,n,&got);
    if(ret!=1)return error(t,ret);
    memcpy(data,t->read_buffer,got);OPENSSL_cleanse(t->read_buffer,sizeof(t->read_buffer));
    return result(t,LIZA_TLS_OK,0,(uint32_t)got);
}
liza_tls_result liza_tls_shutdown(liza_tls *t,uint64_t now) {
    uint32_t code=guard(t,now);if(code)return denied(t,code);
    if(t->state==LIZA_TLS_DONE)return result(t,LIZA_TLS_OK,0,0);
    if((t->state!=LIZA_TLS_OPEN && t->state!=LIZA_TLS_CLOSING)||t->pending_write)return result(t,LIZA_TLS_INVALID,0,0);
    t->state=LIZA_TLS_CLOSING;ERR_clear_error();int ret=SSL_shutdown(t->ssl);
    if(ret==1){t->state=LIZA_TLS_DONE;return result(t,LIZA_TLS_OK,0,0);}
    if(ret==0)return result(t,LIZA_TLS_WANT,LIZA_TLS_INPUT,0);
    return error(t,ret);
}
liza_tls_result liza_tls_feed(liza_tls *t,const uint8_t *data,uint32_t n,uint64_t now) {
    uint32_t code=guard(t,now);if(code)return denied(t,code);
    if(t->eof || t->state==LIZA_TLS_DONE || !data || !n || n>LIZA_TLS_WIRE_CAP)return result(t,LIZA_TLS_INVALID,0,0);
    int ret=BIO_write(t->wire,data,(int)n);
    if(ret>0)return result(t,LIZA_TLS_OK,0,(uint32_t)ret);
    if(BIO_should_retry(t->wire))return result(t,LIZA_TLS_WANT,0,0);
    t->state=LIZA_TLS_DEAD;t->failed=LIZA_TLS_FAILED;return result(t,LIZA_TLS_FAILED,0,0);
}
liza_tls_result liza_tls_drain(liza_tls *t,uint8_t *data,uint32_t n,uint64_t now) {
    uint32_t code=guard(t,now);if(code)return denied(t,code);
    if(!data || !n || n>LIZA_TLS_WIRE_CAP)return result(t,LIZA_TLS_INVALID,0,0);
    int ret=BIO_read(t->wire,data,(int)n);
    if(ret>0)return result(t,LIZA_TLS_OK,0,(uint32_t)ret);
    if(BIO_should_retry(t->wire))return result(t,LIZA_TLS_WANT,0,0);
    return result(t,LIZA_TLS_CLOSED,0,0);
}
liza_tls_result liza_tls_eof(liza_tls *t,uint64_t now) {
    uint32_t code=guard(t,now);if(code)return denied(t,code);
    if(t->eof)return result(t,LIZA_TLS_INVALID,0,0);
    BIO_shutdown_wr(t->wire);t->eof=1;return result(t,LIZA_TLS_OK,0,0);
}
