/*
 * Minimal startup compatible with ps1-bare-metal's executable.ld layout.
 *
 * The EXE header supplies the initial stack.  We set $gp before touching
 * small-data variables, clear every word in BSS, and then call main.
 */

	.set noreorder
	.section .text.start, "ax", @progbits
	.globl _start
	.ent _start

_start:
	la	$gp, _gp

	la	$t0, _bssStart
	la	$t1, _bssEnd
1:
	beq	$t0, $t1, 2f
	nop
	sw	$zero, 0($t0)
	addiu	$t0, $t0, 4
	b	1b
	nop

2:
	jal	main
	nop

3:
	b	3b
	nop

	.end _start
