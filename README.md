# n00bROM bare-metal standalone PS-X EXE

This repository produces two different PS1 images from the proven n00bROM
0.30b source:

- `n00brom.rom`: the original expansion-port cartridge firmware image
  (`romhead.bin + ramprog.bin`), built with Kingcom's armips assembler.
- `n00brom.psexe`: the standalone release. It is a new RAM-resident,
  direct-hardware program at `0x80010000`; it does **not** execute n00bROM's
  BIOS interrupt hook, cartridge ROM bootstrap, or expansion-port mappings.

The standalone runtime's GPU and SIO0 setup follows the proven register-level
patterns in [spicyjpeg/ps1-bare-metal](https://github.com/spicyjpeg/ps1-bare-metal).
Its controller transport enables RX, waits for DSR acknowledgements and accepts
digital, analog-stick and DualShock reply IDs on controller port 1. This avoids
the cartridge-era controller code that could display a frame but never accept
input in emulators.

## First bare-metal build

Load **only** `n00brom.psexe` from the current Actions artifact. Its opening
screen reads `N00BROM STANDALONE`, `BARE METAL RUNTIME`, and `INPUT IS DIRECT
SIO0`; a screen carrying n00bROM's original disclaimer is the retired
relocated reference build, not this executable.

- Press **SELECT** to open Settings.
- Press **START** to open the Disc Services status page.
- In Settings, use the **D-pad** to move, **Cross** to change the available
  in-memory video/background options, and **SELECT** or **START** to return.

The screen immediately changes `PAD 1: WAITING` to `DIGITAL`, `ANALOG STICK`
or `DUALSHOCK` after a compatible controller answers. That gives an explicit
controller transport check instead of treating a frozen splash screen as a
successful boot.

## Feature compatibility

The requested rewrite has to distinguish capabilities that belong to the
n00bROM program from capabilities that physically belong to the cartridge.

| Capability | Bare-metal EXE | Original cartridge ROM |
| --- | --- | --- |
| GPU home/settings UI and direct controller polling | Implemented | Implemented |
| Video/background settings for the running session | Implemented | Implemented and EEPROM-persistent |
| CD services | Dedicated direct-CD port in progress | Implemented through the intercepted BIOS bootstrap |
| Serial PS-X EXE loader and serial TTY | Direct-SIO1 port in progress | Implemented |
| Exception display | Bare exception handler port in progress | Implemented through BIOS hooks |
| EEPROM identification, save settings and flasher | Requires physical expansion-port EEPROM | Implemented with supported hardware |
| Xplorer upload/TTY/PCDRV | Requires physical Xplorer parallel hardware | Implemented with supported hardware |

n00bROM itself deliberately has **no cheat functionality**; attaching UniROM
or another cheat cartridge cannot turn a PS-X EXE into an expansion-port
firmware image. The standalone runtime therefore never probes, writes or
hooks a cartridge in an emulator. Hardware-only features stay in
`n00brom.rom`, where they belong.

`n00brom-relocated-legacy.psexe` is retained in the artifact only as a source
comparison reference. Do not use it for testing; it is the older conversion
approach being replaced.

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

The command writes `dist/n00brom.rom`, the legacy reference image and a
`dist/manifest.json`. Build the release standalone executable separately with
a MIPS GCC and objcopy pair:

```powershell
python tools\build_baremetal.py `
  --gcc C:\path\to\mipsel-none-elf-gcc.exe `
  --objcopy C:\path\to\mipsel-none-elf-objcopy.exe `
  --output dist\n00brom.psexe
```

The standalone output is a valid PS-X EXE (`PS-X EXE` magic, aligned payload,
load address `0x80010000`, and entry point inside the payload).

For CMake users:

```powershell
cmake -S . -B build -G Ninja `
  -DN00BROM_SOURCE_DIR=C:\path\to\n00brom `
  -DARMIPS_EXECUTABLE=C:\path\to\armips.exe
cmake --build build --target n00brom
```

## GitHub Actions

`.github/workflows/build.yml` builds armips from its upstream CMake project,
checks out n00bROM tag `0.30b`, builds the independent bare-metal EXE with a
MIPS cross compiler, verifies its PS-X EXE header and identifying strings, and
uploads the images plus manifest as a workflow artifact. It runs on push, pull
request and manual dispatch.

## Provenance and licensing

n00bROM is by Lameguy64 and contributors; its original license and source
remain upstream at [Lameguy64/n00brom](https://github.com/Lameguy64/n00brom).
armips is by Kingcom and contributors. The PS1 executable layout reference is
MIT-licensed in [spicyjpeg/ps1-bare-metal](https://github.com/spicyjpeg/ps1-bare-metal).
This repository's build scripts are provided under the MIT license.
