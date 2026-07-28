# n00bROM standalone PS-X EXE build

This repository packages the proven n00bROM 0.30b source for two PS1 targets:

- `n00brom.rom`: the original cartridge firmware image (`romhead.bin +
  ramprog.bin`), built with Kingcom's armips assembler.
- `n00brom.psexe`: a standalone BIOS-loadable PS-X EXE. It relocates the
  n00bROM RAM program together with the routines/data that normally live in
  the cartridge ROM window into main RAM. It is useful for emulator and
  development-loader testing; cartridge-only expansion-port behavior cannot be
  provided by a RAM executable.

The PS-X EXE layout follows the format and address conventions used by
[spicyjpeg/ps1-bare-metal](https://github.com/spicyjpeg/ps1-bare-metal). The
source transformation is deliberately limited to the original n00bROM assembly:
the normal cartridge build remains byte-for-byte in the upstream build path,
while the standalone build removes the cartridge bootstrap/break-vector phase,
changes the exception-only delay slot to a normal `nop`, and co-locates the
RAM-resident code, configuration, strings, tables and firmware routines.

## Prerequisites

- Python 3.10 or newer
- CMake 3.25 or newer (only needed for the CMake target)
- Kingcom armips
- An upstream n00bROM checkout or release source archive, pinned to 0.30b

The repository does not vendor third-party source. This keeps licensing and
provenance clear and lets CI pin the exact upstream revision.

## Local build

Set `N00BROM_SOURCE_DIR` to a checkout whose root contains `rom/n00brom.asm`.
The attached source archive can be extracted to a temporary directory and used
the same way.

```powershell
python tools\build_n00brom.py `
  --source-dir C:\path\to\n00brom `
  --armips C:\path\to\armips.exe `
  --out-dir dist
```

The command writes `dist/n00brom.rom`, `dist/n00brom.psexe` and a
`dist/manifest.json` containing the upstream revision, source hash and output
hashes. The standalone output is a valid PS-X EXE (`PS-X EXE` magic, aligned
payload, load address `0x80010000`, and entry point inside the payload).

For CMake users:

```powershell
cmake -S . -B build -G Ninja `
  -DN00BROM_SOURCE_DIR=C:\path\to\n00brom `
  -DARMIPS_EXECUTABLE=C:\path\to\armips.exe
cmake --build build --target n00brom
```

## GitHub Actions

`.github/workflows/build.yml` builds armips from its upstream CMake project,
checks out n00bROM tag `0.30b`, generates both images, verifies the PS-X EXE
header, and uploads the images plus manifest as a workflow artifact. It runs on
push, pull request, and manual dispatch.

## Provenance and licensing

n00bROM is by Lameguy64 and contributors; its original license and source
remain upstream at [Lameguy64/n00brom](https://github.com/Lameguy64/n00brom).
armips is by Kingcom and contributors. The PS1 executable layout reference is
MIT-licensed in [spicyjpeg/ps1-bare-metal](https://github.com/spicyjpeg/ps1-bare-metal).
This repository's build scripts are provided under the MIT license.

