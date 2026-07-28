# ps1-bare-metal - (C) 2023-2025 spicyjpeg
#
# Permission to use, copy, modify, and/or distribute this software for any
# purpose with or without fee is hereby granted, provided that the above
# copyright notice and this permission notice appear in all copies.
#
# THE SOFTWARE IS PROVIDED "AS IS" AND THE AUTHOR DISCLAIMS ALL WARRANTIES
# WITH REGARD TO THIS SOFTWARE INCLUDING ALL IMPLIED WARRANTIES OF
# MERCHANTABILITY AND FITNESS. IN NO EVENT SHALL THE AUTHOR BE LIABLE FOR ANY
# SPECIAL, DIRECT, INDIRECT, OR CONSEQUENTIAL DAMAGES OR ANY DAMAGES WHATSOEVER
# RESULTING FROM LOSS OF USE, DATA OR PROFITS, WHETHER IN AN ACTION OF CONTRACT,
# NEGLIGENCE OR OTHER TORTIOUS ACTION, ARISING OUT OF OR IN CONNECTION WITH THE
# USE OR PERFORMANCE OF THIS SOFTWARE.

# Minimal instruction-cache tag flush derived from ps1-bare-metal/src/ps1/cache.s.

.set noreorder

.set KSEG1_BASE, 0xa0000000
.set CPU_BCC,    0xfffe0130

.set CPU_BCC_TAG, 1 <<  2
.set CPU_BCC_DS,  1 <<  7
.set CPU_BCC_IS1, 1 << 11

.set COP0_STATUS, $12
.set COP0_STATUS_IsC, 1 << 16

.set ptr,         $a0
.set temp,        $a1
.set savedStatus, $a2
.set savedBCC,    $a3

.section .text.flushCache, "ax", @progbits
.global flushCache
.type flushCache, @function

flushCache:
	la    ptr, _flushCacheInner
	lui   temp, %hi(KSEG1_BASE)
	or    ptr, temp

	jr    ptr
	lui   ptr, %hi(CPU_BCC)

.section .text._flushCacheInner, "ax", @progbits
.type _flushCacheInner, @function

_flushCacheInner:
	mfc0  savedStatus, COP0_STATUS
	lw    savedBCC, %lo(CPU_BCC)(ptr)

	mtc0  $0, COP0_STATUS

	li    temp, ~CPU_BCC_DS
	and   temp, savedBCC
	ori   temp, CPU_BCC_TAG | CPU_BCC_IS1
	sw    temp, %lo(CPU_BCC)(ptr)

	li    temp, COP0_STATUS_IsC
	mtc0  temp, COP0_STATUS

	li    temp, 0x1000 - 256

.LclearLoop:
	sw    $0, 0x00(temp)
	sw    $0, 0x10(temp)
	sw    $0, 0x20(temp)
	sw    $0, 0x30(temp)
	sw    $0, 0x40(temp)
	sw    $0, 0x50(temp)
	sw    $0, 0x60(temp)
	sw    $0, 0x70(temp)
	sw    $0, 0x80(temp)
	sw    $0, 0x90(temp)
	sw    $0, 0xa0(temp)
	sw    $0, 0xb0(temp)
	sw    $0, 0xc0(temp)
	sw    $0, 0xd0(temp)
	sw    $0, 0xe0(temp)
	sw    $0, 0xf0(temp)

	bgtz  temp, .LclearLoop
	addiu temp, -256

	mtc0  $0, COP0_STATUS
	nop
	sw    savedBCC, %lo(CPU_BCC)(ptr)
	mtc0  savedStatus, COP0_STATUS

	jr    $ra
	nop
