; ModuleID = '/private/tmp/liza-json-bench/benchmarks/json/parser.cpp'
source_filename = "/private/tmp/liza-json-bench/benchmarks/json/parser.cpp"
target datalayout = "e-m:o-p270:32:32-p271:32:32-p272:64:64-i64:64-i128:128-n32:64-S128-Fn32"
target triple = "arm64-apple-macosx26.0.0"

%struct.State = type { %struct.Encoding, i64, %"struct.std::__1::array", i32, i8, i32, i8, i32, i32, i32, i32, i64, i64, i32, i64 }
%struct.Encoding = type { i64, i64, i64, i32, i8, i8, i32, i64 }
%"struct.std::__1::array" = type { [64 x i8] }

@.str = private unnamed_addr constant [10 x i8] c"array::at\00", align 1
@_ZTISt12out_of_range = external constant ptr
@_ZTVSt12out_of_range = external unnamed_addr constant { [5 x ptr] }, align 8

; Function Attrs: mustprogress nofree norecurse nosync nounwind ssp willreturn memory(none) uwtable(sync)
define noundef i64 @stream_size() local_unnamed_addr #0 {
  ret i64 184
}

; Function Attrs: mustprogress nofree norecurse nosync nounwind ssp willreturn memory(argmem: write) uwtable(sync)
define void @stream_start(ptr noundef writeonly captures(none) initializes((0, 30), (32, 36), (40, 125), (128, 133), (136, 172), (176, 184)) %0) local_unnamed_addr #1 {
  %2 = getelementptr inbounds nuw i8, ptr %0, i64 28
  tail call void @llvm.memset.p0.i64(ptr noundef nonnull align 8 dereferenceable(28) %0, i8 0, i64 28, i1 false)
  store i8 -128, ptr %2, align 4, !tbaa !6
  %3 = getelementptr inbounds nuw i8, ptr %0, i64 29
  store i8 -65, ptr %3, align 1, !tbaa !12
  %4 = getelementptr inbounds nuw i8, ptr %0, i64 32
  store i32 0, ptr %4, align 8, !tbaa !13
  %5 = getelementptr inbounds nuw i8, ptr %0, i64 40
  %6 = getelementptr inbounds nuw i8, ptr %0, i64 128
  store i32 0, ptr %6, align 8, !tbaa !14
  %7 = getelementptr inbounds nuw i8, ptr %0, i64 132
  store i8 0, ptr %7, align 4, !tbaa !18
  %8 = getelementptr inbounds nuw i8, ptr %0, i64 136
  %9 = getelementptr inbounds nuw i8, ptr %0, i64 176
  store i64 0, ptr %9, align 8, !tbaa !19
  tail call void @llvm.memset.p0.i64(ptr noundef nonnull align 8 dereferenceable(85) %5, i8 0, i64 85, i1 false)
  tail call void @llvm.memset.p0.i64(ptr noundef nonnull align 8 dereferenceable(36) %8, i8 0, i64 36, i1 false)
  ret void
}

; Function Attrs: mustprogress nocallback nofree nounwind willreturn memory(argmem: write)
declare void @llvm.memset.p0.i64(ptr writeonly captures(none), i8, i64, i1 immarg) #2

; Function Attrs: mustprogress ssp uwtable(sync)
define void @stream_feed(ptr noundef captures(none) %0, ptr noundef readonly captures(none) %1, i32 noundef %2) local_unnamed_addr #3 {
  %4 = alloca %struct.State, align 8
  %5 = alloca %struct.State, align 8
  %6 = getelementptr inbounds nuw i8, ptr %0, i64 168
  %7 = load i32, ptr %6, align 8, !tbaa !20
  %8 = icmp eq i32 %7, 0
  %9 = icmp ne i32 %2, 0
  %10 = and i1 %8, %9
  br i1 %10, label %11, label %392

11:                                               ; preds = %3
  %12 = getelementptr inbounds nuw i8, ptr %0, i64 8
  %13 = getelementptr inbounds nuw i8, ptr %0, i64 16
  %14 = getelementptr inbounds nuw i8, ptr %0, i64 24
  %15 = getelementptr inbounds nuw i8, ptr %0, i64 28
  %16 = getelementptr inbounds nuw i8, ptr %0, i64 29
  %17 = getelementptr inbounds nuw i8, ptr %0, i64 30
  %18 = getelementptr inbounds nuw i8, ptr %0, i64 32
  %19 = getelementptr inbounds nuw i8, ptr %0, i64 40
  %20 = getelementptr inbounds nuw i8, ptr %5, i64 128
  %21 = getelementptr inbounds nuw i8, ptr %5, i64 136
  %22 = getelementptr inbounds nuw i8, ptr %5, i64 140
  %23 = getelementptr inbounds nuw i8, ptr %5, i64 48
  %24 = getelementptr inbounds nuw i8, ptr %5, i64 168
  %25 = getelementptr inbounds nuw i8, ptr %5, i64 176
  %26 = getelementptr inbounds nuw i8, ptr %5, i64 120
  %27 = getelementptr inbounds nuw i8, ptr %5, i64 56
  %28 = getelementptr inbounds nuw i8, ptr %5, i64 124
  %29 = getelementptr inbounds nuw i8, ptr %5, i64 148
  %30 = getelementptr inbounds nuw i8, ptr %5, i64 144
  %31 = getelementptr inbounds nuw i8, ptr %5, i64 152
  %32 = getelementptr inbounds nuw i8, ptr %5, i64 160
  %33 = getelementptr inbounds nuw i8, ptr %5, i64 132
  %34 = getelementptr inbounds nuw i8, ptr %0, i64 48
  %35 = zext i32 %2 to i64
  br label %36

36:                                               ; preds = %11, %387
  %37 = phi i64 [ 0, %11 ], [ %390, %387 ]
  %38 = load i64, ptr %0, align 8, !tbaa !21
  %39 = load i64, ptr %12, align 8, !tbaa !21
  %40 = load i64, ptr %13, align 8, !tbaa !21
  %41 = load i32, ptr %14, align 8, !tbaa !22
  %42 = load i8, ptr %15, align 4, !tbaa !23
  %43 = load i8, ptr %16, align 1, !tbaa !23
  %44 = load i16, ptr %17, align 2
  %45 = load i32, ptr %18, align 8, !tbaa !22
  %46 = load i64, ptr %19, align 8, !tbaa !21
  %47 = getelementptr inbounds nuw i8, ptr %1, i64 %37
  %48 = load i8, ptr %47, align 1, !tbaa !23
  %49 = icmp eq i32 %45, 0
  br i1 %49, label %50, label %93

50:                                               ; preds = %36
  %51 = icmp eq i64 %38, -1
  br i1 %51, label %93, label %52

52:                                               ; preds = %50
  %53 = icmp eq i32 %41, 0
  br i1 %53, label %54, label %75

54:                                               ; preds = %52
  %55 = icmp sgt i8 %48, -1
  br i1 %55, label %56, label %60

56:                                               ; preds = %54
  %57 = icmp eq i64 %39, -1
  br i1 %57, label %93, label %58

58:                                               ; preds = %56
  %59 = add nuw i64 %39, 1
  br label %86

60:                                               ; preds = %54
  %61 = add nsw i8 %48, 62
  %62 = icmp ult i8 %61, 30
  br i1 %62, label %86, label %63

63:                                               ; preds = %60
  %64 = and i8 %48, -16
  %65 = icmp eq i8 %64, -32
  br i1 %65, label %66, label %69

66:                                               ; preds = %63
  switch i8 %48, label %86 [
    i8 -32, label %67
    i8 -19, label %68
  ]

67:                                               ; preds = %66
  br label %86

68:                                               ; preds = %66
  br label %86

69:                                               ; preds = %63
  %70 = add nsw i8 %48, 16
  %71 = icmp ult i8 %70, 5
  br i1 %71, label %72, label %93

72:                                               ; preds = %69
  switch i8 %48, label %86 [
    i8 -16, label %73
    i8 -12, label %74
  ]

73:                                               ; preds = %72
  br label %86

74:                                               ; preds = %72
  br label %86

75:                                               ; preds = %52
  %76 = icmp ult i8 %48, %42
  %77 = icmp ugt i8 %48, %43
  %78 = select i1 %76, i1 true, i1 %77
  br i1 %78, label %93, label %79

79:                                               ; preds = %75
  %80 = add i32 %41, -1
  %81 = icmp eq i32 %80, 0
  br i1 %81, label %82, label %86

82:                                               ; preds = %79
  %83 = icmp eq i64 %39, -1
  br i1 %83, label %93, label %84

84:                                               ; preds = %82
  %85 = add nuw i64 %39, 1
  br label %86

86:                                               ; preds = %60, %84, %79, %74, %73, %72, %68, %67, %66, %58
  %87 = phi i8 [ %43, %58 ], [ -65, %66 ], [ -65, %67 ], [ -97, %68 ], [ -65, %72 ], [ -65, %73 ], [ -113, %74 ], [ -65, %84 ], [ -65, %79 ], [ -65, %60 ]
  %88 = phi i8 [ %42, %58 ], [ -128, %66 ], [ -96, %67 ], [ -128, %68 ], [ -128, %72 ], [ -112, %73 ], [ -128, %74 ], [ -128, %84 ], [ -128, %79 ], [ -128, %60 ]
  %89 = phi i32 [ 0, %58 ], [ 2, %66 ], [ 2, %67 ], [ 2, %68 ], [ 3, %72 ], [ 3, %73 ], [ 3, %74 ], [ 0, %84 ], [ %80, %79 ], [ 1, %60 ]
  %90 = phi i64 [ %38, %58 ], [ %38, %66 ], [ %38, %67 ], [ %38, %68 ], [ %38, %72 ], [ %38, %73 ], [ %38, %74 ], [ %40, %84 ], [ %40, %79 ], [ %38, %60 ]
  %91 = phi i64 [ %59, %58 ], [ %39, %66 ], [ %39, %67 ], [ %39, %68 ], [ %39, %72 ], [ %39, %73 ], [ %39, %74 ], [ %85, %84 ], [ %39, %79 ], [ %39, %60 ]
  %92 = add nuw i64 %38, 1
  br label %93

93:                                               ; preds = %82, %75, %69, %56, %50, %36, %86
  %94 = phi i64 [ %46, %86 ], [ %46, %36 ], [ -1, %50 ], [ %38, %56 ], [ %38, %69 ], [ %40, %75 ], [ %38, %82 ]
  %95 = phi i32 [ 0, %86 ], [ %45, %36 ], [ 2, %50 ], [ 2, %56 ], [ 1, %69 ], [ 1, %75 ], [ 2, %82 ]
  %96 = phi i8 [ %87, %86 ], [ %43, %36 ], [ %43, %50 ], [ %43, %56 ], [ -65, %69 ], [ %43, %75 ], [ -65, %82 ]
  %97 = phi i8 [ %88, %86 ], [ %42, %36 ], [ %42, %50 ], [ %42, %56 ], [ -128, %69 ], [ %42, %75 ], [ -128, %82 ]
  %98 = phi i32 [ %89, %86 ], [ %41, %36 ], [ %41, %50 ], [ 0, %56 ], [ 0, %69 ], [ %41, %75 ], [ 0, %82 ]
  %99 = phi i64 [ %90, %86 ], [ %40, %36 ], [ %40, %50 ], [ %38, %56 ], [ %38, %69 ], [ %40, %75 ], [ %40, %82 ]
  %100 = phi i64 [ %91, %86 ], [ %39, %36 ], [ %39, %50 ], [ -1, %56 ], [ %39, %69 ], [ %39, %75 ], [ -1, %82 ]
  %101 = phi i64 [ %92, %86 ], [ %38, %36 ], [ -1, %50 ], [ %38, %56 ], [ %38, %69 ], [ %38, %75 ], [ %38, %82 ]
  store i64 %101, ptr %0, align 8, !tbaa !21
  store i64 %100, ptr %12, align 8, !tbaa !21
  store i64 %99, ptr %13, align 8, !tbaa !21
  store i32 %98, ptr %14, align 8, !tbaa !22
  store i8 %97, ptr %15, align 4, !tbaa !23
  store i8 %96, ptr %16, align 1, !tbaa !23
  store i16 %44, ptr %17, align 2
  store i32 %95, ptr %18, align 8, !tbaa !22
  store i64 %94, ptr %19, align 8, !tbaa !21
  %102 = icmp eq i32 %95, 0
  br i1 %102, label %107, label %103

103:                                              ; preds = %93
  %104 = icmp eq i32 %95, 1
  %105 = select i1 %104, i32 5, i32 8
  store i32 %105, ptr %6, align 8, !tbaa !20
  %106 = getelementptr inbounds nuw i8, ptr %0, i64 176
  store i64 %94, ptr %106, align 8, !tbaa !19
  br label %392

107:                                              ; preds = %93
  call void @llvm.lifetime.start.p0(i64 184, ptr nonnull %4)
  call void @llvm.lifetime.start.p0(i64 184, ptr nonnull %5) #11
  call void @llvm.memcpy.p0.p0.i64(ptr noundef nonnull align 8 dereferenceable(184) %5, ptr noundef nonnull align 8 dereferenceable(184) %0, i64 184, i1 false), !tbaa.struct !24
  %108 = load i8, ptr %47, align 1, !tbaa !23
  %109 = load i32, ptr %20, align 8, !tbaa !14, !noalias !26
  switch i32 %109, label %246 [
    i32 1, label %110
    i32 2, label %142
    i32 4, label %147
    i32 5, label %152
    i32 3, label %157
    i32 6, label %157
    i32 20, label %199
  ]

110:                                              ; preds = %107
  %111 = icmp ult i8 %108, 32
  br i1 %111, label %112, label %114

112:                                              ; preds = %110
  %113 = load i64, ptr %23, align 8, !tbaa !29, !noalias !26
  store i32 1, ptr %24, align 8, !tbaa !20, !noalias !26
  store i64 %113, ptr %25, align 8, !tbaa !19, !noalias !26
  br label %384

114:                                              ; preds = %110
  switch i8 %108, label %384 [
    i8 34, label %115
    i8 92, label %140
  ]

115:                                              ; preds = %114
  store i32 0, ptr %20, align 8, !tbaa !14, !noalias !26
  %116 = load i8, ptr %33, align 4, !tbaa !18, !range !30, !noalias !26, !noundef !31
  %117 = trunc nuw i8 %116 to i1
  %118 = load i32, ptr %26, align 8, !tbaa !32, !noalias !26
  br i1 %117, label %119, label %126

119:                                              ; preds = %115
  %120 = add i32 %118, -1
  %121 = icmp ugt i32 %120, 63
  br i1 %121, label %122, label %123

122:                                              ; preds = %119
  tail call void @_ZNSt3__120__throw_out_of_rangeB9nqe210106EPKc(ptr noundef nonnull @.str) #12, !noalias !26
  unreachable

123:                                              ; preds = %119
  %124 = zext nneg i32 %120 to i64
  %125 = getelementptr inbounds nuw [64 x i8], ptr %27, i64 0, i64 %124
  store i8 5, ptr %125, align 1, !tbaa !23, !noalias !26
  br label %384

126:                                              ; preds = %115
  %127 = icmp eq i32 %118, 0
  br i1 %127, label %128, label %129

128:                                              ; preds = %126
  store i8 1, ptr %28, align 4, !tbaa !33, !noalias !26
  br label %384

129:                                              ; preds = %126
  %130 = add i32 %118, -1
  %131 = icmp ugt i32 %130, 63
  br i1 %131, label %132, label %133

132:                                              ; preds = %129
  tail call void @_ZNSt3__120__throw_out_of_rangeB9nqe210106EPKc(ptr noundef nonnull @.str) #12, !noalias !26
  unreachable

133:                                              ; preds = %129
  %134 = zext nneg i32 %130 to i64
  %135 = getelementptr inbounds nuw [64 x i8], ptr %27, i64 0, i64 %134
  %136 = load i8, ptr %135, align 1, !tbaa !23, !noalias !26
  %137 = and i8 %136, -3
  %138 = icmp eq i8 %137, 1
  %139 = select i1 %138, i8 2, i8 7
  store i8 %139, ptr %135, align 1, !tbaa !23, !noalias !26
  br label %384

140:                                              ; preds = %114
  store i32 2, ptr %20, align 8, !tbaa !14, !noalias !26
  %141 = load i64, ptr %23, align 8, !tbaa !29, !noalias !26
  store i64 %141, ptr %31, align 8, !tbaa !34, !noalias !26
  br label %384

142:                                              ; preds = %107
  switch i8 %108, label %145 [
    i8 116, label %143
    i8 114, label %143
    i8 110, label %143
    i8 102, label %143
    i8 98, label %143
    i8 92, label %143
    i8 47, label %143
    i8 34, label %143
    i8 117, label %144
  ]

143:                                              ; preds = %142, %142, %142, %142, %142, %142, %142, %142
  store i32 1, ptr %20, align 8, !tbaa !14, !noalias !26
  br label %384

144:                                              ; preds = %142
  store i32 3, ptr %20, align 8, !tbaa !14, !noalias !26
  store <2 x i32> zeroinitializer, ptr %30, align 8, !tbaa !22, !noalias !26
  br label %384

145:                                              ; preds = %142
  %146 = load i64, ptr %23, align 8, !tbaa !29, !noalias !26
  store i32 3, ptr %24, align 8, !tbaa !20, !noalias !26
  store i64 %146, ptr %25, align 8, !tbaa !19, !noalias !26
  br label %384

147:                                              ; preds = %107
  %148 = icmp eq i8 %108, 92
  br i1 %148, label %151, label %149

149:                                              ; preds = %147
  %150 = load i64, ptr %32, align 8, !tbaa !35, !noalias !26
  store i32 4, ptr %24, align 8, !tbaa !20, !noalias !26
  store i64 %150, ptr %25, align 8, !tbaa !19, !noalias !26
  br label %384

151:                                              ; preds = %147
  store i32 5, ptr %20, align 8, !tbaa !14, !noalias !26
  br label %384

152:                                              ; preds = %107
  %153 = icmp eq i8 %108, 117
  br i1 %153, label %156, label %154

154:                                              ; preds = %152
  %155 = load i64, ptr %32, align 8, !tbaa !35, !noalias !26
  store i32 4, ptr %24, align 8, !tbaa !20, !noalias !26
  store i64 %155, ptr %25, align 8, !tbaa !19, !noalias !26
  br label %384

156:                                              ; preds = %152
  store i32 6, ptr %20, align 8, !tbaa !14, !noalias !26
  store <2 x i32> zeroinitializer, ptr %30, align 8, !tbaa !22, !noalias !26
  br label %384

157:                                              ; preds = %107, %107
  %158 = zext i8 %108 to i32
  %159 = add i8 %108, -48
  %160 = icmp ult i8 %159, 10
  br i1 %160, label %161, label %163

161:                                              ; preds = %157
  %162 = add nsw i32 %158, -48
  br label %172

163:                                              ; preds = %157
  %164 = add i8 %108, -65
  %165 = icmp ult i8 %164, 6
  br i1 %165, label %166, label %168

166:                                              ; preds = %163
  %167 = add nsw i32 %158, -55
  br label %172

168:                                              ; preds = %163
  %169 = add i8 %108, -97
  %170 = icmp ult i8 %169, 6
  %171 = add nsw i32 %158, -87
  br i1 %170, label %172, label %175

172:                                              ; preds = %168, %166, %161
  %173 = phi i32 [ %162, %161 ], [ %167, %166 ], [ %171, %168 ]
  %174 = icmp eq i32 %173, 16
  br i1 %174, label %175, label %177

175:                                              ; preds = %172, %168
  %176 = load i64, ptr %23, align 8, !tbaa !29, !noalias !26
  store i32 3, ptr %24, align 8, !tbaa !20, !noalias !26
  store i64 %176, ptr %25, align 8, !tbaa !19, !noalias !26
  br label %384

177:                                              ; preds = %172
  %178 = load i32, ptr %29, align 4, !tbaa !36, !noalias !26
  %179 = shl i32 %178, 4
  %180 = add i32 %179, %173
  store i32 %180, ptr %29, align 4, !tbaa !36, !noalias !26
  %181 = load i32, ptr %30, align 8, !tbaa !37, !noalias !26
  %182 = add i32 %181, 1
  store i32 %182, ptr %30, align 8, !tbaa !37, !noalias !26
  %183 = icmp eq i32 %182, 4
  br i1 %183, label %184, label %384

184:                                              ; preds = %177
  %185 = icmp eq i32 %109, 6
  br i1 %185, label %186, label %192

186:                                              ; preds = %184
  %187 = add i32 %180, -57344
  %188 = icmp ult i32 %187, -1024
  br i1 %188, label %189, label %191

189:                                              ; preds = %186
  %190 = load i64, ptr %32, align 8, !tbaa !35, !noalias !26
  store i32 4, ptr %24, align 8, !tbaa !20, !noalias !26
  store i64 %190, ptr %25, align 8, !tbaa !19, !noalias !26
  br label %384

191:                                              ; preds = %186
  store i32 1, ptr %20, align 8, !tbaa !14, !noalias !26
  br label %384

192:                                              ; preds = %184
  %193 = and i32 %180, -1024
  switch i32 %193, label %198 [
    i32 55296, label %194
    i32 56320, label %196
  ]

194:                                              ; preds = %192
  store i32 4, ptr %20, align 8, !tbaa !14, !noalias !26
  %195 = load i64, ptr %31, align 8, !tbaa !34, !noalias !26
  store i64 %195, ptr %32, align 8, !tbaa !35, !noalias !26
  br label %384

196:                                              ; preds = %192
  %197 = load i64, ptr %31, align 8, !tbaa !34, !noalias !26
  store i32 4, ptr %24, align 8, !tbaa !20, !noalias !26
  store i64 %197, ptr %25, align 8, !tbaa !19, !noalias !26
  br label %384

198:                                              ; preds = %192
  store i32 1, ptr %20, align 8, !tbaa !14, !noalias !26
  br label %384

199:                                              ; preds = %107
  %200 = load i32, ptr %21, align 8, !tbaa !38, !noalias !26
  %201 = load i32, ptr %22, align 4, !noalias !26
  switch i32 %200, label %218 [
    i32 1, label %202
    i32 2, label %209
  ]

202:                                              ; preds = %199
  %203 = icmp eq i32 %201, 1
  %204 = select i1 %203, i8 114, i8 0
  %205 = icmp eq i32 %201, 2
  %206 = select i1 %205, i8 117, i8 %204
  %207 = icmp eq i32 %201, 3
  %208 = select i1 %207, i8 101, i8 %206
  br label %218

209:                                              ; preds = %199
  %210 = icmp eq i32 %201, 1
  %211 = select i1 %210, i8 97, i8 0
  %212 = icmp eq i32 %201, 2
  %213 = select i1 %212, i8 108, i8 %211
  %214 = icmp eq i32 %201, 3
  %215 = select i1 %214, i8 115, i8 %213
  %216 = icmp eq i32 %201, 4
  %217 = select i1 %216, i8 101, i8 %215
  br label %218

218:                                              ; preds = %209, %202, %199
  %219 = phi i8 [ %217, %209 ], [ %208, %202 ], [ 0, %199 ]
  %220 = phi i32 [ 5, %209 ], [ 4, %202 ], [ 4, %199 ]
  %221 = icmp eq i32 %200, 3
  %222 = icmp eq i32 %201, 1
  %223 = select i1 %222, i8 117, i8 108
  %224 = select i1 %221, i8 %223, i8 %219
  %225 = icmp eq i8 %108, %224
  br i1 %225, label %228, label %226

226:                                              ; preds = %218
  %227 = load i64, ptr %23, align 8, !tbaa !29, !noalias !26
  store i32 1, ptr %24, align 8, !tbaa !20, !noalias !26
  store i64 %227, ptr %25, align 8, !tbaa !19, !noalias !26
  br label %384

228:                                              ; preds = %218
  %229 = add i32 %201, 1
  store i32 %229, ptr %22, align 4, !tbaa !39, !noalias !26
  %230 = icmp eq i32 %229, %220
  br i1 %230, label %231, label %384

231:                                              ; preds = %228
  store i32 0, ptr %20, align 8, !tbaa !14, !noalias !26
  %232 = load i32, ptr %26, align 8, !tbaa !32, !noalias !26
  %233 = icmp eq i32 %232, 0
  br i1 %233, label %234, label %235

234:                                              ; preds = %231
  store i8 1, ptr %28, align 4, !tbaa !33, !noalias !26
  br label %384

235:                                              ; preds = %231
  %236 = add i32 %232, -1
  %237 = icmp ugt i32 %236, 63
  br i1 %237, label %238, label %239

238:                                              ; preds = %235
  tail call void @_ZNSt3__120__throw_out_of_rangeB9nqe210106EPKc(ptr noundef nonnull @.str) #12, !noalias !26
  unreachable

239:                                              ; preds = %235
  %240 = zext nneg i32 %236 to i64
  %241 = getelementptr inbounds nuw [64 x i8], ptr %27, i64 0, i64 %240
  %242 = load i8, ptr %241, align 1, !tbaa !23, !noalias !26
  %243 = and i8 %242, -3
  %244 = icmp eq i8 %243, 1
  %245 = select i1 %244, i8 2, i8 7
  store i8 %245, ptr %241, align 1, !tbaa !23, !noalias !26
  br label %384

246:                                              ; preds = %107
  %247 = add i32 %109, -10
  %248 = icmp ult i32 %247, 8
  br i1 %248, label %249, label %291

249:                                              ; preds = %246
  %250 = add i8 %108, -48
  %251 = icmp ult i8 %250, 10
  br i1 %251, label %252, label %264

252:                                              ; preds = %249
  switch i32 %109, label %259 [
    i32 11, label %253
    i32 10, label %255
    i32 13, label %258
  ]

253:                                              ; preds = %252
  %254 = load i64, ptr %23, align 8, !tbaa !29, !noalias !26
  store i32 2, ptr %24, align 8, !tbaa !20, !noalias !26
  store i64 %254, ptr %25, align 8, !tbaa !19, !noalias !26
  br label %384

255:                                              ; preds = %252
  %256 = icmp eq i8 %108, 48
  %257 = select i1 %256, i32 11, i32 12
  store i32 %257, ptr %20, align 8, !tbaa !14, !noalias !26
  br label %259

258:                                              ; preds = %252
  store i32 14, ptr %20, align 8, !tbaa !14, !noalias !26
  br label %384

259:                                              ; preds = %255, %252
  %260 = phi i32 [ %257, %255 ], [ %109, %252 ]
  %261 = add nsw i32 %260, -15
  %262 = icmp ult i32 %261, 2
  br i1 %262, label %263, label %384

263:                                              ; preds = %259
  store i32 17, ptr %20, align 8, !tbaa !14, !noalias !26
  br label %384

264:                                              ; preds = %249
  %265 = icmp eq i32 %109, 11
  br i1 %265, label %270, label %266

266:                                              ; preds = %264
  %267 = icmp eq i32 %109, 12
  %268 = icmp eq i8 %108, 46
  %269 = and i1 %268, %267
  br i1 %269, label %272, label %273

270:                                              ; preds = %264
  %271 = icmp eq i8 %108, 46
  br i1 %271, label %272, label %277

272:                                              ; preds = %270, %266
  store i32 13, ptr %20, align 8, !tbaa !14, !noalias !26
  br label %384

273:                                              ; preds = %266
  switch i32 %109, label %287 [
    i32 11, label %274
    i32 12, label %274
    i32 14, label %274
    i32 15, label %281
    i32 10, label %285
    i32 13, label %285
    i32 16, label %285
  ]

274:                                              ; preds = %273, %273, %273
  %275 = and i8 %108, -33
  %276 = icmp eq i8 %275, 69
  br i1 %276, label %280, label %283

277:                                              ; preds = %270
  %278 = and i8 %108, -33
  %279 = icmp eq i8 %278, 69
  br i1 %279, label %280, label %287

280:                                              ; preds = %277, %274
  store i32 15, ptr %20, align 8, !tbaa !14, !noalias !26
  br label %384

281:                                              ; preds = %273
  switch i8 %108, label %285 [
    i8 45, label %282
    i8 43, label %282
  ]

282:                                              ; preds = %281, %281
  store i32 16, ptr %20, align 8, !tbaa !14, !noalias !26
  br label %384

283:                                              ; preds = %274
  %284 = icmp eq i32 %109, 13
  br i1 %284, label %285, label %287

285:                                              ; preds = %283, %281, %273, %273, %273
  %286 = load i64, ptr %23, align 8, !tbaa !29, !noalias !26
  store i32 2, ptr %24, align 8, !tbaa !20, !noalias !26
  store i64 %286, ptr %25, align 8, !tbaa !19, !noalias !26
  br label %384

287:                                              ; preds = %283, %277, %273
  switch i8 %108, label %288 [
    i8 32, label %290
    i8 10, label %290
    i8 9, label %290
    i8 13, label %290
    i8 125, label %290
    i8 93, label %290
    i8 44, label %290
  ]

288:                                              ; preds = %287
  %289 = load i64, ptr %23, align 8, !tbaa !29, !noalias !26
  store i32 2, ptr %24, align 8, !tbaa !20, !noalias !26
  store i64 %289, ptr %25, align 8, !tbaa !19, !noalias !26
  br label %384

290:                                              ; preds = %287, %287, %287, %287, %287, %287, %287
  store i32 0, ptr %20, align 8, !tbaa !14, !noalias !26
  call fastcc void @_ZL4doneR5State(ptr noundef nonnull align 8 dereferenceable(184) %5), !noalias !26
  br label %291

291:                                              ; preds = %290, %246
  switch i8 %108, label %292 [
    i8 32, label %384
    i8 10, label %384
    i8 9, label %384
    i8 13, label %384
  ]

292:                                              ; preds = %291
  %293 = load i32, ptr %26, align 8, !tbaa !32, !noalias !26
  %294 = icmp eq i32 %293, 0
  br i1 %294, label %309, label %295

295:                                              ; preds = %292
  %296 = add i32 %293, -1
  %297 = icmp ugt i32 %296, 63
  br i1 %297, label %298, label %299

298:                                              ; preds = %295
  tail call void @_ZNSt3__120__throw_out_of_rangeB9nqe210106EPKc(ptr noundef nonnull @.str) #12, !noalias !26
  unreachable

299:                                              ; preds = %295
  %300 = zext nneg i32 %296 to i64
  %301 = getelementptr inbounds nuw [64 x i8], ptr %27, i64 0, i64 %300
  %302 = load i8, ptr %301, align 1, !tbaa !23, !noalias !26
  %303 = zext i8 %302 to i32
  %304 = icmp eq i8 %108, 93
  %305 = add i8 %302, -1
  %306 = icmp ult i8 %305, 2
  %307 = select i1 %304, i1 %306, i1 false
  br i1 %307, label %308, label %309

308:                                              ; preds = %299
  store i32 %296, ptr %26, align 8, !tbaa !32, !noalias !26
  br label %384

309:                                              ; preds = %299, %292
  %310 = phi i32 [ %303, %299 ], [ 0, %292 ]
  %311 = icmp eq i8 %108, 125
  %312 = trunc nuw i32 %310 to i8
  br i1 %311, label %313, label %316

313:                                              ; preds = %309
  switch i8 %312, label %316 [
    i8 7, label %314
    i8 4, label %314
  ]

314:                                              ; preds = %313, %313
  %315 = add nsw i32 %293, -1
  store i32 %315, ptr %26, align 8, !tbaa !32, !noalias !26
  br label %384

316:                                              ; preds = %313, %309
  %317 = icmp eq i32 %310, 2
  switch i8 %312, label %346 [
    i8 7, label %318
    i8 2, label %318
    i8 5, label %330
    i8 8, label %341
    i8 4, label %341
  ]

318:                                              ; preds = %316, %316
  %319 = icmp eq i8 %108, 44
  br i1 %319, label %322, label %320

320:                                              ; preds = %318
  %321 = load i64, ptr %23, align 8, !tbaa !29, !noalias !26
  store i32 1, ptr %24, align 8, !tbaa !20, !noalias !26
  store i64 %321, ptr %25, align 8, !tbaa !19, !noalias !26
  br label %384

322:                                              ; preds = %318
  %323 = add nsw i32 %293, -1
  %324 = icmp ugt i32 %323, 63
  br i1 %324, label %325, label %326

325:                                              ; preds = %322
  tail call void @_ZNSt3__120__throw_out_of_rangeB9nqe210106EPKc(ptr noundef nonnull @.str) #12, !noalias !26
  unreachable

326:                                              ; preds = %322
  %327 = zext nneg i32 %323 to i64
  %328 = select i1 %317, i8 3, i8 8
  %329 = getelementptr inbounds nuw [64 x i8], ptr %27, i64 0, i64 %327
  store i8 %328, ptr %329, align 1, !tbaa !23, !noalias !26
  br label %384

330:                                              ; preds = %316
  %331 = icmp eq i8 %108, 58
  br i1 %331, label %334, label %332

332:                                              ; preds = %330
  %333 = load i64, ptr %23, align 8, !tbaa !29, !noalias !26
  store i32 1, ptr %24, align 8, !tbaa !20, !noalias !26
  store i64 %333, ptr %25, align 8, !tbaa !19, !noalias !26
  br label %384

334:                                              ; preds = %330
  %335 = add nsw i32 %293, -1
  %336 = icmp ugt i32 %335, 63
  br i1 %336, label %337, label %338

337:                                              ; preds = %334
  tail call void @_ZNSt3__120__throw_out_of_rangeB9nqe210106EPKc(ptr noundef nonnull @.str) #12, !noalias !26
  unreachable

338:                                              ; preds = %334
  %339 = zext nneg i32 %335 to i64
  %340 = getelementptr inbounds nuw [64 x i8], ptr %27, i64 0, i64 %339
  store i8 6, ptr %340, align 1, !tbaa !23, !noalias !26
  br label %384

341:                                              ; preds = %316, %316
  %342 = icmp eq i8 %108, 34
  br i1 %342, label %345, label %343

343:                                              ; preds = %341
  %344 = load i64, ptr %23, align 8, !tbaa !29, !noalias !26
  store i32 1, ptr %24, align 8, !tbaa !20, !noalias !26
  store i64 %344, ptr %25, align 8, !tbaa !19, !noalias !26
  br label %384

345:                                              ; preds = %341
  store i8 1, ptr %33, align 4, !tbaa !18, !noalias !26
  store i32 1, ptr %20, align 8, !tbaa !14, !noalias !26
  br label %384

346:                                              ; preds = %316
  %347 = load i8, ptr %28, align 4, !range !30, !noalias !26
  %348 = trunc nuw i8 %347 to i1
  %349 = select i1 %294, i1 %348, i1 false
  br i1 %349, label %350, label %352

350:                                              ; preds = %346
  %351 = load i64, ptr %23, align 8, !tbaa !29, !noalias !26
  store i32 1, ptr %24, align 8, !tbaa !20, !noalias !26
  store i64 %351, ptr %25, align 8, !tbaa !19, !noalias !26
  br label %384

352:                                              ; preds = %346
  %353 = icmp eq i8 %108, 91
  switch i8 %108, label %370 [
    i8 123, label %354
    i8 91, label %354
    i8 34, label %368
    i8 45, label %369
  ]

354:                                              ; preds = %352, %352
  %355 = icmp eq i32 %293, 64
  br i1 %355, label %356, label %358

356:                                              ; preds = %354
  %357 = load i64, ptr %23, align 8, !tbaa !29, !noalias !26
  store i32 7, ptr %24, align 8, !tbaa !20, !noalias !26
  store i64 %357, ptr %25, align 8, !tbaa !19, !noalias !26
  br label %384

358:                                              ; preds = %354
  call fastcc void @_ZL4doneR5State(ptr noundef nonnull align 8 dereferenceable(184) %5), !noalias !26
  %359 = load i32, ptr %26, align 8, !tbaa !32, !noalias !26
  %360 = icmp ugt i32 %359, 63
  br i1 %360, label %361, label %362

361:                                              ; preds = %358
  tail call void @_ZNSt3__120__throw_out_of_rangeB9nqe210106EPKc(ptr noundef nonnull @.str) #12, !noalias !26
  unreachable

362:                                              ; preds = %358
  %363 = zext nneg i32 %359 to i64
  %364 = select i1 %353, i8 1, i8 4
  %365 = getelementptr inbounds nuw [64 x i8], ptr %27, i64 0, i64 %363
  store i8 %364, ptr %365, align 1, !tbaa !23, !noalias !26
  %366 = load i32, ptr %26, align 8, !tbaa !32, !noalias !26
  %367 = add i32 %366, 1
  store i32 %367, ptr %26, align 8, !tbaa !32, !noalias !26
  br label %384

368:                                              ; preds = %352
  store i8 0, ptr %33, align 4, !tbaa !18, !noalias !26
  store i32 1, ptr %20, align 8, !tbaa !14, !noalias !26
  br label %384

369:                                              ; preds = %352
  store i32 10, ptr %20, align 8, !tbaa !14, !noalias !26
  br label %384

370:                                              ; preds = %352
  %371 = add i8 %108, -48
  %372 = icmp ult i8 %371, 10
  br i1 %372, label %373, label %376

373:                                              ; preds = %370
  %374 = icmp eq i8 %108, 48
  %375 = select i1 %374, i32 11, i32 12
  store i32 %375, ptr %20, align 8, !tbaa !14, !noalias !26
  br label %384

376:                                              ; preds = %370
  switch i8 %108, label %382 [
    i8 116, label %377
    i8 110, label %377
    i8 102, label %377
  ]

377:                                              ; preds = %376, %376, %376
  %378 = icmp eq i8 %108, 102
  %379 = icmp eq i8 %108, 116
  store i32 20, ptr %20, align 8, !tbaa !14, !noalias !26
  store i32 1, ptr %22, align 4, !tbaa !39, !noalias !26
  %380 = select i1 %378, i32 2, i32 3
  %381 = select i1 %379, i32 1, i32 %380
  store i32 %381, ptr %21, align 8, !tbaa !38, !noalias !26
  br label %384

382:                                              ; preds = %376
  %383 = load i64, ptr %23, align 8, !tbaa !29, !noalias !26
  store i32 1, ptr %24, align 8, !tbaa !20, !noalias !26
  store i64 %383, ptr %25, align 8, !tbaa !19, !noalias !26
  br label %384

384:                                              ; preds = %133, %128, %112, %114, %123, %140, %143, %144, %145, %149, %151, %154, %156, %175, %177, %189, %191, %194, %196, %198, %226, %228, %234, %239, %253, %258, %259, %263, %272, %280, %282, %285, %288, %291, %291, %291, %291, %308, %314, %320, %326, %332, %338, %343, %345, %350, %356, %362, %368, %369, %373, %377, %382
  call void @llvm.memcpy.p0.p0.i64(ptr noundef nonnull align 8 dereferenceable(184) %4, ptr noundef nonnull align 8 dereferenceable(184) %5, i64 184, i1 false), !tbaa.struct !24
  call void @llvm.lifetime.end.p0(i64 184, ptr nonnull %5) #11
  call void @llvm.memcpy.p0.p0.i64(ptr noundef nonnull align 8 dereferenceable(184) %0, ptr noundef nonnull align 8 dereferenceable(184) %4, i64 184, i1 false), !tbaa.struct !24
  call void @llvm.lifetime.end.p0(i64 184, ptr nonnull %4)
  %385 = load i32, ptr %6, align 8, !tbaa !20
  %386 = icmp eq i32 %385, 0
  br i1 %386, label %387, label %392

387:                                              ; preds = %384
  %388 = load i64, ptr %34, align 8, !tbaa !29
  %389 = add i64 %388, 1
  store i64 %389, ptr %34, align 8, !tbaa !29
  %390 = add nuw nsw i64 %37, 1
  %391 = icmp eq i64 %390, %35
  br i1 %391, label %392, label %36, !llvm.loop !40

392:                                              ; preds = %384, %387, %103, %3
  ret void
}

; Function Attrs: mustprogress nocallback nofree nosync nounwind willreturn memory(argmem: readwrite)
declare void @llvm.lifetime.start.p0(i64 immarg, ptr captures(none)) #4

; Function Attrs: mustprogress nocallback nofree nounwind willreturn memory(argmem: readwrite)
declare void @llvm.memcpy.p0.p0.i64(ptr noalias writeonly captures(none), ptr noalias readonly captures(none), i64, i1 immarg) #5

; Function Attrs: mustprogress nocallback nofree nosync nounwind willreturn memory(argmem: readwrite)
declare void @llvm.lifetime.end.p0(i64 immarg, ptr captures(none)) #4

; Function Attrs: mustprogress nofree norecurse nosync nounwind ssp willreturn memory(argmem: read) uwtable(sync)
define i32 @stream_pending(ptr noundef readonly captures(none) %0) local_unnamed_addr #6 {
  %2 = getelementptr inbounds nuw i8, ptr %0, i64 168
  %3 = load i32, ptr %2, align 8, !tbaa !20
  ret i32 %3
}

; Function Attrs: mustprogress ssp uwtable(sync)
define i32 @stream_status(ptr noundef readonly captures(none) %0) local_unnamed_addr #3 {
  %2 = alloca %struct.State, align 8
  %3 = alloca %struct.State, align 8
  call void @llvm.lifetime.start.p0(i64 184, ptr nonnull %2) #11
  call void @llvm.lifetime.start.p0(i64 184, ptr nonnull %3) #11
  call void @llvm.memcpy.p0.p0.i64(ptr noundef nonnull align 8 dereferenceable(184) %3, ptr noundef nonnull align 8 dereferenceable(184) %0, i64 184, i1 false), !tbaa.struct !24
  call fastcc void @_ZL6finish5State(ptr dead_on_unwind writable sret(%struct.State) align 8 %2, ptr noundef %3)
  call void @llvm.lifetime.end.p0(i64 184, ptr nonnull %3) #11
  %4 = getelementptr inbounds nuw i8, ptr %2, i64 168
  %5 = load i32, ptr %4, align 8, !tbaa !20
  call void @llvm.lifetime.end.p0(i64 184, ptr nonnull %2) #11
  ret i32 %5
}

; Function Attrs: mustprogress ssp uwtable(sync)
define internal fastcc void @_ZL6finish5State(ptr dead_on_unwind noalias nonnull writable writeonly sret(%struct.State) align 8 captures(none) %0, ptr noundef nonnull captures(none) %1) unnamed_addr #3 {
  %3 = getelementptr inbounds nuw i8, ptr %1, i64 168
  %4 = load i32, ptr %3, align 8, !tbaa !20
  %5 = icmp eq i32 %4, 0
  br i1 %5, label %6, label %53

6:                                                ; preds = %2
  %7 = getelementptr inbounds nuw i8, ptr %1, i64 32
  %8 = load i32, ptr %7, align 8, !tbaa !42
  %9 = icmp eq i32 %8, 0
  br i1 %9, label %10, label %47

10:                                               ; preds = %6
  %11 = getelementptr inbounds nuw i8, ptr %1, i64 24
  %12 = load i32, ptr %11, align 8, !tbaa !43
  %13 = icmp eq i32 %12, 0
  br i1 %13, label %14, label %47

14:                                               ; preds = %10
  %15 = getelementptr inbounds nuw i8, ptr %1, i64 128
  %16 = load i32, ptr %15, align 8, !tbaa !14
  switch i32 %16, label %36 [
    i32 11, label %17
    i32 12, label %17
    i32 14, label %17
    i32 17, label %17
  ]

17:                                               ; preds = %14, %14, %14, %14
  store i32 0, ptr %15, align 8, !tbaa !14
  %18 = getelementptr inbounds nuw i8, ptr %1, i64 120
  %19 = load i32, ptr %18, align 8, !tbaa !32
  %20 = icmp eq i32 %19, 0
  br i1 %20, label %21, label %23

21:                                               ; preds = %17
  %22 = getelementptr inbounds nuw i8, ptr %1, i64 124
  store i8 1, ptr %22, align 4, !tbaa !33
  br label %38

23:                                               ; preds = %17
  %24 = add i32 %19, -1
  %25 = icmp ugt i32 %24, 63
  br i1 %25, label %26, label %27

26:                                               ; preds = %23
  tail call void @_ZNSt3__120__throw_out_of_rangeB9nqe210106EPKc(ptr noundef nonnull @.str) #12
  unreachable

27:                                               ; preds = %23
  %28 = zext nneg i32 %24 to i64
  %29 = getelementptr inbounds nuw i8, ptr %1, i64 56
  %30 = getelementptr inbounds nuw [64 x i8], ptr %29, i64 0, i64 %28
  %31 = load i8, ptr %30, align 1, !tbaa !23
  %32 = and i8 %31, -3
  %33 = icmp eq i8 %32, 1
  %34 = select i1 %33, i8 2, i8 7
  store i8 %34, ptr %30, align 1, !tbaa !23
  %35 = load i32, ptr %15, align 8, !tbaa !14
  br label %36

36:                                               ; preds = %27, %14
  %37 = phi i32 [ %16, %14 ], [ %35, %27 ]
  switch i32 %37, label %46 [
    i32 4, label %47
    i32 5, label %47
    i32 6, label %47
    i32 0, label %38
  ]

38:                                               ; preds = %21, %36
  %39 = getelementptr inbounds nuw i8, ptr %1, i64 120
  %40 = load i32, ptr %39, align 8, !tbaa !32
  %41 = icmp eq i32 %40, 0
  br i1 %41, label %42, label %46

42:                                               ; preds = %38
  %43 = getelementptr inbounds nuw i8, ptr %1, i64 124
  %44 = load i8, ptr %43, align 4, !tbaa !33, !range !30, !noundef !31
  %45 = trunc nuw i8 %44 to i1
  br i1 %45, label %53, label %46

46:                                               ; preds = %36, %42, %38
  br label %47

47:                                               ; preds = %36, %36, %36, %6, %10, %46
  %48 = phi i64 [ 48, %46 ], [ 16, %10 ], [ 40, %6 ], [ 160, %36 ], [ 160, %36 ], [ 160, %36 ]
  %49 = phi i32 [ 6, %46 ], [ 5, %10 ], [ 5, %6 ], [ 4, %36 ], [ 4, %36 ], [ 4, %36 ]
  %50 = getelementptr inbounds nuw i8, ptr %1, i64 %48
  %51 = load i64, ptr %50, align 8, !tbaa !21
  store i32 %49, ptr %3, align 8, !tbaa !20
  %52 = getelementptr inbounds nuw i8, ptr %1, i64 176
  store i64 %51, ptr %52, align 8, !tbaa !19
  br label %53

53:                                               ; preds = %47, %42, %2
  tail call void @llvm.memcpy.p0.p0.i64(ptr noundef nonnull align 8 dereferenceable(184) %0, ptr noundef nonnull align 8 dereferenceable(184) %1, i64 184, i1 false)
  ret void
}

; Function Attrs: mustprogress ssp uwtable(sync)
define i64 @stream_value(ptr noundef readonly captures(none) %0) local_unnamed_addr #3 {
  %2 = alloca %struct.State, align 8
  %3 = alloca %struct.State, align 8
  call void @llvm.lifetime.start.p0(i64 184, ptr nonnull %2) #11
  call void @llvm.lifetime.start.p0(i64 184, ptr nonnull %3) #11
  call void @llvm.memcpy.p0.p0.i64(ptr noundef nonnull align 8 dereferenceable(184) %3, ptr noundef nonnull align 8 dereferenceable(184) %0, i64 184, i1 false), !tbaa.struct !24
  call fastcc void @_ZL6finish5State(ptr dead_on_unwind writable sret(%struct.State) align 8 %2, ptr noundef %3)
  call void @llvm.lifetime.end.p0(i64 184, ptr nonnull %3) #11
  %4 = getelementptr inbounds nuw i8, ptr %2, i64 168
  %5 = load i32, ptr %4, align 8, !tbaa !20
  %6 = icmp eq i32 %5, 0
  %7 = getelementptr inbounds nuw i8, ptr %2, i64 176
  %8 = load i64, ptr %7, align 8
  %9 = getelementptr inbounds nuw i8, ptr %2, i64 48
  %10 = load i64, ptr %9, align 8
  %11 = select i1 %6, i64 %10, i64 %8
  call void @llvm.lifetime.end.p0(i64 184, ptr nonnull %2) #11
  ret i64 %11
}

; Function Attrs: mustprogress ssp uwtable(sync)
define internal fastcc void @_ZL4doneR5State(ptr noundef nonnull align 8 captures(none) dereferenceable(184) %0) unnamed_addr #3 {
  %2 = getelementptr inbounds nuw i8, ptr %0, i64 120
  %3 = load i32, ptr %2, align 8, !tbaa !32
  %4 = icmp eq i32 %3, 0
  br i1 %4, label %5, label %7

5:                                                ; preds = %1
  %6 = getelementptr inbounds nuw i8, ptr %0, i64 124
  store i8 1, ptr %6, align 4, !tbaa !33
  br label %19

7:                                                ; preds = %1
  %8 = add i32 %3, -1
  %9 = icmp ugt i32 %8, 63
  br i1 %9, label %10, label %11

10:                                               ; preds = %7
  tail call void @_ZNSt3__120__throw_out_of_rangeB9nqe210106EPKc(ptr noundef nonnull @.str) #12
  unreachable

11:                                               ; preds = %7
  %12 = zext nneg i32 %8 to i64
  %13 = getelementptr inbounds nuw i8, ptr %0, i64 56
  %14 = getelementptr inbounds nuw [64 x i8], ptr %13, i64 0, i64 %12
  %15 = load i8, ptr %14, align 1, !tbaa !23
  %16 = and i8 %15, -3
  %17 = icmp eq i8 %16, 1
  %18 = select i1 %17, i8 2, i8 7
  store i8 %18, ptr %14, align 1, !tbaa !23
  br label %19

19:                                               ; preds = %11, %5
  ret void
}

; Function Attrs: inlinehint mustprogress noreturn ssp uwtable(sync)
define linkonce_odr hidden void @_ZNSt3__120__throw_out_of_rangeB9nqe210106EPKc(ptr noundef %0) local_unnamed_addr #7 personality ptr @__gxx_personality_v0 {
  %2 = tail call ptr @__cxa_allocate_exception(i64 16) #11
  %3 = invoke ptr @_ZNSt12out_of_rangeC1B9nqe210106EPKc(ptr noundef %2, ptr noundef %0)
          to label %4 unwind label %5

4:                                                ; preds = %1
  tail call void @__cxa_throw(ptr %2, ptr nonnull @_ZTISt12out_of_range, ptr nonnull @_ZNSt12out_of_rangeD1Ev) #12
  unreachable

5:                                                ; preds = %1
  %6 = landingpad { ptr, i32 }
          cleanup
  tail call void @__cxa_free_exception(ptr %2) #11
  resume { ptr, i32 } %6
}

declare ptr @__cxa_allocate_exception(i64) local_unnamed_addr

; Function Attrs: mustprogress ssp uwtable(sync)
define linkonce_odr hidden ptr @_ZNSt12out_of_rangeC1B9nqe210106EPKc(ptr noundef returned %0, ptr noundef %1) unnamed_addr #3 {
  %3 = tail call ptr @_ZNSt11logic_errorC2EPKc(ptr noundef %0, ptr noundef %1)
  store ptr getelementptr inbounds nuw inrange(-16, 24) (i8, ptr @_ZTVSt12out_of_range, i64 16), ptr %0, align 8, !tbaa !44
  ret ptr %0
}

declare i32 @__gxx_personality_v0(...)

declare void @__cxa_free_exception(ptr) local_unnamed_addr

; Function Attrs: nounwind
declare ptr @_ZNSt12out_of_rangeD1Ev(ptr noundef returned) unnamed_addr #8

; Function Attrs: cold noreturn
declare void @__cxa_throw(ptr, ptr, ptr) local_unnamed_addr #9

declare ptr @_ZNSt11logic_errorC2EPKc(ptr noundef returned, ptr noundef) unnamed_addr #10

attributes #0 = { mustprogress nofree norecurse nosync nounwind ssp willreturn memory(none) uwtable(sync) "frame-pointer"="non-leaf" "no-trapping-math"="true" "probe-stack"="__chkstk_darwin" "stack-protector-buffer-size"="8" "target-cpu"="generic" "target-features"="+ete,+fp-armv8,+neon,+trbe,+v8a" }
attributes #1 = { mustprogress nofree norecurse nosync nounwind ssp willreturn memory(argmem: write) uwtable(sync) "frame-pointer"="non-leaf" "no-trapping-math"="true" "probe-stack"="__chkstk_darwin" "stack-protector-buffer-size"="8" "target-cpu"="generic" "target-features"="+ete,+fp-armv8,+neon,+trbe,+v8a" }
attributes #2 = { mustprogress nocallback nofree nounwind willreturn memory(argmem: write) }
attributes #3 = { mustprogress ssp uwtable(sync) "frame-pointer"="non-leaf" "no-trapping-math"="true" "probe-stack"="__chkstk_darwin" "stack-protector-buffer-size"="8" "target-cpu"="generic" "target-features"="+ete,+fp-armv8,+neon,+trbe,+v8a" }
attributes #4 = { mustprogress nocallback nofree nosync nounwind willreturn memory(argmem: readwrite) }
attributes #5 = { mustprogress nocallback nofree nounwind willreturn memory(argmem: readwrite) }
attributes #6 = { mustprogress nofree norecurse nosync nounwind ssp willreturn memory(argmem: read) uwtable(sync) "frame-pointer"="non-leaf" "no-trapping-math"="true" "probe-stack"="__chkstk_darwin" "stack-protector-buffer-size"="8" "target-cpu"="generic" "target-features"="+ete,+fp-armv8,+neon,+trbe,+v8a" }
attributes #7 = { inlinehint mustprogress noreturn ssp uwtable(sync) "frame-pointer"="non-leaf" "no-trapping-math"="true" "probe-stack"="__chkstk_darwin" "stack-protector-buffer-size"="8" "target-cpu"="generic" "target-features"="+ete,+fp-armv8,+neon,+trbe,+v8a" }
attributes #8 = { nounwind "frame-pointer"="non-leaf" "no-trapping-math"="true" "probe-stack"="__chkstk_darwin" "stack-protector-buffer-size"="8" "target-cpu"="generic" "target-features"="+ete,+fp-armv8,+neon,+trbe,+v8a" }
attributes #9 = { cold noreturn }
attributes #10 = { "frame-pointer"="non-leaf" "no-trapping-math"="true" "probe-stack"="__chkstk_darwin" "stack-protector-buffer-size"="8" "target-cpu"="generic" "target-features"="+ete,+fp-armv8,+neon,+trbe,+v8a" }
attributes #11 = { nounwind }
attributes #12 = { noreturn }

!llvm.module.flags = !{!0, !1, !2, !3, !4}
!llvm.ident = !{!5}

!0 = !{i32 2, !"SDK Version", [2 x i32] [i32 26, i32 5]}
!1 = !{i32 1, !"wchar_size", i32 4}
!2 = !{i32 8, !"PIC Level", i32 2}
!3 = !{i32 7, !"uwtable", i32 1}
!4 = !{i32 7, !"frame-pointer", i32 1}
!5 = !{!"Apple clang version 21.0.0 (clang-2100.1.1.101)"}
!6 = !{!7, !9, i64 28}
!7 = !{!"_ZTS8Encoding", !8, i64 0, !8, i64 8, !8, i64 16, !11, i64 24, !9, i64 28, !9, i64 29, !11, i64 32, !8, i64 40}
!8 = !{!"long long", !9, i64 0}
!9 = !{!"omnipotent char", !10, i64 0}
!10 = !{!"Simple C++ TBAA"}
!11 = !{!"int", !9, i64 0}
!12 = !{!7, !9, i64 29}
!13 = !{!7, !11, i64 32}
!14 = !{!15, !11, i64 128}
!15 = !{!"_ZTS5State", !7, i64 0, !8, i64 48, !16, i64 56, !11, i64 120, !17, i64 124, !11, i64 128, !17, i64 132, !11, i64 136, !11, i64 140, !11, i64 144, !11, i64 148, !8, i64 152, !8, i64 160, !11, i64 168, !8, i64 176}
!16 = !{!"_ZTSNSt3__15arrayIhLm64EEE", !9, i64 0}
!17 = !{!"bool", !9, i64 0}
!18 = !{!15, !17, i64 132}
!19 = !{!15, !8, i64 176}
!20 = !{!15, !11, i64 168}
!21 = !{!8, !8, i64 0}
!22 = !{!11, !11, i64 0}
!23 = !{!9, !9, i64 0}
!24 = !{i64 0, i64 8, !21, i64 8, i64 8, !21, i64 16, i64 8, !21, i64 24, i64 4, !22, i64 28, i64 1, !23, i64 29, i64 1, !23, i64 32, i64 4, !22, i64 40, i64 8, !21, i64 48, i64 8, !21, i64 56, i64 64, !23, i64 120, i64 4, !22, i64 124, i64 1, !25, i64 128, i64 4, !22, i64 132, i64 1, !25, i64 136, i64 4, !22, i64 140, i64 4, !22, i64 144, i64 4, !22, i64 148, i64 4, !22, i64 152, i64 8, !21, i64 160, i64 8, !21, i64 168, i64 4, !22, i64 176, i64 8, !21}
!25 = !{!17, !17, i64 0}
!26 = !{!27}
!27 = distinct !{!27, !28, !"_ZL10step_value5Stateh: argument 0"}
!28 = distinct !{!28, !"_ZL10step_value5Stateh"}
!29 = !{!15, !8, i64 48}
!30 = !{i8 0, i8 2}
!31 = !{}
!32 = !{!15, !11, i64 120}
!33 = !{!15, !17, i64 124}
!34 = !{!15, !8, i64 152}
!35 = !{!15, !8, i64 160}
!36 = !{!15, !11, i64 148}
!37 = !{!15, !11, i64 144}
!38 = !{!15, !11, i64 136}
!39 = !{!15, !11, i64 140}
!40 = distinct !{!40, !41}
!41 = !{!"llvm.loop.mustprogress"}
!42 = !{!15, !11, i64 32}
!43 = !{!15, !11, i64 24}
!44 = !{!45, !45, i64 0}
!45 = !{!"vtable pointer", !10, i64 0}
