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
