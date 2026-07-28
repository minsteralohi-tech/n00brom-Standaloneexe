/*
 * Visual hardware smoke test, based directly on ps1-bare-metal's
 * 01_basicGraphics example (ISC license).
 */

#include "ps1_gpu.h"

int main(void) {
	setupGPU();

	fillVRAM(0, 0, SCREEN_WIDTH, SCREEN_HEIGHT, RGB(64, 64, 64));

	/* Gouraud shaded triangle: red, green and blue vertices. */
	sendGP0(0x30000000u | RGB(255, 0, 0));
	sendGP0(XY(SCREEN_WIDTH / 2, 32));
	sendGP0(RGB(0, 255, 0));
	sendGP0(XY(32, SCREEN_HEIGHT - 32));
	sendGP0(RGB(0, 0, 255));
	sendGP0(XY(SCREEN_WIDTH - 32, SCREEN_HEIGHT - 32));

	showFramebuffer();

	for (;;)
		__asm__ volatile("");
}
