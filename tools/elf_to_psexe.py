#!/usr/bin/env python3
"""Convert a 32-bit little-endian MIPS ELF into a PS-X EXE.

This is a focused adaptation of ps1-bare-metal/tools/convertExecutable.py
version 0.1.3 by spicyjpeg, distributed under the ISC license.  Unlike a raw
objcopy wrapper, it uses the ELF entry point and preserves the addresses of all
loadable segments.
"""

from __future__ import annotations

import argparse
import struct
from dataclasses import dataclass
from pathlib import Path

ELF_HEADER = struct.Struct("<4s4B8x2H5I6H")
PROGRAM_HEADER = struct.Struct("<8I")
EXE_HEADER = struct.Struct("<8s8x4I16x2I20x1972s")
EXE_ALIGNMENT = 2048


@dataclass(frozen=True)
class Segment:
    address: int
    data: bytes


def align(data: bytearray, alignment: int) -> None:
    padding = (-len(data)) % alignment
    if padding:
        data.extend(b"\0" * padding)


def parse_elf(path: Path) -> tuple[int, list[Segment]]:
    contents = path.read_bytes()
    if len(contents) < ELF_HEADER.size:
        raise ValueError("ELF header is truncated")

    fields = ELF_HEADER.unpack_from(contents)
    (
        magic,
        word_size,
        endianness,
        _version,
        _abi,
        elf_type,
        architecture,
        _machine_version,
        entry_point,
        program_offset,
        _section_offset,
        _flags,
        elf_header_size,
        program_header_size,
        program_count,
        _section_header_size,
        _section_count,
        _string_index,
    ) = fields

    if magic != b"\x7fELF":
        raise ValueError("input is not an ELF file")
    if word_size != 1 or endianness != 1:
        raise ValueError("ELF must be 32-bit little-endian")
    if elf_type != 2 or architecture != 8:
        raise ValueError("ELF must be a MIPS executable")
    if elf_header_size != ELF_HEADER.size or program_header_size != PROGRAM_HEADER.size:
        raise ValueError("unsupported ELF header layout")

    segments: list[Segment] = []
    for index in range(program_count):
        offset = program_offset + index * program_header_size
        if offset + PROGRAM_HEADER.size > len(contents):
            raise ValueError("ELF program header table is truncated")
        (
            header_type,
            file_offset,
            virtual_address,
            _physical_address,
            file_size,
            _memory_size,
            _segment_flags,
            _segment_alignment,
        ) = PROGRAM_HEADER.unpack_from(contents, offset)
        if header_type != 1:
            continue
        if file_offset + file_size > len(contents):
            raise ValueError("ELF load segment is truncated")
        segments.append(
            Segment(virtual_address, contents[file_offset : file_offset + file_size])
        )

    if not segments:
        raise ValueError("ELF has no loadable segments")
    return entry_point, segments


def convert(
    source: Path,
    output: Path,
    *,
    stack_pointer: int = 0,
    global_pointer: int = 0,
    region: str = "",
) -> None:
    entry_point, segments = parse_elf(source)
    load_address = min(segment.address for segment in segments)
    end_address = max(segment.address + len(segment.data) for segment in segments)
    payload = bytearray(end_address - load_address)

    for segment in segments:
        offset = segment.address - load_address
        payload[offset : offset + len(segment.data)] = segment.data
    align(payload, EXE_ALIGNMENT)

    if not (load_address <= entry_point < load_address + len(payload)):
        raise ValueError("ELF entry point is outside the flattened payload")
    region_bytes = region.strip().encode("ascii")
    if len(region_bytes) > 1972:
        raise ValueError("region string is too long")

    header = EXE_HEADER.pack(
        b"PS-X EXE",
        entry_point,
        global_pointer,
        load_address,
        len(payload),
        stack_pointer,
        0,
        region_bytes,
    )
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_bytes(header + payload)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("-s", "--set-sp", type=lambda value: int(value, 0), default=0)
    parser.add_argument("-g", "--set-gp", type=lambda value: int(value, 0), default=0)
    parser.add_argument("-r", "--region-str", default="")
    parser.add_argument("input", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    convert(
        args.input,
        args.output,
        stack_pointer=args.set_sp,
        global_pointer=args.set_gp,
        region=args.region_str,
    )


if __name__ == "__main__":
    main()
