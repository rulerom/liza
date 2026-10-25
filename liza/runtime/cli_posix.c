/* Borrow argv verbatim. No decoding, allocation or argument copies. */
#include <stdint.h>
#include <string.h>
static uint32_t count;
static char **arguments;
void liza_rt_cli_init(int argc, char **argv) {count=argc>0?(uint32_t)argc:0;arguments=argv;}
uint32_t liza_rt_cli_count(void) {return count;}
const char *liza_rt_cli_path(uint32_t index) {return index<count?arguments[index]:0;}
uint32_t liza_rt_cli_equals(uint32_t index,const uint8_t *text,uint32_t size) {
    if(index>=count)return 0;
    const char *arg=arguments[index];
    return strlen(arg)==size && memcmp(arg,text,size)==0;
}

/* Bounded ASCII inspection, including NUL. Invalid/non-ASCII => 256. */
uint32_t liza_rt_cli_ascii_at(uint32_t arg,uint32_t index) {
    if(arg>=count || index>=64)return 256;
    const unsigned char *p=(const unsigned char*)arguments[arg];
    for(uint32_t i=0;i<index;i++)if(!p[i])return 256;
    uint32_t value=(uint32_t)p[index];
    return value<128?value:256;
}
