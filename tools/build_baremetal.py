#!/usr/bin/env python3
"""Build the independent n00bROM bare-metal PS-X EXE target."""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import tempfile
from pathlib import Path

from elf_to_psexe import convert

ROOT = Path(__file__).resolve().parents[1]
BASE_ADDRESS = 0x80010000
STACK_POINTER = 0x801FFF00


def run(command: list[str]) -> None:
    print("+", " ".join(command))
    subprocess.run(command, check=True)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def compile_elf(gcc: Path, source: Path, output: Path) -> None:
    run(
        [
            str(gcc),
            "-march=r3000",
            "-mabi=32",
            "-mfp32",
            "-mno-mt",
            "-mno-llsc",
            "-mno-abicalls",
            "-mno-extern-sdata",
            "-fno-pic",
            "-ffreestanding",
            "-fno-builtin",
            "-fno-stack-protector",
            "-fno-strict-aliasing",
            "-fno-strict-overflow",
            "-ffunction-sections",
            "-fdata-sections",
            "-fsigned-char",
            "-G8",
            "-Os",
            "-Wall",
            "-Wextra",
            "-Werror",
            "-static",
            "-nostdlib",
            "-Wl,--gc-sections",
            "-Wl,-Map," + str(output.with_suffix(".map")),
            f"-Wl,-T,{ROOT / 'standalone' / 'bare.ld'}",
            "-o",
            str(output),
            str(ROOT / "standalone" / "start.S"),
            str(ROOT / "standalone" / "cache.s"),
            str(source),
            "-lgcc",
        ]
    )


def build(gcc: Path, output: Path, smoke_output: Path | None) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="n00brom-baremetal-") as temporary:
        temporary_path = Path(temporary)
        elf = temporary_path / "n00brom-baremetal.elf"
        compile_elf(gcc, ROOT / "standalone" / "main.c", elf)
        convert(
            elf,
            output,
            stack_pointer=STACK_POINTER,
            region="Sony Computer Entertainment Inc. for North America area",
        )

        if smoke_output is not None:
            smoke_elf = temporary_path / "ps1-bare-metal-smoke.elf"
            compile_elf(gcc, ROOT / "standalone" / "smoke.c", smoke_elf)
            convert(
                smoke_elf,
                smoke_output,
                stack_pointer=STACK_POINTER,
                region="Sony Computer Entertainment Inc. for North America area",
            )

    # Add the final release artifact to the native-build provenance manifest
    # when both outputs are produced into the same directory (as in CI).
    manifest_path = output.parent / "manifest.json"
    manifest = {}
    if manifest_path.is_file():
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["n00brom_baremetal_psexe_sha256"] = sha256(output)
    manifest["n00brom_baremetal_psexe_size"] = str(output.stat().st_size)
    if smoke_output is not None:
        manifest["ps1_baremetal_smoketest_psexe_sha256"] = sha256(smoke_output)
        manifest["ps1_baremetal_smoketest_psexe_size"] = str(
            smoke_output.stat().st_size
        )
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--gcc", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--smoke-output", type=Path)
    args = parser.parse_args()
    build(
        args.gcc.resolve(),
        args.output.resolve(),
        args.smoke_output.resolve() if args.smoke_output else None,
    )


if __name__ == "__main__":
    main()
