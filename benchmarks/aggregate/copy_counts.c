// Diagnostics only, never linked into timed executables. Single-threaded driver.
#include <stdint.h>
#include <stdio.h>
static uint64_t calls, bytes;
void study_record_copy(uint64_t size){++calls;bytes+=size;}
__attribute__((destructor)) static void report(void){
 fprintf(stderr,"{\"copy_calls\":%llu,\"copy_bytes\":%llu}\n",(unsigned long long)calls,(unsigned long long)bytes);
}
