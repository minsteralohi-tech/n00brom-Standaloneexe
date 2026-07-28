/*
 * Bare PS-X EXE linker script.
 *
 * Derived from spicyjpeg/ps1-bare-metal's cmake/executable.ld (ISC license).
 * This standalone program is deliberately placed after the 64 KiB region
 * reserved by the PlayStation BIOS kernel.
 */

ENTRY(_start)

MEMORY {
	APP_RAM (rwx) : ORIGIN = 0x80010000, LENGTH = 0x1f0000
}

SECTIONS {
	.text : ALIGN(4) {
		*(.text.start)
		*(.text .text.*)
		*(.rodata .rodata.*)
	} > APP_RAM

	.data : ALIGN(4) {
		*(.data .data.*)
	} > APP_RAM

	.bss (NOLOAD) : ALIGN(4) {
		_bss_start = .;
		*(.bss .bss.*)
		*(COMMON)
		. = ALIGN(4);
		_bss_end = .;
	} > APP_RAM

	/DISCARD/ : {
		*(.comment .note.* .gnu.* .MIPS.abiflags)
	}
}
