// Scalar port of b320611 liza/stdlib/{json,utf8_stream}.liza.
// VALUE_STATE changes only the update convention, not the automaton.
#include <array>
#include <new>
#include <cstdint>
#include <limits>
using u8=uint8_t; using u32=uint32_t; using u64=uint64_t;
struct Encoding { u64 position=0,count=0,start=0; u32 remaining=0; u8 lower=128,upper=191; u32 error=0; u64 offset=0; };
struct State {
 Encoding encoding; u64 position=0; std::array<u8,64> stack{}; u32 depth=0;
 bool root_done=false; u32 mode=0; bool key=false; u32 word=0,index=0,digits=0,unit=0;
 u64 escape_start=0,high_start=0; u32 error=0; u64 offset=0;
};
static void encoding_byte(Encoding& n,u8 b) {
 if(n.error)return;
 if(n.position==UINT64_MAX){n.error=2;n.offset=n.position;return;}
 if(n.remaining==0){
  n.start=n.position;
  if(b<128){if(n.count==UINT64_MAX){n.error=2;n.offset=n.position;return;}++n.count;}
  else {
   n.lower=128;n.upper=191;
   if(b>=194&&b<=223)n.remaining=1;
   else if(b>=224&&b<=239){n.remaining=2;if(b==224)n.lower=160;if(b==237)n.upper=159;}
   else if(b>=240&&b<=244){n.remaining=3;if(b==240)n.lower=144;if(b==244)n.upper=143;}
   else {n.error=1;n.offset=n.start;return;}
  }
 }else{
  if(b<n.lower||b>n.upper){n.error=1;n.offset=n.start;return;}
  --n.remaining;n.lower=128;n.upper=191;
  if(n.remaining==0){if(n.count==UINT64_MAX){n.error=2;n.offset=n.position;return;}++n.count;}
 }
 ++n.position;
}
static void fail(State& n,u32 code,u64 at){n.error=code;n.offset=at;}
static void done(State& n){
 if(n.depth==0)n.root_done=true;
 else {auto& c=n.stack.at(n.depth-1);c=(c==1||c==3)?2:7;}
}
static bool space(u8 b){return b==32||b==9||b==10||b==13;}
static bool digit(u8 b){return b>=48&&b<=57;}
static u32 hex(u8 b){if(b>=48&&b<=57)return b-48;if(b>=65&&b<=70)return b-55;if(b>=97&&b<=102)return b-87;return 16;}
static void step(State& n,u8 b){
 if(n.mode==1){
  if(b<32){fail(n,1,n.position);return;}
  if(b==34){n.mode=0;if(n.key)n.stack.at(n.depth-1)=5;else done(n);return;}
  if(b==92){n.mode=2;n.escape_start=n.position;}return;
 }
 if(n.mode==2){
  if(b==34||b==92||b==47||b==98||b==102||b==110||b==114||b==116){n.mode=1;return;}
  if(b==117){n.mode=3;n.digits=0;n.unit=0;return;}fail(n,3,n.position);return;
 }
 if(n.mode==4){if(b!=92){fail(n,4,n.high_start);return;}n.mode=5;return;}
 if(n.mode==5){if(b!=117){fail(n,4,n.high_start);return;}n.mode=6;n.digits=0;n.unit=0;return;}
 if(n.mode==3||n.mode==6){
  u32 x=hex(b);if(x==16){fail(n,3,n.position);return;}
  n.unit=n.unit*16+x;++n.digits;
  if(n.digits==4){
   if(n.mode==6){if(n.unit<56320||n.unit>57343){fail(n,4,n.high_start);return;}n.mode=1;return;}
   if(n.unit>=55296&&n.unit<=56319){n.mode=4;n.high_start=n.escape_start;return;}
   if(n.unit>=56320&&n.unit<=57343){fail(n,4,n.escape_start);return;}n.mode=1;
  }return;
 }
 if(n.mode==20){
  u8 expected=0;u32 length=4;
  if(n.word==1){if(n.index==1)expected=114;if(n.index==2)expected=117;if(n.index==3)expected=101;}
  if(n.word==2){length=5;if(n.index==1)expected=97;if(n.index==2)expected=108;if(n.index==3)expected=115;if(n.index==4)expected=101;}
  if(n.word==3)expected=n.index==1?117:108;
  if(b!=expected){fail(n,1,n.position);return;}++n.index;
  if(n.index==length){n.mode=0;done(n);}return;
 }
 if(n.mode>=10&&n.mode<=17){
  if(digit(b)){
   if(n.mode==11){fail(n,2,n.position);return;}
   if(n.mode==10)n.mode=b==48?11:12;
   if(n.mode==13)n.mode=14;
   if(n.mode==15||n.mode==16)n.mode=17;return;
  }
  if((n.mode==11||n.mode==12)&&b==46){n.mode=13;return;}
  if((n.mode==11||n.mode==12||n.mode==14)&&(b==101||b==69)){n.mode=15;return;}
  if(n.mode==15&&(b==43||b==45)){n.mode=16;return;}
  if(n.mode==10||n.mode==13||n.mode==15||n.mode==16){fail(n,2,n.position);return;}
  if(!(space(b)||b==44||b==93||b==125)){fail(n,2,n.position);return;}
  n.mode=0;done(n);
 }
 if(space(b))return;
 u8 context=0;if(n.depth>0)context=n.stack.at(n.depth-1);
 if(b==93&&(context==1||context==2)){--n.depth;return;}
 if(b==125&&(context==4||context==7)){--n.depth;return;}
 if(context==2||context==7){if(b!=44){fail(n,1,n.position);return;}n.stack.at(n.depth-1)=context==2?3:8;return;}
 if(context==5){if(b!=58){fail(n,1,n.position);return;}n.stack.at(n.depth-1)=6;return;}
 if(context==4||context==8){if(b!=34){fail(n,1,n.position);return;}n.key=true;n.mode=1;return;}
 if(n.depth==0&&n.root_done){fail(n,1,n.position);return;}
 if(b==91||b==123){if(n.depth==64){fail(n,7,n.position);return;}done(n);n.stack.at(n.depth)=b==91?1:4;++n.depth;return;}
 if(b==34){n.key=false;n.mode=1;return;}
 if(b==45){n.mode=10;return;}
 if(digit(b)){n.mode=b==48?11:12;return;}
 if(b==116||b==102||b==110){n.mode=20;n.index=1;n.word=b==116?1:(b==102?2:3);return;}
 fail(n,1,n.position);
}
static State step_value(State n,u8 b){step(n,b);return n;}
static Encoding encoding_value(Encoding n,u8 b){encoding_byte(n,b);return n;}
static State finish(State n){
 if(n.error)return n;
 if(n.encoding.error||n.encoding.remaining){fail(n,5,n.encoding.error?n.encoding.offset:n.encoding.start);return n;}
 if(n.mode==11||n.mode==12||n.mode==14||n.mode==17){n.mode=0;done(n);}
 if(n.mode==4||n.mode==5||n.mode==6){fail(n,4,n.high_start);return n;}
 if(n.mode!=0||n.depth!=0||!n.root_done)fail(n,6,n.position);
 return n;
}
extern "C" {
u64 stream_size(){return sizeof(State);}
void stream_start(void* p){new(p) State{};}
void stream_feed(void* p,const u8* bytes,u32 length){
 auto& n=*static_cast<State*>(p);if(n.error)return;
 for(u32 i=0;i<length;++i){
#ifdef VALUE_STATE
  n.encoding=encoding_value(n.encoding,bytes[i]);
#else
  encoding_byte(n.encoding,bytes[i]);
#endif
  if(n.encoding.error){fail(n,n.encoding.error==1?5:8,n.encoding.offset);return;}
#ifdef VALUE_STATE
  n=step_value(n,bytes[i]);
#else
  step(n,bytes[i]);
#endif
  if(n.error)return;++n.position;
 }
}
u32 stream_pending(const void* p){return static_cast<const State*>(p)->error;}
u32 stream_status(const void* p){return finish(*static_cast<const State*>(p)).error;}
u64 stream_value(const void* p){auto n=finish(*static_cast<const State*>(p));return n.error?n.offset:n.position;}
}
