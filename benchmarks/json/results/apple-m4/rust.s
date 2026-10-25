	.build_version macos, 11, 0
	.section	__TEXT,__text,regular,pure_instructions
	.p2align	2
__RNvCscgRqy0Y3eGg_6parser4done:
	ldr	w8, [x0, #144]
	cbz	w8, LBB0_3
	cmp	w8, #64
	sub	w8, w8, #1
	b.hi	LBB0_4
	ldrb	w9, [x0, x8]
	mov	w10, #253
	sub	w9, w9, #1
	tst	w9, w10
	mov	w9, #7
	mov	w10, #2
	csel	w9, w10, w9, eq
	strb	w9, [x0, x8]
	ret
LBB0_3:
	mov	w8, #1
	strb	w8, [x0, #172]
	ret
LBB0_4:
	stp	x29, x30, [sp, #-16]!
Lloh0:
	adrp	x2, l_alloc_17c2635886f4fbc2ea36dbf6a4113cf0@PAGE
Lloh1:
	add	x2, x2, l_alloc_17c2635886f4fbc2ea36dbf6a4113cf0@PAGEOFF
	mov	x0, x8
	mov	w1, #64
	mov	x29, sp
	bl	__RNvNtCs9nEiEE0E2Vj_4core9panicking18panic_bounds_check
	.loh AdrpAdd	Lloh0, Lloh1

	.globl	_stream_feed
	.p2align	2
_stream_feed:
	stp	x28, x27, [sp, #-96]!
	ldr	w8, [x0, #168]
	stp	x26, x25, [sp, #16]
	stp	x24, x23, [sp, #32]
	stp	x22, x21, [sp, #48]
	stp	x20, x19, [sp, #64]
	stp	x29, x30, [sp, #80]
	add	x29, sp, #80
	cbnz	w8, LBB1_169
	cbz	w2, LBB1_169
	mov	x7, #8193
	mov	w19, #4113
	mov	w21, w2
	add	x20, x0, #88
	add	x23, x0, #112
	mov	w13, #8
	mov	w24, #49024
	mov	w25, #1
	mov	w14, #2
	mov	w15, #160
	mov	w16, #159
	mov	w17, #3
	mov	w2, #143
	mov	w3, #144
	mov	w4, #5
	mov	w5, #253
	mov	w6, #7
	movk	x7, #1024, lsl #48
	movk	w19, #5, lsl #16
	mov	w28, #55296
	mov	w30, #4
	mov	w12, #6
	mov	w27, #117
	mov	w26, #108
LBB1_3:
	ldr	w8, [x0, #100]
	cbnz	w8, LBB1_161
	ldr	x9, [x0, #64]
	cmn	x9, #1
	b.eq	LBB1_162
	ldr	w8, [x0, #96]
	ldrb	w22, [x1], #1
	cbz	w8, LBB1_9
	ldrb	w10, [x0, #104]
	cmp	w22, w10
	b.lo	LBB1_163
	ldrb	w10, [x0, #105]
	cmp	w22, w10
	b.hi	LBB1_163
	subs	w8, w8, #1
	strh	w24, [x0, #104]
	str	w8, [x0, #96]
	b.ne	LBB1_12
	b	LBB1_10
LBB1_9:
	str	x9, [x0, #80]
	tbnz	w22, #7, LBB1_29
LBB1_10:
	ldr	x8, [x0, #72]
	cmn	x8, #1
	b.eq	LBB1_162
	add	x8, x8, #1
	str	x8, [x0, #72]
LBB1_12:
	ldr	w8, [x0, #148]
	add	x9, x9, #1
	str	x9, [x0, #64]
	cmp	w8, #3
	b.le	LBB1_18
	cmp	w8, #5
	b.gt	LBB1_21
	cmp	w8, #4
	b.eq	LBB1_43
	cmp	w8, #5
	b.ne	LBB1_38
	cmp	w22, #117
	b.ne	LBB1_165
	str	w12, [x0, #148]
	str	xzr, [x0, #160]
	b	LBB1_107
LBB1_18:
	cmp	w8, #1
	b.eq	LBB1_31
	cmp	w8, #2
	b.eq	LBB1_45
	cmp	w8, #3
	b.eq	LBB1_26
	b	LBB1_38
LBB1_21:
	cmp	w8, #6
	b.eq	LBB1_26
	cmp	w8, #20
	b.ne	LBB1_38
	ldp	w9, w8, [x0, #152]
	cmp	w9, #1
	b.eq	LBB1_66
	cmp	w9, #2
	b.ne	LBB1_67
	cmp	w8, #1
	mov	w10, #97
	mov	w11, #115
	csel	w10, w10, wzr, eq
	cmp	w8, #2
	csel	w10, w26, w10, eq
	cmp	w8, #3
	csel	w10, w11, w10, eq
	cmp	w8, #4
	mov	w11, #101
	csel	w11, w11, w10, eq
	mov	w10, #5
	b	LBB1_69
LBB1_26:
	sub	w9, w22, #48
	cmp	w9, #10
	b.lo	LBB1_55
	sub	w9, w22, #65
	cmp	w9, #6
	b.hs	LBB1_53
	sub	w9, w22, #55
	b	LBB1_55
LBB1_29:
	add	w8, w22, #62
	strh	w24, [x0, #104]
	and	w8, w8, #0xff
	cmp	w8, #30
	b.hs	LBB1_49
	str	w25, [x0, #96]
	b	LBB1_12
LBB1_31:
	cmp	w22, #32
	b.lo	LBB1_166
	cmp	w22, #92
	b.eq	LBB1_75
	cmp	w22, #34
	b.ne	LBB1_107
	ldrb	w8, [x0, #173]
	str	wzr, [x0, #148]
	tbz	w8, #0, LBB1_83
	ldr	w8, [x0, #144]
	cbz	w8, LBB1_181
	cmp	w8, #65
	sub	w8, w8, #1
	b.hs	LBB1_180
	strb	w4, [x0, x8]
	b	LBB1_107
LBB1_38:
	sub	w9, w8, #10
	cmp	w9, #8
	b.hs	LBB1_105
	sub	w9, w22, #48
	cmp	w9, #10
	b.hs	LBB1_80
	cmp	w8, #10
	b.eq	LBB1_92
	cmp	w8, #13
	b.eq	LBB1_91
	cmp	w8, #11
	b.ne	LBB1_93
	b	LBB1_172
LBB1_43:
	cmp	w22, #92
	b.ne	LBB1_165
	str	w4, [x0, #148]
	b	LBB1_107
LBB1_45:
	sub	w8, w22, #98
	cmp	w8, #19
	b.hi	LBB1_63
	lsr	w9, w19, w8
	tbnz	w9, #0, LBB1_65
	cmp	w8, #19
	b.ne	LBB1_63
	str	w17, [x0, #148]
	str	xzr, [x0, #160]
	b	LBB1_107
LBB1_49:
	and	w8, w22, #0xf0
	cmp	w8, #224
	b.ne	LBB1_76
	cmp	w22, #224
	str	w14, [x0, #96]
	b.eq	LBB1_89
	cmp	w22, #237
	b.ne	LBB1_12
	strb	w16, [x0, #105]
	b	LBB1_12
LBB1_53:
	sub	w9, w22, #103
	and	w9, w9, #0xff
	cmp	w9, #250
	b.lo	LBB1_170
	sub	w9, w22, #87
LBB1_55:
	ldr	w10, [x0, #164]
	lsr	w11, w10, #28
	cbnz	w11, LBB1_177
	lsl	w10, w10, #4
	adds	w9, w10, w9, uxtb
	b.hs	LBB1_176
	ldr	w10, [x0, #160]
	str	w9, [x0, #164]
	cmn	w10, #1
	b.eq	LBB1_175
	add	w10, w10, #1
	cmp	w10, #4
	str	w10, [x0, #160]
	b.ne	LBB1_107
	cmp	w8, #6
	b.ne	LBB1_61
	sub	w8, w9, #14, lsl #12
	cmn	w8, #1024
	b.hs	LBB1_65
	b	LBB1_165
LBB1_61:
	and	w8, w9, #0xfffffc00
	cmp	w8, w28
	b.eq	LBB1_82
	mov	w9, #56320
	cmp	w8, w9
	b.ne	LBB1_65
	b	LBB1_171
LBB1_63:
	sub	w9, w22, #34
	mov	w8, #3
	cmp	w9, #58
	b.hi	LBB1_167
	lsr	x9, x7, x9
	tbz	w9, #0, LBB1_167
LBB1_65:
	str	w25, [x0, #148]
	b	LBB1_107
LBB1_66:
	cmp	w8, #1
	mov	w10, #114
	mov	w11, #101
	csel	w10, w10, wzr, eq
	cmp	w8, #2
	csel	w10, w27, w10, eq
	cmp	w8, #3
	csel	w11, w11, w10, eq
	b	LBB1_68
LBB1_67:
	mov	w11, wzr
LBB1_68:
	mov	w10, #4
LBB1_69:
	cmp	w8, #1
	csel	w12, w27, w26, eq
	cmp	w9, #3
	csel	w9, w12, w11, eq
	cmp	w22, w9
	b.ne	LBB1_166
	cmn	w8, #1
	b.eq	LBB1_178
	add	w8, w8, #1
	mov	w12, #6
	cmp	w8, w10
	str	w8, [x0, #156]
	b.ne	LBB1_107
	ldr	w8, [x0, #144]
	str	wzr, [x0, #148]
	cbz	w8, LBB1_84
LBB1_73:
	cmp	w8, #64
	sub	w8, w8, #1
	b.hi	LBB1_179
	ldrb	w9, [x0, x8]
	sub	w9, w9, #1
	tst	w9, w5
	csel	w9, w14, w6, eq
	strb	w9, [x0, x8]
	b	LBB1_107
LBB1_75:
	ldr	x8, [x0, #112]
	str	w14, [x0, #148]
	str	x8, [x0, #120]
	b	LBB1_107
LBB1_76:
	add	w8, w22, #16
	and	w8, w8, #0xff
	cmp	w8, #5
	b.hs	LBB1_164
	cmp	w22, #244
	str	w17, [x0, #96]
	b.eq	LBB1_90
	cmp	w22, #240
	b.ne	LBB1_12
	strb	w3, [x0, #104]
	b	LBB1_12
LBB1_80:
	sub	w9, w8, #11
	cmp	w9, #2
	mov	w9, #46
	ccmp	w22, w9, #0, lo
	b.ne	LBB1_85
	mov	w8, #13
	b	LBB1_99
LBB1_82:
	ldr	x8, [x0, #120]
	str	w30, [x0, #148]
	str	x8, [x0, #128]
	b	LBB1_107
LBB1_83:
	ldr	w8, [x0, #144]
	cbnz	w8, LBB1_73
LBB1_84:
	strb	w25, [x0, #172]
	b	LBB1_107
LBB1_85:
	cmp	w8, #16
	b.hi	LBB1_102
	mov	w9, #22528
	lsr	w9, w9, w8
	tbz	w9, #0, LBB1_95
	orr	w9, w22, #0x20
	cmp	w9, #101
	b.ne	LBB1_100
	mov	w8, #15
	b	LBB1_99
LBB1_89:
	strb	w15, [x0, #104]
	b	LBB1_12
LBB1_90:
	strb	w2, [x0, #105]
	b	LBB1_12
LBB1_91:
	mov	w8, #14
	b	LBB1_99
LBB1_92:
	cmp	w22, #48
	mov	w8, #11
	cinc	w8, w8, ne
	str	w8, [x0, #148]
LBB1_93:
	sub	w8, w8, #15
	cmp	w8, #1
	b.hi	LBB1_107
	mov	w8, #17
	b	LBB1_99
LBB1_95:
	cmp	w8, #15
	b.ne	LBB1_101
	cmp	w22, #45
	b.eq	LBB1_98
	cmp	w22, #43
	b.ne	LBB1_172
LBB1_98:
	mov	w8, #16
LBB1_99:
	str	w8, [x0, #148]
	b	LBB1_107
LBB1_100:
	cmp	w8, #13
	b.ne	LBB1_102
	b	LBB1_172
LBB1_101:
	mov	w9, #9216
	movk	w9, #1, lsl #16
	lsr	w8, w9, w8
	tbnz	w8, #0, LBB1_172
LBB1_102:
	mov	x28, x1
	cmp	w22, #44
	b.hi	LBB1_143
	mov	x8, #9728
	movk	x8, #4097, lsl #32
	lsr	x8, x8, x22
	tbz	w8, #0, LBB1_143
LBB1_104:
	str	wzr, [x0, #148]
	mov	x19, x0
	bl	__RNvCscgRqy0Y3eGg_6parser4done
	mov	x0, x19
	mov	x7, #8193
	mov	w19, #4113
	mov	x1, x28
	mov	w13, #8
	mov	w14, #2
	mov	w15, #160
	mov	w16, #159
	mov	w17, #3
	mov	w2, #143
	mov	w3, #144
	mov	w4, #5
	mov	w5, #253
	mov	w6, #7
	movk	x7, #1024, lsl #48
	movk	w19, #5, lsl #16
	mov	w28, #55296
	mov	w30, #4
	mov	w12, #6
LBB1_105:
	cmp	w22, #32
	b.hi	LBB1_110
	mov	x8, #9728
	movk	x8, #1, lsl #32
	lsr	x8, x8, x22
	tbz	w8, #0, LBB1_110
LBB1_107:
	ldr	w8, [x0, #168]
	cbnz	w8, LBB1_169
	ldr	x8, [x23]
	cmn	x8, #1
	b.eq	LBB1_174
	add	x8, x8, #1
	subs	x21, x21, #1
	str	x8, [x23]
	b.ne	LBB1_3
	b	LBB1_169
LBB1_110:
	ldr	w9, [x0, #144]
	cbz	w9, LBB1_115
	cmp	w9, #64
	sub	w8, w9, #1
	b.hi	LBB1_182
	ldrb	w10, [x0, x8]
	cmp	w22, #93
	b.ne	LBB1_123
	sub	w11, w10, #1
	cmp	w11, #2
	b.hs	LBB1_128
	str	w8, [x0, #144]
	b	LBB1_107
LBB1_115:
	cmp	w22, #93
	b.ne	LBB1_122
LBB1_116:
	cbnz	w9, LBB1_118
	ldrb	w8, [x0, #172]
	tbnz	w8, #0, LBB1_166
LBB1_118:
	cmp	w22, #90
	b.gt	LBB1_139
	cmp	w22, #34
	b.eq	LBB1_150
	cmp	w22, #45
	b.ne	LBB1_148
	mov	w8, #10
	b	LBB1_99
LBB1_122:
	mov	w10, wzr
LBB1_123:
	cmp	w22, #125
	b.ne	LBB1_128
	cmp	w10, #4
	b.eq	LBB1_126
	cmp	w10, #7
	b.ne	LBB1_128
LBB1_126:
	cbz	w9, LBB1_184
	sub	w8, w9, #1
	str	w8, [x0, #144]
	b	LBB1_107
LBB1_128:
	cmp	w10, #4
	b.le	LBB1_132
	cmp	w10, #5
	b.eq	LBB1_145
	cmp	w10, #7
	b.eq	LBB1_136
	cmp	w10, #8
	b.eq	LBB1_134
	b	LBB1_116
LBB1_132:
	cmp	w10, #2
	b.eq	LBB1_136
	cmp	w10, #4
	b.ne	LBB1_116
LBB1_134:
	cmp	w22, #34
	b.ne	LBB1_166
	strb	w25, [x0, #173]
	str	w25, [x0, #148]
	b	LBB1_107
LBB1_136:
	cmp	w22, #44
	b.ne	LBB1_166
	cbz	w9, LBB1_185
	cmp	w10, #2
	add	x9, x0, x9
	csel	w8, w17, w13, eq
	sturb	w8, [x9, #-1]
	b	LBB1_107
LBB1_139:
	cmp	w22, #123
	b.eq	LBB1_151
	cmp	w22, #91
	b.ne	LBB1_148
	cmp	w9, #64
	b.eq	LBB1_173
	mov	x22, x1
	mov	w28, #1
	b	LBB1_153
LBB1_143:
	cmp	w22, #125
	b.eq	LBB1_104
	cmp	w22, #93
	b.eq	LBB1_104
	b	LBB1_172
LBB1_145:
	cmp	w22, #58
	b.ne	LBB1_166
	cbz	w9, LBB1_188
	add	x8, x0, x9
	sturb	w12, [x8, #-1]
	b	LBB1_107
LBB1_148:
	sub	w8, w22, #48
	cmp	w8, #10
	b.hs	LBB1_156
	cmp	w22, #48
	mov	w8, #11
	cinc	w8, w8, ne
	b	LBB1_99
LBB1_150:
	strb	wzr, [x0, #173]
	str	w25, [x0, #148]
	b	LBB1_107
LBB1_151:
	cmp	w9, #64
	b.eq	LBB1_173
	mov	x22, x1
	mov	w28, #4
LBB1_153:
	mov	x19, x0
	bl	__RNvCscgRqy0Y3eGg_6parser4done
	ldr	w8, [x19, #144]
	cmp	w8, #64
	b.hs	LBB1_186
	strb	w28, [x19, x8]
	mov	x0, x19
	mov	w30, #4
	ldr	w8, [x19, #144]
	mov	w12, #6
	cmn	w8, #1
	b.eq	LBB1_187
	add	w8, w8, #1
	mov	x7, #8193
	mov	w19, #4113
	mov	x1, x22
	str	w8, [x0, #144]
	mov	w13, #8
	mov	w14, #2
	mov	w15, #160
	mov	w16, #159
	mov	w17, #3
	mov	w2, #143
	mov	w3, #144
	mov	w4, #5
	mov	w5, #253
	mov	w6, #7
	movk	x7, #1024, lsl #48
	movk	w19, #5, lsl #16
	mov	w28, #55296
	b	LBB1_107
LBB1_156:
	cmp	w22, #102
	b.eq	LBB1_160
	cmp	w22, #110
	b.eq	LBB1_160
	cmp	w22, #116
	b.ne	LBB1_166
	mov	w8, #20
	stp	w25, w25, [x0, #152]
	str	w8, [x0, #148]
	b	LBB1_107
LBB1_160:
	cmp	w22, #102
	mov	w9, #20
	cinc	w8, w14, ne
	str	w9, [x0, #148]
	stp	w8, w25, [x0, #152]
	b	LBB1_107
LBB1_161:
	cmp	w8, #1
	mov	w8, #5
	csel	w8, w8, w13, eq
	b	LBB1_168
LBB1_162:
	mov	w8, #2
	str	x9, [x0, #88]
	str	w8, [x0, #100]
	mov	w8, #8
	b	LBB1_168
LBB1_163:
	ldr	x9, [x0, #80]
LBB1_164:
	mov	w8, #1
	str	w8, [x0, #100]
	mov	w8, #5
	str	x9, [x0, #88]
	b	LBB1_168
LBB1_165:
	mov	w8, #4
	add	x20, x0, #128
	b	LBB1_168
LBB1_166:
	mov	w8, #1
LBB1_167:
	add	x20, x0, #112
LBB1_168:
	ldr	x9, [x20]
	str	w8, [x0, #168]
	str	x9, [x0, #136]
LBB1_169:
	ldp	x29, x30, [sp, #80]
	ldp	x20, x19, [sp, #64]
	ldp	x22, x21, [sp, #48]
	ldp	x24, x23, [sp, #32]
	ldp	x26, x25, [sp, #16]
	ldp	x28, x27, [sp], #96
	ret
LBB1_170:
	mov	w8, #3
	b	LBB1_167
LBB1_171:
	mov	w8, #4
	add	x20, x0, #120
	b	LBB1_168
LBB1_172:
	mov	w8, #2
	b	LBB1_167
LBB1_173:
	mov	w8, #7
	b	LBB1_167
LBB1_174:
Lloh2:
	adrp	x0, l_alloc_67efdafa9b0dc47c916e8f72fff3e807@PAGE
Lloh3:
	add	x0, x0, l_alloc_67efdafa9b0dc47c916e8f72fff3e807@PAGEOFF
	bl	__RNvNtNtCs9nEiEE0E2Vj_4core9panicking11panic_const24panic_const_add_overflow
LBB1_175:
Lloh4:
	adrp	x0, l_alloc_e67dfff62b8e4ecb323b784eaa923bef@PAGE
Lloh5:
	add	x0, x0, l_alloc_e67dfff62b8e4ecb323b784eaa923bef@PAGEOFF
	bl	__RNvNtNtCs9nEiEE0E2Vj_4core9panicking11panic_const24panic_const_add_overflow
LBB1_176:
Lloh6:
	adrp	x0, l_alloc_7fcdd0112aa4a922a81991942fa2013b@PAGE
Lloh7:
	add	x0, x0, l_alloc_7fcdd0112aa4a922a81991942fa2013b@PAGEOFF
	bl	__RNvNtNtCs9nEiEE0E2Vj_4core9panicking11panic_const24panic_const_add_overflow
LBB1_177:
Lloh8:
	adrp	x0, l_alloc_7fcdd0112aa4a922a81991942fa2013b@PAGE
Lloh9:
	add	x0, x0, l_alloc_7fcdd0112aa4a922a81991942fa2013b@PAGEOFF
	bl	__RNvNtNtCs9nEiEE0E2Vj_4core9panicking11panic_const24panic_const_mul_overflow
LBB1_178:
Lloh10:
	adrp	x0, l_alloc_2d6ba3368b9b590ce6e8441798328433@PAGE
Lloh11:
	add	x0, x0, l_alloc_2d6ba3368b9b590ce6e8441798328433@PAGEOFF
	bl	__RNvNtNtCs9nEiEE0E2Vj_4core9panicking11panic_const24panic_const_add_overflow
LBB1_179:
Lloh12:
	adrp	x2, l_alloc_17c2635886f4fbc2ea36dbf6a4113cf0@PAGE
Lloh13:
	add	x2, x2, l_alloc_17c2635886f4fbc2ea36dbf6a4113cf0@PAGEOFF
	b	LBB1_183
LBB1_180:
Lloh14:
	adrp	x2, l_alloc_38ab136aad52e23038f13eabe203b7df@PAGE
Lloh15:
	add	x2, x2, l_alloc_38ab136aad52e23038f13eabe203b7df@PAGEOFF
	b	LBB1_183
LBB1_181:
Lloh16:
	adrp	x0, l_alloc_e4ed959f92efea1cff8b4b98f2146f02@PAGE
Lloh17:
	add	x0, x0, l_alloc_e4ed959f92efea1cff8b4b98f2146f02@PAGEOFF
	bl	__RNvNtNtCs9nEiEE0E2Vj_4core9panicking11panic_const24panic_const_sub_overflow
LBB1_182:
Lloh18:
	adrp	x2, l_alloc_ca89a41573afe1edc3f237491af5f4cb@PAGE
Lloh19:
	add	x2, x2, l_alloc_ca89a41573afe1edc3f237491af5f4cb@PAGEOFF
LBB1_183:
	mov	x0, x8
	mov	w1, #64
	bl	__RNvNtCs9nEiEE0E2Vj_4core9panicking18panic_bounds_check
LBB1_184:
Lloh20:
	adrp	x0, l_alloc_232157ae9decd89c9f2076cdf71110bc@PAGE
Lloh21:
	add	x0, x0, l_alloc_232157ae9decd89c9f2076cdf71110bc@PAGEOFF
	bl	__RNvNtNtCs9nEiEE0E2Vj_4core9panicking11panic_const24panic_const_sub_overflow
LBB1_185:
Lloh22:
	adrp	x0, l_alloc_04fe8135d2319897c873529430c986db@PAGE
Lloh23:
	add	x0, x0, l_alloc_04fe8135d2319897c873529430c986db@PAGEOFF
	bl	__RNvNtNtCs9nEiEE0E2Vj_4core9panicking11panic_const24panic_const_sub_overflow
LBB1_186:
Lloh24:
	adrp	x2, l_alloc_21a6ae3fdeb0c022136d547ac7b9c594@PAGE
Lloh25:
	add	x2, x2, l_alloc_21a6ae3fdeb0c022136d547ac7b9c594@PAGEOFF
	b	LBB1_183
LBB1_187:
Lloh26:
	adrp	x0, l_alloc_e0474d9a635040eab39bac01d02d2ec4@PAGE
Lloh27:
	add	x0, x0, l_alloc_e0474d9a635040eab39bac01d02d2ec4@PAGEOFF
	bl	__RNvNtNtCs9nEiEE0E2Vj_4core9panicking11panic_const24panic_const_add_overflow
LBB1_188:
Lloh28:
	adrp	x0, l_alloc_1fb0c37e44d2c7e7dd89cb8d4cf14241@PAGE
Lloh29:
	add	x0, x0, l_alloc_1fb0c37e44d2c7e7dd89cb8d4cf14241@PAGEOFF
	bl	__RNvNtNtCs9nEiEE0E2Vj_4core9panicking11panic_const24panic_const_sub_overflow
	.loh AdrpAdd	Lloh2, Lloh3
	.loh AdrpAdd	Lloh4, Lloh5
	.loh AdrpAdd	Lloh6, Lloh7
	.loh AdrpAdd	Lloh8, Lloh9
	.loh AdrpAdd	Lloh10, Lloh11
	.loh AdrpAdd	Lloh12, Lloh13
	.loh AdrpAdd	Lloh14, Lloh15
	.loh AdrpAdd	Lloh16, Lloh17
	.loh AdrpAdd	Lloh18, Lloh19
	.loh AdrpAdd	Lloh20, Lloh21
	.loh AdrpAdd	Lloh22, Lloh23
	.loh AdrpAdd	Lloh24, Lloh25
	.loh AdrpAdd	Lloh26, Lloh27
	.loh AdrpAdd	Lloh28, Lloh29

	.globl	_stream_pending
	.p2align	2
_stream_pending:
	ldr	w0, [x0, #168]
	ret

	.globl	_stream_size
	.p2align	2
_stream_size:
	mov	w0, #176
	ret

	.globl	_stream_start
	.p2align	2
_stream_start:
	movi.2d	v0, #0000000000000000
	mov	w8, #49024
	str	xzr, [x0, #96]
	strh	w8, [x0, #104]
	stp	q0, q0, [x0]
	stp	q0, q0, [x0, #32]
	stp	q0, q0, [x0, #64]
	stp	q0, q0, [x0, #112]
	str	q0, [x0, #144]
	stur	q0, [x0, #158]
	ret

	.globl	_stream_status
	.p2align	2
_stream_status:
	sub	sp, sp, #192
	ldp	q0, q1, [x0, #128]
	ldr	q2, [x0, #160]
	stp	x29, x30, [sp, #176]
	add	x29, sp, #176
	str	q2, [sp, #160]
	stp	q0, q1, [sp, #128]
	ldp	q0, q1, [x0, #64]
	stp	q0, q1, [sp, #64]
	ldp	q2, q0, [x0, #96]
	stp	q2, q0, [sp, #96]
	ldp	q1, q0, [x0]
	stp	q1, q0, [sp]
	ldp	q2, q0, [x0, #32]
	ldr	w0, [sp, #168]
	stp	q2, q0, [sp, #32]
	cbnz	w0, LBB5_14
	ldp	w9, w8, [sp, #96]
	orr	w8, w8, w9
	cbnz	w8, LBB5_9
	ldr	w8, [sp, #148]
	cmp	w8, #17
	b.hi	LBB5_7
	mov	w9, #22528
	movk	w9, #2, lsl #16
	lsr	w9, w9, w8
	tbz	w9, #0, LBB5_7
	ldr	w8, [sp, #144]
	str	wzr, [sp, #148]
	cbz	w8, LBB5_13
	cmp	w8, #64
	sub	w0, w8, #1
	b.hi	LBB5_15
	mov	x8, sp
	mov	w10, #253
	ldrb	w9, [x8, x0]
	sub	w9, w9, #1
	tst	w9, w10
	mov	w9, #7
	mov	w10, #2
	csel	w9, w10, w9, eq
	strb	w9, [x8, x0]
	ldr	w8, [sp, #148]
LBB5_7:
	sub	w9, w8, #4
	cmp	w9, #3
	b.hs	LBB5_10
	mov	w0, #4
	b	LBB5_14
LBB5_9:
	mov	w0, #5
	b	LBB5_14
LBB5_10:
	mov	w0, #6
	cbnz	w8, LBB5_14
	ldr	w8, [sp, #144]
	cbnz	w8, LBB5_14
	ldrb	w8, [sp, #172]
	tbz	w8, #0, LBB5_14
LBB5_13:
	ldr	w0, [sp, #168]
LBB5_14:
	ldp	x29, x30, [sp, #176]
	add	sp, sp, #192
	ret
LBB5_15:
Lloh30:
	adrp	x2, l_alloc_17c2635886f4fbc2ea36dbf6a4113cf0@PAGE
Lloh31:
	add	x2, x2, l_alloc_17c2635886f4fbc2ea36dbf6a4113cf0@PAGEOFF
	mov	w1, #64
	bl	__RNvNtCs9nEiEE0E2Vj_4core9panicking18panic_bounds_check
	.loh AdrpAdd	Lloh30, Lloh31

	.globl	_stream_value
	.p2align	2
_stream_value:
	sub	sp, sp, #192
	ldp	q0, q1, [x0, #128]
	ldr	q2, [x0, #160]
	stp	x29, x30, [sp, #176]
	add	x29, sp, #176
	str	q2, [sp, #160]
	stp	q0, q1, [sp, #128]
	ldp	q0, q1, [x0, #64]
	ldr	w8, [sp, #168]
	stp	q0, q1, [sp, #64]
	ldp	q2, q0, [x0, #96]
	stp	q2, q0, [sp, #96]
	ldp	q1, q0, [x0]
	stp	q1, q0, [sp]
	ldp	q2, q0, [x0, #32]
	stp	q2, q0, [sp, #32]
	cbnz	w8, LBB6_11
	ldp	w9, w8, [sp, #96]
	orr	w9, w8, w9
	cbnz	w9, LBB6_9
	ldr	w9, [sp, #148]
	cmp	w9, #17
	b.hi	LBB6_7
	mov	w8, #22528
	movk	w8, #2, lsl #16
	lsr	w8, w8, w9
	tbz	w8, #0, LBB6_7
	ldr	w8, [sp, #144]
	str	wzr, [sp, #148]
	cbz	w8, LBB6_16
	cmp	w8, #64
	sub	w0, w8, #1
	b.hi	LBB6_17
	mov	x8, sp
	mov	w10, #253
	ldrb	w9, [x8, x0]
	sub	w9, w9, #1
	tst	w9, w10
	mov	w9, #7
	mov	w10, #2
	csel	w9, w10, w9, eq
	strb	w9, [x8, x0]
	ldr	w9, [sp, #148]
LBB6_7:
	sub	w8, w9, #4
	cmp	w8, #3
	b.hs	LBB6_13
	mov	w8, #128
	b	LBB6_10
LBB6_9:
	cmp	w8, #0
	mov	w8, #88
	mov	w9, #80
	csel	x8, x9, x8, eq
LBB6_10:
	mov	x9, sp
	ldr	x8, [x9, x8]
	str	x8, [sp, #136]
LBB6_11:
	ldr	x0, [sp, #136]
LBB6_12:
	ldp	x29, x30, [sp, #176]
	add	sp, sp, #192
	ret
LBB6_13:
	mov	w8, #112
	cbnz	w9, LBB6_10
	ldr	w9, [sp, #144]
	cbnz	w9, LBB6_10
	ldrb	w9, [sp, #172]
	tbz	w9, #0, LBB6_10
LBB6_16:
	ldr	w8, [sp, #168]
	mov	x9, sp
	add	x10, x9, #112
	add	x9, x9, #136
	cmp	w8, #0
	csel	x8, x10, x9, eq
	ldr	x0, [x8]
	b	LBB6_12
LBB6_17:
Lloh32:
	adrp	x2, l_alloc_17c2635886f4fbc2ea36dbf6a4113cf0@PAGE
Lloh33:
	add	x2, x2, l_alloc_17c2635886f4fbc2ea36dbf6a4113cf0@PAGEOFF
	mov	w1, #64
	bl	__RNvNtCs9nEiEE0E2Vj_4core9panicking18panic_bounds_check
	.loh AdrpAdd	Lloh32, Lloh33

	.section	__TEXT,__cstring,cstring_literals
l_alloc_84f9d846ecfb9e37dadbe3e781f512ce:
	.asciz	"/private/tmp/liza-json-bench/benchmarks/json/parser.rs"

	.section	__DATA,__const
	.p2align	3, 0x0
l_alloc_17c2635886f4fbc2ea36dbf6a4113cf0:
	.quad	l_alloc_84f9d846ecfb9e37dadbe3e781f512ce
	.asciz	"6\000\000\000\000\000\000\000\035\000\000\000G\000\000"

	.p2align	3, 0x0
l_alloc_e4ed959f92efea1cff8b4b98f2146f02:
	.quad	l_alloc_84f9d846ecfb9e37dadbe3e781f512ce
	.asciz	"6\000\000\000\000\000\000\000$\000\000\000&\000\000"

	.p2align	3, 0x0
l_alloc_38ab136aad52e23038f13eabe203b7df:
	.quad	l_alloc_84f9d846ecfb9e37dadbe3e781f512ce
	.asciz	"6\000\000\000\000\000\000\000$\000\000\000\036\000\000"

	.p2align	3, 0x0
l_alloc_7fcdd0112aa4a922a81991942fa2013b:
	.quad	l_alloc_84f9d846ecfb9e37dadbe3e781f512ce
	.asciz	"6\000\000\000\000\000\000\000/\000\000\000\n\000\000"

	.p2align	3, 0x0
l_alloc_e67dfff62b8e4ecb323b784eaa923bef:
	.quad	l_alloc_84f9d846ecfb9e37dadbe3e781f512ce
	.asciz	"6\000\000\000\000\000\000\000/\000\000\000\026\000\000"

	.p2align	3, 0x0
l_alloc_2d6ba3368b9b590ce6e8441798328433:
	.quad	l_alloc_84f9d846ecfb9e37dadbe3e781f512ce
	.asciz	"6\000\000\000\000\000\000\000;\000\000\000/\000\000"

	.p2align	3, 0x0
l_alloc_ca89a41573afe1edc3f237491af5f4cb:
	.quad	l_alloc_84f9d846ecfb9e37dadbe3e781f512ce
	.asciz	"6\000\000\000\000\000\000\000M\000\000\000\033\000\000"

	.p2align	3, 0x0
l_alloc_232157ae9decd89c9f2076cdf71110bc:
	.quad	l_alloc_84f9d846ecfb9e37dadbe3e781f512ce
	.asciz	"6\000\000\000\000\000\000\000O\000\000\000&\000\000"

	.p2align	3, 0x0
l_alloc_04fe8135d2319897c873529430c986db:
	.quad	l_alloc_84f9d846ecfb9e37dadbe3e781f512ce
	.asciz	"6\000\000\000\000\000\000\000P\000\000\000J\000\000"

	.p2align	3, 0x0
l_alloc_1fb0c37e44d2c7e7dd89cb8d4cf14241:
	.quad	l_alloc_84f9d846ecfb9e37dadbe3e781f512ce
	.asciz	"6\000\000\000\000\000\000\000Q\000\000\000>\000\000"

	.p2align	3, 0x0
l_alloc_21a6ae3fdeb0c022136d547ac7b9c594:
	.quad	l_alloc_84f9d846ecfb9e37dadbe3e781f512ce
	.asciz	"6\000\000\000\000\000\000\000T\000\000\000G\000\000"

	.p2align	3, 0x0
l_alloc_e0474d9a635040eab39bac01d02d2ec4:
	.quad	l_alloc_84f9d846ecfb9e37dadbe3e781f512ce
	.asciz	"6\000\000\000\000\000\000\000T\000\000\000t\000\000"

	.p2align	3, 0x0
l_alloc_67efdafa9b0dc47c916e8f72fff3e807:
	.quad	l_alloc_84f9d846ecfb9e37dadbe3e781f512ce
	.asciz	"6\000\000\000\000\000\000\000l\000\000\000&\000\000"

.subsections_via_symbols
