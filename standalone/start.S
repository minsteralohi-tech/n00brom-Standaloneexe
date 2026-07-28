/*
 * Minimal PS-X EXE entry point. No BIOS function vectors, exception hooks or
 * cartridge mapping are used by the bare-metal standalone program.
 */

	.set noreorder
	.section .text.start, "ax", @progbits
	.globl _start
	.ent _start

_start:
	/* Keep the stack below the conventional 2 MiB RAM top. */
	lui	$sp, 0x8020
	addiu	$sp, $sp, -256

	/* The PS-X EXE loader does not clear BSS. */
	la	$t0, _bss_start
	la	$t1, _bss_end
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
