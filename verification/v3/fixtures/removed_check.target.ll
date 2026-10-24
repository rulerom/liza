declare void @llvm.trap()
declare {i8, i1} @llvm.uadd.with.overflow.i8(i8, i8)
define i8 @subject(i8 %x) {
entry:
  %value = add i8 %x, 1
  ret i8 %value
}
