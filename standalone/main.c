/*
 * n00bROM standalone bare-metal runtime.
 *
 * This target intentionally talks to the PS1 GPU and SIO0 registers directly.
 * Its controller transport follows the documented flow in spicyjpeg's
 * ps1-bare-metal controller example, rather than n00bROM's BIOS IRQ hook.
 */

typedef unsigned char  u8;
typedef unsigned short u16;
typedef unsigned int   u32;

#define MMIO8(address)  (*(volatile u8  *)(address))
#define MMIO16(address) (*(volatile u16 *)(address))
#define MMIO32(address) (*(volatile u32 *)(address))

#define GPU_GP0 MMIO32(0x1f801810)
#define GPU_GP1 MMIO32(0x1f801814)

#define SIO0_DATA MMIO8(0x1f801040)
#define SIO0_STAT MMIO16(0x1f801044)
#define SIO0_MODE MMIO16(0x1f801048)
#define SIO0_CTRL MMIO16(0x1f80104a)
#define SIO0_BAUD MMIO16(0x1f80104e)
#define IRQ_STAT  MMIO16(0x1f801070)

#define SIO_STAT_TX_NOT_FULL 0x0001
#define SIO_STAT_RX_NOT_EMPTY 0x0002
#define IRQ_SIO0              0x0080

#define SIO_CTRL_TX_ENABLE      0x0001
#define SIO_CTRL_DTR            0x0002
#define SIO_CTRL_RX_ENABLE      0x0004
#define SIO_CTRL_ACKNOWLEDGE    0x0010
#define SIO_CTRL_RESET          0x0040
#define SIO_CTRL_DSR_IRQ_ENABLE 0x1000

#define PAD_SELECT 0x0001
#define PAD_START  0x0008
#define PAD_UP     0x0010
#define PAD_RIGHT  0x0020
#define PAD_DOWN   0x0040
#define PAD_LEFT   0x0080
#define PAD_CROSS  0x4000

#define SCREEN_WIDTH  320
#define SCREEN_HEIGHT 240

/* RGB is stored by GP0 as little-endian 0x00BBGGRR. */
#define RGB(r, g, b) ((u32) (r) | ((u32) (g) << 8) | ((u32) (b) << 16))

static int page;
static int menuItem;
static int videoMode;
static int backgroundMode;
static int controllerPresent = -1;
static u8 controllerType;
static u16 previousButtons = 0xffff;

static void delayMicroseconds(int microseconds) {
	/* 34 short iterations are approximately one microsecond on the R3000A. */
	volatile int count = microseconds * 17;
	while (count-- > 0)
		__asm__ volatile("nop");
}

static void waitGP0(void) {
	while (!(GPU_GP1 & (1u << 26)))
		__asm__ volatile("");
}

static void gp0(u32 command) {
	waitGP0();
	GPU_GP0 = command;
}

static void fillRect(int x, int y, int width, int height, u32 color) {
	gp0(0x02000000 | color);
	gp0((u32) x | ((u32) y << 16));
	gp0((u32) width | ((u32) height << 16));
}

static void drawBlock(int x, int y, int scale, u32 color) {
	gp0(0x60000000 | color);
	gp0((u32) x | ((u32) y << 16));
	gp0((u32) scale | ((u32) scale << 16));
}

static void initGPU(void) {
	GPU_GP1 = 0x00000000; /* Reset GPU. */
	GPU_GP1 = 0x05000000; /* Display VRAM origin. */
	GPU_GP1 = 0x06c58258; /* Horizontal display range for 320 pixels. */
	GPU_GP1 = 0x07040010; /* NTSC vertical range. */
	GPU_GP1 = 0x08000001; /* 320x240, 15-bit, NTSC. */
	GPU_GP1 = 0x03000000; /* Enable display. */

	gp0(0xe1000000); /* Draw mode. */
	gp0(0xe3000000); /* Draw area top-left. */
	gp0(0xe403bd3f); /* Draw area bottom-right (319, 239). */
	gp0(0xe5000000); /* Draw offset. */
}

static void initControllerBus(void) {
	/* Same SIO0 format, clock and ACK policy as ps1-bare-metal's example. */
	SIO0_CTRL = SIO_CTRL_RESET;
	SIO0_MODE = 0x000d; /* 8 bits, no parity, divisor 1. */
	SIO0_BAUD = 135;    /* 33,868,800 / 250,000 rounded. */
	SIO0_CTRL = SIO_CTRL_TX_ENABLE | SIO_CTRL_RX_ENABLE |
		SIO_CTRL_DSR_IRQ_ENABLE;
}

static int waitForAcknowledge(void) {
	int timeout;
	for (timeout = 0; timeout < 12; timeout++) {
		if (IRQ_STAT & IRQ_SIO0) {
			IRQ_STAT = (u16) ~IRQ_SIO0;
			SIO0_CTRL |= SIO_CTRL_ACKNOWLEDGE;
			return 1;
		}
		delayMicroseconds(10);
	}
	return 0;
}

static u8 exchangeByte(u8 value) {
	while (!(SIO0_STAT & SIO_STAT_TX_NOT_FULL))
		__asm__ volatile("");
	SIO0_DATA = value;
	while (!(SIO0_STAT & SIO_STAT_RX_NOT_EMPTY))
		__asm__ volatile("");
	return SIO0_DATA;
}

static int pollController(u16 *buttons, u8 *type) {
	u8 response[4];
	int index;

	/* Assert /CS (DTR), then let the controller settle before address byte. */
	IRQ_STAT = (u16) ~IRQ_SIO0;
	SIO0_CTRL = SIO_CTRL_TX_ENABLE | SIO_CTRL_RX_ENABLE |
		SIO_CTRL_DSR_IRQ_ENABLE | SIO_CTRL_DTR;
	delayMicroseconds(60);
	SIO0_DATA = 0x01;
	if (!waitForAcknowledge())
		goto no_controller;

	/* Discard the address reply and collect a standard 0x42 poll response. */
	while (SIO0_STAT & SIO_STAT_RX_NOT_EMPTY)
		(void) SIO0_DATA;

	response[0] = exchangeByte(0x42);
	if (!waitForAcknowledge())
		goto no_controller;
	response[1] = exchangeByte(0x00);
	if (!waitForAcknowledge())
		goto no_controller;
	response[2] = exchangeByte(0x00);
	if (!waitForAcknowledge())
		goto no_controller;
	response[3] = exchangeByte(0x00);
	(void) waitForAcknowledge();

	/* 0x4x digital, 0x5x analog stick and 0x7x DualShock are accepted. */
	if ((response[0] & 0xf0) < 0x40)
		goto no_controller;
	*type = response[0];
	*buttons = (u16) response[2] | ((u16) response[3] << 8);

	delayMicroseconds(60);
	SIO0_CTRL = SIO_CTRL_TX_ENABLE | SIO_CTRL_RX_ENABLE |
		SIO_CTRL_DSR_IRQ_ENABLE;
	return 1;

no_controller:
	for (index = 0; index < 8 && (SIO0_STAT & SIO_STAT_RX_NOT_EMPTY); index++)
		(void) SIO0_DATA;
	SIO0_CTRL = SIO_CTRL_TX_ENABLE | SIO_CTRL_RX_ENABLE |
		SIO_CTRL_DSR_IRQ_ENABLE;
	return 0;
}

/* A compact 5x7, uppercase-only display font. Each row is five low bits. */
static u8 glyphRow(char character, int row) {
	static const u8 letters[26][7] = {
		{14,17,17,31,17,17,17}, {30,17,17,30,17,17,30},
		{15,16,16,16,16,16,15}, {30,17,17,17,17,17,30},
		{31,16,16,30,16,16,31}, {31,16,16,30,16,16,16},
		{15,16,16,23,17,17,15}, {17,17,17,31,17,17,17},
		{31,4,4,4,4,4,31}, {7,2,2,2,2,18,12},
		{17,18,20,24,20,18,17}, {16,16,16,16,16,16,31},
		{17,27,21,21,17,17,17}, {17,25,21,19,17,17,17},
		{14,17,17,17,17,17,14}, {30,17,17,30,16,16,16},
		{14,17,17,17,21,18,13}, {30,17,17,30,20,18,17},
		{15,16,16,14,1,1,30}, {31,4,4,4,4,4,4},
		{17,17,17,17,17,17,14}, {17,17,17,17,17,10,4},
		{17,17,17,21,21,21,10}, {17,17,10,4,10,17,17},
		{17,17,10,4,4,4,4}, {31,1,2,4,8,16,31}
	};
	static const u8 digits[10][7] = {
		{14,17,19,21,25,17,14}, {4,12,4,4,4,4,14},
		{14,17,1,2,4,8,31}, {30,1,1,14,1,1,30},
		{2,6,10,18,31,2,2}, {31,16,30,1,1,17,14},
		{6,8,16,30,17,17,14}, {31,1,2,4,8,8,8},
		{14,17,17,14,17,17,14}, {14,17,17,15,1,2,28}
	};

	if (character >= 'A' && character <= 'Z')
		return letters[character - 'A'][row];
	if (character >= '0' && character <= '9')
		return digits[character - '0'][row];
	if (character == ':')
		return (row == 2 || row == 5) ? 4 : 0;
	if (character == '-')
		return row == 3 ? 14 : 0;
	if (character == '/')
		return 1u << (4 - ((row * 5) / 7));
	if (character == '>')
		return (row == 1 || row == 5) ? 2 : (row == 2 || row == 4) ? 4 : row == 3 ? 8 : 0;
	if (character == '.')
		return row == 6 ? 4 : 0;
	return 0;
}

static void drawChar(int x, int y, char character, int scale, u32 color) {
	int row, column;
	for (row = 0; row < 7; row++) {
		u8 pixels = glyphRow(character, row);
		for (column = 0; column < 5; column++) {
			if (pixels & (1u << (4 - column)))
				drawBlock(x + column * scale, y + row * scale, scale, color);
		}
	}
}

static void drawText(int x, int y, const char *text, int scale, u32 color) {
	int cursor = x;
	while (*text) {
		if (*text == '\n') {
			y += 8 * scale;
			cursor = x;
		} else {
			drawChar(cursor, y, *text, scale, color);
			cursor += 6 * scale;
		}
		text++;
	}
}

static const char *controllerName(void) {
	if (controllerPresent <= 0)
		return "WAITING";
	if ((controllerType & 0xf0) == 0x40)
		return "DIGITAL";
	if ((controllerType & 0xf0) == 0x50)
		return "ANALOG STICK";
	if ((controllerType & 0xf0) == 0x70)
		return "DUALSHOCK";
	return "UNKNOWN";
}

static void renderHome(void) {
	fillRect(0, 0, SCREEN_WIDTH, SCREEN_HEIGHT,
		backgroundMode ? RGB(10, 20, 40) : RGB(30, 8, 45));
	fillRect(12, 12, 296, 32, RGB(20, 115, 150));
	drawText(26, 20, "N00BROM STANDALONE", 2, RGB(255, 255, 255));
	drawText(20, 64, "BARE METAL RUNTIME", 2, RGB(255, 220, 110));
	drawText(20, 92, "PAD 1:", 2, RGB(180, 230, 255));
	drawText(104, 92, controllerName(), 2, RGB(255, 255, 255));
	drawText(20, 122, "SELECT: SETTINGS", 2, RGB(255, 255, 255));
	drawText(20, 146, "START: DISC SERVICES", 2, RGB(255, 255, 255));
	drawText(20, 188, "INPUT IS DIRECT SIO0", 2, RGB(130, 255, 165));
}

static void renderMenu(void) {
	static const char *const items[] = {
		"VIDEO: AUTO", "BACKGROUND: PLASMA", "CONTROLLER: PORT 1",
		"DISC SERVICES", "HARDWARE TOOLS", "RETURN"
	};
	int index;
	fillRect(0, 0, SCREEN_WIDTH, SCREEN_HEIGHT, RGB(8, 24, 40));
	drawText(20, 18, "N00BROM SETTINGS", 2, RGB(255, 220, 110));
	for (index = 0; index < 6; index++) {
		u32 color = index == menuItem ? RGB(90, 255, 180) : RGB(255, 255, 255);
		if (index == 0 && videoMode == 1)
			drawText(44, 54 + index * 24, "VIDEO: NTSC", 2, color);
		else if (index == 0 && videoMode == 2)
			drawText(44, 54 + index * 24, "VIDEO: PAL", 2, color);
		else if (index == 1 && backgroundMode)
			drawText(44, 54 + index * 24, "BACKGROUND: BARS", 2, color);
		else
			drawText(44, 54 + index * 24, items[index], 2, color);
		if (index == menuItem)
			drawText(24, 54 + index * 24, ">", 2, color);
	}
	drawText(20, 210, "DPAD: MOVE  X: CHANGE", 1, RGB(180, 230, 255));
}

static void renderInfo(const char *title, const char *line1, const char *line2) {
	fillRect(0, 0, SCREEN_WIDTH, SCREEN_HEIGHT, RGB(45, 12, 28));
	drawText(20, 24, title, 2, RGB(255, 220, 110));
	drawText(20, 84, line1, 2, RGB(255, 255, 255));
	drawText(20, 116, line2, 2, RGB(255, 255, 255));
	drawText(20, 190, "SELECT OR START: RETURN", 1, RGB(130, 255, 165));
}

static void render(void) {
	if (page == 0)
		renderHome();
	else if (page == 1)
		renderMenu();
	else if (page == 2)
		renderInfo("DISC SERVICES", "CD BOOT PORT IN PROGRESS", "NO CARTRIDGE JUMP USED");
	else
		renderInfo("HARDWARE TOOLS", "EEPROM AND XPLORER NEED CART", "NOT TOUCHED IN EMULATOR");
}

static void handlePressed(u16 pressed) {
	if (page == 0) {
		if (pressed & PAD_SELECT)
			page = 1;
		else if (pressed & PAD_START)
			page = 2;
		return;
	}
	if (page == 1) {
		if (pressed & PAD_UP)
			menuItem = menuItem ? menuItem - 1 : 5;
		if (pressed & PAD_DOWN)
			menuItem = menuItem < 5 ? menuItem + 1 : 0;
		if (pressed & (PAD_SELECT | PAD_START))
			page = 0;
		if (pressed & PAD_CROSS) {
			if (menuItem == 0)
				videoMode = (videoMode + 1) % 3;
			else if (menuItem == 1)
				backgroundMode ^= 1;
			else if (menuItem == 3)
				page = 2;
			else if (menuItem == 4)
				page = 3;
			else if (menuItem == 5)
				page = 0;
		}
		return;
	}
	if (pressed & (PAD_SELECT | PAD_START | PAD_CROSS))
		page = 0;
}

int main(void) {
	int connected;
	u16 buttons;

	initGPU();
	initControllerBus();
	render();

	for (;;) {
		connected = pollController(&buttons, &controllerType);
		if (connected != controllerPresent) {
			controllerPresent = connected;
			previousButtons = 0xffff;
			render();
		}
		if (connected) {
			u16 pressed = previousButtons & (u16) ~buttons;
			previousButtons = buttons;
			if (pressed) {
				handlePressed(pressed);
				render();
			}
		}
		delayMicroseconds(1000);
	}
}
