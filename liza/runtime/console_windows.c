/* Same private scalar ABI as POSIX: error in high word, byte count in low.
 * Text console output uses Unicode without changing process/console code pages.
 */
#define WIN32_LEAN_AND_MEAN
#include <windows.h>
#include <stdint.h>

static uint32_t error_kind(DWORD e) {
    switch(e) {
    case ERROR_INVALID_HANDLE: return 1;
    case ERROR_ACCESS_DENIED: return 2;
    case ERROR_BROKEN_PIPE: case ERROR_NO_DATA: case ERROR_PIPE_NOT_CONNECTED: return 3;
    case ERROR_PIPE_BUSY: case ERROR_IO_PENDING: return 4;
    case ERROR_DISK_FULL: case ERROR_HANDLE_DISK_FULL: return 5;
    default: return 6;
    }
}
static uint64_t result(uint32_t error,uint32_t done) {return ((uint64_t)error<<32)|done;}
static uint64_t write_stream(DWORD stream,const uint8_t *data,uint32_t length) {
    if(!length)return 0;
    HANDLE out=GetStdHandle(stream);
    if(!out || out==INVALID_HANDLE_VALUE)return result(1,0);
    uint32_t done=0;
    while(done<length) {
        DWORD count=length-done,written=0;
        if(count>1048576)count=1048576;
        if(!WriteFile(out,data+done,count,&written,NULL))return result(error_kind(GetLastError()),done);
        done+=written;
        /* Successful zero-byte nonblocking pipe write must not spin. */
        if(!written)return result(GetFileType(out)==FILE_TYPE_PIPE?4:6,done);
    }
    return done;
}
static uint64_t text_stream(DWORD stream,const uint8_t *data,uint32_t length) {
    if(!length)return 0;
    HANDLE out=GetStdHandle(stream);
    if(!out || out==INVALID_HANDLE_VALUE)return result(1,0);
    DWORD mode;
    if(!GetConsoleMode(out,&mode))return write_stream(stream,data,length);
    uint32_t done=0;
    while(done<length) {
        WCHAR wide[512];
        uint32_t bytes[513]; /* UTF-8 bytes consumed after each UTF-16 unit. */
        DWORD units=0;uint32_t cursor=done;
        bytes[0]=0;
        while(cursor<length && units<510) {
            uint32_t start=cursor,cp=data[cursor++],extra=0,min=0;
            if(cp>=0x80) {
                if(cp>=0xc2 && cp<=0xdf){extra=1;min=0x80;cp&=31;}
                else if(cp>=0xe0 && cp<=0xef){extra=2;min=0x800;cp&=15;}
                else if(cp>=0xf0 && cp<=0xf4){extra=3;min=0x10000;cp&=7;}
                else return result(6,done);
                if(extra>length-cursor)return result(6,done);
                while(extra--) {uint32_t b=data[cursor++];if((b&0xc0)!=0x80)return result(6,done);cp=(cp<<6)|(b&63);}
                if(cp<min || cp>0x10ffff || (cp>=0xd800 && cp<=0xdfff))return result(6,done);
            }
            if(cp>0xffff) {
                cp-=0x10000;wide[units++]=(WCHAR)(0xd800+(cp>>10));bytes[units]=start-done;
                wide[units++]=(WCHAR)(0xdc00+(cp&1023));
            } else wide[units++]=(WCHAR)cp;
            bytes[units]=cursor-done;
        }
        DWORD offset=0;
        while(offset<units) {
            DWORD written=0;
            if(!WriteConsoleW(out,wide+offset,units-offset,&written,NULL))return result(error_kind(GetLastError()),done+bytes[offset]);
            if(!written)return result(6,done+bytes[offset]);
            offset+=written;
        }
        done=cursor;
    }
    return done;
}
static uint64_t number(DWORD stream,uint64_t value,int negative) {
    uint8_t buffer[21];unsigned start=sizeof buffer;
    do{buffer[--start]=(uint8_t)('0'+value%10);value/=10;}while(value);
    if(negative)buffer[--start]='-';
    return text_stream(stream,buffer+start,(uint32_t)(sizeof buffer-start));
}
uint64_t liza_rt_print_u64(uint64_t value){return number(STD_OUTPUT_HANDLE,value,0);}
uint64_t liza_rt_print_i64(int64_t value){return number(STD_OUTPUT_HANDLE,value<0?UINT64_C(0)-(uint64_t)value:(uint64_t)value,value<0);}

uint64_t liza_rt_write(const uint8_t *p,uint32_t n){return write_stream(STD_OUTPUT_HANDLE,p,n);}
uint64_t liza_rt_write_text(const uint8_t *p,uint32_t n){return text_stream(STD_OUTPUT_HANDLE,p,n);}
uint64_t liza_rt_err(const uint8_t *p,uint32_t n){return write_stream(STD_ERROR_HANDLE,p,n);}
uint64_t liza_rt_err_text(const uint8_t *p,uint32_t n){return text_stream(STD_ERROR_HANDLE,p,n);}
uint64_t liza_rt_err_print_u64(uint64_t n){return number(STD_ERROR_HANDLE,n,0);}
uint64_t liza_rt_err_print_i64(int64_t n){return number(STD_ERROR_HANDLE,n<0?UINT64_C(0)-(uint64_t)n:(uint64_t)n,n<0);}
