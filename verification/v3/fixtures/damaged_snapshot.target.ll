define i8 @subject(i8 %old, i8 %new) {
entry:
  %original = alloca i8, align 1
  %updated = alloca i8, align 1
  store i8 %old, ptr %original, align 1
  store i8 %old, ptr %updated, align 1
  store i8 %new, ptr %original, align 1
  %result = load i8, ptr %original, align 1
  ret i8 %result
}
