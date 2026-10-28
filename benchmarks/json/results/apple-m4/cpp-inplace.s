	.build_version macos, 26, 0	sdk_version 26, 5
	.section	__TEXT,__text,regular,pure_instructions
	.globl	_stream_size                    ; -- Begin function stream_size
	.p2align	2
_stream_size:                           ; @stream_size
	.cfi_startproc
; %bb.0:
	mov	w0, #184                        ; =0xb8
	ret
	.cfi_endproc
                                        ; -- End function
	.globl	_stream_start                   ; -- Begin function stream_start
	.p2align	2
_stream_start:                          ; @stream_start
	.cfi_startproc
; %bb.0:
	movi.2d	v0, #0000000000000000
	mov	w8, #49024                      ; =0xbf80
	stp	xzr, xzr, [x0]
	str	wzr, [x0, #24]
	str	xzr, [x0, #16]
	strh	w8, [x0, #28]
	str	wzr, [x0, #32]
	str	wzr, [x0, #128]
	strb	wzr, [x0, #132]
	str	xzr, [x0, #176]
	stur	q0, [x0, #40]
	stur	q0, [x0, #56]
	stur	q0, [x0, #72]
	stur	q0, [x0, #88]
	stur	q0, [x0, #104]
	stur	xzr, [x0, #117]
	stur	q0, [x0, #136]
	stur	q0, [x0, #152]
	str	wzr, [x0, #168]
	ret
	.cfi_endproc
                                        ; -- End function
	.globl	_stream_feed                    ; -- Begin function stream_feed
	.p2align	2
_stream_feed:                           ; @stream_feed
	.cfi_startproc
; %bb.0:
	stp	x28, x27, [sp, #-96]!           ; 16-byte Folded Spill
	stp	x26, x25, [sp, #16]             ; 16-byte Folded Spill
	stp	x24, x23, [sp, #32]             ; 16-byte Folded Spill
	stp	x22, x21, [sp, #48]             ; 16-byte Folded Spill
	stp	x20, x19, [sp, #64]             ; 16-byte Folded Spill
	stp	x29, x30, [sp, #80]             ; 16-byte Folded Spill
	add	x29, sp, #80
	.cfi_def_cfa w29, 16
	.cfi_offset w30, -8
	.cfi_offset w29, -16
	.cfi_offset w19, -24
	.cfi_offset w20, -32
	.cfi_offset w21, -40
	.cfi_offset w22, -48
	.cfi_offset w23, -56
	.cfi_offset w24, -64
	.cfi_offset w25, -72
	.cfi_offset w26, -80
	.cfi_offset w27, -88
	.cfi_offset w28, -96
	ldr	w8, [x0, #168]
	cbnz	w8, LBB2_161
; %bb.1:
	cbz	w2, LBB2_161
; %bb.2:
	mov	x5, #8193                       ; =0x2001
	mov	w6, #4113                       ; =0x1011
	add	x23, x0, #56
	add	x22, x0, #152
	add	x21, x0, #160
	add	x20, x0, #48
	mov	w24, w2
	mov	w25, #49024                     ; =0xbf80
	mov	w26, #1                         ; =0x1
	mov	w13, #2                         ; =0x2
	mov	w14, #159                       ; =0x9f
	mov	w15, #160                       ; =0xa0
	mov	w16, #3                         ; =0x3
	mov	w17, #143                       ; =0x8f
	mov	w2, #144                        ; =0x90
	mov	w3, #5                          ; =0x5
	mov	w4, #7                          ; =0x7
	movk	x5, #1024, lsl #48
	movk	w6, #5, lsl #16
	mov	w7, #55296                      ; =0xd800
	mov	w19, #4                         ; =0x4
	mov	w28, #56320                     ; =0xdc00
	mov	w30, #11                        ; =0xb
	mov	w12, #13                        ; =0xd
LBB2_3:                                 ; =>This Inner Loop Header: Depth=1
	ldr	w8, [x0, #32]
	cbnz	w8, LBB2_152
; %bb.4:                                ;   in Loop: Header=BB2_3 Depth=1
	ldr	x8, [x0]
	cmn	x8, #1
	b.eq	LBB2_157
; %bb.5:                                ;   in Loop: Header=BB2_3 Depth=1
	ldr	w10, [x0, #24]
	ldrb	w9, [x1]
	cbz	w10, LBB2_9
; %bb.6:                                ;   in Loop: Header=BB2_3 Depth=1
	ldrb	w11, [x0, #28]
	cmp	w9, w11
	b.lo	LBB2_154
; %bb.7:                                ;   in Loop: Header=BB2_3 Depth=1
	ldrb	w11, [x0, #29]
	cmp	w9, w11
	b.hi	LBB2_154
; %bb.8:                                ;   in Loop: Header=BB2_3 Depth=1
	subs	w9, w10, #1
	strh	w25, [x0, #28]
	str	w9, [x0, #24]
	b.ne	LBB2_12
	b	LBB2_10
LBB2_9:                                 ;   in Loop: Header=BB2_3 Depth=1
	str	x8, [x0, #16]
	tbnz	w9, #7, LBB2_30
LBB2_10:                                ;   in Loop: Header=BB2_3 Depth=1
	ldr	x9, [x0, #8]
	cmn	x9, #1
	b.eq	LBB2_158
; %bb.11:                               ;   in Loop: Header=BB2_3 Depth=1
	add	x9, x9, #1
	str	x9, [x0, #8]
LBB2_12:                                ;   in Loop: Header=BB2_3 Depth=1
	add	x9, x8, #1
	ldr	w8, [x0, #128]
	str	x9, [x0]
	ldrb	w27, [x1]
	cmp	w8, #3
	b.le	LBB2_19
; %bb.13:                               ;   in Loop: Header=BB2_3 Depth=1
	cmp	w8, #5
	b.gt	LBB2_22
; %bb.14:                               ;   in Loop: Header=BB2_3 Depth=1
	cmp	w8, #4
	b.eq	LBB2_43
; %bb.15:                               ;   in Loop: Header=BB2_3 Depth=1
	cmp	w8, #5
	b.ne	LBB2_38
; %bb.16:                               ;   in Loop: Header=BB2_3 Depth=1
	cmp	w27, #117
	b.ne	LBB2_163
; %bb.17:                               ;   in Loop: Header=BB2_3 Depth=1
	mov	w8, #6                          ; =0x6
	str	w8, [x0, #128]
LBB2_18:                                ;   in Loop: Header=BB2_3 Depth=1
	str	xzr, [x0, #144]
	b	LBB2_107
LBB2_19:                                ;   in Loop: Header=BB2_3 Depth=1
	cmp	w8, #1
	b.eq	LBB2_32
; %bb.20:                               ;   in Loop: Header=BB2_3 Depth=1
	cmp	w8, #2
	b.eq	LBB2_45
; %bb.21:                               ;   in Loop: Header=BB2_3 Depth=1
	cmp	w8, #3
	b.eq	LBB2_27
	b	LBB2_38
LBB2_22:                                ;   in Loop: Header=BB2_3 Depth=1
	cmp	w8, #6
	b.eq	LBB2_27
; %bb.23:                               ;   in Loop: Header=BB2_3 Depth=1
	cmp	w8, #20
	b.ne	LBB2_38
; %bb.24:                               ;   in Loop: Header=BB2_3 Depth=1
	ldp	w9, w8, [x0, #136]
	mov	x14, x21
	mov	x21, x22
	cmp	w9, #2
	b.eq	LBB2_64
; %bb.25:                               ;   in Loop: Header=BB2_3 Depth=1
	cmp	w9, #1
	b.ne	LBB2_65
; %bb.26:                               ;   in Loop: Header=BB2_3 Depth=1
	cmp	w8, #1
	mov	w10, #114                       ; =0x72
	mov	w11, #117                       ; =0x75
	csel	w10, w10, wzr, eq
	cmp	w8, #2
	csel	w10, w11, w10, eq
	cmp	w8, #3
	mov	w11, #101                       ; =0x65
	csel	w11, w11, w10, eq
	b	LBB2_66
LBB2_27:                                ;   in Loop: Header=BB2_3 Depth=1
	sub	w9, w27, #48
	cmp	w9, #9
	b.ls	LBB2_55
; %bb.28:                               ;   in Loop: Header=BB2_3 Depth=1
	sub	w9, w27, #65
	cmp	w9, #5
	b.hi	LBB2_53
; %bb.29:                               ;   in Loop: Header=BB2_3 Depth=1
	sub	w9, w27, #55
	b	LBB2_55
LBB2_30:                                ;   in Loop: Header=BB2_3 Depth=1
	sub	w10, w9, #194
	strh	w25, [x0, #28]
	cmp	w10, #29
	b.hi	LBB2_49
; %bb.31:                               ;   in Loop: Header=BB2_3 Depth=1
	str	w26, [x0, #24]
	b	LBB2_12
LBB2_32:                                ;   in Loop: Header=BB2_3 Depth=1
	cmp	w27, #32
	b.lo	LBB2_164
; %bb.33:                               ;   in Loop: Header=BB2_3 Depth=1
	cmp	w27, #92
	b.eq	LBB2_72
; %bb.34:                               ;   in Loop: Header=BB2_3 Depth=1
	cmp	w27, #34
	b.ne	LBB2_107
; %bb.35:                               ;   in Loop: Header=BB2_3 Depth=1
	ldrb	w9, [x0, #132]
	ldr	w8, [x0, #120]
	str	wzr, [x0, #128]
	cmp	w9, #1
	b.ne	LBB2_81
; %bb.36:                               ;   in Loop: Header=BB2_3 Depth=1
	sub	w8, w8, #1
	cmp	w8, #64
	b.hs	LBB2_168
; %bb.37:                               ;   in Loop: Header=BB2_3 Depth=1
	strb	w3, [x23, w8, uxtw]
	b	LBB2_107
LBB2_38:                                ;   in Loop: Header=BB2_3 Depth=1
	sub	w9, w8, #10
	cmp	w9, #7
	b.hi	LBB2_105
; %bb.39:                               ;   in Loop: Header=BB2_3 Depth=1
	sub	w9, w27, #48
	cmp	w9, #9
	b.hi	LBB2_77
; %bb.40:                               ;   in Loop: Header=BB2_3 Depth=1
	cmp	w8, #10
	b.eq	LBB2_89
; %bb.41:                               ;   in Loop: Header=BB2_3 Depth=1
	cmp	w8, #13
	b.eq	LBB2_88
; %bb.42:                               ;   in Loop: Header=BB2_3 Depth=1
	cmp	w8, #11
	b.ne	LBB2_90
	b	LBB2_166
LBB2_43:                                ;   in Loop: Header=BB2_3 Depth=1
	cmp	w27, #92
	b.ne	LBB2_163
; %bb.44:                               ;   in Loop: Header=BB2_3 Depth=1
	str	w3, [x0, #128]
	b	LBB2_107
LBB2_45:                                ;   in Loop: Header=BB2_3 Depth=1
	sub	w8, w27, #98
	cmp	w8, #19
	b.hi	LBB2_61
; %bb.46:                               ;   in Loop: Header=BB2_3 Depth=1
	lsl	w9, w26, w8
	tst	w9, w6
	b.ne	LBB2_63
; %bb.47:                               ;   in Loop: Header=BB2_3 Depth=1
	cmp	w8, #19
	b.ne	LBB2_61
; %bb.48:                               ;   in Loop: Header=BB2_3 Depth=1
	str	w16, [x0, #128]
	b	LBB2_18
LBB2_49:                                ;   in Loop: Header=BB2_3 Depth=1
	and	w10, w9, #0xf0
	cmp	w10, #224
	b.ne	LBB2_73
; %bb.50:                               ;   in Loop: Header=BB2_3 Depth=1
	cmp	w9, #237
	str	w13, [x0, #24]
	b.eq	LBB2_86
; %bb.51:                               ;   in Loop: Header=BB2_3 Depth=1
	cmp	w9, #224
	b.ne	LBB2_12
; %bb.52:                               ;   in Loop: Header=BB2_3 Depth=1
	strb	w15, [x0, #28]
	b	LBB2_12
LBB2_53:                                ;   in Loop: Header=BB2_3 Depth=1
	sub	w9, w27, #97
	cmp	w9, #5
	b.hi	LBB2_162
; %bb.54:                               ;   in Loop: Header=BB2_3 Depth=1
	sub	w9, w27, #87
LBB2_55:                                ;   in Loop: Header=BB2_3 Depth=1
	cmp	w9, #16
	b.eq	LBB2_162
; %bb.56:                               ;   in Loop: Header=BB2_3 Depth=1
	ldp	w11, w10, [x0, #144]
	add	w9, w9, w10, lsl #4
	add	w10, w11, #1
	cmp	w10, #4
	stp	w10, w9, [x0, #144]
	b.ne	LBB2_107
; %bb.57:                               ;   in Loop: Header=BB2_3 Depth=1
	cmp	w8, #6
	b.ne	LBB2_59
; %bb.58:                               ;   in Loop: Header=BB2_3 Depth=1
	sub	w8, w9, #14, lsl #12            ; =57344
	cmn	w8, #1024
	b.hs	LBB2_63
	b	LBB2_163
LBB2_59:                                ;   in Loop: Header=BB2_3 Depth=1
	and	w8, w9, #0xfffffc00
	cmp	w8, w7
	b.eq	LBB2_80
; %bb.60:                               ;   in Loop: Header=BB2_3 Depth=1
	cmp	w8, w28
	b.ne	LBB2_63
	b	LBB2_165
LBB2_61:                                ;   in Loop: Header=BB2_3 Depth=1
	sub	w9, w27, #34
	mov	w8, #3                          ; =0x3
	cmp	w9, #58
	b.hi	LBB2_160
; %bb.62:                               ;   in Loop: Header=BB2_3 Depth=1
	lsl	x9, x26, x9
	tst	x9, x5
	b.eq	LBB2_160
LBB2_63:                                ;   in Loop: Header=BB2_3 Depth=1
	str	w26, [x0, #128]
	b	LBB2_107
LBB2_64:                                ;   in Loop: Header=BB2_3 Depth=1
	cmp	w8, #1
	mov	w10, #97                        ; =0x61
	mov	w11, #108                       ; =0x6c
	csel	w10, w10, wzr, eq
	cmp	w8, #2
	csel	w10, w11, w10, eq
	cmp	w8, #3
	mov	w11, #115                       ; =0x73
	csel	w10, w11, w10, eq
	cmp	w8, #4
	mov	w11, #101                       ; =0x65
	csel	w11, w11, w10, eq
	mov	w10, #5                         ; =0x5
	b	LBB2_67
LBB2_65:                                ;   in Loop: Header=BB2_3 Depth=1
	mov	w11, wzr
LBB2_66:                                ;   in Loop: Header=BB2_3 Depth=1
	mov	w10, #4                         ; =0x4
LBB2_67:                                ;   in Loop: Header=BB2_3 Depth=1
	cmp	w8, #1
	mov	w12, #108                       ; =0x6c
	mov	w22, #117                       ; =0x75
	csel	w12, w22, w12, eq
	cmp	w9, #3
	csel	w9, w12, w11, eq
	cmp	w27, w9
	b.ne	LBB2_164
; %bb.68:                               ;   in Loop: Header=BB2_3 Depth=1
	add	w8, w8, #1
	mov	w12, #13                        ; =0xd
	mov	x22, x21
	cmp	w8, w10
	mov	x21, x14
	mov	w14, #159                       ; =0x9f
	str	w8, [x0, #140]
	b.ne	LBB2_107
; %bb.69:                               ;   in Loop: Header=BB2_3 Depth=1
	ldr	w8, [x0, #120]
	str	wzr, [x0, #128]
	cbz	w8, LBB2_82
LBB2_70:                                ;   in Loop: Header=BB2_3 Depth=1
	sub	w8, w8, #1
	cmp	w8, #64
	b.hs	LBB2_168
; %bb.71:                               ;   in Loop: Header=BB2_3 Depth=1
	ldrb	w9, [x23, w8, uxtw]
	and	w9, w9, #0xfffffffd
	cmp	w9, #1
	csel	w9, w13, w4, eq
	strb	w9, [x23, w8, uxtw]
	b	LBB2_107
LBB2_72:                                ;   in Loop: Header=BB2_3 Depth=1
	ldr	x8, [x0, #48]
	str	w13, [x0, #128]
	str	x8, [x0, #152]
	b	LBB2_107
LBB2_73:                                ;   in Loop: Header=BB2_3 Depth=1
	sub	w10, w9, #240
	cmp	w10, #4
	b.hi	LBB2_155
; %bb.74:                               ;   in Loop: Header=BB2_3 Depth=1
	cmp	w9, #244
	str	w16, [x0, #24]
	b.eq	LBB2_87
; %bb.75:                               ;   in Loop: Header=BB2_3 Depth=1
	cmp	w9, #240
	b.ne	LBB2_12
; %bb.76:                               ;   in Loop: Header=BB2_3 Depth=1
	strb	w2, [x0, #28]
	b	LBB2_12
LBB2_77:                                ;   in Loop: Header=BB2_3 Depth=1
	cmp	w8, #11
	b.ne	LBB2_83
; %bb.78:                               ;   in Loop: Header=BB2_3 Depth=1
	cmp	w27, #46
	b.eq	LBB2_85
; %bb.79:                               ;   in Loop: Header=BB2_3 Depth=1
	and	w8, w27, #0xffffffdf
	cmp	w8, #69
	b.eq	LBB2_95
	b	LBB2_102
LBB2_80:                                ;   in Loop: Header=BB2_3 Depth=1
	ldr	x8, [x0, #152]
	str	w19, [x0, #128]
	str	x8, [x0, #160]
	b	LBB2_107
LBB2_81:                                ;   in Loop: Header=BB2_3 Depth=1
	cbnz	w8, LBB2_70
LBB2_82:                                ;   in Loop: Header=BB2_3 Depth=1
	strb	w26, [x0, #124]
	b	LBB2_107
LBB2_83:                                ;   in Loop: Header=BB2_3 Depth=1
	cmp	w27, #46
	b.ne	LBB2_92
; %bb.84:                               ;   in Loop: Header=BB2_3 Depth=1
	cmp	w8, #12
	b.ne	LBB2_92
LBB2_85:                                ;   in Loop: Header=BB2_3 Depth=1
	str	w12, [x0, #128]
	b	LBB2_107
LBB2_86:                                ;   in Loop: Header=BB2_3 Depth=1
	strb	w14, [x0, #29]
	b	LBB2_12
LBB2_87:                                ;   in Loop: Header=BB2_3 Depth=1
	strb	w17, [x0, #29]
	b	LBB2_12
LBB2_88:                                ;   in Loop: Header=BB2_3 Depth=1
	mov	w8, #14                         ; =0xe
	str	w8, [x0, #128]
	b	LBB2_107
LBB2_89:                                ;   in Loop: Header=BB2_3 Depth=1
	cmp	w27, #48
	cinc	w8, w30, ne
	str	w8, [x0, #128]
LBB2_90:                                ;   in Loop: Header=BB2_3 Depth=1
	sub	w8, w8, #15
	cmp	w8, #1
	b.hi	LBB2_107
; %bb.91:                               ;   in Loop: Header=BB2_3 Depth=1
	mov	w8, #17                         ; =0x11
	str	w8, [x0, #128]
	b	LBB2_107
LBB2_92:                                ;   in Loop: Header=BB2_3 Depth=1
	cmp	w8, #16
	b.hi	LBB2_102
; %bb.93:                               ;   in Loop: Header=BB2_3 Depth=1
	lsl	w9, w26, w8
	mov	w10, #22528                     ; =0x5800
	tst	w9, w10
	b.eq	LBB2_96
; %bb.94:                               ;   in Loop: Header=BB2_3 Depth=1
	and	w9, w27, #0xffffffdf
	cmp	w9, #69
	b.ne	LBB2_100
LBB2_95:                                ;   in Loop: Header=BB2_3 Depth=1
	mov	w8, #15                         ; =0xf
	str	w8, [x0, #128]
	b	LBB2_107
LBB2_96:                                ;   in Loop: Header=BB2_3 Depth=1
	cmp	w8, #15
	b.ne	LBB2_101
; %bb.97:                               ;   in Loop: Header=BB2_3 Depth=1
	cmp	w27, #45
	b.eq	LBB2_99
; %bb.98:                               ;   in Loop: Header=BB2_3 Depth=1
	cmp	w27, #43
	b.ne	LBB2_166
LBB2_99:                                ;   in Loop: Header=BB2_3 Depth=1
	mov	w8, #16                         ; =0x10
	str	w8, [x0, #128]
	b	LBB2_107
LBB2_100:                               ;   in Loop: Header=BB2_3 Depth=1
	cmp	w8, #13
	b.ne	LBB2_102
	b	LBB2_166
LBB2_101:                               ;   in Loop: Header=BB2_3 Depth=1
	mov	w8, #9216                       ; =0x2400
	movk	w8, #1, lsl #16
	tst	w9, w8
	b.ne	LBB2_166
LBB2_102:                               ;   in Loop: Header=BB2_3 Depth=1
	mov	x28, x1
	cmp	w27, #44
	b.hi	LBB2_127
; %bb.103:                              ;   in Loop: Header=BB2_3 Depth=1
	lsl	x8, x26, x27
	mov	x9, #9728                       ; =0x2600
	movk	x9, #4097, lsl #32
	tst	x8, x9
	b.eq	LBB2_127
LBB2_104:                               ;   in Loop: Header=BB2_3 Depth=1
	str	wzr, [x0, #128]
	mov	x19, x0
	bl	__ZL4doneR5State
	mov	x5, #8193                       ; =0x2001
	mov	w6, #4113                       ; =0x1011
	mov	x0, x19
	mov	x1, x28
	mov	w13, #2                         ; =0x2
	mov	w14, #159                       ; =0x9f
	mov	w15, #160                       ; =0xa0
	mov	w16, #3                         ; =0x3
	mov	w17, #143                       ; =0x8f
	mov	w2, #144                        ; =0x90
	mov	w3, #5                          ; =0x5
	mov	w4, #7                          ; =0x7
	movk	x5, #1024, lsl #48
	movk	w6, #5, lsl #16
	mov	w7, #55296                      ; =0xd800
	mov	w19, #4                         ; =0x4
	mov	w28, #56320                     ; =0xdc00
	mov	w30, #11                        ; =0xb
	mov	w12, #13                        ; =0xd
LBB2_105:                               ;   in Loop: Header=BB2_3 Depth=1
	cmp	w27, #32
	b.hi	LBB2_109
; %bb.106:                              ;   in Loop: Header=BB2_3 Depth=1
	lsl	x8, x26, x27
	mov	x9, #9728                       ; =0x2600
	movk	x9, #1, lsl #32
	tst	x8, x9
	b.eq	LBB2_109
LBB2_107:                               ;   in Loop: Header=BB2_3 Depth=1
	ldr	w8, [x0, #168]
	cbnz	w8, LBB2_161
; %bb.108:                              ;   in Loop: Header=BB2_3 Depth=1
	ldr	x8, [x20]
	subs	x24, x24, #1
	add	x1, x1, #1
	add	x8, x8, #1
	str	x8, [x20]
	b.ne	LBB2_3
	b	LBB2_161
LBB2_109:                               ;   in Loop: Header=BB2_3 Depth=1
	ldr	w8, [x0, #120]
	cbz	w8, LBB2_114
; %bb.110:                              ;   in Loop: Header=BB2_3 Depth=1
	sub	w10, w8, #1
	cmp	w10, #64
	b.hs	LBB2_168
; %bb.111:                              ;   in Loop: Header=BB2_3 Depth=1
	ldrb	w9, [x23, w10, uxtw]
	cmp	w27, #93
	b.ne	LBB2_115
; %bb.112:                              ;   in Loop: Header=BB2_3 Depth=1
	sub	w11, w9, #1
	cmp	w11, #1
	b.hi	LBB2_115
; %bb.113:                              ;   in Loop: Header=BB2_3 Depth=1
	str	w10, [x0, #120]
	b	LBB2_107
LBB2_114:                               ;   in Loop: Header=BB2_3 Depth=1
	mov	w9, wzr
LBB2_115:                               ;   in Loop: Header=BB2_3 Depth=1
	cmp	w27, #125
	b.ne	LBB2_119
; %bb.116:                              ;   in Loop: Header=BB2_3 Depth=1
	cmp	w9, #7
	b.eq	LBB2_118
; %bb.117:                              ;   in Loop: Header=BB2_3 Depth=1
	cmp	w9, #4
	b.ne	LBB2_119
LBB2_118:                               ;   in Loop: Header=BB2_3 Depth=1
	sub	w8, w8, #1
	str	w8, [x0, #120]
	b	LBB2_107
LBB2_119:                               ;   in Loop: Header=BB2_3 Depth=1
	cmp	w9, #4
	b.le	LBB2_123
; %bb.120:                              ;   in Loop: Header=BB2_3 Depth=1
	cmp	w9, #5
	b.eq	LBB2_132
; %bb.121:                              ;   in Loop: Header=BB2_3 Depth=1
	cmp	w9, #8
	b.eq	LBB2_125
; %bb.122:                              ;   in Loop: Header=BB2_3 Depth=1
	cmp	w9, #7
	b.eq	LBB2_129
	b	LBB2_135
LBB2_123:                               ;   in Loop: Header=BB2_3 Depth=1
	cmp	w9, #2
	b.eq	LBB2_129
; %bb.124:                              ;   in Loop: Header=BB2_3 Depth=1
	cmp	w9, #4
	b.ne	LBB2_135
LBB2_125:                               ;   in Loop: Header=BB2_3 Depth=1
	cmp	w27, #34
	b.ne	LBB2_164
; %bb.126:                              ;   in Loop: Header=BB2_3 Depth=1
	strb	w26, [x0, #132]
	str	w26, [x0, #128]
	b	LBB2_107
LBB2_127:                               ;   in Loop: Header=BB2_3 Depth=1
	cmp	w27, #125
	b.eq	LBB2_104
; %bb.128:                              ;   in Loop: Header=BB2_3 Depth=1
	cmp	w27, #93
	b.eq	LBB2_104
	b	LBB2_166
LBB2_129:                               ;   in Loop: Header=BB2_3 Depth=1
	cmp	w27, #44
	b.ne	LBB2_164
; %bb.130:                              ;   in Loop: Header=BB2_3 Depth=1
	sub	w8, w8, #1
	cmp	w8, #64
	b.hs	LBB2_168
; %bb.131:                              ;   in Loop: Header=BB2_3 Depth=1
	cmp	w9, #2
	mov	w9, #8                          ; =0x8
	csel	w9, w16, w9, eq
	strb	w9, [x23, w8, uxtw]
	b	LBB2_107
LBB2_132:                               ;   in Loop: Header=BB2_3 Depth=1
	cmp	w27, #58
	b.ne	LBB2_164
; %bb.133:                              ;   in Loop: Header=BB2_3 Depth=1
	sub	w8, w8, #1
	cmp	w8, #64
	b.hs	LBB2_168
; %bb.134:                              ;   in Loop: Header=BB2_3 Depth=1
	mov	w9, #6                          ; =0x6
	strb	w9, [x23, w8, uxtw]
	b	LBB2_107
LBB2_135:                               ;   in Loop: Header=BB2_3 Depth=1
	cbnz	w8, LBB2_137
; %bb.136:                              ;   in Loop: Header=BB2_3 Depth=1
	ldrb	w9, [x0, #124]
	tbnz	w9, #0, LBB2_164
LBB2_137:                               ;   in Loop: Header=BB2_3 Depth=1
	cmp	w27, #90
	b.gt	LBB2_141
; %bb.138:                              ;   in Loop: Header=BB2_3 Depth=1
	cmp	w27, #34
	b.eq	LBB2_148
; %bb.139:                              ;   in Loop: Header=BB2_3 Depth=1
	cmp	w27, #45
	b.ne	LBB2_146
; %bb.140:                              ;   in Loop: Header=BB2_3 Depth=1
	mov	w8, #10                         ; =0xa
	str	w8, [x0, #128]
	b	LBB2_107
LBB2_141:                               ;   in Loop: Header=BB2_3 Depth=1
	cmp	w27, #123
	b.eq	LBB2_143
; %bb.142:                              ;   in Loop: Header=BB2_3 Depth=1
	cmp	w27, #91
	b.ne	LBB2_146
LBB2_143:                               ;   in Loop: Header=BB2_3 Depth=1
	cmp	w8, #64
	b.eq	LBB2_167
; %bb.144:                              ;   in Loop: Header=BB2_3 Depth=1
	mov	x28, x1
	mov	x19, x0
	bl	__ZL4doneR5State
	ldr	w8, [x19, #120]
	cmp	w8, #64
	b.hs	LBB2_168
; %bb.145:                              ;   in Loop: Header=BB2_3 Depth=1
	mov	x0, x19
	cmp	w27, #91
	mov	w19, #4                         ; =0x4
	csinc	w9, w19, wzr, ne
	strb	w9, [x23, x8]
	mov	x5, #8193                       ; =0x2001
	ldr	w8, [x0, #120]
	mov	w6, #4113                       ; =0x1011
	mov	x1, x28
	mov	w13, #2                         ; =0x2
	mov	w14, #159                       ; =0x9f
	mov	w15, #160                       ; =0xa0
	add	w8, w8, #1
	mov	w16, #3                         ; =0x3
	mov	w17, #143                       ; =0x8f
	str	w8, [x0, #120]
	mov	w2, #144                        ; =0x90
	mov	w3, #5                          ; =0x5
	mov	w4, #7                          ; =0x7
	movk	x5, #1024, lsl #48
	movk	w6, #5, lsl #16
	mov	w7, #55296                      ; =0xd800
	mov	w28, #56320                     ; =0xdc00
	mov	w30, #11                        ; =0xb
	mov	w12, #13                        ; =0xd
	b	LBB2_107
LBB2_146:                               ;   in Loop: Header=BB2_3 Depth=1
	sub	w8, w27, #48
	cmp	w8, #9
	b.hi	LBB2_149
; %bb.147:                              ;   in Loop: Header=BB2_3 Depth=1
	cmp	w27, #48
	cinc	w8, w30, ne
	str	w8, [x0, #128]
	b	LBB2_107
LBB2_148:                               ;   in Loop: Header=BB2_3 Depth=1
	strb	wzr, [x0, #132]
	str	w26, [x0, #128]
	b	LBB2_107
LBB2_149:                               ;   in Loop: Header=BB2_3 Depth=1
	sub	w9, w27, #102
	mov	w8, #1                          ; =0x1
	cmp	w9, #14
	b.hi	LBB2_160
; %bb.150:                              ;   in Loop: Header=BB2_3 Depth=1
	lsl	w9, w26, w9
	mov	w10, #16641                     ; =0x4101
	tst	w9, w10
	b.eq	LBB2_160
; %bb.151:                              ;   in Loop: Header=BB2_3 Depth=1
	cmp	w27, #102
	mov	w8, #20                         ; =0x14
	str	w8, [x0, #128]
	cinc	w8, w13, ne
	cmp	w27, #116
	csinc	w8, w8, wzr, ne
	stp	w8, w26, [x0, #136]
	b	LBB2_107
LBB2_152:
	cmp	w8, #1
	b.eq	LBB2_156
; %bb.153:
	mov	w8, #8                          ; =0x8
	b	LBB2_159
LBB2_154:
	ldr	x8, [x0, #16]
LBB2_155:
	mov	w9, #1                          ; =0x1
	str	w9, [x0, #32]
	str	x8, [x0, #40]
LBB2_156:
	mov	w8, #5                          ; =0x5
	b	LBB2_159
LBB2_157:
	mov	w8, #2                          ; =0x2
	mov	x9, #-1                         ; =0xffffffffffffffff
	str	w8, [x0, #32]
	mov	w8, #8                          ; =0x8
	str	x9, [x0, #40]
	b	LBB2_159
LBB2_158:
	mov	w9, #2                          ; =0x2
	str	x8, [x0, #40]
	mov	w8, #8                          ; =0x8
	str	w9, [x0, #32]
LBB2_159:
	add	x20, x0, #40
LBB2_160:
	ldr	x9, [x20]
	str	w8, [x0, #168]
	str	x9, [x0, #176]
LBB2_161:
	ldp	x29, x30, [sp, #80]             ; 16-byte Folded Reload
	ldp	x20, x19, [sp, #64]             ; 16-byte Folded Reload
	ldp	x22, x21, [sp, #48]             ; 16-byte Folded Reload
	ldp	x24, x23, [sp, #32]             ; 16-byte Folded Reload
	ldp	x26, x25, [sp, #16]             ; 16-byte Folded Reload
	ldp	x28, x27, [sp], #96             ; 16-byte Folded Reload
	ret
LBB2_162:
	mov	w8, #3                          ; =0x3
	b	LBB2_160
LBB2_163:
	mov	w8, #4                          ; =0x4
	mov	x20, x21
	b	LBB2_160
LBB2_164:
	mov	w8, #1                          ; =0x1
	b	LBB2_160
LBB2_165:
	mov	w8, #4                          ; =0x4
	mov	x20, x22
	b	LBB2_160
LBB2_166:
	mov	w8, #2                          ; =0x2
	b	LBB2_160
LBB2_167:
	mov	w8, #7                          ; =0x7
	b	LBB2_160
LBB2_168:
Lloh0:
	adrp	x0, l_.str@PAGE
Lloh1:
	add	x0, x0, l_.str@PAGEOFF
	bl	__ZNSt3__120__throw_out_of_rangeB9nqe210106EPKc
	.loh AdrpAdd	Lloh0, Lloh1
	.cfi_endproc
                                        ; -- End function
	.globl	_stream_pending                 ; -- Begin function stream_pending
	.p2align	2
_stream_pending:                        ; @stream_pending
	.cfi_startproc
; %bb.0:
	ldr	w0, [x0, #168]
	ret
	.cfi_endproc
                                        ; -- End function
	.globl	_stream_status                  ; -- Begin function stream_status
	.p2align	2
_stream_status:                         ; @stream_status
	.cfi_startproc
; %bb.0:
	sub	sp, sp, #416
	stp	x28, x27, [sp, #384]            ; 16-byte Folded Spill
	stp	x29, x30, [sp, #400]            ; 16-byte Folded Spill
	add	x29, sp, #400
	.cfi_def_cfa w29, 16
	.cfi_offset w30, -8
	.cfi_offset w29, -16
	.cfi_offset w27, -24
	.cfi_offset w28, -32
Lloh2:
	adrp	x8, ___stack_chk_guard@GOTPAGE
Lloh3:
	ldr	x8, [x8, ___stack_chk_guard@GOTPAGEOFF]
Lloh4:
	ldr	x8, [x8]
	stur	x8, [x29, #-24]
	ldp	q0, q1, [x0, #128]
	ldr	q2, [x0, #160]
	ldr	x8, [x0, #176]
	str	q2, [sp, #160]
	stp	q0, q1, [sp, #128]
	ldp	q0, q1, [x0, #64]
	str	x8, [sp, #176]
	add	x8, sp, #192
	stp	q0, q1, [sp, #64]
	ldp	q2, q0, [x0, #96]
	stp	q2, q0, [sp, #96]
	ldp	q1, q0, [x0]
	stp	q1, q0, [sp]
	ldp	q2, q0, [x0, #32]
	mov	x0, sp
	stp	q2, q0, [sp, #32]
	bl	__ZL6finish5State
Lloh5:
	adrp	x8, ___stack_chk_guard@GOTPAGE
Lloh6:
	ldr	x8, [x8, ___stack_chk_guard@GOTPAGEOFF]
	ldr	w0, [sp, #360]
	ldur	x9, [x29, #-24]
Lloh7:
	ldr	x8, [x8]
	cmp	x8, x9
	b.ne	LBB4_2
; %bb.1:
	ldp	x29, x30, [sp, #400]            ; 16-byte Folded Reload
	ldp	x28, x27, [sp, #384]            ; 16-byte Folded Reload
	add	sp, sp, #416
	ret
LBB4_2:
	bl	___stack_chk_fail
	.loh AdrpLdrGotLdr	Lloh5, Lloh6, Lloh7
	.loh AdrpLdrGotLdr	Lloh2, Lloh3, Lloh4
	.cfi_endproc
                                        ; -- End function
	.p2align	2                               ; -- Begin function _ZL6finish5State
__ZL6finish5State:                      ; @_ZL6finish5State
	.cfi_startproc
; %bb.0:
	ldr	w9, [x0, #168]
	cbnz	w9, LBB5_18
; %bb.1:
	ldr	w9, [x0, #32]
	cbz	w9, LBB5_3
; %bb.2:
	mov	w9, #5                          ; =0x5
	mov	w10, #40                        ; =0x28
	b	LBB5_17
LBB5_3:
	ldr	w9, [x0, #24]
	cbz	w9, LBB5_5
; %bb.4:
	mov	w9, #5                          ; =0x5
	mov	w10, #16                        ; =0x10
	b	LBB5_17
LBB5_5:
	ldr	w9, [x0, #128]
	cmp	w9, #17
	b.hi	LBB5_10
; %bb.6:
	mov	w10, #1                         ; =0x1
	mov	w11, #22528                     ; =0x5800
	lsl	w10, w10, w9
	movk	w11, #2, lsl #16
	tst	w10, w11
	b.eq	LBB5_10
; %bb.7:
	ldr	w9, [x0, #120]
	str	wzr, [x0, #128]
	cbz	w9, LBB5_12
; %bb.8:
	sub	w9, w9, #1
	cmp	w9, #64
	b.hs	LBB5_19
; %bb.9:
	add	x9, x0, w9, uxtw
	mov	w11, #2                         ; =0x2
	ldrb	w10, [x9, #56]
	and	w10, w10, #0xfffffffd
	cmp	w10, #1
	mov	w10, #7                         ; =0x7
	csel	w10, w11, w10, eq
	strb	w10, [x9, #56]
	ldr	w9, [x0, #128]
LBB5_10:
	sub	w10, w9, #4
	cmp	w10, #3
	b.hs	LBB5_13
; %bb.11:
	mov	w9, #4                          ; =0x4
	mov	w10, #160                       ; =0xa0
	b	LBB5_17
LBB5_12:
	mov	w9, #1                          ; =0x1
	strb	w9, [x0, #124]
	b	LBB5_14
LBB5_13:
	cbnz	w9, LBB5_16
LBB5_14:
	ldr	w9, [x0, #120]
	cbnz	w9, LBB5_16
; %bb.15:
	ldrb	w9, [x0, #124]
	tbnz	w9, #0, LBB5_18
LBB5_16:
	mov	w9, #6                          ; =0x6
	mov	w10, #48                        ; =0x30
LBB5_17:
	ldr	x10, [x0, x10]
	str	w9, [x0, #168]
	str	x10, [x0, #176]
LBB5_18:
	ldp	q0, q1, [x0, #128]
	ldr	q2, [x0, #160]
	ldr	x9, [x0, #176]
	str	q2, [x8, #160]
	stp	q0, q1, [x8, #128]
	ldp	q0, q1, [x0, #64]
	str	x9, [x8, #176]
	stp	q0, q1, [x8, #64]
	ldp	q2, q0, [x0, #96]
	stp	q2, q0, [x8, #96]
	ldp	q1, q0, [x0]
	stp	q1, q0, [x8]
	ldp	q2, q0, [x0, #32]
	stp	q2, q0, [x8, #32]
	ret
LBB5_19:
	stp	x29, x30, [sp, #-16]!           ; 16-byte Folded Spill
	mov	x29, sp
	.cfi_def_cfa w29, 16
	.cfi_offset w30, -8
	.cfi_offset w29, -16
Lloh8:
	adrp	x0, l_.str@PAGE
Lloh9:
	add	x0, x0, l_.str@PAGEOFF
	bl	__ZNSt3__120__throw_out_of_rangeB9nqe210106EPKc
	.loh AdrpAdd	Lloh8, Lloh9
	.cfi_endproc
                                        ; -- End function
	.globl	_stream_value                   ; -- Begin function stream_value
	.p2align	2
_stream_value:                          ; @stream_value
	.cfi_startproc
; %bb.0:
	sub	sp, sp, #416
	stp	x20, x19, [sp, #384]            ; 16-byte Folded Spill
	stp	x29, x30, [sp, #400]            ; 16-byte Folded Spill
	add	x29, sp, #400
	.cfi_def_cfa w29, 16
	.cfi_offset w30, -8
	.cfi_offset w29, -16
	.cfi_offset w19, -24
	.cfi_offset w20, -32
Lloh10:
	adrp	x8, ___stack_chk_guard@GOTPAGE
	add	x19, sp, #192
Lloh11:
	ldr	x8, [x8, ___stack_chk_guard@GOTPAGEOFF]
Lloh12:
	ldr	x8, [x8]
	stur	x8, [x29, #-24]
	ldp	q0, q1, [x0, #128]
	ldr	q2, [x0, #160]
	ldr	x8, [x0, #176]
	str	q2, [sp, #160]
	stp	q0, q1, [sp, #128]
	ldp	q0, q1, [x0, #64]
	str	x8, [sp, #176]
	add	x8, sp, #192
	stp	q0, q1, [sp, #64]
	ldp	q2, q0, [x0, #96]
	stp	q2, q0, [sp, #96]
	ldp	q1, q0, [x0]
	stp	q1, q0, [sp]
	ldp	q2, q0, [x0, #32]
	mov	x0, sp
	stp	q2, q0, [sp, #32]
	bl	__ZL6finish5State
	ldr	w8, [sp, #360]
	add	x9, x19, #176
	add	x10, x19, #48
	cmp	w8, #0
	csel	x8, x10, x9, eq
Lloh13:
	adrp	x9, ___stack_chk_guard@GOTPAGE
Lloh14:
	ldr	x9, [x9, ___stack_chk_guard@GOTPAGEOFF]
	ldr	x0, [x8]
	ldur	x8, [x29, #-24]
Lloh15:
	ldr	x9, [x9]
	cmp	x9, x8
	b.ne	LBB6_2
; %bb.1:
	ldp	x29, x30, [sp, #400]            ; 16-byte Folded Reload
	ldp	x20, x19, [sp, #384]            ; 16-byte Folded Reload
	add	sp, sp, #416
	ret
LBB6_2:
	bl	___stack_chk_fail
	.loh AdrpLdrGotLdr	Lloh13, Lloh14, Lloh15
	.loh AdrpLdrGotLdr	Lloh10, Lloh11, Lloh12
	.cfi_endproc
                                        ; -- End function
	.p2align	2                               ; -- Begin function _ZL4doneR5State
__ZL4doneR5State:                       ; @_ZL4doneR5State
	.cfi_startproc
; %bb.0:
	ldr	w8, [x0, #120]
	cbz	w8, LBB7_3
; %bb.1:
	sub	w8, w8, #1
	cmp	w8, #64
	b.hs	LBB7_4
; %bb.2:
	add	x8, x0, w8, uxtw
	mov	w10, #2                         ; =0x2
	ldrb	w9, [x8, #56]
	and	w9, w9, #0xfffffffd
	cmp	w9, #1
	mov	w9, #7                          ; =0x7
	csel	w9, w10, w9, eq
	strb	w9, [x8, #56]
	ret
LBB7_3:
	mov	w8, #1                          ; =0x1
	strb	w8, [x0, #124]
	ret
LBB7_4:
	stp	x29, x30, [sp, #-16]!           ; 16-byte Folded Spill
	mov	x29, sp
	.cfi_def_cfa w29, 16
	.cfi_offset w30, -8
	.cfi_offset w29, -16
Lloh16:
	adrp	x0, l_.str@PAGE
Lloh17:
	add	x0, x0, l_.str@PAGEOFF
	bl	__ZNSt3__120__throw_out_of_rangeB9nqe210106EPKc
	.loh AdrpAdd	Lloh16, Lloh17
	.cfi_endproc
                                        ; -- End function
	.private_extern	__ZNSt3__120__throw_out_of_rangeB9nqe210106EPKc ; -- Begin function _ZNSt3__120__throw_out_of_rangeB9nqe210106EPKc
	.globl	__ZNSt3__120__throw_out_of_rangeB9nqe210106EPKc
	.weak_def_can_be_hidden	__ZNSt3__120__throw_out_of_rangeB9nqe210106EPKc
	.p2align	2
__ZNSt3__120__throw_out_of_rangeB9nqe210106EPKc: ; @_ZNSt3__120__throw_out_of_rangeB9nqe210106EPKc
Lfunc_begin0:
	.cfi_startproc
	.cfi_personality 155, ___gxx_personality_v0
	.cfi_lsda 16, Lexception0
; %bb.0:
	stp	x20, x19, [sp, #-32]!           ; 16-byte Folded Spill
	stp	x29, x30, [sp, #16]             ; 16-byte Folded Spill
	add	x29, sp, #16
	.cfi_def_cfa w29, 16
	.cfi_offset w30, -8
	.cfi_offset w29, -16
	.cfi_offset w19, -24
	.cfi_offset w20, -32
	mov	x20, x0
	mov	w0, #16                         ; =0x10
	bl	___cxa_allocate_exception
	mov	x19, x0
Ltmp0:
	mov	x1, x20
	bl	__ZNSt12out_of_rangeC1B9nqe210106EPKc
Ltmp1:
; %bb.1:
Lloh18:
	adrp	x1, __ZTISt12out_of_range@GOTPAGE
Lloh19:
	adrp	x2, __ZNSt12out_of_rangeD1Ev@GOTPAGE
	mov	x0, x19
Lloh20:
	ldr	x1, [x1, __ZTISt12out_of_range@GOTPAGEOFF]
Lloh21:
	ldr	x2, [x2, __ZNSt12out_of_rangeD1Ev@GOTPAGEOFF]
	bl	___cxa_throw
LBB8_2:
Ltmp2:
	mov	x20, x0
	mov	x0, x19
	bl	___cxa_free_exception
	mov	x0, x20
	bl	__Unwind_Resume
	.loh AdrpLdrGot	Lloh19, Lloh21
	.loh AdrpLdrGot	Lloh18, Lloh20
Lfunc_end0:
	.cfi_endproc
	.section	__TEXT,__gcc_except_tab
	.p2align	2, 0x0
GCC_except_table8:
Lexception0:
	.byte	255                             ; @LPStart Encoding = omit
	.byte	255                             ; @TType Encoding = omit
	.byte	1                               ; Call site Encoding = uleb128
	.uleb128 Lcst_end0-Lcst_begin0
Lcst_begin0:
	.uleb128 Lfunc_begin0-Lfunc_begin0      ; >> Call Site 1 <<
	.uleb128 Ltmp0-Lfunc_begin0             ;   Call between Lfunc_begin0 and Ltmp0
	.byte	0                               ;     has no landing pad
	.byte	0                               ;   On action: cleanup
	.uleb128 Ltmp0-Lfunc_begin0             ; >> Call Site 2 <<
	.uleb128 Ltmp1-Ltmp0                    ;   Call between Ltmp0 and Ltmp1
	.uleb128 Ltmp2-Lfunc_begin0             ;     jumps to Ltmp2
	.byte	0                               ;   On action: cleanup
	.uleb128 Ltmp1-Lfunc_begin0             ; >> Call Site 3 <<
	.uleb128 Lfunc_end0-Ltmp1               ;   Call between Ltmp1 and Lfunc_end0
	.byte	0                               ;     has no landing pad
	.byte	0                               ;   On action: cleanup
Lcst_end0:
	.p2align	2, 0x0
                                        ; -- End function
	.section	__TEXT,__text,regular,pure_instructions
	.private_extern	__ZNSt12out_of_rangeC1B9nqe210106EPKc ; -- Begin function _ZNSt12out_of_rangeC1B9nqe210106EPKc
	.globl	__ZNSt12out_of_rangeC1B9nqe210106EPKc
	.weak_def_can_be_hidden	__ZNSt12out_of_rangeC1B9nqe210106EPKc
	.p2align	2
__ZNSt12out_of_rangeC1B9nqe210106EPKc:  ; @_ZNSt12out_of_rangeC1B9nqe210106EPKc
	.cfi_startproc
; %bb.0:
	stp	x29, x30, [sp, #-16]!           ; 16-byte Folded Spill
	mov	x29, sp
	.cfi_def_cfa w29, 16
	.cfi_offset w30, -8
	.cfi_offset w29, -16
	bl	__ZNSt11logic_errorC2EPKc
Lloh22:
	adrp	x8, __ZTVSt12out_of_range@GOTPAGE
Lloh23:
	ldr	x8, [x8, __ZTVSt12out_of_range@GOTPAGEOFF]
	add	x8, x8, #16
	str	x8, [x0]
	ldp	x29, x30, [sp], #16             ; 16-byte Folded Reload
	ret
	.loh AdrpLdrGot	Lloh22, Lloh23
	.cfi_endproc
                                        ; -- End function
	.section	__TEXT,__cstring,cstring_literals
l_.str:                                 ; @.str
	.asciz	"array::at"

.subsections_via_symbols
