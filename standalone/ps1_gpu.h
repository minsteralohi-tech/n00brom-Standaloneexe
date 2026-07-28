/*
 * Small GPU subset derived from spicyjpeg/ps1-bare-metal's gpucmd.h and
 * 01_basicGraphics example (ISC license).
 */

#ifndef N00BROM_PS1_GPU_H
#define N00BROM_PS1_GPU_H

typedef unsigned char u8;
typedef unsigned short u16;
typedef unsigned int u32;

#define MMIO8(address)  (*(volatile u8 *)(address))
#define MMIO16(address) (*(volatile u16 *)(address))
#define MMIO32(address) (*(volatile u32 *)(address))

#define GPU_GP0 MMIO32(0x1f801810)
#define GPU_GP1 MMIO32(0x1f801814)

#define GP1_STAT_CMD_READY (1u << 26)
#define GP1_STAT_PAL       (1u << 20)

#define SCREEN_WIDTH  320
#define SCREEN_HEIGHT 240

#define RGB(r, g, b) ((u32) (r) | ((u32) (g) << 8) | ((u32) (b) << 16))
#define XY(x, y)      (((u32) (x) & 0xffffu) | (((u32) (y) & 0xffffu) << 16))

static inline void waitForGP0Ready(void) {
	while (!(GPU_GP1 & GP1_STAT_CMD_READY))
		__asm__ volatile("");
}

static inline void sendGP0(u32 command) {
	waitForGP0Ready();
	GPU_GP0 = command;
}

static inline void setupGPU(void) {
	/*
	 * These are the same centered 320x240 ranges used by the official
	 * 01_basicGraphics example.  Preserve the loader's PAL/NTSC selection.
	 */
	u32 isPAL = GPU_GP1 & GP1_STAT_PAL;
	u32 centerY = isPAL ? 0xa3u : 0x88u;
	u32 offsetX = (SCREEN_WIDTH * 8u) / 2u;
	u32 offsetY = SCREEN_HEIGHT / 2u;
	u32 lowX = 0x760u - offsetX;
	u32 highX = 0x760u + offsetX;
	u32 lowY = centerY - offsetY;
	u32 highY = centerY + offsetY;

	GPU_GP1 = 0x00000000u;
	GPU_GP1 = 0x06000000u | lowX | (highX << 12);
	GPU_GP1 = 0x07000000u | lowY | (highY << 10);
	GPU_GP1 = 0x08000001u | (isPAL ? (1u << 3) : 0u);
	GPU_GP1 = 0x03000000u;

	sendGP0(0xe1000200u); /* Drawing page 0, dithering enabled. */
	sendGP0(0xe3000000u); /* Drawing area top-left: (0, 0). */
	sendGP0(0xe4000000u | 319u | (239u << 10));
	sendGP0(0xe5000000u); /* Drawing origin: (0, 0). */
}

static inline void showFramebuffer(void) {
	GPU_GP1 = 0x05000000u;
}

static inline void fillVRAM(int x, int y, int width, int height, u32 color) {
	sendGP0(0x02000000u | color);
	sendGP0(XY(x, y));
	sendGP0(XY(width, height));
}

#endif
