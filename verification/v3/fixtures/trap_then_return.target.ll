declare void @llvm.trap()
declare {i8, i1} @llvm.uadd.with.overflow.i8(i8, i8)
define i8 @subject(i8 %x) {
entry:
  %pair = call {i8, i1} @llvm.uadd.with.overflow.i8(i8 %x, i8 1)
  %value = extractvalue {i8, i1} %pair, 0
  %overflow = extractvalue {i8, i1} %pair, 1
  br i1 %overflow, label %fail, label %ok
fail:
  call void @llvm.trap()
  ret i8 0
ok:
  ret i8 %value
}
