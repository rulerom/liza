// Scalar port of the same bounded streaming automaton; no DOM or token storage.
#[derive(Clone, Copy)]
struct Encoding {position:u64,count:u64,start:u64,remaining:u32,lower:u8,upper:u8,error:u32,offset:u64}
impl Default for Encoding {fn default()->Self {Self{position:0,count:0,start:0,remaining:0,lower:128,upper:191,error:0,offset:0}}}
#[derive(Clone, Copy)]
struct State {encoding:Encoding,position:u64,stack:[u8;64],depth:u32,root_done:bool,mode:u32,key:bool,word:u32,index:u32,digits:u32,unit:u32,escape_start:u64,high_start:u64,error:u32,offset:u64}
impl Default for State {fn default()->Self {Self{encoding:Encoding::default(),position:0,stack:[0;64],depth:0,root_done:false,mode:0,key:false,word:0,index:0,digits:0,unit:0,escape_start:0,high_start:0,error:0,offset:0}}}
fn encoding_byte(n:&mut Encoding,b:u8){
 if n.error!=0{return;}
 if n.position==u64::MAX{n.error=2;n.offset=n.position;return;}
 if n.remaining==0{
  n.start=n.position;
  if b<128{if n.count==u64::MAX{n.error=2;n.offset=n.position;return;}n.count+=1;}
  else{
   n.lower=128;n.upper=191;
   if b>=194&&b<=223{n.remaining=1;}
   else if b>=224&&b<=239{n.remaining=2;if b==224{n.lower=160;}if b==237{n.upper=159;}}
   else if b>=240&&b<=244{n.remaining=3;if b==240{n.lower=144;}if b==244{n.upper=143;}}
   else{n.error=1;n.offset=n.start;return;}
  }
 }else{
  if b<n.lower||b>n.upper{n.error=1;n.offset=n.start;return;}
  n.remaining-=1;n.lower=128;n.upper=191;
  if n.remaining==0{if n.count==u64::MAX{n.error=2;n.offset=n.position;return;}n.count+=1;}
 }
 n.position+=1;
}
fn fail(n:&mut State,code:u32,at:u64){n.error=code;n.offset=at;}
fn done(n:&mut State){if n.depth==0{n.root_done=true;}else{let c=&mut n.stack[(n.depth-1) as usize];*c=if *c==1||*c==3{2}else{7};}}
fn space(b:u8)->bool{b==32||b==9||b==10||b==13}
fn digit(b:u8)->bool{b>=48&&b<=57}
fn hex(b:u8)->u32{if b>=48&&b<=57{return (b-48) as u32;}if b>=65&&b<=70{return (b-55) as u32;}if b>=97&&b<=102{return (b-87) as u32;}16}
fn step(n:&mut State,b:u8){
 if n.mode==1{
  if b<32{fail(n,1,n.position);return;}
  if b==34{n.mode=0;if n.key{n.stack[(n.depth-1) as usize]=5;}else{done(n);}return;}
  if b==92{n.mode=2;n.escape_start=n.position;}return;
 }
 if n.mode==2{
  if b==34||b==92||b==47||b==98||b==102||b==110||b==114||b==116{n.mode=1;return;}
  if b==117{n.mode=3;n.digits=0;n.unit=0;return;}fail(n,3,n.position);return;
 }
 if n.mode==4{if b!=92{fail(n,4,n.high_start);return;}n.mode=5;return;}
 if n.mode==5{if b!=117{fail(n,4,n.high_start);return;}n.mode=6;n.digits=0;n.unit=0;return;}
 if n.mode==3||n.mode==6{
  let x=hex(b);if x==16{fail(n,3,n.position);return;}
  n.unit=n.unit*16+x;n.digits+=1;
  if n.digits==4{
   if n.mode==6{if n.unit<56320||n.unit>57343{fail(n,4,n.high_start);return;}n.mode=1;return;}
   if n.unit>=55296&&n.unit<=56319{n.mode=4;n.high_start=n.escape_start;return;}
   if n.unit>=56320&&n.unit<=57343{fail(n,4,n.escape_start);return;}n.mode=1;
  }return;
 }
 if n.mode==20{
  let mut expected=0;let mut length=4;
  if n.word==1{if n.index==1{expected=114;}if n.index==2{expected=117;}if n.index==3{expected=101;}}
  if n.word==2{length=5;if n.index==1{expected=97;}if n.index==2{expected=108;}if n.index==3{expected=115;}if n.index==4{expected=101;}}
  if n.word==3{expected=if n.index==1{117}else{108};}
  if b!=expected{fail(n,1,n.position);return;}n.index+=1;
  if n.index==length{n.mode=0;done(n);}return;
 }
 if n.mode>=10&&n.mode<=17{
  if digit(b){
   if n.mode==11{fail(n,2,n.position);return;}
   if n.mode==10{n.mode=if b==48{11}else{12};}
   if n.mode==13{n.mode=14;}
   if n.mode==15||n.mode==16{n.mode=17;}return;
  }
  if (n.mode==11||n.mode==12)&&b==46{n.mode=13;return;}
  if (n.mode==11||n.mode==12||n.mode==14)&&(b==101||b==69){n.mode=15;return;}
  if n.mode==15&&(b==43||b==45){n.mode=16;return;}
  if n.mode==10||n.mode==13||n.mode==15||n.mode==16{fail(n,2,n.position);return;}
  if !(space(b)||b==44||b==93||b==125){fail(n,2,n.position);return;}
  n.mode=0;done(n);
 }
 if space(b){return;}
 let context=if n.depth>0{n.stack[(n.depth-1) as usize]}else{0};
 if b==93&&(context==1||context==2){n.depth-=1;return;}
 if b==125&&(context==4||context==7){n.depth-=1;return;}
 if context==2||context==7{if b!=44{fail(n,1,n.position);return;}n.stack[(n.depth-1) as usize]=if context==2{3}else{8};return;}
 if context==5{if b!=58{fail(n,1,n.position);return;}n.stack[(n.depth-1) as usize]=6;return;}
 if context==4||context==8{if b!=34{fail(n,1,n.position);return;}n.key=true;n.mode=1;return;}
 if n.depth==0&&n.root_done{fail(n,1,n.position);return;}
 if b==91||b==123{if n.depth==64{fail(n,7,n.position);return;}done(n);n.stack[n.depth as usize]=if b==91{1}else{4};n.depth+=1;return;}
 if b==34{n.key=false;n.mode=1;return;}
 if b==45{n.mode=10;return;}
 if digit(b){n.mode=if b==48{11}else{12};return;}
 if b==116||b==102||b==110{n.mode=20;n.index=1;n.word=if b==116{1}else if b==102{2}else{3};return;}
 fail(n,1,n.position);
}
fn finish(mut n:State)->State{
 if n.error!=0{return n;}
 if n.encoding.error!=0||n.encoding.remaining!=0{let at=if n.encoding.error!=0{n.encoding.offset}else{n.encoding.start};fail(&mut n,5,at);return n;}
 if n.mode==11||n.mode==12||n.mode==14||n.mode==17{n.mode=0;done(&mut n);}
 if n.mode==4||n.mode==5||n.mode==6{let at=n.high_start;fail(&mut n,4,at);return n;}
 if n.mode!=0||n.depth!=0||!n.root_done{let at=n.position;fail(&mut n,6,at);}
 n
}
// Only the shared benchmark driver calls this ABI: correctly sized/aligned opaque
// state and valid byte spans, allocated before timing. The parser itself is safe Rust.
#[no_mangle] pub extern "C" fn stream_size()->u64{std::mem::size_of::<State>() as u64}
#[no_mangle] pub unsafe extern "C" fn stream_start(p:*mut u8){(p as *mut State).write(State::default());}
#[no_mangle] pub unsafe extern "C" fn stream_feed(p:*mut u8,b:*const u8,len:u32){
 let n=&mut *(p as *mut State);if n.error!=0{return;}
 for &byte in std::slice::from_raw_parts(b,len as usize){
  encoding_byte(&mut n.encoding,byte);
  if n.encoding.error!=0{fail(n,if n.encoding.error==1{5}else{8},n.encoding.offset);return;}
  step(n,byte);if n.error!=0{return;}n.position+=1;
 }
}
#[no_mangle] pub unsafe extern "C" fn stream_pending(p:*const u8)->u32{(*(p as *const State)).error}
#[no_mangle] pub unsafe extern "C" fn stream_status(p:*const u8)->u32{finish(*(p as *const State)).error}
#[no_mangle] pub unsafe extern "C" fn stream_value(p:*const u8)->u64{let n=finish(*(p as *const State));if n.error!=0{n.offset}else{n.position}}
