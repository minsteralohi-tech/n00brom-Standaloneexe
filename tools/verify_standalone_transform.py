#!/usr/bin/env python3
"""Validate the n00bROM-to-standalone source transformation before assembly."""

from __future__ import annotations

import argparse
from pathlib import Path

from build_n00brom import locate_rom, make_standalone_source, patch_standalone_pad_source


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-dir", type=Path, required=True)
    args = parser.parse_args()

    source = (locate_rom(args.source_dir) / "n00brom.asm").read_text(encoding="utf-8")
    transformed = make_standalone_source(source)

    assert '.create "n00brom-standalone.bin", 0x80010000' in transformed
    assert '.create "ramprog.bin"' not in transformed
    assert '.create "romhead.bin"' not in transformed
    assert "dw\t\tPROG_addr" not in transformed
    assert "dw\t\t(program_end-program_start)" not in transformed
    assert "@@exit_boot:\n\tb\t\t@@no_pad\n\tnop" in transformed
    assert "\n\trfe" not in transformed

    pad = patch_standalone_pad_source(
        (locate_rom(args.source_dir) / "pad.inc").read_text(encoding="utf-8")
    )
    assert pad.count("0x1007") == 2
    assert "bgt\tv1, 1000, @@timeout" in pad
    print("standalone source transformation: OK")


if __name__ == "__main__":
    main()
