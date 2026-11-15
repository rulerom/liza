/* Scalar/pointer ABI only; never pass an LLVM aggregate through a C ABI. */
#include "tls.h"
#include <string.h>
uint32_t liza_rt_tls_create(const uint8_t *peer,uint32_t plen,const uint8_t *ca,uint32_t clen,
    uint32_t custom,uint64_t budget,uint64_t now,uint64_t deadline,liza_tls **out) {
    *out=NULL;
    if(!peer||!plen||plen>253||clen>4096||custom>1||(!custom&&clen)||(custom&&!clen)||
        memchr(peer,0,plen)||(clen&&(!ca||memchr(ca,0,clen))))return LIZA_TLS_INVALID;
    if(now>=deadline)return LIZA_TLS_TIMEOUT;
    if(budget<liza_tls_managed_bytes())return 8;
    char host[254],path[4097];memcpy(host,peer,plen);host[plen]=0;
    if(custom){memcpy(path,ca,clen);path[clen]=0;return liza_tls_create(path,host,now,deadline,out);}
    return liza_tls_create_system(host,now,deadline,out);
}
void liza_rt_tls_step(uint32_t op,liza_tls *t,uint8_t *data,uint32_t length,uint32_t start,uint32_t count,uint64_t now,uint64_t out[6]) {
    liza_tls_result r={LIZA_TLS_INVALID,0,0,LIZA_TLS_UNAVAILABLE,0,0};
    if(start<=length&&count<=length-start){
        uint8_t *p=data?data+start:NULL;
        switch(op){
        case 0:r=liza_tls_handshake(t,now);break;
        case 1:r=liza_tls_write(t,p,count,now);break;
        case 2:r=liza_tls_read(t,p,count,now);break;
        case 3:r=liza_tls_shutdown(t,now);break;
        case 4:r=liza_tls_feed(t,p,count,now);break;
        case 5:r=liza_tls_drain(t,p,count,now);break;
        case 6:r=liza_tls_eof(t,now);break;
        }
    }
    out[0]=r.status;out[1]=r.wants;out[2]=r.count;out[3]=r.state;
    out[4]=(uint64_t)r.verify_error;out[5]=(uint64_t)r.ssl_error;
}
uint64_t liza_rt_tls_bytes(void){return (uint64_t)liza_tls_managed_bytes();}
