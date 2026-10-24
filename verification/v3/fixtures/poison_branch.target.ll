declare void @llvm.trap()
declare {i8, i1} @llvm.uadd.with.overflow.i8(i8, i8)
define i8 @subject(i8 %x) {
entry:
  %value = add nuw i8 %x, 1
  %cond = icmp eq i8 %value, 0
  br i1 %cond, label %a, label %b
a:
  ret i8 0
b:
  ret i8 %value
}
