-- Automated framebuffer capture for local PCSX-Redux validation.
--
-- Run PCSX-Redux with -run, -exe and -dofile.  The output path is supplied
-- through N00BROM_CAPTURE so this script does not depend on the current
-- directory selected by the emulator.

local outputPath = os.getenv("N00BROM_CAPTURE")
local buttonName = os.getenv("N00BROM_BUTTON")
local frames = 0
local button

if not outputPath or outputPath == "" then
	printError("N00BROM_CAPTURE is not set")
	PCSX.quit(2)
end

if buttonName and buttonName ~= "" then
	button = PCSX.CONSTS.PAD.BUTTON[buttonName]
	if not button then
		printError("unknown N00BROM_BUTTON: " .. buttonName)
		PCSX.quit(4)
	end
end

function DrawImguiFrame()
	frames = frames + 1

	if button and frames == 60 then
		PCSX.SIO0.slots[1].pads[1].setOverride(button)
	end
	if button and frames == 68 then
		PCSX.SIO0.slots[1].pads[1].clearOverride(button)
	end

	if frames < 140 then
		return
	end

	local shot = PCSX.GPU.takeScreenShot()
	local output = Support.File.open(outputPath, "TRUNCATE")

	if output:failed() then
		printError("could not open capture: " .. outputPath)
		PCSX.quit(3)
		return
	end

	local width = tonumber(shot.width)
	local height = tonumber(shot.height)
	local bpp = tonumber(shot.bpp)

	output:writeMoveSlice(shot.data)
	output:close()
	print(string.format(
		"N00BROM_CAPTURE width=%d height=%d bpp=%d path=%s",
		width, height, bpp, outputPath
	))
	PCSX.quit(0)
end
