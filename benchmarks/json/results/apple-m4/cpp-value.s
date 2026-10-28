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
	sub	sp, sp, #416
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
Lloh0:
	adrp	x8, ___stack_chk_guard@GOTPAGE
Lloh1:
	ldr	x8, [x8, ___stack_chk_guard@GOTPAGEOFF]
Lloh2:
	ldr	x8, [x8]
	stur	x8, [x29, #-96]
	ldr	w8, [x0, #168]
	cbnz	w8, LBB2_173
; %bb.1:
	cbz	w2, LBB2_173
; %bb.2:
	add	x8, sp, #16
	mov	x3, #8193                       ; =0x2001
	mov	w4, #4113                       ; =0x1011
	mov	w19, w2
	mov	w20, #1                         ; =0x1
	mov	w26, #2                         ; =0x2
	mov	w27, #5                         ; =0x5
	add	x23, x8, #56
	mov	w2, #7                          ; =0x7
	mov	w25, #3                         ; =0x3
	movk	x3, #1024, lsl #48
	movk	w4, #5, lsl #16
	mov	w28, #4                         ; =0x4
	mov	w5, #56320                      ; =0xdc00
	mov	w6, #55296                      ; =0xd800
	mov	w7, #11                         ; =0xb
	mov	w30, #17                        ; =0x11
	mov	w21, #108                       ; =0x6c
	mov	w24, #117                       ; =0x75
LBB2_3:                                 ; =>This Inner Loop Header: Depth=1
	ldp	x10, x8, [x0]
	ldr	x15, [x0, #16]
	ldr	w12, [x0, #24]
	ldrb	w13, [x0, #28]
	ldr	w16, [x0, #32]
	ldrb	w14, [x0, #29]
	ldrh	w9, [x0, #30]
	ldr	x11, [x0, #40]
	cbz	w16, LBB2_14
LBB2_4:                                 ;   in Loop: Header=BB2_3 Depth=1
	stp	x10, x8, [x0]
	str	x15, [x0, #16]
	str	w12, [x0, #24]
	strb	w13, [x0, #28]
	strb	w14, [x0, #29]
	strh	w9, [x0, #30]
	str	w16, [x0, #32]
	str	x11, [x0, #40]
	cbnz	w16, LBB2_172
; %bb.5:                                ;   in Loop: Header=BB2_3 Depth=1
	ldp	q0, q1, [x0, #128]
	ldr	q2, [x0, #160]
	ldr	x8, [x0, #176]
	ldrb	w22, [x1]
	str	q2, [sp, #176]
	stp	q0, q1, [sp, #144]
	ldp	q0, q1, [x0, #64]
	str	x8, [sp, #192]
	ldr	w8, [sp, #144]
	stp	q0, q1, [sp, #80]
	ldp	q2, q0, [x0, #96]
	cmp	w8, #3
	stp	q2, q0, [sp, #112]
	ldp	q1, q0, [x0]
	stp	q1, q0, [sp, #16]
	ldp	q2, q0, [x0, #32]
	stp	q2, q0, [sp, #48]
	b.le	LBB2_11
; %bb.6:                                ;   in Loop: Header=BB2_3 Depth=1
	cmp	w8, #5
	b.gt	LBB2_22
; %bb.7:                                ;   in Loop: Header=BB2_3 Depth=1
	cmp	w8, #4
	b.eq	LBB2_46
; %bb.8:                                ;   in Loop: Header=BB2_3 Depth=1
	cmp	w8, #5
	b.ne	LBB2_41
; %bb.9:                                ;   in Loop: Header=BB2_3 Depth=1
	cmp	w22, #117
	b.ne	LBB2_48
; %bb.10:                               ;   in Loop: Header=BB2_3 Depth=1
	mov	w8, #6                          ; =0x6
	str	xzr, [sp, #160]
	str	w8, [sp, #144]
	b	LBB2_154
LBB2_11:                                ;   in Loop: Header=BB2_3 Depth=1
	cmp	w8, #1
	b.eq	LBB2_35
; %bb.12:                               ;   in Loop: Header=BB2_3 Depth=1
	cmp	w8, #2
	b.eq	LBB2_49
; %bb.13:                               ;   in Loop: Header=BB2_3 Depth=1
	cmp	w8, #3
	b.eq	LBB2_27
	b	LBB2_41
LBB2_14:                                ;   in Loop: Header=BB2_3 Depth=1
	cmn	x10, #1
	b.eq	LBB2_34
; %bb.15:                               ;   in Loop: Header=BB2_3 Depth=1
	ldrb	w17, [x1]
	cbz	w12, LBB2_53
; %bb.16:                               ;   in Loop: Header=BB2_3 Depth=1
	cmp	w17, w13
	mov	w16, #1                         ; =0x1
	b.lo	LBB2_56
; %bb.17:                               ;   in Loop: Header=BB2_3 Depth=1
	cmp	w17, w14
	b.hi	LBB2_56
; %bb.18:                               ;   in Loop: Header=BB2_3 Depth=1
	subs	w12, w12, #1
	b.ne	LBB2_21
; %bb.19:                               ;   in Loop: Header=BB2_3 Depth=1
	cmn	x8, #1
	b.eq	LBB2_103
; %bb.20:                               ;   in Loop: Header=BB2_3 Depth=1
	mov	w12, wzr
	add	x8, x8, #1
LBB2_21:                                ;   in Loop: Header=BB2_3 Depth=1
	mov	w13, #128                       ; =0x80
	mov	w14, #191                       ; =0xbf
	b	LBB2_76
LBB2_22:                                ;   in Loop: Header=BB2_3 Depth=1
	cmp	w8, #6
	b.eq	LBB2_27
; %bb.23:                               ;   in Loop: Header=BB2_3 Depth=1
	cmp	w8, #20
	b.ne	LBB2_41
; %bb.24:                               ;   in Loop: Header=BB2_3 Depth=1
	ldp	w9, w8, [sp, #152]
	cmp	w9, #2
	b.eq	LBB2_63
; %bb.25:                               ;   in Loop: Header=BB2_3 Depth=1
	cmp	w9, #1
	b.ne	LBB2_64
; %bb.26:                               ;   in Loop: Header=BB2_3 Depth=1
	cmp	w8, #1
	mov	w10, #114                       ; =0x72
	mov	w11, #101                       ; =0x65
	csel	w10, w10, wzr, eq
	cmp	w8, #2
	csel	w10, w24, w10, eq
	cmp	w8, #3
	csel	w11, w11, w10, eq
	b	LBB2_65
LBB2_27:                                ;   in Loop: Header=BB2_3 Depth=1
	sub	w9, w22, #48
	cmp	w9, #9
	b.ls	LBB2_30
; %bb.28:                               ;   in Loop: Header=BB2_3 Depth=1
	sub	w9, w22, #65
	cmp	w9, #5
	b.hi	LBB2_57
; %bb.29:                               ;   in Loop: Header=BB2_3 Depth=1
	sub	w9, w22, #55
LBB2_30:                                ;   in Loop: Header=BB2_3 Depth=1
	cmp	w9, #16
	b.eq	LBB2_62
LBB2_31:                                ;   in Loop: Header=BB2_3 Depth=1
	ldp	w11, w10, [sp, #160]
	add	w9, w9, w10, lsl #4
	add	w10, w11, #1
	cmp	w10, #4
	stp	w10, w9, [sp, #160]
	b.ne	LBB2_154
; %bb.32:                               ;   in Loop: Header=BB2_3 Depth=1
	cmp	w8, #6
	b.ne	LBB2_90
; %bb.33:                               ;   in Loop: Header=BB2_3 Depth=1
	sub	w8, w9, #14, lsl #12            ; =57344
	cmn	w8, #1025
	b.hi	LBB2_61
	b	LBB2_48
LBB2_34:                                ;   in Loop: Header=BB2_3 Depth=1
	mov	w16, #2                         ; =0x2
	mov	x11, #-1                        ; =0xffffffffffffffff
	b	LBB2_4
LBB2_35:                                ;   in Loop: Header=BB2_3 Depth=1
	cmp	w22, #31
	b.ls	LBB2_152
; %bb.36:                               ;   in Loop: Header=BB2_3 Depth=1
	cmp	w22, #92
	b.eq	LBB2_95
; %bb.37:                               ;   in Loop: Header=BB2_3 Depth=1
	cmp	w22, #34
	b.ne	LBB2_154
; %bb.38:                               ;   in Loop: Header=BB2_3 Depth=1
	ldrb	w9, [sp, #148]
	ldr	w8, [sp, #136]
	str	wzr, [sp, #144]
	cmp	w9, #1
	b.ne	LBB2_104
; %bb.39:                               ;   in Loop: Header=BB2_3 Depth=1
	sub	w8, w8, #1
	cmp	w8, #64
	b.hs	LBB2_176
; %bb.40:                               ;   in Loop: Header=BB2_3 Depth=1
	strb	w27, [x23, w8, uxtw]
	b	LBB2_154
LBB2_41:                                ;   in Loop: Header=BB2_3 Depth=1
	sub	w9, w8, #10
	cmp	w9, #7
	b.hi	LBB2_83
; %bb.42:                               ;   in Loop: Header=BB2_3 Depth=1
	sub	w9, w22, #48
	cmp	w9, #9
	b.hi	LBB2_77
; %bb.43:                               ;   in Loop: Header=BB2_3 Depth=1
	cmp	w8, #10
	b.eq	LBB2_116
; %bb.44:                               ;   in Loop: Header=BB2_3 Depth=1
	cmp	w8, #13
	b.eq	LBB2_111
; %bb.45:                               ;   in Loop: Header=BB2_3 Depth=1
	cmp	w8, #11
	b.eq	LBB2_115
	b	LBB2_117
LBB2_46:                                ;   in Loop: Header=BB2_3 Depth=1
	cmp	w22, #92
	b.ne	LBB2_48
; %bb.47:                               ;   in Loop: Header=BB2_3 Depth=1
	str	w27, [sp, #144]
	b	LBB2_154
LBB2_48:                                ;   in Loop: Header=BB2_3 Depth=1
	ldr	x8, [sp, #176]
	str	w28, [sp, #184]
	b	LBB2_153
LBB2_49:                                ;   in Loop: Header=BB2_3 Depth=1
	sub	w8, w22, #98
	cmp	w8, #19
	b.hi	LBB2_59
; %bb.50:                               ;   in Loop: Header=BB2_3 Depth=1
	lsl	w9, w20, w8
	tst	w9, w4
	b.ne	LBB2_61
; %bb.51:                               ;   in Loop: Header=BB2_3 Depth=1
	cmp	w8, #19
	b.ne	LBB2_59
; %bb.52:                               ;   in Loop: Header=BB2_3 Depth=1
	str	xzr, [sp, #160]
	str	w25, [sp, #144]
	b	LBB2_154
LBB2_53:                                ;   in Loop: Header=BB2_3 Depth=1
	tbnz	w17, #7, LBB2_71
; %bb.54:                               ;   in Loop: Header=BB2_3 Depth=1
	cmn	x8, #1
	b.eq	LBB2_93
; %bb.55:                               ;   in Loop: Header=BB2_3 Depth=1
	mov	w12, wzr
	add	x8, x8, #1
	b	LBB2_75
LBB2_56:                                ;   in Loop: Header=BB2_3 Depth=1
	mov	x11, x15
	b	LBB2_4
LBB2_57:                                ;   in Loop: Header=BB2_3 Depth=1
	sub	w9, w22, #97
	cmp	w9, #5
	b.hi	LBB2_62
; %bb.58:                               ;   in Loop: Header=BB2_3 Depth=1
	sub	w9, w22, #87
	cmp	w9, #16
	b.ne	LBB2_31
	b	LBB2_62
LBB2_59:                                ;   in Loop: Header=BB2_3 Depth=1
	sub	w8, w22, #34
	cmp	w8, #58
	b.hi	LBB2_62
; %bb.60:                               ;   in Loop: Header=BB2_3 Depth=1
	lsl	x8, x20, x8
	tst	x8, x3
	b.eq	LBB2_62
LBB2_61:                                ;   in Loop: Header=BB2_3 Depth=1
	str	w20, [sp, #144]
	b	LBB2_154
LBB2_62:                                ;   in Loop: Header=BB2_3 Depth=1
	ldr	x8, [sp, #64]
	str	w25, [sp, #184]
	b	LBB2_153
LBB2_63:                                ;   in Loop: Header=BB2_3 Depth=1
	cmp	w8, #1
	mov	w10, #97                        ; =0x61
	mov	w11, #115                       ; =0x73
	csel	w10, w10, wzr, eq
	cmp	w8, #2
	csel	w10, w21, w10, eq
	cmp	w8, #3
	csel	w10, w11, w10, eq
	cmp	w8, #4
	mov	w11, #101                       ; =0x65
	csel	w11, w11, w10, eq
	mov	w10, #5                         ; =0x5
	b	LBB2_66
LBB2_64:                                ;   in Loop: Header=BB2_3 Depth=1
	mov	w11, wzr
LBB2_65:                                ;   in Loop: Header=BB2_3 Depth=1
	mov	w10, #4                         ; =0x4
LBB2_66:                                ;   in Loop: Header=BB2_3 Depth=1
	cmp	w8, #1
	csel	w12, w24, w21, eq
	cmp	w9, #3
	csel	w9, w12, w11, eq
	cmp	w22, w9
	b.ne	LBB2_152
; %bb.67:                               ;   in Loop: Header=BB2_3 Depth=1
	add	w8, w8, #1
	cmp	w8, w10
	str	w8, [sp, #156]
	b.ne	LBB2_154
; %bb.68:                               ;   in Loop: Header=BB2_3 Depth=1
	ldr	w8, [sp, #136]
	str	wzr, [sp, #144]
	cbz	w8, LBB2_105
LBB2_69:                                ;   in Loop: Header=BB2_3 Depth=1
	sub	w8, w8, #1
	cmp	w8, #64
	b.hs	LBB2_176
; %bb.70:                               ;   in Loop: Header=BB2_3 Depth=1
	ldrb	w9, [x23, w8, uxtw]
	and	w9, w9, #0xfffffffd
	cmp	w9, #1
	csel	w9, w26, w2, eq
	strb	w9, [x23, w8, uxtw]
	b	LBB2_154
LBB2_71:                                ;   in Loop: Header=BB2_3 Depth=1
	sub	w12, w17, #194
	cmp	w12, #30
	b.hs	LBB2_96
; %bb.72:                               ;   in Loop: Header=BB2_3 Depth=1
	mov	w12, #1                         ; =0x1
LBB2_73:                                ;   in Loop: Header=BB2_3 Depth=1
	mov	w13, #128                       ; =0x80
LBB2_74:                                ;   in Loop: Header=BB2_3 Depth=1
	mov	w14, #191                       ; =0xbf
LBB2_75:                                ;   in Loop: Header=BB2_3 Depth=1
	mov	x15, x10
LBB2_76:                                ;   in Loop: Header=BB2_3 Depth=1
	mov	w16, wzr
	add	x10, x10, #1
	b	LBB2_4
LBB2_77:                                ;   in Loop: Header=BB2_3 Depth=1
	cmp	w8, #11
	b.ne	LBB2_100
; %bb.78:                               ;   in Loop: Header=BB2_3 Depth=1
	cmp	w22, #46
	b.eq	LBB2_102
; %bb.79:                               ;   in Loop: Header=BB2_3 Depth=1
	and	w8, w22, #0xffffffdf
	cmp	w8, #69
	b.eq	LBB2_130
LBB2_80:                                ;   in Loop: Header=BB2_3 Depth=1
	cmp	w22, #44
	b.hi	LBB2_136
; %bb.81:                               ;   in Loop: Header=BB2_3 Depth=1
	lsl	x8, x20, x22
	mov	x9, #9728                       ; =0x2600
	movk	x9, #4097, lsl #32
	tst	x8, x9
	b.eq	LBB2_136
LBB2_82:                                ;   in Loop: Header=BB2_3 Depth=1
	mov	x27, x0
	add	x0, sp, #16
	str	wzr, [sp, #144]
	mov	x26, x1
	bl	__ZL4doneR5State
	mov	w4, #4113                       ; =0x1011
	mov	x3, #8193                       ; =0x2001
	mov	w30, #17                        ; =0x11
	mov	w7, #11                         ; =0xb
	mov	w6, #55296                      ; =0xd800
	mov	w5, #56320                      ; =0xdc00
	movk	w4, #5, lsl #16
	movk	x3, #1024, lsl #48
	mov	w2, #7                          ; =0x7
	mov	x1, x26
	mov	w26, #2                         ; =0x2
	mov	x0, x27
	mov	w27, #5                         ; =0x5
LBB2_83:                                ;   in Loop: Header=BB2_3 Depth=1
	cmp	w22, #32
	b.hi	LBB2_85
; %bb.84:                               ;   in Loop: Header=BB2_3 Depth=1
	lsl	x8, x20, x22
	mov	x9, #9728                       ; =0x2600
	movk	x9, #1, lsl #32
	tst	x8, x9
	b.ne	LBB2_154
LBB2_85:                                ;   in Loop: Header=BB2_3 Depth=1
	ldr	w8, [sp, #136]
	cbz	w8, LBB2_119
; %bb.86:                               ;   in Loop: Header=BB2_3 Depth=1
	sub	w10, w8, #1
	cmp	w10, #64
	b.hs	LBB2_176
; %bb.87:                               ;   in Loop: Header=BB2_3 Depth=1
	ldrb	w9, [x23, w10, uxtw]
	cmp	w22, #93
	b.ne	LBB2_120
; %bb.88:                               ;   in Loop: Header=BB2_3 Depth=1
	sub	w11, w9, #1
	cmp	w11, #1
	b.hi	LBB2_120
; %bb.89:                               ;   in Loop: Header=BB2_3 Depth=1
	str	w10, [sp, #136]
	b	LBB2_154
LBB2_90:                                ;   in Loop: Header=BB2_3 Depth=1
	and	w8, w9, #0xfffffc00
	cmp	w8, w5
	b.eq	LBB2_106
; %bb.91:                               ;   in Loop: Header=BB2_3 Depth=1
	cmp	w8, w6
	b.ne	LBB2_61
; %bb.92:                               ;   in Loop: Header=BB2_3 Depth=1
	ldr	x8, [sp, #168]
	str	w28, [sp, #144]
	str	x8, [sp, #176]
	b	LBB2_154
LBB2_93:                                ;   in Loop: Header=BB2_3 Depth=1
	mov	w12, wzr
	mov	w16, #2                         ; =0x2
LBB2_94:                                ;   in Loop: Header=BB2_3 Depth=1
	mov	x11, x10
	mov	x15, x10
	b	LBB2_4
LBB2_95:                                ;   in Loop: Header=BB2_3 Depth=1
	ldr	x8, [sp, #64]
	str	w26, [sp, #144]
	str	x8, [sp, #168]
	b	LBB2_154
LBB2_96:                                ;   in Loop: Header=BB2_3 Depth=1
	and	w12, w17, #0xf0
	cmp	w12, #224
	b.ne	LBB2_107
; %bb.97:                               ;   in Loop: Header=BB2_3 Depth=1
	mov	w12, #2                         ; =0x2
	cmp	w17, #237
	b.eq	LBB2_131
; %bb.98:                               ;   in Loop: Header=BB2_3 Depth=1
	cmp	w17, #224
	b.ne	LBB2_73
; %bb.99:                               ;   in Loop: Header=BB2_3 Depth=1
	mov	w13, #160                       ; =0xa0
	b	LBB2_74
LBB2_100:                               ;   in Loop: Header=BB2_3 Depth=1
	cmp	w22, #46
	b.ne	LBB2_112
; %bb.101:                              ;   in Loop: Header=BB2_3 Depth=1
	cmp	w8, #12
	b.ne	LBB2_112
LBB2_102:                               ;   in Loop: Header=BB2_3 Depth=1
	mov	w8, #13                         ; =0xd
	str	w8, [sp, #144]
	b	LBB2_154
LBB2_103:                               ;   in Loop: Header=BB2_3 Depth=1
	mov	w12, wzr
	mov	w13, #128                       ; =0x80
	mov	w14, #191                       ; =0xbf
	mov	w16, #2                         ; =0x2
	mov	x11, x10
	b	LBB2_4
LBB2_104:                               ;   in Loop: Header=BB2_3 Depth=1
	cbnz	w8, LBB2_69
LBB2_105:                               ;   in Loop: Header=BB2_3 Depth=1
	strb	w20, [sp, #140]
	b	LBB2_154
LBB2_106:                               ;   in Loop: Header=BB2_3 Depth=1
	ldr	x8, [sp, #168]
	str	w28, [sp, #184]
	b	LBB2_153
LBB2_107:                               ;   in Loop: Header=BB2_3 Depth=1
	sub	w12, w17, #240
	cmp	w12, #4
	b.hi	LBB2_128
; %bb.108:                              ;   in Loop: Header=BB2_3 Depth=1
	mov	w12, #3                         ; =0x3
	cmp	w17, #244
	b.eq	LBB2_146
; %bb.109:                              ;   in Loop: Header=BB2_3 Depth=1
	cmp	w17, #240
	b.ne	LBB2_73
; %bb.110:                              ;   in Loop: Header=BB2_3 Depth=1
	mov	w13, #144                       ; =0x90
	b	LBB2_74
LBB2_111:                               ;   in Loop: Header=BB2_3 Depth=1
	mov	w8, #14                         ; =0xe
	str	w8, [sp, #144]
	b	LBB2_154
LBB2_112:                               ;   in Loop: Header=BB2_3 Depth=1
	cmp	w8, #16
	b.hi	LBB2_80
; %bb.113:                              ;   in Loop: Header=BB2_3 Depth=1
	lsl	w9, w20, w8
	mov	w10, #22528                     ; =0x5800
	tst	w9, w10
	b.ne	LBB2_129
; %bb.114:                              ;   in Loop: Header=BB2_3 Depth=1
	mov	w10, #9216                      ; =0x2400
	movk	w10, #1, lsl #16
	tst	w9, w10
	b.eq	LBB2_141
LBB2_115:                               ;   in Loop: Header=BB2_3 Depth=1
	ldr	x8, [sp, #64]
	str	w26, [sp, #184]
	b	LBB2_153
LBB2_116:                               ;   in Loop: Header=BB2_3 Depth=1
	cmp	w22, #48
	cinc	w8, w7, ne
	str	w8, [sp, #144]
LBB2_117:                               ;   in Loop: Header=BB2_3 Depth=1
	sub	w8, w8, #15
	cmp	w8, #1
	b.hi	LBB2_154
; %bb.118:                              ;   in Loop: Header=BB2_3 Depth=1
	str	w30, [sp, #144]
	b	LBB2_154
LBB2_119:                               ;   in Loop: Header=BB2_3 Depth=1
	mov	w9, wzr
LBB2_120:                               ;   in Loop: Header=BB2_3 Depth=1
	cmp	w22, #125
	b.ne	LBB2_124
; %bb.121:                              ;   in Loop: Header=BB2_3 Depth=1
	cmp	w9, #7
	b.eq	LBB2_123
; %bb.122:                              ;   in Loop: Header=BB2_3 Depth=1
	cmp	w9, #4
	b.ne	LBB2_124
LBB2_123:                               ;   in Loop: Header=BB2_3 Depth=1
	sub	w8, w8, #1
	str	w8, [sp, #136]
	b	LBB2_154
LBB2_124:                               ;   in Loop: Header=BB2_3 Depth=1
	cmp	w9, #4
	b.le	LBB2_132
; %bb.125:                              ;   in Loop: Header=BB2_3 Depth=1
	cmp	w9, #5
	b.eq	LBB2_147
; %bb.126:                              ;   in Loop: Header=BB2_3 Depth=1
	cmp	w9, #8
	b.eq	LBB2_134
; %bb.127:                              ;   in Loop: Header=BB2_3 Depth=1
	cmp	w9, #7
	b.eq	LBB2_138
	b	LBB2_150
LBB2_128:                               ;   in Loop: Header=BB2_3 Depth=1
	mov	w12, wzr
	mov	w13, #128                       ; =0x80
	mov	w14, #191                       ; =0xbf
	mov	w16, #1                         ; =0x1
	b	LBB2_94
LBB2_129:                               ;   in Loop: Header=BB2_3 Depth=1
	and	w9, w22, #0xffffffdf
	cmp	w9, #69
	b.ne	LBB2_145
LBB2_130:                               ;   in Loop: Header=BB2_3 Depth=1
	mov	w8, #15                         ; =0xf
	str	w8, [sp, #144]
	b	LBB2_154
LBB2_131:                               ;   in Loop: Header=BB2_3 Depth=1
	mov	w13, #128                       ; =0x80
	mov	w14, #159                       ; =0x9f
	b	LBB2_75
LBB2_132:                               ;   in Loop: Header=BB2_3 Depth=1
	cmp	w9, #2
	b.eq	LBB2_138
; %bb.133:                              ;   in Loop: Header=BB2_3 Depth=1
	cmp	w9, #4
	b.ne	LBB2_150
LBB2_134:                               ;   in Loop: Header=BB2_3 Depth=1
	cmp	w22, #34
	b.ne	LBB2_152
; %bb.135:                              ;   in Loop: Header=BB2_3 Depth=1
	strb	w20, [sp, #148]
	str	w20, [sp, #144]
	b	LBB2_154
LBB2_136:                               ;   in Loop: Header=BB2_3 Depth=1
	cmp	w22, #93
	b.eq	LBB2_82
; %bb.137:                              ;   in Loop: Header=BB2_3 Depth=1
	cmp	w22, #125
	b.eq	LBB2_82
	b	LBB2_115
LBB2_138:                               ;   in Loop: Header=BB2_3 Depth=1
	cmp	w22, #44
	b.ne	LBB2_152
; %bb.139:                              ;   in Loop: Header=BB2_3 Depth=1
	sub	w8, w8, #1
	cmp	w8, #64
	b.hs	LBB2_176
; %bb.140:                              ;   in Loop: Header=BB2_3 Depth=1
	cmp	w9, #2
	mov	w9, #8                          ; =0x8
	csel	w9, w25, w9, eq
	strb	w9, [x23, w8, uxtw]
	b	LBB2_154
LBB2_141:                               ;   in Loop: Header=BB2_3 Depth=1
	cmp	w8, #15
	b.ne	LBB2_80
; %bb.142:                              ;   in Loop: Header=BB2_3 Depth=1
	cmp	w22, #45
	b.eq	LBB2_144
; %bb.143:                              ;   in Loop: Header=BB2_3 Depth=1
	cmp	w22, #43
	b.ne	LBB2_115
LBB2_144:                               ;   in Loop: Header=BB2_3 Depth=1
	mov	w8, #16                         ; =0x10
	str	w8, [sp, #144]
	b	LBB2_154
LBB2_145:                               ;   in Loop: Header=BB2_3 Depth=1
	cmp	w8, #13
	b.ne	LBB2_80
	b	LBB2_115
LBB2_146:                               ;   in Loop: Header=BB2_3 Depth=1
	mov	w13, #128                       ; =0x80
	mov	w14, #143                       ; =0x8f
	b	LBB2_75
LBB2_147:                               ;   in Loop: Header=BB2_3 Depth=1
	cmp	w22, #58
	b.ne	LBB2_152
; %bb.148:                              ;   in Loop: Header=BB2_3 Depth=1
	sub	w8, w8, #1
	cmp	w8, #64
	b.hs	LBB2_176
; %bb.149:                              ;   in Loop: Header=BB2_3 Depth=1
	mov	w9, #6                          ; =0x6
	strb	w9, [x23, w8, uxtw]
	b	LBB2_154
LBB2_150:                               ;   in Loop: Header=BB2_3 Depth=1
	cbnz	w8, LBB2_156
; %bb.151:                              ;   in Loop: Header=BB2_3 Depth=1
	ldrb	w9, [sp, #140]
	tbz	w9, #0, LBB2_156
LBB2_152:                               ;   in Loop: Header=BB2_3 Depth=1
	ldr	x8, [sp, #64]
	str	w20, [sp, #184]
LBB2_153:                               ;   in Loop: Header=BB2_3 Depth=1
	str	x8, [sp, #192]
LBB2_154:                               ;   in Loop: Header=BB2_3 Depth=1
	ldp	q0, q1, [sp, #144]
	ldr	q2, [sp, #176]
	ldr	x8, [sp, #192]
	str	q2, [sp, #368]
	stp	q0, q1, [sp, #336]
	ldp	q0, q1, [sp, #80]
	str	x8, [sp, #384]
	ldr	x8, [sp, #384]
	stp	q0, q1, [sp, #272]
	ldp	q2, q0, [sp, #112]
	str	x8, [x0, #176]
	stp	q2, q0, [sp, #304]
	ldp	q1, q0, [sp, #16]
	stp	q1, q0, [sp, #208]
	ldp	q2, q0, [sp, #48]
	stp	q2, q0, [sp, #240]
	ldp	q1, q0, [sp, #336]
	ldr	q2, [sp, #368]
	stp	q1, q0, [x0, #128]
	ldp	q0, q1, [sp, #272]
	str	q2, [x0, #160]
	ldr	w8, [x0, #168]
	stp	q0, q1, [x0, #64]
	ldp	q2, q0, [sp, #304]
	stp	q2, q0, [x0, #96]
	ldp	q1, q0, [sp, #208]
	stp	q1, q0, [x0]
	ldp	q2, q0, [sp, #240]
	stp	q2, q0, [x0, #32]
	cbnz	w8, LBB2_173
; %bb.155:                              ;   in Loop: Header=BB2_3 Depth=1
	ldr	x8, [x0, #48]
	subs	x19, x19, #1
	add	x1, x1, #1
	add	x8, x8, #1
	str	x8, [x0, #48]
	b.ne	LBB2_3
	b	LBB2_173
LBB2_156:                               ;   in Loop: Header=BB2_3 Depth=1
	cmp	w22, #90
	b.gt	LBB2_160
; %bb.157:                              ;   in Loop: Header=BB2_3 Depth=1
	cmp	w22, #34
	b.eq	LBB2_168
; %bb.158:                              ;   in Loop: Header=BB2_3 Depth=1
	cmp	w22, #45
	b.ne	LBB2_164
; %bb.159:                              ;   in Loop: Header=BB2_3 Depth=1
	mov	w8, #10                         ; =0xa
	str	w8, [sp, #144]
	b	LBB2_154
LBB2_160:                               ;   in Loop: Header=BB2_3 Depth=1
	cmp	w22, #123
	b.eq	LBB2_162
; %bb.161:                              ;   in Loop: Header=BB2_3 Depth=1
	cmp	w22, #91
	b.ne	LBB2_164
LBB2_162:                               ;   in Loop: Header=BB2_3 Depth=1
	cmp	w8, #64
	b.ne	LBB2_166
; %bb.163:                              ;   in Loop: Header=BB2_3 Depth=1
	ldr	x8, [sp, #64]
	str	w2, [sp, #184]
	b	LBB2_153
LBB2_164:                               ;   in Loop: Header=BB2_3 Depth=1
	sub	w8, w22, #48
	cmp	w8, #9
	b.hi	LBB2_169
; %bb.165:                              ;   in Loop: Header=BB2_3 Depth=1
	cmp	w22, #48
	cinc	w8, w7, ne
	str	w8, [sp, #144]
	b	LBB2_154
LBB2_166:                               ;   in Loop: Header=BB2_3 Depth=1
	stp	x0, x1, [sp]                    ; 16-byte Folded Spill
	add	x0, sp, #16
	bl	__ZL4doneR5State
	ldr	w8, [sp, #136]
	cmp	w8, #64
	b.hs	LBB2_176
; %bb.167:                              ;   in Loop: Header=BB2_3 Depth=1
	cmp	w22, #91
	ldp	x0, x1, [sp]                    ; 16-byte Folded Reload
	csinc	w9, w28, wzr, ne
	strb	w9, [x23, x8]
	mov	x3, #8193                       ; =0x2001
	ldr	w8, [sp, #136]
	mov	w4, #4113                       ; =0x1011
	mov	w2, #7                          ; =0x7
	movk	x3, #1024, lsl #48
	movk	w4, #5, lsl #16
	mov	w5, #56320                      ; =0xdc00
	add	w8, w8, #1
	mov	w6, #55296                      ; =0xd800
	mov	w7, #11                         ; =0xb
	str	w8, [sp, #136]
	mov	w30, #17                        ; =0x11
	b	LBB2_154
LBB2_168:                               ;   in Loop: Header=BB2_3 Depth=1
	strb	wzr, [sp, #148]
	str	w20, [sp, #144]
	b	LBB2_154
LBB2_169:                               ;   in Loop: Header=BB2_3 Depth=1
	sub	w8, w22, #102
	cmp	w8, #14
	b.hi	LBB2_152
; %bb.170:                              ;   in Loop: Header=BB2_3 Depth=1
	lsl	w8, w20, w8
	mov	w9, #16641                      ; =0x4101
	tst	w8, w9
	b.eq	LBB2_152
; %bb.171:                              ;   in Loop: Header=BB2_3 Depth=1
	cmp	w22, #102
	mov	w9, #20                         ; =0x14
	cinc	w8, w26, ne
	cmp	w22, #116
	str	w9, [sp, #144]
	csinc	w8, w8, wzr, ne
	stp	w8, w20, [sp, #152]
	b	LBB2_154
LBB2_172:
	cmp	w16, #1
	mov	w8, #8                          ; =0x8
	mov	w9, #5                          ; =0x5
	csel	w8, w9, w8, eq
	str	x11, [x0, #176]
	str	w8, [x0, #168]
LBB2_173:
Lloh3:
	adrp	x8, ___stack_chk_guard@GOTPAGE
Lloh4:
	ldr	x8, [x8, ___stack_chk_guard@GOTPAGEOFF]
	ldur	x9, [x29, #-96]
Lloh5:
	ldr	x8, [x8]
	cmp	x8, x9
	b.ne	LBB2_175
; %bb.174:
	add	sp, sp, #416
	ldp	x29, x30, [sp, #80]             ; 16-byte Folded Reload
	ldp	x20, x19, [sp, #64]             ; 16-byte Folded Reload
	ldp	x22, x21, [sp, #48]             ; 16-byte Folded Reload
	ldp	x24, x23, [sp, #32]             ; 16-byte Folded Reload
	ldp	x26, x25, [sp, #16]             ; 16-byte Folded Reload
	ldp	x28, x27, [sp], #96             ; 16-byte Folded Reload
	ret
LBB2_175:
	bl	___stack_chk_fail
LBB2_176:
Lloh6:
	adrp	x0, l_.str@PAGE
Lloh7:
	add	x0, x0, l_.str@PAGEOFF
	bl	__ZNSt3__120__throw_out_of_rangeB9nqe210106EPKc
	.loh AdrpLdrGotLdr	Lloh0, Lloh1, Lloh2
	.loh AdrpLdrGotLdr	Lloh3, Lloh4, Lloh5
	.loh AdrpAdd	Lloh6, Lloh7
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
Lloh8:
	adrp	x8, ___stack_chk_guard@GOTPAGE
Lloh9:
	ldr	x8, [x8, ___stack_chk_guard@GOTPAGEOFF]
Lloh10:
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
Lloh11:
	adrp	x8, ___stack_chk_guard@GOTPAGE
Lloh12:
	ldr	x8, [x8, ___stack_chk_guard@GOTPAGEOFF]
	ldr	w0, [sp, #360]
	ldur	x9, [x29, #-24]
Lloh13:
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
	.loh AdrpLdrGotLdr	Lloh11, Lloh12, Lloh13
	.loh AdrpLdrGotLdr	Lloh8, Lloh9, Lloh10
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
Lloh14:
	adrp	x0, l_.str@PAGE
Lloh15:
	add	x0, x0, l_.str@PAGEOFF
	bl	__ZNSt3__120__throw_out_of_rangeB9nqe210106EPKc
	.loh AdrpAdd	Lloh14, Lloh15
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
Lloh16:
	adrp	x8, ___stack_chk_guard@GOTPAGE
	add	x19, sp, #192
Lloh17:
	ldr	x8, [x8, ___stack_chk_guard@GOTPAGEOFF]
Lloh18:
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
Lloh19:
	adrp	x9, ___stack_chk_guard@GOTPAGE
Lloh20:
	ldr	x9, [x9, ___stack_chk_guard@GOTPAGEOFF]
	ldr	x0, [x8]
	ldur	x8, [x29, #-24]
Lloh21:
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
	.loh AdrpLdrGotLdr	Lloh19, Lloh20, Lloh21
	.loh AdrpLdrGotLdr	Lloh16, Lloh17, Lloh18
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
Lloh22:
	adrp	x0, l_.str@PAGE
Lloh23:
	add	x0, x0, l_.str@PAGEOFF
	bl	__ZNSt3__120__throw_out_of_rangeB9nqe210106EPKc
	.loh AdrpAdd	Lloh22, Lloh23
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
Lloh24:
	adrp	x1, __ZTISt12out_of_range@GOTPAGE
Lloh25:
	adrp	x2, __ZNSt12out_of_rangeD1Ev@GOTPAGE
	mov	x0, x19
Lloh26:
	ldr	x1, [x1, __ZTISt12out_of_range@GOTPAGEOFF]
Lloh27:
	ldr	x2, [x2, __ZNSt12out_of_rangeD1Ev@GOTPAGEOFF]
	bl	___cxa_throw
LBB8_2:
Ltmp2:
	mov	x20, x0
	mov	x0, x19
	bl	___cxa_free_exception
	mov	x0, x20
	bl	__Unwind_Resume
	.loh AdrpLdrGot	Lloh25, Lloh27
	.loh AdrpLdrGot	Lloh24, Lloh26
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
Lloh28:
	adrp	x8, __ZTVSt12out_of_range@GOTPAGE
Lloh29:
	ldr	x8, [x8, __ZTVSt12out_of_range@GOTPAGEOFF]
	add	x8, x8, #16
	str	x8, [x0]
	ldp	x29, x30, [sp], #16             ; 16-byte Folded Reload
	ret
	.loh AdrpLdrGot	Lloh28, Lloh29
	.cfi_endproc
                                        ; -- End function
	.section	__TEXT,__cstring,cstring_literals
l_.str:                                 ; @.str
	.asciz	"array::at"

.subsections_via_symbols
