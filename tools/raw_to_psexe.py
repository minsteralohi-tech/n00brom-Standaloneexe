#!/usr/bin/env python3
"""Wrap a flat MIPS image in the PS-X EXE header used by PS1 BIOS loaders."""

from __future__ import annotations

import argparse
import struct
from pathlib import Path

MAGIC = b"PS-X EXE"
HEADER = struct.Struct("<8s8x4I16x2I20x1972s")
ALIGNMENT = 2048
RAM_START = 0x80010000
RAM_END = 0x80200000


def aligned(data: bytes) -> bytes:
    padding = (-len(data)) % ALIGNMENT
    return data + (b"\0" * padding)


def write_psexe(
    payload: bytes,
    output: Path,
    *,
    load_address: int,
    entry_point: int,
    stack_pointer: int,
    region: str,
) -> None:
    if not payload:
        raise ValueError("payload is empty")
    end_address = load_address + len(payload)
    if load_address < RAM_START or end_address > RAM_END:
        raise ValueError(
            f"payload range {load_address:#x}..{end_address:#x} exceeds 2 MiB PS1 RAM"
        )
    if not load_address <= entry_point < end_address:
        raise ValueError("entry point is outside the payload")

    region_bytes = region.encode("ascii")
    if len(region_bytes) > 20:
        raise ValueError("region string is longer than the PS-X EXE field")

    body = aligned(payload)
    header = HEADER.pack(
        MAGIC,
        entry_point,
        0,  # initial $gp
        load_address,
        len(body),
        stack_pointer,
        0,  # stack size
        region_bytes,
    )
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_bytes(header + body)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("input", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--load-address", type=lambda value: int(value, 0), default=RAM_START)
    parser.add_argument("--entry-point", type=lambda value: int(value, 0), default=RAM_START)
    parser.add_argument("--stack-pointer", type=lambda value: int(value, 0), default=0x801FFF00)
    parser.add_argument("--region", default="SYSTEM.CNF")
    args = parser.parse_args()
    write_psexe(
        args.input.read_bytes(),
        args.output,
        load_address=args.load_address,
        entry_point=args.entry_point,
        stack_pointer=args.stack_pointer,
        region=args.region,
    )


if __name__ == "__main__":
    main()
