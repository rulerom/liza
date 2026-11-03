/* Diagnostic-only wall-clock stages. Never linked into preserved baseline. */
#define STAGE_BINS 10001
static uint64_t stage_hist[4][STAGE_BINS],stage_max[4],stage_count;
static uint64_t stage_rx_start,stage_rx_end,stage_first,stage_last;
static unsigned stage_sends,stage_ordinal,stage_active,stage_samples;
struct stage_sample {uint64_t seq,rx_end,first_send_enter,last_send_return;};
static struct stage_sample stage_records[4096];
static void stage_observe(unsigned which,uint64_t ns){
 unsigned bin=ns/1000<STAGE_BINS?(unsigned)(ns/1000):STAGE_BINS-1;
 stage_hist[which][bin]++;if(ns>stage_max[which])stage_max[which]=ns;
}
static void stage_receive(uint64_t begin,uint64_t end,uint32_t seq,int active){
 stage_rx_start=begin;stage_rx_end=end;stage_ordinal=seq;stage_active=active;stage_sends=0;stage_first=stage_last=0;
}
static void stage_send_begin(void){if(stage_active&&++stage_sends==1)stage_first=now();}
static void stage_send_end(void){if(stage_active&&stage_sends==RECEIVERS)stage_last=now();}
static void stage_next(void){
 if(stage_active&&stage_last){
  uint64_t end=now();stage_count++;
  stage_observe(0,stage_rx_end-stage_rx_start);
  stage_observe(1,stage_first-stage_rx_end);
  stage_observe(2,stage_last-stage_first);
  stage_observe(3,end-stage_last);
  if(stage_ordinal%256==0){
   if(stage_samples>=4096)abort();
   stage_records[stage_samples++]=(struct stage_sample){stage_ordinal,stage_rx_end,stage_first,stage_last};
  }
 }
 stage_active=0;
}
static void stage_output(void){
 const char *names[]={"native_receive","receive_return_to_first_send","fanout","last_send_to_next"};
 printf("\"stage_timing\":{\"count\":%llu,\"histograms_1us\":{",(unsigned long long)stage_count);
 for(unsigned s=0;s<4;s++){
  printf("%s\"%s\":{",s?",":"",names[s]);int first=1;
  for(unsigned b=0;b<STAGE_BINS;b++)if(stage_hist[s][b]){printf("%s\"%u\":%llu",first?"":",",b,(unsigned long long)stage_hist[s][b]);first=0;}
  printf("}");
 }
 printf("},\"max_ns\":[%llu,%llu,%llu,%llu],\"samples\":[",(unsigned long long)stage_max[0],(unsigned long long)stage_max[1],(unsigned long long)stage_max[2],(unsigned long long)stage_max[3]);
 for(unsigned i=0;i<stage_samples;i++){struct stage_sample *s=&stage_records[i];printf("%s[%llu,%llu,%llu,%llu]",i?",":"",(unsigned long long)s->seq,(unsigned long long)s->rx_end,(unsigned long long)s->first_send_enter,(unsigned long long)s->last_send_return);}
 printf("]},");
}
