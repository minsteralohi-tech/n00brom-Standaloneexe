/*
 * Minimal startup compatible with ps1-bare-metal's executable.ld layout.
 *
 * We establish both stack and global pointers ourselves before touching
 * small-data variables.  This makes the entry point safe for BIOS loaders,
 * DuckStation's direct EXE injector and serial loaders that ignore header
 * register values.  We then clear every word in BSS and call main.
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
