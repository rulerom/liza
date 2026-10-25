; ModuleID = 'parser.8ef06c2e83c6299e-cgu.0'
source_filename = "parser.8ef06c2e83c6299e-cgu.0"
target datalayout = "e-m:o-p270:32:32-p271:32:32-p272:64:64-i64:64-i128:128-n32:64-S128-Fn32"
target triple = "arm64-apple-macosx11.0.0"

@alloc_84f9d846ecfb9e37dadbe3e781f512ce = private unnamed_addr constant [55 x i8] c"/private/tmp/liza-json-bench/benchmarks/json/parser.rs\00", align 1, !guid !0
@alloc_17c2635886f4fbc2ea36dbf6a4113cf0 = private unnamed_addr constant <{ ptr, [16 x i8] }> <{ ptr @alloc_84f9d846ecfb9e37dadbe3e781f512ce, [16 x i8] c"6\00\00\00\00\00\00\00\1D\00\00\00G\00\00\00" }>, align 8, !guid !1
@alloc_e4ed959f92efea1cff8b4b98f2146f02 = private unnamed_addr constant <{ ptr, [16 x i8] }> <{ ptr @alloc_84f9d846ecfb9e37dadbe3e781f512ce, [16 x i8] c"6\00\00\00\00\00\00\00$\00\00\00&\00\00\00" }>, align 8, !guid !2
@alloc_38ab136aad52e23038f13eabe203b7df = private unnamed_addr constant <{ ptr, [16 x i8] }> <{ ptr @alloc_84f9d846ecfb9e37dadbe3e781f512ce, [16 x i8] c"6\00\00\00\00\00\00\00$\00\00\00\1E\00\00\00" }>, align 8, !guid !3
@alloc_7fcdd0112aa4a922a81991942fa2013b = private unnamed_addr constant <{ ptr, [16 x i8] }> <{ ptr @alloc_84f9d846ecfb9e37dadbe3e781f512ce, [16 x i8] c"6\00\00\00\00\00\00\00/\00\00\00\0A\00\00\00" }>, align 8, !guid !4
@alloc_e67dfff62b8e4ecb323b784eaa923bef = private unnamed_addr constant <{ ptr, [16 x i8] }> <{ ptr @alloc_84f9d846ecfb9e37dadbe3e781f512ce, [16 x i8] c"6\00\00\00\00\00\00\00/\00\00\00\16\00\00\00" }>, align 8, !guid !5
@alloc_2d6ba3368b9b590ce6e8441798328433 = private unnamed_addr constant <{ ptr, [16 x i8] }> <{ ptr @alloc_84f9d846ecfb9e37dadbe3e781f512ce, [16 x i8] c"6\00\00\00\00\00\00\00;\00\00\00/\00\00\00" }>, align 8, !guid !6
@alloc_ca89a41573afe1edc3f237491af5f4cb = private unnamed_addr constant <{ ptr, [16 x i8] }> <{ ptr @alloc_84f9d846ecfb9e37dadbe3e781f512ce, [16 x i8] c"6\00\00\00\00\00\00\00M\00\00\00\1B\00\00\00" }>, align 8, !guid !7
@alloc_232157ae9decd89c9f2076cdf71110bc = private unnamed_addr constant <{ ptr, [16 x i8] }> <{ ptr @alloc_84f9d846ecfb9e37dadbe3e781f512ce, [16 x i8] c"6\00\00\00\00\00\00\00O\00\00\00&\00\00\00" }>, align 8, !guid !8
@alloc_04fe8135d2319897c873529430c986db = private unnamed_addr constant <{ ptr, [16 x i8] }> <{ ptr @alloc_84f9d846ecfb9e37dadbe3e781f512ce, [16 x i8] c"6\00\00\00\00\00\00\00P\00\00\00J\00\00\00" }>, align 8, !guid !9
@alloc_1fb0c37e44d2c7e7dd89cb8d4cf14241 = private unnamed_addr constant <{ ptr, [16 x i8] }> <{ ptr @alloc_84f9d846ecfb9e37dadbe3e781f512ce, [16 x i8] c"6\00\00\00\00\00\00\00Q\00\00\00>\00\00\00" }>, align 8, !guid !10
@alloc_21a6ae3fdeb0c022136d547ac7b9c594 = private unnamed_addr constant <{ ptr, [16 x i8] }> <{ ptr @alloc_84f9d846ecfb9e37dadbe3e781f512ce, [16 x i8] c"6\00\00\00\00\00\00\00T\00\00\00G\00\00\00" }>, align 8, !guid !11
@alloc_e0474d9a635040eab39bac01d02d2ec4 = private unnamed_addr constant <{ ptr, [16 x i8] }> <{ ptr @alloc_84f9d846ecfb9e37dadbe3e781f512ce, [16 x i8] c"6\00\00\00\00\00\00\00T\00\00\00t\00\00\00" }>, align 8, !guid !12
@alloc_67efdafa9b0dc47c916e8f72fff3e807 = private unnamed_addr constant <{ ptr, [16 x i8] }> <{ ptr @alloc_84f9d846ecfb9e37dadbe3e781f512ce, [16 x i8] c"6\00\00\00\00\00\00\00l\00\00\00&\00\00\00" }>, align 8, !guid !13

; parser::done
; Function Attrs: nounwind
define internal fastcc void @_RNvCscgRqy0Y3eGg_6parser4done(ptr noalias nofree noundef nonnull align 8 captures(none) dereferenceable(176) %n) unnamed_addr #0 !guid !17 {
start:
  %0 = getelementptr inbounds nuw i8, ptr %n, i64 144
  %_2 = load i32, ptr %0, align 8, !noundef !18
  %1 = icmp eq i32 %_2, 0
  br i1 %1, label %bb1, label %bb3

bb1:                                              ; preds = %start
  %2 = getelementptr inbounds nuw i8, ptr %n, i64 172
  store i8 1, ptr %2, align 4
  br label %bb11

bb11:                                             ; preds = %bb4, %bb1
  ret void

bb3:                                              ; preds = %start
  %_7.0 = add i32 %_2, -1
  %_4 = zext i32 %_7.0 to i64
  %_8 = icmp ult i32 %_2, 65
  br i1 %_8, label %bb4, label %panic1

bb4:                                              ; preds = %bb3
  %c = getelementptr inbounds nuw i8, ptr %n, i64 %_4
  %_10 = load i8, ptr %c, align 1, !noundef !18
  %3 = add i8 %_10, -1
  %switch.and = and i8 %3, -3
  %switch.selectcmp = icmp eq i8 %switch.and, 0
  %4 = select i1 %switch.selectcmp, i8 2, i8 7
  store i8 %4, ptr %c, align 1
  br label %bb11

panic1:                                           ; preds = %bb3
; call core::panicking::panic_bounds_check
  tail call void @_RNvNtCs9nEiEE0E2Vj_4core9panicking18panic_bounds_check(i64 noundef %_4, i64 noundef 64, ptr noalias nofree noundef readonly align 8 captures(address, read_provenance) dereferenceable(24) @alloc_17c2635886f4fbc2ea36dbf6a4113cf0) #10
  unreachable
}

; Function Attrs: nounwind
define void @stream_feed(ptr nofree noundef %p, ptr nofree noundef readonly captures(address) %b, i32 noundef %len) unnamed_addr #0 !guid !19 {
start:
  %0 = getelementptr inbounds nuw i8, ptr %p, i64 168
  %_6 = load i32, ptr %0, align 8, !noundef !18
  %1 = icmp eq i32 %_6, 0
  br i1 %1, label %bb2, label %bb16

bb2:                                              ; preds = %start
  %_8 = zext i32 %len to i64
  call void @llvm.assume(i1 true) [ "nonnull"(ptr %b) ]
  %_25 = getelementptr inbounds nuw i8, ptr %b, i64 %_8
  %_3231 = icmp eq i32 %len, 0
  br i1 %_3231, label %bb16, label %bb18.lr.ph

bb18.lr.ph:                                       ; preds = %bb2
  %_12 = getelementptr inbounds nuw i8, ptr %p, i64 64
  %2 = getelementptr inbounds nuw i8, ptr %p, i64 100
  %3 = getelementptr inbounds nuw i8, ptr %p, i64 96
  %4 = getelementptr inbounds nuw i8, ptr %p, i64 104
  %5 = getelementptr inbounds nuw i8, ptr %p, i64 105
  %6 = getelementptr inbounds nuw i8, ptr %p, i64 72
  %7 = getelementptr inbounds nuw i8, ptr %p, i64 88
  %8 = getelementptr inbounds nuw i8, ptr %p, i64 80
  %9 = getelementptr inbounds nuw i8, ptr %p, i64 148
  %10 = getelementptr inbounds nuw i8, ptr %p, i64 152
  %.phi.trans.insert.i = getelementptr inbounds nuw i8, ptr %p, i64 156
  %11 = getelementptr inbounds nuw i8, ptr %p, i64 144
  %12 = getelementptr inbounds nuw i8, ptr %p, i64 172
  %13 = getelementptr inbounds nuw i8, ptr %p, i64 164
  %14 = getelementptr inbounds nuw i8, ptr %p, i64 160
  %15 = getelementptr inbounds nuw i8, ptr %p, i64 120
  %16 = getelementptr inbounds nuw i8, ptr %p, i64 128
  %17 = getelementptr inbounds nuw i8, ptr %p, i64 112
  %18 = getelementptr inbounds nuw i8, ptr %p, i64 173
  br label %bb18

bb18:                                             ; preds = %bb18.lr.ph, %bb13
  %iter.sroa.0.032 = phi ptr [ %b, %bb18.lr.ph ], [ %_38, %bb13 ]
  %_38 = getelementptr inbounds nuw i8, ptr %iter.sroa.0.032, i64 1
  %byte = load i8, ptr %iter.sroa.0.032, align 1, !noundef !18
  %_3.i = load i32, ptr %2, align 4, !alias.scope !20, !noundef !18
  switch i32 %_3.i, label %bb16.sink.split [
    i32 0, label %bb2.i
    i32 1, label %bb16.sink.split.loopexit
  ]

bb2.i:                                            ; preds = %bb18
  %_4.i = load i64, ptr %_12, align 8, !alias.scope !20, !noundef !18
  %19 = icmp eq i64 %_4.i, -1
  br i1 %19, label %bb8.loopexit33.sink.split, label %bb4.i

bb4.i:                                            ; preds = %bb2.i
  %_6.i = load i32, ptr %3, align 8, !alias.scope !20, !noundef !18
  %20 = icmp eq i32 %_6.i, 0
  br i1 %20, label %bb5.i, label %bb6.i

bb5.i:                                            ; preds = %bb4.i
  store i64 %_4.i, ptr %8, align 8, !alias.scope !20
  %_8.i = icmp sgt i8 %byte, -1
  br i1 %_8.i, label %bb7.i, label %bb11.i

bb6.i:                                            ; preds = %bb4.i
  %_20.i = load i8, ptr %4, align 8, !alias.scope !20, !noundef !18
  %_19.i = icmp ult i8 %byte, %_20.i
  %_22.i = load i8, ptr %5, align 1, !alias.scope !20
  %_21.i = icmp ugt i8 %byte, %_22.i
  %or.cond6.i = select i1 %_19.i, i1 true, i1 %_21.i
  br i1 %or.cond6.i, label %bb36.i, label %bb37.i

bb11.i:                                           ; preds = %bb5.i
  store i8 -128, ptr %4, align 8, !alias.scope !20
  store i8 -65, ptr %5, align 1, !alias.scope !20
  %21 = add nsw i8 %byte, 62
  %or.cond.i = icmp ult i8 %21, 30
  br i1 %or.cond.i, label %bb13.i, label %bb14.i

bb7.i:                                            ; preds = %bb5.i
  %_9.i = load i64, ptr %6, align 8, !alias.scope !20, !noundef !18
  %22 = icmp eq i64 %_9.i, -1
  br i1 %22, label %bb8.loopexit33.sink.split, label %bb10.i

bb14.i:                                           ; preds = %bb11.i
  %23 = and i8 %byte, -16
  %or.cond4.i = icmp eq i8 %23, -32
  br i1 %or.cond4.i, label %bb16.i, label %bb21.i

bb13.i:                                           ; preds = %bb11.i
  store i32 1, ptr %3, align 8, !alias.scope !20
  br label %_RNvCscgRqy0Y3eGg_6parser13encoding_byte.exit.thread43

bb21.i:                                           ; preds = %bb14.i
  %24 = add nsw i8 %byte, 16
  %or.cond5.i = icmp ult i8 %24, 5
  br i1 %or.cond5.i, label %bb23.i, label %bb28.i

bb16.i:                                           ; preds = %bb14.i
  store i32 2, ptr %3, align 8, !alias.scope !20
  switch i8 %byte, label %_RNvCscgRqy0Y3eGg_6parser13encoding_byte.exit.thread43 [
    i8 -32, label %bb17.i
    i8 -19, label %bb19.i
  ]

bb28.i:                                           ; preds = %bb21.i
  store i32 1, ptr %2, align 4, !alias.scope !20
  store i64 %_4.i, ptr %7, align 8, !alias.scope !20
  br label %bb16.sink.split

bb23.i:                                           ; preds = %bb21.i
  store i32 3, ptr %3, align 8, !alias.scope !20
  switch i8 %byte, label %_RNvCscgRqy0Y3eGg_6parser13encoding_byte.exit.thread43 [
    i8 -16, label %bb24.i
    i8 -12, label %bb26.i
  ]

bb24.i:                                           ; preds = %bb23.i
  store i8 -112, ptr %4, align 8, !alias.scope !20
  br label %_RNvCscgRqy0Y3eGg_6parser13encoding_byte.exit.thread43

bb26.i:                                           ; preds = %bb23.i
  store i8 -113, ptr %5, align 1, !alias.scope !20
  br label %_RNvCscgRqy0Y3eGg_6parser13encoding_byte.exit.thread43

bb17.i:                                           ; preds = %bb16.i
  store i8 -96, ptr %4, align 8, !alias.scope !20
  br label %_RNvCscgRqy0Y3eGg_6parser13encoding_byte.exit.thread43

bb19.i:                                           ; preds = %bb16.i
  store i8 -97, ptr %5, align 1, !alias.scope !20
  br label %_RNvCscgRqy0Y3eGg_6parser13encoding_byte.exit.thread43

bb10.i:                                           ; preds = %bb7.i
  %_11.0.i = add nuw i64 %_9.i, 1
  store i64 %_11.0.i, ptr %6, align 8, !alias.scope !20
  br label %_RNvCscgRqy0Y3eGg_6parser13encoding_byte.exit.thread43

bb37.i:                                           ; preds = %bb6.i
  %_24.0.i = add i32 %_6.i, -1
  store i32 %_24.0.i, ptr %3, align 8, !alias.scope !20
  store i8 -128, ptr %4, align 8, !alias.scope !20
  store i8 -65, ptr %5, align 1, !alias.scope !20
  %25 = icmp eq i32 %_24.0.i, 0
  br i1 %25, label %bb38.i, label %_RNvCscgRqy0Y3eGg_6parser13encoding_byte.exit.thread43

bb38.i:                                           ; preds = %bb37.i
  %_26.i = load i64, ptr %6, align 8, !alias.scope !20, !noundef !18
  %26 = icmp eq i64 %_26.i, -1
  br i1 %26, label %bb8.loopexit33.sink.split, label %bb41.i

bb41.i:                                           ; preds = %bb38.i
  %_28.0.i = add nuw i64 %_26.i, 1
  store i64 %_28.0.i, ptr %6, align 8, !alias.scope !20
  br label %_RNvCscgRqy0Y3eGg_6parser13encoding_byte.exit.thread43

_RNvCscgRqy0Y3eGg_6parser13encoding_byte.exit.thread43: ; preds = %bb13.i, %bb16.i, %bb23.i, %bb24.i, %bb26.i, %bb17.i, %bb19.i, %bb10.i, %bb37.i, %bb41.i
  %_29.0.i = add nuw i64 %_4.i, 1
  store i64 %_29.0.i, ptr %_12, align 8, !alias.scope !20
  %_3.i1 = load i32, ptr %9, align 4, !alias.scope !23, !noundef !18
  switch i32 %_3.i1, label %bb67.i [
    i32 1, label %bb1.i
    i32 2, label %bb14.i8
    i32 4, label %bb27.i
    i32 5, label %bb31.i
    i32 6, label %bb39.i2
    i32 3, label %bb39.i2
    i32 20, label %bb66.i
  ]

bb36.i:                                           ; preds = %bb6.i
  store i32 1, ptr %2, align 4, !alias.scope !20
  %_23.i = load i64, ptr %8, align 8, !alias.scope !20, !noundef !18
  store i64 %_23.i, ptr %7, align 8, !alias.scope !20
  br label %bb16.sink.split

bb1.i:                                            ; preds = %_RNvCscgRqy0Y3eGg_6parser13encoding_byte.exit.thread43
  %_4.i11 = icmp ult i8 %byte, 32
  br i1 %_4.i11, label %bb16.sink.split, label %bb3.i12

bb3.i12:                                          ; preds = %bb1.i
  switch i8 %byte, label %_RNvCscgRqy0Y3eGg_6parser4step.exit [
    i8 34, label %bb4.i14
    i8 92, label %bb11.i13
  ]

bb4.i14:                                          ; preds = %bb3.i12
  store i32 0, ptr %9, align 4, !alias.scope !23
  %27 = load i8, ptr %18, align 1, !range !26, !alias.scope !23, !noundef !18
  %_6.i15 = trunc nuw i8 %27 to i1
  br i1 %_6.i15, label %bb6.i16, label %bb9.i

bb9.i:                                            ; preds = %bb4.i14
  tail call void @llvm.experimental.noalias.scope.decl(metadata !27)
  %_2.i = load i32, ptr %11, align 8, !alias.scope !27, !noundef !18
  %28 = icmp eq i32 %_2.i, 0
  br i1 %28, label %bb1.i28, label %bb3.i22

bb1.i28:                                          ; preds = %bb9.i
  store i8 1, ptr %12, align 4, !alias.scope !27
  br label %_RNvCscgRqy0Y3eGg_6parser4step.exit

bb3.i22:                                          ; preds = %bb9.i
  %_7.0.i = add i32 %_2.i, -1
  %_4.i23 = zext i32 %_7.0.i to i64
  %_8.i24 = icmp ult i32 %_2.i, 65
  br i1 %_8.i24, label %bb4.i26, label %panic1.i25

bb4.i26:                                          ; preds = %bb3.i22
  %c.i = getelementptr inbounds nuw i8, ptr %p, i64 %_4.i23
  %_10.i = load i8, ptr %c.i, align 1, !alias.scope !27, !noundef !18
  %29 = add i8 %_10.i, -1
  %switch.and.i = and i8 %29, -3
  %switch.selectcmp.i = icmp eq i8 %switch.and.i, 0
  %30 = select i1 %switch.selectcmp.i, i8 2, i8 7
  store i8 %30, ptr %c.i, align 1, !alias.scope !27
  br label %_RNvCscgRqy0Y3eGg_6parser4step.exit

panic1.i25:                                       ; preds = %bb3.i22
; call core::panicking::panic_bounds_check
  tail call void @_RNvNtCs9nEiEE0E2Vj_4core9panicking18panic_bounds_check(i64 noundef %_4.i23, i64 noundef 64, ptr noalias nofree noundef readonly align 8 captures(address, read_provenance) dereferenceable(24) @alloc_17c2635886f4fbc2ea36dbf6a4113cf0) #10, !noalias !27
  unreachable

bb6.i16:                                          ; preds = %bb4.i14
  %_9.i17 = load i32, ptr %11, align 8, !alias.scope !23, !noundef !18
  %_10.1.i = icmp eq i32 %_9.i17, 0
  br i1 %_10.1.i, label %panic.i, label %bb7.i18

bb7.i18:                                          ; preds = %bb6.i16
  %_10.0.i = add i32 %_9.i17, -1
  %_7.i = zext i32 %_10.0.i to i64
  %_11.i = icmp ult i32 %_9.i17, 65
  br i1 %_11.i, label %bb8.i19, label %panic1.i

panic.i:                                          ; preds = %bb6.i16
; call core::panicking::panic_const::panic_const_sub_overflow
  tail call void @_RNvNtNtCs9nEiEE0E2Vj_4core9panicking11panic_const24panic_const_sub_overflow(ptr noalias nofree noundef readonly align 8 captures(address, read_provenance) dereferenceable(24) @alloc_e4ed959f92efea1cff8b4b98f2146f02) #10
  unreachable

bb8.i19:                                          ; preds = %bb7.i18
  %31 = getelementptr inbounds nuw i8, ptr %p, i64 %_7.i
  store i8 5, ptr %31, align 1, !alias.scope !23
  br label %_RNvCscgRqy0Y3eGg_6parser4step.exit

panic1.i:                                         ; preds = %bb7.i18
; call core::panicking::panic_bounds_check
  tail call void @_RNvNtCs9nEiEE0E2Vj_4core9panicking18panic_bounds_check(i64 noundef %_7.i, i64 noundef 64, ptr noalias nofree noundef readonly align 8 captures(address, read_provenance) dereferenceable(24) @alloc_38ab136aad52e23038f13eabe203b7df) #10
  unreachable

bb11.i13:                                         ; preds = %bb3.i12
  store i32 2, ptr %9, align 4, !alias.scope !23
  %_13.i = load i64, ptr %17, align 8, !alias.scope !23, !noundef !18
  store i64 %_13.i, ptr %15, align 8, !alias.scope !23
  br label %_RNvCscgRqy0Y3eGg_6parser4step.exit

bb14.i8:                                          ; preds = %_RNvCscgRqy0Y3eGg_6parser13encoding_byte.exit.thread43
  switch i8 %byte, label %bb16.sink.split [
    i8 34, label %bb23.i9
    i8 92, label %bb23.i9
    i8 47, label %bb23.i9
    i8 98, label %bb23.i9
    i8 102, label %bb23.i9
    i8 110, label %bb23.i9
    i8 114, label %bb23.i9
    i8 116, label %bb23.i9
    i8 117, label %bb25.i
  ]

bb23.i9:                                          ; preds = %bb14.i8, %bb14.i8, %bb14.i8, %bb14.i8, %bb14.i8, %bb14.i8, %bb14.i8, %bb14.i8
  store i32 1, ptr %9, align 4, !alias.scope !23
  br label %_RNvCscgRqy0Y3eGg_6parser4step.exit

bb25.i:                                           ; preds = %bb14.i8
  store i32 3, ptr %9, align 4, !alias.scope !23
  store i32 0, ptr %14, align 8, !alias.scope !23
  store i32 0, ptr %13, align 4, !alias.scope !23
  br label %_RNvCscgRqy0Y3eGg_6parser4step.exit

bb27.i:                                           ; preds = %_RNvCscgRqy0Y3eGg_6parser13encoding_byte.exit.thread43
  %32 = icmp eq i8 %byte, 92
  br i1 %32, label %bb30.i, label %bb16.sink.split

bb30.i:                                           ; preds = %bb27.i
  store i32 5, ptr %9, align 4, !alias.scope !23
  br label %_RNvCscgRqy0Y3eGg_6parser4step.exit

bb31.i:                                           ; preds = %_RNvCscgRqy0Y3eGg_6parser13encoding_byte.exit.thread43
  %33 = icmp eq i8 %byte, 117
  br i1 %33, label %bb34.i, label %bb16.sink.split

bb34.i:                                           ; preds = %bb31.i
  store i32 6, ptr %9, align 4, !alias.scope !23
  store i32 0, ptr %14, align 8, !alias.scope !23
  store i32 0, ptr %13, align 4, !alias.scope !23
  br label %_RNvCscgRqy0Y3eGg_6parser4step.exit

bb39.i2:                                          ; preds = %_RNvCscgRqy0Y3eGg_6parser13encoding_byte.exit.thread43, %_RNvCscgRqy0Y3eGg_6parser13encoding_byte.exit.thread43
  %34 = add i8 %byte, -48
  %or.cond.i.i = icmp ult i8 %34, 10
  br i1 %or.cond.i.i, label %bb42.i, label %bb4.i.i

bb4.i.i:                                          ; preds = %bb39.i2
  %35 = add i8 %byte, -65
  %or.cond3.i.i = icmp ult i8 %35, 6
  br i1 %or.cond3.i.i, label %bb6.i.i, label %bb8.i.i

bb8.i.i:                                          ; preds = %bb4.i.i
  %_13.0.i.i = add nsw i8 %byte, -87
  %36 = add i8 %byte, -103
  %or.cond83.i = icmp ult i8 %36, -6
  br i1 %or.cond83.i, label %bb16.sink.split, label %bb42.i

bb6.i.i:                                          ; preds = %bb4.i.i
  %_9.0.i.i = add nsw i8 %byte, -55
  br label %bb42.i

bb42.i:                                           ; preds = %bb39.i2, %bb6.i.i, %bb8.i.i
  %_0.sroa.0.0.i77.in.i = phi i8 [ %_13.0.i.i, %bb8.i.i ], [ %34, %bb39.i2 ], [ %_9.0.i.i, %bb6.i.i ]
  %_25.i = load i32, ptr %13, align 4, !alias.scope !23, !noundef !18
  %_26.1.i = icmp ugt i32 %_25.i, 268435455
  br i1 %_26.1.i, label %panic2.i, label %bb43.i

bb43.i:                                           ; preds = %bb42.i
  %_0.sroa.0.0.i77.i = zext i8 %_0.sroa.0.0.i77.in.i to i32
  %_26.0.i = shl nuw i32 %_25.i, 4
  %_27.0.i = add i32 %_26.0.i, %_0.sroa.0.0.i77.i
  %_27.1.i = icmp ult i32 %_27.0.i, %_26.0.i
  br i1 %_27.1.i, label %panic3.i, label %bb44.i

panic2.i:                                         ; preds = %bb42.i
; call core::panicking::panic_const::panic_const_mul_overflow
  tail call void @_RNvNtNtCs9nEiEE0E2Vj_4core9panicking11panic_const24panic_const_mul_overflow(ptr noalias nofree noundef readonly align 8 captures(address, read_provenance) dereferenceable(24) @alloc_7fcdd0112aa4a922a81991942fa2013b) #10
  unreachable

bb44.i:                                           ; preds = %bb43.i
  store i32 %_27.0.i, ptr %13, align 4, !alias.scope !23
  %37 = load i32, ptr %14, align 8, !alias.scope !23, !noundef !18
  %_28.1.i = icmp eq i32 %37, -1
  br i1 %_28.1.i, label %panic4.i, label %bb45.i3

panic3.i:                                         ; preds = %bb43.i
; call core::panicking::panic_const::panic_const_add_overflow
  tail call void @_RNvNtNtCs9nEiEE0E2Vj_4core9panicking11panic_const24panic_const_add_overflow(ptr noalias nofree noundef readonly align 8 captures(address, read_provenance) dereferenceable(24) @alloc_7fcdd0112aa4a922a81991942fa2013b) #10
  unreachable

bb45.i3:                                          ; preds = %bb44.i
  %_28.0.i4 = add nuw i32 %37, 1
  store i32 %_28.0.i4, ptr %14, align 8, !alias.scope !23
  %38 = icmp eq i32 %_28.0.i4, 4
  br i1 %38, label %bb46.i, label %_RNvCscgRqy0Y3eGg_6parser4step.exit

panic4.i:                                         ; preds = %bb44.i
; call core::panicking::panic_const::panic_const_add_overflow
  tail call void @_RNvNtNtCs9nEiEE0E2Vj_4core9panicking11panic_const24panic_const_add_overflow(ptr noalias nofree noundef readonly align 8 captures(address, read_provenance) dereferenceable(24) @alloc_e67dfff62b8e4ecb323b784eaa923bef) #10
  unreachable

bb46.i:                                           ; preds = %bb45.i3
  %39 = icmp eq i32 %_3.i1, 6
  br i1 %39, label %bb47.i, label %bb53.i

bb47.i:                                           ; preds = %bb46.i
  %40 = add i32 %_27.0.i, -57344
  %or.cond19.i = icmp ult i32 %40, -1024
  br i1 %or.cond19.i, label %bb16.sink.split, label %bb52.i

bb53.i:                                           ; preds = %bb46.i
  %41 = and i32 %_27.0.i, -1024
  switch i32 %41, label %bb63.i [
    i32 55296, label %bb56.i
    i32 56320, label %bb16.sink.split
  ]

bb52.i:                                           ; preds = %bb47.i
  store i32 1, ptr %9, align 4, !alias.scope !23
  br label %_RNvCscgRqy0Y3eGg_6parser4step.exit

bb56.i:                                           ; preds = %bb53.i
  store i32 4, ptr %9, align 4, !alias.scope !23
  %_40.i = load i64, ptr %15, align 8, !alias.scope !23, !noundef !18
  store i64 %_40.i, ptr %16, align 8, !alias.scope !23
  br label %_RNvCscgRqy0Y3eGg_6parser4step.exit

bb63.i:                                           ; preds = %bb53.i
  store i32 1, ptr %9, align 4, !alias.scope !23
  br label %_RNvCscgRqy0Y3eGg_6parser4step.exit

bb66.i:                                           ; preds = %_RNvCscgRqy0Y3eGg_6parser13encoding_byte.exit.thread43
  %_48.i = load i32, ptr %10, align 8, !alias.scope !23, !noundef !18
  %_59.pre.i = load i32, ptr %.phi.trans.insert.i, align 4, !alias.scope !23
  switch i32 %_48.i, label %bb94.i [
    i32 1, label %bb79.thread.i
    i32 2, label %bb80.i
  ]

bb67.i:                                           ; preds = %_RNvCscgRqy0Y3eGg_6parser13encoding_byte.exit.thread43
  %42 = add i32 %_3.i1, -10
  %or.cond22.i = icmp ult i32 %42, 8
  br i1 %or.cond22.i, label %bb109.i, label %bb166.i

bb79.thread.i:                                    ; preds = %bb66.i
  %43 = icmp eq i32 %_59.pre.i, 1
  %spec.select.i = select i1 %43, i8 114, i8 0
  %44 = icmp eq i32 %_59.pre.i, 2
  %expected.sroa.0.1.i = select i1 %44, i8 117, i8 %spec.select.i
  %45 = icmp eq i32 %_59.pre.i, 3
  %spec.select61.i = select i1 %45, i8 101, i8 %expected.sroa.0.1.i
  br label %bb94.i

bb80.i:                                           ; preds = %bb66.i
  %46 = icmp eq i32 %_59.pre.i, 1
  %spec.select56.i = select i1 %46, i8 97, i8 0
  %47 = icmp eq i32 %_59.pre.i, 2
  %expected.sroa.0.4.i = select i1 %47, i8 108, i8 %spec.select56.i
  %48 = icmp eq i32 %_59.pre.i, 3
  %expected.sroa.0.5.i = select i1 %48, i8 115, i8 %expected.sroa.0.4.i
  %49 = icmp eq i32 %_59.pre.i, 4
  %spec.select62.i = select i1 %49, i8 101, i8 %expected.sroa.0.5.i
  br label %bb94.i

bb94.i:                                           ; preds = %bb80.i, %bb79.thread.i, %bb66.i
  %expected.sroa.0.6.i = phi i8 [ %spec.select61.i, %bb79.thread.i ], [ %spec.select62.i, %bb80.i ], [ 0, %bb66.i ]
  %length.sroa.0.0.i = phi i32 [ 4, %bb79.thread.i ], [ 5, %bb80.i ], [ 4, %bb66.i ]
  %50 = icmp eq i32 %_48.i, 3
  %51 = icmp eq i32 %_59.pre.i, 1
  %..i = select i1 %51, i8 117, i8 108
  %expected.sroa.0.7.i = select i1 %50, i8 %..i, i8 %expected.sroa.0.6.i
  %_60.not.i = icmp eq i8 %byte, %expected.sroa.0.7.i
  br i1 %_60.not.i, label %bb102.i, label %bb16.sink.split

bb102.i:                                          ; preds = %bb94.i
  %_62.1.i = icmp eq i32 %_59.pre.i, -1
  br i1 %_62.1.i, label %panic5.i, label %bb103.i

bb103.i:                                          ; preds = %bb102.i
  %_62.0.i = add nuw i32 %_59.pre.i, 1
  store i32 %_62.0.i, ptr %.phi.trans.insert.i, align 4, !alias.scope !23
  %_63.i = icmp eq i32 %_62.0.i, %length.sroa.0.0.i
  br i1 %_63.i, label %bb104.i, label %_RNvCscgRqy0Y3eGg_6parser4step.exit

panic5.i:                                         ; preds = %bb102.i
; call core::panicking::panic_const::panic_const_add_overflow
  tail call void @_RNvNtNtCs9nEiEE0E2Vj_4core9panicking11panic_const24panic_const_add_overflow(ptr noalias nofree noundef readonly align 8 captures(address, read_provenance) dereferenceable(24) @alloc_2d6ba3368b9b590ce6e8441798328433) #10
  unreachable

bb104.i:                                          ; preds = %bb103.i
  store i32 0, ptr %9, align 4, !alias.scope !23
  tail call void @llvm.experimental.noalias.scope.decl(metadata !30)
  %_2.i.i = load i32, ptr %11, align 8, !alias.scope !33, !noundef !18
  %52 = icmp eq i32 %_2.i.i, 0
  br i1 %52, label %bb1.i.i, label %bb3.i.i

bb1.i.i:                                          ; preds = %bb104.i
  store i8 1, ptr %12, align 4, !alias.scope !33
  br label %_RNvCscgRqy0Y3eGg_6parser4step.exit

bb3.i.i:                                          ; preds = %bb104.i
  %_7.0.i.i = add i32 %_2.i.i, -1
  %_4.i.i = zext i32 %_7.0.i.i to i64
  %_8.i.i = icmp ult i32 %_2.i.i, 65
  br i1 %_8.i.i, label %bb4.i63.i, label %panic1.i.i

bb4.i63.i:                                        ; preds = %bb3.i.i
  %c.i.i = getelementptr inbounds nuw i8, ptr %p, i64 %_4.i.i
  %_10.i.i = load i8, ptr %c.i.i, align 1, !alias.scope !33, !noundef !18
  %53 = add i8 %_10.i.i, -1
  %switch.and.i.i = and i8 %53, -3
  %switch.selectcmp.i.i = icmp eq i8 %switch.and.i.i, 0
  %54 = select i1 %switch.selectcmp.i.i, i8 2, i8 7
  store i8 %54, ptr %c.i.i, align 1, !alias.scope !33
  br label %_RNvCscgRqy0Y3eGg_6parser4step.exit

panic1.i.i:                                       ; preds = %bb3.i.i
; call core::panicking::panic_bounds_check
  tail call void @_RNvNtCs9nEiEE0E2Vj_4core9panicking18panic_bounds_check(i64 noundef %_4.i.i, i64 noundef 64, ptr noalias nofree noundef readonly align 8 captures(address, read_provenance) dereferenceable(24) @alloc_17c2635886f4fbc2ea36dbf6a4113cf0) #10, !noalias !30
  unreachable

bb166.i:                                          ; preds = %bb164.i, %bb67.i
  switch i8 %byte, label %bb168.i [
    i8 32, label %_RNvCscgRqy0Y3eGg_6parser4step.exit
    i8 9, label %_RNvCscgRqy0Y3eGg_6parser4step.exit
    i8 10, label %_RNvCscgRqy0Y3eGg_6parser4step.exit
    i8 13, label %_RNvCscgRqy0Y3eGg_6parser4step.exit
  ]

bb109.i:                                          ; preds = %bb67.i
  %55 = add i8 %byte, -48
  %or.cond.i21 = icmp ult i8 %55, 10
  br i1 %or.cond.i21, label %bb110.i, label %bb128.i

bb128.i:                                          ; preds = %bb109.i
  %56 = add nsw i32 %_3.i1, -11
  %or.cond24.i = icmp ult i32 %56, 2
  %57 = icmp eq i8 %byte, 46
  %or.cond25.i = and i1 %57, %or.cond24.i
  br i1 %or.cond25.i, label %bb134.i, label %bb135.i

bb110.i:                                          ; preds = %bb109.i
  switch i32 %_3.i1, label %bb121.i [
    i32 11, label %bb16.sink.split
    i32 10, label %bb118.thread.i
    i32 13, label %bb121.thread.i
  ]

bb134.i:                                          ; preds = %bb128.i
  store i32 13, ptr %9, align 4, !alias.scope !23
  br label %_RNvCscgRqy0Y3eGg_6parser4step.exit

bb135.i:                                          ; preds = %bb128.i
  switch i32 %_3.i1, label %bb158.i [
    i32 14, label %bb142.i
    i32 12, label %bb142.i
    i32 11, label %bb142.i
    i32 15, label %bb146.i
    i32 16, label %bb16.sink.split
    i32 13, label %bb16.sink.split
    i32 10, label %bb16.sink.split
  ]

bb142.i:                                          ; preds = %bb135.i, %bb135.i, %bb135.i
  switch i8 %byte, label %bb150.i [
    i8 101, label %bb144.i
    i8 69, label %bb144.i
  ]

bb144.i:                                          ; preds = %bb142.i, %bb142.i
  store i32 15, ptr %9, align 4, !alias.scope !23
  br label %_RNvCscgRqy0Y3eGg_6parser4step.exit

bb146.i:                                          ; preds = %bb135.i
  switch i8 %byte, label %bb16.sink.split [
    i8 43, label %bb149.i
    i8 45, label %bb149.i
  ]

bb149.i:                                          ; preds = %bb146.i, %bb146.i
  store i32 16, ptr %9, align 4, !alias.scope !23
  br label %_RNvCscgRqy0Y3eGg_6parser4step.exit

bb150.i:                                          ; preds = %bb142.i
  %cond.i = icmp eq i32 %_3.i1, 13
  br i1 %cond.i, label %bb16.sink.split, label %bb158.i

bb158.i:                                          ; preds = %bb150.i, %bb135.i
  switch i8 %byte, label %bb16.sink.split [
    i8 32, label %bb164.i
    i8 9, label %bb164.i
    i8 10, label %bb164.i
    i8 13, label %bb164.i
    i8 44, label %bb164.i
    i8 93, label %bb164.i
    i8 125, label %bb164.i
  ]

bb164.i:                                          ; preds = %bb158.i, %bb158.i, %bb158.i, %bb158.i, %bb158.i, %bb158.i, %bb158.i
  store i32 0, ptr %9, align 4, !alias.scope !23
; call parser::done
  tail call fastcc void @_RNvCscgRqy0Y3eGg_6parser4done(ptr noalias nofree noundef nonnull align 8 dereferenceable(176) %p) #11
  br label %bb166.i

bb168.i:                                          ; preds = %bb166.i
  %_95.i = load i32, ptr %11, align 8, !alias.scope !23, !noundef !18
  %_94.not.i = icmp eq i32 %_95.i, 0
  br i1 %_94.not.i, label %bb170.i, label %bb171.i

bb170.i:                                          ; preds = %bb168.i
  %58 = icmp eq i8 %byte, 93
  br i1 %58, label %bb210.i, label %bb180.i

bb180.i:                                          ; preds = %bb172.i, %bb170.i
  %context.sroa.0.0.i = phi i8 [ 0, %bb170.i ], [ %61, %bb172.i ]
  %59 = icmp eq i8 %byte, 125
  br i1 %59, label %bb181.i, label %bb188.i

bb171.i:                                          ; preds = %bb168.i
  %_99.0.i = add i32 %_95.i, -1
  %_96.i = zext i32 %_99.0.i to i64
  %_100.i = icmp ult i32 %_95.i, 65
  br i1 %_100.i, label %bb172.i, label %panic7.i

bb172.i:                                          ; preds = %bb171.i
  %60 = getelementptr inbounds nuw i8, ptr %p, i64 %_96.i
  %61 = load i8, ptr %60, align 1, !alias.scope !23, !noundef !18
  %62 = icmp eq i8 %byte, 93
  br i1 %62, label %bb173.i, label %bb180.i

panic7.i:                                         ; preds = %bb171.i
; call core::panicking::panic_bounds_check
  tail call void @_RNvNtCs9nEiEE0E2Vj_4core9panicking18panic_bounds_check(i64 noundef %_96.i, i64 noundef 64, ptr noalias nofree noundef readonly align 8 captures(address, read_provenance) dereferenceable(24) @alloc_ca89a41573afe1edc3f237491af5f4cb) #10
  unreachable

bb173.i:                                          ; preds = %bb172.i
  %.off.i = add i8 %61, -1
  %switch.i = icmp ult i8 %.off.i, 2
  br i1 %switch.i, label %bb178.i, label %bb188.i

bb181.i:                                          ; preds = %bb180.i
  switch i8 %context.sroa.0.0.i, label %bb188.i [
    i8 7, label %bb185.i
    i8 4, label %bb185.i
  ]

bb188.i:                                          ; preds = %bb181.i, %bb173.i, %bb180.i
  %context.sroa.0.066.i = phi i8 [ %context.sroa.0.0.i, %bb180.i ], [ %context.sroa.0.0.i, %bb181.i ], [ %61, %bb173.i ]
  %63 = icmp eq i8 %context.sroa.0.066.i, 2
  switch i8 %context.sroa.0.066.i, label %bb210.i [
    i8 7, label %bb193.i
    i8 2, label %bb193.i
    i8 5, label %bb201.i
    i8 8, label %bb211.i
    i8 4, label %bb211.i
  ]

bb185.i:                                          ; preds = %bb181.i, %bb181.i
  br i1 %_94.not.i, label %panic8.i, label %bb186.i

bb186.i:                                          ; preds = %bb185.i
  %_108.0.i = add nsw i32 %_95.i, -1
  store i32 %_108.0.i, ptr %11, align 8, !alias.scope !23
  br label %_RNvCscgRqy0Y3eGg_6parser4step.exit

panic8.i:                                         ; preds = %bb185.i
; call core::panicking::panic_const::panic_const_sub_overflow
  tail call void @_RNvNtNtCs9nEiEE0E2Vj_4core9panicking11panic_const24panic_const_sub_overflow(ptr noalias nofree noundef readonly align 8 captures(address, read_provenance) dereferenceable(24) @alloc_232157ae9decd89c9f2076cdf71110bc) #10
  unreachable

bb193.i:                                          ; preds = %bb188.i, %bb188.i
  %64 = icmp eq i8 %byte, 44
  br i1 %64, label %bb195.i, label %bb16.sink.split

bb195.i:                                          ; preds = %bb193.i
  br i1 %_94.not.i, label %panic9.i, label %bb200.i

panic9.i:                                         ; preds = %bb195.i
; call core::panicking::panic_const::panic_const_sub_overflow
  tail call void @_RNvNtNtCs9nEiEE0E2Vj_4core9panicking11panic_const24panic_const_sub_overflow(ptr noalias nofree noundef readonly align 8 captures(address, read_provenance) dereferenceable(24) @alloc_04fe8135d2319897c873529430c986db) #10
  unreachable

bb200.i:                                          ; preds = %bb195.i
  %.57.i = select i1 %63, i8 3, i8 8
  %65 = zext nneg i32 %_95.i to i64
  %66 = getelementptr i8, ptr %p, i64 %65
  %67 = getelementptr i8, ptr %66, i64 -1
  store i8 %.57.i, ptr %67, align 1, !alias.scope !23
  br label %_RNvCscgRqy0Y3eGg_6parser4step.exit

bb201.i:                                          ; preds = %bb188.i
  %68 = icmp eq i8 %byte, 58
  br i1 %68, label %bb204.i, label %bb16.sink.split

bb204.i:                                          ; preds = %bb201.i
  br i1 %_94.not.i, label %panic11.i, label %bb206.i

panic11.i:                                        ; preds = %bb204.i
; call core::panicking::panic_const::panic_const_sub_overflow
  tail call void @_RNvNtNtCs9nEiEE0E2Vj_4core9panicking11panic_const24panic_const_sub_overflow(ptr noalias nofree noundef readonly align 8 captures(address, read_provenance) dereferenceable(24) @alloc_1fb0c37e44d2c7e7dd89cb8d4cf14241) #10
  unreachable

bb206.i:                                          ; preds = %bb204.i
  %69 = zext nneg i32 %_95.i to i64
  %70 = getelementptr i8, ptr %p, i64 %69
  %71 = getelementptr i8, ptr %70, i64 -1
  store i8 6, ptr %71, align 1, !alias.scope !23
  br label %_RNvCscgRqy0Y3eGg_6parser4step.exit

bb211.i:                                          ; preds = %bb188.i, %bb188.i
  %72 = icmp eq i8 %byte, 34
  br i1 %72, label %bb213.i, label %bb16.sink.split

bb210.i:                                          ; preds = %bb188.i, %bb170.i
  %73 = load i8, ptr %12, align 4, !range !26, !alias.scope !23
  %_128.i = trunc nuw i8 %73 to i1
  %or.cond41.i = select i1 %_94.not.i, i1 %_128.i, i1 false
  br i1 %or.cond41.i, label %bb16.sink.split, label %bb217.i

bb213.i:                                          ; preds = %bb211.i
  store i8 1, ptr %18, align 1, !alias.scope !23
  store i32 1, ptr %9, align 4, !alias.scope !23
  br label %_RNvCscgRqy0Y3eGg_6parser4step.exit

bb217.i:                                          ; preds = %bb210.i
  switch i8 %byte, label %bb227.i [
    i8 91, label %bb268.i
    i8 123, label %bb271.i
    i8 34, label %bb224.i
    i8 45, label %bb226.i
  ]

bb268.i:                                          ; preds = %bb217.i
  %74 = icmp eq i32 %_95.i, 64
  br i1 %74, label %bb16.sink.split, label %bb221.i

bb221.i:                                          ; preds = %bb271.i, %bb268.i
  %_134.sroa.0.0.i = phi i8 [ 4, %bb271.i ], [ 1, %bb268.i ]
; call parser::done
  tail call fastcc void @_RNvCscgRqy0Y3eGg_6parser4done(ptr noalias nofree noundef nonnull align 8 dereferenceable(176) %p) #11
  %_136.i = load i32, ptr %11, align 8, !alias.scope !23, !noundef !18
  %_135.i = zext i32 %_136.i to i64
  %_137.i = icmp ult i32 %_136.i, 64
  br i1 %_137.i, label %bb222.i, label %panic13.i

bb271.i:                                          ; preds = %bb217.i
  %75 = icmp eq i32 %_95.i, 64
  br i1 %75, label %bb16.sink.split, label %bb221.i

bb222.i:                                          ; preds = %bb221.i
  %76 = getelementptr inbounds nuw i8, ptr %p, i64 %_135.i
  store i8 %_134.sroa.0.0.i, ptr %76, align 1, !alias.scope !23
  %77 = load i32, ptr %11, align 8, !alias.scope !23, !noundef !18
  %_138.1.i = icmp eq i32 %77, -1
  br i1 %_138.1.i, label %panic14.i, label %bb223.i

panic13.i:                                        ; preds = %bb221.i
; call core::panicking::panic_bounds_check
  tail call void @_RNvNtCs9nEiEE0E2Vj_4core9panicking18panic_bounds_check(i64 noundef %_135.i, i64 noundef 64, ptr noalias nofree noundef readonly align 8 captures(address, read_provenance) dereferenceable(24) @alloc_21a6ae3fdeb0c022136d547ac7b9c594) #10
  unreachable

bb223.i:                                          ; preds = %bb222.i
  %_138.0.i = add nuw i32 %77, 1
  store i32 %_138.0.i, ptr %11, align 8, !alias.scope !23
  br label %_RNvCscgRqy0Y3eGg_6parser4step.exit

panic14.i:                                        ; preds = %bb222.i
; call core::panicking::panic_const::panic_const_add_overflow
  tail call void @_RNvNtNtCs9nEiEE0E2Vj_4core9panicking11panic_const24panic_const_add_overflow(ptr noalias nofree noundef readonly align 8 captures(address, read_provenance) dereferenceable(24) @alloc_e0474d9a635040eab39bac01d02d2ec4) #10
  unreachable

bb224.i:                                          ; preds = %bb217.i
  store i8 0, ptr %18, align 1, !alias.scope !23
  store i32 1, ptr %9, align 4, !alias.scope !23
  br label %_RNvCscgRqy0Y3eGg_6parser4step.exit

bb226.i:                                          ; preds = %bb217.i
  store i32 10, ptr %9, align 4, !alias.scope !23
  br label %_RNvCscgRqy0Y3eGg_6parser4step.exit

bb227.i:                                          ; preds = %bb217.i
  %78 = add i8 %byte, -48
  %or.cond16.i = icmp ult i8 %78, 10
  br i1 %or.cond16.i, label %bb228.i, label %bb232.i

bb232.i:                                          ; preds = %bb227.i
  switch i8 %byte, label %bb16.sink.split [
    i8 116, label %bb274.i
    i8 102, label %bb275.i
    i8 110, label %bb275.i
  ]

bb228.i:                                          ; preds = %bb227.i
  %79 = icmp eq i8 %byte, 48
  %.58.i = select i1 %79, i32 11, i32 12
  store i32 %.58.i, ptr %9, align 4, !alias.scope !23
  br label %_RNvCscgRqy0Y3eGg_6parser4step.exit

bb274.i:                                          ; preds = %bb232.i
  store i32 20, ptr %9, align 4, !alias.scope !23
  store i32 1, ptr %.phi.trans.insert.i, align 4, !alias.scope !23
  br label %bb239.i

bb239.i:                                          ; preds = %bb275.i, %bb274.i
  %_141.sroa.0.0.i = phi i32 [ 1, %bb274.i ], [ %.59.i, %bb275.i ]
  store i32 %_141.sroa.0.0.i, ptr %10, align 8, !alias.scope !23
  br label %_RNvCscgRqy0Y3eGg_6parser4step.exit

bb275.i:                                          ; preds = %bb232.i, %bb232.i
  store i32 20, ptr %9, align 4, !alias.scope !23
  store i32 1, ptr %.phi.trans.insert.i, align 4, !alias.scope !23
  %80 = icmp eq i8 %byte, 102
  %.59.i = select i1 %80, i32 2, i32 3
  br label %bb239.i

bb178.i:                                          ; preds = %bb173.i
  store i32 %_99.0.i, ptr %11, align 8, !alias.scope !23
  br label %_RNvCscgRqy0Y3eGg_6parser4step.exit

bb118.thread.i:                                   ; preds = %bb110.i
  %81 = icmp eq i8 %byte, 48
  %.60.i = select i1 %81, i32 11, i32 12
  store i32 %.60.i, ptr %9, align 4, !alias.scope !23
  br label %bb121.i

bb121.thread.i:                                   ; preds = %bb110.i
  store i32 14, ptr %9, align 4, !alias.scope !23
  br label %_RNvCscgRqy0Y3eGg_6parser4step.exit

bb121.i:                                          ; preds = %bb118.thread.i, %bb110.i
  %_76.i = phi i32 [ %.60.i, %bb118.thread.i ], [ %_3.i1, %bb110.i ]
  %82 = add nsw i32 %_76.i, -15
  %or.cond43.i = icmp ult i32 %82, 2
  br i1 %or.cond43.i, label %bb125.i, label %_RNvCscgRqy0Y3eGg_6parser4step.exit

bb125.i:                                          ; preds = %bb121.i
  store i32 17, ptr %9, align 4, !alias.scope !23
  br label %_RNvCscgRqy0Y3eGg_6parser4step.exit

_RNvCscgRqy0Y3eGg_6parser4step.exit:              ; preds = %bb4.i26, %bb1.i28, %bb3.i12, %bb8.i19, %bb11.i13, %bb23.i9, %bb25.i, %bb30.i, %bb34.i, %bb45.i3, %bb52.i, %bb56.i, %bb63.i, %bb103.i, %bb1.i.i, %bb4.i63.i, %bb166.i, %bb166.i, %bb166.i, %bb166.i, %bb134.i, %bb144.i, %bb149.i, %bb186.i, %bb200.i, %bb206.i, %bb213.i, %bb223.i, %bb224.i, %bb226.i, %bb228.i, %bb239.i, %bb178.i, %bb121.thread.i, %bb121.i, %bb125.i
  %_18.pr = load i32, ptr %0, align 8
  %83 = icmp eq i32 %_18.pr, 0
  br i1 %83, label %bb12, label %bb16

bb12:                                             ; preds = %_RNvCscgRqy0Y3eGg_6parser4step.exit
  %84 = load i64, ptr %17, align 8, !noundef !18
  %_19.1 = icmp eq i64 %84, -1
  br i1 %_19.1, label %panic, label %bb13

bb13:                                             ; preds = %bb12
  %_19.0 = add nuw i64 %84, 1
  store i64 %_19.0, ptr %17, align 8
  %_32 = icmp eq ptr %_38, %_25
  br i1 %_32, label %bb16, label %bb18

panic:                                            ; preds = %bb12
; call core::panicking::panic_const::panic_const_add_overflow
  tail call void @_RNvNtNtCs9nEiEE0E2Vj_4core9panicking11panic_const24panic_const_add_overflow(ptr noalias nofree noundef readonly align 8 captures(address, read_provenance) dereferenceable(24) @alloc_67efdafa9b0dc47c916e8f72fff3e807) #10
  unreachable

bb8.loopexit33.sink.split:                        ; preds = %bb38.i, %bb7.i, %bb2.i
  %_4.i.lcssa85.sink = phi i64 [ %_4.i, %bb7.i ], [ -1, %bb2.i ], [ %_4.i, %bb38.i ]
  store i32 2, ptr %2, align 4, !alias.scope !20
  store i64 %_4.i.lcssa85.sink, ptr %7, align 8, !alias.scope !20
  br label %bb16.sink.split

bb16.sink.split.loopexit:                         ; preds = %bb18
  br label %bb16.sink.split

bb16.sink.split:                                  ; preds = %bb110.i, %bb232.i, %bb268.i, %bb271.i, %bb210.i, %bb211.i, %bb201.i, %bb193.i, %bb158.i, %bb135.i, %bb135.i, %bb135.i, %bb146.i, %bb150.i, %bb94.i, %bb53.i, %bb47.i, %bb8.i.i, %bb31.i, %bb27.i, %bb14.i8, %bb1.i, %bb8.loopexit33.sink.split, %bb18, %bb16.sink.split.loopexit, %bb36.i, %bb28.i
  %.sink = phi i32 [ 5, %bb36.i ], [ 8, %bb8.loopexit33.sink.split ], [ 5, %bb28.i ], [ 8, %bb18 ], [ 7, %bb271.i ], [ 2, %bb135.i ], [ 2, %bb135.i ], [ 2, %bb146.i ], [ 2, %bb150.i ], [ 2, %bb110.i ], [ 1, %bb1.i ], [ 3, %bb14.i8 ], [ 4, %bb27.i ], [ 4, %bb31.i ], [ 3, %bb8.i.i ], [ 4, %bb47.i ], [ 4, %bb53.i ], [ 1, %bb94.i ], [ 2, %bb135.i ], [ 2, %bb158.i ], [ 1, %bb193.i ], [ 1, %bb201.i ], [ 1, %bb211.i ], [ 1, %bb210.i ], [ 7, %bb268.i ], [ 1, %bb232.i ], [ 5, %bb16.sink.split.loopexit ]
  %_72.i.sink.in = phi ptr [ %7, %bb36.i ], [ %7, %bb8.loopexit33.sink.split ], [ %7, %bb28.i ], [ %7, %bb18 ], [ %17, %bb271.i ], [ %17, %bb135.i ], [ %17, %bb135.i ], [ %17, %bb146.i ], [ %17, %bb150.i ], [ %17, %bb110.i ], [ %17, %bb1.i ], [ %17, %bb14.i8 ], [ %16, %bb27.i ], [ %16, %bb31.i ], [ %17, %bb8.i.i ], [ %16, %bb47.i ], [ %15, %bb53.i ], [ %17, %bb94.i ], [ %17, %bb135.i ], [ %17, %bb158.i ], [ %17, %bb193.i ], [ %17, %bb201.i ], [ %17, %bb211.i ], [ %17, %bb210.i ], [ %17, %bb268.i ], [ %17, %bb232.i ], [ %7, %bb16.sink.split.loopexit ]
  %_72.i.sink = load i64, ptr %_72.i.sink.in, align 8, !noundef !18
  store i32 %.sink, ptr %0, align 8
  %85 = getelementptr inbounds nuw i8, ptr %p, i64 136
  store i64 %_72.i.sink, ptr %85, align 8
  br label %bb16

bb16:                                             ; preds = %bb13, %_RNvCscgRqy0Y3eGg_6parser4step.exit, %bb16.sink.split, %bb2, %start
  ret void
}

; Function Attrs: mustprogress nofree norecurse nosync nounwind willreturn memory(argmem: read)
define noundef i32 @stream_pending(ptr nofree noundef readonly captures(none) %p) unnamed_addr #1 !guid !34 {
start:
  %0 = getelementptr inbounds nuw i8, ptr %p, i64 168
  %_0 = load i32, ptr %0, align 8, !noundef !18
  ret i32 %_0
}

; Function Attrs: mustprogress nofree norecurse nosync nounwind willreturn memory(none)
define noundef i64 @stream_size() unnamed_addr #2 !guid !35 {
start:
  ret i64 176
}

; Function Attrs: mustprogress nofree norecurse nosync nounwind willreturn memory(argmem: write)
define void @stream_start(ptr nofree noundef writeonly captures(none) initializes((0, 106), (112, 174)) %p) unnamed_addr #3 !guid !36 {
start:
  %_3.sroa.0.sroa.10.0.p.sroa_idx = getelementptr inbounds nuw i8, ptr %p, i64 104
  tail call void @llvm.memset.p0.i64(ptr noundef nonnull align 8 dereferenceable(104) %p, i8 0, i64 104, i1 false)
  store i8 -128, ptr %_3.sroa.0.sroa.10.0.p.sroa_idx, align 8
  %_3.sroa.0.sroa.11.0.p.sroa_idx = getelementptr inbounds nuw i8, ptr %p, i64 105
  store i8 -65, ptr %_3.sroa.0.sroa.11.0.p.sroa_idx, align 1
  %_3.sroa.5.0.p.sroa_idx = getelementptr inbounds nuw i8, ptr %p, i64 112
  tail call void @llvm.memset.p0.i64(ptr noundef nonnull align 8 dereferenceable(62) %_3.sroa.5.0.p.sroa_idx, i8 0, i64 62, i1 false)
  ret void
}

; Function Attrs: nounwind
define noundef i32 @stream_status(ptr nofree noundef readonly captures(none) %p) unnamed_addr #0 !guid !37 {
start:
  %_3 = alloca [176 x i8], align 8
  call void @llvm.lifetime.start.p0(ptr nonnull %_3)
  call void @llvm.memcpy.p0.p0.i64(ptr noundef nonnull align 8 dereferenceable(176) %_3, ptr noundef nonnull align 8 dereferenceable(176) %p, i64 176, i1 false)
  tail call void @llvm.experimental.noalias.scope.decl(metadata !38)
  tail call void @llvm.experimental.noalias.scope.decl(metadata !41)
  %0 = getelementptr inbounds nuw i8, ptr %_3, i64 168
  %_2.i = load i32, ptr %0, align 8, !alias.scope !41, !noalias !38, !noundef !18
  %1 = icmp eq i32 %_2.i, 0
  br i1 %1, label %bb2.i, label %_RNvCscgRqy0Y3eGg_6parser6finish.exit

bb2.i:                                            ; preds = %start
  %2 = getelementptr inbounds nuw i8, ptr %_3, i64 100
  %_3.i = load i32, ptr %2, align 4, !alias.scope !41, !noalias !38, !noundef !18
  %3 = icmp eq i32 %_3.i, 0
  %4 = getelementptr inbounds nuw i8, ptr %_3, i64 96
  %_4.i = load i32, ptr %4, align 8, !alias.scope !41, !noalias !38
  %5 = icmp eq i32 %_4.i, 0
  %or.cond.i = select i1 %3, i1 %5, i1 false
  br i1 %or.cond.i, label %bb6.i, label %_RNvCscgRqy0Y3eGg_6parser6finish.exit

bb6.i:                                            ; preds = %bb2.i
  %6 = getelementptr inbounds nuw i8, ptr %_3, i64 148
  %_7.i = load i32, ptr %6, align 4, !alias.scope !41, !noalias !38, !noundef !18
  switch i32 %_7.i, label %bb21.i [
    i32 17, label %bb19.i
    i32 14, label %bb19.i
    i32 12, label %bb19.i
    i32 11, label %bb19.i
  ]

bb19.i:                                           ; preds = %bb6.i, %bb6.i, %bb6.i, %bb6.i
  store i32 0, ptr %6, align 4, !alias.scope !41, !noalias !38
  tail call void @llvm.experimental.noalias.scope.decl(metadata !43)
  %7 = getelementptr inbounds nuw i8, ptr %_3, i64 144
  %_2.i.i = load i32, ptr %7, align 8, !alias.scope !46, !noalias !38, !noundef !18
  %8 = icmp eq i32 %_2.i.i, 0
  br i1 %8, label %bb28.i._RNvCscgRqy0Y3eGg_6parser6finish.exit_crit_edge, label %bb3.i.i

bb3.i.i:                                          ; preds = %bb19.i
  %_7.0.i.i = add i32 %_2.i.i, -1
  %_4.i.i = zext i32 %_7.0.i.i to i64
  %_8.i.i = icmp ult i32 %_2.i.i, 65
  br i1 %_8.i.i, label %bb4.i.i, label %panic1.i.i

bb4.i.i:                                          ; preds = %bb3.i.i
  %c.i.i = getelementptr inbounds nuw i8, ptr %_3, i64 %_4.i.i
  %_10.i.i = load i8, ptr %c.i.i, align 1, !alias.scope !46, !noalias !38, !noundef !18
  %9 = add i8 %_10.i.i, -1
  %switch.and.i.i = and i8 %9, -3
  %switch.selectcmp.i.i = icmp eq i8 %switch.and.i.i, 0
  %10 = select i1 %switch.selectcmp.i.i, i8 2, i8 7
  store i8 %10, ptr %c.i.i, align 1, !alias.scope !46, !noalias !38
  %_13.pre.i = load i32, ptr %6, align 4, !alias.scope !41, !noalias !38
  br label %bb21.i

panic1.i.i:                                       ; preds = %bb3.i.i
; call core::panicking::panic_bounds_check
  tail call void @_RNvNtCs9nEiEE0E2Vj_4core9panicking18panic_bounds_check(i64 noundef %_4.i.i, i64 noundef 64, ptr noalias nofree noundef readonly align 8 captures(address, read_provenance) dereferenceable(24) @alloc_17c2635886f4fbc2ea36dbf6a4113cf0) #10, !noalias !47
  unreachable

bb21.i:                                           ; preds = %bb4.i.i, %bb6.i
  %_13.i = phi i32 [ %_13.pre.i, %bb4.i.i ], [ %_7.i, %bb6.i ]
  %11 = add i32 %_13.i, -4
  %or.cond14.i = icmp ult i32 %11, 3
  br i1 %or.cond14.i, label %_RNvCscgRqy0Y3eGg_6parser6finish.exit, label %bb28.i

bb28.i:                                           ; preds = %bb21.i
  %.phi.trans.insert = getelementptr inbounds nuw i8, ptr %_3, i64 144
  %_18.i.pre = load i32, ptr %.phi.trans.insert, align 8, !alias.scope !41, !noalias !38
  %.phi.trans.insert2 = getelementptr inbounds nuw i8, ptr %_3, i64 172
  %.pre = load i8, ptr %.phi.trans.insert2, align 4, !range !26, !alias.scope !41, !noalias !38
  %extract.t = trunc nuw i8 %.pre to i1
  %12 = icmp eq i32 %_13.i, 0
  %13 = icmp eq i32 %_18.i.pre, 0
  %14 = select i1 %12, i1 %13, i1 false
  %15 = select i1 %14, i1 %extract.t, i1 false
  br i1 %15, label %bb28.i._RNvCscgRqy0Y3eGg_6parser6finish.exit_crit_edge, label %_RNvCscgRqy0Y3eGg_6parser6finish.exit

bb28.i._RNvCscgRqy0Y3eGg_6parser6finish.exit_crit_edge: ; preds = %bb19.i, %bb28.i
  %_2.sroa.3.0.copyload.pre = load i32, ptr %0, align 8, !alias.scope !48
  br label %_RNvCscgRqy0Y3eGg_6parser6finish.exit

_RNvCscgRqy0Y3eGg_6parser6finish.exit:            ; preds = %bb2.i, %bb21.i, %bb28.i, %bb28.i._RNvCscgRqy0Y3eGg_6parser6finish.exit_crit_edge, %start
  %_2.sroa.3.0.copyload = phi i32 [ %_2.sroa.3.0.copyload.pre, %bb28.i._RNvCscgRqy0Y3eGg_6parser6finish.exit_crit_edge ], [ %_2.i, %start ], [ 6, %bb28.i ], [ 4, %bb21.i ], [ 5, %bb2.i ]
  call void @llvm.lifetime.end.p0(ptr nonnull %_3)
  ret i32 %_2.sroa.3.0.copyload
}

; Function Attrs: nounwind
define noundef i64 @stream_value(ptr nofree noundef readonly captures(none) %p) unnamed_addr #0 !guid !49 {
start:
  %_3 = alloca [176 x i8], align 8
  call void @llvm.lifetime.start.p0(ptr nonnull %_3)
  call void @llvm.memcpy.p0.p0.i64(ptr noundef nonnull align 8 dereferenceable(176) %_3, ptr noundef nonnull align 8 dereferenceable(176) %p, i64 176, i1 false)
  tail call void @llvm.experimental.noalias.scope.decl(metadata !50)
  tail call void @llvm.experimental.noalias.scope.decl(metadata !53)
  %0 = getelementptr inbounds nuw i8, ptr %_3, i64 168
  %_2.i = load i32, ptr %0, align 8, !alias.scope !53, !noalias !50, !noundef !18
  %1 = icmp eq i32 %_2.i, 0
  br i1 %1, label %bb2.i, label %_RNvCscgRqy0Y3eGg_6parser6finish.exit.thread

bb2.i:                                            ; preds = %start
  %2 = getelementptr inbounds nuw i8, ptr %_3, i64 100
  %_3.i = load i32, ptr %2, align 4, !alias.scope !53, !noalias !50, !noundef !18
  %3 = icmp eq i32 %_3.i, 0
  %4 = getelementptr inbounds nuw i8, ptr %_3, i64 96
  %_4.i = load i32, ptr %4, align 8, !alias.scope !53, !noalias !50
  %5 = icmp eq i32 %_4.i, 0
  %or.cond.i = select i1 %3, i1 %5, i1 false
  br i1 %or.cond.i, label %bb6.i, label %bb7.i

bb6.i:                                            ; preds = %bb2.i
  %6 = getelementptr inbounds nuw i8, ptr %_3, i64 148
  %_7.i = load i32, ptr %6, align 4, !alias.scope !53, !noalias !50, !noundef !18
  switch i32 %_7.i, label %bb21.i [
    i32 17, label %bb19.i
    i32 14, label %bb19.i
    i32 12, label %bb19.i
    i32 11, label %bb19.i
  ]

bb19.i:                                           ; preds = %bb6.i, %bb6.i, %bb6.i, %bb6.i
  store i32 0, ptr %6, align 4, !alias.scope !53, !noalias !50
  tail call void @llvm.experimental.noalias.scope.decl(metadata !55)
  %7 = getelementptr inbounds nuw i8, ptr %_3, i64 144
  %_2.i.i = load i32, ptr %7, align 8, !alias.scope !58, !noalias !50, !noundef !18
  %8 = icmp eq i32 %_2.i.i, 0
  br i1 %8, label %_RNvCscgRqy0Y3eGg_6parser6finish.exit, label %bb3.i.i

bb3.i.i:                                          ; preds = %bb19.i
  %_7.0.i.i = add i32 %_2.i.i, -1
  %_4.i.i = zext i32 %_7.0.i.i to i64
  %_8.i.i = icmp ult i32 %_2.i.i, 65
  br i1 %_8.i.i, label %bb4.i.i, label %panic1.i.i

bb4.i.i:                                          ; preds = %bb3.i.i
  %c.i.i = getelementptr inbounds nuw i8, ptr %_3, i64 %_4.i.i
  %_10.i.i = load i8, ptr %c.i.i, align 1, !alias.scope !58, !noalias !50, !noundef !18
  %9 = add i8 %_10.i.i, -1
  %switch.and.i.i = and i8 %9, -3
  %switch.selectcmp.i.i = icmp eq i8 %switch.and.i.i, 0
  %10 = select i1 %switch.selectcmp.i.i, i8 2, i8 7
  store i8 %10, ptr %c.i.i, align 1, !alias.scope !58, !noalias !50
  %_13.pre.i = load i32, ptr %6, align 4, !alias.scope !53, !noalias !50
  br label %bb21.i

panic1.i.i:                                       ; preds = %bb3.i.i
; call core::panicking::panic_bounds_check
  tail call void @_RNvNtCs9nEiEE0E2Vj_4core9panicking18panic_bounds_check(i64 noundef %_4.i.i, i64 noundef 64, ptr noalias nofree noundef readonly align 8 captures(address, read_provenance) dereferenceable(24) @alloc_17c2635886f4fbc2ea36dbf6a4113cf0) #10, !noalias !59
  unreachable

bb21.i:                                           ; preds = %bb4.i.i, %bb6.i
  %_13.i = phi i32 [ %_13.pre.i, %bb4.i.i ], [ %_7.i, %bb6.i ]
  %11 = add i32 %_13.i, -4
  %or.cond14.i = icmp ult i32 %11, 3
  br i1 %or.cond14.i, label %bb35.sink.split.i, label %bb28.i

bb28.i:                                           ; preds = %bb21.i
  %.phi.trans.insert = getelementptr inbounds nuw i8, ptr %_3, i64 144
  %_18.i.pre = load i32, ptr %.phi.trans.insert, align 8, !alias.scope !53, !noalias !50
  %.phi.trans.insert4 = getelementptr inbounds nuw i8, ptr %_3, i64 172
  %.pre = load i8, ptr %.phi.trans.insert4, align 4, !range !26, !alias.scope !53, !noalias !50
  %extract.t = trunc nuw i8 %.pre to i1
  %12 = icmp eq i32 %_13.i, 0
  %13 = icmp eq i32 %_18.i.pre, 0
  %14 = select i1 %12, i1 %13, i1 false
  %15 = select i1 %14, i1 %extract.t, i1 false
  br i1 %15, label %_RNvCscgRqy0Y3eGg_6parser6finish.exit, label %bb35.sink.split.i

bb35.sink.split.i:                                ; preds = %bb7.i, %bb28.i, %bb21.i
  %.sink24.i = phi i64 [ 112, %bb28.i ], [ %at.sroa.0.0.in.v.i, %bb7.i ], [ 128, %bb21.i ]
  %16 = getelementptr inbounds nuw i8, ptr %_3, i64 %.sink24.i
  %at2.i = load i64, ptr %16, align 8, !alias.scope !53, !noalias !50, !noundef !18
  %17 = getelementptr inbounds nuw i8, ptr %_3, i64 136
  store i64 %at2.i, ptr %17, align 8, !alias.scope !53, !noalias !50
  br label %_RNvCscgRqy0Y3eGg_6parser6finish.exit.thread

bb7.i:                                            ; preds = %bb2.i
  %at.sroa.0.0.in.v.i = select i1 %3, i64 80, i64 88
  br label %bb35.sink.split.i

_RNvCscgRqy0Y3eGg_6parser6finish.exit.thread:     ; preds = %start, %bb35.sink.split.i
  %n.sroa.41.0._3.sroa_idx10 = getelementptr inbounds nuw i8, ptr %_3, i64 136
  %n.sroa.41.0.copyload11 = load i64, ptr %n.sroa.41.0._3.sroa_idx10, align 8, !alias.scope !60
  call void @llvm.lifetime.end.p0(ptr nonnull %_3)
  br label %19

_RNvCscgRqy0Y3eGg_6parser6finish.exit:            ; preds = %bb19.i, %bb28.i
  %n.sroa.52.0.copyload.pre = load i32, ptr %0, align 8, !alias.scope !60
  %n.sroa.52.0.copyload.pre.fr = freeze i32 %n.sroa.52.0.copyload.pre
  %18 = icmp eq i32 %n.sroa.52.0.copyload.pre.fr, 0
  %n.sroa.3.0._3.sroa_idx = getelementptr inbounds nuw i8, ptr %_3, i64 112
  %n.sroa.3.0.copyload = load i64, ptr %n.sroa.3.0._3.sroa_idx, align 8, !alias.scope !60
  %n.sroa.41.0._3.sroa_idx = getelementptr inbounds nuw i8, ptr %_3, i64 136
  %n.sroa.41.0.copyload = load i64, ptr %n.sroa.41.0._3.sroa_idx, align 8, !alias.scope !60
  call void @llvm.lifetime.end.p0(ptr nonnull %_3)
  %spec.select = select i1 %18, i64 %n.sroa.3.0.copyload, i64 %n.sroa.41.0.copyload
  br label %19

19:                                               ; preds = %_RNvCscgRqy0Y3eGg_6parser6finish.exit, %_RNvCscgRqy0Y3eGg_6parser6finish.exit.thread
  %20 = phi i64 [ %n.sroa.41.0.copyload11, %_RNvCscgRqy0Y3eGg_6parser6finish.exit.thread ], [ %spec.select, %_RNvCscgRqy0Y3eGg_6parser6finish.exit ]
  ret i64 %20
}

; core::panicking::panic_const::panic_const_add_overflow
; Function Attrs: cold noinline noreturn nounwind
declare void @_RNvNtNtCs9nEiEE0E2Vj_4core9panicking11panic_const24panic_const_add_overflow(ptr noalias nofree noundef readonly align 8 captures(address, read_provenance) dereferenceable(24)) unnamed_addr #4

; core::panicking::panic_const::panic_const_sub_overflow
; Function Attrs: cold noinline noreturn nounwind
declare void @_RNvNtNtCs9nEiEE0E2Vj_4core9panicking11panic_const24panic_const_sub_overflow(ptr noalias nofree noundef readonly align 8 captures(address, read_provenance) dereferenceable(24)) unnamed_addr #4

; core::panicking::panic_bounds_check
; Function Attrs: cold minsize noinline noreturn nounwind optsize
declare void @_RNvNtCs9nEiEE0E2Vj_4core9panicking18panic_bounds_check(i64 noundef, i64 noundef, ptr noalias nofree noundef readonly align 8 captures(address, read_provenance) dereferenceable(24)) unnamed_addr #5

; Function Attrs: mustprogress nocallback nofree nosync nounwind willreturn memory(argmem: readwrite)
declare void @llvm.lifetime.start.p0(ptr captures(none)) #6

; Function Attrs: mustprogress nocallback nofree nosync nounwind willreturn memory(argmem: readwrite)
declare void @llvm.lifetime.end.p0(ptr captures(none)) #6

; core::panicking::panic_const::panic_const_mul_overflow
; Function Attrs: cold noinline noreturn nounwind
declare void @_RNvNtNtCs9nEiEE0E2Vj_4core9panicking11panic_const24panic_const_mul_overflow(ptr noalias nofree noundef readonly align 8 captures(address, read_provenance) dereferenceable(24)) unnamed_addr #4

; Function Attrs: mustprogress nocallback nofree nosync nounwind willreturn memory(argmem: readwrite)
declare void @llvm.memcpy.p0.p0.i64(ptr noalias writeonly captures(none), ptr noalias readonly captures(none), i64, i1 immarg) #6

; Function Attrs: mustprogress nocallback nofree nosync nounwind willreturn memory(inaccessiblemem: write)
declare void @llvm.assume(i1 noundef) #7

; Function Attrs: mustprogress nocallback nofree nosync nounwind willreturn memory(argmem: write)
declare void @llvm.memset.p0.i64(ptr writeonly captures(none), i8, i64, i1 immarg) #8

; Function Attrs: nocallback nofree nosync nounwind willreturn memory(inaccessiblemem: readwrite)
declare void @llvm.experimental.noalias.scope.decl(metadata) #9

attributes #0 = { nounwind "frame-pointer"="non-leaf" "probe-stack"="inline-asm" "target-cpu"="generic" }
attributes #1 = { mustprogress nofree norecurse nosync nounwind willreturn memory(argmem: read) "frame-pointer"="non-leaf" "probe-stack"="inline-asm" "target-cpu"="generic" }
attributes #2 = { mustprogress nofree norecurse nosync nounwind willreturn memory(none) "frame-pointer"="non-leaf" "probe-stack"="inline-asm" "target-cpu"="generic" }
attributes #3 = { mustprogress nofree norecurse nosync nounwind willreturn memory(argmem: write) "frame-pointer"="non-leaf" "probe-stack"="inline-asm" "target-cpu"="generic" }
attributes #4 = { cold noinline noreturn nounwind "frame-pointer"="non-leaf" "probe-stack"="inline-asm" "target-cpu"="generic" }
attributes #5 = { cold minsize noinline noreturn nounwind optsize "frame-pointer"="non-leaf" "probe-stack"="inline-asm" "target-cpu"="generic" }
attributes #6 = { mustprogress nocallback nofree nosync nounwind willreturn memory(argmem: readwrite) }
attributes #7 = { mustprogress nocallback nofree nosync nounwind willreturn memory(inaccessiblemem: write) }
attributes #8 = { mustprogress nocallback nofree nosync nounwind willreturn memory(argmem: write) }
attributes #9 = { nocallback nofree nosync nounwind willreturn memory(inaccessiblemem: readwrite) }
attributes #10 = { noinline noreturn nounwind }
attributes #11 = { nounwind }

!llvm.module.flags = !{!14, !15}
!llvm.ident = !{!16}

!0 = !{i64 -6297053161993449740}
!1 = !{i64 -3510524862181007109}
!2 = !{i64 3714375859257021753}
!3 = !{i64 -6726614943874362767}
!4 = !{i64 -7466585116998909484}
!5 = !{i64 -444915590312019230}
!6 = !{i64 -8400207999207897383}
!7 = !{i64 3108184073453944983}
!8 = !{i64 -2129928904612804306}
!9 = !{i64 100773606297024674}
!10 = !{i64 6463080620118093204}
!11 = !{i64 -7608611212819242443}
!12 = !{i64 9218882285299014095}
!13 = !{i64 -6983383373342215714}
!14 = !{i32 8, !"PIC Level", i32 2}
!15 = !{i32 7, !"frame-pointer", i32 1}
!16 = !{!"rustc version 1.99.1 (58cf8f9c3 2026-10-13) (Homebrew)"}
!17 = !{i64 6090643705355222641}
!18 = !{}
!19 = !{i64 -2436849661378344251}
!20 = !{!21}
!21 = distinct !{!21, !22, !"_RNvCscgRqy0Y3eGg_6parser13encoding_byte: %n"}
!22 = distinct !{!22, !"_RNvCscgRqy0Y3eGg_6parser13encoding_byte"}
!23 = !{!24}
!24 = distinct !{!24, !25, !"_RNvCscgRqy0Y3eGg_6parser4step: %n"}
!25 = distinct !{!25, !"_RNvCscgRqy0Y3eGg_6parser4step"}
!26 = !{i8 0, i8 2}
!27 = !{!28}
!28 = distinct !{!28, !29, !"_RNvCscgRqy0Y3eGg_6parser4done: %n"}
!29 = distinct !{!29, !"_RNvCscgRqy0Y3eGg_6parser4done"}
!30 = !{!31}
!31 = distinct !{!31, !32, !"_RNvCscgRqy0Y3eGg_6parser4done: %n"}
!32 = distinct !{!32, !"_RNvCscgRqy0Y3eGg_6parser4done"}
!33 = !{!31, !24}
!34 = !{i64 6291344654974525855}
!35 = !{i64 -1356963505183173567}
!36 = !{i64 -9119629366087381497}
!37 = !{i64 -4439800407747234215}
!38 = !{!39}
!39 = distinct !{!39, !40, !"_RNvCscgRqy0Y3eGg_6parser6finish: %_0"}
!40 = distinct !{!40, !"_RNvCscgRqy0Y3eGg_6parser6finish"}
!41 = !{!42}
!42 = distinct !{!42, !40, !"_RNvCscgRqy0Y3eGg_6parser6finish: %n"}
!43 = !{!44}
!44 = distinct !{!44, !45, !"_RNvCscgRqy0Y3eGg_6parser4done: %n"}
!45 = distinct !{!45, !"_RNvCscgRqy0Y3eGg_6parser4done"}
!46 = !{!44, !42}
!47 = !{!44, !39, !42}
!48 = !{!39, !42}
!49 = !{i64 5032672057777375315}
!50 = !{!51}
!51 = distinct !{!51, !52, !"_RNvCscgRqy0Y3eGg_6parser6finish: %_0"}
!52 = distinct !{!52, !"_RNvCscgRqy0Y3eGg_6parser6finish"}
!53 = !{!54}
!54 = distinct !{!54, !52, !"_RNvCscgRqy0Y3eGg_6parser6finish: %n"}
!55 = !{!56}
!56 = distinct !{!56, !57, !"_RNvCscgRqy0Y3eGg_6parser4done: %n"}
!57 = distinct !{!57, !"_RNvCscgRqy0Y3eGg_6parser4done"}
!58 = !{!56, !54}
!59 = !{!56, !51, !54}
!60 = !{!51, !54}
