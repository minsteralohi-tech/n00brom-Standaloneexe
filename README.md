# n00bROM bare-metal standalone PS-X EXE

This repository produces two different PS1 images from the proven n00bROM
0.30b source:

- `n00brom.rom`: the original expansion-port cartridge firmware image
  (`romhead.bin + ramprog.bin`), built with Kingcom's armips assembler.
- `n00brom.psexe`: the standalone release. It is a new RAM-resident,
  direct-hardware program at `0x80010000`; it does **not** execute n00bROM's
  BIOS interrupt hook, cartridge ROM bootstrap, or expansion-port mappings.
- `n00brom-unirom-highram.psexe`: the same independent runtime linked at
  `0x80180000`, with 512 KiB reserved below the top-of-RAM stack. It is a
  diagnostic image for a suspected resident-loader RAM collision; the normal
  image remains at UniROM's documented conventional EXE address.
- `ps1-bare-metal-smoketest.psexe`: a deliberately tiny visual control based
  on ps1-bare-metal's `01_basicGraphics`; it displays a gray background and a
  red/green/blue shaded triangle.

The standalone runtime's GPU and SIO0 setup follows the proven register-level
patterns in [spicyjpeg/ps1-bare-metal](https://github.com/spicyjpeg/ps1-bare-metal).
Its controller transport enables RX, waits for DSR acknowledgements and accepts
digital, analog-stick and DualShock reply IDs on controller port 1. This avoids
the cartridge-era controller code that could display a frame but never accept
input in emulators.

## First bare-metal build

First load `ps1-bare-metal-smoketest.psexe`. If the gray screen and colored
triangle appear, PS-X EXE loading and GPU output are working in the emulator.
Then load **only** `n00brom.psexe` from the same Actions artifact. Its opening
screen reads `N00BROM STANDALONE`, `BARE METAL RUNTIME`, and `INPUT IS DIRECT
SIO0`; a screen carrying n00bROM's original disclaimer is the retired
relocated reference build, not this executable.

Do not use `00_helloWorld` as a video test: the upstream example writes
`Hello world!` to SIO1 serial and intentionally initializes no video output.
The standalone and smoke-test targets use the GPU sequence from
`01_basicGraphics`, including PAL/NTSC preservation, centered display ranges,
drawing-area setup and the final framebuffer display offset.

- Press **SELECT** to open Settings.
- Press **START** to open the Disc Services status page.
- In Settings, use the **D-pad** to move, **Cross** to change the available
  in-memory video/background options, and **SELECT** or **START** to return.

### PCSX-Redux keyboard controls

The PCSX-Redux configuration on this machine maps: **Start** = Enter,
**Select** = Tab, **D-pad** = arrow keys, **Cross** = X, **Circle** = D,
**Square** = Z and **Triangle** = S. L1/L2/L3 are Q/A/W and R1/R2/R3 are
R/F/T. These bindings can be changed from PCSX-Redux's controller settings.

### DuckStation and UniROM loading

In DuckStation, boot the file as an executable (not as a disc image):

```text
duckstation-qt-x64-ReleaseLTCG.exe -exe n00brom.psexe
```

The startup code establishes its own stack and `$gp`, invalidates the CPU
instruction cache, and disables inherited CPU interrupts before running C
code. That is required for serial transfer loaders such as UniROM, which may
otherwise leave stale code in cache or BIOS interrupts active. If DuckStation
still shows black, use its **interpreter** CPU mode once and disable
PGXP/runahead while testing; then capture its debug log.

For real hardware, first send the normal `n00brom.psexe` with NOPS `/exe`.
NOPS's public source shows that `/exe` transfers and uses the PS-X EXE header's
declared load and entry addresses, and its own published UniROM example uses
`0x80010000`; that makes a collision at the normal address unproven. If the
normal image still crashes after the cache/interrupt-safe startup, send
`n00brom-unirom-highram.psexe` instead. It uses the same code and controller
path at `0x80180000`, while keeping the conventional image available for
emulators and ordinary loaders. Do not use `/bin` for either image: `/bin`
does not interpret a PS-X EXE header.

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

The small linker/converter/GPU subsets derived from ps1-bare-metal retain
upstream attribution and its ISC license notice in
[`THIRD_PARTY_NOTICES.md`](THIRD_PARTY_NOTICES.md). n00bROM and armips source
remain upstream, and CI pins the n00bROM release tag and armips commit.

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
`dist/manifest.json`. Build the release standalone executable and visual
smoke test separately with a MIPS GCC:

```powershell
python tools\build_baremetal.py `
  --gcc C:\path\to\mipsel-none-elf-gcc.exe `
  --output dist\n00brom.psexe `
  --smoke-output dist\ps1-bare-metal-smoketest.psexe
```

To make the UniROM high-RAM diagnostic image locally, add
`--load-address 0x80180000` and choose a distinct output filename.

The ELF-to-EXE step is derived from ps1-bare-metal's proven
`convertExecutable.py`; it reads the ELF entry point and loadable segments
instead of assuming an objcopy-generated raw image.

For CMake users:

```powershell
cmake -S . -B build -G Ninja `
  -DN00BROM_SOURCE_DIR=C:\path\to\n00brom `
  -DARMIPS_EXECUTABLE=C:\path\to\armips.exe
cmake --build build --target n00brom
```

## GitHub Actions

`.github/workflows/build.yml` builds armips from its upstream CMake project,
checks out n00bROM tag `0.30b`, builds the independent bare-metal and smoke-test
EXEs with a MIPS cross compiler, verifies both PS-X EXE headers and identifying
strings, and uploads the images plus manifest as a workflow artifact. It runs
on push, pull request and manual dispatch.

## Provenance and licensing

n00bROM is by Lameguy64 and contributors; its original license and source
remain upstream at [Lameguy64/n00brom](https://github.com/Lameguy64/n00brom).
armips is by Kingcom and contributors. The derived linker, converter and GPU
initialization are based on the ISC-licensed
[spicyjpeg/ps1-bare-metal](https://github.com/spicyjpeg/ps1-bare-metal).
This repository's original build scripts are provided under the MIT license.
