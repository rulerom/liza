/* TLS-A conformance caller. Only this test loop knows about Reactor/socket I/O. */
#ifndef _WIN32
#define _POSIX_C_SOURCE 200809L
#endif
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <openssl/ssl.h>
#include <openssl/err.h>
#include "../../liza/runtime/tls.h"
#include "../../liza/runtime/reactor_common.h"
#define CHECK(x) do{if(!(x)){fprintf(stderr,"check %s line %d\n",#x,__LINE__);exit(90);}}while(0)
static uint64_t now_ms(void){uint64_t n=0;CHECK(!liza_rt_reactor_clock(&n));return n;}
static int wants(SSL *ssl,int ret){int e=SSL_get_error(ssl,ret);return e==SSL_ERROR_WANT_READ||e==SSL_ERROR_WANT_WRITE;}
static void pump(liza_tls *t,BIO *wire,unsigned limit){
    uint8_t data[LIZA_TLS_WIRE_CAP];
    liza_tls_result a=liza_tls_drain(t,data,limit,1);
    CHECK(a.status==LIZA_TLS_OK||a.status==LIZA_TLS_WANT);
    if(a.count)CHECK(BIO_write(wire,data,(int)a.count)==(int)a.count);
    int n=BIO_read(wire,data,(int)limit);
    if(n>0){liza_tls_result b=liza_tls_feed(t,data,(uint32_t)n,1);CHECK(b.status==LIZA_TLS_OK&&b.count==(uint32_t)n);}
    else CHECK(BIO_should_retry(wire));
}
static void memory_test(const char *ca,const char *cert,const char *key,int version){
    SSL_CTX *ctx=SSL_CTX_new(TLS_server_method());CHECK(ctx);
    CHECK(SSL_CTX_set_min_proto_version(ctx,version));CHECK(SSL_CTX_set_max_proto_version(ctx,version));
    CHECK(SSL_CTX_use_certificate_file(ctx,cert,SSL_FILETYPE_PEM)==1);
    CHECK(SSL_CTX_use_PrivateKey_file(ctx,key,SSL_FILETYPE_PEM)==1);
    SSL *server=SSL_new(ctx);CHECK(server);SSL_set_accept_state(server);
    BIO *internal=NULL,*wire=NULL;CHECK(BIO_new_bio_pair(&internal,65536,&wire,65536));SSL_set_bio(server,internal,internal);
    char peer_name[]="localhost";char *ca_copy=malloc(strlen(ca)+1);CHECK(ca_copy);strcpy(ca_copy,ca);
    liza_tls *t=NULL;CHECK(liza_tls_create(ca_copy,peer_name,1,1000000,&t)==LIZA_TLS_OK);
    memset(peer_name,'x',sizeof(peer_name)-1);memset(ca_copy,'x',strlen(ca_copy));free(ca_copy);
    int client_done=0,server_done=0;
    for(unsigned i=0;i<100000&&(!client_done||!server_done);i++){
        if(!client_done){liza_tls_result r=liza_tls_handshake(t,1);CHECK(r.status==LIZA_TLS_OK||r.status==LIZA_TLS_WANT);client_done=r.status==LIZA_TLS_OK;}
        if(!server_done){ERR_clear_error();int ret=SSL_do_handshake(server);CHECK(ret==1||wants(server,ret));server_done=ret==1;}
        pump(t,wire,7);
    }
    CHECK(client_done&&server_done);CHECK(SSL_version(server)==version);
    CHECK(!strcmp(SSL_get_servername(server,TLSEXT_NAMETYPE_host_name),"localhost"));
    uint8_t plain[4096],received[4096];memset(plain,42,sizeof plain);
    unsigned accepted=0,got=0,blocked=0;
    /* Saturate the fixed ciphertext ring before draining it. */
    for(unsigned i=0;i<32;i++){
        liza_tls_result r=liza_tls_write(t,plain,sizeof plain,1);
        if(r.status==LIZA_TLS_WANT){CHECK(!r.count&&(r.wants&LIZA_TLS_OUTPUT));blocked++;break;}
        CHECK(r.status==LIZA_TLS_OK&&r.count==sizeof plain);accepted++;
    }
    CHECK(blocked&&accepted<32);
    plain[0]=43;CHECK(liza_tls_write(t,plain,sizeof plain,1).status==LIZA_TLS_INVALID);plain[0]=42;
    uint8_t moved_plain[4096];memcpy(moved_plain,plain,sizeof plain);
    CHECK(liza_tls_write(t,moved_plain,sizeof moved_plain,1).status==LIZA_TLS_WANT);
    unsigned target=accepted+3;
    for(unsigned i=0;i<100000&&got<target*sizeof plain;i++){
        if(accepted<target){liza_tls_result r=liza_tls_write(t,plain,sizeof plain,1);CHECK(r.status==LIZA_TLS_OK||r.status==LIZA_TLS_WANT);if(r.status==LIZA_TLS_OK){CHECK(r.count==sizeof plain);accepted++;}}
        pump(t,wire,97);
        size_t n=0;ERR_clear_error();int ret=SSL_read_ex(server,received,sizeof received,&n);
        if(ret==1){for(size_t j=0;j<n;j++)CHECK(received[j]==42);got+=(unsigned)n;}
        else CHECK(wants(server,ret));
    }
    CHECK(got==target*sizeof plain);
    if(version==TLS1_3_VERSION)CHECK(SSL_key_update(server,SSL_KEY_UPDATE_REQUESTED)==1);
    size_t sent=0;ERR_clear_error();CHECK(SSL_write_ex(server,"pong",4,&sent)==1&&sent==4);
    unsigned read=0;
    for(unsigned i=0;i<10000&&read<4;i++){
        pump(t,wire,3);liza_tls_result r=liza_tls_read(t,received,1,1);
        CHECK(r.status==LIZA_TLS_OK||r.status==LIZA_TLS_WANT);
        if(r.count){CHECK(r.count==1&&received[0]==(uint8_t)"pong"[read]);read++;}
    }
    CHECK(read==4);
    ERR_clear_error();int initiated=SSL_shutdown(server);CHECK(initiated==0||wants(server,initiated));
    int peer_closed=0;
    for(unsigned i=0;i<10000&&!peer_closed;i++){
        pump(t,wire,3);liza_tls_result r=liza_tls_read(t,received,sizeof received,1);
        CHECK(r.status==LIZA_TLS_WANT||r.status==LIZA_TLS_CLOSED);
        if(r.status==LIZA_TLS_CLOSED){CHECK(r.state==LIZA_TLS_CLOSING);peer_closed=1;}
    }
    CHECK(peer_closed&&liza_tls_write(t,plain,1,1).status==LIZA_TLS_INVALID);
    int closed=0,server_closed=0;
    for(unsigned i=0;i<10000&&(!closed||!server_closed);i++){
        if(!closed){liza_tls_result r=liza_tls_shutdown(t,1);CHECK(r.status==LIZA_TLS_OK||r.status==LIZA_TLS_WANT);closed=r.status==LIZA_TLS_OK;}
        pump(t,wire,5);
        if(!server_closed){ERR_clear_error();int ret=SSL_shutdown(server);CHECK(ret>=0||wants(server,ret));server_closed=ret==1;}
    }
    CHECK(closed&&server_closed);
    for(unsigned i=0;i<100;i++)pump(t,wire,5);
    CHECK(liza_tls_write(t,plain,1,1).status==LIZA_TLS_INVALID);
    CHECK(liza_tls_read(t,received,1,1).status==LIZA_TLS_INVALID);
    CHECK(liza_tls_shutdown(t,1).status==LIZA_TLS_OK);
    CHECK(!liza_tls_destroy(t));BIO_free(wire);SSL_free(server);SSL_CTX_free(ctx);
    printf("memory tls=%d partial_write=1 retry_identity=1 close=1\n",version);
}
#ifdef _WIN32
static DWORD WINAPI foreign(void *p){CHECK(liza_tls_handshake(p,1).status==LIZA_TLS_WRONG_THREAD);CHECK(liza_tls_destroy(p)==LIZA_TLS_WRONG_THREAD);return 0;}
#else
static void *foreign(void *p){CHECK(liza_tls_handshake(p,1).status==LIZA_TLS_WRONG_THREAD);CHECK(liza_tls_destroy(p)==LIZA_TLS_WRONG_THREAD);return NULL;}
#endif
static void boundary(const char *ca){
    liza_tls *t=NULL;CHECK(liza_tls_managed_bytes()>2*LIZA_TLS_WIRE_CAP);
    printf("backend %s adapter_and_ring_capacity=%zu\n",OpenSSL_version(OPENSSL_VERSION),liza_tls_managed_bytes());
    CHECK(liza_tls_create(ca,"",1,10,&t)==LIZA_TLS_INVALID&&!t);
    CHECK(liza_tls_create(ca,"localhost",1,1,&t)==LIZA_TLS_INVALID&&!t);
    CHECK(liza_tls_create("liza-tls-no-such-ca.pem","localhost",1,10,&t)==LIZA_TLS_FAILED&&!t);
    CHECK(!liza_tls_create(ca,"localhost",1,10,&t));
#ifdef _WIN32
    HANDLE h=CreateThread(NULL,0,foreign,t,0,NULL);CHECK(h);CHECK(WaitForSingleObject(h,INFINITE)==WAIT_OBJECT_0);CloseHandle(h);
#else
    pthread_t h;CHECK(!pthread_create(&h,NULL,foreign,t));CHECK(!pthread_join(h,NULL));
#endif
    uint8_t b[32768];memset(b,0,sizeof b);
    CHECK(liza_tls_write(t,b,1,1).status==LIZA_TLS_INVALID);
    CHECK(liza_tls_read(t,b,1,1).status==LIZA_TLS_INVALID);
    CHECK(liza_tls_shutdown(t,1).status==LIZA_TLS_INVALID);
    liza_tls_result r=liza_tls_handshake(t,1);CHECK(r.status==LIZA_TLS_WANT&&(r.wants&LIZA_TLS_OUTPUT));
    CHECK(liza_tls_drain(t,b,1,1).count==1);
    r=liza_tls_feed(t,b,sizeof b,1);CHECK(r.status==LIZA_TLS_OK&&r.count==sizeof b);
    r=liza_tls_feed(t,b,1,1);CHECK(r.status==LIZA_TLS_WANT&&!r.count);
    CHECK(liza_tls_handshake(t,10).status==LIZA_TLS_TIMEOUT);
    CHECK(liza_tls_handshake(t,1).status==LIZA_TLS_TIMEOUT);CHECK(!liza_tls_destroy(t));
    CHECK(!liza_tls_create(ca,"localhost",2,10,&t));
    CHECK(liza_tls_handshake(t,1).status==LIZA_TLS_INVALID);CHECK(!liza_tls_destroy(t));
    CHECK(!liza_tls_destroy(NULL));puts("boundary thread_affinity=1 budget=1 backpressure=1 deadline=1");
}
static int network(const char *ca,const char *peer,uint16_t port,const char *mode){
    uint64_t start=now_ms(),deadline=start+(!strcmp(mode,"timeout")?150:5000);
    liza_tls *t=NULL;uint32_t made=liza_tls_create(ca,peer,start,deadline,&t);if(made)return (int)made;
    reactor *r=NULL;CHECK(!liza_rt_reactor_create(0,1,&r));CHECK(!liza_rt_reactor_stop_accepting(r));
    uint64_t id[3]={0};CHECK(!liza_rt_reactor_connect(r,port,id));
    uint8_t outgoing[1],incoming[7],plain[4096];unsigned pending=0,offset=0,connected=0,phase=0,got=0,polls=0,wire_in=0,wire_out=0;
    const uint8_t message[]="TLS-A reactor echo";int status=90;
    for(unsigned steps=0;steps<100000;steps++){
        uint64_t now=now_ms();liza_tls_result result={0};
        if(!connected){uint64_t q=liza_rt_reactor_finish_connect(r,id[0],id[1],id[2]);if(q>>32){if((q>>32)!=4){status=4;break;}}else connected=(unsigned)q;}
        if(connected){
            unsigned phase_before=phase;
            if(phase==0)result=liza_tls_handshake(t,now);
            else if(phase==1)result=liza_tls_write(t,message,sizeof(message)-1,now);
            else if(phase==2)result=liza_tls_read(t,plain,sizeof plain,now);
            else result=liza_tls_shutdown(t,now);
            if(result.status==LIZA_TLS_TIMEOUT||result.status==LIZA_TLS_FAILED){status=(int)result.status;printf("failure status=%u verify=%ld\n",result.status,result.verify_error);break;}
            CHECK(result.status==LIZA_TLS_OK||result.status==LIZA_TLS_WANT||result.status==LIZA_TLS_CLOSED);
            if(result.status==LIZA_TLS_OK){
                if(phase<2)phase++;
                else if(phase==2){CHECK(result.count&&got+result.count<=sizeof(message)-1);CHECK(!memcmp(plain,message+got,result.count));got+=result.count;if(got==sizeof(message)-1)phase=3;}
            }
            if(result.status==LIZA_TLS_CLOSED){status=4;break;}
            /* One-byte ciphertext writes exercise offsets independently of TLS. */
            if(!pending){liza_tls_result d=liza_tls_drain(t,outgoing,sizeof outgoing,now);CHECK(d.status==LIZA_TLS_OK||d.status==LIZA_TLS_WANT);pending=d.count;offset=0;}
            if(phase_before==3&&result.status==LIZA_TLS_OK&&!pending&&!(result.wants&LIZA_TLS_OUTPUT)){status=0;break;}
            /* A completed TLS step can enable the next application operation
             * without any new kernel readiness (handshake -> write -> read). */
            if(result.status==LIZA_TLS_OK&&(phase_before!=phase||result.count))continue;
        }
        if(now>=deadline){status=5;break;}
        unsigned interest=connected?LIZA_TLS_INPUT:2;if(pending)interest|=2;
        CHECK(!liza_rt_reactor_interest(r,id[0],id[1],id[2],interest));
        uint64_t events=liza_rt_reactor_poll(r,(uint32_t)(deadline-now));CHECK(!(events>>32));polls++;
        uint64_t ready=liza_rt_reactor_ready(r,id[0],id[1],id[2]);CHECK(!(ready>>32));
        if(pending&&(ready&6)){uint64_t n=liza_rt_reactor_write(r,id[0],id[1],id[2],outgoing,sizeof outgoing,offset,pending-offset);if(!(n>>32)){CHECK(n>0);wire_out+=(unsigned)n;offset+=(unsigned)n;if(offset==pending)pending=0;}else CHECK((n>>32)==4||(n>>32)==3);}
        if(connected&&(ready&5)){
            uint64_t n=liza_rt_reactor_read(r,id[0],id[1],id[2],incoming,sizeof incoming,0,sizeof incoming);
            if(!(n>>32)){
                wire_in+=(unsigned)n;
                liza_tls_result in=n?liza_tls_feed(t,incoming,(uint32_t)n,now_ms()):liza_tls_eof(t,now_ms());
                if(in.status==LIZA_TLS_TIMEOUT){status=5;break;}CHECK(in.status==LIZA_TLS_OK&&in.count==(uint32_t)n);
            }else CHECK((n>>32)==4||(n>>32)==3);
        }
    }
    CHECK(!liza_tls_destroy(t));CHECK(!liza_rt_reactor_close(r));
    printf("network status=%d received=%u polls=%u phase=%u in=%u out=%u\n",status,got,polls,phase,wire_in,wire_out);return status;
}
int main(int argc,char **argv){
    CHECK(argc>=3);
    if(!strcmp(argv[1],"boundary")){boundary(argv[2]);return 0;}
    if(!strcmp(argv[1],"memory")){CHECK(argc==6);memory_test(argv[2],argv[3],argv[4],atoi(argv[5]));return 0;}
    CHECK(argc==6);return network(argv[2],argv[3],(uint16_t)atoi(argv[4]),argv[5]);
}
