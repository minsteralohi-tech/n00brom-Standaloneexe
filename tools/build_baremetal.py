#!/usr/bin/env python3
"""Build the independent n00bROM bare-metal PS-X EXE target."""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import tempfile
from pathlib import Path

from raw_to_psexe import write_psexe

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


def build(gcc: Path, objcopy: Path, output: Path) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="n00brom-baremetal-") as temporary:
        temporary_path = Path(temporary)
        elf = temporary_path / "n00brom-baremetal.elf"
        raw = temporary_path / "n00brom-baremetal.bin"
        run(
            [
                str(gcc),
                "-march=r3000",
                "-mabi=32",
                "-mfp32",
                "-mno-abicalls",
                "-fno-pic",
                "-ffreestanding",
                "-fno-builtin",
                "-fno-stack-protector",
                "-fno-strict-aliasing",
                "-G0",
                "-Os",
                "-Wall",
                "-Wextra",
                "-Werror",
                "-nostdlib",
                "-Wl,--gc-sections",
                f"-Wl,-T,{ROOT / 'standalone' / 'bare.ld'}",
                "-o",
                str(elf),
                str(ROOT / "standalone" / "start.S"),
                str(ROOT / "standalone" / "main.c"),
            ]
        )
        run([str(objcopy), "-O", "binary", str(elf), str(raw)])
        write_psexe(
            raw.read_bytes(),
            output,
            load_address=BASE_ADDRESS,
            entry_point=BASE_ADDRESS,
            stack_pointer=STACK_POINTER,
            region="n00bROM bare metal",
        )

    # Add the final release artifact to the native-build provenance manifest
    # when both outputs are produced into the same directory (as in CI).
    manifest_path = output.parent / "manifest.json"
    manifest = {}
    if manifest_path.is_file():
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["n00brom_baremetal_psexe_sha256"] = sha256(output)
    manifest["n00brom_baremetal_psexe_size"] = str(output.stat().st_size)
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--gcc", type=Path, required=True)
    parser.add_argument("--objcopy", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    build(args.gcc.resolve(), args.objcopy.resolve(), args.output.resolve())


if __name__ == "__main__":
    main()
