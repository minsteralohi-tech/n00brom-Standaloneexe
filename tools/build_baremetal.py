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
DEFAULT_LOAD_ADDRESS = 0x80010000
# Kept deliberately below the stack at the top of PS1 RAM. This leaves a
# 512 KiB application window for the UniROM high-RAM test image.
UNIROM_HIGH_RAM_LOAD_ADDRESS = 0x80180000
STACK_POINTER = 0x801FFF00
MINIMUM_STACK_GAP = 0x10000


def run(command: list[str]) -> None:
    print("+", " ".join(command))
    subprocess.run(command, check=True)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def make_linker_script(directory: Path, load_address: int) -> Path:
    """Materialize the proven linker script at the requested KSEG0 base."""
    original = (ROOT / "standalone" / "bare.ld").read_text(encoding="utf-8")
    marker = "ORIGIN = 0x80010000"
    if marker not in original:
        raise RuntimeError("could not find the APP_RAM origin in standalone/bare.ld")
    script = directory / "bare.ld"
    script.write_text(
        original.replace(marker, f"ORIGIN = {load_address:#010x}", 1),
        encoding="utf-8",
    )
    return script


def compile_elf(gcc: Path, source: Path, output: Path, linker_script: Path) -> None:
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
            f"-Wl,-T,{linker_script}",
            "-o",
            str(output),
            str(ROOT / "standalone" / "start.S"),
            str(ROOT / "standalone" / "cache.s"),
            str(source),
            "-lgcc",
        ]
    )


def build(
    gcc: Path, output: Path, smoke_output: Path | None, load_address: int
) -> None:
    if not (DEFAULT_LOAD_ADDRESS <= load_address <= STACK_POINTER - MINIMUM_STACK_GAP):
        raise ValueError(
            "load address must be in KSEG0 application RAM and leave at least "
            f"{MINIMUM_STACK_GAP:#x} bytes below the stack"
        )
    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="n00brom-baremetal-") as temporary:
        temporary_path = Path(temporary)
        elf = temporary_path / "n00brom-baremetal.elf"
        linker_script = make_linker_script(temporary_path, load_address)
        compile_elf(gcc, ROOT / "standalone" / "main.c", elf, linker_script)
        convert(
            elf,
            output,
            stack_pointer=STACK_POINTER,
            region="Sony Computer Entertainment Inc. for North America area",
        )

        if smoke_output is not None:
            smoke_elf = temporary_path / "ps1-bare-metal-smoke.elf"
            compile_elf(
                gcc, ROOT / "standalone" / "smoke.c", smoke_elf, linker_script
            )
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
    artifact_key = output.stem.replace("-", "_")
    manifest[f"{artifact_key}_sha256"] = sha256(output)
    manifest[f"{artifact_key}_size"] = str(output.stat().st_size)
    # Keep the original manifest field names stable for automation that already
    # consumes the normal release, while giving alternate-address images their
    # own unambiguous filename-based fields above.
    if artifact_key == "n00brom":
        manifest["n00brom_baremetal_psexe_sha256"] = manifest[
            f"{artifact_key}_sha256"
        ]
        manifest["n00brom_baremetal_psexe_size"] = manifest[f"{artifact_key}_size"]
    if smoke_output is not None:
        smoke_key = smoke_output.stem.replace("-", "_")
        manifest[f"{smoke_key}_sha256"] = sha256(smoke_output)
        manifest[f"{smoke_key}_size"] = str(smoke_output.stat().st_size)
        if smoke_key == "ps1_bare_metal_smoketest":
            manifest["ps1_baremetal_smoketest_psexe_sha256"] = manifest[
                f"{smoke_key}_sha256"
            ]
            manifest["ps1_baremetal_smoketest_psexe_size"] = manifest[
                f"{smoke_key}_size"
            ]
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--gcc", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--smoke-output", type=Path)
    parser.add_argument(
        "--load-address",
        type=lambda value: int(value, 0),
        default=DEFAULT_LOAD_ADDRESS,
        help=(
            "KSEG0 PS-X EXE load address "
            f"(default: {DEFAULT_LOAD_ADDRESS:#010x}; UniROM test: "
            f"{UNIROM_HIGH_RAM_LOAD_ADDRESS:#010x})"
        ),
    )
    args = parser.parse_args()
    build(
        args.gcc.resolve(),
        args.output.resolve(),
        args.smoke_output.resolve() if args.smoke_output else None,
        args.load_address,
    )


if __name__ == "__main__":
    main()
