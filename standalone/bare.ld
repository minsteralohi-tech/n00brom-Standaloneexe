/*
 * PS1 executable linker script.
 *
 * Derived from ps1-bare-metal/cmake/executable.ld.
 * Copyright (c) 2023-2025 spicyjpeg (ISC license).
 */

ENTRY(_start)

MEMORY {
	/* The BIOS kernel owns the first 64 KiB of the PS1's 2 MiB main RAM. */
	APP_RAM (rwx) : ORIGIN = 0x80010000, LENGTH = 0x1f0000
}

SECTIONS {
	.text : ALIGN(4) {
		_textStart = .;
		KEEP(*(.text.start))
		*(.text .text.* .gnu.linkonce.t.*)
		*(.plt .MIPS.stubs)
	} > APP_RAM

	.rodata : ALIGN(4) {
		*(.rodata .rodata.* .gnu.linkonce.r.*)
		_textEnd = .;
	} > APP_RAM

	.preinit_array : ALIGN(4) {
		_preinitArrayStart = .;
		KEEP(*(.preinit_array))
		_preinitArrayEnd = .;
	} > APP_RAM

	.init_array : ALIGN(4) {
		_initArrayStart = .;
		KEEP(*(SORT(.init_array.*) SORT(.ctors.*)))
		KEEP(*(.init_array .ctors))
		_initArrayEnd = .;
	} > APP_RAM

	.fini_array : ALIGN(4) {
		_finiArrayStart = .;
		KEEP(*(.fini_array .dtors))
		KEEP(*(SORT(.fini_array.*) SORT(.dtors.*)))
		_finiArrayEnd = .;
	} > APP_RAM

	.data : ALIGN(4) {
		_dataStart = .;
		*(.data .data.* .gnu.linkonce.d.*)
	} > APP_RAM

	.sdata : ALIGN(4) {
		_gp = ALIGN(16) + 0x7ff0;
		*(.sdata .sdata.* .gnu.linkonce.s.*)
		_dataEnd = .;
	} > APP_RAM

	.sbss (NOLOAD) : ALIGN(4) {
		_bssStart = .;
		*(.sbss .sbss.* .gnu.linkonce.sb.*)
		*(.scommon)
	} > APP_RAM

	.bss (NOLOAD) : ALIGN(4) {
		*(.bss .bss.* .gnu.linkonce.b.*)
		*(COMMON)
		. = ALIGN(4);
		_bssEnd = .;
	} > APP_RAM

	/DISCARD/ : {
		*(.comment)
		*(.note.* .gnu_debuglink .gnu.lto_*)
		*(.MIPS.abiflags)
	}
}
