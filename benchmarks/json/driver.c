// Shared measurement/probe driver, not part of the parsers. No LTO across ABI.
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>
#ifdef _WIN32
#include <windows.h>
#include <fcntl.h>
#include <io.h>
#else
#include <sys/resource.h>
#endif
extern uint64_t stream_size(void);
extern void stream_start(void*);
extern void stream_feed(void*,const uint8_t*,uint32_t);
extern uint32_t stream_pending(const void*);
extern uint32_t stream_status(const void*);
extern uint64_t stream_value(const void*);
static double now(void){
#ifdef _WIN32
 LARGE_INTEGER n,f;QueryPerformanceCounter(&n);QueryPerformanceFrequency(&f);return (double)n.QuadPart/f.QuadPart;
#else
 struct timespec t;if(clock_gettime(CLOCK_MONOTONIC,&t))exit(10);return t.tv_sec+t.tv_nsec*1e-9;
#endif
}
static uint64_t rss(void){
#ifdef _WIN32
 return 0; // unavailable, not a claim of zero memory use
#else
 struct rusage u;if(getrusage(RUSAGE_SELF,&u))return 0;
#ifdef __APPLE__
 return u.ru_maxrss;
#else
 return (uint64_t)u.ru_maxrss*1024;
#endif
#endif
}
static uint32_t word(const uint8_t*p){return p[0]|((uint32_t)p[1]<<8)|((uint32_t)p[2]<<16)|((uint32_t)p[3]<<24);}
static int probe(void* state){
#ifdef _WIN32
 _setmode(_fileno(stdin),_O_BINARY);_setmode(_fileno(stdout),_O_BINARY);
#endif
 uint8_t header[4],out[12];size_t n;
 while((n=fread(header,1,4,stdin))){
  if(n!=4)return 2;uint32_t chunks=word(header);stream_start(state);
  for(uint32_t i=0;i<chunks;++i){
   if(fread(header,1,4,stdin)!=4)return 2;uint32_t size=word(header);
   if(size>16*1024*1024)return 2;
   uint8_t* bytes=malloc(size?size:1);if(!bytes)return 3;
   if(fread(bytes,1,size,stdin)!=size){free(bytes);return 2;}
   stream_feed(state,bytes,size);free(bytes);
   // finish must not mutate a pending parser between chunks.
   (void)stream_status(state);(void)stream_value(state);
  }
  uint32_t status=stream_status(state);uint64_t value=stream_value(state);
  for(int i=0;i<4;++i)out[i]=(uint8_t)(status>>(8*i));
  for(int i=0;i<8;++i)out[4+i]=(uint8_t)(value>>(8*i));
  if(fwrite(out,1,12,stdout)!=12)return 3;
 }
 return ferror(stdin)?3:0;
}
static int check(void* state,const char* path){
 FILE* f=fopen(path,"rb");if(!f)return 3;stream_start(state);
 uint8_t data[2048];size_t n;
 while((n=fread(data,1,sizeof(data),f))){stream_feed(state,data,(uint32_t)n);if(stream_pending(state))break;}
 int bad=ferror(f);if(fclose(f))bad=1;if(bad)return 3;
 uint32_t status=stream_status(state);if(!status){puts("OK");return 0;}
 const char* names[]={"","Syntax","InvalidNumber","InvalidEscape","InvalidSurrogate","InvalidUtf8","UnexpectedEof","DepthLimit","SizeOverflow"};
 if(status>8)return 3;
 fprintf(stderr,"%s at byte %llu\n",names[status],(unsigned long long)stream_value(state));return status>=7?4:1;
}
static int bench(void* state,const char* path,uint32_t chunk,uint32_t rounds){
 if(!chunk||!rounds||chunk>16777216)return 2;
 FILE* f=fopen(path,"rb");if(!f)return 3;
 if(fseek(f,0,SEEK_END))return 3;long size=ftell(f);if(size<0||size>16777216)return 2;
 rewind(f);uint8_t* bytes=malloc(size?size:1);if(!bytes)return 3;
 if(fread(bytes,1,size,f)!=(size_t)size)return 3;if(fclose(f))return 3;
 uint64_t checksum=0,value=0;uint32_t status=0;
 // One untimed warmup, then measured iterations. Input and state allocations
 // are outside the timer; initialize + feed + finish and result consumption are inside.
 for(int warmup=1;warmup>=0;--warmup){
  double start=now();uint32_t limit=warmup?1:rounds;
  for(uint32_t r=0;r<limit;++r){
   stream_start(state);
   for(size_t i=0;i<(size_t)size;i+=chunk){
    uint32_t n=(uint32_t)((size_t)size-i);if(n>chunk)n=chunk;
    stream_feed(state,bytes+i,n);if(stream_pending(state))break;
   }
   status=stream_status(state);value=stream_value(state);checksum+=value+status;
  }
  double elapsed=now()-start;
  if(!warmup)printf("{\"seconds\":%.9f,\"status\":%u,\"value\":%llu,\"iterations\":%u,\"checksum\":%llu,\"state_bytes\":%llu,\"max_rss_bytes\":%llu}\n",elapsed,status,(unsigned long long)value,rounds,(unsigned long long)checksum,(unsigned long long)stream_size(),(unsigned long long)rss());
 }
 free(bytes);return 0;
}
int main(int argc,char**argv){
 void* state=malloc((size_t)stream_size());if(!state)return 3;int result=2;
 if(argc==2&&!strcmp(argv[1],"probe"))result=probe(state);
 else if(argc==3&&!strcmp(argv[1],"check"))result=check(state,argv[2]);
 else if(argc==5&&!strcmp(argv[1],"bench"))result=bench(state,argv[2],(uint32_t)strtoul(argv[3],0,10),(uint32_t)strtoul(argv[4],0,10));
 free(state);return result;
}
