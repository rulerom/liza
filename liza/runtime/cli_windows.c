/* Borrow the UTF-16 argv prepared by the CRT for wmain. No ANSI conversion. */
#define WIN32_LEAN_AND_MEAN
#include <windows.h>
#include <stdint.h>
static uint32_t count;
static wchar_t **arguments;
void liza_rt_cli_init(int argc,wchar_t **argv) {count=argc>0?(uint32_t)argc:0;arguments=argv;}
uint32_t liza_rt_cli_count(void) {return count;}
const wchar_t *liza_rt_cli_path(uint32_t index) {return index<count?arguments[index]:0;}
uint32_t liza_rt_cli_equals(uint32_t index,const uint8_t *text,uint32_t size) {
    if(index>=count)return 0;
    const wchar_t *arg=arguments[index];uint32_t i=0,j=0;
    while(i<size) {
        uint32_t cp=text[i++],extra=0;
        if(!cp)return 0; /* An argument cannot contain an embedded NUL. */
        if(cp>=0x80) {
            if(cp<0xe0){cp&=31;extra=1;}
            else if(cp<0xf0){cp&=15;extra=2;}
            else {cp&=7;extra=3;}
            if(extra>size-i)return 0;
            while(extra--)cp=(cp<<6)|(text[i++]&63);
        }
        // Text is a compiler-validated UTF-8 literal. Compare UTF-16 code units.
        if(cp>0xffff) {
            cp-=0x10000;
            if(arg[j]!=(wchar_t)(0xd800+(cp>>10)))return 0;
            j++;
            if(arg[j]!=(wchar_t)(0xdc00+(cp&1023)))return 0;
            j++;
        } else {if(arg[j]!=(wchar_t)cp)return 0;j++;}
    }
    return arg[j]==0;
}
