/*
 * Minimal startup compatible with ps1-bare-metal's executable.ld layout.
 *
 * We establish both stack and global pointers ourselves before touching
 * small-data variables. This matches ps1-bare-metal's minimal CRT model while
 * retaining a known stack for serial loaders that do not restore PS-X EXE
 * registers. We then clear every word in BSS and call main.
 */

	.set noreorder
	.section .text.start, "ax", @progbits
	.globl _start
	.ent _start

_start:
	/* Do not rely on a loader honoring the PS-X EXE stack fields. */
	lui	$sp, 0x8020
	addiu	$sp, $sp, -256

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
