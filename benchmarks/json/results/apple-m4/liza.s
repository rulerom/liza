	.build_version macos, 26, 0
	.section	__TEXT,__text,regular,pure_instructions
	.globl	_liza_status                    ; -- Begin function liza_status
	.p2align	2
_liza_status:                           ; @liza_status
; %bb.0:                                ; %b0
	stp	x29, x30, [sp, #-16]!           ; 16-byte Folded Spill
	bl	_liza_json.finish
	cmp	w0, #0
	csinc	w0, wzr, w2, eq
	ldp	x29, x30, [sp], #16             ; 16-byte Folded Reload
	ret
                                        ; -- End function
	.globl	_liza_value                     ; -- Begin function liza_value
	.p2align	2
_liza_value:                            ; @liza_value
; %bb.0:                                ; %b0
	stp	x29, x30, [sp, #-16]!           ; 16-byte Folded Spill
	bl	_liza_json.finish
	cmp	w0, #0
	csel	x0, x1, x3, eq
	ldp	x29, x30, [sp], #16             ; 16-byte Folded Reload
	ret
                                        ; -- End function
	.globl	_liza_pending                   ; -- Begin function liza_pending
	.p2align	2
_liza_pending:                          ; @liza_pending
; %bb.0:                                ; %b0
	ldr	w8, [x0, #168]
	cmp	w8, #0
	cset	w0, ne
	ret
                                        ; -- End function
	.globl	_liza_start                     ; -- Begin function liza_start
	.p2align	2
_liza_start:                            ; @liza_start
; %bb.0:                                ; %b0
	sub	sp, sp, #144
	movi.2d	v0, #0000000000000000
	str	wzr, [sp, #132]
	mov	w9, #49024                      ; =0xbf80
	strh	w9, [x8, #28]
	stur	wzr, [sp, #44]
	strb	wzr, [sp, #140]
	stur	q0, [sp, #68]
	stur	q0, [sp, #84]
	stur	q0, [sp, #100]
	stur	q0, [sp, #52]
	stur	q0, [sp, #116]
	stur	q0, [sp, #12]
	ldr	x9, [sp, #128]
	stur	q0, [sp, #28]
	ldp	q0, q1, [sp, #80]
	stur	x9, [x8, #116]
	ldur	x9, [sp, #40]
	strb	wzr, [sp, #136]
	stur	q0, [x8, #68]
	ldr	q0, [sp, #112]
	stur	q1, [x8, #84]
	stur	q0, [x8, #100]
	ldp	q0, q1, [sp, #48]
	stp	xzr, xzr, [x8]
	str	wzr, [x8, #24]
	stur	q0, [x8, #36]
	ldur	q0, [sp, #25]
	stur	q1, [x8, #52]
	ldur	q1, [sp, #9]
	str	xzr, [x8, #16]
	str	wzr, [x8, #32]
	strb	wzr, [x8, #124]
	str	wzr, [x8, #128]
	strb	wzr, [x8, #132]
	stur	x9, [x8, #164]
	stur	q0, [x8, #149]
	stur	q1, [x8, #133]
	str	xzr, [x8, #176]
	add	sp, sp, #144
	ret
                                        ; -- End function
	.globl	_liza_feed                      ; -- Begin function liza_feed
	.p2align	2
_liza_feed:                             ; @liza_feed
; %bb.0:                                ; %b0
	sub	sp, sp, #224
	stp	x20, x19, [sp, #192]            ; 16-byte Folded Spill
	mov	x19, x8
	add	x8, sp, #8
	stp	x29, x30, [sp, #208]            ; 16-byte Folded Spill
	bl	_liza_json.feed
	ldur	q0, [sp, #136]
	ldur	q1, [sp, #152]
	ldur	q2, [sp, #168]
	ldr	x8, [sp, #184]
	ldp	x29, x30, [sp, #208]            ; 16-byte Folded Reload
	stp	q0, q1, [x19, #128]
	ldur	q0, [sp, #72]
	ldur	q1, [sp, #88]
	str	q2, [x19, #160]
	ldur	q2, [sp, #104]
	stp	q0, q1, [x19, #64]
	ldur	q0, [sp, #120]
	ldur	q1, [sp, #8]
	str	x8, [x19, #176]
	stp	q2, q0, [x19, #96]
	ldur	q0, [sp, #24]
	ldur	q2, [sp, #40]
	stp	q1, q0, [x19]
	ldur	q0, [sp, #56]
	stp	q2, q0, [x19, #32]
	ldp	x20, x19, [sp, #192]            ; 16-byte Folded Reload
	add	sp, sp, #224
	ret
                                        ; -- End function
	.globl	_liza_main                      ; -- Begin function liza_main
	.p2align	2
_liza_main:                             ; @liza_main
; %bb.0:                                ; %b0
	mov	w0, wzr
	ret
                                        ; -- End function
	.globl	_liza_utf8_stream.create        ; -- Begin function liza_utf8_stream.create
	.p2align	2
_liza_utf8_stream.create:               ; @liza_utf8_stream.create
; %bb.0:                                ; %b0
	mov	x0, xzr
	mov	x1, xzr
	mov	x2, xzr
	mov	w3, wzr
	mov	w4, #128                        ; =0x80
	mov	w5, #191                        ; =0xbf
	mov	w6, wzr
	mov	x7, xzr
	ret
                                        ; -- End function
	.globl	_liza_utf8_stream.feed_byte     ; -- Begin function liza_utf8_stream.feed_byte
	.p2align	2
_liza_utf8_stream.feed_byte:            ; @liza_utf8_stream.feed_byte
; %bb.0:                                ; %b0
	cbz	w6, LBB7_2
LBB7_1:                                 ; %common.ret
	ret
LBB7_2:                                 ; %b3
	cmn	x0, #1
	b.eq	LBB7_9
; %bb.3:                                ; %b6
	ldrb	w8, [sp]
	cbz	w3, LBB7_10
; %bb.4:                                ; %b8
	and	w8, w8, #0xff
	cmp	w8, w4, uxtb
	b.lo	LBB7_13
; %bb.5:                                ; %b8
	cmp	w8, w5, uxtb
	b.hi	LBB7_13
; %bb.6:                                ; %v115_ok
	subs	w3, w3, #1
	mov	w5, #191                        ; =0xbf
	mov	w4, #128                        ; =0x80
	b.ne	LBB7_24
; %bb.7:                                ; %b51
	cmn	x1, #1
	b.eq	LBB7_20
; %bb.8:                                ; %v138_ok
	add	x1, x1, #1
	b	LBB7_24
LBB7_9:                                 ; %b4
	mov	x7, #-1                         ; =0xffffffffffffffff
	mov	w6, #2                          ; =0x2
	ret
LBB7_10:                                ; %b7
	tbnz	w8, #7, LBB7_14
; %bb.11:                               ; %b9
	cmn	x1, #1
	b.eq	LBB7_16
; %bb.12:                               ; %v32_ok
	add	x1, x1, #1
	mov	x2, x0
	b	LBB7_24
LBB7_13:                                ; %b48
	mov	w6, #1                          ; =0x1
	mov	x7, x2
	ret
LBB7_14:                                ; %b10
	add	w9, w8, #62
	mov	w5, #191                        ; =0xbf
	mov	w4, #128                        ; =0x80
	and	w9, w9, #0xff
	cmp	w9, #30
	b.hs	LBB7_18
; %bb.15:                               ; %b17
	mov	w3, #1                          ; =0x1
	mov	x2, x0
	b	LBB7_24
LBB7_16:                                ; %b11
	mov	w6, #2                          ; =0x2
LBB7_17:                                ; %common.ret
	mov	x2, x0
	mov	x7, x0
	ret
LBB7_18:                                ; %b18
	and	w9, w8, #0xf0
	cmp	w9, #224
	b.ne	LBB7_21
; %bb.19:                               ; %b22
	and	w8, w8, #0xff
	mov	w9, #-96                        ; =0xffffffa0
	mov	w3, #2                          ; =0x2
	cmp	w8, #224
	mov	x2, x0
	csel	w4, w9, w4, eq
	cmp	w8, #237
	mov	w8, #-97                        ; =0xffffff9f
	b	LBB7_23
LBB7_20:                                ; %b53
	mov	w6, #2                          ; =0x2
	mov	x7, x0
	ret
LBB7_21:                                ; %b23
	add	w9, w8, #16
	and	w9, w9, #0xff
	cmp	w9, #4
	b.hi	LBB7_26
; %bb.22:                               ; %b33
	and	w8, w8, #0xff
	mov	w9, #-112                       ; =0xffffff90
	mov	w3, #3                          ; =0x3
	cmp	w8, #240
	mov	x2, x0
	csel	w4, w9, w4, eq
	cmp	w8, #244
	mov	w8, #-113                       ; =0xffffff8f
LBB7_23:                                ; %b57
	csel	w5, w8, w5, eq
LBB7_24:                                ; %b57
	adds	x0, x0, #1
	b.lo	LBB7_1
; %bb.25:                               ; %v145_trap
	brk	#0x1
LBB7_26:                                ; %b34
	mov	w6, #1                          ; =0x1
	b	LBB7_17
                                        ; -- End function
	.globl	_liza_utf8_stream.finish        ; -- Begin function liza_utf8_stream.finish
	.p2align	2
_liza_utf8_stream.finish:               ; @liza_utf8_stream.finish
; %bb.0:                                ; %b0
	cmp	w6, #1
	b.eq	LBB8_3
; %bb.1:                                ; %b0
	cmp	w6, #2
	b.ne	LBB8_4
; %bb.2:                                ; %b4
	mov	x1, xzr
	mov	w0, #1                          ; =0x1
	mov	w2, #1                          ; =0x1
	mov	x3, x7
	ret
LBB8_3:                                 ; %b1
	mov	x1, xzr
	b	LBB8_6
LBB8_4:                                 ; %b6
	cbz	w3, LBB8_7
; %bb.5:                                ; %b7
	mov	x1, xzr
	mov	x7, x2
LBB8_6:                                 ; %common.ret
	mov	w2, wzr
	mov	w0, #1                          ; =0x1
	mov	x3, x7
	ret
LBB8_7:                                 ; %b9
	mov	w0, wzr
	mov	w2, wzr
	mov	x3, xzr
	ret
                                        ; -- End function
	.globl	_liza_utf8_stream.status        ; -- Begin function liza_utf8_stream.status
	.p2align	2
_liza_utf8_stream.status:               ; @liza_utf8_stream.status
; %bb.0:                                ; %b0
	mov	w8, #1                          ; =0x1
	cmp	w6, #2
	mov	w9, #1                          ; =0x1
	csel	w8, wzr, w8, eq
	csel	w9, w9, wzr, eq
	csel	x10, x7, xzr, eq
	cmp	w6, #1
	csel	w0, wzr, w8, eq
	csel	w1, wzr, w9, eq
	csel	x2, x7, x10, eq
	ret
                                        ; -- End function
	.globl	_liza_json.create               ; -- Begin function liza_json.create
	.p2align	2
_liza_json.create:                      ; @liza_json.create
; %bb.0:                                ; %b0
	sub	sp, sp, #16
	movi.2d	v0, #0000000000000000
	mov	w9, #49024                      ; =0xbf80
	strb	wzr, [sp, #12]
	strb	wzr, [sp, #8]
	stp	xzr, xzr, [x8, #8]
	str	xzr, [x8]
	str	wzr, [x8, #24]
	strh	w9, [x8, #28]
	str	wzr, [x8, #32]
	stur	q0, [x8, #40]
	stur	q0, [x8, #56]
	stur	q0, [x8, #72]
	stur	q0, [x8, #88]
	stur	q0, [x8, #104]
	str	wzr, [x8, #120]
	strb	wzr, [x8, #124]
	str	wzr, [x8, #128]
	strb	wzr, [x8, #132]
	str	xzr, [x8, #176]
	str	wzr, [x8, #168]
	stur	q0, [x8, #152]
	stur	q0, [x8, #136]
	add	sp, sp, #16
	ret
                                        ; -- End function
	.globl	_liza___liza_json_fail          ; -- Begin function liza___liza_json_fail
	.p2align	2
_liza___liza_json_fail:                 ; @liza___liza_json_fail
; %bb.0:                                ; %b0
	ldp	q0, q1, [x0]
	ldr	x9, [x0, #160]
	ldp	q2, q3, [x0, #32]
	ldr	w10, [x0, #172]
	ldp	q4, q5, [x0, #64]
	ldp	q6, q7, [x0, #128]
	ldp	q16, q17, [x0, #96]
	str	x9, [x8, #160]
	stp	q0, q1, [x8]
	stp	q2, q3, [x8, #32]
	stp	q4, q5, [x8, #64]
	stp	q16, q17, [x8, #96]
	stp	q6, q7, [x8, #128]
	stp	w1, w10, [x8, #168]
	str	x2, [x8, #176]
	ret
                                        ; -- End function
	.globl	_liza___liza_json_done          ; -- Begin function liza___liza_json_done
	.p2align	2
_liza___liza_json_done:                 ; @liza___liza_json_done
; %bb.0:                                ; %b0
	stp	x28, x27, [sp, #-96]!           ; 16-byte Folded Spill
	stp	x26, x25, [sp, #16]             ; 16-byte Folded Spill
	stp	x24, x23, [sp, #32]             ; 16-byte Folded Spill
	stp	x22, x21, [sp, #48]             ; 16-byte Folded Spill
	stp	x20, x19, [sp, #64]             ; 16-byte Folded Spill
	stp	x29, x30, [sp, #80]             ; 16-byte Folded Spill
	sub	sp, sp, #688
	ldr	w20, [x0, #120]
	add	x13, sp, #304
	cbz	w20, LBB12_5
; %bb.1:                                ; %b2
	ldrb	w9, [x0, #57]
	ldrb	w10, [x0, #59]
	sub	w21, w20, #1
	ldrb	w11, [x0, #61]
	ldrb	w23, [x0, #56]
	cmp	w21, #64
	stp	w10, w9, [sp, #168]             ; 8-byte Folded Spill
	ldrb	w22, [x0, #58]
	ldrb	w24, [x0, #98]
	strb	w9, [sp, #177]
	ldrb	w9, [x0, #60]
	ldrb	w25, [x0, #99]
	strb	w10, [sp, #179]
	ldrb	w10, [x0, #62]
	ldrb	w26, [x0, #100]
	stp	w11, w9, [sp, #160]             ; 8-byte Folded Spill
	ldrb	w27, [x0, #101]
	ldrb	w28, [x0, #102]
	strb	w9, [sp, #180]
	ldrb	w9, [x0, #63]
	ldrb	w30, [x0, #103]
	strb	w11, [sp, #181]
	ldrb	w11, [x0, #64]
	ldrb	w12, [x0, #107]
	stp	w9, w10, [sp, #152]             ; 8-byte Folded Spill
	ldrb	w13, [x0, #108]
	ldrb	w14, [x0, #109]
	strb	w10, [sp, #182]
	ldrb	w10, [x0, #65]
	ldrb	w15, [x0, #110]
	strb	w9, [sp, #183]
	ldrb	w9, [x0, #66]
	ldrb	w16, [x0, #111]
	stp	w10, w11, [sp, #144]            ; 8-byte Folded Spill
	ldrb	w17, [x0, #112]
	ldrb	w2, [x0, #113]
	strb	w11, [sp, #184]
	ldrb	w11, [x0, #67]
	ldrb	w3, [x0, #114]
	strb	w10, [sp, #185]
	ldrb	w10, [x0, #68]
	ldrb	w4, [x0, #115]
	stp	w11, w9, [sp, #136]             ; 8-byte Folded Spill
	ldrb	w5, [x0, #116]
	ldrb	w6, [x0, #117]
	strb	w9, [sp, #186]
	ldrb	w9, [x0, #69]
	ldrb	w7, [x0, #118]
	strb	w11, [sp, #187]
	ldrb	w11, [x0, #70]
	ldrb	w19, [x0, #119]
	stp	w9, w10, [sp, #128]             ; 8-byte Folded Spill
	strb	w10, [sp, #188]
	ldrb	w10, [x0, #71]
	strb	w9, [sp, #189]
	ldrb	w9, [x0, #72]
	stp	w10, w11, [sp, #120]            ; 8-byte Folded Spill
	strb	w11, [sp, #190]
	ldrb	w11, [x0, #73]
	strb	w10, [sp, #191]
	ldrb	w10, [x0, #74]
	stp	w11, w9, [sp, #112]             ; 8-byte Folded Spill
	strb	w9, [sp, #192]
	ldrb	w9, [x0, #75]
	strb	w11, [sp, #193]
	ldrb	w11, [x0, #76]
	stp	w9, w10, [sp, #104]             ; 8-byte Folded Spill
	strb	w10, [sp, #194]
	ldrb	w10, [x0, #77]
	strb	w9, [sp, #195]
	ldrb	w9, [x0, #78]
	stp	w10, w11, [sp, #96]             ; 8-byte Folded Spill
	strb	w11, [sp, #196]
	ldrb	w11, [x0, #79]
	strb	w10, [sp, #197]
	ldrb	w10, [x0, #80]
	stp	w11, w9, [sp, #88]              ; 8-byte Folded Spill
	strb	w9, [sp, #198]
	ldrb	w9, [x0, #81]
	strb	w11, [sp, #199]
	ldrb	w11, [x0, #82]
	stp	w9, w10, [sp, #80]              ; 8-byte Folded Spill
	strb	w10, [sp, #200]
	ldrb	w10, [x0, #83]
	strb	w9, [sp, #201]
	ldrb	w9, [x0, #84]
	stp	w10, w11, [sp, #72]             ; 8-byte Folded Spill
	strb	w11, [sp, #202]
	ldrb	w11, [x0, #85]
	strb	w10, [sp, #203]
	ldrb	w10, [x0, #87]
	stp	w11, w9, [sp, #64]              ; 8-byte Folded Spill
	strb	w9, [sp, #204]
	ldrb	w9, [x0, #86]
	strb	w10, [sp, #207]
	stp	w10, w9, [sp, #56]              ; 8-byte Folded Spill
	ldrb	w10, [x0, #89]
	strb	w9, [sp, #206]
	ldrb	w9, [x0, #88]
	strb	w10, [sp, #209]
	stp	w10, w9, [sp, #48]              ; 8-byte Folded Spill
	ldrb	w10, [x0, #91]
	strb	w9, [sp, #208]
	ldrb	w9, [x0, #90]
	strb	w10, [sp, #211]
	stp	w10, w9, [sp, #40]              ; 8-byte Folded Spill
	ldrb	w10, [x0, #93]
	strb	w9, [sp, #210]
	ldrb	w9, [x0, #92]
	strb	w10, [sp, #213]
	stp	w10, w9, [sp, #32]              ; 8-byte Folded Spill
	ldrb	w10, [x0, #95]
	strb	w9, [sp, #212]
	ldrb	w9, [x0, #94]
	strb	w10, [sp, #215]
	stp	w10, w9, [sp, #24]              ; 8-byte Folded Spill
	ldrb	w10, [x0, #97]
	strb	w9, [sp, #214]
	ldrb	w9, [x0, #96]
	strb	w11, [sp, #205]
	ldrb	w11, [x0, #106]
	stp	w10, w9, [sp, #16]              ; 8-byte Folded Spill
	strb	w9, [sp, #216]
	ldrb	w9, [x0, #104]
	strb	w10, [sp, #217]
	ldrb	w10, [x0, #105]
	strb	w23, [sp, #176]
	strb	w22, [sp, #178]
	strb	w24, [sp, #218]
	strb	w25, [sp, #219]
	strb	w26, [sp, #220]
	strb	w27, [sp, #221]
	strb	w28, [sp, #222]
	strb	w30, [sp, #223]
	strb	w9, [sp, #224]
	strb	w10, [sp, #225]
	strb	w11, [sp, #226]
	strb	w12, [sp, #227]
	strb	w13, [sp, #228]
	strb	w14, [sp, #229]
	strb	w15, [sp, #230]
	strb	w16, [sp, #231]
	strb	w17, [sp, #232]
	strb	w2, [sp, #233]
	strb	w3, [sp, #234]
	strb	w4, [sp, #235]
	strb	w5, [sp, #236]
	strb	w6, [sp, #237]
	strb	w7, [sp, #238]
	strb	w19, [sp, #239]
	b.hs	LBB12_7
; %bb.2:                                ; %v10_ok
	add	x1, sp, #176
	add	x20, sp, #620
	ldrb	w1, [x1, x21]
	cmp	w1, #1
	mov	w1, #2                          ; =0x2
	b.eq	LBB12_4
; %bb.3:                                ; %b3
	strb	w23, [sp, #240]
	mov	w23, w22
	ldr	w22, [sp, #172]                 ; 4-byte Folded Reload
	strb	w23, [sp, #242]
	strb	w22, [sp, #241]
	ldr	w22, [sp, #168]                 ; 4-byte Folded Reload
	strb	w24, [sp, #282]
	strb	w22, [sp, #243]
	ldr	w22, [sp, #164]                 ; 4-byte Folded Reload
	strb	w25, [sp, #283]
	strb	w22, [sp, #244]
	ldr	w22, [sp, #160]                 ; 4-byte Folded Reload
	strb	w26, [sp, #284]
	strb	w22, [sp, #245]
	ldr	w22, [sp, #156]                 ; 4-byte Folded Reload
	strb	w27, [sp, #285]
	strb	w22, [sp, #246]
	ldr	w22, [sp, #152]                 ; 4-byte Folded Reload
	strb	w28, [sp, #286]
	strb	w22, [sp, #247]
	ldr	w22, [sp, #148]                 ; 4-byte Folded Reload
	strb	w30, [sp, #287]
	strb	w22, [sp, #248]
	ldr	w22, [sp, #144]                 ; 4-byte Folded Reload
	strb	w9, [sp, #288]
	add	x9, sp, #240
	strb	w22, [sp, #249]
	ldr	w22, [sp, #140]                 ; 4-byte Folded Reload
	strb	w10, [sp, #289]
	mov	w10, #7                         ; =0x7
	strb	w22, [sp, #250]
	ldr	w22, [sp, #136]                 ; 4-byte Folded Reload
	strb	w11, [sp, #290]
	strb	w22, [sp, #251]
	ldr	w22, [sp, #132]                 ; 4-byte Folded Reload
	strb	w12, [sp, #291]
	strb	w22, [sp, #252]
	ldr	w22, [sp, #128]                 ; 4-byte Folded Reload
	strb	w13, [sp, #292]
	strb	w22, [sp, #253]
	ldr	w22, [sp, #124]                 ; 4-byte Folded Reload
	strb	w14, [sp, #293]
	strb	w22, [sp, #254]
	ldr	w22, [sp, #120]                 ; 4-byte Folded Reload
	strb	w15, [sp, #294]
	strb	w22, [sp, #255]
	ldr	w22, [sp, #116]                 ; 4-byte Folded Reload
	strb	w16, [sp, #295]
	strb	w22, [sp, #256]
	ldr	w22, [sp, #112]                 ; 4-byte Folded Reload
	strb	w17, [sp, #296]
	strb	w22, [sp, #257]
	ldr	w22, [sp, #108]                 ; 4-byte Folded Reload
	strb	w2, [sp, #297]
	strb	w22, [sp, #258]
	ldr	w22, [sp, #104]                 ; 4-byte Folded Reload
	strb	w3, [sp, #298]
	strb	w22, [sp, #259]
	ldr	w22, [sp, #100]                 ; 4-byte Folded Reload
	strb	w4, [sp, #299]
	strb	w22, [sp, #260]
	ldr	w22, [sp, #96]                  ; 4-byte Folded Reload
	strb	w5, [sp, #300]
	strb	w22, [sp, #261]
	ldr	w22, [sp, #92]                  ; 4-byte Folded Reload
	strb	w6, [sp, #301]
	strb	w22, [sp, #262]
	ldr	w22, [sp, #88]                  ; 4-byte Folded Reload
	strb	w7, [sp, #302]
	strb	w22, [sp, #263]
	ldr	w22, [sp, #84]                  ; 4-byte Folded Reload
	strb	w19, [sp, #303]
	strb	w22, [sp, #264]
	ldr	w22, [sp, #80]                  ; 4-byte Folded Reload
	strb	w22, [sp, #265]
	ldr	w22, [sp, #76]                  ; 4-byte Folded Reload
	strb	w22, [sp, #266]
	ldr	w22, [sp, #72]                  ; 4-byte Folded Reload
	strb	w22, [sp, #267]
	ldr	w22, [sp, #68]                  ; 4-byte Folded Reload
	strb	w22, [sp, #268]
	ldr	w22, [sp, #64]                  ; 4-byte Folded Reload
	strb	w22, [sp, #269]
	ldr	w22, [sp, #60]                  ; 4-byte Folded Reload
	strb	w22, [sp, #270]
	ldr	w22, [sp, #56]                  ; 4-byte Folded Reload
	strb	w22, [sp, #271]
	ldr	w22, [sp, #52]                  ; 4-byte Folded Reload
	strb	w22, [sp, #272]
	ldr	w22, [sp, #48]                  ; 4-byte Folded Reload
	strb	w22, [sp, #273]
	ldr	w22, [sp, #44]                  ; 4-byte Folded Reload
	strb	w22, [sp, #274]
	ldr	w22, [sp, #40]                  ; 4-byte Folded Reload
	strb	w22, [sp, #275]
	ldr	w22, [sp, #36]                  ; 4-byte Folded Reload
	strb	w22, [sp, #276]
	ldr	w22, [sp, #32]                  ; 4-byte Folded Reload
	strb	w22, [sp, #277]
	ldr	w22, [sp, #28]                  ; 4-byte Folded Reload
	strb	w22, [sp, #278]
	ldr	w22, [sp, #24]                  ; 4-byte Folded Reload
	strb	w22, [sp, #279]
	ldr	w22, [sp, #20]                  ; 4-byte Folded Reload
	strb	w22, [sp, #280]
	ldr	w22, [sp, #16]                  ; 4-byte Folded Reload
	strb	w22, [sp, #281]
	ldrb	w9, [x9, x21]
	cmp	w9, #3
	add	x9, sp, #556
	csel	x20, x20, x9, eq
	csel	w1, w1, w10, eq
LBB12_4:                                ; %b8_to_b9
	ldur	q0, [x0, #56]
	ldur	q1, [x0, #72]
	add	x13, sp, #304
	ldur	q2, [x0, #88]
	ldur	q3, [x0, #168]
	add	x11, sp, #432
	stp	q0, q1, [x20]
	ldur	q0, [x0, #104]
	ldr	x9, [x0, #48]
	stur	q3, [x13, #171]
	ldur	q4, [x0, #157]
	ldur	q5, [x0, #141]
	stp	q2, q0, [x20, #32]
	ldr	q2, [x0]
	ldur	q6, [x0, #125]
	strb	w1, [x20, x21]
	ldrb	w10, [x0, #124]
	str	q2, [sp, #496]
	ldp	q1, q0, [x0, #16]
	str	x9, [sp, #544]
	ldr	w9, [x0, #120]
	add	x0, sp, #496
	stp	q5, q4, [sp, #448]
	ldp	q2, q3, [x20, #32]
	stp	q1, q0, [sp, #512]
	ldp	q0, q1, [x20]
	str	q6, [sp, #432]
	b	LBB12_6
LBB12_5:                                ; %b1
	ldur	q0, [x0, #56]
	ldur	q1, [x0, #72]
	mov	w10, #1                         ; =0x1
	ldur	q2, [x0, #88]
	ldur	q3, [x0, #104]
	mov	w9, wzr
	add	x11, x0, #125
	strb	w10, [sp, #684]
LBB12_6:                                ; %b9
	ldp	q6, q7, [x11]
	ldr	q16, [x0, #32]
	ldp	q4, q5, [x0]
	ldr	x12, [x0, #48]
	str	q16, [sp, #400]
	stp	q6, q7, [sp, #304]
	ldr	q6, [x11, #32]
	stp	q4, q5, [sp, #368]
	str	q6, [sp, #336]
	ldur	q6, [x11, #43]
	stur	q0, [x8, #56]
	stur	q6, [x13, #43]
	ldur	q0, [x13, #43]
	stur	q1, [x8, #72]
	str	x12, [sp, #416]
	stur	q0, [x8, #168]
	ldp	q0, q1, [sp, #320]
	stp	q4, q5, [x8]
	str	q16, [x8, #32]
	stur	q1, [x8, #157]
	ldr	q1, [sp, #304]
	str	x12, [x8, #48]
	stur	q2, [x8, #88]
	stur	q3, [x8, #104]
	str	w9, [x8, #120]
	strb	w10, [x8, #124]
	stur	q0, [x8, #141]
	stur	q1, [x8, #125]
	add	sp, sp, #688
	ldp	x29, x30, [sp, #80]             ; 16-byte Folded Reload
	ldp	x20, x19, [sp, #64]             ; 16-byte Folded Reload
	ldp	x22, x21, [sp, #48]             ; 16-byte Folded Reload
	ldp	x24, x23, [sp, #32]             ; 16-byte Folded Reload
	ldp	x26, x25, [sp, #16]             ; 16-byte Folded Reload
	ldp	x28, x27, [sp], #96             ; 16-byte Folded Reload
	ret
LBB12_7:                                ; %v10_trap
	brk	#0x1
                                        ; -- End function
	.globl	_liza___liza_json_space         ; -- Begin function liza___liza_json_space
	.p2align	2
_liza___liza_json_space:                ; @liza___liza_json_space
; %bb.0:                                ; %b0
	mov	x8, #9728                       ; =0x2600
                                        ; kill: def $w0 killed $w0 def $x0
	and	w9, w0, #0xff
	movk	x8, #1, lsl #32
	cmp	w9, #33
	lsr	x8, x8, x0
	cset	w9, lo
	and	w0, w9, w8
	ret
                                        ; -- End function
	.globl	_liza___liza_json_digit         ; -- Begin function liza___liza_json_digit
	.p2align	2
_liza___liza_json_digit:                ; @liza___liza_json_digit
; %bb.0:                                ; %b0
	and	w8, w0, #0xff
	sub	w8, w8, #48
	cmp	w8, #10
	cset	w0, lo
	ret
                                        ; -- End function
	.globl	_liza___liza_json_hex           ; -- Begin function liza___liza_json_hex
	.p2align	2
_liza___liza_json_hex:                  ; @liza___liza_json_hex
; %bb.0:                                ; %b0
	and	w8, w0, #0xff
	sub	w0, w8, #48
	cmp	w0, #9
	b.hi	LBB15_2
; %bb.1:                                ; %common.ret
	ret
LBB15_2:                                ; %b6
	sub	w9, w8, #65
	cmp	w9, #5
	b.hi	LBB15_4
; %bb.3:                                ; %v15_ok
	sub	w0, w8, #55
	ret
LBB15_4:                                ; %b12
	sub	w9, w8, #97
	cmp	w9, #5
	b.hi	LBB15_6
; %bb.5:                                ; %v24_ok
	sub	w0, w8, #87
	ret
LBB15_6:
	mov	w0, #16                         ; =0x10
	ret
                                        ; -- End function
	.globl	_liza___liza_json_step          ; -- Begin function liza___liza_json_step
	.p2align	2
_liza___liza_json_step:                 ; @liza___liza_json_step
; %bb.0:                                ; %b0
	stp	x28, x27, [sp, #-48]!           ; 16-byte Folded Spill
	stp	x20, x19, [sp, #16]             ; 16-byte Folded Spill
	stp	x29, x30, [sp, #32]             ; 16-byte Folded Spill
	sub	sp, sp, #1, lsl #12             ; =4096
	sub	sp, sp, #336
	ldr	w9, [x0, #128]
	mov	w19, w1
	add	x20, sp, #2936
	cmp	w9, #3
	b.le	LBB16_7
; %bb.1:                                ; %b0
	cmp	w9, #5
	b.gt	LBB16_10
; %bb.2:                                ; %b0
	cmp	w9, #4
	b.eq	LBB16_31
; %bb.3:                                ; %b0
	cmp	w9, #5
	b.ne	LBB16_25
; %bb.4:                                ; %b52
	and	w9, w19, #0xff
	cmp	w9, #117
	b.ne	LBB16_33
; %bb.5:                                ; %b56
	ldur	q0, [x0, #152]
	ldur	q1, [x0, #168]
	ldur	x9, [x0, #132]
	ldr	w10, [x0, #140]
	ldp	q2, q3, [x0, #32]
	str	q0, [sp, #3568]
	ldp	q4, q5, [x0, #96]
	str	q1, [sp, #3584]
	ldp	q1, q0, [x0]
	str	x9, [sp, #3600]
	mov	w9, #6                          ; =0x6
	str	w10, [sp, #3608]
	ldr	x10, [sp, #3600]
	ldp	q6, q7, [x0, #64]
	str	w9, [x8, #128]
	ldr	w9, [sp, #3608]
	stp	q1, q0, [x8]
	ldr	q0, [sp, #3584]
	ldr	q1, [sp, #3568]
LBB16_6:                                ; %common.ret
	stp	q2, q3, [x8, #32]
	stp	q6, q7, [x8, #64]
	stp	q4, q5, [x8, #96]
	stur	x10, [x8, #132]
	str	w9, [x8, #140]
	str	wzr, [x8, #148]
	str	wzr, [x8, #144]
	stur	q0, [x8, #168]
	stur	q1, [x8, #152]
	b	LBB16_85
LBB16_7:                                ; %b0
	cmp	w9, #1
	b.eq	LBB16_18
; %bb.8:                                ; %b0
	cmp	w9, #2
	b.eq	LBB16_36
; %bb.9:                                ; %b0
	cmp	w9, #3
	b.eq	LBB16_16
	b	LBB16_25
LBB16_10:                               ; %b0
	cmp	w9, #6
	b.eq	LBB16_16
; %bb.11:                               ; %b0
	cmp	w9, #20
	b.ne	LBB16_25
; %bb.12:                               ; %b91
	ldr	w9, [x0, #136]
	cmp	w9, #3
	b.eq	LBB16_69
; %bb.13:                               ; %b91
	cmp	w9, #2
	b.eq	LBB16_65
; %bb.14:                               ; %b91
	cmp	w9, #1
	b.ne	LBB16_70
; %bb.15:                               ; %b104.thread
	ldr	w9, [x0, #140]
	mov	w10, #114                       ; =0x72
	mov	w11, #117                       ; =0x75
	cmp	w9, #1
	csel	w10, w10, wzr, eq
	cmp	w9, #2
	csel	w10, w11, w10, eq
	cmp	w9, #3
	mov	w9, #101                        ; =0x65
	csel	w10, w9, w10, eq
	b	LBB16_71
LBB16_16:                               ; %b61
	sub	w10, w19, #48
	and	w10, w10, #0xff
	cmp	w10, #10
	b.hs	LBB16_34
; %bb.17:
	mov	w10, #-48                       ; =0xffffffd0
	b	LBB16_46
LBB16_18:                               ; %b1
	and	w9, w19, #0xff
	cmp	w9, #32
	b.lo	LBB16_66
; %bb.19:                               ; %b5
	cmp	w9, #92
	b.eq	LBB16_77
; %bb.20:                               ; %b5
	cmp	w9, #34
	b.ne	LBB16_78
; %bb.21:                               ; %b6
	ldp	q0, q1, [x0, #128]
	ldr	q2, [x0, #160]
	ldr	x9, [x0, #176]
	str	q2, [sp, #4400]
	str	q0, [sp, #4368]
	str	q1, [sp, #4384]
	ldp	q0, q1, [x0, #64]
	str	x9, [sp, #4416]
	ldrb	w9, [x20, #1436]
	str	wzr, [sp, #4368]
	str	q0, [sp, #4304]
	ldp	q2, q0, [x0, #96]
	str	q1, [sp, #4320]
	cmp	w9, #1
	str	q0, [sp, #4352]
	ldp	q1, q0, [x0]
	str	q2, [sp, #4336]
	str	q0, [sp, #4256]
	ldp	q2, q0, [x0, #32]
	str	q1, [sp, #4240]
	str	q2, [sp, #4272]
	str	q0, [sp, #4288]
	b.ne	LBB16_92
; %bb.22:                               ; %b8
	ldr	w9, [sp, #4360]
	subs	w9, w9, #1
	b.lo	LBB16_183
; %bb.23:                               ; %v17_ok
	cmp	w9, #64
	b.hs	LBB16_183
; %bb.24:                               ; %v18_ok
	add	x10, sp, #1, lsl #12            ; =4096
	mov	w12, #5                         ; =0x5
	ldr	x11, [x0, #48]
	add	x10, x10, #144
	ldur	q0, [x10, #56]
	ldur	q1, [x10, #72]
	ldur	q2, [x10, #88]
	str	q0, [sp, #4176]
	ldur	q0, [x10, #104]
	add	x10, sp, #1, lsl #12            ; =4096
	str	q1, [sp, #4192]
	add	x10, x10, #80
	str	q0, [sp, #4224]
	ldp	q1, q0, [x0, #16]
	str	q2, [sp, #4208]
	ldr	q2, [x0]
	strb	w12, [x10, w9, uxtw]
	add	x9, sp, #1, lsl #12             ; =4096
	stp	q1, q0, [x8, #16]
	ldr	q0, [sp, #4176]
	ldr	q1, [sp, #4192]
	add	x9, x9, #144
	str	x11, [x8, #48]
	stur	q0, [x8, #56]
	ldr	q0, [sp, #4208]
	stur	q1, [x8, #72]
	ldr	q1, [sp, #4224]
	stur	q0, [x8, #88]
	ldur	q0, [x9, #120]
	stur	q1, [x8, #104]
	ldur	q1, [x9, #136]
	stur	q0, [x8, #120]
	ldur	q0, [x9, #152]
	stur	q1, [x8, #136]
	ldur	q1, [x9, #168]
	str	q2, [x8]
	stur	q0, [x8, #152]
	stur	q1, [x8, #168]
	b	LBB16_85
LBB16_25:                               ; %b132
	sub	w10, w9, #10
	cmp	w10, #7
	b.hi	LBB16_40
; %bb.26:                               ; %b136
	sub	w10, w19, #48
	and	w10, w10, #0xff
	cmp	w10, #9
	b.hi	LBB16_60
; %bb.27:                               ; %b138
	cmp	w9, #10
	b.eq	LBB16_94
; %bb.28:                               ; %b138
	cmp	w9, #11
	b.eq	LBB16_150
; %bb.29:                               ; %b148
	ldp	q0, q1, [x0, #64]
	cmp	w9, #13
	ldr	w10, [x0, #180]
	str	q0, [sp, #2672]
	ldp	q0, q2, [x0, #96]
	str	q1, [sp, #2688]
	str	w10, [sp, #2592]
	str	q0, [sp, #2704]
	ldp	q1, q0, [x0]
	str	q2, [sp, #2720]
	str	q0, [sp, #2624]
	ldp	q2, q0, [x0, #32]
	str	q1, [sp, #2608]
	ldur	q1, [x0, #148]
	str	q2, [sp, #2640]
	ldur	q2, [x0, #132]
	str	q0, [sp, #2656]
	ldur	q0, [x0, #164]
	str	q1, [sp, #2560]
	str	q0, [sp, #2576]
	str	q2, [sp, #2544]
	b.ne	LBB16_95
; %bb.30:                               ; %b151.thread
	ldp	q0, q1, [x0, #64]
	add	x10, sp, #2352
	ldur	w9, [x0, #180]
	add	x11, sp, #2416
	str	q0, [sp, #2480]
	ldp	q0, q2, [x0, #96]
	str	q1, [sp, #2496]
	str	w9, [sp, #2400]
	mov	w9, #14                         ; =0xe
	str	q0, [sp, #2512]
	ldp	q1, q0, [x0]
	str	q2, [sp, #2528]
	str	q0, [sp, #2432]
	ldp	q2, q0, [x0, #32]
	str	q1, [sp, #2416]
	ldur	q1, [x0, #148]
	str	q2, [sp, #2448]
	ldur	q2, [x0, #132]
	str	q0, [sp, #2464]
	ldur	q0, [x0, #164]
	str	q1, [sp, #2368]
	str	q0, [sp, #2384]
	str	q2, [sp, #2352]
	b	LBB16_105
LBB16_31:                               ; %b46
	and	w9, w19, #0xff
	cmp	w9, #92
	b.ne	LBB16_33
; %bb.32:                               ; %b50
	ldur	q0, [x0, #132]
	ldur	q1, [x0, #148]
	ldur	q2, [x0, #164]
	ldr	w9, [x0, #180]
	ldp	q4, q5, [x0, #96]
	str	q0, [sp, #3616]
	ldp	q6, q7, [x0, #64]
	str	q1, [sp, #3632]
	ldp	q1, q0, [x0]
	str	q2, [sp, #3648]
	ldp	q2, q3, [x0, #32]
	str	w9, [sp, #3664]
	mov	w9, #5                          ; =0x5
	stp	q1, q0, [x8]
	ldr	q0, [sp, #3616]
	ldr	q1, [sp, #3632]
	str	w9, [x8, #128]
	ldr	w9, [sp, #3664]
	stur	q0, [x8, #132]
	ldr	q0, [sp, #3648]
	b	LBB16_58
LBB16_33:                               ; %b48
	ldp	q0, q1, [x0]
	mov	w11, #4                         ; =0x4
	ldp	q2, q3, [x0, #32]
	ldr	x9, [x0, #160]
	ldp	q4, q5, [x0, #64]
	ldr	w10, [x0, #172]
	ldp	q6, q7, [x0, #128]
	ldp	q16, q17, [x0, #96]
	str	x9, [x8, #160]
	stp	q0, q1, [x8]
	stp	q2, q3, [x8, #32]
	stp	q4, q5, [x8, #64]
	stp	q16, q17, [x8, #96]
	stp	q6, q7, [x8, #128]
	stp	w11, w10, [x8, #168]
	b	LBB16_68
LBB16_34:                               ; %b6.i
	sub	w10, w19, #65
	and	w10, w10, #0xff
	cmp	w10, #6
	b.hs	LBB16_44
; %bb.35:
	mov	w10, #-55                       ; =0xffffffc9
	b	LBB16_46
LBB16_36:                               ; %b16
	and	w9, w19, #0xff
	sub	w10, w9, #98
	cmp	w10, #19
	b.hi	LBB16_55
; %bb.37:                               ; %b16
	mov	w11, #1                         ; =0x1
	mov	w12, #4113                      ; =0x1011
	lsl	w11, w11, w10
	movk	w12, #5, lsl #16
	tst	w11, w12
	b.ne	LBB16_57
; %bb.38:                               ; %b16
	cmp	w10, #19
	b.ne	LBB16_55
; %bb.39:                               ; %b42
	ldur	q0, [x0, #152]
	ldur	q1, [x0, #168]
	ldur	x9, [x0, #132]
	ldr	w10, [x0, #140]
	ldp	q2, q3, [x0, #32]
	str	q0, [sp, #3680]
	ldp	q4, q5, [x0, #96]
	str	q1, [sp, #3696]
	ldp	q1, q0, [x0]
	str	x9, [sp, #3712]
	mov	w9, #3                          ; =0x3
	str	w10, [sp, #3720]
	ldr	x10, [sp, #3712]
	ldp	q6, q7, [x0, #64]
	stp	q1, q0, [x8]
	str	w9, [x8, #128]
	ldr	w9, [sp, #3720]
	ldr	q0, [sp, #3696]
	ldr	q1, [sp, #3680]
	b	LBB16_6
LBB16_40:                               ; %b137_to_b216
	ldp	q0, q1, [x0, #128]
	ldr	q2, [x0, #160]
	ldr	x9, [x0, #176]
	str	q2, [sp, #1552]
	str	q0, [sp, #1520]
	str	q1, [sp, #1536]
	ldp	q0, q1, [x0, #64]
	str	x9, [sp, #1568]
	str	q0, [sp, #1456]
	ldp	q2, q0, [x0, #96]
	str	q1, [sp, #1472]
	str	q0, [sp, #1504]
	ldp	q1, q0, [x0]
	str	q2, [sp, #1488]
	str	q0, [sp, #1408]
	ldp	q2, q0, [x0, #32]
	str	q1, [sp, #1392]
	str	q2, [sp, #1424]
	str	q0, [sp, #1440]
LBB16_41:                               ; %b216
	ldp	q0, q1, [x0, #128]
	ldr	q2, [x0, #160]
	ldr	x9, [x0, #176]
	str	q2, [sp, #1744]
	str	q0, [sp, #1712]
	str	q1, [sp, #1728]
	ldp	q0, q1, [x0, #64]
	str	x9, [sp, #1760]
	and	w9, w19, #0xff
	cmp	w9, #32
	str	q0, [sp, #1648]
	ldp	q2, q0, [x0, #96]
	str	q1, [sp, #1664]
	str	q0, [sp, #1696]
	ldp	q1, q0, [x0]
	str	q2, [sp, #1680]
	str	q1, [sp, #1584]
	str	q0, [sp, #1600]
	ldp	q1, q0, [x0, #32]
	str	q1, [sp, #1616]
	str	q0, [sp, #1632]
	b.hi	LBB16_89
; %bb.42:                               ; %b216
	mov	w9, w19
	mov	w10, #1                         ; =0x1
	and	x9, x9, #0xff
	lsl	x9, x10, x9
	mov	x10, #9728                      ; =0x2600
	movk	x10, #1, lsl #32
	tst	x9, x10
	b.eq	LBB16_89
; %bb.43:                               ; %b217
	ldr	q0, [sp, #1712]
	ldr	q1, [sp, #1728]
	ldr	q2, [sp, #1744]
	ldr	x9, [sp, #1760]
	stp	q0, q1, [x8, #128]
	ldr	q0, [sp, #1648]
	ldr	q1, [sp, #1664]
	str	q2, [x8, #160]
	ldr	q2, [sp, #1680]
	stp	q0, q1, [x8, #64]
	ldr	q0, [sp, #1696]
	ldr	q1, [sp, #1584]
	str	x9, [x8, #176]
	stp	q2, q0, [x8, #96]
	ldr	q0, [sp, #1600]
	ldr	q2, [sp, #1616]
	stp	q1, q0, [x8]
	ldr	q0, [sp, #1632]
	stp	q2, q0, [x8, #32]
	b	LBB16_85
LBB16_44:                               ; %b12.i
	sub	w10, w19, #97
	and	w10, w10, #0xff
	cmp	w10, #6
	b.hs	LBB16_59
; %bb.45:
	mov	w10, #-87                       ; =0xffffffa9
LBB16_46:                               ; %b65
	ldr	w12, [x0, #148]
	lsr	w11, w12, #28
	cbnz	w11, LBB16_183
; %bb.47:                               ; %v128_ok
	ldr	w11, [x0, #144]
	adds	w16, w11, #1
	b.hs	LBB16_183
; %bb.48:                               ; %v133_ok
	add	w10, w10, w19, uxtb
	ldp	x11, x13, [x0, #152]
	ldr	x14, [x0, #176]
	cmp	w16, #4
	add	w12, w10, w12, lsl #4
	ldp	w15, w10, [x0, #168]
	b.ne	LBB16_82
; %bb.49:                               ; %b66
	cmp	w9, #6
	b.ne	LBB16_52
; %bb.50:                               ; %b68
	sub	w9, w12, #14, lsl #12           ; =57344
	cmn	w9, #1025
	b.hi	LBB16_76
; %bb.51:                               ; %b73
	ldur	x9, [x0, #132]
	ldur	w14, [x0, #140]
	ldp	q1, q0, [x0]
	str	x9, [sp, #3552]
	ldp	q2, q3, [x0, #32]
	str	w14, [sp, #3560]
	mov	w9, #6                          ; =0x6
	ldr	x14, [sp, #3552]
	ldp	q4, q5, [x0, #96]
	ldp	q6, q7, [x0, #64]
	str	w9, [x8, #128]
	ldr	w9, [sp, #3560]
	stur	x14, [x8, #132]
	mov	w14, #4                         ; =0x4
	stp	q1, q0, [x8]
	stp	q2, q3, [x8, #32]
	stp	q6, q7, [x8, #64]
	stp	q4, q5, [x8, #96]
	stp	w9, w14, [x8, #140]
	str	w12, [x8, #148]
	stp	x11, x13, [x8, #152]
	stp	w14, w10, [x8, #168]
	str	x13, [x8, #176]
	b	LBB16_85
LBB16_52:                               ; %b76
	and	w17, w12, #0xfffffc00
	mov	w1, #56320                      ; =0xdc00
	cmp	w17, w1
	b.eq	LBB16_80
; %bb.53:                               ; %b76
	mov	w9, #55296                      ; =0xd800
	cmp	w17, w9
	b.ne	LBB16_81
; %bb.54:                               ; %b80
	ldur	w13, [x0, #140]
	ldur	x9, [x0, #132]
	ldp	q0, q1, [x0, #96]
	str	w13, [sp, #3528]
	ldp	q2, q3, [x0, #32]
	ldp	q4, q5, [x0, #64]
	mov	w13, #4                         ; =0x4
	ldp	q7, q6, [x0]
	str	x9, [sp, #3520]
	stur	x9, [x8, #132]
	ldr	w9, [sp, #3528]
	stp	q2, q3, [x8, #32]
	stp	q7, q6, [x8]
	stp	q4, q5, [x8, #64]
	stp	q0, q1, [x8, #96]
	str	w13, [x8, #128]
	stp	w9, w13, [x8, #140]
	str	w12, [x8, #148]
	stp	x11, x11, [x8, #152]
	b	LBB16_84
LBB16_55:                               ; %b16
	sub	w9, w9, #34
	cmp	w9, #58
	b.hi	LBB16_59
; %bb.56:                               ; %b16
	mov	w10, #1                         ; =0x1
	lsl	x9, x10, x9
	mov	x10, #8193                      ; =0x2001
	movk	x10, #1024, lsl #48
	tst	x9, x10
	b.eq	LBB16_59
LBB16_57:                               ; %b39
	ldur	q0, [x0, #132]
	ldur	q1, [x0, #148]
	ldur	q2, [x0, #164]
	ldr	w9, [x0, #180]
	ldp	q4, q5, [x0, #96]
	str	q0, [sp, #3728]
	ldp	q6, q7, [x0, #64]
	str	q1, [sp, #3744]
	ldp	q1, q0, [x0]
	str	q2, [sp, #3760]
	ldp	q2, q3, [x0, #32]
	str	w9, [sp, #3776]
	mov	w9, #1                          ; =0x1
	stp	q1, q0, [x8]
	ldr	q0, [sp, #3728]
	ldr	q1, [sp, #3744]
	str	w9, [x8, #128]
	ldr	w9, [sp, #3776]
	stur	q0, [x8, #132]
	ldr	q0, [sp, #3760]
LBB16_58:                               ; %common.ret
	stp	q2, q3, [x8, #32]
	stp	q6, q7, [x8, #64]
	stp	q4, q5, [x8, #96]
	stur	q1, [x8, #148]
	stur	q0, [x8, #164]
	str	w9, [x8, #180]
	b	LBB16_85
LBB16_59:                               ; %b44
	ldp	q0, q1, [x0]
	ldr	x10, [x0, #160]
	ldp	q2, q3, [x0, #32]
	ldr	x9, [x0, #48]
	ldr	w11, [x0, #172]
	ldp	q4, q5, [x0, #64]
	ldp	q6, q16, [x0, #96]
	ldp	q17, q7, [x0, #128]
	str	x10, [x8, #160]
	mov	w10, #3                         ; =0x3
	b	LBB16_67
LBB16_60:                               ; %b158
	cmp	w9, #11
	b.ne	LBB16_86
; %bb.61:                               ; %b162
	and	w9, w19, #0xff
	cmp	w9, #92
	b.gt	LBB16_114
; %bb.62:                               ; %b162
	sub	w9, w9, #9
	cmp	w9, #60
	b.hi	LBB16_150
; %bb.63:                               ; %b162
	mov	w10, #1                         ; =0x1
	mov	x11, #19                        ; =0x13
	lsl	x10, x10, x9
	movk	x11, #128, lsl #16
	movk	x11, #8, lsl #32
	tst	x10, x11
	b.eq	LBB16_121
LBB16_64:                               ; %b215
	ldp	q0, q1, [x0, #128]
	mov	x20, x8
	ldr	q2, [x0, #160]
	ldr	x9, [x0, #176]
	add	x8, sp, #1392
	str	q0, [sp, #1904]
	str	q1, [sp, #1920]
	ldp	q0, q1, [x0, #64]
	str	q2, [sp, #1936]
	str	x9, [sp, #1952]
	str	q0, [sp, #1840]
	ldp	q2, q0, [x0, #96]
	str	q1, [sp, #1856]
	str	wzr, [sp, #1904]
	str	q0, [sp, #1888]
	ldp	q1, q0, [x0]
	str	q2, [sp, #1872]
	str	q0, [sp, #1792]
	ldp	q2, q0, [x0, #32]
	add	x0, sp, #1776
	str	q1, [sp, #1776]
	str	q2, [sp, #1808]
	str	q0, [sp, #1824]
	bl	_liza___liza_json_done
	add	x0, sp, #1392
	mov	x8, x20
	b	LBB16_41
LBB16_65:                               ; %b105
	ldr	w9, [x0, #140]
	mov	w10, #97                        ; =0x61
	mov	w11, #108                       ; =0x6c
	cmp	w9, #1
	csel	w10, w10, wzr, eq
	cmp	w9, #2
	csel	w10, w11, w10, eq
	cmp	w9, #3
	mov	w11, #115                       ; =0x73
	csel	w10, w11, w10, eq
	cmp	w9, #4
	mov	w9, #101                        ; =0x65
	csel	w10, w9, w10, eq
	mov	w9, #5                          ; =0x5
	cmp	w10, w19, uxtb
	b.eq	LBB16_72
LBB16_66:                               ; %b3
	ldp	q0, q1, [x0]
	ldr	x10, [x0, #160]
	ldp	q2, q3, [x0, #32]
	ldr	x9, [x0, #48]
	ldr	w11, [x0, #172]
	ldp	q4, q5, [x0, #64]
	ldp	q6, q16, [x0, #96]
	ldp	q17, q7, [x0, #128]
	str	x10, [x8, #160]
	mov	w10, #1                         ; =0x1
LBB16_67:                               ; %common.ret
	stp	q2, q3, [x8, #32]
	stp	q4, q5, [x8, #64]
	stp	q6, q16, [x8, #96]
	stp	q17, q7, [x8, #128]
	str	q1, [x8, #16]
	str	q0, [x8]
	stp	w10, w11, [x8, #168]
LBB16_68:                               ; %common.ret
	str	x9, [x8, #176]
	b	LBB16_85
LBB16_69:                               ; %b120
	ldr	w9, [x0, #140]
	mov	w10, #117                       ; =0x75
	cmp	w9, #1
	mov	w9, #108                        ; =0x6c
	csel	w10, w10, w9, eq
	b	LBB16_71
LBB16_70:
	mov	w10, wzr
LBB16_71:                               ; %b125
	mov	w9, #4                          ; =0x4
	cmp	w10, w19, uxtb
	b.ne	LBB16_66
LBB16_72:                               ; %b128
	ldr	w10, [x0, #140]
	adds	w10, w10, #1
	b.hs	LBB16_183
; %bb.73:                               ; %v251_ok
	ldp	q0, q1, [x0, #144]
	cmp	w10, w9
	ldr	x11, [x0, #176]
	str	q0, [sp, #3312]
	str	q1, [sp, #3328]
	str	x11, [sp, #3344]
	b.ne	LBB16_75
; %bb.74:                               ; %b129
	ldp	q0, q1, [x0, #96]
	add	x10, sp, #2989
	ldur	q2, [x0, #124]
	mov	x19, x8
	add	x8, sp, #2936
	str	w9, [sp, #3260]
	str	q0, [sp, #3216]
	str	q1, [sp, #3232]
	ldp	q0, q1, [x0, #32]
	stur	q2, [x10, #255]
	ldur	x10, [x0, #176]
	str	wzr, [sp, #3248]
	str	q0, [sp, #3152]
	ldp	q0, q2, [x0, #64]
	str	q1, [sp, #3168]
	str	x10, [sp, #3296]
	str	q0, [sp, #3184]
	ldp	q0, q1, [x0]
	str	q2, [sp, #3200]
	str	q0, [sp, #3120]
	ldp	q2, q0, [x0, #144]
	add	x0, sp, #3120
	str	q1, [sp, #3136]
	str	q2, [sp, #3264]
	str	q0, [sp, #3280]
	bl	_liza___liza_json_done
	ldp	q0, q1, [x20, #128]
	ldr	q2, [x20, #160]
	ldr	x8, [sp, #3112]
	str	q2, [x19, #160]
	stp	q0, q1, [x19, #128]
	ldp	q0, q1, [x20, #64]
	str	x8, [x19, #176]
	stp	q0, q1, [x19, #64]
	ldp	q2, q0, [x20, #96]
	stp	q2, q0, [x19, #96]
	ldp	q1, q0, [x20]
	stp	q1, q0, [x19]
	ldp	q2, q0, [x20, #32]
	b	LBB16_93
LBB16_75:                               ; %b131
	ldp	q0, q1, [x0]
	ldr	x9, [x0, #128]
	ldp	q2, q3, [x0, #32]
	ldr	w11, [x0, #136]
	ldp	q4, q5, [x0, #96]
	ldp	q6, q7, [x0, #64]
	str	x9, [x8, #128]
	stp	q0, q1, [x8]
	ldr	q0, [sp, #3312]
	ldr	q1, [sp, #3328]
	ldr	x9, [sp, #3344]
	stp	q2, q3, [x8, #32]
	stp	q6, q7, [x8, #64]
	stp	q4, q5, [x8, #96]
	stp	w11, w10, [x8, #136]
	stp	q0, q1, [x8, #144]
	b	LBB16_68
LBB16_76:                               ; %b75
	ldur	x9, [x0, #132]
	ldur	w16, [x0, #140]
	ldp	q1, q0, [x0]
	str	x9, [sp, #3536]
	ldp	q2, q3, [x0, #32]
	str	w16, [sp, #3544]
	mov	w9, #1                          ; =0x1
	ldr	x16, [sp, #3536]
	ldp	q4, q5, [x0, #96]
	ldp	q6, q7, [x0, #64]
	str	w9, [x8, #128]
	ldr	w9, [sp, #3544]
	stur	x16, [x8, #132]
	mov	w16, #4                         ; =0x4
	stp	q1, q0, [x8]
	stp	q2, q3, [x8, #32]
	stp	q6, q7, [x8, #64]
	stp	q4, q5, [x8, #96]
	stur	w9, [x8, #140]
	b	LBB16_83
LBB16_77:                               ; %b12
	ldr	x9, [x0, #48]
	mov	w10, #2                         ; =0x2
	mov	x11, x9
	b	LBB16_79
LBB16_78:                               ; %b13_to_b14
	ldr	x11, [x0, #48]
	ldr	x9, [x0, #152]
	mov	w10, #1                         ; =0x1
LBB16_79:                               ; %b14
	ldp	q0, q1, [x0]
	ldr	q2, [x0, #32]
	ldr	x12, [x0, #120]
	ldr	w13, [x0, #148]
	ldr	x14, [x0, #176]
	str	q2, [sp, #3968]
	ldur	q2, [x0, #72]
	str	q0, [sp, #3936]
	ldur	q0, [x0, #88]
	str	q1, [sp, #3952]
	ldur	q1, [x0, #104]
	str	q0, [sp, #3888]
	ldur	q0, [x0, #56]
	str	q1, [sp, #3904]
	ldur	q1, [x0, #132]
	str	q0, [sp, #3856]
	ldr	q0, [x0, #160]
	str	q1, [sp, #3824]
	ldr	q1, [sp, #3936]
	str	q0, [sp, #3792]
	ldr	q0, [sp, #3952]
	str	q2, [sp, #3872]
	ldr	q2, [sp, #3968]
	stp	q1, q0, [x8]
	ldr	q0, [sp, #3872]
	ldr	q1, [sp, #3888]
	str	q2, [x8, #32]
	ldr	q2, [sp, #3856]
	stur	q0, [x8, #72]
	ldr	q0, [sp, #3904]
	str	x11, [x8, #48]
	mov	w11, w13
	stur	q0, [x8, #104]
	ldr	q0, [sp, #3824]
	str	w10, [x8, #128]
	mov	x10, x14
	stur	q0, [x8, #132]
	ldr	q0, [sp, #3792]
	stur	q1, [x8, #88]
	str	x12, [sp, #3920]
	str	w13, [sp, #3840]
	str	x14, [sp, #3808]
	str	x12, [x8, #120]
	stur	q2, [x8, #56]
	str	w11, [x8, #148]
	str	x9, [x8, #152]
	str	x10, [x8, #176]
	str	q0, [x8, #160]
	b	LBB16_85
LBB16_80:                               ; %b86
	ldur	x14, [x0, #132]
	ldur	w15, [x0, #140]
	ldp	q0, q1, [x0, #96]
	ldp	q2, q3, [x0, #32]
	str	x14, [sp, #3504]
	ldp	q4, q5, [x0, #64]
	str	w15, [sp, #3512]
	ldp	q7, q6, [x0]
	str	w9, [x8, #128]
	mov	w9, w15
	stur	x14, [x8, #132]
	mov	w14, #4                         ; =0x4
	stp	q2, q3, [x8, #32]
	stp	q7, q6, [x8]
	stp	q4, q5, [x8, #64]
	stp	q0, q1, [x8, #96]
	stp	w9, w14, [x8, #140]
	str	w12, [x8, #148]
	stp	x11, x13, [x8, #152]
	str	w14, [x8, #168]
	b	LBB16_175
LBB16_81:
	mov	w9, #1                          ; =0x1
LBB16_82:                               ; %b89
	ldp	q0, q1, [x0, #64]
	ldur	w17, [x0, #140]
	str	w17, [sp, #3368]
	str	q0, [sp, #3440]
	ldp	q0, q2, [x0, #96]
	str	q1, [sp, #3456]
	str	q0, [sp, #3472]
	ldp	q1, q0, [x0]
	str	q2, [sp, #3488]
	str	q0, [sp, #3392]
	ldp	q2, q0, [x0, #32]
	str	q1, [sp, #3376]
	ldr	q1, [sp, #3456]
	ldur	x0, [x0, #132]
	str	w9, [x8, #128]
	ldr	w9, [sp, #3368]
	str	q0, [sp, #3424]
	ldr	q0, [sp, #3440]
	mov	x17, x0
	str	q2, [sp, #3408]
	ldr	q2, [sp, #3472]
	stp	q0, q1, [x8, #64]
	ldr	q0, [sp, #3488]
	ldr	q1, [sp, #3376]
	str	x0, [sp, #3360]
	stp	q2, q0, [x8, #96]
	ldr	q0, [sp, #3392]
	ldr	q2, [sp, #3408]
	stur	x17, [x8, #132]
	stp	q1, q0, [x8]
	ldr	q0, [sp, #3424]
	str	w9, [x8, #140]
	stp	q2, q0, [x8, #32]
LBB16_83:                               ; %common.ret
	stp	w16, w12, [x8, #144]
	stp	x11, x13, [x8, #152]
LBB16_84:                               ; %common.ret
	stp	w15, w10, [x8, #168]
	str	x14, [x8, #176]
LBB16_85:                               ; %common.ret
	add	sp, sp, #1, lsl #12             ; =4096
	add	sp, sp, #336
	ldp	x29, x30, [sp, #32]             ; 16-byte Folded Reload
	ldp	x20, x19, [sp, #16]             ; 16-byte Folded Reload
	ldp	x28, x27, [sp], #48             ; 16-byte Folded Reload
	ret
LBB16_86:                               ; %b159
	cmp	w9, #12
	b.ne	LBB16_97
; %bb.87:                               ; %b159
	and	w10, w19, #0xff
	cmp	w10, #46
	b.ne	LBB16_97
LBB16_88:                               ; %b165
	ldur	q0, [x0, #132]
	ldur	q1, [x0, #148]
	ldur	q2, [x0, #164]
	ldr	w9, [x0, #180]
	ldp	q4, q5, [x0, #96]
	str	q0, [sp, #2096]
	ldp	q6, q7, [x0, #64]
	str	q1, [sp, #2112]
	ldp	q1, q0, [x0]
	str	q2, [sp, #2128]
	ldp	q2, q3, [x0, #32]
	str	w9, [sp, #2144]
	mov	w9, #13                         ; =0xd
	stp	q1, q0, [x8]
	ldr	q0, [sp, #2096]
	ldr	q1, [sp, #2112]
	str	w9, [x8, #128]
	ldr	w9, [sp, #2144]
	stur	q0, [x8, #132]
	ldr	q0, [sp, #2128]
	b	LBB16_58
LBB16_89:                               ; %b219
	ldr	w11, [sp, #1704]
	add	x9, sp, #1584
	cbz	w11, LBB16_106
; %bb.90:                               ; %b220
	ldur	q0, [x9, #56]
	ldur	q1, [x9, #72]
	sub	w10, w11, #1
	ldur	q2, [x9, #88]
	cmp	w10, #64
	stp	q0, q1, [sp]
	ldur	q0, [x9, #104]
	stp	q2, q0, [sp, #32]
	b.hs	LBB16_183
; %bb.91:                               ; %v411_ok
	mov	x12, sp
	ldrb	w12, [x12, w10, uxtw]
	b	LBB16_107
LBB16_92:                               ; %b10
	add	x0, sp, #1, lsl #12             ; =4096
	mov	x19, x8
	add	x8, sp, #3992
	add	x0, x0, #144
	bl	_liza___liza_json_done
	ldr	q0, [x20, #1184]
	ldr	q1, [x20, #1200]
	ldr	q2, [x20, #1216]
	ldr	x8, [sp, #4168]
	stp	q0, q1, [x19, #128]
	ldr	q0, [x20, #1120]
	ldr	q1, [x20, #1136]
	str	q2, [x19, #160]
	ldr	q2, [x20, #1152]
	stp	q0, q1, [x19, #64]
	ldr	q0, [x20, #1168]
	ldr	q1, [x20, #1056]
	str	x8, [x19, #176]
	stp	q2, q0, [x19, #96]
	ldr	q0, [x20, #1072]
	ldr	q2, [x20, #1088]
	stp	q1, q0, [x19]
	ldr	q0, [x20, #1104]
LBB16_93:                               ; %common.ret
	stp	q2, q0, [x19, #32]
	b	LBB16_85
LBB16_94:                               ; %b143
	ldp	q0, q1, [x0, #64]
	ldr	w9, [x0, #180]
	str	w9, [sp, #2784]
	str	q0, [sp, #2864]
	ldp	q2, q0, [x0, #96]
	str	q1, [sp, #2880]
	ldr	w9, [sp, #2784]
	str	q0, [sp, #2912]
	ldp	q1, q0, [x0]
	str	q2, [sp, #2896]
	str	w9, [sp, #2592]
	and	w9, w19, #0xff
	str	q0, [sp, #2816]
	ldp	q2, q0, [x0, #32]
	str	q1, [sp, #2800]
	ldur	q1, [x0, #164]
	cmp	w9, #48
	mov	w9, #11                         ; =0xb
	str	q0, [sp, #2848]
	ldur	q0, [x0, #148]
	cinc	w9, w9, ne
	str	q2, [sp, #2832]
	ldur	q2, [x0, #132]
	str	q0, [sp, #2752]
	ldr	q0, [sp, #2880]
	str	q1, [sp, #2768]
	ldr	q1, [sp, #2864]
	str	q0, [sp, #2688]
	ldr	q0, [sp, #2912]
	str	q2, [sp, #2736]
	ldr	q2, [sp, #2896]
	str	q0, [sp, #2720]
	ldr	q0, [sp, #2816]
	str	q1, [sp, #2672]
	ldr	q1, [sp, #2800]
	str	q0, [sp, #2624]
	ldr	q0, [sp, #2848]
	str	q2, [sp, #2704]
	ldr	q2, [sp, #2832]
	str	q0, [sp, #2656]
	ldr	q0, [sp, #2768]
	str	q1, [sp, #2608]
	ldr	q1, [sp, #2752]
	str	q0, [sp, #2576]
	ldr	q0, [sp, #2736]
	str	q2, [sp, #2640]
	str	q1, [sp, #2560]
	str	q0, [sp, #2544]
LBB16_95:                               ; %b151
	ldr	q0, [sp, #2672]
	ldr	q1, [sp, #2688]
	ldr	q2, [sp, #2720]
	ldr	w10, [sp, #2592]
	str	q0, [sp, #2480]
	ldr	q0, [sp, #2704]
	str	q1, [sp, #2496]
	ldr	q1, [sp, #2608]
	str	q0, [sp, #2512]
	ldr	q0, [sp, #2624]
	str	q2, [sp, #2528]
	ldr	q2, [sp, #2640]
	str	q0, [sp, #2432]
	ldr	q0, [sp, #2656]
	str	q1, [sp, #2416]
	ldr	q1, [sp, #2560]
	str	q2, [sp, #2448]
	ldr	q2, [sp, #2544]
	str	q0, [sp, #2464]
	ldr	q0, [sp, #2576]
	str	w10, [sp, #2400]
	sub	w10, w9, #15
	cmp	w10, #1
	str	q0, [sp, #2384]
	str	q1, [sp, #2368]
	str	q2, [sp, #2352]
	b.hi	LBB16_104
; %bb.96:                               ; %b155
	mov	w9, #17                         ; =0x11
	add	x10, sp, #2544
	add	x11, sp, #2608
	b	LBB16_105
LBB16_97:                               ; %b167
	cmp	w9, #16
	b.hi	LBB16_151
; %bb.98:                               ; %b167
	mov	w10, #1                         ; =0x1
	mov	w11, #22528                     ; =0x5800
	lsl	w10, w10, w9
	tst	w10, w11
	b.ne	LBB16_128
; %bb.99:                               ; %b167
	mov	w11, #9216                      ; =0x2400
	movk	w11, #1, lsl #16
	tst	w10, w11
	b.ne	LBB16_150
; %bb.100:                              ; %b167
	cmp	w9, #15
	b.ne	LBB16_151
; %bb.101:                              ; %b183
	and	w9, w19, #0xff
	cmp	w9, #45
	b.eq	LBB16_103
; %bb.102:                              ; %b183
	cmp	w9, #43
	b.ne	LBB16_150
LBB16_103:                              ; %b189
	ldur	q0, [x0, #132]
	ldur	q1, [x0, #148]
	ldur	q2, [x0, #164]
	ldr	w9, [x0, #180]
	ldp	q4, q5, [x0, #96]
	str	q0, [sp, #1968]
	ldp	q6, q7, [x0, #64]
	str	q1, [sp, #1984]
	ldp	q1, q0, [x0]
	str	q2, [sp, #2000]
	ldp	q2, q3, [x0, #32]
	str	w9, [sp, #2016]
	mov	w9, #16                         ; =0x10
	stp	q1, q0, [x8]
	ldr	q0, [sp, #1968]
	ldr	q1, [sp, #1984]
	str	w9, [x8, #128]
	ldr	w9, [sp, #2016]
	stur	q0, [x8, #132]
	ldr	q0, [sp, #2000]
	b	LBB16_58
LBB16_104:
	add	x10, sp, #2352
	add	x11, sp, #2416
LBB16_105:                              ; %b157
	ldp	q0, q1, [x11, #64]
	str	w9, [x8, #128]
	str	q0, [sp, #2288]
	ldp	q0, q2, [x11, #96]
	str	q1, [sp, #2304]
	str	q0, [sp, #2320]
	ldp	q1, q0, [x11]
	str	q2, [sp, #2336]
	str	q0, [sp, #2240]
	ldp	q2, q0, [x11, #32]
	str	q1, [sp, #2224]
	ldr	w11, [x10, #48]
	str	q0, [sp, #2272]
	ldp	q1, q0, [x10, #16]
	str	q2, [sp, #2256]
	ldr	q2, [x10]
	str	w11, [sp, #2208]
	str	q0, [sp, #2192]
	ldr	q0, [sp, #2272]
	ldr	w10, [sp, #2208]
	str	q1, [sp, #2176]
	ldr	q1, [sp, #2256]
	str	q2, [sp, #2160]
	ldr	q2, [sp, #2240]
	stp	q1, q0, [x8, #32]
	ldr	q0, [sp, #2224]
	ldr	q1, [sp, #2336]
	str	w10, [x8, #180]
	stp	q0, q2, [x8]
	ldr	q0, [sp, #2320]
	ldr	q2, [sp, #2304]
	stp	q0, q1, [x8, #96]
	ldr	q0, [sp, #2288]
	ldr	q1, [sp, #2176]
	stp	q0, q2, [x8, #64]
	ldr	q0, [sp, #2192]
	ldr	q2, [sp, #2160]
	stur	q1, [x8, #148]
	stur	q0, [x8, #164]
	stur	q2, [x8, #132]
	b	LBB16_85
LBB16_106:
	mov	w12, wzr
LBB16_107:                              ; %b222
	and	w10, w19, #0xff
	cmp	w10, #125
	b.eq	LBB16_117
; %bb.108:                              ; %b222
	cmp	w10, #93
	b.ne	LBB16_110
; %bb.109:                              ; %b223
	sub	w10, w12, #1
	cmp	w10, #1
	b.ls	LBB16_137
LBB16_110:                              ; %b240
	cmp	w12, #4
	add	x10, sp, #1584
	b.le	LBB16_123
; %bb.111:                              ; %b240
	cmp	w12, #5
	b.eq	LBB16_145
; %bb.112:                              ; %b240
	cmp	w12, #8
	b.eq	LBB16_125
; %bb.113:                              ; %b240
	cmp	w12, #7
	b.eq	LBB16_130
	b	LBB16_139
LBB16_114:                              ; %b162
	cmp	w9, #93
	b.eq	LBB16_64
; %bb.115:                              ; %b162
	cmp	w9, #101
	b.eq	LBB16_129
LBB16_116:                              ; %b203
	cmp	w9, #125
	b.eq	LBB16_64
	b	LBB16_150
LBB16_117:                              ; %b232
	cmp	w12, #4
	b.le	LBB16_135
; %bb.118:                              ; %b232
	cmp	w12, #5
	b.eq	LBB16_173
; %bb.119:                              ; %b232
	cmp	w12, #8
	b.eq	LBB16_173
; %bb.120:                              ; %b232
	cmp	w12, #7
	b.eq	LBB16_137
	b	LBB16_139
LBB16_121:                              ; %b162
	cmp	x9, #37
	b.eq	LBB16_88
; %bb.122:                              ; %b162
	cmp	x9, #60
	b.eq	LBB16_129
	b	LBB16_150
LBB16_123:                              ; %b240
	cmp	w12, #2
	b.eq	LBB16_130
; %bb.124:                              ; %b240
	cmp	w12, #4
	b.ne	LBB16_139
LBB16_125:                              ; %b262
	and	w10, w19, #0xff
	cmp	w10, #34
	b.ne	LBB16_173
; %bb.126:                              ; %b266
	ldr	q0, [sp, #1648]
	ldr	q1, [sp, #1664]
	mov	w10, #1                         ; =0x1
	ldr	q2, [sp, #1696]
	strb	w10, [sp, #1068]
	stp	q0, q1, [x8, #64]
	ldr	q0, [sp, #1680]
	ldr	q1, [sp, #1584]
	str	w10, [x8, #128]
	stp	q0, q2, [x8, #96]
	ldr	q0, [sp, #1600]
	ldr	q2, [sp, #1616]
	strb	w10, [x8, #132]
LBB16_127:                              ; %common.ret
	stp	q1, q0, [x8]
	ldr	q0, [sp, #1632]
	stp	q2, q0, [x8, #32]
	ldur	q0, [x9, #133]
	stur	q0, [x8, #133]
	ldur	q0, [x9, #149]
	stur	q0, [x8, #149]
	ldur	q0, [x9, #165]
	ldr	w9, [sp, #1764]
	stur	q0, [x8, #165]
	str	w9, [x8, #180]
	b	LBB16_85
LBB16_128:                              ; %b174
	orr	w10, w19, #0x20
	and	w10, w10, #0xff
	cmp	w10, #101
	b.ne	LBB16_149
LBB16_129:                              ; %b180
	ldur	q0, [x0, #132]
	ldur	q1, [x0, #148]
	ldur	q2, [x0, #164]
	ldr	w9, [x0, #180]
	ldp	q4, q5, [x0, #96]
	str	q0, [sp, #2032]
	ldp	q6, q7, [x0, #64]
	str	q1, [sp, #2048]
	ldp	q1, q0, [x0]
	str	q2, [sp, #2064]
	ldp	q2, q3, [x0, #32]
	str	w9, [sp, #2080]
	mov	w9, #15                         ; =0xf
	stp	q1, q0, [x8]
	ldr	q0, [sp, #2032]
	ldr	q1, [sp, #2048]
	str	w9, [x8, #128]
	ldr	w9, [sp, #2080]
	stur	q0, [x8, #132]
	ldr	q0, [sp, #2064]
	b	LBB16_58
LBB16_130:                              ; %b244
	and	w13, w19, #0xff
	cmp	w13, #44
	b.ne	LBB16_173
; %bb.131:                              ; %b248
	ldur	q0, [x9, #56]
	ldur	q1, [x9, #72]
	subs	w11, w11, #1
	ldur	q2, [x9, #88]
	ldur	q3, [x9, #104]
	cset	w9, lo
	cmp	w12, #2
	b.ne	LBB16_154
; %bb.132:                              ; %b249
	cbnz	w9, LBB16_183
; %bb.133:                              ; %v459_ok
	cmp	w11, #64
	b.hs	LBB16_183
; %bb.134:
	mov	w12, #3                         ; =0x3
	add	x9, sp, #1328
	b	LBB16_157
LBB16_135:                              ; %b232
	cmp	w12, #2
	b.eq	LBB16_173
; %bb.136:                              ; %b232
	cmp	w12, #4
	b.ne	LBB16_139
LBB16_137:                              ; %b229
	subs	w10, w11, #1
	b.lo	LBB16_183
; %bb.138:                              ; %v426_ok
	ldr	q0, [sp, #1648]
	ldr	q1, [sp, #1664]
	ldr	q2, [sp, #1680]
	ldr	x11, [sp, #1696]
	str	w10, [x8, #120]
	stp	q0, q1, [x8, #64]
	ldr	q0, [sp, #1584]
	ldr	q1, [sp, #1600]
	str	q2, [x8, #96]
	ldr	q2, [sp, #1616]
	stp	q0, q1, [x8]
	ldr	q0, [sp, #1632]
	ldur	q1, [x9, #168]
	str	x11, [x8, #112]
	stp	q2, q0, [x8, #32]
	ldur	q0, [x9, #156]
	stur	q1, [x8, #168]
	stur	q0, [x8, #156]
	ldur	q0, [x9, #140]
	stur	q0, [x8, #140]
	ldur	q0, [x9, #124]
	stur	q0, [x8, #124]
	b	LBB16_85
LBB16_139:                              ; %b259
	cbnz	w11, LBB16_141
; %bb.140:                              ; %b259
	ldrb	w10, [sp, #1708]
	tbnz	w10, #0, LBB16_173
LBB16_141:                              ; %b273
	and	w10, w19, #0xff
	cmp	w10, #90
	b.gt	LBB16_158
; %bb.142:                              ; %b273
	cmp	w10, #34
	b.eq	LBB16_167
; %bb.143:                              ; %b273
	cmp	w10, #45
	b.ne	LBB16_162
; %bb.144:                              ; %b289
	ldr	q0, [sp, #1648]
	ldr	q1, [sp, #1664]
	mov	w10, #10                        ; =0xa
	ldr	q2, [sp, #1696]
	str	w10, [x8, #128]
	ldr	w10, [sp, #1764]
	stp	q0, q1, [x8, #64]
	ldr	q0, [sp, #1680]
	ldr	q1, [sp, #1584]
	str	w10, [x8, #180]
	stp	q0, q2, [x8, #96]
	ldr	q0, [sp, #1600]
	ldr	q2, [sp, #1616]
	stp	q1, q0, [x8]
	ldr	q0, [sp, #1632]
	ldur	q1, [x9, #164]
	stp	q2, q0, [x8, #32]
	ldur	q0, [x9, #148]
	stur	q1, [x8, #164]
	stur	q0, [x8, #148]
	ldur	q0, [x9, #132]
	stur	q0, [x8, #132]
	b	LBB16_85
LBB16_145:                              ; %b253
	and	w12, w19, #0xff
	cmp	w12, #58
	b.ne	LBB16_173
; %bb.146:                              ; %b257
	subs	w11, w11, #1
	b.lo	LBB16_183
; %bb.147:                              ; %v483_ok
	cmp	w11, #64
	b.hs	LBB16_183
; %bb.148:                              ; %v484_ok
	ldur	q0, [x9, #56]
	ldur	q1, [x9, #72]
	mov	w12, #6                         ; =0x6
	ldur	q2, [x9, #88]
	str	q0, [sp, #1072]
	ldur	q0, [x9, #104]
	add	x9, sp, #1072
	str	q1, [sp, #1088]
	ldr	q1, [sp, #1600]
	str	q0, [sp, #1120]
	ldr	q0, [sp, #1584]
	str	q2, [sp, #1104]
	ldr	q2, [sp, #1616]
	strb	w12, [x9, w11, uxtw]
	ldr	x9, [sp, #1632]
	stp	q0, q1, [x8]
	ldr	q0, [sp, #1072]
	ldr	q1, [sp, #1088]
	str	q2, [x8, #32]
	ldur	q2, [x10, #136]
	stur	q0, [x8, #56]
	ldr	q0, [sp, #1104]
	stur	q1, [x8, #72]
	ldr	q1, [sp, #1120]
	stur	q0, [x8, #88]
	ldur	q0, [x10, #168]
	stur	q1, [x8, #104]
	ldur	q1, [x10, #152]
	stur	q0, [x8, #168]
	ldur	q0, [x10, #120]
	str	x9, [x8, #48]
	stur	q1, [x8, #152]
	stur	q2, [x8, #136]
	stur	q0, [x8, #120]
	b	LBB16_85
LBB16_149:                              ; %b191
	cmp	w9, #13
	b.ne	LBB16_151
LBB16_150:                              ; %b140
	ldp	q0, q1, [x0]
	ldr	x10, [x0, #160]
	ldp	q2, q3, [x0, #32]
	ldr	x9, [x0, #48]
	ldr	w11, [x0, #172]
	ldp	q4, q5, [x0, #64]
	ldp	q6, q16, [x0, #96]
	ldp	q17, q7, [x0, #128]
	str	x10, [x8, #160]
	mov	w10, #2                         ; =0x2
	b	LBB16_67
LBB16_151:                              ; %b203
	and	w9, w19, #0xff
	cmp	w9, #44
	b.hi	LBB16_153
; %bb.152:                              ; %b203
	and	x10, x19, #0xff
	mov	w11, #1                         ; =0x1
	lsl	x10, x11, x10
	mov	x11, #9728                      ; =0x2600
	movk	x11, #4097, lsl #32
	tst	x10, x11
	b.ne	LBB16_64
LBB16_153:                              ; %b203
	cmp	w9, #93
	b.ne	LBB16_116
	b	LBB16_64
LBB16_154:                              ; %b250
	cbnz	w9, LBB16_183
; %bb.155:                              ; %v467_ok
	cmp	w11, #64
	b.hs	LBB16_183
; %bb.156:
	mov	w12, #8                         ; =0x8
	add	x9, sp, #1264
LBB16_157:                              ; %b251
	stp	q0, q1, [x9]
	ldr	q0, [sp, #1584]
	ldr	q1, [sp, #1600]
	stp	q2, q3, [x9, #32]
	ldr	q2, [sp, #1616]
	str	q0, [sp, #1200]
	ldur	q0, [x10, #168]
	str	q1, [sp, #1216]
	ldur	q1, [x10, #152]
	str	q0, [sp, #1184]
	ldur	q0, [x10, #120]
	str	q2, [sp, #1232]
	ldur	q2, [x10, #136]
	str	q1, [sp, #1168]
	ldr	q1, [sp, #1216]
	str	q0, [sp, #1136]
	ldr	q0, [sp, #1232]
	strb	w12, [x9, w11, uxtw]
	ldr	x11, [sp, #1632]
	stp	q1, q0, [x8, #16]
	ldr	q0, [sp, #1200]
	str	q2, [sp, #1152]
	mov	x10, x11
	str	q0, [x8]
	ldp	q2, q0, [x9]
	str	x11, [sp, #1248]
	str	x10, [x8, #48]
	stur	q0, [x8, #72]
	ldp	q1, q0, [x9, #32]
	stur	q2, [x8, #56]
	ldr	q2, [sp, #1168]
	stur	q1, [x8, #88]
	ldr	q1, [sp, #1184]
	stur	q0, [x8, #104]
	ldr	q0, [sp, #1152]
	stur	q1, [x8, #168]
	ldr	q1, [sp, #1136]
	stur	q2, [x8, #152]
	stur	q0, [x8, #136]
	stur	q1, [x8, #120]
	b	LBB16_85
LBB16_158:                              ; %b273
	cmp	w10, #123
	b.eq	LBB16_160
; %bb.159:                              ; %b273
	cmp	w10, #91
	b.ne	LBB16_162
LBB16_160:                              ; %b277
	cmp	w11, #64
	b.ne	LBB16_164
; %bb.161:                              ; %b279
	ldr	q0, [sp, #1712]
	ldr	q1, [sp, #1728]
	ldr	q2, [sp, #1648]
	ldr	q4, [sp, #1680]
	ldr	q3, [sp, #1696]
	ldr	x9, [sp, #1744]
	stp	q0, q1, [x8, #128]
	ldr	q0, [sp, #1632]
	ldr	q1, [sp, #1616]
	str	q3, [x8, #112]
	stp	q0, q2, [x8, #48]
	ldr	q0, [sp, #1664]
	ldr	q2, [sp, #1600]
	str	x9, [x8, #160]
	mov	w9, #7                          ; =0x7
	b	LBB16_174
LBB16_162:                              ; %b291
	sub	w10, w19, #48
	and	w10, w10, #0xff
	cmp	w10, #9
	b.hi	LBB16_168
; %bb.163:                              ; %b292
	ldr	q0, [sp, #1648]
	ldr	q1, [sp, #1664]
	ldr	q2, [sp, #1680]
	ldr	w10, [sp, #1764]
	stp	q0, q1, [sp, #544]
	ldr	q0, [sp, #1696]
	ldr	q1, [sp, #1584]
	str	w10, [sp, #464]
	stp	q2, q0, [sp, #576]
	ldr	q0, [sp, #1600]
	ldr	q2, [sp, #1616]
	ldr	w10, [sp, #464]
	stp	q1, q0, [sp, #480]
	ldr	q0, [sp, #1632]
	ldur	q1, [x9, #164]
	str	w10, [x8, #180]
	stp	q2, q0, [sp, #512]
	ldur	q0, [x9, #148]
	ldur	q2, [x9, #132]
	and	w9, w19, #0xff
	stp	q0, q1, [sp, #432]
	ldp	q1, q0, [sp, #544]
	str	q2, [sp, #416]
	cmp	w9, #48
	mov	w9, #11                         ; =0xb
	cinc	w9, w9, ne
	stp	q1, q0, [x8, #64]
	ldp	q2, q0, [sp, #576]
	str	w9, [x8, #128]
	stp	q2, q0, [x8, #96]
	ldp	q1, q0, [sp, #480]
	stp	q1, q0, [x8]
	ldp	q1, q0, [sp, #512]
	stp	q1, q0, [x8, #32]
	ldp	q1, q0, [sp, #432]
	stur	q0, [x8, #164]
	ldr	q0, [sp, #416]
	stur	q1, [x8, #148]
	stur	q0, [x8, #132]
	b	LBB16_85
LBB16_164:                              ; %b281
	mov	x20, x8
	add	x8, sp, #880
	add	x0, sp, #1584
	bl	_liza___liza_json_done
	and	w9, w19, #0xff
	ldr	w8, [sp, #1000]
	cmp	w9, #91
	b.ne	LBB16_176
; %bb.165:                              ; %b282
	cmp	w8, #64
	b.hs	LBB16_183
; %bb.166:
	mov	w11, #1                         ; =0x1
	add	x10, sp, #816
	b	LBB16_178
LBB16_167:                              ; %b286
	ldr	q0, [sp, #1648]
	ldr	q1, [sp, #1664]
	mov	w10, #1                         ; =0x1
	ldr	q2, [sp, #1696]
	strb	wzr, [sp, #620]
	stp	q0, q1, [x8, #64]
	ldr	q0, [sp, #1680]
	ldr	q1, [sp, #1584]
	str	w10, [x8, #128]
	stp	q0, q2, [x8, #96]
	ldr	q0, [sp, #1600]
	ldr	q2, [sp, #1616]
	strb	wzr, [x8, #132]
	b	LBB16_127
LBB16_168:                              ; %b297
	and	w9, w19, #0xff
	sub	w9, w9, #102
	cmp	w9, #14
	b.hi	LBB16_173
; %bb.169:                              ; %b297
	mov	w10, #1                         ; =0x1
	lsl	w9, w10, w9
	mov	w10, #16641                     ; =0x4101
	tst	w9, w10
	b.eq	LBB16_173
; %bb.170:                              ; %b304
	mov	x10, x8
	and	w9, w19, #0xff
	ldr	w8, [sp, #1716]
	add	x12, sp, #1584
	cmp	w9, #102
	add	x11, x12, #144
	b.eq	LBB16_179
; %bb.171:                              ; %b304
	cmp	w9, #116
	b.ne	LBB16_180
; %bb.172:
	mov	w9, #1                          ; =0x1
	b	LBB16_182
LBB16_173:                              ; %b246
	ldr	q0, [sp, #1712]
	ldr	q1, [sp, #1728]
	ldr	q2, [sp, #1648]
	ldr	q4, [sp, #1680]
	ldr	x9, [sp, #1744]
	ldr	q3, [sp, #1696]
	stp	q0, q1, [x8, #128]
	ldr	q0, [sp, #1632]
	ldr	q1, [sp, #1616]
	str	x9, [x8, #160]
	mov	w9, #1                          ; =0x1
	stp	q0, q2, [x8, #48]
	ldr	q0, [sp, #1664]
	ldr	q2, [sp, #1600]
	str	q3, [x8, #112]
LBB16_174:                              ; %common.ret
	stp	q0, q4, [x8, #80]
	ldr	q0, [sp, #1584]
	stp	q0, q2, [x8]
	ldr	w10, [sp, #1756]
	ldr	x11, [sp, #1632]
	str	q1, [x8, #32]
	str	w9, [x8, #168]
LBB16_175:                              ; %common.ret
	str	w10, [x8, #172]
	str	x11, [x8, #176]
	b	LBB16_85
LBB16_176:                              ; %b283
	cmp	w8, #64
	b.hs	LBB16_183
; %bb.177:
	mov	w11, #4                         ; =0x4
	add	x10, sp, #752
LBB16_178:                              ; %v545_ok
	add	x12, sp, #880
	add	x13, sp, #624
	ldur	q0, [x12, #56]
	ldur	q1, [x12, #72]
	ldur	q2, [x12, #88]
	stp	q0, q1, [x10]
	ldur	q0, [x12, #104]
	stp	q2, q0, [x10, #32]
	ldp	q0, q1, [sp, #880]
	ldr	q2, [sp, #912]
	strb	w11, [x10, x8]
	ldr	x11, [sp, #928]
	add	w8, w8, #1
	stp	q0, q1, [sp, #688]
	ldur	q0, [x12, #168]
	ldur	q1, [x12, #156]
	str	q2, [sp, #720]
	ldur	q2, [x12, #140]
	stur	q0, [x13, #44]
	ldur	q0, [x12, #124]
	stp	q2, q1, [sp, #640]
	str	q0, [sp, #624]
	ldp	q1, q0, [sp, #704]
	str	x11, [sp, #736]
	str	x11, [x20, #48]
	stp	q1, q0, [x20, #16]
	ldr	q0, [sp, #688]
	str	w8, [x20, #120]
	str	q0, [x20]
	ldp	q2, q0, [x10]
	stur	q0, [x20, #72]
	ldp	q1, q0, [x10, #32]
	stur	q2, [x20, #56]
	ldr	q2, [sp, #624]
	stur	q0, [x20, #104]
	ldur	q0, [x13, #44]
	stur	q1, [x20, #88]
	stur	q0, [x20, #168]
	ldp	q0, q1, [sp, #640]
	stur	q2, [x20, #124]
	stur	q1, [x20, #156]
	stur	q0, [x20, #140]
	b	LBB16_85
LBB16_179:
	mov	w9, #2                          ; =0x2
	b	LBB16_181
LBB16_180:                              ; %b309
	mov	w9, #3                          ; =0x3
LBB16_181:                              ; %b310_to_b311
	ldr	q0, [sp, #1648]
	ldr	q1, [sp, #1664]
	ldr	q2, [sp, #1696]
	ldr	x12, [x11, #32]
	stp	q0, q1, [sp, #352]
	ldr	q0, [sp, #1680]
	ldr	q1, [sp, #1584]
	str	x12, [sp, #272]
	add	x12, sp, #288
	stp	q0, q2, [sp, #384]
	ldr	q0, [sp, #1600]
	ldr	q2, [sp, #1616]
	stp	q1, q0, [sp, #288]
	ldr	q0, [sp, #1632]
	stp	q2, q0, [sp, #320]
	ldp	q1, q0, [x11]
	add	x11, sp, #240
	stp	q1, q0, [sp, #240]
LBB16_182:                              ; %b311
	ldp	q0, q1, [x12, #64]
	stp	q0, q1, [sp, #176]
	ldp	q0, q2, [x12, #96]
	stp	q0, q2, [sp, #208]
	ldp	q1, q0, [x12]
	stp	q1, q0, [sp, #112]
	ldp	q2, q0, [x12, #32]
	ldr	x12, [x11, #32]
	stp	q2, q0, [sp, #144]
	ldp	q1, q0, [x11]
	str	x12, [sp, #96]
	mov	w11, #20                        ; =0x14
	stp	w11, w8, [x10, #128]
	ldr	x11, [sp, #96]
	mov	w8, #1                          ; =0x1
	stp	q1, q0, [sp, #64]
	ldp	q0, q2, [sp, #144]
	stp	w9, w8, [x10, #136]
	str	x11, [x10, #176]
	stp	q0, q2, [x10, #32]
	ldp	q0, q1, [sp, #112]
	stp	q0, q1, [x10]
	ldp	q0, q2, [sp, #208]
	stp	q0, q2, [x10, #96]
	ldp	q0, q1, [sp, #176]
	stp	q0, q1, [x10, #64]
	ldp	q1, q0, [sp, #64]
	stp	q1, q0, [x10, #144]
	b	LBB16_85
LBB16_183:                              ; %v17_trap
	brk	#0x1
                                        ; -- End function
	.globl	_liza_json.feed                 ; -- Begin function liza_json.feed
	.p2align	2
_liza_json.feed:                        ; @liza_json.feed
; %bb.0:                                ; %b0
	stp	x28, x27, [sp, #-96]!           ; 16-byte Folded Spill
	stp	x26, x25, [sp, #16]             ; 16-byte Folded Spill
	stp	x24, x23, [sp, #32]             ; 16-byte Folded Spill
	stp	x22, x21, [sp, #48]             ; 16-byte Folded Spill
	stp	x20, x19, [sp, #64]             ; 16-byte Folded Spill
	stp	x29, x30, [sp, #80]             ; 16-byte Folded Spill
	sub	sp, sp, #512
	ldr	w10, [x0, #168]
	mov	x19, x8
	cbz	w10, LBB17_2
; %bb.1:                                ; %b1
	ldp	q0, q1, [x0]
	ldr	x8, [x0, #176]
	ldp	q2, q3, [x0, #32]
	ldr	q17, [x0, #128]
	ldp	q4, q5, [x0, #64]
	ldp	q6, q7, [x0, #96]
	ldp	q18, q16, [x0, #144]
	str	x8, [x19, #176]
	stp	q1, q2, [x19, #16]
	stp	q3, q4, [x19, #48]
	stp	q5, q6, [x19, #80]
	stp	q7, q17, [x19, #112]
	stp	q18, q16, [x19, #144]
	str	q0, [x19]
	b	LBB17_18
LBB17_2:                                ; %b3_to_b4
	mov	x8, x0
	ldur	q0, [x0, #120]
	mov	w9, w2
	ldur	q1, [x8, #136]
	mov	x20, x1
	ldr	x0, [x0]
	ldp	x1, x2, [x8, #8]
	ldr	w3, [x8, #24]
	stp	q0, q1, [sp, #448]
	ldur	q0, [x8, #152]
	ldur	q1, [x8, #168]
	ldp	w6, w28, [x8, #32]
	stp	q0, q1, [sp, #480]
	ldur	q0, [x8, #56]
	ldur	q1, [x8, #72]
	ldrb	w4, [x8, #28]
	ldrb	w5, [x8, #29]
	ldrh	w27, [x8, #30]
	stp	q0, q1, [sp, #384]
	ldur	q0, [x8, #88]
	ldur	q1, [x8, #104]
	ldp	x7, x23, [x8, #40]
	stp	q0, q1, [sp, #416]
	cbz	w9, LBB17_12
; %bb.3:                                ; %v8_ok.lr.ph
	add	x22, sp, #200
	add	x24, sp, #200
	add	x25, sp, #16
	mov	w26, w9
LBB17_4:                                ; %v8_ok
                                        ; =>This Inner Loop Header: Depth=1
	ldrb	w21, [x20], #1
	strb	w21, [sp]
	bl	_liza_utf8_stream.feed_byte
	ldp	q0, q1, [sp, #448]
	cmp	w6, #2
	strh	w27, [sp, #230]
	stp	x0, x1, [sp, #200]
	stur	q0, [x24, #120]
	stur	q1, [x24, #136]
	ldp	q0, q1, [sp, #480]
	str	x2, [sp, #216]
	str	w3, [sp, #224]
	stur	q0, [x24, #152]
	stur	q1, [x24, #168]
	ldp	q0, q1, [sp, #384]
	strb	w4, [sp, #228]
	strb	w5, [sp, #229]
	stur	q0, [x24, #56]
	stur	q1, [x24, #72]
	ldp	q0, q1, [sp, #416]
	stp	w6, w28, [sp, #232]
	stp	x7, x23, [sp, #240]
	stur	q0, [x24, #88]
	stur	q1, [x24, #104]
	b.eq	LBB17_7
; %bb.5:                                ; %v8_ok
                                        ;   in Loop: Header=BB17_4 Depth=1
	cmp	w6, #1
	b.ne	LBB17_8
; %bb.6:                                ; %b1.i
                                        ;   in Loop: Header=BB17_4 Depth=1
	mov	w9, wzr
	mov	w8, wzr
	cmp	w9, #1
	b.eq	LBB17_9
	b	LBB17_13
LBB17_7:                                ; %b4.i
                                        ;   in Loop: Header=BB17_4 Depth=1
	mov	w9, wzr
	mov	w8, #1                          ; =0x1
	cmp	w9, #1
	b.eq	LBB17_9
	b	LBB17_13
LBB17_8:                                ;   in Loop: Header=BB17_4 Depth=1
	mov	w8, wzr
	mov	x7, xzr
	mov	w9, #1                          ; =0x1
	cmp	w9, #1
	b.ne	LBB17_13
LBB17_9:                                ; %b13
                                        ;   in Loop: Header=BB17_4 Depth=1
	add	x8, sp, #16
	add	x0, sp, #200
	mov	w1, w21
	bl	_liza___liza_json_step
	ldr	w8, [sp, #184]
	cbnz	w8, LBB17_15
; %bb.10:                               ; %b16
                                        ;   in Loop: Header=BB17_4 Depth=1
	ldr	x8, [sp, #64]
	adds	x23, x8, #1
	b.hs	LBB17_19
; %bb.11:                               ; %v32_ok
                                        ;   in Loop: Header=BB17_4 Depth=1
	ldur	q0, [x25, #120]
	ldur	q1, [x25, #136]
	subs	x26, x26, #1
	ldp	x0, x1, [sp, #16]
	ldr	x2, [sp, #32]
	stp	q0, q1, [sp, #448]
	ldur	q0, [x25, #152]
	ldur	q1, [x25, #168]
	ldr	w3, [sp, #40]
	ldrb	w4, [sp, #44]
	ldrb	w5, [sp, #45]
	stp	q0, q1, [sp, #480]
	ldur	q0, [x25, #56]
	ldur	q1, [x25, #72]
	ldrh	w27, [sp, #46]
	ldr	x7, [sp, #56]
	stp	q0, q1, [sp, #384]
	ldur	q0, [x25, #88]
	ldur	q1, [x25, #104]
	ldp	w6, w28, [sp, #48]
	stp	q0, q1, [sp, #416]
	b.ne	LBB17_4
LBB17_12:                               ; %b6
	ldp	q0, q1, [sp, #448]
	stp	x0, x1, [x19]
	str	x2, [x19, #16]
	str	w3, [x19, #24]
	stur	q0, [x19, #120]
	stur	q1, [x19, #136]
	ldp	q0, q1, [sp, #480]
	strb	w4, [x19, #28]
	strb	w5, [x19, #29]
	stur	q0, [x19, #152]
	stur	q1, [x19, #168]
	ldp	q0, q1, [sp, #384]
	strh	w27, [x19, #30]
	stp	w6, w28, [x19, #32]
	stur	q0, [x19, #56]
	stur	q1, [x19, #72]
	ldp	q0, q1, [sp, #416]
	stp	x7, x23, [x19, #40]
	stur	q0, [x19, #88]
	stur	q1, [x19, #104]
	b	LBB17_18
LBB17_13:                               ; %b9
	ldp	q0, q1, [x22, #128]
	ldr	x9, [sp, #360]
	str	x9, [x19, #160]
	ldr	w9, [sp, #372]
	stp	q0, q1, [x19, #128]
	ldp	q0, q1, [x22, #64]
	stp	q0, q1, [x19, #64]
	ldp	q0, q2, [x22, #96]
	stp	q0, q2, [x19, #96]
	ldp	q1, q0, [x22]
	stp	q1, q0, [x19]
	ldp	q0, q2, [x22, #32]
	stp	q0, q2, [x19, #32]
	cbz	w8, LBB17_16
; %bb.14:                               ; %b12
	mov	w8, #8                          ; =0x8
	b	LBB17_17
LBB17_15:                               ; %b14
	ldp	q0, q1, [sp, #144]
	ldr	q2, [sp, #176]
	ldr	x8, [sp, #192]
	str	q2, [x19, #160]
	stp	q0, q1, [x19, #128]
	ldp	q0, q1, [sp, #80]
	str	x8, [x19, #176]
	stp	q0, q1, [x19, #64]
	ldp	q2, q0, [sp, #112]
	stp	q2, q0, [x19, #96]
	ldp	q1, q0, [sp, #16]
	stp	q1, q0, [x19]
	ldp	q2, q0, [sp, #48]
	stp	q2, q0, [x19, #32]
	b	LBB17_18
LBB17_16:                               ; %b11
	mov	w8, #5                          ; =0x5
LBB17_17:                               ; %common.ret
	stp	w8, w9, [x19, #168]
	str	x7, [x19, #176]
LBB17_18:                               ; %common.ret
	add	sp, sp, #512
	ldp	x29, x30, [sp, #80]             ; 16-byte Folded Reload
	ldp	x20, x19, [sp, #64]             ; 16-byte Folded Reload
	ldp	x22, x21, [sp, #48]             ; 16-byte Folded Reload
	ldp	x24, x23, [sp, #32]             ; 16-byte Folded Reload
	ldp	x26, x25, [sp, #16]             ; 16-byte Folded Reload
	ldp	x28, x27, [sp], #96             ; 16-byte Folded Reload
	ret
LBB17_19:                               ; %v32_trap
	brk	#0x1
                                        ; -- End function
	.globl	_liza_json.status               ; -- Begin function liza_json.status
	.p2align	2
_liza_json.status:                      ; @liza_json.status
; %bb.0:                                ; %b0
	ldr	w9, [x0, #168]
	cbz	w9, LBB18_2
; %bb.1:                                ; %b3
	cmp	w9, #2
	mov	w10, #2                         ; =0x2
	mov	x8, x0
	cset	w11, eq
	cmp	w9, #3
	ldr	x2, [x8, #176]
	csel	w10, w10, w11, eq
	mov	w11, #3                         ; =0x3
	cmp	w9, #4
	csel	w10, w11, w10, eq
	mov	w11, #4                         ; =0x4
	cmp	w9, #5
	csel	w10, w11, w10, eq
	mov	w11, #5                         ; =0x5
	cmp	w9, #6
	csel	w10, w11, w10, eq
	mov	w11, #6                         ; =0x6
	cmp	w9, #7
	csel	w10, w11, w10, eq
	cmp	w9, #8
	mov	w9, #7                          ; =0x7
	mov	w0, wzr
	csel	w1, w9, w10, eq
	ret
LBB18_2:
	mov	w1, wzr
	mov	x2, xzr
	mov	w0, #1                          ; =0x1
	ret
                                        ; -- End function
	.globl	_liza_json.finish               ; -- Begin function liza_json.finish
	.p2align	2
_liza_json.finish:                      ; @liza_json.finish
; %bb.0:                                ; %b0
	ldr	w9, [x0, #168]
	cbz	w9, LBB19_6
; %bb.1:                                ; %b3.i
	cmp	w9, #2
	mov	w10, #2                         ; =0x2
	ldr	x3, [x0, #176]
	cset	w11, eq
	cmp	w9, #3
	mov	w8, wzr
	csel	w10, w10, w11, eq
	mov	w11, #3                         ; =0x3
	cmp	w9, #4
	csel	w10, w11, w10, eq
	mov	w11, #4                         ; =0x4
	cmp	w9, #5
	csel	w10, w11, w10, eq
	mov	w11, #5                         ; =0x5
	cmp	w9, #6
	csel	w10, w11, w10, eq
	mov	w11, #6                         ; =0x6
	cmp	w9, #7
	csel	w10, w11, w10, eq
	cmp	w9, #8
	mov	w9, #7                          ; =0x7
	csel	w2, w9, w10, eq
	cbz	w8, LBB19_7
LBB19_2:                                ; %b4
	ldr	w8, [x0, #32]
	ldr	x3, [x0, #40]
	cmp	w8, #2
	b.eq	LBB19_8
; %bb.3:                                ; %b4
	cmp	w8, #1
	b.eq	LBB19_9
; %bb.4:                                ; %b6.i
	ldr	w8, [x0, #24]
	cbz	w8, LBB19_11
; %bb.5:                                ; %b7.i
	ldr	x3, [x0, #16]
	mov	w8, #1                          ; =0x1
	cbnz	w8, LBB19_10
	b	LBB19_12
LBB19_6:
	mov	w2, wzr
	mov	x3, xzr
	mov	w8, #1                          ; =0x1
	cbnz	w8, LBB19_2
LBB19_7:                                ; %b2
	mov	x1, xzr
	mov	w0, #1                          ; =0x1
	ret
LBB19_8:                                ; %b4.i
	mov	w8, #1                          ; =0x1
LBB19_9:                                ; %liza_utf8_stream.finish.exit
	cbz	w8, LBB19_12
LBB19_10:                               ; %b7
	mov	x1, xzr
	mov	w2, #4                          ; =0x4
	mov	w0, #1                          ; =0x1
	ret
LBB19_11:                               ; %b9.i
	mov	x3, xzr
	cbnz	w8, LBB19_10
LBB19_12:                               ; %b6
	ldr	w8, [x0, #128]
	cmp	w8, #17
	b.hi	LBB19_22
; %bb.13:                               ; %b6
	mov	w9, #1                          ; =0x1
	mov	w10, #22528                     ; =0x5800
	lsl	w9, w9, w8
	movk	w10, #2, lsl #16
	tst	w9, w10
	b.eq	LBB19_22
; %bb.14:                               ; %b18
	sub	sp, sp, #416
	ldp	q0, q1, [x0, #128]
	add	x8, sp, #192
	ldr	q2, [x0, #160]
	ldr	x9, [x0, #176]
	stp	x28, x27, [sp, #384]            ; 16-byte Folded Spill
	stp	x29, x30, [sp, #400]            ; 16-byte Folded Spill
	stp	q0, q1, [x8, #128]
	ldp	q0, q1, [x0, #64]
	str	q2, [x8, #160]
	str	x9, [sp, #368]
	stp	q0, q1, [x8, #64]
	ldp	q2, q0, [x0, #96]
	str	wzr, [sp, #320]
	stp	q2, q0, [x8, #96]
	ldp	q1, q0, [x0]
	stp	q1, q0, [x8]
	ldp	q2, q0, [x0, #32]
	add	x0, sp, #192
	stp	q2, q0, [x8, #32]
	add	x8, sp, #8
	bl	_liza___liza_json_done
	ldp	x29, x30, [sp, #400]            ; 16-byte Folded Reload
	ldr	x3, [sp, #56]
	ldp	x28, x27, [sp, #384]            ; 16-byte Folded Reload
	ldr	w10, [sp, #128]
	ldrb	w9, [sp, #132]
	ldr	w8, [sp, #136]
	ldr	x11, [sp, #168]
	add	sp, sp, #416
LBB19_15:                               ; %b20
	sub	w12, w8, #4
	cmp	w12, #2
	b.hi	LBB19_17
; %bb.16:                               ; %b27
	mov	x1, xzr
	mov	w2, #3                          ; =0x3
	mov	w0, #1                          ; =0x1
	mov	x3, x11
	ret
LBB19_17:                               ; %b29
	cbnz	w8, LBB19_21
; %bb.18:                               ; %b29
	cbnz	w10, LBB19_21
; %bb.19:                               ; %b29
	tbz	w9, #0, LBB19_21
; %bb.20:                               ; %b38
	mov	w0, wzr
	mov	w2, wzr
	mov	x1, x3
	mov	x3, xzr
	ret
LBB19_21:                               ; %b36
	mov	x1, xzr
	mov	w2, #5                          ; =0x5
	mov	w0, #1                          ; =0x1
	ret
LBB19_22:                               ; %b19_to_b20
	ldr	x3, [x0, #48]
	ldr	w10, [x0, #120]
	ldrb	w9, [x0, #124]
	ldr	x11, [x0, #160]
	b	LBB19_15
                                        ; -- End function
	.globl	_example_entry                  ; -- Begin function example_entry
	.p2align	2
_example_entry:                         ; @example_entry
; %bb.0:                                ; %entry
	mov	w0, wzr
	ret
                                        ; -- End function
	.globl	_stream_start                   ; -- Begin function stream_start
	.p2align	2
_stream_start:                          ; @stream_start
; %bb.0:
	sub	sp, sp, #16
	movi.2d	v0, #0000000000000000
	mov	w8, #49024                      ; =0xbf80
	strb	wzr, [sp, #12]
	strb	wzr, [sp, #8]
	stp	xzr, xzr, [x0, #8]
	str	xzr, [x0]
	str	wzr, [x0, #24]
	strh	w8, [x0, #28]
	str	wzr, [x0, #32]
	stur	q0, [x0, #40]
	stur	q0, [x0, #56]
	stur	q0, [x0, #72]
	stur	q0, [x0, #88]
	stur	q0, [x0, #104]
	str	wzr, [x0, #120]
	strb	wzr, [x0, #124]
	str	wzr, [x0, #128]
	strb	wzr, [x0, #132]
	str	xzr, [x0, #176]
	str	wzr, [x0, #168]
	stur	q0, [x0, #152]
	stur	q0, [x0, #136]
	add	sp, sp, #16
	ret
                                        ; -- End function
	.globl	_stream_feed                    ; -- Begin function stream_feed
	.p2align	2
_stream_feed:                           ; @stream_feed
; %bb.0:
	sub	sp, sp, #224
	add	x8, sp, #8
	stp	x20, x19, [sp, #192]            ; 16-byte Folded Spill
	mov	x19, x0
	stp	x29, x30, [sp, #208]            ; 16-byte Folded Spill
	bl	_liza_json.feed
	ldur	w8, [sp, #115]
	ldur	w10, [sp, #103]
	ldur	x9, [sp, #107]
	ldur	q0, [sp, #8]
	ldp	x29, x30, [sp, #208]            ; 16-byte Folded Reload
	stur	w8, [x19, #107]
	ldur	x8, [sp, #95]
	stur	w10, [x19, #95]
	ldur	x10, [sp, #83]
	stur	x8, [x19, #87]
	ldur	w8, [sp, #79]
	stur	x9, [x19, #99]
	ldur	w9, [sp, #91]
	stur	x10, [x19, #75]
	ldur	w10, [sp, #67]
	stur	w8, [x19, #71]
	ldurh	w8, [sp, #65]
	stur	w9, [x19, #83]
	ldur	x9, [sp, #71]
	stur	w10, [x19, #59]
	sturh	w8, [x19, #57]
	ldp	x10, x8, [sp, #48]
	stur	x9, [x19, #63]
	ldrb	w9, [sp, #64]
	str	q0, [x19]
	stp	x10, x8, [x19, #40]
	ldrh	w8, [sp, #36]
	ldr	w10, [sp, #32]
	strb	w9, [x19, #56]
	ldr	w9, [sp, #40]
	strh	w8, [x19, #28]
	ldr	x8, [sp, #184]
	str	w9, [x19, #32]
	ldr	x9, [sp, #24]
	str	w10, [x19, #24]
	str	x8, [x19, #176]
	ldp	x10, x8, [sp, #160]
	str	x9, [x19, #16]
	ldr	w9, [sp, #176]
	str	w9, [x19, #168]
	ldr	w9, [sp, #156]
	stp	x10, x8, [x19, #152]
	ldur	x8, [sp, #148]
	ldr	w10, [sp, #144]
	str	w9, [x19, #148]
	ldrb	w9, [sp, #140]
	stur	x8, [x19, #140]
	ldr	w8, [sp, #136]
	str	w10, [x19, #136]
	ldrb	w10, [sp, #132]
	strb	w9, [x19, #132]
	ldr	w9, [sp, #128]
	str	w8, [x19, #128]
	ldr	x8, [sp, #120]
	strb	w10, [x19, #124]
	ldrb	w10, [sp, #119]
	str	w9, [x19, #120]
	str	x8, [x19, #112]
	strb	w10, [x19, #111]
	ldp	x20, x19, [sp, #192]            ; 16-byte Folded Reload
	add	sp, sp, #224
	ret
                                        ; -- End function
	.globl	_stream_status                  ; -- Begin function stream_status
	.p2align	2
_stream_status:                         ; @stream_status
; %bb.0:                                ; %liza_status.exit
	stp	x29, x30, [sp, #-16]!           ; 16-byte Folded Spill
	bl	_liza_json.finish
	cmp	w0, #0
	csinc	w0, wzr, w2, eq
	ldp	x29, x30, [sp], #16             ; 16-byte Folded Reload
	ret
                                        ; -- End function
	.globl	_stream_pending                 ; -- Begin function stream_pending
	.p2align	2
_stream_pending:                        ; @stream_pending
; %bb.0:
	ldr	w8, [x0, #168]
	cmp	w8, #0
	cset	w0, ne
	ret
                                        ; -- End function
	.globl	_stream_value                   ; -- Begin function stream_value
	.p2align	2
_stream_value:                          ; @stream_value
; %bb.0:
	stp	x29, x30, [sp, #-16]!           ; 16-byte Folded Spill
	bl	_liza_json.finish
	cmp	w0, #0
	csel	x0, x1, x3, eq
	ldp	x29, x30, [sp], #16             ; 16-byte Folded Reload
	ret
                                        ; -- End function
	.globl	_stream_size                    ; -- Begin function stream_size
	.p2align	2
_stream_size:                           ; @stream_size
; %bb.0:
	mov	w0, #184                        ; =0xb8
	ret
                                        ; -- End function
.subsections_via_symbols
