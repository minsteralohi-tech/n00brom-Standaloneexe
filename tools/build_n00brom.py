#!/usr/bin/env python3
"""Build n00bROM's native cartridge image and a relocated standalone PS-X EXE."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

from raw_to_psexe import write_psexe

STANDALONE_BASE = 0x80010000
STANDALONE_STACK = 0x801FFF00


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def locate_rom(source_dir: Path) -> Path:
    rom_dir = source_dir / "rom"
    if (rom_dir / "n00brom.asm").is_file():
        return rom_dir
    if (source_dir / "n00brom.asm").is_file():
        return source_dir
    raise FileNotFoundError(
        f"{source_dir} does not contain n00brom.asm or rom/n00brom.asm"
    )


def run_armips(armips: Path, cwd: Path, source: str, build_date: str) -> None:
    command = [
        str(armips),
        "-strequ",
        "build_date",
        build_date,
        "-sym",
        "n00brom.sym",
        "-temp",
        "n00brom.lst",
        source,
    ]
    result = subprocess.run(command, cwd=cwd, text=True, capture_output=True)
    # armips versions used by n00bROM have historically returned an unreliable
    # status code; generated-file validation below is therefore authoritative.
    if result.stdout:
        print(result.stdout, end="")
    if result.stderr:
        print(result.stderr, end="", file=sys.stderr)


def make_standalone_source(original: str) -> str:
    first = original.find('.create "ramprog.bin"')
    second = original.find('.create "romhead.bin"')
    if first < 0 or second < 0 or second <= first:
        raise ValueError("unrecognized n00bROM assembly layout")

    prefix = original[:first]
    ram_block = original[first:second]
    ram_block = ram_block[ram_block.find("\n", ram_block.find(".create")) + 1 :]
    ram_block = ram_block[: ram_block.rfind(".close")]
    ram_block = re.sub(r"^\s*dw\s+PROG_addr.*\n", "", ram_block, count=1, flags=re.MULTILINE)
    ram_block = ram_block.replace("\n\tjal\tmain\t\t\t\t\t; Jump to main\n\trfe", "\n\tjal\tmain\t\t\t\t\t; Jump to main\n\tnop")
    if "\trfe" in ram_block:
        ram_block = ram_block.replace("\n\trfe", "\n\tnop", 1)

    rom_block = original[second:]
    config_start = rom_block.find("config:")
    sram_start = rom_block.find("sram_jump:")
    data_start = rom_block.find("text:")
    close = rom_block.rfind(".close")
    if min(config_start, sram_start, data_start, close) < 0:
        raise ValueError("unrecognized n00bROM ROM block")
    config = rom_block[config_start:sram_start]
    data = rom_block[data_start:close]

    return (
        prefix
        + f'.create "n00brom-standalone.bin", {STANDALONE_BASE:#x}\n\n'
        + ram_block
        + "\n\n"
        + config
        + "\n"
        + data
        + "\n.close\n"
    )


def build(source_dir: Path, armips: Path, out_dir: Path) -> dict[str, str]:
    rom_dir = locate_rom(source_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    build_date = datetime.now(timezone.utc).strftime("%Y%m%d%H%M")

    with tempfile.TemporaryDirectory(prefix="n00brom-build-") as temp:
        stage = Path(temp) / "rom"
        shutil.copytree(rom_dir, stage)
        source_text = (stage / "n00brom.asm").read_text(encoding="utf-8")

        run_armips(armips, stage, "n00brom.asm", build_date)
        rom_head = stage / "romhead.bin"
        ram_prog = stage / "ramprog.bin"
        if not rom_head.is_file() or not ram_prog.is_file():
            raise RuntimeError("armips did not produce romhead.bin and ramprog.bin")
        native = out_dir / "n00brom.rom"
        native.write_bytes(rom_head.read_bytes() + ram_prog.read_bytes())

        standalone_asm = stage / "n00brom-standalone.asm"
        standalone_asm.write_text(make_standalone_source(source_text), encoding="utf-8")
        run_armips(armips, stage, standalone_asm.name, build_date)
        raw = stage / "n00brom-standalone.bin"
        if not raw.is_file():
            raise RuntimeError("armips did not produce n00brom-standalone.bin")
        psexe = out_dir / "n00brom.psexe"
        write_psexe(
            raw.read_bytes(),
            psexe,
            load_address=STANDALONE_BASE,
            entry_point=STANDALONE_BASE,
            stack_pointer=STANDALONE_STACK,
            region="n00bROM standalone",
        )

    manifest = {
        "build_date_utc": build_date,
        "source": str(rom_dir),
        "source_sha256": sha256(rom_dir / "n00brom.asm"),
        "n00brom_rom_sha256": sha256(native),
        "n00brom_psexe_sha256": sha256(psexe),
        "n00brom_rom_size": str(native.stat().st_size),
        "n00brom_psexe_size": str(psexe.stat().st_size),
    }
    (out_dir / "manifest.json").write_text(
        json.dumps(manifest, indent=2) + "\n", encoding="utf-8"
    )
    return manifest


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-dir", type=Path, required=True)
    parser.add_argument("--armips", type=Path, required=True)
    parser.add_argument("--out-dir", type=Path, default=Path("dist"))
    args = parser.parse_args()
    manifest = build(args.source_dir.resolve(), args.armips.resolve(), args.out_dir.resolve())
    print(json.dumps(manifest, indent=2))


if __name__ == "__main__":
    main()
