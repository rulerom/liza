; ModuleID = '/private/tmp/liza-json-pinned-target-baseline/liza.ll'
source_filename = "/private/tmp/liza-json-pinned-target-baseline/liza.ll"
target datalayout = "e-m:o-p270:32:32-p271:32:32-p272:64:64-i64:64-i128:128-n32:64-S128-Fn32"
target triple = "arm64-apple-macosx26.0.0"

%variant.5 = type { i32, i64, %struct.JsonError }
%struct.JsonError = type { %variant.1, i64 }
%variant.1 = type { i32, [0 x i8], [0 x i8], [0 x i8], [0 x i8], [0 x i8], [0 x i8], [0 x i8], [0 x i8] }
%struct.JsonState = type { %struct.Utf8StreamState, i64, [64 x i8], i32, i1, i32, i1, i32, i32, i32, i32, i64, i64, i32, i64 }
%struct.Utf8StreamState = type { i64, i64, i64, i32, i8, i8, i32, i64 }
%variant.2 = type { i32, i64, %struct.Utf8StreamError }
%struct.Utf8StreamError = type { %variant.0, i64 }
%variant.0 = type { i32, [0 x i8], [0 x i8] }
%variant.3 = type { i32, %struct.Utf8StreamError, [0 x i8] }
%variant.4 = type { i32, %struct.JsonError, [0 x i8] }

; Function Attrs: cold noreturn nounwind memory(inaccessiblemem: write)
declare void @llvm.trap() #0

; Function Attrs: mustprogress nocallback nofree nounwind willreturn memory(argmem: readwrite)
declare void @llvm.memmove.p0.p0.i64(ptr writeonly captures(none), ptr readonly captures(none), i64, i1 immarg) #1

; Function Attrs: mustprogress nocallback nofree nosync nounwind speculatable willreturn memory(none)
declare { i32, i1 } @llvm.uadd.with.overflow.i32(i32, i32) #2

; Function Attrs: mustprogress nocallback nofree nosync nounwind speculatable willreturn memory(none)
declare { i32, i1 } @llvm.usub.with.overflow.i32(i32, i32) #2

; Function Attrs: mustprogress nocallback nofree nosync nounwind speculatable willreturn memory(none)
declare { i64, i1 } @llvm.uadd.with.overflow.i64(i64, i64) #2

; Function Attrs: nounwind memory(readwrite, inaccessiblemem: write)
define range(i32 0, 9) i32 @liza_status(ptr readonly captures(none) %p0) local_unnamed_addr #3 {
b0:
  %v0 = tail call %variant.5 @liza_json.finish(ptr %p0)
  %v1 = extractvalue %variant.5 %v0, 0
  %switch = icmp eq i32 %v1, 0
  %v4 = extractvalue %variant.5 %v0, 2
  %v5 = extractvalue %struct.JsonError %v4, 0
  %v6 = extractvalue %variant.1 %v5, 0
  %switch.offset = add nsw i32 %v6, 1
  %common.ret.op = select i1 %switch, i32 0, i32 %switch.offset
  ret i32 %common.ret.op
}

; Function Attrs: nounwind memory(readwrite, inaccessiblemem: write)
define i64 @liza_value(ptr readonly captures(none) %p0) local_unnamed_addr #3 {
b0:
  %v0 = tail call %variant.5 @liza_json.finish(ptr %p0)
  %v1 = extractvalue %variant.5 %v0, 0
  %switch = icmp eq i32 %v1, 0
  %v2 = extractvalue %variant.5 %v0, 1
  %v3 = extractvalue %variant.5 %v0, 2
  %v4 = extractvalue %struct.JsonError %v3, 1
  %common.ret.op = select i1 %switch, i64 %v2, i64 %v4
  ret i64 %common.ret.op
}

; Function Attrs: mustprogress nofree norecurse nosync nounwind willreturn memory(argmem: read)
define range(i32 0, 2) i32 @liza_pending(ptr readonly captures(none) %p0) local_unnamed_addr #4 {
b0:
  %v0_ptr.i = getelementptr i8, ptr %p0, i64 168
  %v0.i = load i32, ptr %v0_ptr.i, align 4
  %v2.i.not = icmp ne i32 %v0.i, 0
  %spec.select = zext i1 %v2.i.not to i32
  ret i32 %spec.select
}

; Function Attrs: mustprogress nofree norecurse nosync nounwind willreturn memory(argmem: readwrite)
define void @liza_start(ptr writeonly sret(%struct.JsonState) captures(none) initializes((0, 30), (32, 125), (128, 172), (176, 184)) %return_storage) local_unnamed_addr #5 {
b0:
  %v16_mem.sroa.75.sroa.0.i = alloca i8, align 4
  %v16_mem.sroa.77.sroa.0.i = alloca i8, align 4
  %v0_mem.sroa.5 = alloca [88 x i8], align 4
  %v0_mem.sroa.9 = alloca [39 x i8], align 1
  call void @llvm.lifetime.start.p0(i64 1, ptr nonnull %v16_mem.sroa.75.sroa.0.i)
  call void @llvm.lifetime.start.p0(i64 1, ptr nonnull %v16_mem.sroa.77.sroa.0.i)
  store i1 false, ptr %v16_mem.sroa.75.sroa.0.i, align 4
  store i1 false, ptr %v16_mem.sroa.77.sroa.0.i, align 4
  %v0_mem.sroa.5.4.sroa_idx = getelementptr inbounds nuw i8, ptr %v0_mem.sroa.5, i64 4
  call void @llvm.memset.p0.i64(ptr noundef nonnull align 4 dereferenceable(84) %v0_mem.sroa.5.4.sroa_idx, i8 0, i64 84, i1 false)
  %v16_mem.sroa.75.sroa.0.i.0.v16_mem.sroa.75.sroa.0.i.0.v16_mem.sroa.75.sroa.0.i.0.v16_mem.sroa.75.sroa.0.0.v16_mem.sroa.75.sroa.0.0..i = load i8, ptr %v16_mem.sroa.75.sroa.0.i, align 4
  %v16_mem.sroa.77.sroa.0.i.0.v16_mem.sroa.77.sroa.0.i.0.v16_mem.sroa.77.sroa.0.i.0.v16_mem.sroa.77.sroa.0.0.v16_mem.sroa.77.sroa.0.0..i = load i8, ptr %v16_mem.sroa.77.sroa.0.i, align 4
  %v0_mem.sroa.9.3.sroa_idx = getelementptr inbounds nuw i8, ptr %v0_mem.sroa.9, i64 3
  call void @llvm.memset.p0.i64(ptr noundef nonnull align 1 dereferenceable(36) %v0_mem.sroa.9.3.sroa_idx, i8 0, i64 36, i1 false)
  call void @llvm.lifetime.end.p0(i64 1, ptr nonnull %v16_mem.sroa.75.sroa.0.i)
  call void @llvm.lifetime.end.p0(i64 1, ptr nonnull %v16_mem.sroa.77.sroa.0.i)
  tail call void @llvm.memset.p0.i64(ptr noundef nonnull align 8 dereferenceable(28) %return_storage, i8 0, i64 28, i1 false)
  %v0_mem.sroa.2.0.return_storage.sroa_idx = getelementptr inbounds nuw i8, ptr %return_storage, i64 28
  store i8 -128, ptr %v0_mem.sroa.2.0.return_storage.sroa_idx, align 4
  %v0_mem.sroa.3.0.return_storage.sroa_idx = getelementptr inbounds nuw i8, ptr %return_storage, i64 29
  store i8 -65, ptr %v0_mem.sroa.3.0.return_storage.sroa_idx, align 1
  %v0_mem.sroa.41.0.return_storage.sroa_idx = getelementptr inbounds nuw i8, ptr %return_storage, i64 32
  store i32 0, ptr %v0_mem.sroa.41.0.return_storage.sroa_idx, align 8
  %v0_mem.sroa.5.0.return_storage.sroa_idx = getelementptr inbounds nuw i8, ptr %return_storage, i64 36
  call void @llvm.memcpy.p0.p0.i64(ptr noundef nonnull align 4 dereferenceable(88) %v0_mem.sroa.5.0.return_storage.sroa_idx, ptr noundef nonnull align 4 dereferenceable(88) %v0_mem.sroa.5, i64 88, i1 false)
  %v0_mem.sroa.6.0.return_storage.sroa_idx = getelementptr inbounds nuw i8, ptr %return_storage, i64 124
  store i8 %v16_mem.sroa.75.sroa.0.i.0.v16_mem.sroa.75.sroa.0.i.0.v16_mem.sroa.75.sroa.0.i.0.v16_mem.sroa.75.sroa.0.0.v16_mem.sroa.75.sroa.0.0..i, ptr %v0_mem.sroa.6.0.return_storage.sroa_idx, align 4
  %v0_mem.sroa.72.0.return_storage.sroa_idx = getelementptr inbounds nuw i8, ptr %return_storage, i64 128
  store i32 0, ptr %v0_mem.sroa.72.0.return_storage.sroa_idx, align 8
  %v0_mem.sroa.8.0.return_storage.sroa_idx = getelementptr inbounds nuw i8, ptr %return_storage, i64 132
  store i8 %v16_mem.sroa.77.sroa.0.i.0.v16_mem.sroa.77.sroa.0.i.0.v16_mem.sroa.77.sroa.0.i.0.v16_mem.sroa.77.sroa.0.0.v16_mem.sroa.77.sroa.0.0..i, ptr %v0_mem.sroa.8.0.return_storage.sroa_idx, align 4
  %v0_mem.sroa.9.0.return_storage.sroa_idx = getelementptr inbounds nuw i8, ptr %return_storage, i64 133
  call void @llvm.memcpy.p0.p0.i64(ptr noundef nonnull align 1 dereferenceable(39) %v0_mem.sroa.9.0.return_storage.sroa_idx, ptr noundef nonnull align 1 dereferenceable(39) %v0_mem.sroa.9, i64 39, i1 false)
  %v0_mem.sroa.103.0.return_storage.sroa_idx = getelementptr inbounds nuw i8, ptr %return_storage, i64 176
  store i64 0, ptr %v0_mem.sroa.103.0.return_storage.sroa_idx, align 8
  ret void
}

; Function Attrs: nounwind memory(readwrite, inaccessiblemem: write)
define void @liza_feed(ptr writeonly sret(%struct.JsonState) captures(none) initializes((0, 184)) %return_storage, ptr readonly captures(none) %p0, { ptr, i32 } %p1) local_unnamed_addr #3 {
b0:
  %v0_mem = alloca %struct.JsonState, align 8
  call void @liza_json.feed(ptr nonnull sret(%struct.JsonState) %v0_mem, ptr %p0, { ptr, i32 } %p1)
  call void @llvm.memcpy.p0.p0.i64(ptr noundef nonnull align 8 dereferenceable(184) %return_storage, ptr noundef nonnull align 8 dereferenceable(184) %v0_mem, i64 184, i1 false)
  ret void
}

; Function Attrs: mustprogress nofree norecurse nosync nounwind willreturn memory(none)
define noundef i32 @liza_main() local_unnamed_addr #6 {
b0:
  ret i32 0
}

; Function Attrs: mustprogress nofree norecurse nosync nounwind willreturn memory(none)
define %struct.Utf8StreamState @liza_utf8_stream.create() local_unnamed_addr #6 {
b0:
  ret %struct.Utf8StreamState { i64 0, i64 0, i64 0, i32 0, i8 -128, i8 -65, i32 0, i64 0 }
}

; Function Attrs: nounwind memory(inaccessiblemem: write)
define %struct.Utf8StreamState @liza_utf8_stream.feed_byte(%struct.Utf8StreamState %p0, i8 %p1) local_unnamed_addr #7 {
b0:
  %v0 = extractvalue %struct.Utf8StreamState %p0, 6
  %v2.not = icmp eq i32 %v0, 0
  br i1 %v2.not, label %b3, label %common.ret

common.ret:                                       ; preds = %b0, %v145_ok, %b53, %b48, %b34, %b11, %b4
  %common.ret.op = phi %struct.Utf8StreamState [ %v11, %b4 ], [ %v28, %b11 ], [ %v96, %b34 ], [ %v111, %b48 ], [ %v134, %b53 ], [ %v146, %v145_ok ], [ %p0, %b0 ]
  ret %struct.Utf8StreamState %common.ret.op

b3:                                               ; preds = %b0
  %v3 = extractvalue %struct.Utf8StreamState %p0, 0
  %v5 = icmp eq i64 %v3, -1
  br i1 %v5, label %b4, label %b6

b4:                                               ; preds = %b3
  %v8 = insertvalue %struct.Utf8StreamState %p0, i32 2, 6
  %v11 = insertvalue %struct.Utf8StreamState %v8, i64 -1, 7
  br label %common.ret

b6:                                               ; preds = %b3
  %v12 = extractvalue %struct.Utf8StreamState %p0, 3
  %v14 = icmp eq i32 %v12, 0
  br i1 %v14, label %b7, label %b8

b7:                                               ; preds = %b6
  %v17 = insertvalue %struct.Utf8StreamState %p0, i64 %v3, 2
  %v19 = icmp sgt i8 %p1, -1
  br i1 %v19, label %b9, label %b10

b8:                                               ; preds = %b6
  %v100 = extractvalue %struct.Utf8StreamState %p0, 4
  %v101 = icmp ult i8 %p1, %v100
  %v103 = extractvalue %struct.Utf8StreamState %p0, 5
  %v104 = icmp ugt i8 %p1, %v103
  %v105 = select i1 %v101, i1 true, i1 %v104
  br i1 %v105, label %b48, label %v115_ok

b9:                                               ; preds = %b7
  %v20 = extractvalue %struct.Utf8StreamState %p0, 1
  %v22 = icmp eq i64 %v20, -1
  br i1 %v22, label %b11, label %v32_ok

b10:                                              ; preds = %b7
  %v36 = insertvalue %struct.Utf8StreamState %v17, i8 -128, 4
  %v39 = insertvalue %struct.Utf8StreamState %v36, i8 -65, 5
  %0 = add nsw i8 %p1, 62
  %v45 = icmp ult i8 %0, 30
  br i1 %v45, label %b17, label %b18

b11:                                              ; preds = %b9
  %v25 = insertvalue %struct.Utf8StreamState %v17, i32 2, 6
  %v28 = insertvalue %struct.Utf8StreamState %v25, i64 %v3, 7
  br label %common.ret

v32_ok:                                           ; preds = %b9
  %v32 = add nuw i64 %v20, 1
  %v33 = insertvalue %struct.Utf8StreamState %v17, i64 %v32, 1
  br label %b57

b17:                                              ; preds = %b10
  %v48 = insertvalue %struct.Utf8StreamState %v39, i32 1, 3
  br label %b57

b18:                                              ; preds = %b10
  %1 = and i8 %p1, -16
  %v54 = icmp eq i8 %1, -32
  br i1 %v54, label %b22, label %b23

b22:                                              ; preds = %b18
  %v57 = insertvalue %struct.Utf8StreamState %v39, i32 2, 3
  %v59 = icmp eq i8 %p1, -32
  %v62 = insertvalue %struct.Utf8StreamState %v57, i8 -96, 4
  %spec.select = select i1 %v59, %struct.Utf8StreamState %v62, %struct.Utf8StreamState %v57
  %v65 = icmp eq i8 %p1, -19
  %v68 = insertvalue %struct.Utf8StreamState %spec.select, i8 -97, 5
  %spec.select2 = select i1 %v65, %struct.Utf8StreamState %v68, %struct.Utf8StreamState %spec.select
  br label %b57

b23:                                              ; preds = %b18
  %2 = add nsw i8 %p1, 16
  %v75 = icmp ult i8 %2, 5
  br i1 %v75, label %b33, label %b34

b33:                                              ; preds = %b23
  %v78 = insertvalue %struct.Utf8StreamState %v39, i32 3, 3
  %v80 = icmp eq i8 %p1, -16
  %v83 = insertvalue %struct.Utf8StreamState %v78, i8 -112, 4
  %spec.select1 = select i1 %v80, %struct.Utf8StreamState %v83, %struct.Utf8StreamState %v78
  %v86 = icmp eq i8 %p1, -12
  %v89 = insertvalue %struct.Utf8StreamState %spec.select1, i8 -113, 5
  %spec.select3 = select i1 %v86, %struct.Utf8StreamState %v89, %struct.Utf8StreamState %spec.select1
  br label %b57

b34:                                              ; preds = %b23
  %v93 = insertvalue %struct.Utf8StreamState %v39, i32 1, 6
  %v96 = insertvalue %struct.Utf8StreamState %v93, i64 %v3, 7
  br label %common.ret

b48:                                              ; preds = %b8
  %v108 = insertvalue %struct.Utf8StreamState %p0, i32 1, 6
  %v110 = extractvalue %struct.Utf8StreamState %p0, 2
  %v111 = insertvalue %struct.Utf8StreamState %v108, i64 %v110, 7
  br label %common.ret

v115_ok:                                          ; preds = %b8
  %v115 = add i32 %v12, -1
  %v116 = insertvalue %struct.Utf8StreamState %p0, i32 %v115, 3
  %v119 = insertvalue %struct.Utf8StreamState %v116, i8 -128, 4
  %v122 = insertvalue %struct.Utf8StreamState %v119, i8 -65, 5
  %v125 = icmp eq i32 %v115, 0
  br i1 %v125, label %b51, label %b57

b51:                                              ; preds = %v115_ok
  %v126 = extractvalue %struct.Utf8StreamState %p0, 1
  %v128 = icmp eq i64 %v126, -1
  br i1 %v128, label %b53, label %v138_ok

b53:                                              ; preds = %b51
  %v131 = insertvalue %struct.Utf8StreamState %v122, i32 2, 6
  %v134 = insertvalue %struct.Utf8StreamState %v131, i64 %v3, 7
  br label %common.ret

v138_ok:                                          ; preds = %b51
  %v138 = add nuw i64 %v126, 1
  %v139 = insertvalue %struct.Utf8StreamState %v122, i64 %v138, 1
  br label %b57

b57:                                              ; preds = %b33, %b22, %v138_ok, %v115_ok, %v32_ok, %b17
  %v141 = phi %struct.Utf8StreamState [ %v33, %v32_ok ], [ %v48, %b17 ], [ %v139, %v138_ok ], [ %v122, %v115_ok ], [ %spec.select2, %b22 ], [ %spec.select3, %b33 ]
  %v143 = extractvalue %struct.Utf8StreamState %v141, 0
  %v145_pair = tail call { i64, i1 } @llvm.uadd.with.overflow.i64(i64 %v143, i64 1)
  %v145_overflow = extractvalue { i64, i1 } %v145_pair, 1
  br i1 %v145_overflow, label %v145_trap, label %v145_ok

v145_trap:                                        ; preds = %b57
  tail call void @llvm.trap()
  unreachable

v145_ok:                                          ; preds = %b57
  %v145 = extractvalue { i64, i1 } %v145_pair, 0
  %v146 = insertvalue %struct.Utf8StreamState %v141, i64 %v145, 0
  br label %common.ret
}

; Function Attrs: mustprogress nofree norecurse nosync nounwind willreturn memory(none)
define %variant.2 @liza_utf8_stream.finish(%struct.Utf8StreamState %p0) local_unnamed_addr #6 {
b0:
  %v0 = extractvalue %struct.Utf8StreamState %p0, 6
  switch i32 %v0, label %b6 [
    i32 1, label %b1
    i32 2, label %b4
  ]

common.ret:                                       ; preds = %b9, %b7, %b4, %b1
  %common.ret.op = phi %variant.2 [ %v6, %b1 ], [ %v13, %b4 ], [ %v20, %b7 ], [ %v22, %b9 ]
  ret %variant.2 %common.ret.op

b1:                                               ; preds = %b0
  %v4 = extractvalue %struct.Utf8StreamState %p0, 7
  %v5 = insertvalue %struct.Utf8StreamError zeroinitializer, i64 %v4, 1
  %v6 = insertvalue %variant.2 { i32 1, i64 0, %struct.Utf8StreamError zeroinitializer }, %struct.Utf8StreamError %v5, 2
  br label %common.ret

b4:                                               ; preds = %b0
  %v11 = extractvalue %struct.Utf8StreamState %p0, 7
  %v12 = insertvalue %struct.Utf8StreamError { %variant.0 { i32 1, [0 x i8] zeroinitializer, [0 x i8] zeroinitializer }, i64 0 }, i64 %v11, 1
  %v13 = insertvalue %variant.2 { i32 1, i64 0, %struct.Utf8StreamError zeroinitializer }, %struct.Utf8StreamError %v12, 2
  br label %common.ret

b6:                                               ; preds = %b0
  %v14 = extractvalue %struct.Utf8StreamState %p0, 3
  %v16.not = icmp eq i32 %v14, 0
  br i1 %v16.not, label %b9, label %b7

b7:                                               ; preds = %b6
  %v18 = extractvalue %struct.Utf8StreamState %p0, 2
  %v19 = insertvalue %struct.Utf8StreamError zeroinitializer, i64 %v18, 1
  %v20 = insertvalue %variant.2 { i32 1, i64 0, %struct.Utf8StreamError zeroinitializer }, %struct.Utf8StreamError %v19, 2
  br label %common.ret

b9:                                               ; preds = %b6
  %v21 = extractvalue %struct.Utf8StreamState %p0, 1
  %v22 = insertvalue %variant.2 zeroinitializer, i64 %v21, 1
  br label %common.ret
}

; Function Attrs: mustprogress nofree norecurse nosync nounwind willreturn memory(none)
define %variant.3 @liza_utf8_stream.status(%struct.Utf8StreamState %p0) local_unnamed_addr #6 {
b0:
  %v0 = extractvalue %struct.Utf8StreamState %p0, 6
  switch i32 %v0, label %common.ret [
    i32 1, label %b1
    i32 2, label %b4
  ]

common.ret:                                       ; preds = %b0, %b4, %b1
  %common.ret.op = phi %variant.3 [ %v6, %b1 ], [ %v13, %b4 ], [ { i32 1, %struct.Utf8StreamError zeroinitializer, [0 x i8] zeroinitializer }, %b0 ]
  ret %variant.3 %common.ret.op

b1:                                               ; preds = %b0
  %v4 = extractvalue %struct.Utf8StreamState %p0, 7
  %v5 = insertvalue %struct.Utf8StreamError zeroinitializer, i64 %v4, 1
  %v6 = insertvalue %variant.3 zeroinitializer, %struct.Utf8StreamError %v5, 1
  br label %common.ret

b4:                                               ; preds = %b0
  %v11 = extractvalue %struct.Utf8StreamState %p0, 7
  %v12 = insertvalue %struct.Utf8StreamError { %variant.0 { i32 1, [0 x i8] zeroinitializer, [0 x i8] zeroinitializer }, i64 0 }, i64 %v11, 1
  %v13 = insertvalue %variant.3 zeroinitializer, %struct.Utf8StreamError %v12, 1
  br label %common.ret
}

; Function Attrs: mustprogress nofree norecurse nosync nounwind willreturn memory(argmem: write)
define void @liza_json.create(ptr writeonly sret(%struct.JsonState) captures(none) initializes((0, 30), (32, 36), (40, 125), (128, 133), (136, 172), (176, 184)) %return_storage) local_unnamed_addr #8 {
b0:
  %v16_mem.sroa.75.sroa.0 = alloca i8, align 4
  %v16_mem.sroa.77.sroa.0 = alloca i8, align 4
  store i1 false, ptr %v16_mem.sroa.75.sroa.0, align 4
  store i1 false, ptr %v16_mem.sroa.77.sroa.0, align 4
  %v16_mem.sroa.5.0.return_storage.sroa_idx = getelementptr inbounds nuw i8, ptr %return_storage, i64 28
  tail call void @llvm.memset.p0.i64(ptr noundef nonnull align 8 dereferenceable(28) %return_storage, i8 0, i64 28, i1 false)
  store i8 -128, ptr %v16_mem.sroa.5.0.return_storage.sroa_idx, align 4
  %v16_mem.sroa.6.0.return_storage.sroa_idx = getelementptr inbounds nuw i8, ptr %return_storage, i64 29
  store i8 -65, ptr %v16_mem.sroa.6.0.return_storage.sroa_idx, align 1
  %v16_mem.sroa.71.0.return_storage.sroa_idx = getelementptr inbounds nuw i8, ptr %return_storage, i64 32
  store i32 0, ptr %v16_mem.sroa.71.0.return_storage.sroa_idx, align 8
  %v16_mem.sroa.82.0.return_storage.sroa_idx = getelementptr inbounds nuw i8, ptr %return_storage, i64 40
  %v16_mem.sroa.75.0.return_storage.sroa_idx = getelementptr inbounds nuw i8, ptr %return_storage, i64 124
  tail call void @llvm.memset.p0.i64(ptr noundef nonnull align 8 dereferenceable(84) %v16_mem.sroa.82.0.return_storage.sroa_idx, i8 0, i64 84, i1 false)
  %v16_mem.sroa.75.sroa.0.0.v16_mem.sroa.75.sroa.0.0.v16_mem.sroa.75.sroa.0.0. = load i8, ptr %v16_mem.sroa.75.sroa.0, align 4
  store i8 %v16_mem.sroa.75.sroa.0.0.v16_mem.sroa.75.sroa.0.0.v16_mem.sroa.75.sroa.0.0., ptr %v16_mem.sroa.75.0.return_storage.sroa_idx, align 4
  %v16_mem.sroa.764.0.return_storage.sroa_idx = getelementptr inbounds nuw i8, ptr %return_storage, i64 128
  store i32 0, ptr %v16_mem.sroa.764.0.return_storage.sroa_idx, align 8
  %v16_mem.sroa.77.0.return_storage.sroa_idx = getelementptr inbounds nuw i8, ptr %return_storage, i64 132
  %v16_mem.sroa.77.sroa.0.0.v16_mem.sroa.77.sroa.0.0.v16_mem.sroa.77.sroa.0.0. = load i8, ptr %v16_mem.sroa.77.sroa.0, align 4
  store i8 %v16_mem.sroa.77.sroa.0.0.v16_mem.sroa.77.sroa.0.0.v16_mem.sroa.77.sroa.0.0., ptr %v16_mem.sroa.77.0.return_storage.sroa_idx, align 4
  %v16_mem.sroa.785.0.return_storage.sroa_idx = getelementptr inbounds nuw i8, ptr %return_storage, i64 136
  %v16_mem.sroa.857.0.return_storage.sroa_idx = getelementptr inbounds nuw i8, ptr %return_storage, i64 176
  store i64 0, ptr %v16_mem.sroa.857.0.return_storage.sroa_idx, align 8
  tail call void @llvm.memset.p0.i64(ptr noundef nonnull align 8 dereferenceable(36) %v16_mem.sroa.785.0.return_storage.sroa_idx, i8 0, i64 36, i1 false)
  ret void
}

; Function Attrs: mustprogress nofree norecurse nosync nounwind willreturn memory(argmem: readwrite)
define void @liza___liza_json_fail(ptr writeonly sret(%struct.JsonState) captures(none) initializes((0, 184)) %return_storage, ptr readonly captures(none) %p0, i32 %p1, i64 %p2) local_unnamed_addr #5 {
b0:
  %v1_mem.sroa.3.0.p0.sroa_idx = getelementptr inbounds nuw i8, ptr %p0, i64 172
  %v1_mem.sroa.3.0.copyload = load i32, ptr %v1_mem.sroa.3.0.p0.sroa_idx, align 1
  tail call void @llvm.memmove.p0.p0.i64(ptr noundef nonnull align 8 dereferenceable(168) %return_storage, ptr noundef nonnull align 1 dereferenceable(168) %p0, i64 168, i1 false)
  %v3_mem.sroa.0.sroa.2.0.return_storage.sroa_idx = getelementptr inbounds nuw i8, ptr %return_storage, i64 168
  store i32 %p1, ptr %v3_mem.sroa.0.sroa.2.0.return_storage.sroa_idx, align 8
  %v3_mem.sroa.0.sroa.3.0.return_storage.sroa_idx = getelementptr inbounds nuw i8, ptr %return_storage, i64 172
  store i32 %v1_mem.sroa.3.0.copyload, ptr %v3_mem.sroa.0.sroa.3.0.return_storage.sroa_idx, align 4
  %v3_mem.sroa.2.0.return_storage.sroa_idx = getelementptr inbounds nuw i8, ptr %return_storage, i64 176
  store i64 %p2, ptr %v3_mem.sroa.2.0.return_storage.sroa_idx, align 8
  ret void
}

; Function Attrs: nounwind memory(readwrite, inaccessiblemem: write)
define void @liza___liza_json_done(ptr writeonly sret(%struct.JsonState) captures(none) %return_storage, ptr readonly %p0) local_unnamed_addr #3 {
b0:
  %v5_mem.sroa.67.sroa.0 = alloca i8, align 4
  %v22_scratch = alloca [64 x i8], align 1
  %v27_scratch = alloca [64 x i8], align 1
  %v29_mem.sroa.0 = alloca { %struct.Utf8StreamState, i64 }, align 8
  %v29_mem.sroa.131.sroa.4 = alloca [59 x i8], align 1
  %v30_mem.sroa.0 = alloca { %struct.Utf8StreamState, i64 }, align 8
  %v30_mem.sroa.131.sroa.5 = alloca [59 x i8], align 1
  %v14_storage = alloca [64 x i8], align 1
  %v9_storage = alloca [64 x i8], align 1
  %v0_ptr = getelementptr i8, ptr %p0, i64 120
  %v0 = load i32, ptr %v0_ptr, align 4
  %v2 = icmp eq i32 %v0, 0
  br i1 %v2, label %b1, label %b2

b1:                                               ; preds = %b0
  %v5_mem.sroa.2.0.p0.sroa_idx = getelementptr inbounds nuw i8, ptr %p0, i64 56
  %0 = load <16 x i8>, ptr %v5_mem.sroa.2.0.p0.sroa_idx, align 1
  %v5_mem.sroa.18.0.p0.sroa_idx = getelementptr inbounds nuw i8, ptr %p0, i64 72
  %1 = load <16 x i8>, ptr %v5_mem.sroa.18.0.p0.sroa_idx, align 1
  %v5_mem.sroa.34.0.p0.sroa_idx = getelementptr inbounds nuw i8, ptr %p0, i64 88
  %2 = load <16 x i8>, ptr %v5_mem.sroa.34.0.p0.sroa_idx, align 1
  %v5_mem.sroa.50.0.p0.sroa_idx = getelementptr inbounds nuw i8, ptr %p0, i64 104
  %3 = load <16 x i8>, ptr %v5_mem.sroa.50.0.p0.sroa_idx, align 1
  %v5_mem.sroa.68.0.p0.sroa_idx = getelementptr inbounds nuw i8, ptr %p0, i64 125
  store i1 true, ptr %v5_mem.sroa.67.sroa.0, align 4
  %v5_mem.sroa.67.sroa.0.0.v5_mem.sroa.67.sroa.0.0.v5_mem.sroa.67.sroa.0.0. = load i8, ptr %v5_mem.sroa.67.sroa.0, align 4
  br label %b9

b2:                                               ; preds = %b0
  %v8_pair = add i32 %v0, -1
  %v9_ptr = getelementptr i8, ptr %p0, i64 56
  %v9.unpack = load i8, ptr %v9_ptr, align 1
  %v9.elt257 = getelementptr i8, ptr %p0, i64 57
  %v9.unpack258 = load i8, ptr %v9.elt257, align 1
  %v9.elt259 = getelementptr i8, ptr %p0, i64 58
  %v9.unpack260 = load i8, ptr %v9.elt259, align 1
  %v9.elt261 = getelementptr i8, ptr %p0, i64 59
  %v9.unpack262 = load i8, ptr %v9.elt261, align 1
  %v9.elt263 = getelementptr i8, ptr %p0, i64 60
  %v9.unpack264 = load i8, ptr %v9.elt263, align 1
  %v9.elt265 = getelementptr i8, ptr %p0, i64 61
  %v9.unpack266 = load i8, ptr %v9.elt265, align 1
  %v9.elt267 = getelementptr i8, ptr %p0, i64 62
  %v9.unpack268 = load i8, ptr %v9.elt267, align 1
  %v9.elt269 = getelementptr i8, ptr %p0, i64 63
  %v9.unpack270 = load i8, ptr %v9.elt269, align 1
  %v9.elt271 = getelementptr i8, ptr %p0, i64 64
  %v9.unpack272 = load i8, ptr %v9.elt271, align 1
  %v9.elt273 = getelementptr i8, ptr %p0, i64 65
  %v9.unpack274 = load i8, ptr %v9.elt273, align 1
  %v9.elt275 = getelementptr i8, ptr %p0, i64 66
  %v9.unpack276 = load i8, ptr %v9.elt275, align 1
  %v9.elt277 = getelementptr i8, ptr %p0, i64 67
  %v9.unpack278 = load i8, ptr %v9.elt277, align 1
  %v9.elt279 = getelementptr i8, ptr %p0, i64 68
  %v9.unpack280 = load i8, ptr %v9.elt279, align 1
  %v9.elt281 = getelementptr i8, ptr %p0, i64 69
  %v9.unpack282 = load i8, ptr %v9.elt281, align 1
  %v9.elt283 = getelementptr i8, ptr %p0, i64 70
  %v9.unpack284 = load i8, ptr %v9.elt283, align 1
  %v9.elt285 = getelementptr i8, ptr %p0, i64 71
  %v9.unpack286 = load i8, ptr %v9.elt285, align 1
  %v9.elt287 = getelementptr i8, ptr %p0, i64 72
  %v9.unpack288 = load i8, ptr %v9.elt287, align 1
  %v9.elt289 = getelementptr i8, ptr %p0, i64 73
  %v9.unpack290 = load i8, ptr %v9.elt289, align 1
  %v9.elt291 = getelementptr i8, ptr %p0, i64 74
  %v9.unpack292 = load i8, ptr %v9.elt291, align 1
  %v9.elt293 = getelementptr i8, ptr %p0, i64 75
  %v9.unpack294 = load i8, ptr %v9.elt293, align 1
  %v9.elt295 = getelementptr i8, ptr %p0, i64 76
  %v9.unpack296 = load i8, ptr %v9.elt295, align 1
  %v9.elt297 = getelementptr i8, ptr %p0, i64 77
  %v9.unpack298 = load i8, ptr %v9.elt297, align 1
  %v9.elt299 = getelementptr i8, ptr %p0, i64 78
  %v9.unpack300 = load i8, ptr %v9.elt299, align 1
  %v9.elt301 = getelementptr i8, ptr %p0, i64 79
  %v9.unpack302 = load i8, ptr %v9.elt301, align 1
  %v9.elt303 = getelementptr i8, ptr %p0, i64 80
  %v9.unpack304 = load i8, ptr %v9.elt303, align 1
  %v9.elt305 = getelementptr i8, ptr %p0, i64 81
  %v9.unpack306 = load i8, ptr %v9.elt305, align 1
  %v9.elt307 = getelementptr i8, ptr %p0, i64 82
  %v9.unpack308 = load i8, ptr %v9.elt307, align 1
  %v9.elt309 = getelementptr i8, ptr %p0, i64 83
  %v9.unpack310 = load i8, ptr %v9.elt309, align 1
  %v9.elt311 = getelementptr i8, ptr %p0, i64 84
  %v9.unpack312 = load i8, ptr %v9.elt311, align 1
  %v9.elt313 = getelementptr i8, ptr %p0, i64 85
  %v9.unpack314 = load i8, ptr %v9.elt313, align 1
  %v9.elt315 = getelementptr i8, ptr %p0, i64 86
  %v9.unpack316 = load i8, ptr %v9.elt315, align 1
  %v9.elt317 = getelementptr i8, ptr %p0, i64 87
  %v9.unpack318 = load i8, ptr %v9.elt317, align 1
  %v9.elt319 = getelementptr i8, ptr %p0, i64 88
  %v9.unpack320 = load i8, ptr %v9.elt319, align 1
  %v9.elt321 = getelementptr i8, ptr %p0, i64 89
  %v9.unpack322 = load i8, ptr %v9.elt321, align 1
  %v9.elt323 = getelementptr i8, ptr %p0, i64 90
  %v9.unpack324 = load i8, ptr %v9.elt323, align 1
  %v9.elt325 = getelementptr i8, ptr %p0, i64 91
  %v9.unpack326 = load i8, ptr %v9.elt325, align 1
  %v9.elt327 = getelementptr i8, ptr %p0, i64 92
  %v9.unpack328 = load i8, ptr %v9.elt327, align 1
  %v9.elt329 = getelementptr i8, ptr %p0, i64 93
  %v9.unpack330 = load i8, ptr %v9.elt329, align 1
  %v9.elt331 = getelementptr i8, ptr %p0, i64 94
  %v9.unpack332 = load i8, ptr %v9.elt331, align 1
  %v9.elt333 = getelementptr i8, ptr %p0, i64 95
  %v9.unpack334 = load i8, ptr %v9.elt333, align 1
  %v9.elt335 = getelementptr i8, ptr %p0, i64 96
  %v9.unpack336 = load i8, ptr %v9.elt335, align 1
  %v9.elt337 = getelementptr i8, ptr %p0, i64 97
  %v9.unpack338 = load i8, ptr %v9.elt337, align 1
  %v9.elt339 = getelementptr i8, ptr %p0, i64 98
  %v9.unpack340 = load i8, ptr %v9.elt339, align 1
  %v9.elt341 = getelementptr i8, ptr %p0, i64 99
  %v9.unpack342 = load i8, ptr %v9.elt341, align 1
  %v9.elt343 = getelementptr i8, ptr %p0, i64 100
  %v9.unpack344 = load i8, ptr %v9.elt343, align 1
  %v9.elt345 = getelementptr i8, ptr %p0, i64 101
  %v9.unpack346 = load i8, ptr %v9.elt345, align 1
  %v9.elt347 = getelementptr i8, ptr %p0, i64 102
  %v9.unpack348 = load i8, ptr %v9.elt347, align 1
  %v9.elt349 = getelementptr i8, ptr %p0, i64 103
  %v9.unpack350 = load i8, ptr %v9.elt349, align 1
  %v9.elt351 = getelementptr i8, ptr %p0, i64 104
  %v9.unpack352 = load i8, ptr %v9.elt351, align 1
  %v9.elt353 = getelementptr i8, ptr %p0, i64 105
  %v9.unpack354 = load i8, ptr %v9.elt353, align 1
  %v9.elt355 = getelementptr i8, ptr %p0, i64 106
  %v9.unpack356 = load i8, ptr %v9.elt355, align 1
  %v9.elt357 = getelementptr i8, ptr %p0, i64 107
  %v9.unpack358 = load i8, ptr %v9.elt357, align 1
  %v9.elt359 = getelementptr i8, ptr %p0, i64 108
  %v9.unpack360 = load i8, ptr %v9.elt359, align 1
  %v9.elt361 = getelementptr i8, ptr %p0, i64 109
  %v9.unpack362 = load i8, ptr %v9.elt361, align 1
  %v9.elt363 = getelementptr i8, ptr %p0, i64 110
  %v9.unpack364 = load i8, ptr %v9.elt363, align 1
  %v9.elt365 = getelementptr i8, ptr %p0, i64 111
  %v9.unpack366 = load i8, ptr %v9.elt365, align 1
  %v9.elt367 = getelementptr i8, ptr %p0, i64 112
  %v9.unpack368 = load i8, ptr %v9.elt367, align 1
  %v9.elt369 = getelementptr i8, ptr %p0, i64 113
  %v9.unpack370 = load i8, ptr %v9.elt369, align 1
  %v9.elt371 = getelementptr i8, ptr %p0, i64 114
  %v9.unpack372 = load i8, ptr %v9.elt371, align 1
  %v9.elt373 = getelementptr i8, ptr %p0, i64 115
  %v9.unpack374 = load i8, ptr %v9.elt373, align 1
  %v9.elt375 = getelementptr i8, ptr %p0, i64 116
  %v9.unpack376 = load i8, ptr %v9.elt375, align 1
  %v9.elt377 = getelementptr i8, ptr %p0, i64 117
  %v9.unpack378 = load i8, ptr %v9.elt377, align 1
  %v9.elt379 = getelementptr i8, ptr %p0, i64 118
  %v9.unpack380 = load i8, ptr %v9.elt379, align 1
  %v9.elt381 = getelementptr i8, ptr %p0, i64 119
  %v9.unpack382 = load i8, ptr %v9.elt381, align 1
  store i8 %v9.unpack, ptr %v9_storage, align 1
  %v9.fca.1.gep = getelementptr inbounds nuw i8, ptr %v9_storage, i64 1
  store i8 %v9.unpack258, ptr %v9.fca.1.gep, align 1
  %v9.fca.2.gep = getelementptr inbounds nuw i8, ptr %v9_storage, i64 2
  store i8 %v9.unpack260, ptr %v9.fca.2.gep, align 1
  %v9.fca.3.gep = getelementptr inbounds nuw i8, ptr %v9_storage, i64 3
  store i8 %v9.unpack262, ptr %v9.fca.3.gep, align 1
  %v9.fca.4.gep = getelementptr inbounds nuw i8, ptr %v9_storage, i64 4
  store i8 %v9.unpack264, ptr %v9.fca.4.gep, align 1
  %v9.fca.5.gep = getelementptr inbounds nuw i8, ptr %v9_storage, i64 5
  store i8 %v9.unpack266, ptr %v9.fca.5.gep, align 1
  %v9.fca.6.gep = getelementptr inbounds nuw i8, ptr %v9_storage, i64 6
  store i8 %v9.unpack268, ptr %v9.fca.6.gep, align 1
  %v9.fca.7.gep = getelementptr inbounds nuw i8, ptr %v9_storage, i64 7
  store i8 %v9.unpack270, ptr %v9.fca.7.gep, align 1
  %v9.fca.8.gep = getelementptr inbounds nuw i8, ptr %v9_storage, i64 8
  store i8 %v9.unpack272, ptr %v9.fca.8.gep, align 1
  %v9.fca.9.gep = getelementptr inbounds nuw i8, ptr %v9_storage, i64 9
  store i8 %v9.unpack274, ptr %v9.fca.9.gep, align 1
  %v9.fca.10.gep = getelementptr inbounds nuw i8, ptr %v9_storage, i64 10
  store i8 %v9.unpack276, ptr %v9.fca.10.gep, align 1
  %v9.fca.11.gep = getelementptr inbounds nuw i8, ptr %v9_storage, i64 11
  store i8 %v9.unpack278, ptr %v9.fca.11.gep, align 1
  %v9.fca.12.gep = getelementptr inbounds nuw i8, ptr %v9_storage, i64 12
  store i8 %v9.unpack280, ptr %v9.fca.12.gep, align 1
  %v9.fca.13.gep = getelementptr inbounds nuw i8, ptr %v9_storage, i64 13
  store i8 %v9.unpack282, ptr %v9.fca.13.gep, align 1
  %v9.fca.14.gep = getelementptr inbounds nuw i8, ptr %v9_storage, i64 14
  store i8 %v9.unpack284, ptr %v9.fca.14.gep, align 1
  %v9.fca.15.gep = getelementptr inbounds nuw i8, ptr %v9_storage, i64 15
  store i8 %v9.unpack286, ptr %v9.fca.15.gep, align 1
  %v9.fca.16.gep = getelementptr inbounds nuw i8, ptr %v9_storage, i64 16
  store i8 %v9.unpack288, ptr %v9.fca.16.gep, align 1
  %v9.fca.17.gep = getelementptr inbounds nuw i8, ptr %v9_storage, i64 17
  store i8 %v9.unpack290, ptr %v9.fca.17.gep, align 1
  %v9.fca.18.gep = getelementptr inbounds nuw i8, ptr %v9_storage, i64 18
  store i8 %v9.unpack292, ptr %v9.fca.18.gep, align 1
  %v9.fca.19.gep = getelementptr inbounds nuw i8, ptr %v9_storage, i64 19
  store i8 %v9.unpack294, ptr %v9.fca.19.gep, align 1
  %v9.fca.20.gep = getelementptr inbounds nuw i8, ptr %v9_storage, i64 20
  store i8 %v9.unpack296, ptr %v9.fca.20.gep, align 1
  %v9.fca.21.gep = getelementptr inbounds nuw i8, ptr %v9_storage, i64 21
  store i8 %v9.unpack298, ptr %v9.fca.21.gep, align 1
  %v9.fca.22.gep = getelementptr inbounds nuw i8, ptr %v9_storage, i64 22
  store i8 %v9.unpack300, ptr %v9.fca.22.gep, align 1
  %v9.fca.23.gep = getelementptr inbounds nuw i8, ptr %v9_storage, i64 23
  store i8 %v9.unpack302, ptr %v9.fca.23.gep, align 1
  %v9.fca.24.gep = getelementptr inbounds nuw i8, ptr %v9_storage, i64 24
  store i8 %v9.unpack304, ptr %v9.fca.24.gep, align 1
  %v9.fca.25.gep = getelementptr inbounds nuw i8, ptr %v9_storage, i64 25
  store i8 %v9.unpack306, ptr %v9.fca.25.gep, align 1
  %v9.fca.26.gep = getelementptr inbounds nuw i8, ptr %v9_storage, i64 26
  store i8 %v9.unpack308, ptr %v9.fca.26.gep, align 1
  %v9.fca.27.gep = getelementptr inbounds nuw i8, ptr %v9_storage, i64 27
  store i8 %v9.unpack310, ptr %v9.fca.27.gep, align 1
  %v9.fca.28.gep = getelementptr inbounds nuw i8, ptr %v9_storage, i64 28
  store i8 %v9.unpack312, ptr %v9.fca.28.gep, align 1
  %v9.fca.29.gep = getelementptr inbounds nuw i8, ptr %v9_storage, i64 29
  store i8 %v9.unpack314, ptr %v9.fca.29.gep, align 1
  %v9.fca.30.gep = getelementptr inbounds nuw i8, ptr %v9_storage, i64 30
  store i8 %v9.unpack316, ptr %v9.fca.30.gep, align 1
  %v9.fca.31.gep = getelementptr inbounds nuw i8, ptr %v9_storage, i64 31
  store i8 %v9.unpack318, ptr %v9.fca.31.gep, align 1
  %v9.fca.32.gep = getelementptr inbounds nuw i8, ptr %v9_storage, i64 32
  store i8 %v9.unpack320, ptr %v9.fca.32.gep, align 1
  %v9.fca.33.gep = getelementptr inbounds nuw i8, ptr %v9_storage, i64 33
  store i8 %v9.unpack322, ptr %v9.fca.33.gep, align 1
  %v9.fca.34.gep = getelementptr inbounds nuw i8, ptr %v9_storage, i64 34
  store i8 %v9.unpack324, ptr %v9.fca.34.gep, align 1
  %v9.fca.35.gep = getelementptr inbounds nuw i8, ptr %v9_storage, i64 35
  store i8 %v9.unpack326, ptr %v9.fca.35.gep, align 1
  %v9.fca.36.gep = getelementptr inbounds nuw i8, ptr %v9_storage, i64 36
  store i8 %v9.unpack328, ptr %v9.fca.36.gep, align 1
  %v9.fca.37.gep = getelementptr inbounds nuw i8, ptr %v9_storage, i64 37
  store i8 %v9.unpack330, ptr %v9.fca.37.gep, align 1
  %v9.fca.38.gep = getelementptr inbounds nuw i8, ptr %v9_storage, i64 38
  store i8 %v9.unpack332, ptr %v9.fca.38.gep, align 1
  %v9.fca.39.gep = getelementptr inbounds nuw i8, ptr %v9_storage, i64 39
  store i8 %v9.unpack334, ptr %v9.fca.39.gep, align 1
  %v9.fca.40.gep = getelementptr inbounds nuw i8, ptr %v9_storage, i64 40
  store i8 %v9.unpack336, ptr %v9.fca.40.gep, align 1
  %v9.fca.41.gep = getelementptr inbounds nuw i8, ptr %v9_storage, i64 41
  store i8 %v9.unpack338, ptr %v9.fca.41.gep, align 1
  %v9.fca.42.gep = getelementptr inbounds nuw i8, ptr %v9_storage, i64 42
  store i8 %v9.unpack340, ptr %v9.fca.42.gep, align 1
  %v9.fca.43.gep = getelementptr inbounds nuw i8, ptr %v9_storage, i64 43
  store i8 %v9.unpack342, ptr %v9.fca.43.gep, align 1
  %v9.fca.44.gep = getelementptr inbounds nuw i8, ptr %v9_storage, i64 44
  store i8 %v9.unpack344, ptr %v9.fca.44.gep, align 1
  %v9.fca.45.gep = getelementptr inbounds nuw i8, ptr %v9_storage, i64 45
  store i8 %v9.unpack346, ptr %v9.fca.45.gep, align 1
  %v9.fca.46.gep = getelementptr inbounds nuw i8, ptr %v9_storage, i64 46
  store i8 %v9.unpack348, ptr %v9.fca.46.gep, align 1
  %v9.fca.47.gep = getelementptr inbounds nuw i8, ptr %v9_storage, i64 47
  store i8 %v9.unpack350, ptr %v9.fca.47.gep, align 1
  %v9.fca.48.gep = getelementptr inbounds nuw i8, ptr %v9_storage, i64 48
  store i8 %v9.unpack352, ptr %v9.fca.48.gep, align 1
  %v9.fca.49.gep = getelementptr inbounds nuw i8, ptr %v9_storage, i64 49
  store i8 %v9.unpack354, ptr %v9.fca.49.gep, align 1
  %v9.fca.50.gep = getelementptr inbounds nuw i8, ptr %v9_storage, i64 50
  store i8 %v9.unpack356, ptr %v9.fca.50.gep, align 1
  %v9.fca.51.gep = getelementptr inbounds nuw i8, ptr %v9_storage, i64 51
  store i8 %v9.unpack358, ptr %v9.fca.51.gep, align 1
  %v9.fca.52.gep = getelementptr inbounds nuw i8, ptr %v9_storage, i64 52
  store i8 %v9.unpack360, ptr %v9.fca.52.gep, align 1
  %v9.fca.53.gep = getelementptr inbounds nuw i8, ptr %v9_storage, i64 53
  store i8 %v9.unpack362, ptr %v9.fca.53.gep, align 1
  %v9.fca.54.gep = getelementptr inbounds nuw i8, ptr %v9_storage, i64 54
  store i8 %v9.unpack364, ptr %v9.fca.54.gep, align 1
  %v9.fca.55.gep = getelementptr inbounds nuw i8, ptr %v9_storage, i64 55
  store i8 %v9.unpack366, ptr %v9.fca.55.gep, align 1
  %v9.fca.56.gep = getelementptr inbounds nuw i8, ptr %v9_storage, i64 56
  store i8 %v9.unpack368, ptr %v9.fca.56.gep, align 1
  %v9.fca.57.gep = getelementptr inbounds nuw i8, ptr %v9_storage, i64 57
  store i8 %v9.unpack370, ptr %v9.fca.57.gep, align 1
  %v9.fca.58.gep = getelementptr inbounds nuw i8, ptr %v9_storage, i64 58
  store i8 %v9.unpack372, ptr %v9.fca.58.gep, align 1
  %v9.fca.59.gep = getelementptr inbounds nuw i8, ptr %v9_storage, i64 59
  store i8 %v9.unpack374, ptr %v9.fca.59.gep, align 1
  %v9.fca.60.gep = getelementptr inbounds nuw i8, ptr %v9_storage, i64 60
  store i8 %v9.unpack376, ptr %v9.fca.60.gep, align 1
  %v9.fca.61.gep = getelementptr inbounds nuw i8, ptr %v9_storage, i64 61
  store i8 %v9.unpack378, ptr %v9.fca.61.gep, align 1
  %v9.fca.62.gep = getelementptr inbounds nuw i8, ptr %v9_storage, i64 62
  store i8 %v9.unpack380, ptr %v9.fca.62.gep, align 1
  %v9.fca.63.gep = getelementptr inbounds nuw i8, ptr %v9_storage, i64 63
  store i8 %v9.unpack382, ptr %v9.fca.63.gep, align 1
  %v10_invalid = icmp ugt i32 %v8_pair, 63
  br i1 %v10_invalid, label %v10_trap, label %v10_ok

v10_trap:                                         ; preds = %b2
  tail call void @llvm.trap()
  unreachable

v10_ok:                                           ; preds = %b2
  %v10_offset = zext nneg i32 %v8_pair to i64
  %v10_ptr = getelementptr [64 x i8], ptr %v9_storage, i64 0, i64 %v10_offset
  %v10 = load i8, ptr %v10_ptr, align 1
  %v12 = icmp eq i8 %v10, 1
  br i1 %v12, label %b8_to_b9, label %b3

b3:                                               ; preds = %v10_ok
  store i8 %v9.unpack, ptr %v14_storage, align 1
  %v14.fca.1.gep = getelementptr inbounds nuw i8, ptr %v14_storage, i64 1
  store i8 %v9.unpack258, ptr %v14.fca.1.gep, align 1
  %v14.fca.2.gep = getelementptr inbounds nuw i8, ptr %v14_storage, i64 2
  store i8 %v9.unpack260, ptr %v14.fca.2.gep, align 1
  %v14.fca.3.gep = getelementptr inbounds nuw i8, ptr %v14_storage, i64 3
  store i8 %v9.unpack262, ptr %v14.fca.3.gep, align 1
  %v14.fca.4.gep = getelementptr inbounds nuw i8, ptr %v14_storage, i64 4
  store i8 %v9.unpack264, ptr %v14.fca.4.gep, align 1
  %v14.fca.5.gep = getelementptr inbounds nuw i8, ptr %v14_storage, i64 5
  store i8 %v9.unpack266, ptr %v14.fca.5.gep, align 1
  %v14.fca.6.gep = getelementptr inbounds nuw i8, ptr %v14_storage, i64 6
  store i8 %v9.unpack268, ptr %v14.fca.6.gep, align 1
  %v14.fca.7.gep = getelementptr inbounds nuw i8, ptr %v14_storage, i64 7
  store i8 %v9.unpack270, ptr %v14.fca.7.gep, align 1
  %v14.fca.8.gep = getelementptr inbounds nuw i8, ptr %v14_storage, i64 8
  store i8 %v9.unpack272, ptr %v14.fca.8.gep, align 1
  %v14.fca.9.gep = getelementptr inbounds nuw i8, ptr %v14_storage, i64 9
  store i8 %v9.unpack274, ptr %v14.fca.9.gep, align 1
  %v14.fca.10.gep = getelementptr inbounds nuw i8, ptr %v14_storage, i64 10
  store i8 %v9.unpack276, ptr %v14.fca.10.gep, align 1
  %v14.fca.11.gep = getelementptr inbounds nuw i8, ptr %v14_storage, i64 11
  store i8 %v9.unpack278, ptr %v14.fca.11.gep, align 1
  %v14.fca.12.gep = getelementptr inbounds nuw i8, ptr %v14_storage, i64 12
  store i8 %v9.unpack280, ptr %v14.fca.12.gep, align 1
  %v14.fca.13.gep = getelementptr inbounds nuw i8, ptr %v14_storage, i64 13
  store i8 %v9.unpack282, ptr %v14.fca.13.gep, align 1
  %v14.fca.14.gep = getelementptr inbounds nuw i8, ptr %v14_storage, i64 14
  store i8 %v9.unpack284, ptr %v14.fca.14.gep, align 1
  %v14.fca.15.gep = getelementptr inbounds nuw i8, ptr %v14_storage, i64 15
  store i8 %v9.unpack286, ptr %v14.fca.15.gep, align 1
  %v14.fca.16.gep = getelementptr inbounds nuw i8, ptr %v14_storage, i64 16
  store i8 %v9.unpack288, ptr %v14.fca.16.gep, align 1
  %v14.fca.17.gep = getelementptr inbounds nuw i8, ptr %v14_storage, i64 17
  store i8 %v9.unpack290, ptr %v14.fca.17.gep, align 1
  %v14.fca.18.gep = getelementptr inbounds nuw i8, ptr %v14_storage, i64 18
  store i8 %v9.unpack292, ptr %v14.fca.18.gep, align 1
  %v14.fca.19.gep = getelementptr inbounds nuw i8, ptr %v14_storage, i64 19
  store i8 %v9.unpack294, ptr %v14.fca.19.gep, align 1
  %v14.fca.20.gep = getelementptr inbounds nuw i8, ptr %v14_storage, i64 20
  store i8 %v9.unpack296, ptr %v14.fca.20.gep, align 1
  %v14.fca.21.gep = getelementptr inbounds nuw i8, ptr %v14_storage, i64 21
  store i8 %v9.unpack298, ptr %v14.fca.21.gep, align 1
  %v14.fca.22.gep = getelementptr inbounds nuw i8, ptr %v14_storage, i64 22
  store i8 %v9.unpack300, ptr %v14.fca.22.gep, align 1
  %v14.fca.23.gep = getelementptr inbounds nuw i8, ptr %v14_storage, i64 23
  store i8 %v9.unpack302, ptr %v14.fca.23.gep, align 1
  %v14.fca.24.gep = getelementptr inbounds nuw i8, ptr %v14_storage, i64 24
  store i8 %v9.unpack304, ptr %v14.fca.24.gep, align 1
  %v14.fca.25.gep = getelementptr inbounds nuw i8, ptr %v14_storage, i64 25
  store i8 %v9.unpack306, ptr %v14.fca.25.gep, align 1
  %v14.fca.26.gep = getelementptr inbounds nuw i8, ptr %v14_storage, i64 26
  store i8 %v9.unpack308, ptr %v14.fca.26.gep, align 1
  %v14.fca.27.gep = getelementptr inbounds nuw i8, ptr %v14_storage, i64 27
  store i8 %v9.unpack310, ptr %v14.fca.27.gep, align 1
  %v14.fca.28.gep = getelementptr inbounds nuw i8, ptr %v14_storage, i64 28
  store i8 %v9.unpack312, ptr %v14.fca.28.gep, align 1
  %v14.fca.29.gep = getelementptr inbounds nuw i8, ptr %v14_storage, i64 29
  store i8 %v9.unpack314, ptr %v14.fca.29.gep, align 1
  %v14.fca.30.gep = getelementptr inbounds nuw i8, ptr %v14_storage, i64 30
  store i8 %v9.unpack316, ptr %v14.fca.30.gep, align 1
  %v14.fca.31.gep = getelementptr inbounds nuw i8, ptr %v14_storage, i64 31
  store i8 %v9.unpack318, ptr %v14.fca.31.gep, align 1
  %v14.fca.32.gep = getelementptr inbounds nuw i8, ptr %v14_storage, i64 32
  store i8 %v9.unpack320, ptr %v14.fca.32.gep, align 1
  %v14.fca.33.gep = getelementptr inbounds nuw i8, ptr %v14_storage, i64 33
  store i8 %v9.unpack322, ptr %v14.fca.33.gep, align 1
  %v14.fca.34.gep = getelementptr inbounds nuw i8, ptr %v14_storage, i64 34
  store i8 %v9.unpack324, ptr %v14.fca.34.gep, align 1
  %v14.fca.35.gep = getelementptr inbounds nuw i8, ptr %v14_storage, i64 35
  store i8 %v9.unpack326, ptr %v14.fca.35.gep, align 1
  %v14.fca.36.gep = getelementptr inbounds nuw i8, ptr %v14_storage, i64 36
  store i8 %v9.unpack328, ptr %v14.fca.36.gep, align 1
  %v14.fca.37.gep = getelementptr inbounds nuw i8, ptr %v14_storage, i64 37
  store i8 %v9.unpack330, ptr %v14.fca.37.gep, align 1
  %v14.fca.38.gep = getelementptr inbounds nuw i8, ptr %v14_storage, i64 38
  store i8 %v9.unpack332, ptr %v14.fca.38.gep, align 1
  %v14.fca.39.gep = getelementptr inbounds nuw i8, ptr %v14_storage, i64 39
  store i8 %v9.unpack334, ptr %v14.fca.39.gep, align 1
  %v14.fca.40.gep = getelementptr inbounds nuw i8, ptr %v14_storage, i64 40
  store i8 %v9.unpack336, ptr %v14.fca.40.gep, align 1
  %v14.fca.41.gep = getelementptr inbounds nuw i8, ptr %v14_storage, i64 41
  store i8 %v9.unpack338, ptr %v14.fca.41.gep, align 1
  %v14.fca.42.gep = getelementptr inbounds nuw i8, ptr %v14_storage, i64 42
  store i8 %v9.unpack340, ptr %v14.fca.42.gep, align 1
  %v14.fca.43.gep = getelementptr inbounds nuw i8, ptr %v14_storage, i64 43
  store i8 %v9.unpack342, ptr %v14.fca.43.gep, align 1
  %v14.fca.44.gep = getelementptr inbounds nuw i8, ptr %v14_storage, i64 44
  store i8 %v9.unpack344, ptr %v14.fca.44.gep, align 1
  %v14.fca.45.gep = getelementptr inbounds nuw i8, ptr %v14_storage, i64 45
  store i8 %v9.unpack346, ptr %v14.fca.45.gep, align 1
  %v14.fca.46.gep = getelementptr inbounds nuw i8, ptr %v14_storage, i64 46
  store i8 %v9.unpack348, ptr %v14.fca.46.gep, align 1
  %v14.fca.47.gep = getelementptr inbounds nuw i8, ptr %v14_storage, i64 47
  store i8 %v9.unpack350, ptr %v14.fca.47.gep, align 1
  %v14.fca.48.gep = getelementptr inbounds nuw i8, ptr %v14_storage, i64 48
  store i8 %v9.unpack352, ptr %v14.fca.48.gep, align 1
  %v14.fca.49.gep = getelementptr inbounds nuw i8, ptr %v14_storage, i64 49
  store i8 %v9.unpack354, ptr %v14.fca.49.gep, align 1
  %v14.fca.50.gep = getelementptr inbounds nuw i8, ptr %v14_storage, i64 50
  store i8 %v9.unpack356, ptr %v14.fca.50.gep, align 1
  %v14.fca.51.gep = getelementptr inbounds nuw i8, ptr %v14_storage, i64 51
  store i8 %v9.unpack358, ptr %v14.fca.51.gep, align 1
  %v14.fca.52.gep = getelementptr inbounds nuw i8, ptr %v14_storage, i64 52
  store i8 %v9.unpack360, ptr %v14.fca.52.gep, align 1
  %v14.fca.53.gep = getelementptr inbounds nuw i8, ptr %v14_storage, i64 53
  store i8 %v9.unpack362, ptr %v14.fca.53.gep, align 1
  %v14.fca.54.gep = getelementptr inbounds nuw i8, ptr %v14_storage, i64 54
  store i8 %v9.unpack364, ptr %v14.fca.54.gep, align 1
  %v14.fca.55.gep = getelementptr inbounds nuw i8, ptr %v14_storage, i64 55
  store i8 %v9.unpack366, ptr %v14.fca.55.gep, align 1
  %v14.fca.56.gep = getelementptr inbounds nuw i8, ptr %v14_storage, i64 56
  store i8 %v9.unpack368, ptr %v14.fca.56.gep, align 1
  %v14.fca.57.gep = getelementptr inbounds nuw i8, ptr %v14_storage, i64 57
  store i8 %v9.unpack370, ptr %v14.fca.57.gep, align 1
  %v14.fca.58.gep = getelementptr inbounds nuw i8, ptr %v14_storage, i64 58
  store i8 %v9.unpack372, ptr %v14.fca.58.gep, align 1
  %v14.fca.59.gep = getelementptr inbounds nuw i8, ptr %v14_storage, i64 59
  store i8 %v9.unpack374, ptr %v14.fca.59.gep, align 1
  %v14.fca.60.gep = getelementptr inbounds nuw i8, ptr %v14_storage, i64 60
  store i8 %v9.unpack376, ptr %v14.fca.60.gep, align 1
  %v14.fca.61.gep = getelementptr inbounds nuw i8, ptr %v14_storage, i64 61
  store i8 %v9.unpack378, ptr %v14.fca.61.gep, align 1
  %v14.fca.62.gep = getelementptr inbounds nuw i8, ptr %v14_storage, i64 62
  store i8 %v9.unpack380, ptr %v14.fca.62.gep, align 1
  %v14.fca.63.gep = getelementptr inbounds nuw i8, ptr %v14_storage, i64 63
  store i8 %v9.unpack382, ptr %v14.fca.63.gep, align 1
  %v15_ptr = getelementptr [64 x i8], ptr %v14_storage, i64 0, i64 %v10_offset
  %v15 = load i8, ptr %v15_ptr, align 1
  %v17 = icmp eq i8 %v15, 3
  %spec.select = select i1 %v17, ptr %v22_scratch, ptr %v27_scratch
  %spec.select1351 = select i1 %v17, i8 2, i8 7
  br label %b8_to_b9

b9:                                               ; preds = %b8_to_b9, %b1
  %v29_mem.sroa.0.sink = phi ptr [ %v29_mem.sroa.0, %b8_to_b9 ], [ %p0, %b1 ]
  %v29_mem.sroa.131.sroa.4.sink = phi ptr [ %v29_mem.sroa.131.sroa.4, %b8_to_b9 ], [ %v5_mem.sroa.68.0.p0.sroa_idx, %b1 ]
  %v30_mem.sroa.131.sroa.3.sroa.0.0 = phi i8 [ %16, %b8_to_b9 ], [ %v5_mem.sroa.67.sroa.0.0.v5_mem.sroa.67.sroa.0.0.v5_mem.sroa.67.sroa.0.0., %b1 ]
  %v30_mem.sroa.131.sroa.0.0 = phi i32 [ %v23_mem.sroa.130.sroa.0.0.copyload, %b8_to_b9 ], [ 0, %b1 ]
  %4 = phi <16 x i8> [ %12, %b8_to_b9 ], [ %0, %b1 ]
  %5 = phi <16 x i8> [ %13, %b8_to_b9 ], [ %1, %b1 ]
  %6 = phi <16 x i8> [ %14, %b8_to_b9 ], [ %2, %b1 ]
  %7 = phi <16 x i8> [ %15, %b8_to_b9 ], [ %3, %b1 ]
  call void @llvm.memcpy.p0.p0.i64(ptr noundef nonnull align 8 dereferenceable(56) %v30_mem.sroa.0, ptr noundef nonnull align 1 dereferenceable(56) %v29_mem.sroa.0.sink, i64 56, i1 false)
  call void @llvm.memcpy.p0.p0.i64(ptr noundef nonnull align 1 dereferenceable(59) %v30_mem.sroa.131.sroa.5, ptr noundef nonnull align 1 dereferenceable(59) %v29_mem.sroa.131.sroa.4.sink, i64 59, i1 false)
  call void @llvm.memcpy.p0.p0.i64(ptr noundef nonnull align 8 dereferenceable(56) %return_storage, ptr noundef nonnull align 8 dereferenceable(56) %v30_mem.sroa.0, i64 56, i1 false)
  %v30_mem.sroa.3.0.return_storage.sroa_idx = getelementptr inbounds nuw i8, ptr %return_storage, i64 56
  store <16 x i8> %4, ptr %v30_mem.sroa.3.0.return_storage.sroa_idx, align 8
  %v30_mem.sroa.35.0.return_storage.sroa_idx = getelementptr inbounds nuw i8, ptr %return_storage, i64 72
  store <16 x i8> %5, ptr %v30_mem.sroa.35.0.return_storage.sroa_idx, align 8
  %v30_mem.sroa.67.0.return_storage.sroa_idx = getelementptr inbounds nuw i8, ptr %return_storage, i64 88
  store <16 x i8> %6, ptr %v30_mem.sroa.67.0.return_storage.sroa_idx, align 8
  %v30_mem.sroa.99.0.return_storage.sroa_idx = getelementptr inbounds nuw i8, ptr %return_storage, i64 104
  store <16 x i8> %7, ptr %v30_mem.sroa.99.0.return_storage.sroa_idx, align 8
  %v30_mem.sroa.131.0.return_storage.sroa_idx = getelementptr inbounds nuw i8, ptr %return_storage, i64 120
  store i32 %v30_mem.sroa.131.sroa.0.0, ptr %v30_mem.sroa.131.0.return_storage.sroa_idx, align 8
  %v30_mem.sroa.131.sroa.3.0.v30_mem.sroa.131.0.return_storage.sroa_idx.sroa_idx = getelementptr inbounds nuw i8, ptr %return_storage, i64 124
  store i8 %v30_mem.sroa.131.sroa.3.sroa.0.0, ptr %v30_mem.sroa.131.sroa.3.0.v30_mem.sroa.131.0.return_storage.sroa_idx.sroa_idx, align 4
  %v30_mem.sroa.131.sroa.5.0.v30_mem.sroa.131.0.return_storage.sroa_idx.sroa_idx = getelementptr inbounds nuw i8, ptr %return_storage, i64 125
  call void @llvm.memcpy.p0.p0.i64(ptr noundef nonnull align 1 dereferenceable(59) %v30_mem.sroa.131.sroa.5.0.v30_mem.sroa.131.0.return_storage.sroa_idx.sroa_idx, ptr noundef nonnull align 1 dereferenceable(59) %v30_mem.sroa.131.sroa.5, i64 59, i1 false)
  ret void

b8_to_b9:                                         ; preds = %b3, %v10_ok
  %v22_scratch.sink1350 = phi ptr [ %v22_scratch, %v10_ok ], [ %spec.select, %b3 ]
  %.sink = phi i8 [ 2, %v10_ok ], [ %spec.select1351, %b3 ]
  %8 = load <16 x i8>, ptr %v9_ptr, align 1
  store <16 x i8> %8, ptr %v22_scratch.sink1350, align 1
  %v19.fca.16.gep162 = getelementptr inbounds nuw i8, ptr %v22_scratch.sink1350, i64 16
  %9 = load <16 x i8>, ptr %v9.elt287, align 1
  store <16 x i8> %9, ptr %v19.fca.16.gep162, align 1
  %v19.fca.32.gep194 = getelementptr inbounds nuw i8, ptr %v22_scratch.sink1350, i64 32
  %10 = load <16 x i8>, ptr %v9.elt319, align 1
  store <16 x i8> %10, ptr %v19.fca.32.gep194, align 1
  %v19.fca.48.gep226 = getelementptr inbounds nuw i8, ptr %v22_scratch.sink1350, i64 48
  %11 = load <16 x i8>, ptr %v9.elt351, align 1
  store <16 x i8> %11, ptr %v19.fca.48.gep226, align 1
  %v22_ptr = getelementptr [64 x i8], ptr %v22_scratch.sink1350, i64 0, i64 %v10_offset
  store i8 %.sink, ptr %v22_ptr, align 1
  %12 = load <16 x i8>, ptr %v22_scratch.sink1350, align 1
  %13 = load <16 x i8>, ptr %v19.fca.16.gep162, align 1
  %14 = load <16 x i8>, ptr %v19.fca.32.gep194, align 1
  %15 = load <16 x i8>, ptr %v19.fca.48.gep226, align 1
  %v23_mem.sroa.130.sroa.0.0.copyload = load i32, ptr %v0_ptr, align 1
  %v23_mem.sroa.130.sroa.2.0.v23_mem.sroa.130.0.p0.sroa_idx.sroa_idx = getelementptr i8, ptr %p0, i64 124
  %16 = load i8, ptr %v23_mem.sroa.130.sroa.2.0.v23_mem.sroa.130.0.p0.sroa_idx.sroa_idx, align 1
  %v23_mem.sroa.130.sroa.3.0.v23_mem.sroa.130.0.p0.sroa_idx.sroa_idx = getelementptr i8, ptr %p0, i64 125
  call void @llvm.memcpy.p0.p0.i64(ptr noundef nonnull align 8 dereferenceable(56) %v29_mem.sroa.0, ptr noundef nonnull align 1 dereferenceable(56) %p0, i64 56, i1 false)
  call void @llvm.memcpy.p0.p0.i64(ptr noundef nonnull align 1 dereferenceable(59) %v29_mem.sroa.131.sroa.4, ptr noundef nonnull align 1 dereferenceable(59) %v23_mem.sroa.130.sroa.3.0.v23_mem.sroa.130.0.p0.sroa_idx.sroa_idx, i64 59, i1 false)
  br label %b9
}

; Function Attrs: mustprogress nofree norecurse nosync nounwind willreturn memory(none)
define noundef i1 @liza___liza_json_space(i8 %p0) local_unnamed_addr #6 {
b0:
  %0 = icmp ult i8 %p0, 33
  %switch.cast = zext nneg i8 %p0 to i33
  %switch.downshift = lshr i33 -4294957568, %switch.cast
  %switch.masked = trunc i33 %switch.downshift to i1
  %v13 = select i1 %0, i1 %switch.masked, i1 false
  ret i1 %v13
}

; Function Attrs: mustprogress nofree norecurse nosync nounwind willreturn memory(none)
define i1 @liza___liza_json_digit(i8 %p0) local_unnamed_addr #6 {
b0:
  %0 = add i8 %p0, -48
  %v5 = icmp ult i8 %0, 10
  ret i1 %v5
}

; Function Attrs: mustprogress nofree norecurse nosync nounwind willreturn memory(none)
define range(i32 0, 17) i32 @liza___liza_json_hex(i8 %p0) local_unnamed_addr #6 {
b0:
  %0 = add i8 %p0, -48
  %v5 = icmp ult i8 %0, 10
  br i1 %v5, label %v6_ok, label %b6

v6_ok:                                            ; preds = %b0
  %v6 = zext nneg i8 %p0 to i32
  %v8_pair = add nsw i32 %v6, -48
  br label %common.ret

common.ret:                                       ; preds = %v24_ok, %v15_ok, %v6_ok, %b12
  %common.ret.op = phi i32 [ %v8_pair, %v6_ok ], [ %v17_pair, %v15_ok ], [ %v26_pair, %v24_ok ], [ 16, %b12 ]
  ret i32 %common.ret.op

b6:                                               ; preds = %b0
  %1 = add i8 %p0, -65
  %v14 = icmp ult i8 %1, 6
  br i1 %v14, label %v15_ok, label %b12

v15_ok:                                           ; preds = %b6
  %v15 = zext nneg i8 %p0 to i32
  %v17_pair = add nsw i32 %v15, -55
  br label %common.ret

b12:                                              ; preds = %b6
  %2 = add i8 %p0, -97
  %v23 = icmp ult i8 %2, 6
  br i1 %v23, label %v24_ok, label %common.ret

v24_ok:                                           ; preds = %b12
  %v24 = zext nneg i8 %p0 to i32
  %v26_pair = add nsw i32 %v24, -87
  br label %common.ret
}

; Function Attrs: nounwind memory(readwrite, inaccessiblemem: write)
define void @liza___liza_json_step(ptr writeonly sret(%struct.JsonState) captures(none) %return_storage, ptr readonly captures(none) %p0, i8 %p1) local_unnamed_addr #3 {
b0:
  %v12_mem = alloca %struct.JsonState, align 8
  %v20_scratch = alloca [64 x i8], align 16
  %v22_mem = alloca %struct.JsonState, align 8
  %v31_mem.sroa.0.sroa.0 = alloca %struct.Utf8StreamState, align 8
  %v31_mem.sroa.0.sroa.5 = alloca { [64 x i8], i32, i1 }, align 8
  %v31_mem.sroa.0.sroa.9 = alloca { i1, i32, i32, i32, i32 }, align 8
  %v31_mem.sroa.5 = alloca { i64, i32, i64 }, align 8
  %v67_mem.sroa.3 = alloca [52 x i8], align 4
  %v78_mem.sroa.0.sroa.0.sroa.3 = alloca [12 x i8], align 8
  %v78_mem.sroa.3 = alloca { i64, i64, i32, i64 }, align 8
  %v92_mem.sroa.3 = alloca [52 x i8], align 4
  %v109_mem.sroa.0.sroa.0.sroa.3 = alloca [12 x i8], align 8
  %v109_mem.sroa.3 = alloca { i64, i64, i32, i64 }, align 8
  %v151_mem.sroa.0.sroa.3 = alloca { i1, i32, i32 }, align 8
  %v154_mem.sroa.3.sroa.0 = alloca [12 x i8], align 4
  %v168_mem.sroa.0.sroa.3.sroa.0 = alloca { i1, i32, i32 }, align 8
  %v179_mem.sroa.0.sroa.3 = alloca { i1, i32, i32 }, align 8
  %v183_mem.sroa.0 = alloca { %struct.Utf8StreamState, i64, [64 x i8], i32, i1 }, align 8
  %v183_mem.sroa.5.sroa.0 = alloca [12 x i8], align 4
  %v252_mem.sroa.4 = alloca { i32, i32, i64, i64, i32, i64 }, align 8
  %v257_mem = alloca %struct.JsonState, align 8
  %v258_mem = alloca %struct.JsonState, align 8
  %v285_mem.sroa.0 = alloca { %struct.Utf8StreamState, i64, [64 x i8], i32, i1 }, align 8
  %v285_mem.sroa.4 = alloca [52 x i8], align 4
  %v286_mem.sroa.0 = alloca { %struct.Utf8StreamState, i64, [64 x i8], i32, i1 }, align 8
  %v286_mem.sroa.7 = alloca [52 x i8], align 4
  %v293_mem.sroa.0 = alloca { %struct.Utf8StreamState, i64, [64 x i8], i32, i1 }, align 8
  %v293_mem.sroa.7 = alloca [52 x i8], align 4
  %v305_mem.sroa.0 = alloca { %struct.Utf8StreamState, i64, [64 x i8], i32, i1 }, align 8
  %v305_mem.sroa.5 = alloca [52 x i8], align 4
  %v320_mem.sroa.3 = alloca [52 x i8], align 4
  %v344_mem.sroa.3 = alloca [52 x i8], align 4
  %v358_mem.sroa.3 = alloca [52 x i8], align 4
  %v399_mem = alloca %struct.JsonState, align 8
  %v401_mem = alloca %struct.JsonState, align 8
  %v401_next = alloca %struct.JsonState, align 8
  %v462_scratch = alloca [64 x i8], align 1
  %v470_scratch = alloca [64 x i8], align 1
  %v472_mem.sroa.0 = alloca { %struct.Utf8StreamState, i64 }, align 8
  %v472_mem.sroa.131 = alloca { i32, i1, i32, i1, i32, i32, i32, i32, i64, i64, i32, i64 }, align 8
  %v486_scratch = alloca [64 x i8], align 16
  %v501_mem.sroa.3.sroa.0 = alloca i8, align 4
  %v526_mem = alloca %struct.JsonState, align 8
  %v533_scratch = alloca [64 x i8], align 1
  %v539_scratch = alloca [64 x i8], align 1
  %v541_mem.sroa.0.sroa.0 = alloca { %struct.Utf8StreamState, i64 }, align 8
  %v541_mem.sroa.5 = alloca [60 x i8], align 4
  %v551_mem.sroa.3.sroa.0 = alloca i8, align 4
  %v569_mem.sroa.0 = alloca { %struct.Utf8StreamState, i64, [64 x i8], i32, i1 }, align 8
  %v569_mem.sroa.5 = alloca [52 x i8], align 4
  %v599_mem.sroa.0.sroa.0 = alloca { %struct.Utf8StreamState, i64, [64 x i8], i32, i1 }, align 8
  %v599_mem.sroa.5.sroa.3 = alloca [40 x i8], align 4
  %v600_mem.sroa.0.sroa.0 = alloca { %struct.Utf8StreamState, i64, [64 x i8], i32, i1 }, align 8
  %v600_mem.sroa.5.sroa.3 = alloca [40 x i8], align 4
  %v407_storage = alloca [64 x i8], align 16
  %v0_ptr = getelementptr i8, ptr %p0, i64 128
  %v0 = load i32, ptr %v0_ptr, align 4
  %v533_scratch.sink2398.sroa.gep = getelementptr inbounds nuw i8, ptr %v533_scratch, i64 16
  %v533_scratch.sink2398.sroa.gep2400 = getelementptr inbounds nuw i8, ptr %v539_scratch, i64 16
  %v533_scratch.sink2398.sroa.gep2402 = getelementptr inbounds nuw i8, ptr %v533_scratch, i64 32
  %v533_scratch.sink2398.sroa.gep2403 = getelementptr inbounds nuw i8, ptr %v539_scratch, i64 32
  %v533_scratch.sink2398.sroa.gep2405 = getelementptr inbounds nuw i8, ptr %v533_scratch, i64 48
  %v533_scratch.sink2398.sroa.gep2406 = getelementptr inbounds nuw i8, ptr %v539_scratch, i64 48
  %v470_scratch.sink2269.sroa.gep = getelementptr inbounds nuw i8, ptr %v462_scratch, i64 16
  %v470_scratch.sink2269.sroa.gep2407 = getelementptr inbounds nuw i8, ptr %v470_scratch, i64 16
  %v470_scratch.sink2269.sroa.gep2409 = getelementptr inbounds nuw i8, ptr %v462_scratch, i64 32
  %v470_scratch.sink2269.sroa.gep2410 = getelementptr inbounds nuw i8, ptr %v470_scratch, i64 32
  %v470_scratch.sink2269.sroa.gep2412 = getelementptr inbounds nuw i8, ptr %v462_scratch, i64 48
  %v470_scratch.sink2269.sroa.gep2413 = getelementptr inbounds nuw i8, ptr %v470_scratch, i64 48
  switch i32 %v0, label %b132 [
    i32 1, label %b1
    i32 2, label %b16
    i32 4, label %b46
    i32 5, label %b52
    i32 3, label %b61
    i32 6, label %b61
    i32 20, label %b91
  ]

b1:                                               ; preds = %b0
  %v4 = icmp ult i8 %p1, 32
  br i1 %v4, label %b3, label %b5

common.ret:                                       ; preds = %b312, %b311, %b292, %b289, %b286, %v545_ok, %b279, %b271, %b266, %b264, %v484_ok, %b255, %b251, %b246, %v441_ok, %v426_ok, %b217, %b210, %b201, %b189, %b180, %b165, %b157, %b140, %b131, %b129, %b126, %b89, %b86, %b80, %b75, %b73, %b63, %b56, %b54, %b50, %b48, %b44, %b42, %b39, %b14, %b10, %v18_ok, %b3
  ret void

b3:                                               ; preds = %b1
  %v6_ptr = getelementptr i8, ptr %p0, i64 48
  %v6 = load i64, ptr %v6_ptr, align 8
  %v1_mem.sroa.3.0.p0.sroa_idx.i = getelementptr inbounds nuw i8, ptr %p0, i64 172
  %v1_mem.sroa.3.0.copyload.i = load i32, ptr %v1_mem.sroa.3.0.p0.sroa_idx.i, align 1
  tail call void @llvm.memmove.p0.p0.i64(ptr noundef nonnull align 8 dereferenceable(168) %return_storage, ptr noundef nonnull align 1 dereferenceable(168) %p0, i64 168, i1 false)
  %v7_mem.sroa.2.0.return_storage.sroa_idx = getelementptr inbounds nuw i8, ptr %return_storage, i64 168
  store i32 1, ptr %v7_mem.sroa.2.0.return_storage.sroa_idx, align 8
  %v7_mem.sroa.3.0.return_storage.sroa_idx = getelementptr inbounds nuw i8, ptr %return_storage, i64 172
  store i32 %v1_mem.sroa.3.0.copyload.i, ptr %v7_mem.sroa.3.0.return_storage.sroa_idx, align 4
  %v7_mem.sroa.4.0.return_storage.sroa_idx = getelementptr inbounds nuw i8, ptr %return_storage, i64 176
  store i64 %v6, ptr %v7_mem.sroa.4.0.return_storage.sroa_idx, align 8
  br label %common.ret

b5:                                               ; preds = %b1
  switch i8 %p1, label %b13_to_b14 [
    i8 34, label %b6
    i8 92, label %b12
  ]

b6:                                               ; preds = %b5
  call void @llvm.memcpy.p0.p0.i64(ptr noundef nonnull align 8 dereferenceable(184) %v12_mem, ptr noundef nonnull align 1 dereferenceable(184) %p0, i64 184, i1 false)
  %v12_part = getelementptr inbounds nuw i8, ptr %v12_mem, i64 128
  store i32 0, ptr %v12_part, align 8
  %v13_ptr = getelementptr inbounds nuw i8, ptr %v12_mem, i64 132
  %v13 = load i1, ptr %v13_ptr, align 4
  br i1 %v13, label %b8, label %b10

b8:                                               ; preds = %b6
  %v14_ptr = getelementptr inbounds nuw i8, ptr %v12_mem, i64 56
  %0 = load <16 x i8>, ptr %v14_ptr, align 8
  %v14.fca.16.gep1184 = getelementptr inbounds nuw i8, ptr %v12_mem, i64 72
  %1 = load <16 x i8>, ptr %v14.fca.16.gep1184, align 8
  %v14.fca.32.gep1200 = getelementptr inbounds nuw i8, ptr %v12_mem, i64 88
  %2 = load <16 x i8>, ptr %v14.fca.32.gep1200, align 8
  %v14.fca.48.gep1216 = getelementptr inbounds nuw i8, ptr %v12_mem, i64 104
  %3 = load <16 x i8>, ptr %v14.fca.48.gep1216, align 8
  %v15_ptr = getelementptr inbounds nuw i8, ptr %v12_mem, i64 120
  %v15 = load i32, ptr %v15_ptr, align 8
  %v17_pair = tail call { i32, i1 } @llvm.usub.with.overflow.i32(i32 %v15, i32 1)
  %v17 = extractvalue { i32, i1 } %v17_pair, 0
  %v17_overflow = extractvalue { i32, i1 } %v17_pair, 1
  br i1 %v17_overflow, label %v17_trap, label %v17_ok

v17_trap:                                         ; preds = %b8
  tail call void @llvm.trap()
  unreachable

v17_ok:                                           ; preds = %b8
  %v18_invalid = icmp ugt i32 %v17, 63
  br i1 %v18_invalid, label %v18_trap, label %v18_ok

v18_trap:                                         ; preds = %v17_ok
  tail call void @llvm.trap()
  unreachable

v18_ok:                                           ; preds = %v17_ok
  %v18_offset = zext nneg i32 %v17 to i64
  store <16 x i8> %0, ptr %v20_scratch, align 16
  %v14.fca.16.gep1073 = getelementptr inbounds nuw i8, ptr %v20_scratch, i64 16
  store <16 x i8> %1, ptr %v14.fca.16.gep1073, align 16
  %v14.fca.32.gep1105 = getelementptr inbounds nuw i8, ptr %v20_scratch, i64 32
  store <16 x i8> %2, ptr %v14.fca.32.gep1105, align 16
  %v14.fca.48.gep1137 = getelementptr inbounds nuw i8, ptr %v20_scratch, i64 48
  store <16 x i8> %3, ptr %v14.fca.48.gep1137, align 16
  %v20_ptr = getelementptr [64 x i8], ptr %v20_scratch, i64 0, i64 %v18_offset
  store i8 5, ptr %v20_ptr, align 1
  tail call void @llvm.memmove.p0.p0.i64(ptr noundef nonnull align 8 dereferenceable(56) %return_storage, ptr noundef nonnull align 1 dereferenceable(56) %p0, i64 56, i1 false)
  %v21_mem.sroa.2.0.return_storage.sroa_idx = getelementptr inbounds nuw i8, ptr %return_storage, i64 56
  %4 = load <16 x i8>, ptr %v20_scratch, align 16
  store <16 x i8> %4, ptr %v21_mem.sroa.2.0.return_storage.sroa_idx, align 8
  %v21_mem.sroa.18.0.return_storage.sroa_idx = getelementptr inbounds nuw i8, ptr %return_storage, i64 72
  %5 = load <16 x i8>, ptr %v14.fca.16.gep1073, align 16
  store <16 x i8> %5, ptr %v21_mem.sroa.18.0.return_storage.sroa_idx, align 8
  %v21_mem.sroa.34.0.return_storage.sroa_idx = getelementptr inbounds nuw i8, ptr %return_storage, i64 88
  %6 = load <16 x i8>, ptr %v14.fca.32.gep1105, align 16
  store <16 x i8> %6, ptr %v21_mem.sroa.34.0.return_storage.sroa_idx, align 8
  %v21_mem.sroa.50.0.return_storage.sroa_idx = getelementptr inbounds nuw i8, ptr %return_storage, i64 104
  %7 = load <16 x i8>, ptr %v14.fca.48.gep1137, align 16
  store <16 x i8> %7, ptr %v21_mem.sroa.50.0.return_storage.sroa_idx, align 8
  %v21_mem.sroa.66.0.return_storage.sroa_idx = getelementptr inbounds nuw i8, ptr %return_storage, i64 120
  call void @llvm.memcpy.p0.p0.i64(ptr noundef nonnull align 8 dereferenceable(64) %v21_mem.sroa.66.0.return_storage.sroa_idx, ptr noundef nonnull align 8 dereferenceable(64) %v15_ptr, i64 64, i1 false)
  br label %common.ret

b10:                                              ; preds = %b6
  call void @liza___liza_json_done(ptr nonnull sret(%struct.JsonState) %v22_mem, ptr nonnull %v12_mem)
  call void @llvm.memcpy.p0.p0.i64(ptr noundef nonnull align 8 dereferenceable(184) %return_storage, ptr noundef nonnull align 8 dereferenceable(184) %v22_mem, i64 184, i1 false)
  br label %common.ret

b12:                                              ; preds = %b5
  %v27_mem.sroa.2.0.p0.sroa_idx = getelementptr inbounds nuw i8, ptr %p0, i64 48
  %v27_mem.sroa.2.0.copyload = load i64, ptr %v27_mem.sroa.2.0.p0.sroa_idx, align 1
  br label %b14

b14:                                              ; preds = %b13_to_b14, %b12
  %v31_mem.sroa.3.0 = phi i64 [ %v31_next.sroa.4.0.copyload2036, %b13_to_b14 ], [ %v27_mem.sroa.2.0.copyload, %b12 ]
  %v31_mem.sroa.0.sroa.3.0 = phi i64 [ %v31_next.sroa.0.sroa.4.0.copyload, %b13_to_b14 ], [ %v27_mem.sroa.2.0.copyload, %b12 ]
  %v31_mem.sroa.0.sroa.7.0 = phi i32 [ 1, %b13_to_b14 ], [ 2, %b12 ]
  %v31_next.sroa.0.sroa.7.0.p0.sroa_idx.sink = getelementptr inbounds nuw i8, ptr %p0, i64 132
  %v31_next.sroa.0.sroa.5.0.p0.sroa_idx.sink = getelementptr inbounds nuw i8, ptr %p0, i64 56
  %v31_next.sroa.5.0.p0.sroa_idx = getelementptr inbounds nuw i8, ptr %p0, i64 160
  call void @llvm.memcpy.p0.p0.i64(ptr noundef nonnull align 8 dereferenceable(48) %v31_mem.sroa.0.sroa.0, ptr noundef nonnull align 1 dereferenceable(48) %p0, i64 48, i1 false)
  call void @llvm.memcpy.p0.p0.i64(ptr noundef nonnull align 8 dereferenceable(72) %v31_mem.sroa.0.sroa.5, ptr noundef nonnull align 1 dereferenceable(72) %v31_next.sroa.0.sroa.5.0.p0.sroa_idx.sink, i64 72, i1 false)
  call void @llvm.memcpy.p0.p0.i64(ptr noundef nonnull align 8 dereferenceable(20) %v31_mem.sroa.0.sroa.9, ptr noundef nonnull align 1 dereferenceable(20) %v31_next.sroa.0.sroa.7.0.p0.sroa_idx.sink, i64 20, i1 false)
  call void @llvm.memcpy.p0.p0.i64(ptr noundef nonnull align 8 dereferenceable(24) %v31_mem.sroa.5, ptr noundef nonnull align 1 dereferenceable(24) %v31_next.sroa.5.0.p0.sroa_idx, i64 24, i1 false)
  call void @llvm.memcpy.p0.p0.i64(ptr noundef nonnull align 8 dereferenceable(48) %return_storage, ptr noundef nonnull align 8 dereferenceable(48) %v31_mem.sroa.0.sroa.0, i64 48, i1 false)
  %v31_mem.sroa.0.sroa.3.0.return_storage.sroa_idx = getelementptr inbounds nuw i8, ptr %return_storage, i64 48
  store i64 %v31_mem.sroa.0.sroa.3.0, ptr %v31_mem.sroa.0.sroa.3.0.return_storage.sroa_idx, align 8
  %v31_mem.sroa.0.sroa.5.0.return_storage.sroa_idx = getelementptr inbounds nuw i8, ptr %return_storage, i64 56
  call void @llvm.memcpy.p0.p0.i64(ptr noundef nonnull align 8 dereferenceable(72) %v31_mem.sroa.0.sroa.5.0.return_storage.sroa_idx, ptr noundef nonnull align 8 dereferenceable(72) %v31_mem.sroa.0.sroa.5, i64 72, i1 false)
  %v31_mem.sroa.0.sroa.7.0.return_storage.sroa_idx = getelementptr inbounds nuw i8, ptr %return_storage, i64 128
  store i32 %v31_mem.sroa.0.sroa.7.0, ptr %v31_mem.sroa.0.sroa.7.0.return_storage.sroa_idx, align 8
  %v31_mem.sroa.0.sroa.9.0.return_storage.sroa_idx = getelementptr inbounds nuw i8, ptr %return_storage, i64 132
  call void @llvm.memcpy.p0.p0.i64(ptr noundef nonnull align 4 dereferenceable(20) %v31_mem.sroa.0.sroa.9.0.return_storage.sroa_idx, ptr noundef nonnull align 8 dereferenceable(20) %v31_mem.sroa.0.sroa.9, i64 20, i1 false)
  %v31_mem.sroa.3.0.return_storage.sroa_idx = getelementptr inbounds nuw i8, ptr %return_storage, i64 152
  store i64 %v31_mem.sroa.3.0, ptr %v31_mem.sroa.3.0.return_storage.sroa_idx, align 8
  %v31_mem.sroa.5.0.return_storage.sroa_idx = getelementptr inbounds nuw i8, ptr %return_storage, i64 160
  call void @llvm.memcpy.p0.p0.i64(ptr noundef nonnull align 8 dereferenceable(24) %v31_mem.sroa.5.0.return_storage.sroa_idx, ptr noundef nonnull align 8 dereferenceable(24) %v31_mem.sroa.5, i64 24, i1 false)
  br label %common.ret

b16:                                              ; preds = %b0
  switch i8 %p1, label %b44 [
    i8 114, label %b39
    i8 110, label %b39
    i8 102, label %b39
    i8 98, label %b39
    i8 92, label %b39
    i8 47, label %b39
    i8 34, label %b39
    i8 116, label %b39
    i8 117, label %b42
  ]

b39:                                              ; preds = %b16, %b16, %b16, %b16, %b16, %b16, %b16, %b16
  %v67_mem.sroa.3.0.p0.sroa_idx = getelementptr inbounds nuw i8, ptr %p0, i64 132
  call void @llvm.memcpy.p0.p0.i64(ptr noundef nonnull align 4 dereferenceable(52) %v67_mem.sroa.3, ptr noundef nonnull align 1 dereferenceable(52) %v67_mem.sroa.3.0.p0.sroa_idx, i64 52, i1 false)
  tail call void @llvm.memmove.p0.p0.i64(ptr noundef nonnull align 8 dereferenceable(128) %return_storage, ptr noundef nonnull align 1 dereferenceable(128) %p0, i64 128, i1 false)
  %v67_mem.sroa.2.0.return_storage.sroa_idx = getelementptr inbounds nuw i8, ptr %return_storage, i64 128
  store i32 1, ptr %v67_mem.sroa.2.0.return_storage.sroa_idx, align 8
  %v67_mem.sroa.3.0.return_storage.sroa_idx = getelementptr inbounds nuw i8, ptr %return_storage, i64 132
  call void @llvm.memcpy.p0.p0.i64(ptr noundef nonnull align 4 dereferenceable(52) %v67_mem.sroa.3.0.return_storage.sroa_idx, ptr noundef nonnull align 4 dereferenceable(52) %v67_mem.sroa.3, i64 52, i1 false)
  br label %common.ret

b42:                                              ; preds = %b16
  %v72_mem.sroa.3.0.p0.sroa_idx = getelementptr inbounds nuw i8, ptr %p0, i64 132
  call void @llvm.memcpy.p0.p0.i64(ptr noundef nonnull align 8 dereferenceable(12) %v78_mem.sroa.0.sroa.0.sroa.3, ptr noundef nonnull align 1 dereferenceable(12) %v72_mem.sroa.3.0.p0.sroa_idx, i64 12, i1 false)
  %v72_mem.sroa.5.0.p0.sroa_idx = getelementptr inbounds nuw i8, ptr %p0, i64 152
  call void @llvm.memcpy.p0.p0.i64(ptr noundef nonnull align 8 dereferenceable(32) %v78_mem.sroa.3, ptr noundef nonnull align 1 dereferenceable(32) %v72_mem.sroa.5.0.p0.sroa_idx, i64 32, i1 false)
  tail call void @llvm.memmove.p0.p0.i64(ptr noundef nonnull align 8 dereferenceable(128) %return_storage, ptr noundef nonnull align 1 dereferenceable(128) %p0, i64 128, i1 false)
  %v78_mem.sroa.0.sroa.0.sroa.2.0.return_storage.sroa_idx = getelementptr inbounds nuw i8, ptr %return_storage, i64 128
  store i32 3, ptr %v78_mem.sroa.0.sroa.0.sroa.2.0.return_storage.sroa_idx, align 8
  %v78_mem.sroa.0.sroa.0.sroa.3.0.return_storage.sroa_idx = getelementptr inbounds nuw i8, ptr %return_storage, i64 132
  call void @llvm.memcpy.p0.p0.i64(ptr noundef nonnull align 4 dereferenceable(12) %v78_mem.sroa.0.sroa.0.sroa.3.0.return_storage.sroa_idx, ptr noundef nonnull align 8 dereferenceable(12) %v78_mem.sroa.0.sroa.0.sroa.3, i64 12, i1 false)
  %v78_mem.sroa.0.sroa.2.0.return_storage.sroa_idx = getelementptr inbounds nuw i8, ptr %return_storage, i64 144
  store <2 x i32> zeroinitializer, ptr %v78_mem.sroa.0.sroa.2.0.return_storage.sroa_idx, align 8
  %v78_mem.sroa.3.0.return_storage.sroa_idx = getelementptr inbounds nuw i8, ptr %return_storage, i64 152
  call void @llvm.memcpy.p0.p0.i64(ptr noundef nonnull align 8 dereferenceable(32) %v78_mem.sroa.3.0.return_storage.sroa_idx, ptr noundef nonnull align 8 dereferenceable(32) %v78_mem.sroa.3, i64 32, i1 false)
  br label %common.ret

b44:                                              ; preds = %b16
  %v80_ptr = getelementptr i8, ptr %p0, i64 48
  %v80 = load i64, ptr %v80_ptr, align 8
  %v1_mem.sroa.3.0.p0.sroa_idx.i1232 = getelementptr inbounds nuw i8, ptr %p0, i64 172
  %v1_mem.sroa.3.0.copyload.i1233 = load i32, ptr %v1_mem.sroa.3.0.p0.sroa_idx.i1232, align 1
  tail call void @llvm.memmove.p0.p0.i64(ptr noundef nonnull align 8 dereferenceable(168) %return_storage, ptr noundef nonnull align 1 dereferenceable(168) %p0, i64 168, i1 false)
  %v81_mem.sroa.2.0.return_storage.sroa_idx = getelementptr inbounds nuw i8, ptr %return_storage, i64 168
  store i32 3, ptr %v81_mem.sroa.2.0.return_storage.sroa_idx, align 8
  %v81_mem.sroa.3.0.return_storage.sroa_idx = getelementptr inbounds nuw i8, ptr %return_storage, i64 172
  store i32 %v1_mem.sroa.3.0.copyload.i1233, ptr %v81_mem.sroa.3.0.return_storage.sroa_idx, align 4
  %v81_mem.sroa.4.0.return_storage.sroa_idx = getelementptr inbounds nuw i8, ptr %return_storage, i64 176
  store i64 %v80, ptr %v81_mem.sroa.4.0.return_storage.sroa_idx, align 8
  br label %common.ret

b46:                                              ; preds = %b0
  %v86.not = icmp eq i8 %p1, 92
  br i1 %v86.not, label %b50, label %b48

b48:                                              ; preds = %b46
  %v88_ptr = getelementptr i8, ptr %p0, i64 160
  %v88 = load i64, ptr %v88_ptr, align 8
  %v1_mem.sroa.3.0.p0.sroa_idx.i1237 = getelementptr inbounds nuw i8, ptr %p0, i64 172
  %v1_mem.sroa.3.0.copyload.i1238 = load i32, ptr %v1_mem.sroa.3.0.p0.sroa_idx.i1237, align 1
  tail call void @llvm.memmove.p0.p0.i64(ptr noundef nonnull align 8 dereferenceable(168) %return_storage, ptr noundef nonnull align 1 dereferenceable(168) %p0, i64 168, i1 false)
  %v89_mem.sroa.2.0.return_storage.sroa_idx = getelementptr inbounds nuw i8, ptr %return_storage, i64 168
  store i32 4, ptr %v89_mem.sroa.2.0.return_storage.sroa_idx, align 8
  %v89_mem.sroa.3.0.return_storage.sroa_idx = getelementptr inbounds nuw i8, ptr %return_storage, i64 172
  store i32 %v1_mem.sroa.3.0.copyload.i1238, ptr %v89_mem.sroa.3.0.return_storage.sroa_idx, align 4
  %v89_mem.sroa.4.0.return_storage.sroa_idx = getelementptr inbounds nuw i8, ptr %return_storage, i64 176
  store i64 %v88, ptr %v89_mem.sroa.4.0.return_storage.sroa_idx, align 8
  br label %common.ret

b50:                                              ; preds = %b46
  %v92_mem.sroa.3.0.p0.sroa_idx = getelementptr inbounds nuw i8, ptr %p0, i64 132
  call void @llvm.memcpy.p0.p0.i64(ptr noundef nonnull align 4 dereferenceable(52) %v92_mem.sroa.3, ptr noundef nonnull align 1 dereferenceable(52) %v92_mem.sroa.3.0.p0.sroa_idx, i64 52, i1 false)
  tail call void @llvm.memmove.p0.p0.i64(ptr noundef nonnull align 8 dereferenceable(128) %return_storage, ptr noundef nonnull align 1 dereferenceable(128) %p0, i64 128, i1 false)
  %v92_mem.sroa.2.0.return_storage.sroa_idx = getelementptr inbounds nuw i8, ptr %return_storage, i64 128
  store i32 5, ptr %v92_mem.sroa.2.0.return_storage.sroa_idx, align 8
  %v92_mem.sroa.3.0.return_storage.sroa_idx = getelementptr inbounds nuw i8, ptr %return_storage, i64 132
  call void @llvm.memcpy.p0.p0.i64(ptr noundef nonnull align 4 dereferenceable(52) %v92_mem.sroa.3.0.return_storage.sroa_idx, ptr noundef nonnull align 4 dereferenceable(52) %v92_mem.sroa.3, i64 52, i1 false)
  br label %common.ret

b52:                                              ; preds = %b0
  %v97.not = icmp eq i8 %p1, 117
  br i1 %v97.not, label %b56, label %b54

b54:                                              ; preds = %b52
  %v99_ptr = getelementptr i8, ptr %p0, i64 160
  %v99 = load i64, ptr %v99_ptr, align 8
  %v1_mem.sroa.3.0.p0.sroa_idx.i1242 = getelementptr inbounds nuw i8, ptr %p0, i64 172
  %v1_mem.sroa.3.0.copyload.i1243 = load i32, ptr %v1_mem.sroa.3.0.p0.sroa_idx.i1242, align 1
  tail call void @llvm.memmove.p0.p0.i64(ptr noundef nonnull align 8 dereferenceable(168) %return_storage, ptr noundef nonnull align 1 dereferenceable(168) %p0, i64 168, i1 false)
  %v100_mem.sroa.2.0.return_storage.sroa_idx = getelementptr inbounds nuw i8, ptr %return_storage, i64 168
  store i32 4, ptr %v100_mem.sroa.2.0.return_storage.sroa_idx, align 8
  %v100_mem.sroa.3.0.return_storage.sroa_idx = getelementptr inbounds nuw i8, ptr %return_storage, i64 172
  store i32 %v1_mem.sroa.3.0.copyload.i1243, ptr %v100_mem.sroa.3.0.return_storage.sroa_idx, align 4
  %v100_mem.sroa.4.0.return_storage.sroa_idx = getelementptr inbounds nuw i8, ptr %return_storage, i64 176
  store i64 %v99, ptr %v100_mem.sroa.4.0.return_storage.sroa_idx, align 8
  br label %common.ret

b56:                                              ; preds = %b52
  %v103_mem.sroa.3.0.p0.sroa_idx = getelementptr inbounds nuw i8, ptr %p0, i64 132
  call void @llvm.memcpy.p0.p0.i64(ptr noundef nonnull align 8 dereferenceable(12) %v109_mem.sroa.0.sroa.0.sroa.3, ptr noundef nonnull align 1 dereferenceable(12) %v103_mem.sroa.3.0.p0.sroa_idx, i64 12, i1 false)
  %v103_mem.sroa.5.0.p0.sroa_idx = getelementptr inbounds nuw i8, ptr %p0, i64 152
  call void @llvm.memcpy.p0.p0.i64(ptr noundef nonnull align 8 dereferenceable(32) %v109_mem.sroa.3, ptr noundef nonnull align 1 dereferenceable(32) %v103_mem.sroa.5.0.p0.sroa_idx, i64 32, i1 false)
  tail call void @llvm.memmove.p0.p0.i64(ptr noundef nonnull align 8 dereferenceable(128) %return_storage, ptr noundef nonnull align 1 dereferenceable(128) %p0, i64 128, i1 false)
  %v109_mem.sroa.0.sroa.0.sroa.2.0.return_storage.sroa_idx = getelementptr inbounds nuw i8, ptr %return_storage, i64 128
  store i32 6, ptr %v109_mem.sroa.0.sroa.0.sroa.2.0.return_storage.sroa_idx, align 8
  %v109_mem.sroa.0.sroa.0.sroa.3.0.return_storage.sroa_idx = getelementptr inbounds nuw i8, ptr %return_storage, i64 132
  call void @llvm.memcpy.p0.p0.i64(ptr noundef nonnull align 4 dereferenceable(12) %v109_mem.sroa.0.sroa.0.sroa.3.0.return_storage.sroa_idx, ptr noundef nonnull align 8 dereferenceable(12) %v109_mem.sroa.0.sroa.0.sroa.3, i64 12, i1 false)
  %v109_mem.sroa.0.sroa.2.0.return_storage.sroa_idx = getelementptr inbounds nuw i8, ptr %return_storage, i64 144
  store <2 x i32> zeroinitializer, ptr %v109_mem.sroa.0.sroa.2.0.return_storage.sroa_idx, align 8
  %v109_mem.sroa.3.0.return_storage.sroa_idx = getelementptr inbounds nuw i8, ptr %return_storage, i64 152
  call void @llvm.memcpy.p0.p0.i64(ptr noundef nonnull align 8 dereferenceable(32) %v109_mem.sroa.3.0.return_storage.sroa_idx, ptr noundef nonnull align 8 dereferenceable(32) %v109_mem.sroa.3, i64 32, i1 false)
  br label %common.ret

b61:                                              ; preds = %b0, %b0
  %8 = add i8 %p1, -48
  %v5.i = icmp ult i8 %8, 10
  br i1 %v5.i, label %b65, label %b6.i

b6.i:                                             ; preds = %b61
  %9 = add i8 %p1, -65
  %v14.i = icmp ult i8 %9, 6
  br i1 %v14.i, label %b65, label %b12.i

b12.i:                                            ; preds = %b6.i
  %10 = add i8 %p1, -97
  %v23.i = icmp ult i8 %10, 6
  br i1 %v23.i, label %b65, label %b63

b63:                                              ; preds = %b12.i
  %v122_ptr = getelementptr i8, ptr %p0, i64 48
  %v122 = load i64, ptr %v122_ptr, align 8
  %v1_mem.sroa.3.0.p0.sroa_idx.i1247 = getelementptr inbounds nuw i8, ptr %p0, i64 172
  %v1_mem.sroa.3.0.copyload.i1248 = load i32, ptr %v1_mem.sroa.3.0.p0.sroa_idx.i1247, align 1
  tail call void @llvm.memmove.p0.p0.i64(ptr noundef nonnull align 8 dereferenceable(168) %return_storage, ptr noundef nonnull align 1 dereferenceable(168) %p0, i64 168, i1 false)
  %v123_mem.sroa.2.0.return_storage.sroa_idx = getelementptr inbounds nuw i8, ptr %return_storage, i64 168
  store i32 3, ptr %v123_mem.sroa.2.0.return_storage.sroa_idx, align 8
  %v123_mem.sroa.3.0.return_storage.sroa_idx = getelementptr inbounds nuw i8, ptr %return_storage, i64 172
  store i32 %v1_mem.sroa.3.0.copyload.i1248, ptr %v123_mem.sroa.3.0.return_storage.sroa_idx, align 4
  %v123_mem.sroa.4.0.return_storage.sroa_idx = getelementptr inbounds nuw i8, ptr %return_storage, i64 176
  store i64 %v122, ptr %v123_mem.sroa.4.0.return_storage.sroa_idx, align 8
  br label %common.ret

b65:                                              ; preds = %b12.i, %b6.i, %b61
  %.sink = phi i32 [ -48, %b61 ], [ -55, %b6.i ], [ -87, %b12.i ]
  %v124_ptr = getelementptr i8, ptr %p0, i64 148
  %v125 = load i32, ptr %v124_ptr, align 4
  %v127_overflow = icmp ugt i32 %v125, 268435455
  br i1 %v127_overflow, label %v127_trap, label %v128_ok

v127_trap:                                        ; preds = %b65
  tail call void @llvm.trap()
  unreachable

v128_ok:                                          ; preds = %b65
  %v6.i = zext nneg i8 %p1 to i32
  %v8_pair.i = add nsw i32 %.sink, %v6.i
  %v127 = shl nuw i32 %v125, 4
  %v128_pair2139 = add nuw i32 %v127, %v8_pair.i
  %v129_mem.sroa.3.0.p0.sroa_idx = getelementptr inbounds nuw i8, ptr %p0, i64 132
  %v129_mem.sroa.4.0.p0.sroa_idx = getelementptr inbounds nuw i8, ptr %p0, i64 144
  %v129_mem.sroa.4.0.copyload = load i32, ptr %v129_mem.sroa.4.0.p0.sroa_idx, align 1
  %v129_mem.sroa.8.0.p0.sroa_idx = getelementptr inbounds nuw i8, ptr %p0, i64 152
  %v129_mem.sroa.8.0.copyload = load i64, ptr %v129_mem.sroa.8.0.p0.sroa_idx, align 1
  %v129_mem.sroa.9.0.p0.sroa_idx = getelementptr inbounds nuw i8, ptr %p0, i64 160
  %v129_mem.sroa.9.0.copyload = load i64, ptr %v129_mem.sroa.9.0.p0.sroa_idx, align 1
  %v129_mem.sroa.10.0.p0.sroa_idx = getelementptr inbounds nuw i8, ptr %p0, i64 168
  %v129_mem.sroa.10.0.copyload = load i32, ptr %v129_mem.sroa.10.0.p0.sroa_idx, align 1
  %v129_mem.sroa.11.0.p0.sroa_idx = getelementptr inbounds nuw i8, ptr %p0, i64 172
  %v129_mem.sroa.11.0.copyload = load i32, ptr %v129_mem.sroa.11.0.p0.sroa_idx, align 1
  %v129_mem.sroa.12.0.p0.sroa_idx = getelementptr inbounds nuw i8, ptr %p0, i64 176
  %v129_mem.sroa.12.0.copyload = load i64, ptr %v129_mem.sroa.12.0.p0.sroa_idx, align 1
  %v133_pair = tail call { i32, i1 } @llvm.uadd.with.overflow.i32(i32 %v129_mem.sroa.4.0.copyload, i32 1)
  %v133_overflow = extractvalue { i32, i1 } %v133_pair, 1
  br i1 %v133_overflow, label %v133_trap, label %v133_ok

v133_trap:                                        ; preds = %v128_ok
  tail call void @llvm.trap()
  unreachable

v133_ok:                                          ; preds = %v128_ok
  %v133 = extractvalue { i32, i1 } %v133_pair, 0
  %v137 = icmp eq i32 %v133, 4
  br i1 %v137, label %b66, label %b89

b66:                                              ; preds = %v133_ok
  %v140 = icmp eq i32 %v0, 6
  br i1 %v140, label %b68, label %b76

b68:                                              ; preds = %b66
  %11 = add i32 %v128_pair2139, -57344
  %v148 = icmp ult i32 %11, -1024
  %v151_mem.sroa.0.sroa.2.0.return_storage.sroa_idx = getelementptr inbounds nuw i8, ptr %return_storage, i64 128
  %v151_mem.sroa.0.sroa.3.0.return_storage.sroa_idx = getelementptr inbounds nuw i8, ptr %return_storage, i64 132
  %v151_mem.sroa.0.sroa.4.0.return_storage.sroa_idx = getelementptr inbounds nuw i8, ptr %return_storage, i64 144
  %v151_mem.sroa.0.sroa.5.0.return_storage.sroa_idx = getelementptr inbounds nuw i8, ptr %return_storage, i64 148
  %v151_mem.sroa.0.sroa.6.0.return_storage.sroa_idx = getelementptr inbounds nuw i8, ptr %return_storage, i64 152
  %v151_mem.sroa.0.sroa.7.0.return_storage.sroa_idx = getelementptr inbounds nuw i8, ptr %return_storage, i64 160
  %v151_mem.sroa.2.0.return_storage.sroa_idx = getelementptr inbounds nuw i8, ptr %return_storage, i64 168
  %v151_mem.sroa.3.0.return_storage.sroa_idx = getelementptr inbounds nuw i8, ptr %return_storage, i64 172
  %v151_mem.sroa.4.0.return_storage.sroa_idx = getelementptr inbounds nuw i8, ptr %return_storage, i64 176
  br i1 %v148, label %b73, label %b75

b73:                                              ; preds = %b68
  call void @llvm.memcpy.p0.p0.i64(ptr noundef nonnull align 8 dereferenceable(12) %v151_mem.sroa.0.sroa.3, ptr noundef nonnull align 1 dereferenceable(12) %v129_mem.sroa.3.0.p0.sroa_idx, i64 12, i1 false)
  tail call void @llvm.memmove.p0.p0.i64(ptr noundef nonnull align 8 dereferenceable(128) %return_storage, ptr noundef nonnull align 1 dereferenceable(128) %p0, i64 128, i1 false)
  store i32 6, ptr %v151_mem.sroa.0.sroa.2.0.return_storage.sroa_idx, align 8
  call void @llvm.memcpy.p0.p0.i64(ptr noundef nonnull align 4 dereferenceable(12) %v151_mem.sroa.0.sroa.3.0.return_storage.sroa_idx, ptr noundef nonnull align 8 dereferenceable(12) %v151_mem.sroa.0.sroa.3, i64 12, i1 false)
  store i32 4, ptr %v151_mem.sroa.0.sroa.4.0.return_storage.sroa_idx, align 8
  store i32 %v128_pair2139, ptr %v151_mem.sroa.0.sroa.5.0.return_storage.sroa_idx, align 4
  store i64 %v129_mem.sroa.8.0.copyload, ptr %v151_mem.sroa.0.sroa.6.0.return_storage.sroa_idx, align 8
  store i64 %v129_mem.sroa.9.0.copyload, ptr %v151_mem.sroa.0.sroa.7.0.return_storage.sroa_idx, align 8
  store i32 4, ptr %v151_mem.sroa.2.0.return_storage.sroa_idx, align 8
  store i32 %v129_mem.sroa.11.0.copyload, ptr %v151_mem.sroa.3.0.return_storage.sroa_idx, align 4
  store i64 %v129_mem.sroa.9.0.copyload, ptr %v151_mem.sroa.4.0.return_storage.sroa_idx, align 8
  br label %common.ret

b75:                                              ; preds = %b68
  call void @llvm.memcpy.p0.p0.i64(ptr noundef nonnull align 4 dereferenceable(12) %v154_mem.sroa.3.sroa.0, ptr noundef nonnull align 1 dereferenceable(12) %v129_mem.sroa.3.0.p0.sroa_idx, i64 12, i1 false)
  tail call void @llvm.memmove.p0.p0.i64(ptr noundef nonnull align 8 dereferenceable(128) %return_storage, ptr noundef nonnull align 1 dereferenceable(128) %p0, i64 128, i1 false)
  store i32 1, ptr %v151_mem.sroa.0.sroa.2.0.return_storage.sroa_idx, align 8
  call void @llvm.memcpy.p0.p0.i64(ptr noundef nonnull align 4 dereferenceable(12) %v151_mem.sroa.0.sroa.3.0.return_storage.sroa_idx, ptr noundef nonnull align 4 dereferenceable(12) %v154_mem.sroa.3.sroa.0, i64 12, i1 false)
  store i32 4, ptr %v151_mem.sroa.0.sroa.4.0.return_storage.sroa_idx, align 8
  store i32 %v128_pair2139, ptr %v151_mem.sroa.0.sroa.5.0.return_storage.sroa_idx, align 4
  store i64 %v129_mem.sroa.8.0.copyload, ptr %v151_mem.sroa.0.sroa.6.0.return_storage.sroa_idx, align 8
  store i64 %v129_mem.sroa.9.0.copyload, ptr %v151_mem.sroa.0.sroa.7.0.return_storage.sroa_idx, align 8
  store i32 %v129_mem.sroa.10.0.copyload, ptr %v151_mem.sroa.2.0.return_storage.sroa_idx, align 8
  store i32 %v129_mem.sroa.11.0.copyload, ptr %v151_mem.sroa.3.0.return_storage.sroa_idx, align 4
  store i64 %v129_mem.sroa.12.0.copyload, ptr %v151_mem.sroa.4.0.return_storage.sroa_idx, align 8
  br label %common.ret

b76:                                              ; preds = %b66
  %12 = and i32 %v128_pair2139, -1024
  switch i32 %12, label %b89 [
    i32 55296, label %b80
    i32 56320, label %b86
  ]

b80:                                              ; preds = %b76
  call void @llvm.memcpy.p0.p0.i64(ptr noundef nonnull align 8 dereferenceable(12) %v168_mem.sroa.0.sroa.3.sroa.0, ptr noundef nonnull align 1 dereferenceable(12) %v129_mem.sroa.3.0.p0.sroa_idx, i64 12, i1 false)
  tail call void @llvm.memmove.p0.p0.i64(ptr noundef nonnull align 8 dereferenceable(128) %return_storage, ptr noundef nonnull align 1 dereferenceable(128) %p0, i64 128, i1 false)
  %v168_mem.sroa.0.sroa.2.0.return_storage.sroa_idx = getelementptr inbounds nuw i8, ptr %return_storage, i64 128
  store i32 4, ptr %v168_mem.sroa.0.sroa.2.0.return_storage.sroa_idx, align 8
  %v168_mem.sroa.0.sroa.3.0.return_storage.sroa_idx = getelementptr inbounds nuw i8, ptr %return_storage, i64 132
  call void @llvm.memcpy.p0.p0.i64(ptr noundef nonnull align 4 dereferenceable(12) %v168_mem.sroa.0.sroa.3.0.return_storage.sroa_idx, ptr noundef nonnull align 8 dereferenceable(12) %v168_mem.sroa.0.sroa.3.sroa.0, i64 12, i1 false)
  %v168_mem.sroa.0.sroa.3.sroa.2.0.v168_mem.sroa.0.sroa.3.0.return_storage.sroa_idx.sroa_idx = getelementptr inbounds nuw i8, ptr %return_storage, i64 144
  store i32 4, ptr %v168_mem.sroa.0.sroa.3.sroa.2.0.v168_mem.sroa.0.sroa.3.0.return_storage.sroa_idx.sroa_idx, align 8
  %v168_mem.sroa.0.sroa.3.sroa.3.0.v168_mem.sroa.0.sroa.3.0.return_storage.sroa_idx.sroa_idx = getelementptr inbounds nuw i8, ptr %return_storage, i64 148
  store i32 %v128_pair2139, ptr %v168_mem.sroa.0.sroa.3.sroa.3.0.v168_mem.sroa.0.sroa.3.0.return_storage.sroa_idx.sroa_idx, align 4
  %v168_mem.sroa.0.sroa.4.0.return_storage.sroa_idx = getelementptr inbounds nuw i8, ptr %return_storage, i64 152
  store i64 %v129_mem.sroa.8.0.copyload, ptr %v168_mem.sroa.0.sroa.4.0.return_storage.sroa_idx, align 8
  %v168_mem.sroa.2.0.return_storage.sroa_idx = getelementptr inbounds nuw i8, ptr %return_storage, i64 160
  store i64 %v129_mem.sroa.8.0.copyload, ptr %v168_mem.sroa.2.0.return_storage.sroa_idx, align 8
  %v168_mem.sroa.3.0.return_storage.sroa_idx = getelementptr inbounds nuw i8, ptr %return_storage, i64 168
  store i32 %v129_mem.sroa.10.0.copyload, ptr %v168_mem.sroa.3.0.return_storage.sroa_idx, align 8
  %v168_mem.sroa.3.sroa.2.0.v168_mem.sroa.3.0.return_storage.sroa_idx.sroa_idx = getelementptr inbounds nuw i8, ptr %return_storage, i64 172
  store i32 %v129_mem.sroa.11.0.copyload, ptr %v168_mem.sroa.3.sroa.2.0.v168_mem.sroa.3.0.return_storage.sroa_idx.sroa_idx, align 4
  %v168_mem.sroa.3.sroa.3.0.v168_mem.sroa.3.0.return_storage.sroa_idx.sroa_idx = getelementptr inbounds nuw i8, ptr %return_storage, i64 176
  store i64 %v129_mem.sroa.12.0.copyload, ptr %v168_mem.sroa.3.sroa.3.0.v168_mem.sroa.3.0.return_storage.sroa_idx.sroa_idx, align 8
  br label %common.ret

b86:                                              ; preds = %b76
  call void @llvm.memcpy.p0.p0.i64(ptr noundef nonnull align 8 dereferenceable(12) %v179_mem.sroa.0.sroa.3, ptr noundef nonnull align 1 dereferenceable(12) %v129_mem.sroa.3.0.p0.sroa_idx, i64 12, i1 false)
  tail call void @llvm.memmove.p0.p0.i64(ptr noundef nonnull align 8 dereferenceable(128) %return_storage, ptr noundef nonnull align 1 dereferenceable(128) %p0, i64 128, i1 false)
  %v179_mem.sroa.0.sroa.2.0.return_storage.sroa_idx = getelementptr inbounds nuw i8, ptr %return_storage, i64 128
  store i32 %v0, ptr %v179_mem.sroa.0.sroa.2.0.return_storage.sroa_idx, align 8
  %v179_mem.sroa.0.sroa.3.0.return_storage.sroa_idx = getelementptr inbounds nuw i8, ptr %return_storage, i64 132
  call void @llvm.memcpy.p0.p0.i64(ptr noundef nonnull align 4 dereferenceable(12) %v179_mem.sroa.0.sroa.3.0.return_storage.sroa_idx, ptr noundef nonnull align 8 dereferenceable(12) %v179_mem.sroa.0.sroa.3, i64 12, i1 false)
  %v179_mem.sroa.0.sroa.4.0.return_storage.sroa_idx = getelementptr inbounds nuw i8, ptr %return_storage, i64 144
  store i32 4, ptr %v179_mem.sroa.0.sroa.4.0.return_storage.sroa_idx, align 8
  %v179_mem.sroa.0.sroa.5.0.return_storage.sroa_idx = getelementptr inbounds nuw i8, ptr %return_storage, i64 148
  store i32 %v128_pair2139, ptr %v179_mem.sroa.0.sroa.5.0.return_storage.sroa_idx, align 4
  %v179_mem.sroa.0.sroa.6.0.return_storage.sroa_idx = getelementptr inbounds nuw i8, ptr %return_storage, i64 152
  store i64 %v129_mem.sroa.8.0.copyload, ptr %v179_mem.sroa.0.sroa.6.0.return_storage.sroa_idx, align 8
  %v179_mem.sroa.0.sroa.7.0.return_storage.sroa_idx = getelementptr inbounds nuw i8, ptr %return_storage, i64 160
  store i64 %v129_mem.sroa.9.0.copyload, ptr %v179_mem.sroa.0.sroa.7.0.return_storage.sroa_idx, align 8
  %v179_mem.sroa.2.0.return_storage.sroa_idx = getelementptr inbounds nuw i8, ptr %return_storage, i64 168
  store i32 4, ptr %v179_mem.sroa.2.0.return_storage.sroa_idx, align 8
  %v179_mem.sroa.3.0.return_storage.sroa_idx = getelementptr inbounds nuw i8, ptr %return_storage, i64 172
  store i32 %v129_mem.sroa.11.0.copyload, ptr %v179_mem.sroa.3.0.return_storage.sroa_idx, align 4
  %v179_mem.sroa.4.0.return_storage.sroa_idx = getelementptr inbounds nuw i8, ptr %return_storage, i64 176
  store i64 %v129_mem.sroa.8.0.copyload, ptr %v179_mem.sroa.4.0.return_storage.sroa_idx, align 8
  br label %common.ret

b89:                                              ; preds = %b76, %v133_ok
  %v183_mem.sroa.3.0 = phi i32 [ %v0, %v133_ok ], [ 1, %b76 ]
  call void @llvm.memcpy.p0.p0.i64(ptr noundef nonnull align 8 dereferenceable(128) %v183_mem.sroa.0, ptr noundef nonnull align 1 dereferenceable(128) %p0, i64 128, i1 false)
  call void @llvm.memcpy.p0.p0.i64(ptr noundef nonnull align 4 dereferenceable(12) %v183_mem.sroa.5.sroa.0, ptr noundef nonnull align 1 dereferenceable(12) %v129_mem.sroa.3.0.p0.sroa_idx, i64 12, i1 false)
  call void @llvm.memcpy.p0.p0.i64(ptr noundef nonnull align 8 dereferenceable(128) %return_storage, ptr noundef nonnull align 8 dereferenceable(128) %v183_mem.sroa.0, i64 128, i1 false)
  %v183_mem.sroa.3.0.return_storage.sroa_idx = getelementptr inbounds nuw i8, ptr %return_storage, i64 128
  store i32 %v183_mem.sroa.3.0, ptr %v183_mem.sroa.3.0.return_storage.sroa_idx, align 8
  %v183_mem.sroa.5.0.return_storage.sroa_idx = getelementptr inbounds nuw i8, ptr %return_storage, i64 132
  call void @llvm.memcpy.p0.p0.i64(ptr noundef nonnull align 4 dereferenceable(12) %v183_mem.sroa.5.0.return_storage.sroa_idx, ptr noundef nonnull align 4 dereferenceable(12) %v183_mem.sroa.5.sroa.0, i64 12, i1 false)
  %v183_mem.sroa.5.sroa.3.0.v183_mem.sroa.5.0.return_storage.sroa_idx.sroa_idx = getelementptr inbounds nuw i8, ptr %return_storage, i64 144
  store i32 %v133, ptr %v183_mem.sroa.5.sroa.3.0.v183_mem.sroa.5.0.return_storage.sroa_idx.sroa_idx, align 8
  %v183_mem.sroa.5.sroa.5.0.v183_mem.sroa.5.0.return_storage.sroa_idx.sroa_idx = getelementptr inbounds nuw i8, ptr %return_storage, i64 148
  store i32 %v128_pair2139, ptr %v183_mem.sroa.5.sroa.5.0.v183_mem.sroa.5.0.return_storage.sroa_idx.sroa_idx, align 4
  %v183_mem.sroa.5.sroa.7.0.v183_mem.sroa.5.0.return_storage.sroa_idx.sroa_idx = getelementptr inbounds nuw i8, ptr %return_storage, i64 152
  store i64 %v129_mem.sroa.8.0.copyload, ptr %v183_mem.sroa.5.sroa.7.0.v183_mem.sroa.5.0.return_storage.sroa_idx.sroa_idx, align 8
  %v183_mem.sroa.5.sroa.9.0.v183_mem.sroa.5.0.return_storage.sroa_idx.sroa_idx = getelementptr inbounds nuw i8, ptr %return_storage, i64 160
  store i64 %v129_mem.sroa.9.0.copyload, ptr %v183_mem.sroa.5.sroa.9.0.v183_mem.sroa.5.0.return_storage.sroa_idx.sroa_idx, align 8
  %v183_mem.sroa.5.sroa.11.0.v183_mem.sroa.5.0.return_storage.sroa_idx.sroa_idx = getelementptr inbounds nuw i8, ptr %return_storage, i64 168
  store i32 %v129_mem.sroa.10.0.copyload, ptr %v183_mem.sroa.5.sroa.11.0.v183_mem.sroa.5.0.return_storage.sroa_idx.sroa_idx, align 8
  %v183_mem.sroa.5.sroa.13.0.v183_mem.sroa.5.0.return_storage.sroa_idx.sroa_idx = getelementptr inbounds nuw i8, ptr %return_storage, i64 172
  store i32 %v129_mem.sroa.11.0.copyload, ptr %v183_mem.sroa.5.sroa.13.0.v183_mem.sroa.5.0.return_storage.sroa_idx.sroa_idx, align 4
  %v183_mem.sroa.5.sroa.15.0.v183_mem.sroa.5.0.return_storage.sroa_idx.sroa_idx = getelementptr inbounds nuw i8, ptr %return_storage, i64 176
  store i64 %v129_mem.sroa.12.0.copyload, ptr %v183_mem.sroa.5.sroa.15.0.v183_mem.sroa.5.0.return_storage.sroa_idx.sroa_idx, align 8
  br label %common.ret

b91:                                              ; preds = %b0
  %v189_ptr = getelementptr i8, ptr %p0, i64 136
  %v189 = load i32, ptr %v189_ptr, align 4
  switch i32 %v189, label %b125 [
    i32 1, label %b104.thread
    i32 2, label %b105
    i32 3, label %b120
  ]

b104.thread:                                      ; preds = %b91
  %v192_ptr = getelementptr i8, ptr %p0, i64 140
  %v192 = load i32, ptr %v192_ptr, align 4
  %v194 = icmp eq i32 %v192, 1
  %. = select i1 %v194, i8 114, i8 0
  %v199 = icmp eq i32 %v192, 2
  %v201 = select i1 %v199, i8 117, i8 %.
  %v204 = icmp eq i32 %v192, 3
  %v206 = select i1 %v204, i8 101, i8 %v201
  br label %b125

b105:                                             ; preds = %b91
  %v212_ptr = getelementptr i8, ptr %p0, i64 140
  %v212 = load i32, ptr %v212_ptr, align 4
  %v214 = icmp eq i32 %v212, 1
  %.v207 = select i1 %v214, i8 97, i8 0
  %v219 = icmp eq i32 %v212, 2
  %v221 = select i1 %v219, i8 108, i8 %.v207
  %v224 = icmp eq i32 %v212, 3
  %v226 = select i1 %v224, i8 115, i8 %v221
  %v229 = icmp eq i32 %v212, 4
  %v231 = select i1 %v229, i8 101, i8 %v226
  br label %b125

b120:                                             ; preds = %b91
  %v237_ptr = getelementptr i8, ptr %p0, i64 140
  %v237 = load i32, ptr %v237_ptr, align 4
  %v239 = icmp eq i32 %v237, 1
  %.1 = select i1 %v239, i8 117, i8 108
  br label %b125

b125:                                             ; preds = %b91, %b105, %b104.thread, %b120
  %v2332124 = phi i32 [ 4, %b120 ], [ 4, %b104.thread ], [ 5, %b105 ], [ 4, %b91 ]
  %v243 = phi i8 [ %.1, %b120 ], [ %v206, %b104.thread ], [ %v231, %b105 ], [ 0, %b91 ]
  %v244.not = icmp eq i8 %p1, %v243
  br i1 %v244.not, label %b128, label %b126

b126:                                             ; preds = %b125
  %v246_ptr = getelementptr i8, ptr %p0, i64 48
  %v246 = load i64, ptr %v246_ptr, align 8
  %v1_mem.sroa.3.0.p0.sroa_idx.i1262 = getelementptr inbounds nuw i8, ptr %p0, i64 172
  %v1_mem.sroa.3.0.copyload.i1263 = load i32, ptr %v1_mem.sroa.3.0.p0.sroa_idx.i1262, align 1
  tail call void @llvm.memmove.p0.p0.i64(ptr noundef nonnull align 8 dereferenceable(168) %return_storage, ptr noundef nonnull align 1 dereferenceable(168) %p0, i64 168, i1 false)
  %v247_mem.sroa.2.0.return_storage.sroa_idx = getelementptr inbounds nuw i8, ptr %return_storage, i64 168
  store i32 1, ptr %v247_mem.sroa.2.0.return_storage.sroa_idx, align 8
  %v247_mem.sroa.3.0.return_storage.sroa_idx = getelementptr inbounds nuw i8, ptr %return_storage, i64 172
  store i32 %v1_mem.sroa.3.0.copyload.i1263, ptr %v247_mem.sroa.3.0.return_storage.sroa_idx, align 4
  %v247_mem.sroa.4.0.return_storage.sroa_idx = getelementptr inbounds nuw i8, ptr %return_storage, i64 176
  store i64 %v246, ptr %v247_mem.sroa.4.0.return_storage.sroa_idx, align 8
  br label %common.ret

b128:                                             ; preds = %b125
  %v248_ptr = getelementptr i8, ptr %p0, i64 140
  %v249 = load i32, ptr %v248_ptr, align 4
  %v251_pair = tail call { i32, i1 } @llvm.uadd.with.overflow.i32(i32 %v249, i32 1)
  %v251_overflow = extractvalue { i32, i1 } %v251_pair, 1
  br i1 %v251_overflow, label %v251_trap, label %v251_ok

v251_trap:                                        ; preds = %b128
  tail call void @llvm.trap()
  unreachable

v251_ok:                                          ; preds = %b128
  %v251 = extractvalue { i32, i1 } %v251_pair, 0
  %v252_mem.sroa.4.0.p0.sroa_idx = getelementptr inbounds nuw i8, ptr %p0, i64 144
  call void @llvm.memcpy.p0.p0.i64(ptr noundef nonnull align 8 dereferenceable(40) %v252_mem.sroa.4, ptr noundef nonnull align 1 dereferenceable(40) %v252_mem.sroa.4.0.p0.sroa_idx, i64 40, i1 false)
  %v254 = icmp eq i32 %v251, %v2332124
  br i1 %v254, label %b129, label %b131

b129:                                             ; preds = %v251_ok
  call void @llvm.memcpy.p0.p0.i64(ptr noundef nonnull align 8 dereferenceable(140) %v257_mem, ptr noundef nonnull align 1 dereferenceable(140) %p0, i64 140, i1 false)
  %v252_mem.sroa.3.0.v257_mem.sroa_idx = getelementptr inbounds nuw i8, ptr %v257_mem, i64 140
  store i32 %v2332124, ptr %v252_mem.sroa.3.0.v257_mem.sroa_idx, align 4
  %v252_mem.sroa.4.0.v257_mem.sroa_idx = getelementptr inbounds nuw i8, ptr %v257_mem, i64 144
  call void @llvm.memcpy.p0.p0.i64(ptr noundef nonnull align 8 dereferenceable(40) %v252_mem.sroa.4.0.v257_mem.sroa_idx, ptr noundef nonnull align 1 dereferenceable(40) %v252_mem.sroa.4.0.p0.sroa_idx, i64 40, i1 false)
  %v257_part = getelementptr inbounds nuw i8, ptr %v257_mem, i64 128
  store i32 0, ptr %v257_part, align 8
  call void @liza___liza_json_done(ptr nonnull sret(%struct.JsonState) %v258_mem, ptr nonnull %v257_mem)
  call void @llvm.memcpy.p0.p0.i64(ptr noundef nonnull align 8 dereferenceable(184) %return_storage, ptr noundef nonnull align 8 dereferenceable(184) %v258_mem, i64 184, i1 false)
  br label %common.ret

b131:                                             ; preds = %v251_ok
  tail call void @llvm.memmove.p0.p0.i64(ptr noundef nonnull align 8 dereferenceable(140) %return_storage, ptr noundef nonnull align 1 dereferenceable(140) %p0, i64 140, i1 false)
  %v252_mem.sroa.3.0.return_storage.sroa_idx = getelementptr inbounds nuw i8, ptr %return_storage, i64 140
  store i32 %v251, ptr %v252_mem.sroa.3.0.return_storage.sroa_idx, align 4
  %v252_mem.sroa.4.0.return_storage.sroa_idx = getelementptr inbounds nuw i8, ptr %return_storage, i64 144
  call void @llvm.memcpy.p0.p0.i64(ptr noundef nonnull align 8 dereferenceable(40) %v252_mem.sroa.4.0.return_storage.sroa_idx, ptr noundef nonnull align 8 dereferenceable(40) %v252_mem.sroa.4, i64 40, i1 false)
  br label %common.ret

b132:                                             ; preds = %b0
  %13 = add i32 %v0, -10
  %or.cond = icmp ult i32 %13, 8
  br i1 %or.cond, label %b136, label %b137_to_b216

b136:                                             ; preds = %b132
  %14 = add i8 %p1, -48
  %v5.i1267 = icmp ult i8 %14, 10
  br i1 %v5.i1267, label %b138, label %b158

b138:                                             ; preds = %b136
  switch i32 %v0, label %b148 [
    i32 11, label %b140
    i32 10, label %b143
  ]

b140:                                             ; preds = %b138
  %v272_ptr = getelementptr i8, ptr %p0, i64 48
  %v272 = load i64, ptr %v272_ptr, align 8
  %v1_mem.sroa.3.0.p0.sroa_idx.i1268 = getelementptr inbounds nuw i8, ptr %p0, i64 172
  %v1_mem.sroa.3.0.copyload.i1269 = load i32, ptr %v1_mem.sroa.3.0.p0.sroa_idx.i1268, align 1
  tail call void @llvm.memmove.p0.p0.i64(ptr noundef nonnull align 8 dereferenceable(168) %return_storage, ptr noundef nonnull align 1 dereferenceable(168) %p0, i64 168, i1 false)
  %v273_mem.sroa.2.0.return_storage.sroa_idx = getelementptr inbounds nuw i8, ptr %return_storage, i64 168
  store i32 2, ptr %v273_mem.sroa.2.0.return_storage.sroa_idx, align 8
  %v273_mem.sroa.3.0.return_storage.sroa_idx = getelementptr inbounds nuw i8, ptr %return_storage, i64 172
  store i32 %v1_mem.sroa.3.0.copyload.i1269, ptr %v273_mem.sroa.3.0.return_storage.sroa_idx, align 4
  %v273_mem.sroa.4.0.return_storage.sroa_idx = getelementptr inbounds nuw i8, ptr %return_storage, i64 176
  store i64 %v272, ptr %v273_mem.sroa.4.0.return_storage.sroa_idx, align 8
  br label %common.ret

b143:                                             ; preds = %b138
  %v278 = icmp eq i8 %p1, 48
  %v281_mem.sroa.4.0.p0.sroa_idx = getelementptr inbounds nuw i8, ptr %p0, i64 132
  call void @llvm.memcpy.p0.p0.i64(ptr noundef nonnull align 8 dereferenceable(128) %v285_mem.sroa.0, ptr noundef nonnull align 1 dereferenceable(128) %p0, i64 128, i1 false)
  call void @llvm.memcpy.p0.p0.i64(ptr noundef nonnull align 4 dereferenceable(52) %v285_mem.sroa.4, ptr noundef nonnull align 1 dereferenceable(52) %v281_mem.sroa.4.0.p0.sroa_idx, i64 52, i1 false)
  %.2140 = select i1 %v278, i32 11, i32 12
  call void @llvm.memcpy.p0.p0.i64(ptr noundef nonnull align 8 dereferenceable(128) %v286_mem.sroa.0, ptr noundef nonnull align 8 dereferenceable(128) %v285_mem.sroa.0, i64 128, i1 false)
  call void @llvm.memcpy.p0.p0.i64(ptr noundef nonnull align 4 dereferenceable(52) %v286_mem.sroa.7, ptr noundef nonnull align 4 dereferenceable(52) %v285_mem.sroa.4, i64 52, i1 false)
  br label %b151

b148:                                             ; preds = %b138
  %v286_next.sroa.6.0.p0.sroa_idx = getelementptr inbounds nuw i8, ptr %p0, i64 132
  call void @llvm.memcpy.p0.p0.i64(ptr noundef nonnull align 8 dereferenceable(128) %v286_mem.sroa.0, ptr noundef nonnull align 1 dereferenceable(128) %p0, i64 128, i1 false)
  call void @llvm.memcpy.p0.p0.i64(ptr noundef nonnull align 4 dereferenceable(52) %v286_mem.sroa.7, ptr noundef nonnull align 1 dereferenceable(52) %v286_next.sroa.6.0.p0.sroa_idx, i64 52, i1 false)
  %v289 = icmp eq i32 %v0, 13
  br i1 %v289, label %b151.thread, label %b151

b151.thread:                                      ; preds = %b148
  call void @llvm.memcpy.p0.p0.i64(ptr noundef nonnull align 8 dereferenceable(128) %v293_mem.sroa.0, ptr noundef nonnull align 1 dereferenceable(128) %p0, i64 128, i1 false)
  call void @llvm.memcpy.p0.p0.i64(ptr noundef nonnull align 4 dereferenceable(52) %v293_mem.sroa.7, ptr noundef nonnull align 1 dereferenceable(52) %v286_next.sroa.6.0.p0.sroa_idx, i64 52, i1 false)
  br label %b157

b151:                                             ; preds = %b148, %b143
  %v286_mem.sroa.4.02127 = phi i32 [ %.2140, %b143 ], [ %v0, %b148 ]
  call void @llvm.memcpy.p0.p0.i64(ptr noundef nonnull align 8 dereferenceable(128) %v293_mem.sroa.0, ptr noundef nonnull align 8 dereferenceable(128) %v286_mem.sroa.0, i64 128, i1 false)
  call void @llvm.memcpy.p0.p0.i64(ptr noundef nonnull align 4 dereferenceable(52) %v293_mem.sroa.7, ptr noundef nonnull align 4 dereferenceable(52) %v286_mem.sroa.7, i64 52, i1 false)
  %15 = add nsw i32 %v286_mem.sroa.4.02127, -15
  %v301 = icmp ult i32 %15, 2
  br i1 %v301, label %b155, label %b157

b155:                                             ; preds = %b151
  br label %b157

b157:                                             ; preds = %b151, %b151.thread, %b155
  %v293_mem.sroa.0.sink = phi ptr [ %v286_mem.sroa.0, %b155 ], [ %v293_mem.sroa.0, %b151.thread ], [ %v293_mem.sroa.0, %b151 ]
  %v293_mem.sroa.7.sink = phi ptr [ %v286_mem.sroa.7, %b155 ], [ %v293_mem.sroa.7, %b151.thread ], [ %v293_mem.sroa.7, %b151 ]
  %v305_mem.sroa.3.0 = phi i32 [ 17, %b155 ], [ 14, %b151.thread ], [ %v286_mem.sroa.4.02127, %b151 ]
  call void @llvm.memcpy.p0.p0.i64(ptr noundef nonnull align 8 dereferenceable(128) %v305_mem.sroa.0, ptr noundef nonnull align 8 dereferenceable(128) %v293_mem.sroa.0.sink, i64 128, i1 false)
  call void @llvm.memcpy.p0.p0.i64(ptr noundef nonnull align 4 dereferenceable(52) %v305_mem.sroa.5, ptr noundef nonnull align 4 dereferenceable(52) %v293_mem.sroa.7.sink, i64 52, i1 false)
  call void @llvm.memcpy.p0.p0.i64(ptr noundef nonnull align 8 dereferenceable(128) %return_storage, ptr noundef nonnull align 8 dereferenceable(128) %v305_mem.sroa.0, i64 128, i1 false)
  %v305_mem.sroa.3.0.return_storage.sroa_idx = getelementptr inbounds nuw i8, ptr %return_storage, i64 128
  store i32 %v305_mem.sroa.3.0, ptr %v305_mem.sroa.3.0.return_storage.sroa_idx, align 8
  %v305_mem.sroa.5.0.return_storage.sroa_idx = getelementptr inbounds nuw i8, ptr %return_storage, i64 132
  call void @llvm.memcpy.p0.p0.i64(ptr noundef nonnull align 4 dereferenceable(52) %v305_mem.sroa.5.0.return_storage.sroa_idx, ptr noundef nonnull align 4 dereferenceable(52) %v305_mem.sroa.5, i64 52, i1 false)
  br label %common.ret

b158:                                             ; preds = %b136
  %v308 = icmp eq i32 %v0, 11
  br i1 %v308, label %b162, label %b159

b159:                                             ; preds = %b158
  %v312 = icmp eq i32 %v0, 12
  %v316 = icmp eq i8 %p1, 46
  %or.cond6 = select i1 %v312, i1 %v316, i1 false
  br i1 %or.cond6, label %b165, label %b167

b162:                                             ; preds = %b158
  switch i8 %p1, label %b210 [
    i8 46, label %b165
    i8 101, label %b180
    i8 69, label %b180
    i8 32, label %b215
    i8 10, label %b215
    i8 9, label %b215
    i8 13, label %b215
    i8 93, label %b215
    i8 44, label %b215
    i8 125, label %b215
  ]

b165:                                             ; preds = %b162, %b159
  %v320_mem.sroa.3.0.p0.sroa_idx = getelementptr inbounds nuw i8, ptr %p0, i64 132
  call void @llvm.memcpy.p0.p0.i64(ptr noundef nonnull align 4 dereferenceable(52) %v320_mem.sroa.3, ptr noundef nonnull align 1 dereferenceable(52) %v320_mem.sroa.3.0.p0.sroa_idx, i64 52, i1 false)
  tail call void @llvm.memmove.p0.p0.i64(ptr noundef nonnull align 8 dereferenceable(128) %return_storage, ptr noundef nonnull align 1 dereferenceable(128) %p0, i64 128, i1 false)
  %v320_mem.sroa.2.0.return_storage.sroa_idx = getelementptr inbounds nuw i8, ptr %return_storage, i64 128
  store i32 13, ptr %v320_mem.sroa.2.0.return_storage.sroa_idx, align 8
  %v320_mem.sroa.3.0.return_storage.sroa_idx = getelementptr inbounds nuw i8, ptr %return_storage, i64 132
  call void @llvm.memcpy.p0.p0.i64(ptr noundef nonnull align 4 dereferenceable(52) %v320_mem.sroa.3.0.return_storage.sroa_idx, ptr noundef nonnull align 4 dereferenceable(52) %v320_mem.sroa.3, i64 52, i1 false)
  br label %common.ret

b167:                                             ; preds = %b159
  switch i32 %v0, label %b203 [
    i32 11, label %b174
    i32 12, label %b174
    i32 14, label %b174
    i32 15, label %b183
    i32 10, label %b201
    i32 13, label %b201
    i32 16, label %b201
  ]

b174:                                             ; preds = %b167, %b167, %b167
  switch i8 %p1, label %b191 [
    i8 101, label %b180
    i8 69, label %b180
  ]

b180:                                             ; preds = %b162, %b162, %b174, %b174
  %v344_mem.sroa.3.0.p0.sroa_idx = getelementptr inbounds nuw i8, ptr %p0, i64 132
  call void @llvm.memcpy.p0.p0.i64(ptr noundef nonnull align 4 dereferenceable(52) %v344_mem.sroa.3, ptr noundef nonnull align 1 dereferenceable(52) %v344_mem.sroa.3.0.p0.sroa_idx, i64 52, i1 false)
  tail call void @llvm.memmove.p0.p0.i64(ptr noundef nonnull align 8 dereferenceable(128) %return_storage, ptr noundef nonnull align 1 dereferenceable(128) %p0, i64 128, i1 false)
  %v344_mem.sroa.2.0.return_storage.sroa_idx = getelementptr inbounds nuw i8, ptr %return_storage, i64 128
  store i32 15, ptr %v344_mem.sroa.2.0.return_storage.sroa_idx, align 8
  %v344_mem.sroa.3.0.return_storage.sroa_idx = getelementptr inbounds nuw i8, ptr %return_storage, i64 132
  call void @llvm.memcpy.p0.p0.i64(ptr noundef nonnull align 4 dereferenceable(52) %v344_mem.sroa.3.0.return_storage.sroa_idx, ptr noundef nonnull align 4 dereferenceable(52) %v344_mem.sroa.3, i64 52, i1 false)
  br label %common.ret

b183:                                             ; preds = %b167
  switch i8 %p1, label %b201 [
    i8 45, label %b189
    i8 43, label %b189
  ]

b189:                                             ; preds = %b183, %b183
  %v358_mem.sroa.3.0.p0.sroa_idx = getelementptr inbounds nuw i8, ptr %p0, i64 132
  call void @llvm.memcpy.p0.p0.i64(ptr noundef nonnull align 4 dereferenceable(52) %v358_mem.sroa.3, ptr noundef nonnull align 1 dereferenceable(52) %v358_mem.sroa.3.0.p0.sroa_idx, i64 52, i1 false)
  tail call void @llvm.memmove.p0.p0.i64(ptr noundef nonnull align 8 dereferenceable(128) %return_storage, ptr noundef nonnull align 1 dereferenceable(128) %p0, i64 128, i1 false)
  %v358_mem.sroa.2.0.return_storage.sroa_idx = getelementptr inbounds nuw i8, ptr %return_storage, i64 128
  store i32 16, ptr %v358_mem.sroa.2.0.return_storage.sroa_idx, align 8
  %v358_mem.sroa.3.0.return_storage.sroa_idx = getelementptr inbounds nuw i8, ptr %return_storage, i64 132
  call void @llvm.memcpy.p0.p0.i64(ptr noundef nonnull align 4 dereferenceable(52) %v358_mem.sroa.3.0.return_storage.sroa_idx, ptr noundef nonnull align 4 dereferenceable(52) %v358_mem.sroa.3, i64 52, i1 false)
  br label %common.ret

b191:                                             ; preds = %b174
  %cond = icmp eq i32 %v0, 13
  br i1 %cond, label %b201, label %b203

b201:                                             ; preds = %b191, %b167, %b167, %b167, %b183
  %v378_ptr = getelementptr i8, ptr %p0, i64 48
  %v378 = load i64, ptr %v378_ptr, align 8
  %v1_mem.sroa.3.0.p0.sroa_idx.i1273 = getelementptr inbounds nuw i8, ptr %p0, i64 172
  %v1_mem.sroa.3.0.copyload.i1274 = load i32, ptr %v1_mem.sroa.3.0.p0.sroa_idx.i1273, align 1
  tail call void @llvm.memmove.p0.p0.i64(ptr noundef nonnull align 8 dereferenceable(168) %return_storage, ptr noundef nonnull align 1 dereferenceable(168) %p0, i64 168, i1 false)
  %v379_mem.sroa.2.0.return_storage.sroa_idx = getelementptr inbounds nuw i8, ptr %return_storage, i64 168
  store i32 2, ptr %v379_mem.sroa.2.0.return_storage.sroa_idx, align 8
  %v379_mem.sroa.3.0.return_storage.sroa_idx = getelementptr inbounds nuw i8, ptr %return_storage, i64 172
  store i32 %v1_mem.sroa.3.0.copyload.i1274, ptr %v379_mem.sroa.3.0.return_storage.sroa_idx, align 4
  %v379_mem.sroa.4.0.return_storage.sroa_idx = getelementptr inbounds nuw i8, ptr %return_storage, i64 176
  store i64 %v378, ptr %v379_mem.sroa.4.0.return_storage.sroa_idx, align 8
  br label %common.ret

b203:                                             ; preds = %b191, %b167
  switch i8 %p1, label %b210 [
    i8 32, label %b215
    i8 10, label %b215
    i8 9, label %b215
    i8 13, label %b215
    i8 93, label %b215
    i8 44, label %b215
    i8 125, label %b215
  ]

b210:                                             ; preds = %b162, %b203
  %v395_ptr = getelementptr i8, ptr %p0, i64 48
  %v395 = load i64, ptr %v395_ptr, align 8
  %v1_mem.sroa.3.0.p0.sroa_idx.i1278 = getelementptr inbounds nuw i8, ptr %p0, i64 172
  %v1_mem.sroa.3.0.copyload.i1279 = load i32, ptr %v1_mem.sroa.3.0.p0.sroa_idx.i1278, align 1
  tail call void @llvm.memmove.p0.p0.i64(ptr noundef nonnull align 8 dereferenceable(168) %return_storage, ptr noundef nonnull align 1 dereferenceable(168) %p0, i64 168, i1 false)
  %v396_mem.sroa.2.0.return_storage.sroa_idx = getelementptr inbounds nuw i8, ptr %return_storage, i64 168
  store i32 2, ptr %v396_mem.sroa.2.0.return_storage.sroa_idx, align 8
  %v396_mem.sroa.3.0.return_storage.sroa_idx = getelementptr inbounds nuw i8, ptr %return_storage, i64 172
  store i32 %v1_mem.sroa.3.0.copyload.i1279, ptr %v396_mem.sroa.3.0.return_storage.sroa_idx, align 4
  %v396_mem.sroa.4.0.return_storage.sroa_idx = getelementptr inbounds nuw i8, ptr %return_storage, i64 176
  store i64 %v395, ptr %v396_mem.sroa.4.0.return_storage.sroa_idx, align 8
  br label %common.ret

b215:                                             ; preds = %b162, %b162, %b162, %b162, %b162, %b162, %b162, %b203, %b203, %b203, %b203, %b203, %b203, %b203
  call void @llvm.memcpy.p0.p0.i64(ptr noundef nonnull align 8 dereferenceable(184) %v399_mem, ptr noundef nonnull align 1 dereferenceable(184) %p0, i64 184, i1 false)
  %v399_part = getelementptr inbounds nuw i8, ptr %v399_mem, i64 128
  store i32 0, ptr %v399_part, align 8
  call void @liza___liza_json_done(ptr nonnull sret(%struct.JsonState) %v401_next, ptr nonnull %v399_mem)
  br label %b216

b216:                                             ; preds = %b137_to_b216, %b215
  %p0.sink = phi ptr [ %p0, %b137_to_b216 ], [ %v401_next, %b215 ]
  call void @llvm.memcpy.p0.p0.i64(ptr noundef nonnull align 8 dereferenceable(184) %v401_mem, ptr noundef nonnull align 1 dereferenceable(184) %p0.sink, i64 184, i1 false)
  switch i8 %p1, label %b219 [
    i8 32, label %b217
    i8 10, label %b217
    i8 9, label %b217
    i8 13, label %b217
  ]

b217:                                             ; preds = %b216, %b216, %b216, %b216
  call void @llvm.memcpy.p0.p0.i64(ptr noundef nonnull align 8 dereferenceable(184) %return_storage, ptr noundef nonnull align 8 dereferenceable(184) %v401_mem, i64 184, i1 false)
  br label %common.ret

b219:                                             ; preds = %b216
  %v404_ptr = getelementptr inbounds nuw i8, ptr %v401_mem, i64 120
  %v404 = load i32, ptr %v404_ptr, align 8
  %v406.not = icmp eq i32 %v404, 0
  br i1 %v406.not, label %b222, label %b220

b220:                                             ; preds = %b219
  %v407_ptr = getelementptr inbounds nuw i8, ptr %v401_mem, i64 56
  %v407.fca.16.gep795 = getelementptr inbounds nuw i8, ptr %v401_mem, i64 72
  %v407.fca.32.gep811 = getelementptr inbounds nuw i8, ptr %v401_mem, i64 88
  %v407.fca.48.gep827 = getelementptr inbounds nuw i8, ptr %v401_mem, i64 104
  %16 = load <16 x i8>, ptr %v407_ptr, align 8
  store <16 x i8> %16, ptr %v407_storage, align 16
  %v407.fca.16.gep = getelementptr inbounds nuw i8, ptr %v407_storage, i64 16
  %17 = load <16 x i8>, ptr %v407.fca.16.gep795, align 8
  store <16 x i8> %17, ptr %v407.fca.16.gep, align 16
  %v407.fca.32.gep = getelementptr inbounds nuw i8, ptr %v407_storage, i64 32
  %18 = load <16 x i8>, ptr %v407.fca.32.gep811, align 8
  store <16 x i8> %18, ptr %v407.fca.32.gep, align 16
  %v407.fca.48.gep = getelementptr inbounds nuw i8, ptr %v407_storage, i64 48
  %19 = load <16 x i8>, ptr %v407.fca.48.gep827, align 8
  store <16 x i8> %19, ptr %v407.fca.48.gep, align 16
  %v410_pair2138 = add i32 %v404, -1
  %v411_invalid = icmp ugt i32 %v410_pair2138, 63
  br i1 %v411_invalid, label %v411_trap, label %v411_ok

v411_trap:                                        ; preds = %b220
  call void @llvm.trap()
  unreachable

v411_ok:                                          ; preds = %b220
  %v411_offset = zext nneg i32 %v410_pair2138 to i64
  %v411_ptr = getelementptr [64 x i8], ptr %v407_storage, i64 0, i64 %v411_offset
  %v411 = load i8, ptr %v411_ptr, align 1
  br label %b222

b222:                                             ; preds = %b219, %v411_ok
  %v412 = phi i8 [ %v411, %v411_ok ], [ 0, %b219 ]
  switch i8 %p1, label %b240 [
    i8 93, label %b223
    i8 125, label %b232
  ]

b223:                                             ; preds = %b222
  %v412.off = add i8 %v412, -1
  %switch = icmp ult i8 %v412.off, 2
  br i1 %switch, label %b229, label %b240

b229:                                             ; preds = %b223
  %v426_pair = call { i32, i1 } @llvm.usub.with.overflow.i32(i32 %v404, i32 1)
  %v426_overflow = extractvalue { i32, i1 } %v426_pair, 1
  br i1 %v426_overflow, label %v426_trap, label %v426_ok

v426_trap:                                        ; preds = %b229
  call void @llvm.trap()
  unreachable

v426_ok:                                          ; preds = %b229
  %v426 = extractvalue { i32, i1 } %v426_pair, 0
  %v427_mem.sroa.3.0.v401_mem.sroa_idx = getelementptr inbounds nuw i8, ptr %v401_mem, i64 124
  call void @llvm.memcpy.p0.p0.i64(ptr noundef nonnull align 8 dereferenceable(120) %return_storage, ptr noundef nonnull align 8 dereferenceable(120) %v401_mem, i64 120, i1 false)
  %v427_mem.sroa.2.0.return_storage.sroa_idx = getelementptr inbounds nuw i8, ptr %return_storage, i64 120
  store i32 %v426, ptr %v427_mem.sroa.2.0.return_storage.sroa_idx, align 8
  %v427_mem.sroa.3.0.return_storage.sroa_idx = getelementptr inbounds nuw i8, ptr %return_storage, i64 124
  call void @llvm.memcpy.p0.p0.i64(ptr noundef nonnull align 4 dereferenceable(60) %v427_mem.sroa.3.0.return_storage.sroa_idx, ptr noundef nonnull align 4 dereferenceable(60) %v427_mem.sroa.3.0.v401_mem.sroa_idx, i64 60, i1 false)
  br label %common.ret

b232:                                             ; preds = %b222
  switch i8 %v412, label %b259 [
    i8 7, label %b238
    i8 4, label %b238
    i8 2, label %b246
    i8 5, label %b255
    i8 8, label %b264
  ]

b238:                                             ; preds = %b232, %b232
  %v441_pair = call { i32, i1 } @llvm.usub.with.overflow.i32(i32 %v404, i32 1)
  %v441_overflow = extractvalue { i32, i1 } %v441_pair, 1
  br i1 %v441_overflow, label %v441_trap, label %v441_ok

v441_trap:                                        ; preds = %b238
  call void @llvm.trap()
  unreachable

v441_ok:                                          ; preds = %b238
  %v441 = extractvalue { i32, i1 } %v441_pair, 0
  %v442_mem.sroa.3.0.v401_mem.sroa_idx = getelementptr inbounds nuw i8, ptr %v401_mem, i64 124
  call void @llvm.memcpy.p0.p0.i64(ptr noundef nonnull align 8 dereferenceable(120) %return_storage, ptr noundef nonnull align 8 dereferenceable(120) %v401_mem, i64 120, i1 false)
  %v442_mem.sroa.2.0.return_storage.sroa_idx = getelementptr inbounds nuw i8, ptr %return_storage, i64 120
  store i32 %v441, ptr %v442_mem.sroa.2.0.return_storage.sroa_idx, align 8
  %v442_mem.sroa.3.0.return_storage.sroa_idx = getelementptr inbounds nuw i8, ptr %return_storage, i64 124
  call void @llvm.memcpy.p0.p0.i64(ptr noundef nonnull align 4 dereferenceable(60) %v442_mem.sroa.3.0.return_storage.sroa_idx, ptr noundef nonnull align 4 dereferenceable(60) %v442_mem.sroa.3.0.v401_mem.sroa_idx, i64 60, i1 false)
  br label %common.ret

b240:                                             ; preds = %b223, %b222
  switch i8 %v412, label %b259 [
    i8 7, label %b244
    i8 2, label %b244
    i8 5, label %b253
    i8 4, label %b262
    i8 8, label %b262
  ]

b244:                                             ; preds = %b240, %b240
  %v450.not = icmp eq i8 %p1, 44
  br i1 %v450.not, label %b248, label %b246

b246:                                             ; preds = %b232, %b244
  %v452_ptr = getelementptr inbounds nuw i8, ptr %v401_mem, i64 48
  %v452 = load i64, ptr %v452_ptr, align 8
  %v1_mem.sroa.3.0.p0.sroa_idx.i1286 = getelementptr inbounds nuw i8, ptr %v401_mem, i64 172
  %v1_mem.sroa.3.0.copyload.i1287 = load i32, ptr %v1_mem.sroa.3.0.p0.sroa_idx.i1286, align 4
  call void @llvm.memcpy.p0.p0.i64(ptr noundef nonnull align 8 dereferenceable(168) %return_storage, ptr noundef nonnull align 8 dereferenceable(168) %v401_mem, i64 168, i1 false)
  %v453_mem.sroa.2.0.return_storage.sroa_idx = getelementptr inbounds nuw i8, ptr %return_storage, i64 168
  store i32 1, ptr %v453_mem.sroa.2.0.return_storage.sroa_idx, align 8
  %v453_mem.sroa.3.0.return_storage.sroa_idx = getelementptr inbounds nuw i8, ptr %return_storage, i64 172
  store i32 %v1_mem.sroa.3.0.copyload.i1287, ptr %v453_mem.sroa.3.0.return_storage.sroa_idx, align 4
  %v453_mem.sroa.4.0.return_storage.sroa_idx = getelementptr inbounds nuw i8, ptr %return_storage, i64 176
  store i64 %v452, ptr %v453_mem.sroa.4.0.return_storage.sroa_idx, align 8
  br label %common.ret

b248:                                             ; preds = %b244
  %v455 = icmp eq i8 %v412, 2
  %v456_ptr = getelementptr inbounds nuw i8, ptr %v401_mem, i64 56
  %20 = load <16 x i8>, ptr %v456_ptr, align 8
  %v456.fca.16.gep859 = getelementptr inbounds nuw i8, ptr %v401_mem, i64 72
  %21 = load <16 x i8>, ptr %v456.fca.16.gep859, align 8
  %v456.fca.32.gep875 = getelementptr inbounds nuw i8, ptr %v401_mem, i64 88
  %22 = load <16 x i8>, ptr %v456.fca.32.gep875, align 8
  %v456.fca.48.gep891 = getelementptr inbounds nuw i8, ptr %v401_mem, i64 104
  %23 = load <16 x i8>, ptr %v456.fca.48.gep891, align 8
  %v459_pair = call { i32, i1 } @llvm.usub.with.overflow.i32(i32 %v404, i32 1)
  %v459 = extractvalue { i32, i1 } %v459_pair, 0
  %v459_overflow = extractvalue { i32, i1 } %v459_pair, 1
  br i1 %v455, label %b249, label %b250

b249:                                             ; preds = %b248
  br i1 %v459_overflow, label %v459_trap, label %v459_ok

v459_trap:                                        ; preds = %b249
  call void @llvm.trap()
  unreachable

v459_ok:                                          ; preds = %b249
  %v460_invalid = icmp ugt i32 %v459, 63
  br i1 %v460_invalid, label %v460_trap, label %b251

v460_trap:                                        ; preds = %v459_ok
  call void @llvm.trap()
  unreachable

b250:                                             ; preds = %b248
  br i1 %v459_overflow, label %v467_trap, label %v467_ok

v467_trap:                                        ; preds = %b250
  call void @llvm.trap()
  unreachable

v467_ok:                                          ; preds = %b250
  %v468_invalid = icmp ugt i32 %v459, 63
  br i1 %v468_invalid, label %v468_trap, label %b251

v468_trap:                                        ; preds = %v467_ok
  call void @llvm.trap()
  unreachable

b251:                                             ; preds = %v467_ok, %v459_ok
  %v470_scratch.sink2269.sroa.phi = phi ptr [ %v470_scratch.sink2269.sroa.gep, %v459_ok ], [ %v470_scratch.sink2269.sroa.gep2407, %v467_ok ]
  %v470_scratch.sink2269.sroa.phi2408 = phi ptr [ %v470_scratch.sink2269.sroa.gep2409, %v459_ok ], [ %v470_scratch.sink2269.sroa.gep2410, %v467_ok ]
  %v470_scratch.sink2269.sroa.phi2411 = phi ptr [ %v470_scratch.sink2269.sroa.gep2412, %v459_ok ], [ %v470_scratch.sink2269.sroa.gep2413, %v467_ok ]
  %v470_scratch.sink2269 = phi ptr [ %v462_scratch, %v459_ok ], [ %v470_scratch, %v467_ok ]
  %.sink2141 = phi i8 [ 3, %v459_ok ], [ 8, %v467_ok ]
  %v468_offset = zext nneg i32 %v459 to i64
  store <16 x i8> %20, ptr %v470_scratch.sink2269, align 1
  store <16 x i8> %21, ptr %v470_scratch.sink2269.sroa.phi, align 1
  store <16 x i8> %22, ptr %v470_scratch.sink2269.sroa.phi2408, align 1
  store <16 x i8> %23, ptr %v470_scratch.sink2269.sroa.phi2411, align 1
  %v470_ptr = getelementptr [64 x i8], ptr %v470_scratch.sink2269, i64 0, i64 %v468_offset
  store i8 %.sink2141, ptr %v470_ptr, align 1
  call void @llvm.memcpy.p0.p0.i64(ptr noundef nonnull align 8 dereferenceable(56) %v472_mem.sroa.0, ptr noundef nonnull align 8 dereferenceable(56) %v401_mem, i64 56, i1 false)
  call void @llvm.memcpy.p0.p0.i64(ptr noundef nonnull align 8 dereferenceable(64) %v472_mem.sroa.131, ptr noundef nonnull align 8 dereferenceable(64) %v404_ptr, i64 64, i1 false)
  call void @llvm.memcpy.p0.p0.i64(ptr noundef nonnull align 8 dereferenceable(56) %return_storage, ptr noundef nonnull align 8 dereferenceable(56) %v472_mem.sroa.0, i64 56, i1 false)
  %v472_mem.sroa.3.0.return_storage.sroa_idx = getelementptr inbounds nuw i8, ptr %return_storage, i64 56
  %24 = load <16 x i8>, ptr %v470_scratch.sink2269, align 1
  store <16 x i8> %24, ptr %v472_mem.sroa.3.0.return_storage.sroa_idx, align 8
  %v472_mem.sroa.35.0.return_storage.sroa_idx = getelementptr inbounds nuw i8, ptr %return_storage, i64 72
  %25 = load <16 x i8>, ptr %v470_scratch.sink2269.sroa.phi, align 1
  store <16 x i8> %25, ptr %v472_mem.sroa.35.0.return_storage.sroa_idx, align 8
  %v472_mem.sroa.67.0.return_storage.sroa_idx = getelementptr inbounds nuw i8, ptr %return_storage, i64 88
  %26 = load <16 x i8>, ptr %v470_scratch.sink2269.sroa.phi2408, align 1
  store <16 x i8> %26, ptr %v472_mem.sroa.67.0.return_storage.sroa_idx, align 8
  %v472_mem.sroa.99.0.return_storage.sroa_idx = getelementptr inbounds nuw i8, ptr %return_storage, i64 104
  %27 = load <16 x i8>, ptr %v470_scratch.sink2269.sroa.phi2411, align 1
  store <16 x i8> %27, ptr %v472_mem.sroa.99.0.return_storage.sroa_idx, align 8
  %v472_mem.sroa.131.0.return_storage.sroa_idx = getelementptr inbounds nuw i8, ptr %return_storage, i64 120
  call void @llvm.memcpy.p0.p0.i64(ptr noundef nonnull align 8 dereferenceable(64) %v472_mem.sroa.131.0.return_storage.sroa_idx, ptr noundef nonnull align 8 dereferenceable(64) %v472_mem.sroa.131, i64 64, i1 false)
  br label %common.ret

b253:                                             ; preds = %b240
  %v476.not = icmp eq i8 %p1, 58
  br i1 %v476.not, label %b257, label %b255

b255:                                             ; preds = %b232, %b253
  %v478_ptr = getelementptr inbounds nuw i8, ptr %v401_mem, i64 48
  %v478 = load i64, ptr %v478_ptr, align 8
  %v1_mem.sroa.3.0.p0.sroa_idx.i1291 = getelementptr inbounds nuw i8, ptr %v401_mem, i64 172
  %v1_mem.sroa.3.0.copyload.i1292 = load i32, ptr %v1_mem.sroa.3.0.p0.sroa_idx.i1291, align 4
  call void @llvm.memcpy.p0.p0.i64(ptr noundef nonnull align 8 dereferenceable(168) %return_storage, ptr noundef nonnull align 8 dereferenceable(168) %v401_mem, i64 168, i1 false)
  %v479_mem.sroa.2.0.return_storage.sroa_idx = getelementptr inbounds nuw i8, ptr %return_storage, i64 168
  store i32 1, ptr %v479_mem.sroa.2.0.return_storage.sroa_idx, align 8
  %v479_mem.sroa.3.0.return_storage.sroa_idx = getelementptr inbounds nuw i8, ptr %return_storage, i64 172
  store i32 %v1_mem.sroa.3.0.copyload.i1292, ptr %v479_mem.sroa.3.0.return_storage.sroa_idx, align 4
  %v479_mem.sroa.4.0.return_storage.sroa_idx = getelementptr inbounds nuw i8, ptr %return_storage, i64 176
  store i64 %v478, ptr %v479_mem.sroa.4.0.return_storage.sroa_idx, align 8
  br label %common.ret

b257:                                             ; preds = %b253
  %v480_ptr = getelementptr inbounds nuw i8, ptr %v401_mem, i64 56
  %28 = load <16 x i8>, ptr %v480_ptr, align 8
  %v480.fca.16.gep987 = getelementptr inbounds nuw i8, ptr %v401_mem, i64 72
  %29 = load <16 x i8>, ptr %v480.fca.16.gep987, align 8
  %v480.fca.32.gep1003 = getelementptr inbounds nuw i8, ptr %v401_mem, i64 88
  %30 = load <16 x i8>, ptr %v480.fca.32.gep1003, align 8
  %v480.fca.48.gep1019 = getelementptr inbounds nuw i8, ptr %v401_mem, i64 104
  %31 = load <16 x i8>, ptr %v480.fca.48.gep1019, align 8
  %v483_pair = call { i32, i1 } @llvm.usub.with.overflow.i32(i32 %v404, i32 1)
  %v483 = extractvalue { i32, i1 } %v483_pair, 0
  %v483_overflow = extractvalue { i32, i1 } %v483_pair, 1
  br i1 %v483_overflow, label %v483_trap, label %v483_ok

v483_trap:                                        ; preds = %b257
  call void @llvm.trap()
  unreachable

v483_ok:                                          ; preds = %b257
  %v484_invalid = icmp ugt i32 %v483, 63
  br i1 %v484_invalid, label %v484_trap, label %v484_ok

v484_trap:                                        ; preds = %v483_ok
  call void @llvm.trap()
  unreachable

v484_ok:                                          ; preds = %v483_ok
  %v484_offset = zext nneg i32 %v483 to i64
  store <16 x i8> %28, ptr %v486_scratch, align 16
  %v480.fca.16.gep428 = getelementptr inbounds nuw i8, ptr %v486_scratch, i64 16
  store <16 x i8> %29, ptr %v480.fca.16.gep428, align 16
  %v480.fca.32.gep460 = getelementptr inbounds nuw i8, ptr %v486_scratch, i64 32
  store <16 x i8> %30, ptr %v480.fca.32.gep460, align 16
  %v480.fca.48.gep492 = getelementptr inbounds nuw i8, ptr %v486_scratch, i64 48
  store <16 x i8> %31, ptr %v480.fca.48.gep492, align 16
  %v486_ptr = getelementptr [64 x i8], ptr %v486_scratch, i64 0, i64 %v484_offset
  store i8 6, ptr %v486_ptr, align 1
  call void @llvm.memcpy.p0.p0.i64(ptr noundef nonnull align 8 dereferenceable(56) %return_storage, ptr noundef nonnull align 8 dereferenceable(56) %v401_mem, i64 56, i1 false)
  %v487_mem.sroa.2.0.return_storage.sroa_idx = getelementptr inbounds nuw i8, ptr %return_storage, i64 56
  %32 = load <16 x i8>, ptr %v486_scratch, align 16
  store <16 x i8> %32, ptr %v487_mem.sroa.2.0.return_storage.sroa_idx, align 8
  %v487_mem.sroa.18.0.return_storage.sroa_idx = getelementptr inbounds nuw i8, ptr %return_storage, i64 72
  %33 = load <16 x i8>, ptr %v480.fca.16.gep428, align 16
  store <16 x i8> %33, ptr %v487_mem.sroa.18.0.return_storage.sroa_idx, align 8
  %v487_mem.sroa.34.0.return_storage.sroa_idx = getelementptr inbounds nuw i8, ptr %return_storage, i64 88
  %34 = load <16 x i8>, ptr %v480.fca.32.gep460, align 16
  store <16 x i8> %34, ptr %v487_mem.sroa.34.0.return_storage.sroa_idx, align 8
  %v487_mem.sroa.50.0.return_storage.sroa_idx = getelementptr inbounds nuw i8, ptr %return_storage, i64 104
  %35 = load <16 x i8>, ptr %v480.fca.48.gep492, align 16
  store <16 x i8> %35, ptr %v487_mem.sroa.50.0.return_storage.sroa_idx, align 8
  %v487_mem.sroa.66.0.return_storage.sroa_idx = getelementptr inbounds nuw i8, ptr %return_storage, i64 120
  call void @llvm.memcpy.p0.p0.i64(ptr noundef nonnull align 8 dereferenceable(64) %v487_mem.sroa.66.0.return_storage.sroa_idx, ptr noundef nonnull align 8 dereferenceable(64) %v404_ptr, i64 64, i1 false)
  br label %common.ret

b259:                                             ; preds = %b232, %b240
  %v509_ptr = getelementptr inbounds nuw i8, ptr %v401_mem, i64 124
  %v509 = load i1, ptr %v509_ptr, align 4
  %v510 = select i1 %v406.not, i1 %v509, i1 false
  br i1 %v510, label %b271, label %b273

b262:                                             ; preds = %b240, %b240
  %v495.not = icmp eq i8 %p1, 34
  br i1 %v495.not, label %b266, label %b264

b264:                                             ; preds = %b232, %b262
  %v497_ptr = getelementptr inbounds nuw i8, ptr %v401_mem, i64 48
  %v497 = load i64, ptr %v497_ptr, align 8
  %v1_mem.sroa.3.0.p0.sroa_idx.i1296 = getelementptr inbounds nuw i8, ptr %v401_mem, i64 172
  %v1_mem.sroa.3.0.copyload.i1297 = load i32, ptr %v1_mem.sroa.3.0.p0.sroa_idx.i1296, align 4
  call void @llvm.memcpy.p0.p0.i64(ptr noundef nonnull align 8 dereferenceable(168) %return_storage, ptr noundef nonnull align 8 dereferenceable(168) %v401_mem, i64 168, i1 false)
  %v498_mem.sroa.2.0.return_storage.sroa_idx = getelementptr inbounds nuw i8, ptr %return_storage, i64 168
  store i32 1, ptr %v498_mem.sroa.2.0.return_storage.sroa_idx, align 8
  %v498_mem.sroa.3.0.return_storage.sroa_idx = getelementptr inbounds nuw i8, ptr %return_storage, i64 172
  store i32 %v1_mem.sroa.3.0.copyload.i1297, ptr %v498_mem.sroa.3.0.return_storage.sroa_idx, align 4
  %v498_mem.sroa.4.0.return_storage.sroa_idx = getelementptr inbounds nuw i8, ptr %return_storage, i64 176
  store i64 %v497, ptr %v498_mem.sroa.4.0.return_storage.sroa_idx, align 8
  br label %common.ret

b266:                                             ; preds = %b262
  %v501_mem.sroa.5.0.v401_mem.sroa_idx = getelementptr inbounds nuw i8, ptr %v401_mem, i64 133
  store i1 true, ptr %v501_mem.sroa.3.sroa.0, align 4
  %v501_mem.sroa.3.sroa.0.0.v501_mem.sroa.3.sroa.0.0.v501_mem.sroa.3.sroa.0.0. = load i8, ptr %v501_mem.sroa.3.sroa.0, align 4
  call void @llvm.memcpy.p0.p0.i64(ptr noundef nonnull align 8 dereferenceable(128) %return_storage, ptr noundef nonnull align 8 dereferenceable(128) %v401_mem, i64 128, i1 false)
  %v504_mem.sroa.2.0.return_storage.sroa_idx = getelementptr inbounds nuw i8, ptr %return_storage, i64 128
  store i32 1, ptr %v504_mem.sroa.2.0.return_storage.sroa_idx, align 8
  %v504_mem.sroa.3.0.return_storage.sroa_idx = getelementptr inbounds nuw i8, ptr %return_storage, i64 132
  store i8 %v501_mem.sroa.3.sroa.0.0.v501_mem.sroa.3.sroa.0.0.v501_mem.sroa.3.sroa.0.0., ptr %v504_mem.sroa.3.0.return_storage.sroa_idx, align 4
  %v504_mem.sroa.3.sroa.2.0.v504_mem.sroa.3.0.return_storage.sroa_idx.sroa_idx = getelementptr inbounds nuw i8, ptr %return_storage, i64 133
  call void @llvm.memcpy.p0.p0.i64(ptr noundef nonnull align 1 dereferenceable(51) %v504_mem.sroa.3.sroa.2.0.v504_mem.sroa.3.0.return_storage.sroa_idx.sroa_idx, ptr noundef nonnull align 1 dereferenceable(51) %v501_mem.sroa.5.0.v401_mem.sroa_idx, i64 51, i1 false)
  br label %common.ret

b271:                                             ; preds = %b259
  %v512_ptr = getelementptr inbounds nuw i8, ptr %v401_mem, i64 48
  %v512 = load i64, ptr %v512_ptr, align 8
  %v1_mem.sroa.3.0.p0.sroa_idx.i1301 = getelementptr inbounds nuw i8, ptr %v401_mem, i64 172
  %v1_mem.sroa.3.0.copyload.i1302 = load i32, ptr %v1_mem.sroa.3.0.p0.sroa_idx.i1301, align 4
  call void @llvm.memcpy.p0.p0.i64(ptr noundef nonnull align 8 dereferenceable(168) %return_storage, ptr noundef nonnull align 8 dereferenceable(168) %v401_mem, i64 168, i1 false)
  %v513_mem.sroa.2.0.return_storage.sroa_idx = getelementptr inbounds nuw i8, ptr %return_storage, i64 168
  store i32 1, ptr %v513_mem.sroa.2.0.return_storage.sroa_idx, align 8
  %v513_mem.sroa.3.0.return_storage.sroa_idx = getelementptr inbounds nuw i8, ptr %return_storage, i64 172
  store i32 %v1_mem.sroa.3.0.copyload.i1302, ptr %v513_mem.sroa.3.0.return_storage.sroa_idx, align 4
  %v513_mem.sroa.4.0.return_storage.sroa_idx = getelementptr inbounds nuw i8, ptr %return_storage, i64 176
  store i64 %v512, ptr %v513_mem.sroa.4.0.return_storage.sroa_idx, align 8
  br label %common.ret

b273:                                             ; preds = %b259
  switch i8 %p1, label %b291 [
    i8 123, label %b277
    i8 91, label %b277
    i8 34, label %b286
    i8 45, label %b289
  ]

b277:                                             ; preds = %b273, %b273
  %v522 = icmp eq i32 %v404, 64
  br i1 %v522, label %b279, label %b281

b279:                                             ; preds = %b277
  %v524_ptr = getelementptr inbounds nuw i8, ptr %v401_mem, i64 48
  %v524 = load i64, ptr %v524_ptr, align 8
  %v1_mem.sroa.3.0.p0.sroa_idx.i1306 = getelementptr inbounds nuw i8, ptr %v401_mem, i64 172
  %v1_mem.sroa.3.0.copyload.i1307 = load i32, ptr %v1_mem.sroa.3.0.p0.sroa_idx.i1306, align 4
  call void @llvm.memcpy.p0.p0.i64(ptr noundef nonnull align 8 dereferenceable(168) %return_storage, ptr noundef nonnull align 8 dereferenceable(168) %v401_mem, i64 168, i1 false)
  %v525_mem.sroa.2.0.return_storage.sroa_idx = getelementptr inbounds nuw i8, ptr %return_storage, i64 168
  store i32 7, ptr %v525_mem.sroa.2.0.return_storage.sroa_idx, align 8
  %v525_mem.sroa.3.0.return_storage.sroa_idx = getelementptr inbounds nuw i8, ptr %return_storage, i64 172
  store i32 %v1_mem.sroa.3.0.copyload.i1307, ptr %v525_mem.sroa.3.0.return_storage.sroa_idx, align 4
  %v525_mem.sroa.4.0.return_storage.sroa_idx = getelementptr inbounds nuw i8, ptr %return_storage, i64 176
  store i64 %v524, ptr %v525_mem.sroa.4.0.return_storage.sroa_idx, align 8
  br label %common.ret

b281:                                             ; preds = %b277
  call void @liza___liza_json_done(ptr nonnull sret(%struct.JsonState) %v526_mem, ptr nonnull %v401_mem)
  %v528 = icmp eq i8 %p1, 91
  %v530_ptr = getelementptr inbounds nuw i8, ptr %v526_mem, i64 120
  %v530 = load i32, ptr %v530_ptr, align 8
  %v531_invalid = icmp ugt i32 %v530, 63
  br i1 %v528, label %b282, label %b283

b282:                                             ; preds = %b281
  br i1 %v531_invalid, label %v531_trap, label %v545_ok

v531_trap:                                        ; preds = %b282
  call void @llvm.trap()
  unreachable

b283:                                             ; preds = %b281
  br i1 %v531_invalid, label %v537_trap, label %v545_ok

v537_trap:                                        ; preds = %b283
  call void @llvm.trap()
  unreachable

v545_ok:                                          ; preds = %b283, %b282
  %v533_scratch.sink2398.sroa.phi = phi ptr [ %v533_scratch.sink2398.sroa.gep, %b282 ], [ %v533_scratch.sink2398.sroa.gep2400, %b283 ]
  %v533_scratch.sink2398.sroa.phi2401 = phi ptr [ %v533_scratch.sink2398.sroa.gep2402, %b282 ], [ %v533_scratch.sink2398.sroa.gep2403, %b283 ]
  %v533_scratch.sink2398.sroa.phi2404 = phi ptr [ %v533_scratch.sink2398.sroa.gep2405, %b282 ], [ %v533_scratch.sink2398.sroa.gep2406, %b283 ]
  %v533_scratch.sink2398 = phi ptr [ %v533_scratch, %b282 ], [ %v539_scratch, %b283 ]
  %.sink2270 = phi i8 [ 1, %b282 ], [ 4, %b283 ]
  %v529_ptr = getelementptr inbounds nuw i8, ptr %v526_mem, i64 56
  %v529.fca.48.gep315 = getelementptr inbounds nuw i8, ptr %v526_mem, i64 104
  %v529.fca.32.gep299 = getelementptr inbounds nuw i8, ptr %v526_mem, i64 88
  %v529.fca.16.gep283 = getelementptr inbounds nuw i8, ptr %v526_mem, i64 72
  %v531_offset = zext nneg i32 %v530 to i64
  %36 = load <16 x i8>, ptr %v529_ptr, align 8
  store <16 x i8> %36, ptr %v533_scratch.sink2398, align 1
  %37 = load <16 x i8>, ptr %v529.fca.16.gep283, align 8
  store <16 x i8> %37, ptr %v533_scratch.sink2398.sroa.phi, align 1
  %38 = load <16 x i8>, ptr %v529.fca.32.gep299, align 8
  store <16 x i8> %38, ptr %v533_scratch.sink2398.sroa.phi2401, align 1
  %39 = load <16 x i8>, ptr %v529.fca.48.gep315, align 8
  store <16 x i8> %39, ptr %v533_scratch.sink2398.sroa.phi2404, align 1
  %v533_ptr = getelementptr [64 x i8], ptr %v533_scratch.sink2398, i64 0, i64 %v531_offset
  store i8 %.sink2270, ptr %v533_ptr, align 1
  %v534_mem.sroa.131.0.v526_mem.sroa_idx = getelementptr inbounds nuw i8, ptr %v526_mem, i64 124
  call void @llvm.memcpy.p0.p0.i64(ptr noundef nonnull align 8 dereferenceable(56) %v541_mem.sroa.0.sroa.0, ptr noundef nonnull align 8 dereferenceable(56) %v526_mem, i64 56, i1 false)
  call void @llvm.memcpy.p0.p0.i64(ptr noundef nonnull align 4 dereferenceable(60) %v541_mem.sroa.5, ptr noundef nonnull align 4 dereferenceable(60) %v534_mem.sroa.131.0.v526_mem.sroa_idx, i64 60, i1 false)
  %v545_pair2137 = add nuw nsw i32 %v530, 1
  call void @llvm.memcpy.p0.p0.i64(ptr noundef nonnull align 8 dereferenceable(56) %return_storage, ptr noundef nonnull align 8 dereferenceable(56) %v541_mem.sroa.0.sroa.0, i64 56, i1 false)
  %v546_mem.sroa.0.sroa.2.0.return_storage.sroa_idx = getelementptr inbounds nuw i8, ptr %return_storage, i64 56
  %40 = load <16 x i8>, ptr %v533_scratch.sink2398, align 1
  store <16 x i8> %40, ptr %v546_mem.sroa.0.sroa.2.0.return_storage.sroa_idx, align 8
  %v546_mem.sroa.0.sroa.18.0.return_storage.sroa_idx = getelementptr inbounds nuw i8, ptr %return_storage, i64 72
  %41 = load <16 x i8>, ptr %v533_scratch.sink2398.sroa.phi, align 1
  store <16 x i8> %41, ptr %v546_mem.sroa.0.sroa.18.0.return_storage.sroa_idx, align 8
  %v546_mem.sroa.0.sroa.34.0.return_storage.sroa_idx = getelementptr inbounds nuw i8, ptr %return_storage, i64 88
  %42 = load <16 x i8>, ptr %v533_scratch.sink2398.sroa.phi2401, align 1
  store <16 x i8> %42, ptr %v546_mem.sroa.0.sroa.34.0.return_storage.sroa_idx, align 8
  %v546_mem.sroa.0.sroa.50.0.return_storage.sroa_idx = getelementptr inbounds nuw i8, ptr %return_storage, i64 104
  %43 = load <16 x i8>, ptr %v533_scratch.sink2398.sroa.phi2404, align 1
  store <16 x i8> %43, ptr %v546_mem.sroa.0.sroa.50.0.return_storage.sroa_idx, align 8
  %v546_mem.sroa.2.0.return_storage.sroa_idx = getelementptr inbounds nuw i8, ptr %return_storage, i64 120
  store i32 %v545_pair2137, ptr %v546_mem.sroa.2.0.return_storage.sroa_idx, align 8
  %v546_mem.sroa.3.0.return_storage.sroa_idx = getelementptr inbounds nuw i8, ptr %return_storage, i64 124
  call void @llvm.memcpy.p0.p0.i64(ptr noundef nonnull align 4 dereferenceable(60) %v546_mem.sroa.3.0.return_storage.sroa_idx, ptr noundef nonnull align 4 dereferenceable(60) %v541_mem.sroa.5, i64 60, i1 false)
  br label %common.ret

b286:                                             ; preds = %b273
  %v551_mem.sroa.5.0.v401_mem.sroa_idx = getelementptr inbounds nuw i8, ptr %v401_mem, i64 133
  store i1 false, ptr %v551_mem.sroa.3.sroa.0, align 4
  %v551_mem.sroa.3.sroa.0.0.v551_mem.sroa.3.sroa.0.0.v551_mem.sroa.3.sroa.0.0. = load i8, ptr %v551_mem.sroa.3.sroa.0, align 4
  call void @llvm.memcpy.p0.p0.i64(ptr noundef nonnull align 8 dereferenceable(128) %return_storage, ptr noundef nonnull align 8 dereferenceable(128) %v401_mem, i64 128, i1 false)
  %v554_mem.sroa.2.0.return_storage.sroa_idx = getelementptr inbounds nuw i8, ptr %return_storage, i64 128
  store i32 1, ptr %v554_mem.sroa.2.0.return_storage.sroa_idx, align 8
  %v554_mem.sroa.3.0.return_storage.sroa_idx = getelementptr inbounds nuw i8, ptr %return_storage, i64 132
  store i8 %v551_mem.sroa.3.sroa.0.0.v551_mem.sroa.3.sroa.0.0.v551_mem.sroa.3.sroa.0.0., ptr %v554_mem.sroa.3.0.return_storage.sroa_idx, align 4
  %v554_mem.sroa.3.sroa.2.0.v554_mem.sroa.3.0.return_storage.sroa_idx.sroa_idx = getelementptr inbounds nuw i8, ptr %return_storage, i64 133
  call void @llvm.memcpy.p0.p0.i64(ptr noundef nonnull align 1 dereferenceable(51) %v554_mem.sroa.3.sroa.2.0.v554_mem.sroa.3.0.return_storage.sroa_idx.sroa_idx, ptr noundef nonnull align 1 dereferenceable(51) %v551_mem.sroa.5.0.v401_mem.sroa_idx, i64 51, i1 false)
  br label %common.ret

b289:                                             ; preds = %b273
  %v559_mem.sroa.3.0.v401_mem.sroa_idx = getelementptr inbounds nuw i8, ptr %v401_mem, i64 132
  call void @llvm.memcpy.p0.p0.i64(ptr noundef nonnull align 8 dereferenceable(128) %return_storage, ptr noundef nonnull align 8 dereferenceable(128) %v401_mem, i64 128, i1 false)
  %v559_mem.sroa.2.0.return_storage.sroa_idx = getelementptr inbounds nuw i8, ptr %return_storage, i64 128
  store i32 10, ptr %v559_mem.sroa.2.0.return_storage.sroa_idx, align 8
  %v559_mem.sroa.3.0.return_storage.sroa_idx = getelementptr inbounds nuw i8, ptr %return_storage, i64 132
  call void @llvm.memcpy.p0.p0.i64(ptr noundef nonnull align 4 dereferenceable(52) %v559_mem.sroa.3.0.return_storage.sroa_idx, ptr noundef nonnull align 4 dereferenceable(52) %v559_mem.sroa.3.0.v401_mem.sroa_idx, i64 52, i1 false)
  br label %common.ret

b291:                                             ; preds = %b273
  %44 = add i8 %p1, -48
  %v5.i1311 = icmp ult i8 %44, 10
  br i1 %v5.i1311, label %b292, label %b297

b292:                                             ; preds = %b291
  %v562 = icmp eq i8 %p1, 48
  %v565_mem.sroa.4.0.v401_mem.sroa_idx = getelementptr inbounds nuw i8, ptr %v401_mem, i64 132
  call void @llvm.memcpy.p0.p0.i64(ptr noundef nonnull align 8 dereferenceable(128) %v569_mem.sroa.0, ptr noundef nonnull align 8 dereferenceable(128) %v401_mem, i64 128, i1 false)
  call void @llvm.memcpy.p0.p0.i64(ptr noundef nonnull align 4 dereferenceable(52) %v569_mem.sroa.5, ptr noundef nonnull align 4 dereferenceable(52) %v565_mem.sroa.4.0.v401_mem.sroa_idx, i64 52, i1 false)
  %.2399 = select i1 %v562, i32 11, i32 12
  call void @llvm.memcpy.p0.p0.i64(ptr noundef nonnull align 8 dereferenceable(128) %return_storage, ptr noundef nonnull align 8 dereferenceable(128) %v569_mem.sroa.0, i64 128, i1 false)
  %v569_mem.sroa.3.0.return_storage.sroa_idx = getelementptr inbounds nuw i8, ptr %return_storage, i64 128
  store i32 %.2399, ptr %v569_mem.sroa.3.0.return_storage.sroa_idx, align 8
  %v569_mem.sroa.5.0.return_storage.sroa_idx = getelementptr inbounds nuw i8, ptr %return_storage, i64 132
  call void @llvm.memcpy.p0.p0.i64(ptr noundef nonnull align 4 dereferenceable(52) %v569_mem.sroa.5.0.return_storage.sroa_idx, ptr noundef nonnull align 4 dereferenceable(52) %v569_mem.sroa.5, i64 52, i1 false)
  br label %common.ret

b297:                                             ; preds = %b291
  switch i8 %p1, label %b312 [
    i8 116, label %b304
    i8 102, label %b304
    i8 110, label %b304
  ]

b304:                                             ; preds = %b297, %b297, %b297
  %v582_mem.sroa.3.0.v401_mem.sroa_idx = getelementptr inbounds nuw i8, ptr %v401_mem, i64 132
  %v582_mem.sroa.3.0.copyload = load i32, ptr %v582_mem.sroa.3.0.v401_mem.sroa_idx, align 4
  %v582_mem.sroa.5.0.v401_mem.sroa_idx = getelementptr inbounds nuw i8, ptr %v401_mem, i64 144
  switch i8 %p1, label %b309 [
    i8 116, label %b311
    i8 102, label %b310_to_b311
  ]

b309:                                             ; preds = %b304
  br label %b310_to_b311

b311:                                             ; preds = %b304, %b310_to_b311
  %v599_mem.sroa.0.sroa.0.sink = phi ptr [ %v599_mem.sroa.0.sroa.0, %b310_to_b311 ], [ %v401_mem, %b304 ]
  %v599_mem.sroa.5.sroa.3.sink = phi ptr [ %v599_mem.sroa.5.sroa.3, %b310_to_b311 ], [ %v582_mem.sroa.5.0.v401_mem.sroa_idx, %b304 ]
  %v600_mem.sroa.3.0 = phi i32 [ %v599_mem.sroa.3.0, %b310_to_b311 ], [ 1, %b304 ]
  call void @llvm.memcpy.p0.p0.i64(ptr noundef nonnull align 8 dereferenceable(128) %v600_mem.sroa.0.sroa.0, ptr noundef nonnull align 8 dereferenceable(128) %v599_mem.sroa.0.sroa.0.sink, i64 128, i1 false)
  call void @llvm.memcpy.p0.p0.i64(ptr noundef nonnull align 4 dereferenceable(40) %v600_mem.sroa.5.sroa.3, ptr noundef nonnull align 4 dereferenceable(40) %v599_mem.sroa.5.sroa.3.sink, i64 40, i1 false)
  call void @llvm.memcpy.p0.p0.i64(ptr noundef nonnull align 8 dereferenceable(128) %return_storage, ptr noundef nonnull align 8 dereferenceable(128) %v600_mem.sroa.0.sroa.0, i64 128, i1 false)
  %v600_mem.sroa.0.sroa.3.0.return_storage.sroa_idx = getelementptr inbounds nuw i8, ptr %return_storage, i64 128
  store i32 20, ptr %v600_mem.sroa.0.sroa.3.0.return_storage.sroa_idx, align 8
  %v600_mem.sroa.0.sroa.5.0.return_storage.sroa_idx = getelementptr inbounds nuw i8, ptr %return_storage, i64 132
  store i32 %v582_mem.sroa.3.0.copyload, ptr %v600_mem.sroa.0.sroa.5.0.return_storage.sroa_idx, align 4
  %v600_mem.sroa.3.0.return_storage.sroa_idx = getelementptr inbounds nuw i8, ptr %return_storage, i64 136
  store i32 %v600_mem.sroa.3.0, ptr %v600_mem.sroa.3.0.return_storage.sroa_idx, align 8
  %v600_mem.sroa.5.0.return_storage.sroa_idx = getelementptr inbounds nuw i8, ptr %return_storage, i64 140
  store i32 1, ptr %v600_mem.sroa.5.0.return_storage.sroa_idx, align 4
  %v600_mem.sroa.5.sroa.3.0.v600_mem.sroa.5.0.return_storage.sroa_idx.sroa_idx = getelementptr inbounds nuw i8, ptr %return_storage, i64 144
  call void @llvm.memcpy.p0.p0.i64(ptr noundef nonnull align 8 dereferenceable(40) %v600_mem.sroa.5.sroa.3.0.v600_mem.sroa.5.0.return_storage.sroa_idx.sroa_idx, ptr noundef nonnull align 4 dereferenceable(40) %v600_mem.sroa.5.sroa.3, i64 40, i1 false)
  br label %common.ret

b312:                                             ; preds = %b297
  %v602_ptr = getelementptr inbounds nuw i8, ptr %v401_mem, i64 48
  %v602 = load i64, ptr %v602_ptr, align 8
  %v1_mem.sroa.3.0.p0.sroa_idx.i1312 = getelementptr inbounds nuw i8, ptr %v401_mem, i64 172
  %v1_mem.sroa.3.0.copyload.i1313 = load i32, ptr %v1_mem.sroa.3.0.p0.sroa_idx.i1312, align 4
  call void @llvm.memcpy.p0.p0.i64(ptr noundef nonnull align 8 dereferenceable(168) %return_storage, ptr noundef nonnull align 8 dereferenceable(168) %v401_mem, i64 168, i1 false)
  %v603_mem.sroa.2.0.return_storage.sroa_idx = getelementptr inbounds nuw i8, ptr %return_storage, i64 168
  store i32 1, ptr %v603_mem.sroa.2.0.return_storage.sroa_idx, align 8
  %v603_mem.sroa.3.0.return_storage.sroa_idx = getelementptr inbounds nuw i8, ptr %return_storage, i64 172
  store i32 %v1_mem.sroa.3.0.copyload.i1313, ptr %v603_mem.sroa.3.0.return_storage.sroa_idx, align 4
  %v603_mem.sroa.4.0.return_storage.sroa_idx = getelementptr inbounds nuw i8, ptr %return_storage, i64 176
  store i64 %v602, ptr %v603_mem.sroa.4.0.return_storage.sroa_idx, align 8
  br label %common.ret

b13_to_b14:                                       ; preds = %b5
  %v31_next.sroa.0.sroa.4.0.p0.sroa_idx = getelementptr inbounds nuw i8, ptr %p0, i64 48
  %v31_next.sroa.0.sroa.4.0.copyload = load i64, ptr %v31_next.sroa.0.sroa.4.0.p0.sroa_idx, align 1
  %v31_next.sroa.4.0.p0.sroa_idx = getelementptr inbounds nuw i8, ptr %p0, i64 152
  %v31_next.sroa.4.0.copyload2036 = load i64, ptr %v31_next.sroa.4.0.p0.sroa_idx, align 1
  br label %b14

b137_to_b216:                                     ; preds = %b132
  call void @llvm.memcpy.p0.p0.i64(ptr noundef nonnull align 8 dereferenceable(184) %v401_next, ptr noundef nonnull align 1 dereferenceable(184) %p0, i64 184, i1 false)
  br label %b216

b310_to_b311:                                     ; preds = %b304, %b309
  %v599_mem.sroa.3.0 = phi i32 [ 3, %b309 ], [ 2, %b304 ]
  call void @llvm.memcpy.p0.p0.i64(ptr noundef nonnull align 8 dereferenceable(128) %v599_mem.sroa.0.sroa.0, ptr noundef nonnull align 8 dereferenceable(128) %v401_mem, i64 128, i1 false)
  call void @llvm.memcpy.p0.p0.i64(ptr noundef nonnull align 4 dereferenceable(40) %v599_mem.sroa.5.sroa.3, ptr noundef nonnull align 8 dereferenceable(40) %v582_mem.sroa.5.0.v401_mem.sroa_idx, i64 40, i1 false)
  br label %b311
}

; Function Attrs: nounwind memory(readwrite, inaccessiblemem: write)
define void @liza_json.feed(ptr writeonly sret(%struct.JsonState) captures(none) %return_storage, ptr readonly captures(none) %p0, { ptr, i32 } %p1) local_unnamed_addr #3 {
b0:
  %v4_mem.sroa.14 = alloca { [64 x i8], i32, i1, i32, i1, i32, i32, i32, i32, i64, i64, i32, i64 }, align 8
  %v12_mem = alloca %struct.JsonState, align 8
  %v25_mem = alloca %struct.JsonState, align 8
  %v0_ptr = getelementptr i8, ptr %p0, i64 168
  %v0 = load i32, ptr %v0_ptr, align 4
  %v2.not = icmp eq i32 %v0, 0
  br i1 %v2.not, label %b3_to_b4, label %b1

common.ret:                                       ; preds = %b14, %b12, %b11, %b6, %b1
  ret void

b1:                                               ; preds = %b0
  tail call void @llvm.memmove.p0.p0.i64(ptr noundef nonnull align 8 dereferenceable(184) %return_storage, ptr noundef nonnull align 1 dereferenceable(184) %p0, i64 184, i1 false)
  br label %common.ret

v8_ok:                                            ; preds = %v8_ok.lr.ph, %v32_ok
  %indvars.iv = phi i64 [ 0, %v8_ok.lr.ph ], [ %indvars.iv.next, %v32_ok ]
  %v4_mem.sroa.0.0122 = phi i64 [ %v4_next.sroa.0.sroa.0.0.copyload, %v8_ok.lr.ph ], [ %v33_mem.sroa.0.sroa.0.0.copyload, %v32_ok ]
  %v4_mem.sroa.5.0121 = phi i64 [ %v4_next.sroa.0.sroa.4.0.copyload, %v8_ok.lr.ph ], [ %v33_mem.sroa.0.sroa.2.0.copyload, %v32_ok ]
  %v4_mem.sroa.6.0120 = phi i64 [ %v4_next.sroa.0.sroa.6.0.copyload, %v8_ok.lr.ph ], [ %v33_mem.sroa.0.sroa.3.0.copyload, %v32_ok ]
  %v4_mem.sroa.7.0119 = phi i32 [ %v4_next.sroa.0.sroa.8.0.copyload, %v8_ok.lr.ph ], [ %v33_mem.sroa.0.sroa.4.0.copyload, %v32_ok ]
  %v4_mem.sroa.8.0118 = phi i8 [ %v4_next.sroa.0.sroa.10.0.copyload, %v8_ok.lr.ph ], [ %v33_mem.sroa.0.sroa.5.0.copyload, %v32_ok ]
  %v4_mem.sroa.9.0117 = phi i8 [ %v4_next.sroa.0.sroa.12.0.copyload, %v8_ok.lr.ph ], [ %v33_mem.sroa.0.sroa.6.0.copyload, %v32_ok ]
  %v4_mem.sroa.1043.0116 = phi i32 [ %v4_next.sroa.0.sroa.16.0.copyload, %v8_ok.lr.ph ], [ %v33_mem.sroa.0.sroa.8.0.copyload, %v32_ok ]
  %v4_mem.sroa.11.0115 = phi i32 [ %v4_next.sroa.0.sroa.18.0.copyload, %v8_ok.lr.ph ], [ %v33_mem.sroa.0.sroa.9.0.copyload, %v32_ok ]
  %v4_mem.sroa.1152.0114 = phi i64 [ %v4_next.sroa.0.sroa.20.0.copyload, %v8_ok.lr.ph ], [ %v33_mem.sroa.0.sroa.10.0.copyload, %v32_ok ]
  %v4_mem.sroa.12.0113 = phi i64 [ %v4_next.sroa.4.0.copyload, %v8_ok.lr.ph ], [ %v32, %v32_ok ]
  %0 = phi i16 [ %2, %v8_ok.lr.ph ], [ %1, %v32_ok ]
  %v8_ptr = getelementptr i8, ptr %v8_base, i64 %indvars.iv
  %v8 = load i8, ptr %v8_ptr, align 1
  %v9.fca.0.insert = insertvalue %struct.Utf8StreamState poison, i64 %v4_mem.sroa.0.0122, 0
  %v9.fca.1.insert = insertvalue %struct.Utf8StreamState %v9.fca.0.insert, i64 %v4_mem.sroa.5.0121, 1
  %v9.fca.2.insert = insertvalue %struct.Utf8StreamState %v9.fca.1.insert, i64 %v4_mem.sroa.6.0120, 2
  %v9.fca.3.insert = insertvalue %struct.Utf8StreamState %v9.fca.2.insert, i32 %v4_mem.sroa.7.0119, 3
  %v9.fca.4.insert = insertvalue %struct.Utf8StreamState %v9.fca.3.insert, i8 %v4_mem.sroa.8.0118, 4
  %v9.fca.5.insert = insertvalue %struct.Utf8StreamState %v9.fca.4.insert, i8 %v4_mem.sroa.9.0117, 5
  %v9.fca.6.insert = insertvalue %struct.Utf8StreamState %v9.fca.5.insert, i32 %v4_mem.sroa.1043.0116, 6
  %v10.fca.7.insert = insertvalue %struct.Utf8StreamState %v9.fca.6.insert, i64 %v4_mem.sroa.1152.0114, 7
  %v11 = tail call %struct.Utf8StreamState @liza_utf8_stream.feed_byte(%struct.Utf8StreamState %v10.fca.7.insert, i8 %v8)
  store i16 %0, ptr %v4_mem.sroa.10.0.v12_mem.sroa_idx, align 2
  store i32 %v4_mem.sroa.11.0115, ptr %v4_mem.sroa.11.0.v12_mem.sroa_idx, align 4
  store i64 %v4_mem.sroa.12.0113, ptr %v4_mem.sroa.12.0.v12_mem.sroa_idx, align 8
  call void @llvm.memcpy.p0.p0.i64(ptr noundef nonnull align 8 dereferenceable(128) %v4_mem.sroa.14.0.v12_mem.sroa_idx, ptr noundef nonnull align 8 dereferenceable(128) %v4_mem.sroa.14, i64 128, i1 false)
  %v11.fca.0.extract = extractvalue %struct.Utf8StreamState %v11, 0
  store i64 %v11.fca.0.extract, ptr %v12_mem, align 8
  %v11.fca.1.extract = extractvalue %struct.Utf8StreamState %v11, 1
  store i64 %v11.fca.1.extract, ptr %v4_mem.sroa.5.0.v12_mem.sroa_idx, align 8
  %v11.fca.2.extract = extractvalue %struct.Utf8StreamState %v11, 2
  store i64 %v11.fca.2.extract, ptr %v4_mem.sroa.6.0.v12_mem.sroa_idx, align 8
  %v11.fca.3.extract = extractvalue %struct.Utf8StreamState %v11, 3
  store i32 %v11.fca.3.extract, ptr %v4_mem.sroa.7.0.v12_mem.sroa_idx, align 8
  %v11.fca.4.extract = extractvalue %struct.Utf8StreamState %v11, 4
  store i8 %v11.fca.4.extract, ptr %v4_mem.sroa.8.0.v12_mem.sroa_idx, align 4
  %v11.fca.5.extract = extractvalue %struct.Utf8StreamState %v11, 5
  store i8 %v11.fca.5.extract, ptr %v4_mem.sroa.9.0.v12_mem.sroa_idx, align 1
  %v11.fca.6.extract = extractvalue %struct.Utf8StreamState %v11, 6
  store i32 %v11.fca.6.extract, ptr %v4_mem.sroa.1043.0.v12_mem.sroa_idx, align 8
  %v11.fca.7.extract = extractvalue %struct.Utf8StreamState %v11, 7
  store i64 %v11.fca.7.extract, ptr %v4_mem.sroa.1152.0.v12_mem.sroa_idx, align 8
  switch i32 %v11.fca.6.extract, label %liza_utf8_stream.status.exit [
    i32 1, label %b1.i
    i32 2, label %b4.i
  ]

b1.i:                                             ; preds = %v8_ok
  %v5.i = insertvalue %struct.Utf8StreamError zeroinitializer, i64 %v11.fca.7.extract, 1
  %v6.i = insertvalue %variant.3 zeroinitializer, %struct.Utf8StreamError %v5.i, 1
  br label %liza_utf8_stream.status.exit

b4.i:                                             ; preds = %v8_ok
  %v12.i = insertvalue %struct.Utf8StreamError { %variant.0 { i32 1, [0 x i8] zeroinitializer, [0 x i8] zeroinitializer }, i64 0 }, i64 %v11.fca.7.extract, 1
  %v13.i = insertvalue %variant.3 zeroinitializer, %struct.Utf8StreamError %v12.i, 1
  br label %liza_utf8_stream.status.exit

liza_utf8_stream.status.exit:                     ; preds = %v8_ok, %b1.i, %b4.i
  %common.ret.op.i = phi %variant.3 [ %v6.i, %b1.i ], [ %v13.i, %b4.i ], [ { i32 1, %struct.Utf8StreamError zeroinitializer, [0 x i8] zeroinitializer }, %v8_ok ]
  %v15 = extractvalue %variant.3 %common.ret.op.i, 0
  %switch = icmp eq i32 %v15, 1
  br i1 %switch, label %b13, label %b9

b6:                                               ; preds = %v32_ok, %b3_to_b4
  %.lcssa = phi i16 [ %2, %b3_to_b4 ], [ %1, %v32_ok ]
  %v4_mem.sroa.12.0.lcssa = phi i64 [ %v4_next.sroa.4.0.copyload, %b3_to_b4 ], [ %v32, %v32_ok ]
  %v4_mem.sroa.1152.0.lcssa = phi i64 [ %v4_next.sroa.0.sroa.20.0.copyload, %b3_to_b4 ], [ %v33_mem.sroa.0.sroa.10.0.copyload, %v32_ok ]
  %v4_mem.sroa.11.0.lcssa = phi i32 [ %v4_next.sroa.0.sroa.18.0.copyload, %b3_to_b4 ], [ %v33_mem.sroa.0.sroa.9.0.copyload, %v32_ok ]
  %v4_mem.sroa.1043.0.lcssa = phi i32 [ %v4_next.sroa.0.sroa.16.0.copyload, %b3_to_b4 ], [ %v33_mem.sroa.0.sroa.8.0.copyload, %v32_ok ]
  %v4_mem.sroa.9.0.lcssa = phi i8 [ %v4_next.sroa.0.sroa.12.0.copyload, %b3_to_b4 ], [ %v33_mem.sroa.0.sroa.6.0.copyload, %v32_ok ]
  %v4_mem.sroa.8.0.lcssa = phi i8 [ %v4_next.sroa.0.sroa.10.0.copyload, %b3_to_b4 ], [ %v33_mem.sroa.0.sroa.5.0.copyload, %v32_ok ]
  %v4_mem.sroa.7.0.lcssa = phi i32 [ %v4_next.sroa.0.sroa.8.0.copyload, %b3_to_b4 ], [ %v33_mem.sroa.0.sroa.4.0.copyload, %v32_ok ]
  %v4_mem.sroa.6.0.lcssa = phi i64 [ %v4_next.sroa.0.sroa.6.0.copyload, %b3_to_b4 ], [ %v33_mem.sroa.0.sroa.3.0.copyload, %v32_ok ]
  %v4_mem.sroa.5.0.lcssa = phi i64 [ %v4_next.sroa.0.sroa.4.0.copyload, %b3_to_b4 ], [ %v33_mem.sroa.0.sroa.2.0.copyload, %v32_ok ]
  %v4_mem.sroa.0.0.lcssa = phi i64 [ %v4_next.sroa.0.sroa.0.0.copyload, %b3_to_b4 ], [ %v33_mem.sroa.0.sroa.0.0.copyload, %v32_ok ]
  store i64 %v4_mem.sroa.0.0.lcssa, ptr %return_storage, align 8
  %v4_mem.sroa.5.0.return_storage.sroa_idx = getelementptr inbounds nuw i8, ptr %return_storage, i64 8
  store i64 %v4_mem.sroa.5.0.lcssa, ptr %v4_mem.sroa.5.0.return_storage.sroa_idx, align 8
  %v4_mem.sroa.6.0.return_storage.sroa_idx = getelementptr inbounds nuw i8, ptr %return_storage, i64 16
  store i64 %v4_mem.sroa.6.0.lcssa, ptr %v4_mem.sroa.6.0.return_storage.sroa_idx, align 8
  %v4_mem.sroa.7.0.return_storage.sroa_idx = getelementptr inbounds nuw i8, ptr %return_storage, i64 24
  store i32 %v4_mem.sroa.7.0.lcssa, ptr %v4_mem.sroa.7.0.return_storage.sroa_idx, align 8
  %v4_mem.sroa.8.0.return_storage.sroa_idx = getelementptr inbounds nuw i8, ptr %return_storage, i64 28
  store i8 %v4_mem.sroa.8.0.lcssa, ptr %v4_mem.sroa.8.0.return_storage.sroa_idx, align 4
  %v4_mem.sroa.9.0.return_storage.sroa_idx = getelementptr inbounds nuw i8, ptr %return_storage, i64 29
  store i8 %v4_mem.sroa.9.0.lcssa, ptr %v4_mem.sroa.9.0.return_storage.sroa_idx, align 1
  %v4_mem.sroa.10.0.return_storage.sroa_idx = getelementptr inbounds nuw i8, ptr %return_storage, i64 30
  store i16 %.lcssa, ptr %v4_mem.sroa.10.0.return_storage.sroa_idx, align 2
  %v4_mem.sroa.1043.0.return_storage.sroa_idx = getelementptr inbounds nuw i8, ptr %return_storage, i64 32
  store i32 %v4_mem.sroa.1043.0.lcssa, ptr %v4_mem.sroa.1043.0.return_storage.sroa_idx, align 8
  %v4_mem.sroa.11.0.return_storage.sroa_idx = getelementptr inbounds nuw i8, ptr %return_storage, i64 36
  store i32 %v4_mem.sroa.11.0.lcssa, ptr %v4_mem.sroa.11.0.return_storage.sroa_idx, align 4
  %v4_mem.sroa.1152.0.return_storage.sroa_idx = getelementptr inbounds nuw i8, ptr %return_storage, i64 40
  store i64 %v4_mem.sroa.1152.0.lcssa, ptr %v4_mem.sroa.1152.0.return_storage.sroa_idx, align 8
  %v4_mem.sroa.12.0.return_storage.sroa_idx = getelementptr inbounds nuw i8, ptr %return_storage, i64 48
  store i64 %v4_mem.sroa.12.0.lcssa, ptr %v4_mem.sroa.12.0.return_storage.sroa_idx, align 8
  %v4_mem.sroa.14.0.return_storage.sroa_idx = getelementptr inbounds nuw i8, ptr %return_storage, i64 56
  call void @llvm.memcpy.p0.p0.i64(ptr noundef nonnull align 8 dereferenceable(128) %v4_mem.sroa.14.0.return_storage.sroa_idx, ptr noundef nonnull align 8 dereferenceable(128) %v4_mem.sroa.14, i64 128, i1 false)
  br label %common.ret

b9:                                               ; preds = %liza_utf8_stream.status.exit
  %v16 = extractvalue %variant.3 %common.ret.op.i, 1
  %v17 = extractvalue %struct.Utf8StreamError %v16, 0
  %v18 = extractvalue %variant.0 %v17, 0
  %switch8 = icmp eq i32 %v18, 0
  %v20 = extractvalue %struct.Utf8StreamError %v16, 1
  %v1_mem.sroa.3.0.p0.sroa_idx.i = getelementptr inbounds nuw i8, ptr %v12_mem, i64 172
  %v1_mem.sroa.3.0.copyload.i = load i32, ptr %v1_mem.sroa.3.0.p0.sroa_idx.i, align 4
  call void @llvm.memcpy.p0.p0.i64(ptr noundef nonnull align 8 dereferenceable(168) %return_storage, ptr noundef nonnull align 8 dereferenceable(168) %v12_mem, i64 168, i1 false)
  %v21_mem.sroa.2.0.return_storage.sroa_idx = getelementptr inbounds nuw i8, ptr %return_storage, i64 168
  %v21_mem.sroa.3.0.return_storage.sroa_idx = getelementptr inbounds nuw i8, ptr %return_storage, i64 172
  %v21_mem.sroa.4.0.return_storage.sroa_idx = getelementptr inbounds nuw i8, ptr %return_storage, i64 176
  br i1 %switch8, label %b11, label %b12

b11:                                              ; preds = %b9
  store i32 5, ptr %v21_mem.sroa.2.0.return_storage.sroa_idx, align 8
  store i32 %v1_mem.sroa.3.0.copyload.i, ptr %v21_mem.sroa.3.0.return_storage.sroa_idx, align 4
  store i64 %v20, ptr %v21_mem.sroa.4.0.return_storage.sroa_idx, align 8
  br label %common.ret

b12:                                              ; preds = %b9
  store i32 8, ptr %v21_mem.sroa.2.0.return_storage.sroa_idx, align 8
  store i32 %v1_mem.sroa.3.0.copyload.i, ptr %v21_mem.sroa.3.0.return_storage.sroa_idx, align 4
  store i64 %v20, ptr %v21_mem.sroa.4.0.return_storage.sroa_idx, align 8
  br label %common.ret

b13:                                              ; preds = %liza_utf8_stream.status.exit
  call void @liza___liza_json_step(ptr nonnull sret(%struct.JsonState) %v25_mem, ptr nonnull %v12_mem, i8 %v8)
  %v26 = load i32, ptr %v26_ptr, align 8
  %v28.not = icmp eq i32 %v26, 0
  br i1 %v28.not, label %b16, label %b14

b14:                                              ; preds = %b13
  call void @llvm.memcpy.p0.p0.i64(ptr noundef nonnull align 8 dereferenceable(184) %return_storage, ptr noundef nonnull align 8 dereferenceable(184) %v25_mem, i64 184, i1 false)
  br label %common.ret

b16:                                              ; preds = %b13
  %v30 = load i64, ptr %v29_ptr, align 8
  %v32_pair = tail call { i64, i1 } @llvm.uadd.with.overflow.i64(i64 %v30, i64 1)
  %v32_overflow = extractvalue { i64, i1 } %v32_pair, 1
  br i1 %v32_overflow, label %v32_trap, label %v32_ok

v32_trap:                                         ; preds = %b16
  tail call void @llvm.trap()
  unreachable

v32_ok:                                           ; preds = %b16
  %v33_mem.sroa.0.sroa.0.0.copyload = load i64, ptr %v25_mem, align 8
  %v33_mem.sroa.0.sroa.2.0.copyload = load i64, ptr %v33_mem.sroa.0.sroa.2.0.v25_mem.sroa_idx, align 8
  %v33_mem.sroa.0.sroa.3.0.copyload = load i64, ptr %v33_mem.sroa.0.sroa.3.0.v25_mem.sroa_idx, align 8
  %v33_mem.sroa.0.sroa.4.0.copyload = load i32, ptr %v33_mem.sroa.0.sroa.4.0.v25_mem.sroa_idx, align 8
  %v33_mem.sroa.0.sroa.5.0.copyload = load i8, ptr %v33_mem.sroa.0.sroa.5.0.v25_mem.sroa_idx, align 4
  %v33_mem.sroa.0.sroa.6.0.copyload = load i8, ptr %v33_mem.sroa.0.sroa.6.0.v25_mem.sroa_idx, align 1
  %1 = load i16, ptr %v33_mem.sroa.0.sroa.7.0.v25_mem.sroa_idx, align 2
  %v33_mem.sroa.0.sroa.8.0.copyload = load i32, ptr %v33_mem.sroa.0.sroa.8.0.v25_mem.sroa_idx, align 8
  %v33_mem.sroa.0.sroa.9.0.copyload = load i32, ptr %v33_mem.sroa.0.sroa.9.0.v25_mem.sroa_idx, align 4
  %v33_mem.sroa.0.sroa.10.0.copyload = load i64, ptr %v33_mem.sroa.0.sroa.10.0.v25_mem.sroa_idx, align 8
  %indvars.iv.next = add nuw nsw i64 %indvars.iv, 1
  %v32 = extractvalue { i64, i1 } %v32_pair, 0
  call void @llvm.memcpy.p0.p0.i64(ptr noundef nonnull align 8 dereferenceable(128) %v4_mem.sroa.14, ptr noundef nonnull align 8 dereferenceable(128) %v33_mem.sroa.3.0.v25_mem.sroa_idx, i64 128, i1 false)
  %exitcond.not = icmp eq i64 %indvars.iv.next, %wide.trip.count
  br i1 %exitcond.not, label %b6, label %v8_ok

b3_to_b4:                                         ; preds = %b0
  %v4_next.sroa.0.sroa.0.0.copyload = load i64, ptr %p0, align 1
  %v4_next.sroa.0.sroa.4.0.p0.sroa_idx = getelementptr inbounds nuw i8, ptr %p0, i64 8
  %v4_next.sroa.0.sroa.4.0.copyload = load i64, ptr %v4_next.sroa.0.sroa.4.0.p0.sroa_idx, align 1
  %v4_next.sroa.0.sroa.6.0.p0.sroa_idx = getelementptr inbounds nuw i8, ptr %p0, i64 16
  %v4_next.sroa.0.sroa.6.0.copyload = load i64, ptr %v4_next.sroa.0.sroa.6.0.p0.sroa_idx, align 1
  %v4_next.sroa.0.sroa.8.0.p0.sroa_idx = getelementptr inbounds nuw i8, ptr %p0, i64 24
  %v4_next.sroa.0.sroa.8.0.copyload = load i32, ptr %v4_next.sroa.0.sroa.8.0.p0.sroa_idx, align 1
  %v4_next.sroa.0.sroa.10.0.p0.sroa_idx = getelementptr inbounds nuw i8, ptr %p0, i64 28
  %v4_next.sroa.0.sroa.10.0.copyload = load i8, ptr %v4_next.sroa.0.sroa.10.0.p0.sroa_idx, align 1
  %v4_next.sroa.0.sroa.12.0.p0.sroa_idx = getelementptr inbounds nuw i8, ptr %p0, i64 29
  %v4_next.sroa.0.sroa.12.0.copyload = load i8, ptr %v4_next.sroa.0.sroa.12.0.p0.sroa_idx, align 1
  %v4_next.sroa.0.sroa.14.0.p0.sroa_idx = getelementptr inbounds nuw i8, ptr %p0, i64 30
  %2 = load i16, ptr %v4_next.sroa.0.sroa.14.0.p0.sroa_idx, align 1
  %v4_next.sroa.0.sroa.16.0.p0.sroa_idx = getelementptr inbounds nuw i8, ptr %p0, i64 32
  %v4_next.sroa.0.sroa.16.0.copyload = load i32, ptr %v4_next.sroa.0.sroa.16.0.p0.sroa_idx, align 1
  %v4_next.sroa.0.sroa.18.0.p0.sroa_idx = getelementptr inbounds nuw i8, ptr %p0, i64 36
  %v4_next.sroa.0.sroa.18.0.copyload = load i32, ptr %v4_next.sroa.0.sroa.18.0.p0.sroa_idx, align 1
  %v4_next.sroa.0.sroa.20.0.p0.sroa_idx = getelementptr inbounds nuw i8, ptr %p0, i64 40
  %v4_next.sroa.0.sroa.20.0.copyload = load i64, ptr %v4_next.sroa.0.sroa.20.0.p0.sroa_idx, align 1
  %v4_next.sroa.4.0.p0.sroa_idx = getelementptr inbounds nuw i8, ptr %p0, i64 48
  %v4_next.sroa.4.0.copyload = load i64, ptr %v4_next.sroa.4.0.p0.sroa_idx, align 1
  %v4_next.sroa.5.0.p0.sroa_idx = getelementptr inbounds nuw i8, ptr %p0, i64 56
  call void @llvm.memcpy.p0.p0.i64(ptr noundef nonnull align 8 dereferenceable(128) %v4_mem.sroa.14, ptr noundef nonnull align 1 dereferenceable(128) %v4_next.sroa.5.0.p0.sroa_idx, i64 128, i1 false)
  %v6 = extractvalue { ptr, i32 } %p1, 1
  %v7112.not = icmp eq i32 %v6, 0
  br i1 %v7112.not, label %b6, label %v8_ok.lr.ph

v8_ok.lr.ph:                                      ; preds = %b3_to_b4
  %v8_base = extractvalue { ptr, i32 } %p1, 0
  %v4_mem.sroa.5.0.v12_mem.sroa_idx = getelementptr inbounds nuw i8, ptr %v12_mem, i64 8
  %v4_mem.sroa.6.0.v12_mem.sroa_idx = getelementptr inbounds nuw i8, ptr %v12_mem, i64 16
  %v4_mem.sroa.7.0.v12_mem.sroa_idx = getelementptr inbounds nuw i8, ptr %v12_mem, i64 24
  %v4_mem.sroa.8.0.v12_mem.sroa_idx = getelementptr inbounds nuw i8, ptr %v12_mem, i64 28
  %v4_mem.sroa.9.0.v12_mem.sroa_idx = getelementptr inbounds nuw i8, ptr %v12_mem, i64 29
  %v4_mem.sroa.10.0.v12_mem.sroa_idx = getelementptr inbounds nuw i8, ptr %v12_mem, i64 30
  %v4_mem.sroa.1043.0.v12_mem.sroa_idx = getelementptr inbounds nuw i8, ptr %v12_mem, i64 32
  %v4_mem.sroa.11.0.v12_mem.sroa_idx = getelementptr inbounds nuw i8, ptr %v12_mem, i64 36
  %v4_mem.sroa.1152.0.v12_mem.sroa_idx = getelementptr inbounds nuw i8, ptr %v12_mem, i64 40
  %v4_mem.sroa.12.0.v12_mem.sroa_idx = getelementptr inbounds nuw i8, ptr %v12_mem, i64 48
  %v4_mem.sroa.14.0.v12_mem.sroa_idx = getelementptr inbounds nuw i8, ptr %v12_mem, i64 56
  %v26_ptr = getelementptr inbounds nuw i8, ptr %v25_mem, i64 168
  %v29_ptr = getelementptr inbounds nuw i8, ptr %v25_mem, i64 48
  %v33_mem.sroa.0.sroa.2.0.v25_mem.sroa_idx = getelementptr inbounds nuw i8, ptr %v25_mem, i64 8
  %v33_mem.sroa.0.sroa.3.0.v25_mem.sroa_idx = getelementptr inbounds nuw i8, ptr %v25_mem, i64 16
  %v33_mem.sroa.0.sroa.4.0.v25_mem.sroa_idx = getelementptr inbounds nuw i8, ptr %v25_mem, i64 24
  %v33_mem.sroa.0.sroa.5.0.v25_mem.sroa_idx = getelementptr inbounds nuw i8, ptr %v25_mem, i64 28
  %v33_mem.sroa.0.sroa.6.0.v25_mem.sroa_idx = getelementptr inbounds nuw i8, ptr %v25_mem, i64 29
  %v33_mem.sroa.0.sroa.7.0.v25_mem.sroa_idx = getelementptr inbounds nuw i8, ptr %v25_mem, i64 30
  %v33_mem.sroa.0.sroa.8.0.v25_mem.sroa_idx = getelementptr inbounds nuw i8, ptr %v25_mem, i64 32
  %v33_mem.sroa.0.sroa.9.0.v25_mem.sroa_idx = getelementptr inbounds nuw i8, ptr %v25_mem, i64 36
  %v33_mem.sroa.0.sroa.10.0.v25_mem.sroa_idx = getelementptr inbounds nuw i8, ptr %v25_mem, i64 40
  %v33_mem.sroa.3.0.v25_mem.sroa_idx = getelementptr inbounds nuw i8, ptr %v25_mem, i64 56
  %wide.trip.count = zext i32 %v6 to i64
  br label %v8_ok
}

; Function Attrs: mustprogress nofree norecurse nosync nounwind willreturn memory(argmem: read)
define %variant.4 @liza_json.status(ptr readonly captures(none) %p0) local_unnamed_addr #4 {
b0:
  %v0_ptr = getelementptr i8, ptr %p0, i64 168
  %v0 = load i32, ptr %v0_ptr, align 4
  %v2 = icmp eq i32 %v0, 0
  br i1 %v2, label %common.ret, label %b3

common.ret:                                       ; preds = %b0, %b3
  %common.ret.op = phi %variant.4 [ %v42, %b3 ], [ { i32 1, %struct.JsonError zeroinitializer, [0 x i8] zeroinitializer }, %b0 ]
  ret %variant.4 %common.ret.op

b3:                                               ; preds = %b0
  %v7 = icmp eq i32 %v0, 2
  %v9 = select i1 %v7, %variant.1 { i32 1, [0 x i8] zeroinitializer, [0 x i8] zeroinitializer, [0 x i8] zeroinitializer, [0 x i8] zeroinitializer, [0 x i8] zeroinitializer, [0 x i8] zeroinitializer, [0 x i8] zeroinitializer, [0 x i8] zeroinitializer }, %variant.1 zeroinitializer
  %v12 = icmp eq i32 %v0, 3
  %v14 = select i1 %v12, %variant.1 { i32 2, [0 x i8] zeroinitializer, [0 x i8] zeroinitializer, [0 x i8] zeroinitializer, [0 x i8] zeroinitializer, [0 x i8] zeroinitializer, [0 x i8] zeroinitializer, [0 x i8] zeroinitializer, [0 x i8] zeroinitializer }, %variant.1 %v9
  %v17 = icmp eq i32 %v0, 4
  %v19 = select i1 %v17, %variant.1 { i32 3, [0 x i8] zeroinitializer, [0 x i8] zeroinitializer, [0 x i8] zeroinitializer, [0 x i8] zeroinitializer, [0 x i8] zeroinitializer, [0 x i8] zeroinitializer, [0 x i8] zeroinitializer, [0 x i8] zeroinitializer }, %variant.1 %v14
  %v22 = icmp eq i32 %v0, 5
  %v24 = select i1 %v22, %variant.1 { i32 4, [0 x i8] zeroinitializer, [0 x i8] zeroinitializer, [0 x i8] zeroinitializer, [0 x i8] zeroinitializer, [0 x i8] zeroinitializer, [0 x i8] zeroinitializer, [0 x i8] zeroinitializer, [0 x i8] zeroinitializer }, %variant.1 %v19
  %v27 = icmp eq i32 %v0, 6
  %v29 = select i1 %v27, %variant.1 { i32 5, [0 x i8] zeroinitializer, [0 x i8] zeroinitializer, [0 x i8] zeroinitializer, [0 x i8] zeroinitializer, [0 x i8] zeroinitializer, [0 x i8] zeroinitializer, [0 x i8] zeroinitializer, [0 x i8] zeroinitializer }, %variant.1 %v24
  %v32 = icmp eq i32 %v0, 7
  %v34 = select i1 %v32, %variant.1 { i32 6, [0 x i8] zeroinitializer, [0 x i8] zeroinitializer, [0 x i8] zeroinitializer, [0 x i8] zeroinitializer, [0 x i8] zeroinitializer, [0 x i8] zeroinitializer, [0 x i8] zeroinitializer, [0 x i8] zeroinitializer }, %variant.1 %v29
  %v37 = icmp eq i32 %v0, 8
  %v39 = select i1 %v37, %variant.1 { i32 7, [0 x i8] zeroinitializer, [0 x i8] zeroinitializer, [0 x i8] zeroinitializer, [0 x i8] zeroinitializer, [0 x i8] zeroinitializer, [0 x i8] zeroinitializer, [0 x i8] zeroinitializer, [0 x i8] zeroinitializer }, %variant.1 %v34
  %v40_ptr = getelementptr i8, ptr %p0, i64 176
  %v40 = load i64, ptr %v40_ptr, align 8
  %v41_field0 = insertvalue %struct.JsonError zeroinitializer, %variant.1 %v39, 0
  %v41 = insertvalue %struct.JsonError %v41_field0, i64 %v40, 1
  %v42 = insertvalue %variant.4 zeroinitializer, %struct.JsonError %v41, 1
  br label %common.ret
}

; Function Attrs: nounwind memory(readwrite, inaccessiblemem: write)
define %variant.5 @liza_json.finish(ptr readonly captures(none) %p0) local_unnamed_addr #3 {
b0:
  %v33_mem = alloca %struct.JsonState, align 8
  %v34_mem = alloca %struct.JsonState, align 8
  %v0_ptr.i = getelementptr i8, ptr %p0, i64 168
  %v0.i = load i32, ptr %v0_ptr.i, align 4
  %v2.i = icmp eq i32 %v0.i, 0
  br i1 %v2.i, label %liza_json.status.exit, label %b3.i

b3.i:                                             ; preds = %b0
  %v7.i = icmp eq i32 %v0.i, 2
  %v9.i = select i1 %v7.i, %variant.1 { i32 1, [0 x i8] zeroinitializer, [0 x i8] zeroinitializer, [0 x i8] zeroinitializer, [0 x i8] zeroinitializer, [0 x i8] zeroinitializer, [0 x i8] zeroinitializer, [0 x i8] zeroinitializer, [0 x i8] zeroinitializer }, %variant.1 zeroinitializer
  %v12.i = icmp eq i32 %v0.i, 3
  %v14.i = select i1 %v12.i, %variant.1 { i32 2, [0 x i8] zeroinitializer, [0 x i8] zeroinitializer, [0 x i8] zeroinitializer, [0 x i8] zeroinitializer, [0 x i8] zeroinitializer, [0 x i8] zeroinitializer, [0 x i8] zeroinitializer, [0 x i8] zeroinitializer }, %variant.1 %v9.i
  %v17.i = icmp eq i32 %v0.i, 4
  %v19.i = select i1 %v17.i, %variant.1 { i32 3, [0 x i8] zeroinitializer, [0 x i8] zeroinitializer, [0 x i8] zeroinitializer, [0 x i8] zeroinitializer, [0 x i8] zeroinitializer, [0 x i8] zeroinitializer, [0 x i8] zeroinitializer, [0 x i8] zeroinitializer }, %variant.1 %v14.i
  %v22.i = icmp eq i32 %v0.i, 5
  %v24.i = select i1 %v22.i, %variant.1 { i32 4, [0 x i8] zeroinitializer, [0 x i8] zeroinitializer, [0 x i8] zeroinitializer, [0 x i8] zeroinitializer, [0 x i8] zeroinitializer, [0 x i8] zeroinitializer, [0 x i8] zeroinitializer, [0 x i8] zeroinitializer }, %variant.1 %v19.i
  %v27.i = icmp eq i32 %v0.i, 6
  %v29.i = select i1 %v27.i, %variant.1 { i32 5, [0 x i8] zeroinitializer, [0 x i8] zeroinitializer, [0 x i8] zeroinitializer, [0 x i8] zeroinitializer, [0 x i8] zeroinitializer, [0 x i8] zeroinitializer, [0 x i8] zeroinitializer, [0 x i8] zeroinitializer }, %variant.1 %v24.i
  %v32.i = icmp eq i32 %v0.i, 7
  %v34.i = select i1 %v32.i, %variant.1 { i32 6, [0 x i8] zeroinitializer, [0 x i8] zeroinitializer, [0 x i8] zeroinitializer, [0 x i8] zeroinitializer, [0 x i8] zeroinitializer, [0 x i8] zeroinitializer, [0 x i8] zeroinitializer, [0 x i8] zeroinitializer }, %variant.1 %v29.i
  %v37.i = icmp eq i32 %v0.i, 8
  %v39.i = select i1 %v37.i, %variant.1 { i32 7, [0 x i8] zeroinitializer, [0 x i8] zeroinitializer, [0 x i8] zeroinitializer, [0 x i8] zeroinitializer, [0 x i8] zeroinitializer, [0 x i8] zeroinitializer, [0 x i8] zeroinitializer, [0 x i8] zeroinitializer }, %variant.1 %v34.i
  %v40_ptr.i = getelementptr i8, ptr %p0, i64 176
  %v40.i = load i64, ptr %v40_ptr.i, align 8
  %v41_field0.i = insertvalue %struct.JsonError zeroinitializer, %variant.1 %v39.i, 0
  %v41.i = insertvalue %struct.JsonError %v41_field0.i, i64 %v40.i, 1
  %v42.i = insertvalue %variant.4 zeroinitializer, %struct.JsonError %v41.i, 1
  br label %liza_json.status.exit

liza_json.status.exit:                            ; preds = %b0, %b3.i
  %common.ret.op.i = phi %variant.4 [ %v42.i, %b3.i ], [ { i32 1, %struct.JsonError zeroinitializer, [0 x i8] zeroinitializer }, %b0 ]
  %v1 = extractvalue %variant.4 %common.ret.op.i, 0
  %switch = icmp eq i32 %v1, 0
  br i1 %switch, label %b2, label %b4

common.ret:                                       ; preds = %b38, %b36, %b27, %b7, %b2
  %common.ret.op = phi %variant.5 [ %v3, %b2 ], [ %v12, %b7 ], [ %v52, %b27 ], [ %v68, %b36 ], [ %v70, %b38 ]
  ret %variant.5 %common.ret.op

b2:                                               ; preds = %liza_json.status.exit
  %v2 = extractvalue %variant.4 %common.ret.op.i, 1
  %v3 = insertvalue %variant.5 { i32 1, i64 0, %struct.JsonError zeroinitializer }, %struct.JsonError %v2, 2
  br label %common.ret

b4:                                               ; preds = %liza_json.status.exit
  %v4 = load %struct.Utf8StreamState, ptr %p0, align 8
  %v0.i8 = extractvalue %struct.Utf8StreamState %v4, 6
  switch i32 %v0.i8, label %b6.i [
    i32 1, label %b1.i
    i32 2, label %b4.i
  ]

b1.i:                                             ; preds = %b4
  %v4.i = extractvalue %struct.Utf8StreamState %v4, 7
  %v5.i = insertvalue %struct.Utf8StreamError zeroinitializer, i64 %v4.i, 1
  %v6.i = insertvalue %variant.2 { i32 1, i64 0, %struct.Utf8StreamError zeroinitializer }, %struct.Utf8StreamError %v5.i, 2
  br label %liza_utf8_stream.finish.exit

b4.i:                                             ; preds = %b4
  %v11.i = extractvalue %struct.Utf8StreamState %v4, 7
  %v12.i9 = insertvalue %struct.Utf8StreamError { %variant.0 { i32 1, [0 x i8] zeroinitializer, [0 x i8] zeroinitializer }, i64 0 }, i64 %v11.i, 1
  %v13.i = insertvalue %variant.2 { i32 1, i64 0, %struct.Utf8StreamError zeroinitializer }, %struct.Utf8StreamError %v12.i9, 2
  br label %liza_utf8_stream.finish.exit

b6.i:                                             ; preds = %b4
  %v14.i11 = extractvalue %struct.Utf8StreamState %v4, 3
  %v16.not.i = icmp eq i32 %v14.i11, 0
  br i1 %v16.not.i, label %b9.i, label %b7.i

b7.i:                                             ; preds = %b6.i
  %v18.i = extractvalue %struct.Utf8StreamState %v4, 2
  %v19.i12 = insertvalue %struct.Utf8StreamError zeroinitializer, i64 %v18.i, 1
  %v20.i = insertvalue %variant.2 { i32 1, i64 0, %struct.Utf8StreamError zeroinitializer }, %struct.Utf8StreamError %v19.i12, 2
  br label %liza_utf8_stream.finish.exit

b9.i:                                             ; preds = %b6.i
  %v21.i = extractvalue %struct.Utf8StreamState %v4, 1
  %v22.i13 = insertvalue %variant.2 zeroinitializer, i64 %v21.i, 1
  br label %liza_utf8_stream.finish.exit

liza_utf8_stream.finish.exit:                     ; preds = %b1.i, %b4.i, %b7.i, %b9.i
  %common.ret.op.i10 = phi %variant.2 [ %v6.i, %b1.i ], [ %v13.i, %b4.i ], [ %v20.i, %b7.i ], [ %v22.i13, %b9.i ]
  %v6 = extractvalue %variant.2 %common.ret.op.i10, 0
  %switch6 = icmp eq i32 %v6, 0
  br i1 %switch6, label %b6, label %b7

b6:                                               ; preds = %liza_utf8_stream.finish.exit
  %v13_ptr = getelementptr i8, ptr %p0, i64 128
  %v13 = load i32, ptr %v13_ptr, align 4
  switch i32 %v13, label %b19_to_b20 [
    i32 11, label %b18
    i32 12, label %b18
    i32 14, label %b18
    i32 17, label %b18
  ]

b7:                                               ; preds = %liza_utf8_stream.finish.exit
  %v8 = extractvalue %variant.2 %common.ret.op.i10, 2
  %v10 = extractvalue %struct.Utf8StreamError %v8, 1
  %v11 = insertvalue %struct.JsonError { %variant.1 { i32 4, [0 x i8] zeroinitializer, [0 x i8] zeroinitializer, [0 x i8] zeroinitializer, [0 x i8] zeroinitializer, [0 x i8] zeroinitializer, [0 x i8] zeroinitializer, [0 x i8] zeroinitializer, [0 x i8] zeroinitializer }, i64 0 }, i64 %v10, 1
  %v12 = insertvalue %variant.5 { i32 1, i64 0, %struct.JsonError zeroinitializer }, %struct.JsonError %v11, 2
  br label %common.ret

b18:                                              ; preds = %b6, %b6, %b6, %b6
  call void @llvm.memcpy.p0.p0.i64(ptr noundef nonnull align 8 dereferenceable(184) %v33_mem, ptr noundef nonnull align 1 dereferenceable(184) %p0, i64 184, i1 false)
  %v33_part = getelementptr inbounds nuw i8, ptr %v33_mem, i64 128
  store i32 0, ptr %v33_part, align 8
  call void @liza___liza_json_done(ptr nonnull sret(%struct.JsonState) %v34_mem, ptr nonnull %v33_mem)
  %v35_next.sroa.4.0.v34_mem.sroa_idx = getelementptr inbounds nuw i8, ptr %v34_mem, i64 48
  %v35_next.sroa.4.0.copyload = load i64, ptr %v35_next.sroa.4.0.v34_mem.sroa_idx, align 8
  %v35_next.sroa.8.0.v34_mem.sroa_idx = getelementptr inbounds nuw i8, ptr %v34_mem, i64 120
  %v35_next.sroa.8.0.copyload = load i32, ptr %v35_next.sroa.8.0.v34_mem.sroa_idx, align 8
  %v35_next.sroa.10.0.v34_mem.sroa_idx = getelementptr inbounds nuw i8, ptr %v34_mem, i64 124
  %0 = load i8, ptr %v35_next.sroa.10.0.v34_mem.sroa_idx, align 4
  %v35_next.sroa.14.0.v34_mem.sroa_idx = getelementptr inbounds nuw i8, ptr %v34_mem, i64 128
  %v35_next.sroa.14.0.copyload = load i32, ptr %v35_next.sroa.14.0.v34_mem.sroa_idx, align 8
  %v35_next.sroa.18.0.v34_mem.sroa_idx = getelementptr inbounds nuw i8, ptr %v34_mem, i64 160
  %v35_next.sroa.18.0.copyload = load i64, ptr %v35_next.sroa.18.0.v34_mem.sroa_idx, align 8
  %extract.t37 = trunc i8 %0 to i1
  br label %b20

b20:                                              ; preds = %b19_to_b20, %b18
  %.sink.off0 = phi i1 [ %extract.t, %b19_to_b20 ], [ %extract.t37, %b18 ]
  %v35_mem.sroa.726.0 = phi i64 [ %v35_next.sroa.18.0.copyload33, %b19_to_b20 ], [ %v35_next.sroa.18.0.copyload, %b18 ]
  %v35_mem.sroa.622.0 = phi i32 [ %v13, %b19_to_b20 ], [ %v35_next.sroa.14.0.copyload, %b18 ]
  %v35_mem.sroa.417.0 = phi i32 [ %v35_next.sroa.8.0.copyload31, %b19_to_b20 ], [ %v35_next.sroa.8.0.copyload, %b18 ]
  %v35_mem.sroa.2.0 = phi i64 [ %v35_next.sroa.4.0.copyload30, %b19_to_b20 ], [ %v35_next.sroa.4.0.copyload, %b18 ]
  %v35_mem.128.v36.off = add i32 %v35_mem.sroa.622.0, -4
  %switch7 = icmp ult i32 %v35_mem.128.v36.off, 3
  br i1 %switch7, label %b27, label %b29

b27:                                              ; preds = %b20
  %v51 = insertvalue %struct.JsonError { %variant.1 { i32 3, [0 x i8] zeroinitializer, [0 x i8] zeroinitializer, [0 x i8] zeroinitializer, [0 x i8] zeroinitializer, [0 x i8] zeroinitializer, [0 x i8] zeroinitializer, [0 x i8] zeroinitializer, [0 x i8] zeroinitializer }, i64 0 }, i64 %v35_mem.sroa.726.0, 1
  %v52 = insertvalue %variant.5 { i32 1, i64 0, %struct.JsonError zeroinitializer }, %struct.JsonError %v51, 2
  br label %common.ret

b29:                                              ; preds = %b20
  %v55 = icmp eq i32 %v35_mem.sroa.622.0, 0
  %v59 = icmp eq i32 %v35_mem.sroa.417.0, 0
  %v60.not5 = select i1 %v55, i1 %v59, i1 false
  %v64.not = select i1 %v60.not5, i1 %.sink.off0, i1 false
  br i1 %v64.not, label %b38, label %b36

b36:                                              ; preds = %b29
  %v67 = insertvalue %struct.JsonError { %variant.1 { i32 5, [0 x i8] zeroinitializer, [0 x i8] zeroinitializer, [0 x i8] zeroinitializer, [0 x i8] zeroinitializer, [0 x i8] zeroinitializer, [0 x i8] zeroinitializer, [0 x i8] zeroinitializer, [0 x i8] zeroinitializer }, i64 0 }, i64 %v35_mem.sroa.2.0, 1
  %v68 = insertvalue %variant.5 { i32 1, i64 0, %struct.JsonError zeroinitializer }, %struct.JsonError %v67, 2
  br label %common.ret

b38:                                              ; preds = %b29
  %v70 = insertvalue %variant.5 zeroinitializer, i64 %v35_mem.sroa.2.0, 1
  br label %common.ret

b19_to_b20:                                       ; preds = %b6
  %v35_next.sroa.4.0.p0.sroa_idx = getelementptr inbounds nuw i8, ptr %p0, i64 48
  %v35_next.sroa.4.0.copyload30 = load i64, ptr %v35_next.sroa.4.0.p0.sroa_idx, align 1
  %v35_next.sroa.8.0.p0.sroa_idx = getelementptr inbounds nuw i8, ptr %p0, i64 120
  %v35_next.sroa.8.0.copyload31 = load i32, ptr %v35_next.sroa.8.0.p0.sroa_idx, align 1
  %v35_next.sroa.10.0.p0.sroa_idx = getelementptr inbounds nuw i8, ptr %p0, i64 124
  %1 = load i8, ptr %v35_next.sroa.10.0.p0.sroa_idx, align 1
  %v35_next.sroa.18.0.p0.sroa_idx = getelementptr inbounds nuw i8, ptr %p0, i64 160
  %v35_next.sroa.18.0.copyload33 = load i64, ptr %v35_next.sroa.18.0.p0.sroa_idx, align 1
  %extract.t = trunc i8 %1 to i1
  br label %b20
}

; Function Attrs: mustprogress nofree norecurse nosync nounwind willreturn memory(none)
define noundef i32 @example_entry() local_unnamed_addr #6 {
entry:
  ret i32 0
}

; Function Attrs: mustprogress nofree norecurse nosync nounwind willreturn memory(argmem: write)
define void @stream_start(ptr writeonly captures(none) initializes((0, 30), (32, 36), (40, 125), (128, 133), (136, 172), (176, 184)) %out) local_unnamed_addr #8 {
  %v16_mem.sroa.75.sroa.0.i = alloca i8, align 4
  %v16_mem.sroa.77.sroa.0.i = alloca i8, align 4
  call void @llvm.lifetime.start.p0(i64 1, ptr nonnull %v16_mem.sroa.75.sroa.0.i)
  call void @llvm.lifetime.start.p0(i64 1, ptr nonnull %v16_mem.sroa.77.sroa.0.i)
  store i1 false, ptr %v16_mem.sroa.75.sroa.0.i, align 4
  store i1 false, ptr %v16_mem.sroa.77.sroa.0.i, align 4
  %v16_mem.sroa.5.0.return_storage.sroa_idx.i = getelementptr inbounds nuw i8, ptr %out, i64 28
  tail call void @llvm.memset.p0.i64(ptr noundef nonnull align 8 dereferenceable(28) %out, i8 0, i64 28, i1 false)
  store i8 -128, ptr %v16_mem.sroa.5.0.return_storage.sroa_idx.i, align 4
  %v16_mem.sroa.6.0.return_storage.sroa_idx.i = getelementptr inbounds nuw i8, ptr %out, i64 29
  store i8 -65, ptr %v16_mem.sroa.6.0.return_storage.sroa_idx.i, align 1
  %v16_mem.sroa.71.0.return_storage.sroa_idx.i = getelementptr inbounds nuw i8, ptr %out, i64 32
  store i32 0, ptr %v16_mem.sroa.71.0.return_storage.sroa_idx.i, align 8
  %v16_mem.sroa.82.0.return_storage.sroa_idx.i = getelementptr inbounds nuw i8, ptr %out, i64 40
  %v16_mem.sroa.75.0.return_storage.sroa_idx.i = getelementptr inbounds nuw i8, ptr %out, i64 124
  tail call void @llvm.memset.p0.i64(ptr noundef nonnull align 8 dereferenceable(84) %v16_mem.sroa.82.0.return_storage.sroa_idx.i, i8 0, i64 84, i1 false)
  %v16_mem.sroa.75.sroa.0.i.0.v16_mem.sroa.75.sroa.0.i.0.v16_mem.sroa.75.sroa.0.i.0.v16_mem.sroa.75.sroa.0.0.v16_mem.sroa.75.sroa.0.0..i = load i8, ptr %v16_mem.sroa.75.sroa.0.i, align 4
  store i8 %v16_mem.sroa.75.sroa.0.i.0.v16_mem.sroa.75.sroa.0.i.0.v16_mem.sroa.75.sroa.0.i.0.v16_mem.sroa.75.sroa.0.0.v16_mem.sroa.75.sroa.0.0..i, ptr %v16_mem.sroa.75.0.return_storage.sroa_idx.i, align 4
  %v16_mem.sroa.764.0.return_storage.sroa_idx.i = getelementptr inbounds nuw i8, ptr %out, i64 128
  store i32 0, ptr %v16_mem.sroa.764.0.return_storage.sroa_idx.i, align 8
  %v16_mem.sroa.77.0.return_storage.sroa_idx.i = getelementptr inbounds nuw i8, ptr %out, i64 132
  %v16_mem.sroa.77.sroa.0.i.0.v16_mem.sroa.77.sroa.0.i.0.v16_mem.sroa.77.sroa.0.i.0.v16_mem.sroa.77.sroa.0.0.v16_mem.sroa.77.sroa.0.0..i = load i8, ptr %v16_mem.sroa.77.sroa.0.i, align 4
  store i8 %v16_mem.sroa.77.sroa.0.i.0.v16_mem.sroa.77.sroa.0.i.0.v16_mem.sroa.77.sroa.0.i.0.v16_mem.sroa.77.sroa.0.0.v16_mem.sroa.77.sroa.0.0..i, ptr %v16_mem.sroa.77.0.return_storage.sroa_idx.i, align 4
  %v16_mem.sroa.785.0.return_storage.sroa_idx.i = getelementptr inbounds nuw i8, ptr %out, i64 136
  %v16_mem.sroa.857.0.return_storage.sroa_idx.i = getelementptr inbounds nuw i8, ptr %out, i64 176
  store i64 0, ptr %v16_mem.sroa.857.0.return_storage.sroa_idx.i, align 8
  tail call void @llvm.memset.p0.i64(ptr noundef nonnull align 8 dereferenceable(36) %v16_mem.sroa.785.0.return_storage.sroa_idx.i, i8 0, i64 36, i1 false)
  call void @llvm.lifetime.end.p0(i64 1, ptr nonnull %v16_mem.sroa.75.sroa.0.i)
  call void @llvm.lifetime.end.p0(i64 1, ptr nonnull %v16_mem.sroa.77.sroa.0.i)
  ret void
}

; Function Attrs: nounwind memory(readwrite, inaccessiblemem: write)
define void @stream_feed(ptr captures(none) %state, ptr %bytes, i32 %length) local_unnamed_addr #3 {
  %result = alloca %struct.JsonState, align 8
  %a = insertvalue { ptr, i32 } zeroinitializer, ptr %bytes, 0
  %v = insertvalue { ptr, i32 } %a, i32 %length, 1
  call void @liza_json.feed(ptr nonnull sret(%struct.JsonState) %result, ptr %state, { ptr, i32 } %v)
  %n.fca.0.0.load = load i64, ptr %result, align 8
  %n.fca.0.0.insert = insertvalue %struct.JsonState poison, i64 %n.fca.0.0.load, 0, 0
  %n.fca.0.1.gep = getelementptr inbounds nuw i8, ptr %result, i64 8
  %n.fca.0.1.load = load i64, ptr %n.fca.0.1.gep, align 8
  %n.fca.0.1.insert = insertvalue %struct.JsonState %n.fca.0.0.insert, i64 %n.fca.0.1.load, 0, 1
  %n.fca.0.2.gep = getelementptr inbounds nuw i8, ptr %result, i64 16
  %n.fca.0.2.load = load i64, ptr %n.fca.0.2.gep, align 8
  %n.fca.0.2.insert = insertvalue %struct.JsonState %n.fca.0.1.insert, i64 %n.fca.0.2.load, 0, 2
  %n.fca.0.3.gep = getelementptr inbounds nuw i8, ptr %result, i64 24
  %n.fca.0.3.load = load i32, ptr %n.fca.0.3.gep, align 8
  %n.fca.0.3.insert = insertvalue %struct.JsonState %n.fca.0.2.insert, i32 %n.fca.0.3.load, 0, 3
  %n.fca.0.4.gep = getelementptr inbounds nuw i8, ptr %result, i64 28
  %n.fca.0.4.load = load i8, ptr %n.fca.0.4.gep, align 4
  %n.fca.0.4.insert = insertvalue %struct.JsonState %n.fca.0.3.insert, i8 %n.fca.0.4.load, 0, 4
  %n.fca.0.5.gep = getelementptr inbounds nuw i8, ptr %result, i64 29
  %n.fca.0.5.load = load i8, ptr %n.fca.0.5.gep, align 1
  %n.fca.0.5.insert = insertvalue %struct.JsonState %n.fca.0.4.insert, i8 %n.fca.0.5.load, 0, 5
  %n.fca.0.6.gep = getelementptr inbounds nuw i8, ptr %result, i64 32
  %n.fca.0.6.load = load i32, ptr %n.fca.0.6.gep, align 8
  %n.fca.0.6.insert = insertvalue %struct.JsonState %n.fca.0.5.insert, i32 %n.fca.0.6.load, 0, 6
  %n.fca.0.7.gep = getelementptr inbounds nuw i8, ptr %result, i64 40
  %n.fca.0.7.load = load i64, ptr %n.fca.0.7.gep, align 8
  %n.fca.0.7.insert = insertvalue %struct.JsonState %n.fca.0.6.insert, i64 %n.fca.0.7.load, 0, 7
  %n.fca.1.gep = getelementptr inbounds nuw i8, ptr %result, i64 48
  %n.fca.1.load = load i64, ptr %n.fca.1.gep, align 8
  %n.fca.1.insert = insertvalue %struct.JsonState %n.fca.0.7.insert, i64 %n.fca.1.load, 1
  %n.fca.2.0.gep = getelementptr inbounds nuw i8, ptr %result, i64 56
  %n.fca.2.0.load = load i8, ptr %n.fca.2.0.gep, align 8
  %n.fca.2.0.insert = insertvalue %struct.JsonState %n.fca.1.insert, i8 %n.fca.2.0.load, 2, 0
  %n.fca.2.1.gep = getelementptr inbounds nuw i8, ptr %result, i64 57
  %n.fca.2.1.load = load i8, ptr %n.fca.2.1.gep, align 1
  %n.fca.2.1.insert = insertvalue %struct.JsonState %n.fca.2.0.insert, i8 %n.fca.2.1.load, 2, 1
  %n.fca.2.2.gep = getelementptr inbounds nuw i8, ptr %result, i64 58
  %n.fca.2.2.load = load i8, ptr %n.fca.2.2.gep, align 2
  %n.fca.2.2.insert = insertvalue %struct.JsonState %n.fca.2.1.insert, i8 %n.fca.2.2.load, 2, 2
  %n.fca.2.3.gep = getelementptr inbounds nuw i8, ptr %result, i64 59
  %n.fca.2.3.load = load i8, ptr %n.fca.2.3.gep, align 1
  %n.fca.2.3.insert = insertvalue %struct.JsonState %n.fca.2.2.insert, i8 %n.fca.2.3.load, 2, 3
  %n.fca.2.4.gep = getelementptr inbounds nuw i8, ptr %result, i64 60
  %n.fca.2.4.load = load i8, ptr %n.fca.2.4.gep, align 4
  %n.fca.2.4.insert = insertvalue %struct.JsonState %n.fca.2.3.insert, i8 %n.fca.2.4.load, 2, 4
  %n.fca.2.5.gep = getelementptr inbounds nuw i8, ptr %result, i64 61
  %n.fca.2.5.load = load i8, ptr %n.fca.2.5.gep, align 1
  %n.fca.2.5.insert = insertvalue %struct.JsonState %n.fca.2.4.insert, i8 %n.fca.2.5.load, 2, 5
  %n.fca.2.6.gep = getelementptr inbounds nuw i8, ptr %result, i64 62
  %n.fca.2.6.load = load i8, ptr %n.fca.2.6.gep, align 2
  %n.fca.2.6.insert = insertvalue %struct.JsonState %n.fca.2.5.insert, i8 %n.fca.2.6.load, 2, 6
  %n.fca.2.7.gep = getelementptr inbounds nuw i8, ptr %result, i64 63
  %n.fca.2.7.load = load i8, ptr %n.fca.2.7.gep, align 1
  %n.fca.2.7.insert = insertvalue %struct.JsonState %n.fca.2.6.insert, i8 %n.fca.2.7.load, 2, 7
  %n.fca.2.8.gep = getelementptr inbounds nuw i8, ptr %result, i64 64
  %n.fca.2.8.load = load i8, ptr %n.fca.2.8.gep, align 8
  %n.fca.2.8.insert = insertvalue %struct.JsonState %n.fca.2.7.insert, i8 %n.fca.2.8.load, 2, 8
  %n.fca.2.9.gep = getelementptr inbounds nuw i8, ptr %result, i64 65
  %n.fca.2.9.load = load i8, ptr %n.fca.2.9.gep, align 1
  %n.fca.2.9.insert = insertvalue %struct.JsonState %n.fca.2.8.insert, i8 %n.fca.2.9.load, 2, 9
  %n.fca.2.10.gep = getelementptr inbounds nuw i8, ptr %result, i64 66
  %n.fca.2.10.load = load i8, ptr %n.fca.2.10.gep, align 2
  %n.fca.2.10.insert = insertvalue %struct.JsonState %n.fca.2.9.insert, i8 %n.fca.2.10.load, 2, 10
  %n.fca.2.11.gep = getelementptr inbounds nuw i8, ptr %result, i64 67
  %n.fca.2.11.load = load i8, ptr %n.fca.2.11.gep, align 1
  %n.fca.2.11.insert = insertvalue %struct.JsonState %n.fca.2.10.insert, i8 %n.fca.2.11.load, 2, 11
  %n.fca.2.12.gep = getelementptr inbounds nuw i8, ptr %result, i64 68
  %n.fca.2.12.load = load i8, ptr %n.fca.2.12.gep, align 4
  %n.fca.2.12.insert = insertvalue %struct.JsonState %n.fca.2.11.insert, i8 %n.fca.2.12.load, 2, 12
  %n.fca.2.13.gep = getelementptr inbounds nuw i8, ptr %result, i64 69
  %n.fca.2.13.load = load i8, ptr %n.fca.2.13.gep, align 1
  %n.fca.2.13.insert = insertvalue %struct.JsonState %n.fca.2.12.insert, i8 %n.fca.2.13.load, 2, 13
  %n.fca.2.14.gep = getelementptr inbounds nuw i8, ptr %result, i64 70
  %n.fca.2.14.load = load i8, ptr %n.fca.2.14.gep, align 2
  %n.fca.2.14.insert = insertvalue %struct.JsonState %n.fca.2.13.insert, i8 %n.fca.2.14.load, 2, 14
  %n.fca.2.15.gep = getelementptr inbounds nuw i8, ptr %result, i64 71
  %n.fca.2.15.load = load i8, ptr %n.fca.2.15.gep, align 1
  %n.fca.2.15.insert = insertvalue %struct.JsonState %n.fca.2.14.insert, i8 %n.fca.2.15.load, 2, 15
  %n.fca.2.16.gep = getelementptr inbounds nuw i8, ptr %result, i64 72
  %n.fca.2.16.load = load i8, ptr %n.fca.2.16.gep, align 8
  %n.fca.2.16.insert = insertvalue %struct.JsonState %n.fca.2.15.insert, i8 %n.fca.2.16.load, 2, 16
  %n.fca.2.17.gep = getelementptr inbounds nuw i8, ptr %result, i64 73
  %n.fca.2.17.load = load i8, ptr %n.fca.2.17.gep, align 1
  %n.fca.2.17.insert = insertvalue %struct.JsonState %n.fca.2.16.insert, i8 %n.fca.2.17.load, 2, 17
  %n.fca.2.18.gep = getelementptr inbounds nuw i8, ptr %result, i64 74
  %n.fca.2.18.load = load i8, ptr %n.fca.2.18.gep, align 2
  %n.fca.2.18.insert = insertvalue %struct.JsonState %n.fca.2.17.insert, i8 %n.fca.2.18.load, 2, 18
  %n.fca.2.19.gep = getelementptr inbounds nuw i8, ptr %result, i64 75
  %n.fca.2.19.load = load i8, ptr %n.fca.2.19.gep, align 1
  %n.fca.2.19.insert = insertvalue %struct.JsonState %n.fca.2.18.insert, i8 %n.fca.2.19.load, 2, 19
  %n.fca.2.20.gep = getelementptr inbounds nuw i8, ptr %result, i64 76
  %n.fca.2.20.load = load i8, ptr %n.fca.2.20.gep, align 4
  %n.fca.2.20.insert = insertvalue %struct.JsonState %n.fca.2.19.insert, i8 %n.fca.2.20.load, 2, 20
  %n.fca.2.21.gep = getelementptr inbounds nuw i8, ptr %result, i64 77
  %n.fca.2.21.load = load i8, ptr %n.fca.2.21.gep, align 1
  %n.fca.2.21.insert = insertvalue %struct.JsonState %n.fca.2.20.insert, i8 %n.fca.2.21.load, 2, 21
  %n.fca.2.22.gep = getelementptr inbounds nuw i8, ptr %result, i64 78
  %n.fca.2.22.load = load i8, ptr %n.fca.2.22.gep, align 2
  %n.fca.2.22.insert = insertvalue %struct.JsonState %n.fca.2.21.insert, i8 %n.fca.2.22.load, 2, 22
  %n.fca.2.23.gep = getelementptr inbounds nuw i8, ptr %result, i64 79
  %n.fca.2.23.load = load i8, ptr %n.fca.2.23.gep, align 1
  %n.fca.2.23.insert = insertvalue %struct.JsonState %n.fca.2.22.insert, i8 %n.fca.2.23.load, 2, 23
  %n.fca.2.24.gep = getelementptr inbounds nuw i8, ptr %result, i64 80
  %n.fca.2.24.load = load i8, ptr %n.fca.2.24.gep, align 8
  %n.fca.2.24.insert = insertvalue %struct.JsonState %n.fca.2.23.insert, i8 %n.fca.2.24.load, 2, 24
  %n.fca.2.25.gep = getelementptr inbounds nuw i8, ptr %result, i64 81
  %n.fca.2.25.load = load i8, ptr %n.fca.2.25.gep, align 1
  %n.fca.2.25.insert = insertvalue %struct.JsonState %n.fca.2.24.insert, i8 %n.fca.2.25.load, 2, 25
  %n.fca.2.26.gep = getelementptr inbounds nuw i8, ptr %result, i64 82
  %n.fca.2.26.load = load i8, ptr %n.fca.2.26.gep, align 2
  %n.fca.2.26.insert = insertvalue %struct.JsonState %n.fca.2.25.insert, i8 %n.fca.2.26.load, 2, 26
  %n.fca.2.27.gep = getelementptr inbounds nuw i8, ptr %result, i64 83
  %n.fca.2.27.load = load i8, ptr %n.fca.2.27.gep, align 1
  %n.fca.2.27.insert = insertvalue %struct.JsonState %n.fca.2.26.insert, i8 %n.fca.2.27.load, 2, 27
  %n.fca.2.28.gep = getelementptr inbounds nuw i8, ptr %result, i64 84
  %n.fca.2.28.load = load i8, ptr %n.fca.2.28.gep, align 4
  %n.fca.2.28.insert = insertvalue %struct.JsonState %n.fca.2.27.insert, i8 %n.fca.2.28.load, 2, 28
  %n.fca.2.29.gep = getelementptr inbounds nuw i8, ptr %result, i64 85
  %n.fca.2.29.load = load i8, ptr %n.fca.2.29.gep, align 1
  %n.fca.2.29.insert = insertvalue %struct.JsonState %n.fca.2.28.insert, i8 %n.fca.2.29.load, 2, 29
  %n.fca.2.30.gep = getelementptr inbounds nuw i8, ptr %result, i64 86
  %n.fca.2.30.load = load i8, ptr %n.fca.2.30.gep, align 2
  %n.fca.2.30.insert = insertvalue %struct.JsonState %n.fca.2.29.insert, i8 %n.fca.2.30.load, 2, 30
  %n.fca.2.31.gep = getelementptr inbounds nuw i8, ptr %result, i64 87
  %n.fca.2.31.load = load i8, ptr %n.fca.2.31.gep, align 1
  %n.fca.2.31.insert = insertvalue %struct.JsonState %n.fca.2.30.insert, i8 %n.fca.2.31.load, 2, 31
  %n.fca.2.32.gep = getelementptr inbounds nuw i8, ptr %result, i64 88
  %n.fca.2.32.load = load i8, ptr %n.fca.2.32.gep, align 8
  %n.fca.2.32.insert = insertvalue %struct.JsonState %n.fca.2.31.insert, i8 %n.fca.2.32.load, 2, 32
  %n.fca.2.33.gep = getelementptr inbounds nuw i8, ptr %result, i64 89
  %n.fca.2.33.load = load i8, ptr %n.fca.2.33.gep, align 1
  %n.fca.2.33.insert = insertvalue %struct.JsonState %n.fca.2.32.insert, i8 %n.fca.2.33.load, 2, 33
  %n.fca.2.34.gep = getelementptr inbounds nuw i8, ptr %result, i64 90
  %n.fca.2.34.load = load i8, ptr %n.fca.2.34.gep, align 2
  %n.fca.2.34.insert = insertvalue %struct.JsonState %n.fca.2.33.insert, i8 %n.fca.2.34.load, 2, 34
  %n.fca.2.35.gep = getelementptr inbounds nuw i8, ptr %result, i64 91
  %n.fca.2.35.load = load i8, ptr %n.fca.2.35.gep, align 1
  %n.fca.2.35.insert = insertvalue %struct.JsonState %n.fca.2.34.insert, i8 %n.fca.2.35.load, 2, 35
  %n.fca.2.36.gep = getelementptr inbounds nuw i8, ptr %result, i64 92
  %n.fca.2.36.load = load i8, ptr %n.fca.2.36.gep, align 4
  %n.fca.2.36.insert = insertvalue %struct.JsonState %n.fca.2.35.insert, i8 %n.fca.2.36.load, 2, 36
  %n.fca.2.37.gep = getelementptr inbounds nuw i8, ptr %result, i64 93
  %n.fca.2.37.load = load i8, ptr %n.fca.2.37.gep, align 1
  %n.fca.2.37.insert = insertvalue %struct.JsonState %n.fca.2.36.insert, i8 %n.fca.2.37.load, 2, 37
  %n.fca.2.38.gep = getelementptr inbounds nuw i8, ptr %result, i64 94
  %n.fca.2.38.load = load i8, ptr %n.fca.2.38.gep, align 2
  %n.fca.2.38.insert = insertvalue %struct.JsonState %n.fca.2.37.insert, i8 %n.fca.2.38.load, 2, 38
  %n.fca.2.39.gep = getelementptr inbounds nuw i8, ptr %result, i64 95
  %n.fca.2.39.load = load i8, ptr %n.fca.2.39.gep, align 1
  %n.fca.2.39.insert = insertvalue %struct.JsonState %n.fca.2.38.insert, i8 %n.fca.2.39.load, 2, 39
  %n.fca.2.40.gep = getelementptr inbounds nuw i8, ptr %result, i64 96
  %n.fca.2.40.load = load i8, ptr %n.fca.2.40.gep, align 8
  %n.fca.2.40.insert = insertvalue %struct.JsonState %n.fca.2.39.insert, i8 %n.fca.2.40.load, 2, 40
  %n.fca.2.41.gep = getelementptr inbounds nuw i8, ptr %result, i64 97
  %n.fca.2.41.load = load i8, ptr %n.fca.2.41.gep, align 1
  %n.fca.2.41.insert = insertvalue %struct.JsonState %n.fca.2.40.insert, i8 %n.fca.2.41.load, 2, 41
  %n.fca.2.42.gep = getelementptr inbounds nuw i8, ptr %result, i64 98
  %n.fca.2.42.load = load i8, ptr %n.fca.2.42.gep, align 2
  %n.fca.2.42.insert = insertvalue %struct.JsonState %n.fca.2.41.insert, i8 %n.fca.2.42.load, 2, 42
  %n.fca.2.43.gep = getelementptr inbounds nuw i8, ptr %result, i64 99
  %n.fca.2.43.load = load i8, ptr %n.fca.2.43.gep, align 1
  %n.fca.2.43.insert = insertvalue %struct.JsonState %n.fca.2.42.insert, i8 %n.fca.2.43.load, 2, 43
  %n.fca.2.44.gep = getelementptr inbounds nuw i8, ptr %result, i64 100
  %n.fca.2.44.load = load i8, ptr %n.fca.2.44.gep, align 4
  %n.fca.2.44.insert = insertvalue %struct.JsonState %n.fca.2.43.insert, i8 %n.fca.2.44.load, 2, 44
  %n.fca.2.45.gep = getelementptr inbounds nuw i8, ptr %result, i64 101
  %n.fca.2.45.load = load i8, ptr %n.fca.2.45.gep, align 1
  %n.fca.2.45.insert = insertvalue %struct.JsonState %n.fca.2.44.insert, i8 %n.fca.2.45.load, 2, 45
  %n.fca.2.46.gep = getelementptr inbounds nuw i8, ptr %result, i64 102
  %n.fca.2.46.load = load i8, ptr %n.fca.2.46.gep, align 2
  %n.fca.2.46.insert = insertvalue %struct.JsonState %n.fca.2.45.insert, i8 %n.fca.2.46.load, 2, 46
  %n.fca.2.47.gep = getelementptr inbounds nuw i8, ptr %result, i64 103
  %n.fca.2.47.load = load i8, ptr %n.fca.2.47.gep, align 1
  %n.fca.2.47.insert = insertvalue %struct.JsonState %n.fca.2.46.insert, i8 %n.fca.2.47.load, 2, 47
  %n.fca.2.48.gep = getelementptr inbounds nuw i8, ptr %result, i64 104
  %n.fca.2.48.load = load i8, ptr %n.fca.2.48.gep, align 8
  %n.fca.2.48.insert = insertvalue %struct.JsonState %n.fca.2.47.insert, i8 %n.fca.2.48.load, 2, 48
  %n.fca.2.49.gep = getelementptr inbounds nuw i8, ptr %result, i64 105
  %n.fca.2.49.load = load i8, ptr %n.fca.2.49.gep, align 1
  %n.fca.2.49.insert = insertvalue %struct.JsonState %n.fca.2.48.insert, i8 %n.fca.2.49.load, 2, 49
  %n.fca.2.50.gep = getelementptr inbounds nuw i8, ptr %result, i64 106
  %n.fca.2.50.load = load i8, ptr %n.fca.2.50.gep, align 2
  %n.fca.2.50.insert = insertvalue %struct.JsonState %n.fca.2.49.insert, i8 %n.fca.2.50.load, 2, 50
  %n.fca.2.51.gep = getelementptr inbounds nuw i8, ptr %result, i64 107
  %n.fca.2.51.load = load i8, ptr %n.fca.2.51.gep, align 1
  %n.fca.2.51.insert = insertvalue %struct.JsonState %n.fca.2.50.insert, i8 %n.fca.2.51.load, 2, 51
  %n.fca.2.52.gep = getelementptr inbounds nuw i8, ptr %result, i64 108
  %n.fca.2.52.load = load i8, ptr %n.fca.2.52.gep, align 4
  %n.fca.2.52.insert = insertvalue %struct.JsonState %n.fca.2.51.insert, i8 %n.fca.2.52.load, 2, 52
  %n.fca.2.53.gep = getelementptr inbounds nuw i8, ptr %result, i64 109
  %n.fca.2.53.load = load i8, ptr %n.fca.2.53.gep, align 1
  %n.fca.2.53.insert = insertvalue %struct.JsonState %n.fca.2.52.insert, i8 %n.fca.2.53.load, 2, 53
  %n.fca.2.54.gep = getelementptr inbounds nuw i8, ptr %result, i64 110
  %n.fca.2.54.load = load i8, ptr %n.fca.2.54.gep, align 2
  %n.fca.2.54.insert = insertvalue %struct.JsonState %n.fca.2.53.insert, i8 %n.fca.2.54.load, 2, 54
  %n.fca.2.55.gep = getelementptr inbounds nuw i8, ptr %result, i64 111
  %n.fca.2.55.load = load i8, ptr %n.fca.2.55.gep, align 1
  %n.fca.2.55.insert = insertvalue %struct.JsonState %n.fca.2.54.insert, i8 %n.fca.2.55.load, 2, 55
  %n.fca.2.56.gep = getelementptr inbounds nuw i8, ptr %result, i64 112
  %n.fca.2.56.load = load i8, ptr %n.fca.2.56.gep, align 8
  %n.fca.2.56.insert = insertvalue %struct.JsonState %n.fca.2.55.insert, i8 %n.fca.2.56.load, 2, 56
  %n.fca.2.57.gep = getelementptr inbounds nuw i8, ptr %result, i64 113
  %n.fca.2.57.load = load i8, ptr %n.fca.2.57.gep, align 1
  %n.fca.2.57.insert = insertvalue %struct.JsonState %n.fca.2.56.insert, i8 %n.fca.2.57.load, 2, 57
  %n.fca.2.58.gep = getelementptr inbounds nuw i8, ptr %result, i64 114
  %n.fca.2.58.load = load i8, ptr %n.fca.2.58.gep, align 2
  %n.fca.2.58.insert = insertvalue %struct.JsonState %n.fca.2.57.insert, i8 %n.fca.2.58.load, 2, 58
  %n.fca.2.59.gep = getelementptr inbounds nuw i8, ptr %result, i64 115
  %n.fca.2.59.load = load i8, ptr %n.fca.2.59.gep, align 1
  %n.fca.2.59.insert = insertvalue %struct.JsonState %n.fca.2.58.insert, i8 %n.fca.2.59.load, 2, 59
  %n.fca.2.60.gep = getelementptr inbounds nuw i8, ptr %result, i64 116
  %n.fca.2.60.load = load i8, ptr %n.fca.2.60.gep, align 4
  %n.fca.2.60.insert = insertvalue %struct.JsonState %n.fca.2.59.insert, i8 %n.fca.2.60.load, 2, 60
  %n.fca.2.61.gep = getelementptr inbounds nuw i8, ptr %result, i64 117
  %n.fca.2.61.load = load i8, ptr %n.fca.2.61.gep, align 1
  %n.fca.2.61.insert = insertvalue %struct.JsonState %n.fca.2.60.insert, i8 %n.fca.2.61.load, 2, 61
  %n.fca.2.62.gep = getelementptr inbounds nuw i8, ptr %result, i64 118
  %n.fca.2.62.load = load i8, ptr %n.fca.2.62.gep, align 2
  %n.fca.2.62.insert = insertvalue %struct.JsonState %n.fca.2.61.insert, i8 %n.fca.2.62.load, 2, 62
  %n.fca.2.63.gep = getelementptr inbounds nuw i8, ptr %result, i64 119
  %n.fca.2.63.load = load i8, ptr %n.fca.2.63.gep, align 1
  %n.fca.2.63.insert = insertvalue %struct.JsonState %n.fca.2.62.insert, i8 %n.fca.2.63.load, 2, 63
  %n.fca.3.gep = getelementptr inbounds nuw i8, ptr %result, i64 120
  %n.fca.3.load = load i32, ptr %n.fca.3.gep, align 8
  %n.fca.3.insert = insertvalue %struct.JsonState %n.fca.2.63.insert, i32 %n.fca.3.load, 3
  %n.fca.4.gep = getelementptr inbounds nuw i8, ptr %result, i64 124
  %n.fca.4.load = load i1, ptr %n.fca.4.gep, align 4
  %n.fca.4.insert = insertvalue %struct.JsonState %n.fca.3.insert, i1 %n.fca.4.load, 4
  %n.fca.5.gep = getelementptr inbounds nuw i8, ptr %result, i64 128
  %n.fca.5.load = load i32, ptr %n.fca.5.gep, align 8
  %n.fca.5.insert = insertvalue %struct.JsonState %n.fca.4.insert, i32 %n.fca.5.load, 5
  %n.fca.6.gep = getelementptr inbounds nuw i8, ptr %result, i64 132
  %n.fca.6.load = load i1, ptr %n.fca.6.gep, align 4
  %n.fca.6.insert = insertvalue %struct.JsonState %n.fca.5.insert, i1 %n.fca.6.load, 6
  %n.fca.7.gep = getelementptr inbounds nuw i8, ptr %result, i64 136
  %n.fca.7.load = load i32, ptr %n.fca.7.gep, align 8
  %n.fca.7.insert = insertvalue %struct.JsonState %n.fca.6.insert, i32 %n.fca.7.load, 7
  %n.fca.8.gep = getelementptr inbounds nuw i8, ptr %result, i64 140
  %n.fca.8.load = load i32, ptr %n.fca.8.gep, align 4
  %n.fca.8.insert = insertvalue %struct.JsonState %n.fca.7.insert, i32 %n.fca.8.load, 8
  %n.fca.9.gep = getelementptr inbounds nuw i8, ptr %result, i64 144
  %n.fca.9.load = load i32, ptr %n.fca.9.gep, align 8
  %n.fca.9.insert = insertvalue %struct.JsonState %n.fca.8.insert, i32 %n.fca.9.load, 9
  %n.fca.10.gep = getelementptr inbounds nuw i8, ptr %result, i64 148
  %n.fca.10.load = load i32, ptr %n.fca.10.gep, align 4
  %n.fca.10.insert = insertvalue %struct.JsonState %n.fca.9.insert, i32 %n.fca.10.load, 10
  %n.fca.11.gep = getelementptr inbounds nuw i8, ptr %result, i64 152
  %n.fca.11.load = load i64, ptr %n.fca.11.gep, align 8
  %n.fca.11.insert = insertvalue %struct.JsonState %n.fca.10.insert, i64 %n.fca.11.load, 11
  %n.fca.12.gep = getelementptr inbounds nuw i8, ptr %result, i64 160
  %n.fca.12.load = load i64, ptr %n.fca.12.gep, align 8
  %n.fca.12.insert = insertvalue %struct.JsonState %n.fca.11.insert, i64 %n.fca.12.load, 12
  %n.fca.13.gep = getelementptr inbounds nuw i8, ptr %result, i64 168
  %n.fca.13.load = load i32, ptr %n.fca.13.gep, align 8
  %n.fca.13.insert = insertvalue %struct.JsonState %n.fca.12.insert, i32 %n.fca.13.load, 13
  %n.fca.14.gep = getelementptr inbounds nuw i8, ptr %result, i64 176
  %n.fca.14.load = load i64, ptr %n.fca.14.gep, align 8
  %n.fca.14.insert = insertvalue %struct.JsonState %n.fca.13.insert, i64 %n.fca.14.load, 14
  store %struct.JsonState %n.fca.14.insert, ptr %state, align 8
  ret void
}

; Function Attrs: nounwind memory(readwrite, inaccessiblemem: write)
define range(i32 0, 9) i32 @stream_status(ptr readonly captures(none) %state) local_unnamed_addr #3 {
liza_status.exit:
  %v0.i = tail call %variant.5 @liza_json.finish(ptr readonly %state)
  %v1.i = extractvalue %variant.5 %v0.i, 0
  %switch.i = icmp eq i32 %v1.i, 0
  %v4.i = extractvalue %variant.5 %v0.i, 2
  %v5.i = extractvalue %struct.JsonError %v4.i, 0
  %v6.i = extractvalue %variant.1 %v5.i, 0
  %switch.offset = add nsw i32 %v6.i, 1
  %common.ret.op.i = select i1 %switch.i, i32 0, i32 %switch.offset
  ret i32 %common.ret.op.i
}

; Function Attrs: mustprogress nofree norecurse nosync nounwind willreturn memory(argmem: read)
define range(i32 0, 2) i32 @stream_pending(ptr readonly captures(none) %state) local_unnamed_addr #4 {
  %v0_ptr.i.i = getelementptr i8, ptr %state, i64 168
  %v0.i.i = load i32, ptr %v0_ptr.i.i, align 4
  %v2.i.not.i = icmp ne i32 %v0.i.i, 0
  %spec.select.i = zext i1 %v2.i.not.i to i32
  ret i32 %spec.select.i
}

; Function Attrs: nounwind memory(readwrite, inaccessiblemem: write)
define i64 @stream_value(ptr readonly captures(none) %state) local_unnamed_addr #3 {
  %v0.i = tail call %variant.5 @liza_json.finish(ptr readonly %state)
  %v1.i = extractvalue %variant.5 %v0.i, 0
  %switch.i = icmp eq i32 %v1.i, 0
  %v2.i = extractvalue %variant.5 %v0.i, 1
  %v3.i = extractvalue %variant.5 %v0.i, 2
  %v4.i = extractvalue %struct.JsonError %v3.i, 1
  %common.ret.op.i = select i1 %switch.i, i64 %v2.i, i64 %v4.i
  ret i64 %common.ret.op.i
}

; Function Attrs: mustprogress nofree norecurse nosync nounwind willreturn memory(none)
define noundef i64 @stream_size() local_unnamed_addr #6 {
  ret i64 184
}

; Function Attrs: nocallback nofree nounwind willreturn memory(argmem: readwrite)
declare void @llvm.memcpy.p0.p0.i64(ptr noalias writeonly captures(none), ptr noalias readonly captures(none), i64, i1 immarg) #9

; Function Attrs: nocallback nofree nounwind willreturn memory(argmem: write)
declare void @llvm.memset.p0.i64(ptr writeonly captures(none), i8, i64, i1 immarg) #10

; Function Attrs: nocallback nofree nosync nounwind willreturn memory(argmem: readwrite)
declare void @llvm.lifetime.start.p0(i64 immarg, ptr captures(none)) #11

; Function Attrs: nocallback nofree nosync nounwind willreturn memory(argmem: readwrite)
declare void @llvm.lifetime.end.p0(i64 immarg, ptr captures(none)) #11

attributes #0 = { cold noreturn nounwind memory(inaccessiblemem: write) }
attributes #1 = { mustprogress nocallback nofree nounwind willreturn memory(argmem: readwrite) }
attributes #2 = { mustprogress nocallback nofree nosync nounwind speculatable willreturn memory(none) }
attributes #3 = { nounwind memory(readwrite, inaccessiblemem: write) }
attributes #4 = { mustprogress nofree norecurse nosync nounwind willreturn memory(argmem: read) }
attributes #5 = { mustprogress nofree norecurse nosync nounwind willreturn memory(argmem: readwrite) }
attributes #6 = { mustprogress nofree norecurse nosync nounwind willreturn memory(none) }
attributes #7 = { nounwind memory(inaccessiblemem: write) }
attributes #8 = { mustprogress nofree norecurse nosync nounwind willreturn memory(argmem: write) }
attributes #9 = { nocallback nofree nounwind willreturn memory(argmem: readwrite) }
attributes #10 = { nocallback nofree nounwind willreturn memory(argmem: write) }
attributes #11 = { nocallback nofree nosync nounwind willreturn memory(argmem: readwrite) }
