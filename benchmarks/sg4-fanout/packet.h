/* RTP parser shared by the C callback and independent measurement observer. */
#include <stdint.h>
#include <stddef.h>
struct rtp_header { uint8_t version,marker,payload_type; uint16_t sequence; uint32_t timestamp,ssrc,payload_offset,payload_length; };
static uint16_t be16(const uint8_t *p) {return (uint16_t)(((uint16_t)p[0]<<8)|p[1]);}
static uint32_t be32(const uint8_t *p) {return ((uint32_t)be16(p)<<16)|be16(p+2);}
/* Equivalent header extraction, CSRC, extension and padding validation. */
static int parse_rtp(const uint8_t *data, size_t size, struct rtp_header *out) {
    if(size<12 || data[0]>>6!=2)return 0;
    size_t header=12u+4u*(data[0]&15u);
    if(header>size)return 0;
    if(data[0]&16u) {
        if(size-header<4)return 0;
        size_t words=((size_t)data[header+2]<<8)|data[header+3];
        if(words>(size-header-4)/4)return 0;
        header+=4+words*4;
    }
    if(data[0]&32u) {
        uint8_t padding=data[size-1];
        if(!padding || padding>size-header)return 0;
    }
    size_t payload_length=size-header;
    if(data[0]&32u)payload_length-=data[size-1];
    *out=(struct rtp_header){(uint8_t)(data[0]>>6),!!(data[1]&128),data[1]&127,
        be16(data+2),be32(data+4),be32(data+8),(uint32_t)header,(uint32_t)payload_length};
    return 1;
}

