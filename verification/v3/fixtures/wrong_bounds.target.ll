declare void @llvm.trap()
define i8 @subject(i32 %index) {
entry:
  %array = alloca [4 x i8], align 1
  store [4 x i8] [i8 10, i8 20, i8 30, i8 40], ptr %array, align 1
  %valid = icmp ule i32 %index, 4
  br i1 %valid, label %ok, label %fail
fail:
  call void @llvm.trap()
  unreachable
ok:
  %p = getelementptr [4 x i8], ptr %array, i32 0, i32 %index
  %value = load i8, ptr %p, align 1
  ret i8 %value
}
