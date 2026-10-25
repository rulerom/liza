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
define void @stream_feed(ptr noundef %0, ptr noundef readonly captures(none) %1, i32 noundef %2) local_unnamed_addr #3 {
  %4 = getelementptr inbounds nuw i8, ptr %0, i64 168
  %5 = load i32, ptr %4, align 8, !tbaa !20
  %6 = icmp eq i32 %5, 0
  %7 = icmp ne i32 %2, 0
  %8 = and i1 %6, %7
  br i1 %8, label %9, label %351

9:                                                ; preds = %3
  %10 = getelementptr inbounds nuw i8, ptr %0, i64 32
  %11 = getelementptr inbounds nuw i8, ptr %0, i64 24
  %12 = getelementptr inbounds nuw i8, ptr %0, i64 28
  %13 = getelementptr inbounds nuw i8, ptr %0, i64 29
  %14 = getelementptr inbounds nuw i8, ptr %0, i64 8
  %15 = getelementptr inbounds nuw i8, ptr %0, i64 16
  %16 = getelementptr inbounds nuw i8, ptr %0, i64 128
  %17 = getelementptr inbounds nuw i8, ptr %0, i64 136
  %18 = getelementptr inbounds nuw i8, ptr %0, i64 140
  %19 = getelementptr inbounds nuw i8, ptr %0, i64 120
  %20 = getelementptr inbounds nuw i8, ptr %0, i64 56
  %21 = getelementptr inbounds nuw i8, ptr %0, i64 124
  %22 = getelementptr inbounds nuw i8, ptr %0, i64 148
  %23 = getelementptr inbounds nuw i8, ptr %0, i64 144
  %24 = getelementptr inbounds nuw i8, ptr %0, i64 152
  %25 = getelementptr inbounds nuw i8, ptr %0, i64 160
  %26 = getelementptr inbounds nuw i8, ptr %0, i64 48
  %27 = getelementptr inbounds nuw i8, ptr %0, i64 132
  %28 = zext i32 %2 to i64
  br label %29

29:                                               ; preds = %9, %341
  %30 = phi i64 [ 0, %9 ], [ %344, %341 ]
  %31 = getelementptr inbounds nuw i8, ptr %1, i64 %30
  %32 = load i8, ptr %31, align 1, !tbaa !21
  %33 = load i32, ptr %10, align 8, !tbaa !13
  %34 = freeze i32 %33
  switch i32 %34, label %90 [
    i32 0, label %35
    i32 1, label %91
  ]

35:                                               ; preds = %29
  %36 = load i64, ptr %0, align 8, !tbaa !22
  %37 = icmp eq i64 %36, -1
  br i1 %37, label %38, label %40

38:                                               ; preds = %35
  store i32 2, ptr %10, align 8, !tbaa !13
  %39 = getelementptr inbounds nuw i8, ptr %0, i64 40
  store i64 -1, ptr %39, align 8, !tbaa !23
  br label %91

40:                                               ; preds = %35
  %41 = load i32, ptr %11, align 8, !tbaa !24
  %42 = icmp eq i32 %41, 0
  br i1 %42, label %43, label %69

43:                                               ; preds = %40
  store i64 %36, ptr %15, align 8, !tbaa !25
  %44 = icmp sgt i8 %32, -1
  br i1 %44, label %45, label %52

45:                                               ; preds = %43
  %46 = load i64, ptr %14, align 8, !tbaa !26
  %47 = icmp eq i64 %46, -1
  br i1 %47, label %48, label %50

48:                                               ; preds = %45
  store i32 2, ptr %10, align 8, !tbaa !13
  %49 = getelementptr inbounds nuw i8, ptr %0, i64 40
  store i64 %36, ptr %49, align 8, !tbaa !23
  br label %91

50:                                               ; preds = %45
  %51 = add nuw i64 %46, 1
  store i64 %51, ptr %14, align 8, !tbaa !26
  br label %94

52:                                               ; preds = %43
  store i8 -128, ptr %12, align 4, !tbaa !6
  store i8 -65, ptr %13, align 1, !tbaa !12
  %53 = add nsw i8 %32, 62
  %54 = icmp ult i8 %53, 30
  br i1 %54, label %55, label %56

55:                                               ; preds = %52
  store i32 1, ptr %11, align 8, !tbaa !24
  br label %94

56:                                               ; preds = %52
  %57 = and i8 %32, -16
  %58 = icmp eq i8 %57, -32
  br i1 %58, label %59, label %62

59:                                               ; preds = %56
  store i32 2, ptr %11, align 8, !tbaa !24
  switch i8 %32, label %94 [
    i8 -32, label %60
    i8 -19, label %61
  ]

60:                                               ; preds = %59
  store i8 -96, ptr %12, align 4, !tbaa !6
  br label %94

61:                                               ; preds = %59
  store i8 -97, ptr %13, align 1, !tbaa !12
  br label %94

62:                                               ; preds = %56
  %63 = add nsw i8 %32, 16
  %64 = icmp ult i8 %63, 5
  br i1 %64, label %65, label %68

65:                                               ; preds = %62
  store i32 3, ptr %11, align 8, !tbaa !24
  switch i8 %32, label %94 [
    i8 -16, label %66
    i8 -12, label %67
  ]

66:                                               ; preds = %65
  store i8 -112, ptr %12, align 4, !tbaa !6
  br label %94

67:                                               ; preds = %65
  store i8 -113, ptr %13, align 1, !tbaa !12
  br label %94

68:                                               ; preds = %62
  store i32 1, ptr %10, align 8, !tbaa !13
  br label %87

69:                                               ; preds = %40
  %70 = load i8, ptr %12, align 4, !tbaa !6
  %71 = icmp ult i8 %32, %70
  br i1 %71, label %75, label %72

72:                                               ; preds = %69
  %73 = load i8, ptr %13, align 1, !tbaa !12
  %74 = icmp ugt i8 %32, %73
  br i1 %74, label %75, label %77

75:                                               ; preds = %72, %69
  store i32 1, ptr %10, align 8, !tbaa !13
  %76 = load i64, ptr %15, align 8, !tbaa !25
  br label %87

77:                                               ; preds = %72
  %78 = add i32 %41, -1
  store i32 %78, ptr %11, align 8, !tbaa !24
  store i8 -128, ptr %12, align 4, !tbaa !6
  store i8 -65, ptr %13, align 1, !tbaa !12
  %79 = icmp eq i32 %78, 0
  br i1 %79, label %80, label %94

80:                                               ; preds = %77
  %81 = load i64, ptr %14, align 8, !tbaa !26
  %82 = icmp eq i64 %81, -1
  br i1 %82, label %83, label %85

83:                                               ; preds = %80
  store i32 2, ptr %10, align 8, !tbaa !13
  %84 = getelementptr inbounds nuw i8, ptr %0, i64 40
  store i64 %36, ptr %84, align 8, !tbaa !23
  br label %91

85:                                               ; preds = %80
  %86 = add nuw i64 %81, 1
  store i64 %86, ptr %14, align 8, !tbaa !26
  br label %94

87:                                               ; preds = %75, %68
  %88 = phi i64 [ %36, %68 ], [ %76, %75 ]
  %89 = getelementptr inbounds nuw i8, ptr %0, i64 40
  store i64 %88, ptr %89, align 8, !tbaa !23
  br label %91

90:                                               ; preds = %29
  br label %91

91:                                               ; preds = %87, %29, %90, %38, %48, %83
  %92 = phi i32 [ 8, %83 ], [ 8, %48 ], [ 8, %38 ], [ 8, %90 ], [ 5, %29 ], [ 5, %87 ]
  %93 = getelementptr inbounds nuw i8, ptr %0, i64 40
  br label %346

94:                                               ; preds = %85, %77, %67, %66, %65, %61, %60, %59, %55, %50
  %95 = add nuw i64 %36, 1
  store i64 %95, ptr %0, align 8, !tbaa !22
  %96 = load i8, ptr %31, align 1, !tbaa !21
  %97 = load i32, ptr %16, align 8, !tbaa !14
  switch i32 %97, label %218 [
    i32 1, label %98
    i32 2, label %128
    i32 4, label %131
    i32 5, label %134
    i32 3, label %137
    i32 6, label %137
    i32 20, label %173
  ]

98:                                               ; preds = %94
  %99 = icmp ult i8 %96, 32
  br i1 %99, label %346, label %100

100:                                              ; preds = %98
  switch i8 %96, label %338 [
    i8 34, label %101
    i8 92, label %126
  ]

101:                                              ; preds = %100
  store i32 0, ptr %16, align 8, !tbaa !14
  %102 = load i8, ptr %27, align 4, !tbaa !18, !range !27, !noundef !28
  %103 = trunc nuw i8 %102 to i1
  %104 = load i32, ptr %19, align 8, !tbaa !29
  br i1 %103, label %105, label %112

105:                                              ; preds = %101
  %106 = add i32 %104, -1
  %107 = icmp ugt i32 %106, 63
  br i1 %107, label %108, label %109

108:                                              ; preds = %105
  tail call void @_ZNSt3__120__throw_out_of_rangeB9nqe210106EPKc(ptr noundef nonnull @.str) #11
  unreachable

109:                                              ; preds = %105
  %110 = zext nneg i32 %106 to i64
  %111 = getelementptr inbounds nuw [64 x i8], ptr %20, i64 0, i64 %110
  store i8 5, ptr %111, align 1, !tbaa !21
  br label %338

112:                                              ; preds = %101
  %113 = icmp eq i32 %104, 0
  br i1 %113, label %114, label %115

114:                                              ; preds = %112
  store i8 1, ptr %21, align 4, !tbaa !30
  br label %338

115:                                              ; preds = %112
  %116 = add i32 %104, -1
  %117 = icmp ugt i32 %116, 63
  br i1 %117, label %118, label %119

118:                                              ; preds = %115
  tail call void @_ZNSt3__120__throw_out_of_rangeB9nqe210106EPKc(ptr noundef nonnull @.str) #11
  unreachable

119:                                              ; preds = %115
  %120 = zext nneg i32 %116 to i64
  %121 = getelementptr inbounds nuw [64 x i8], ptr %20, i64 0, i64 %120
  %122 = load i8, ptr %121, align 1, !tbaa !21
  %123 = and i8 %122, -3
  %124 = icmp eq i8 %123, 1
  %125 = select i1 %124, i8 2, i8 7
  store i8 %125, ptr %121, align 1, !tbaa !21
  br label %338

126:                                              ; preds = %100
  store i32 2, ptr %16, align 8, !tbaa !14
  %127 = load i64, ptr %26, align 8, !tbaa !31
  store i64 %127, ptr %24, align 8, !tbaa !32
  br label %338

128:                                              ; preds = %94
  switch i8 %96, label %346 [
    i8 116, label %129
    i8 114, label %129
    i8 110, label %129
    i8 102, label %129
    i8 98, label %129
    i8 92, label %129
    i8 47, label %129
    i8 34, label %129
    i8 117, label %130
  ]

129:                                              ; preds = %128, %128, %128, %128, %128, %128, %128, %128
  store i32 1, ptr %16, align 8, !tbaa !14
  br label %338

130:                                              ; preds = %128
  store i32 3, ptr %16, align 8, !tbaa !14
  store <2 x i32> zeroinitializer, ptr %23, align 8, !tbaa !33
  br label %338

131:                                              ; preds = %94
  %132 = icmp eq i8 %96, 92
  br i1 %132, label %133, label %346

133:                                              ; preds = %131
  store i32 5, ptr %16, align 8, !tbaa !14
  br label %338

134:                                              ; preds = %94
  %135 = icmp eq i8 %96, 117
  br i1 %135, label %136, label %346

136:                                              ; preds = %134
  store i32 6, ptr %16, align 8, !tbaa !14
  store <2 x i32> zeroinitializer, ptr %23, align 8, !tbaa !33
  br label %338

137:                                              ; preds = %94, %94
  %138 = zext i8 %96 to i32
  %139 = add i8 %96, -48
  %140 = icmp ult i8 %139, 10
  br i1 %140, label %141, label %143

141:                                              ; preds = %137
  %142 = add nsw i32 %138, -48
  br label %152

143:                                              ; preds = %137
  %144 = add i8 %96, -65
  %145 = icmp ult i8 %144, 6
  br i1 %145, label %146, label %148

146:                                              ; preds = %143
  %147 = add nsw i32 %138, -55
  br label %152

148:                                              ; preds = %143
  %149 = add i8 %96, -97
  %150 = icmp ult i8 %149, 6
  %151 = add nsw i32 %138, -87
  br i1 %150, label %152, label %346

152:                                              ; preds = %148, %146, %141
  %153 = phi i32 [ %142, %141 ], [ %147, %146 ], [ %151, %148 ]
  %154 = icmp eq i32 %153, 16
  br i1 %154, label %346, label %155

155:                                              ; preds = %152
  %156 = load i32, ptr %22, align 4, !tbaa !34
  %157 = shl i32 %156, 4
  %158 = add i32 %157, %153
  store i32 %158, ptr %22, align 4, !tbaa !34
  %159 = load i32, ptr %23, align 8, !tbaa !35
  %160 = add i32 %159, 1
  store i32 %160, ptr %23, align 8, !tbaa !35
  %161 = icmp eq i32 %160, 4
  br i1 %161, label %162, label %338

162:                                              ; preds = %155
  %163 = icmp eq i32 %97, 6
  br i1 %163, label %164, label %168

164:                                              ; preds = %162
  %165 = add i32 %158, -57344
  %166 = icmp ult i32 %165, -1024
  br i1 %166, label %346, label %167

167:                                              ; preds = %164
  store i32 1, ptr %16, align 8, !tbaa !14
  br label %338

168:                                              ; preds = %162
  %169 = and i32 %158, -1024
  switch i32 %169, label %172 [
    i32 55296, label %170
    i32 56320, label %346
  ]

170:                                              ; preds = %168
  store i32 4, ptr %16, align 8, !tbaa !14
  %171 = load i64, ptr %24, align 8, !tbaa !32
  store i64 %171, ptr %25, align 8, !tbaa !36
  br label %338

172:                                              ; preds = %168
  store i32 1, ptr %16, align 8, !tbaa !14
  br label %338

173:                                              ; preds = %94
  %174 = load i32, ptr %17, align 8, !tbaa !37
  %175 = load i32, ptr %18, align 4
  switch i32 %174, label %192 [
    i32 1, label %176
    i32 2, label %183
  ]

176:                                              ; preds = %173
  %177 = icmp eq i32 %175, 1
  %178 = select i1 %177, i8 114, i8 0
  %179 = icmp eq i32 %175, 2
  %180 = select i1 %179, i8 117, i8 %178
  %181 = icmp eq i32 %175, 3
  %182 = select i1 %181, i8 101, i8 %180
  br label %192

183:                                              ; preds = %173
  %184 = icmp eq i32 %175, 1
  %185 = select i1 %184, i8 97, i8 0
  %186 = icmp eq i32 %175, 2
  %187 = select i1 %186, i8 108, i8 %185
  %188 = icmp eq i32 %175, 3
  %189 = select i1 %188, i8 115, i8 %187
  %190 = icmp eq i32 %175, 4
  %191 = select i1 %190, i8 101, i8 %189
  br label %192

192:                                              ; preds = %183, %176, %173
  %193 = phi i8 [ %191, %183 ], [ %182, %176 ], [ 0, %173 ]
  %194 = phi i32 [ 5, %183 ], [ 4, %176 ], [ 4, %173 ]
  %195 = icmp eq i32 %174, 3
  %196 = icmp eq i32 %175, 1
  %197 = select i1 %196, i8 117, i8 108
  %198 = select i1 %195, i8 %197, i8 %193
  %199 = icmp eq i8 %96, %198
  br i1 %199, label %200, label %346

200:                                              ; preds = %192
  %201 = add i32 %175, 1
  store i32 %201, ptr %18, align 4, !tbaa !38
  %202 = icmp eq i32 %201, %194
  br i1 %202, label %203, label %338

203:                                              ; preds = %200
  store i32 0, ptr %16, align 8, !tbaa !14
  %204 = load i32, ptr %19, align 8, !tbaa !29
  %205 = icmp eq i32 %204, 0
  br i1 %205, label %206, label %207

206:                                              ; preds = %203
  store i8 1, ptr %21, align 4, !tbaa !30
  br label %338

207:                                              ; preds = %203
  %208 = add i32 %204, -1
  %209 = icmp ugt i32 %208, 63
  br i1 %209, label %210, label %211

210:                                              ; preds = %207
  tail call void @_ZNSt3__120__throw_out_of_rangeB9nqe210106EPKc(ptr noundef nonnull @.str) #11
  unreachable

211:                                              ; preds = %207
  %212 = zext nneg i32 %208 to i64
  %213 = getelementptr inbounds nuw [64 x i8], ptr %20, i64 0, i64 %212
  %214 = load i8, ptr %213, align 1, !tbaa !21
  %215 = and i8 %214, -3
  %216 = icmp eq i8 %215, 1
  %217 = select i1 %216, i8 2, i8 7
  store i8 %217, ptr %213, align 1, !tbaa !21
  br label %338

218:                                              ; preds = %94
  %219 = add i32 %97, -10
  %220 = icmp ult i32 %219, 8
  br i1 %220, label %221, label %257

221:                                              ; preds = %218
  %222 = add i8 %96, -48
  %223 = icmp ult i8 %222, 10
  br i1 %223, label %224, label %234

224:                                              ; preds = %221
  switch i32 %97, label %229 [
    i32 11, label %346
    i32 10, label %225
    i32 13, label %228
  ]

225:                                              ; preds = %224
  %226 = icmp eq i8 %96, 48
  %227 = select i1 %226, i32 11, i32 12
  store i32 %227, ptr %16, align 8, !tbaa !14
  br label %229

228:                                              ; preds = %224
  store i32 14, ptr %16, align 8, !tbaa !14
  br label %338

229:                                              ; preds = %225, %224
  %230 = phi i32 [ %227, %225 ], [ %97, %224 ]
  %231 = add nsw i32 %230, -15
  %232 = icmp ult i32 %231, 2
  br i1 %232, label %233, label %338

233:                                              ; preds = %229
  store i32 17, ptr %16, align 8, !tbaa !14
  br label %338

234:                                              ; preds = %221
  %235 = icmp eq i32 %97, 11
  br i1 %235, label %240, label %236

236:                                              ; preds = %234
  %237 = icmp eq i32 %97, 12
  %238 = icmp eq i8 %96, 46
  %239 = and i1 %238, %237
  br i1 %239, label %242, label %243

240:                                              ; preds = %234
  %241 = icmp eq i8 %96, 46
  br i1 %241, label %242, label %247

242:                                              ; preds = %240, %236
  store i32 13, ptr %16, align 8, !tbaa !14
  br label %338

243:                                              ; preds = %236
  switch i32 %97, label %255 [
    i32 11, label %244
    i32 12, label %244
    i32 14, label %244
    i32 15, label %251
    i32 10, label %346
    i32 13, label %346
    i32 16, label %346
  ]

244:                                              ; preds = %243, %243, %243
  %245 = and i8 %96, -33
  %246 = icmp eq i8 %245, 69
  br i1 %246, label %250, label %253

247:                                              ; preds = %240
  %248 = and i8 %96, -33
  %249 = icmp eq i8 %248, 69
  br i1 %249, label %250, label %255

250:                                              ; preds = %247, %244
  store i32 15, ptr %16, align 8, !tbaa !14
  br label %338

251:                                              ; preds = %243
  switch i8 %96, label %346 [
    i8 45, label %252
    i8 43, label %252
  ]

252:                                              ; preds = %251, %251
  store i32 16, ptr %16, align 8, !tbaa !14
  br label %338

253:                                              ; preds = %244
  %254 = icmp eq i32 %97, 13
  br i1 %254, label %346, label %255

255:                                              ; preds = %247, %253, %243
  switch i8 %96, label %346 [
    i8 32, label %256
    i8 10, label %256
    i8 9, label %256
    i8 13, label %256
    i8 125, label %256
    i8 93, label %256
    i8 44, label %256
  ]

256:                                              ; preds = %255, %255, %255, %255, %255, %255, %255
  store i32 0, ptr %16, align 8, !tbaa !14
  tail call fastcc void @_ZL4doneR5State(ptr noundef nonnull align 8 dereferenceable(184) %0)
  br label %257

257:                                              ; preds = %256, %218
  switch i8 %96, label %258 [
    i8 32, label %338
    i8 10, label %338
    i8 9, label %338
    i8 13, label %338
  ]

258:                                              ; preds = %257
  %259 = load i32, ptr %19, align 8, !tbaa !29
  %260 = icmp eq i32 %259, 0
  br i1 %260, label %275, label %261

261:                                              ; preds = %258
  %262 = add i32 %259, -1
  %263 = icmp ugt i32 %262, 63
  br i1 %263, label %264, label %265

264:                                              ; preds = %261
  tail call void @_ZNSt3__120__throw_out_of_rangeB9nqe210106EPKc(ptr noundef nonnull @.str) #11
  unreachable

265:                                              ; preds = %261
  %266 = zext nneg i32 %262 to i64
  %267 = getelementptr inbounds nuw [64 x i8], ptr %20, i64 0, i64 %266
  %268 = load i8, ptr %267, align 1, !tbaa !21
  %269 = zext i8 %268 to i32
  %270 = icmp eq i8 %96, 93
  %271 = add i8 %268, -1
  %272 = icmp ult i8 %271, 2
  %273 = select i1 %270, i1 %272, i1 false
  br i1 %273, label %274, label %275

274:                                              ; preds = %265
  store i32 %262, ptr %19, align 8, !tbaa !29
  br label %338

275:                                              ; preds = %265, %258
  %276 = phi i32 [ %269, %265 ], [ 0, %258 ]
  %277 = icmp eq i8 %96, 125
  %278 = trunc nuw i32 %276 to i8
  br i1 %277, label %279, label %282

279:                                              ; preds = %275
  switch i8 %278, label %282 [
    i8 7, label %280
    i8 4, label %280
  ]

280:                                              ; preds = %279, %279
  %281 = add nsw i32 %259, -1
  store i32 %281, ptr %19, align 8, !tbaa !29
  br label %338

282:                                              ; preds = %279, %275
  %283 = icmp eq i32 %276, 2
  switch i8 %278, label %306 [
    i8 7, label %284
    i8 2, label %284
    i8 5, label %294
    i8 8, label %303
    i8 4, label %303
  ]

284:                                              ; preds = %282, %282
  %285 = icmp eq i8 %96, 44
  br i1 %285, label %286, label %346

286:                                              ; preds = %284
  %287 = add nsw i32 %259, -1
  %288 = icmp ugt i32 %287, 63
  br i1 %288, label %289, label %290

289:                                              ; preds = %286
  tail call void @_ZNSt3__120__throw_out_of_rangeB9nqe210106EPKc(ptr noundef nonnull @.str) #11
  unreachable

290:                                              ; preds = %286
  %291 = zext nneg i32 %287 to i64
  %292 = select i1 %283, i8 3, i8 8
  %293 = getelementptr inbounds nuw [64 x i8], ptr %20, i64 0, i64 %291
  store i8 %292, ptr %293, align 1, !tbaa !21
  br label %338

294:                                              ; preds = %282
  %295 = icmp eq i8 %96, 58
  br i1 %295, label %296, label %346

296:                                              ; preds = %294
  %297 = add nsw i32 %259, -1
  %298 = icmp ugt i32 %297, 63
  br i1 %298, label %299, label %300

299:                                              ; preds = %296
  tail call void @_ZNSt3__120__throw_out_of_rangeB9nqe210106EPKc(ptr noundef nonnull @.str) #11
  unreachable

300:                                              ; preds = %296
  %301 = zext nneg i32 %297 to i64
  %302 = getelementptr inbounds nuw [64 x i8], ptr %20, i64 0, i64 %301
  store i8 6, ptr %302, align 1, !tbaa !21
  br label %338

303:                                              ; preds = %282, %282
  %304 = icmp eq i8 %96, 34
  br i1 %304, label %305, label %346

305:                                              ; preds = %303
  store i8 1, ptr %27, align 4, !tbaa !18
  store i32 1, ptr %16, align 8, !tbaa !14
  br label %338

306:                                              ; preds = %282
  %307 = load i8, ptr %21, align 4, !range !27
  %308 = trunc nuw i8 %307 to i1
  %309 = select i1 %260, i1 %308, i1 false
  br i1 %309, label %346, label %310

310:                                              ; preds = %306
  %311 = icmp eq i8 %96, 91
  switch i8 %96, label %326 [
    i8 123, label %312
    i8 91, label %312
    i8 34, label %324
    i8 45, label %325
  ]

312:                                              ; preds = %310, %310
  %313 = icmp eq i32 %259, 64
  br i1 %313, label %346, label %314

314:                                              ; preds = %312
  tail call fastcc void @_ZL4doneR5State(ptr noundef nonnull align 8 dereferenceable(184) %0)
  %315 = load i32, ptr %19, align 8, !tbaa !29
  %316 = icmp ugt i32 %315, 63
  br i1 %316, label %317, label %318

317:                                              ; preds = %314
  tail call void @_ZNSt3__120__throw_out_of_rangeB9nqe210106EPKc(ptr noundef nonnull @.str) #11
  unreachable

318:                                              ; preds = %314
  %319 = zext nneg i32 %315 to i64
  %320 = select i1 %311, i8 1, i8 4
  %321 = getelementptr inbounds nuw [64 x i8], ptr %20, i64 0, i64 %319
  store i8 %320, ptr %321, align 1, !tbaa !21
  %322 = load i32, ptr %19, align 8, !tbaa !29
  %323 = add i32 %322, 1
  store i32 %323, ptr %19, align 8, !tbaa !29
  br label %338

324:                                              ; preds = %310
  store i8 0, ptr %27, align 4, !tbaa !18
  store i32 1, ptr %16, align 8, !tbaa !14
  br label %338

325:                                              ; preds = %310
  store i32 10, ptr %16, align 8, !tbaa !14
  br label %338

326:                                              ; preds = %310
  %327 = add i8 %96, -48
  %328 = icmp ult i8 %327, 10
  br i1 %328, label %329, label %332

329:                                              ; preds = %326
  %330 = icmp eq i8 %96, 48
  %331 = select i1 %330, i32 11, i32 12
  store i32 %331, ptr %16, align 8, !tbaa !14
  br label %338

332:                                              ; preds = %326
  switch i8 %96, label %346 [
    i8 116, label %333
    i8 110, label %333
    i8 102, label %333
  ]

333:                                              ; preds = %332, %332, %332
  %334 = icmp eq i8 %96, 102
  %335 = icmp eq i8 %96, 116
  store i32 20, ptr %16, align 8, !tbaa !14
  store i32 1, ptr %18, align 4, !tbaa !38
  %336 = select i1 %334, i32 2, i32 3
  %337 = select i1 %335, i32 1, i32 %336
  store i32 %337, ptr %17, align 8, !tbaa !37
  br label %338

338:                                              ; preds = %119, %114, %100, %109, %126, %129, %130, %133, %136, %155, %167, %170, %172, %200, %206, %211, %228, %229, %233, %242, %250, %252, %257, %257, %257, %257, %274, %280, %290, %300, %305, %318, %324, %325, %329, %333
  %339 = load i32, ptr %4, align 8, !tbaa !20
  %340 = icmp eq i32 %339, 0
  br i1 %340, label %341, label %351

341:                                              ; preds = %338
  %342 = load i64, ptr %26, align 8, !tbaa !31
  %343 = add i64 %342, 1
  store i64 %343, ptr %26, align 8, !tbaa !31
  %344 = add nuw nsw i64 %30, 1
  %345 = icmp eq i64 %344, %28
  br i1 %345, label %351, label %29, !llvm.loop !39

346:                                              ; preds = %332, %312, %306, %303, %294, %284, %255, %243, %243, %243, %251, %253, %224, %192, %168, %164, %148, %152, %134, %131, %128, %98, %91
  %347 = phi i32 [ %92, %91 ], [ 1, %332 ], [ 7, %312 ], [ 1, %306 ], [ 1, %303 ], [ 1, %294 ], [ 1, %284 ], [ 2, %255 ], [ 2, %243 ], [ 2, %243 ], [ 2, %243 ], [ 2, %251 ], [ 2, %253 ], [ 2, %224 ], [ 1, %192 ], [ 4, %168 ], [ 4, %164 ], [ 3, %148 ], [ 3, %152 ], [ 4, %134 ], [ 4, %131 ], [ 3, %128 ], [ 1, %98 ]
  %348 = phi ptr [ %93, %91 ], [ %26, %332 ], [ %26, %312 ], [ %26, %306 ], [ %26, %303 ], [ %26, %294 ], [ %26, %284 ], [ %26, %255 ], [ %26, %243 ], [ %26, %243 ], [ %26, %243 ], [ %26, %251 ], [ %26, %253 ], [ %26, %224 ], [ %26, %192 ], [ %24, %168 ], [ %25, %164 ], [ %26, %148 ], [ %26, %152 ], [ %25, %134 ], [ %25, %131 ], [ %26, %128 ], [ %26, %98 ]
  %349 = load i64, ptr %348, align 8, !tbaa !41
  store i32 %347, ptr %4, align 8, !tbaa !20
  %350 = getelementptr inbounds nuw i8, ptr %0, i64 176
  store i64 %349, ptr %350, align 8, !tbaa !19
  br label %351

351:                                              ; preds = %338, %341, %346, %3
  ret void
}

; Function Attrs: mustprogress nocallback nofree nosync nounwind willreturn memory(argmem: readwrite)
declare void @llvm.lifetime.start.p0(i64 immarg, ptr captures(none)) #4

; Function Attrs: mustprogress nocallback nofree nosync nounwind willreturn memory(argmem: readwrite)
declare void @llvm.lifetime.end.p0(i64 immarg, ptr captures(none)) #4

; Function Attrs: mustprogress nofree norecurse nosync nounwind ssp willreturn memory(argmem: read) uwtable(sync)
define i32 @stream_pending(ptr noundef readonly captures(none) %0) local_unnamed_addr #5 {
  %2 = getelementptr inbounds nuw i8, ptr %0, i64 168
  %3 = load i32, ptr %2, align 8, !tbaa !20
  ret i32 %3
}

; Function Attrs: mustprogress ssp uwtable(sync)
define i32 @stream_status(ptr noundef readonly captures(none) %0) local_unnamed_addr #3 {
  %2 = alloca %struct.State, align 8
  %3 = alloca %struct.State, align 8
  call void @llvm.lifetime.start.p0(i64 184, ptr nonnull %2) #12
  call void @llvm.lifetime.start.p0(i64 184, ptr nonnull %3) #12
  call void @llvm.memcpy.p0.p0.i64(ptr noundef nonnull align 8 dereferenceable(184) %3, ptr noundef nonnull align 8 dereferenceable(184) %0, i64 184, i1 false), !tbaa.struct !42
  call fastcc void @_ZL6finish5State(ptr dead_on_unwind writable sret(%struct.State) align 8 %2, ptr noundef %3)
  call void @llvm.lifetime.end.p0(i64 184, ptr nonnull %3) #12
  %4 = getelementptr inbounds nuw i8, ptr %2, i64 168
  %5 = load i32, ptr %4, align 8, !tbaa !20
  call void @llvm.lifetime.end.p0(i64 184, ptr nonnull %2) #12
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
  %8 = load i32, ptr %7, align 8, !tbaa !44
  %9 = icmp eq i32 %8, 0
  br i1 %9, label %10, label %47

10:                                               ; preds = %6
  %11 = getelementptr inbounds nuw i8, ptr %1, i64 24
  %12 = load i32, ptr %11, align 8, !tbaa !45
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
  %19 = load i32, ptr %18, align 8, !tbaa !29
  %20 = icmp eq i32 %19, 0
  br i1 %20, label %21, label %23

21:                                               ; preds = %17
  %22 = getelementptr inbounds nuw i8, ptr %1, i64 124
  store i8 1, ptr %22, align 4, !tbaa !30
  br label %38

23:                                               ; preds = %17
  %24 = add i32 %19, -1
  %25 = icmp ugt i32 %24, 63
  br i1 %25, label %26, label %27

26:                                               ; preds = %23
  tail call void @_ZNSt3__120__throw_out_of_rangeB9nqe210106EPKc(ptr noundef nonnull @.str) #11
  unreachable

27:                                               ; preds = %23
  %28 = zext nneg i32 %24 to i64
  %29 = getelementptr inbounds nuw i8, ptr %1, i64 56
  %30 = getelementptr inbounds nuw [64 x i8], ptr %29, i64 0, i64 %28
  %31 = load i8, ptr %30, align 1, !tbaa !21
  %32 = and i8 %31, -3
  %33 = icmp eq i8 %32, 1
  %34 = select i1 %33, i8 2, i8 7
  store i8 %34, ptr %30, align 1, !tbaa !21
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
  %40 = load i32, ptr %39, align 8, !tbaa !29
  %41 = icmp eq i32 %40, 0
  br i1 %41, label %42, label %46

42:                                               ; preds = %38
  %43 = getelementptr inbounds nuw i8, ptr %1, i64 124
  %44 = load i8, ptr %43, align 4, !tbaa !30, !range !27, !noundef !28
  %45 = trunc nuw i8 %44 to i1
  br i1 %45, label %53, label %46

46:                                               ; preds = %36, %42, %38
  br label %47

47:                                               ; preds = %36, %36, %36, %6, %10, %46
  %48 = phi i64 [ 48, %46 ], [ 16, %10 ], [ 40, %6 ], [ 160, %36 ], [ 160, %36 ], [ 160, %36 ]
  %49 = phi i32 [ 6, %46 ], [ 5, %10 ], [ 5, %6 ], [ 4, %36 ], [ 4, %36 ], [ 4, %36 ]
  %50 = getelementptr inbounds nuw i8, ptr %1, i64 %48
  %51 = load i64, ptr %50, align 8, !tbaa !41
  store i32 %49, ptr %3, align 8, !tbaa !20
  %52 = getelementptr inbounds nuw i8, ptr %1, i64 176
  store i64 %51, ptr %52, align 8, !tbaa !19
  br label %53

53:                                               ; preds = %47, %42, %2
  tail call void @llvm.memcpy.p0.p0.i64(ptr noundef nonnull align 8 dereferenceable(184) %0, ptr noundef nonnull align 8 dereferenceable(184) %1, i64 184, i1 false)
  ret void
}

; Function Attrs: mustprogress nocallback nofree nounwind willreturn memory(argmem: readwrite)
declare void @llvm.memcpy.p0.p0.i64(ptr noalias writeonly captures(none), ptr noalias readonly captures(none), i64, i1 immarg) #6

; Function Attrs: mustprogress ssp uwtable(sync)
define i64 @stream_value(ptr noundef readonly captures(none) %0) local_unnamed_addr #3 {
  %2 = alloca %struct.State, align 8
  %3 = alloca %struct.State, align 8
  call void @llvm.lifetime.start.p0(i64 184, ptr nonnull %2) #12
  call void @llvm.lifetime.start.p0(i64 184, ptr nonnull %3) #12
  call void @llvm.memcpy.p0.p0.i64(ptr noundef nonnull align 8 dereferenceable(184) %3, ptr noundef nonnull align 8 dereferenceable(184) %0, i64 184, i1 false), !tbaa.struct !42
  call fastcc void @_ZL6finish5State(ptr dead_on_unwind writable sret(%struct.State) align 8 %2, ptr noundef %3)
  call void @llvm.lifetime.end.p0(i64 184, ptr nonnull %3) #12
  %4 = getelementptr inbounds nuw i8, ptr %2, i64 168
  %5 = load i32, ptr %4, align 8, !tbaa !20
  %6 = icmp eq i32 %5, 0
  %7 = getelementptr inbounds nuw i8, ptr %2, i64 176
  %8 = load i64, ptr %7, align 8
  %9 = getelementptr inbounds nuw i8, ptr %2, i64 48
  %10 = load i64, ptr %9, align 8
  %11 = select i1 %6, i64 %10, i64 %8
  call void @llvm.lifetime.end.p0(i64 184, ptr nonnull %2) #12
  ret i64 %11
}

; Function Attrs: mustprogress ssp uwtable(sync)
define internal fastcc void @_ZL4doneR5State(ptr noundef nonnull align 8 captures(none) dereferenceable(184) %0) unnamed_addr #3 {
  %2 = getelementptr inbounds nuw i8, ptr %0, i64 120
  %3 = load i32, ptr %2, align 8, !tbaa !29
  %4 = icmp eq i32 %3, 0
  br i1 %4, label %5, label %7

5:                                                ; preds = %1
  %6 = getelementptr inbounds nuw i8, ptr %0, i64 124
  store i8 1, ptr %6, align 4, !tbaa !30
  br label %19

7:                                                ; preds = %1
  %8 = add i32 %3, -1
  %9 = icmp ugt i32 %8, 63
  br i1 %9, label %10, label %11

10:                                               ; preds = %7
  tail call void @_ZNSt3__120__throw_out_of_rangeB9nqe210106EPKc(ptr noundef nonnull @.str) #11
  unreachable

11:                                               ; preds = %7
  %12 = zext nneg i32 %8 to i64
  %13 = getelementptr inbounds nuw i8, ptr %0, i64 56
  %14 = getelementptr inbounds nuw [64 x i8], ptr %13, i64 0, i64 %12
  %15 = load i8, ptr %14, align 1, !tbaa !21
  %16 = and i8 %15, -3
  %17 = icmp eq i8 %16, 1
  %18 = select i1 %17, i8 2, i8 7
  store i8 %18, ptr %14, align 1, !tbaa !21
  br label %19

19:                                               ; preds = %11, %5
  ret void
}

; Function Attrs: inlinehint mustprogress noreturn ssp uwtable(sync)
define linkonce_odr hidden void @_ZNSt3__120__throw_out_of_rangeB9nqe210106EPKc(ptr noundef %0) local_unnamed_addr #7 personality ptr @__gxx_personality_v0 {
  %2 = tail call ptr @__cxa_allocate_exception(i64 16) #12
  %3 = invoke ptr @_ZNSt12out_of_rangeC1B9nqe210106EPKc(ptr noundef %2, ptr noundef %0)
          to label %4 unwind label %5

4:                                                ; preds = %1
  tail call void @__cxa_throw(ptr %2, ptr nonnull @_ZTISt12out_of_range, ptr nonnull @_ZNSt12out_of_rangeD1Ev) #11
  unreachable

5:                                                ; preds = %1
  %6 = landingpad { ptr, i32 }
          cleanup
  tail call void @__cxa_free_exception(ptr %2) #12
  resume { ptr, i32 } %6
}

declare ptr @__cxa_allocate_exception(i64) local_unnamed_addr

; Function Attrs: mustprogress ssp uwtable(sync)
define linkonce_odr hidden ptr @_ZNSt12out_of_rangeC1B9nqe210106EPKc(ptr noundef returned %0, ptr noundef %1) unnamed_addr #3 {
  %3 = tail call ptr @_ZNSt11logic_errorC2EPKc(ptr noundef %0, ptr noundef %1)
  store ptr getelementptr inbounds nuw inrange(-16, 24) (i8, ptr @_ZTVSt12out_of_range, i64 16), ptr %0, align 8, !tbaa !46
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
attributes #5 = { mustprogress nofree norecurse nosync nounwind ssp willreturn memory(argmem: read) uwtable(sync) "frame-pointer"="non-leaf" "no-trapping-math"="true" "probe-stack"="__chkstk_darwin" "stack-protector-buffer-size"="8" "target-cpu"="generic" "target-features"="+ete,+fp-armv8,+neon,+trbe,+v8a" }
attributes #6 = { mustprogress nocallback nofree nounwind willreturn memory(argmem: readwrite) }
attributes #7 = { inlinehint mustprogress noreturn ssp uwtable(sync) "frame-pointer"="non-leaf" "no-trapping-math"="true" "probe-stack"="__chkstk_darwin" "stack-protector-buffer-size"="8" "target-cpu"="generic" "target-features"="+ete,+fp-armv8,+neon,+trbe,+v8a" }
attributes #8 = { nounwind "frame-pointer"="non-leaf" "no-trapping-math"="true" "probe-stack"="__chkstk_darwin" "stack-protector-buffer-size"="8" "target-cpu"="generic" "target-features"="+ete,+fp-armv8,+neon,+trbe,+v8a" }
attributes #9 = { cold noreturn }
attributes #10 = { "frame-pointer"="non-leaf" "no-trapping-math"="true" "probe-stack"="__chkstk_darwin" "stack-protector-buffer-size"="8" "target-cpu"="generic" "target-features"="+ete,+fp-armv8,+neon,+trbe,+v8a" }
attributes #11 = { noreturn }
attributes #12 = { nounwind }

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
!21 = !{!9, !9, i64 0}
!22 = !{!7, !8, i64 0}
!23 = !{!7, !8, i64 40}
!24 = !{!7, !11, i64 24}
!25 = !{!7, !8, i64 16}
!26 = !{!7, !8, i64 8}
!27 = !{i8 0, i8 2}
!28 = !{}
!29 = !{!15, !11, i64 120}
!30 = !{!15, !17, i64 124}
!31 = !{!15, !8, i64 48}
!32 = !{!15, !8, i64 152}
!33 = !{!11, !11, i64 0}
!34 = !{!15, !11, i64 148}
!35 = !{!15, !11, i64 144}
!36 = !{!15, !8, i64 160}
!37 = !{!15, !11, i64 136}
!38 = !{!15, !11, i64 140}
!39 = distinct !{!39, !40}
!40 = !{!"llvm.loop.mustprogress"}
!41 = !{!8, !8, i64 0}
!42 = !{i64 0, i64 8, !41, i64 8, i64 8, !41, i64 16, i64 8, !41, i64 24, i64 4, !33, i64 28, i64 1, !21, i64 29, i64 1, !21, i64 32, i64 4, !33, i64 40, i64 8, !41, i64 48, i64 8, !41, i64 56, i64 64, !21, i64 120, i64 4, !33, i64 124, i64 1, !43, i64 128, i64 4, !33, i64 132, i64 1, !43, i64 136, i64 4, !33, i64 140, i64 4, !33, i64 144, i64 4, !33, i64 148, i64 4, !33, i64 152, i64 8, !41, i64 160, i64 8, !41, i64 168, i64 4, !33, i64 176, i64 8, !41}
!43 = !{!17, !17, i64 0}
!44 = !{!15, !11, i64 32}
!45 = !{!15, !11, i64 24}
!46 = !{!47, !47, i64 0}
!47 = !{!"vtable pointer", !10, i64 0}
