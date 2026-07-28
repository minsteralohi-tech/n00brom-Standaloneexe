cmake_minimum_required(VERSION 3.25)

project(
	n00brom-Standaloneexe
	VERSION 1.0.0
	DESCRIPTION "n00bROM native ROM and bare-metal standalone PS-X EXE builder"
	LANGUAGES NONE
)

find_package(Python3 3.10 REQUIRED COMPONENTS Interpreter)

set(
	N00BROM_SOURCE_DIR ""
	CACHE PATH "n00bROM checkout root containing rom/n00brom.asm"
)
set(
	ARMIPS_EXECUTABLE ""
	CACHE FILEPATH "Path to the armips executable"
)
set(
	MIPS_GCC_EXECUTABLE ""
	CACHE FILEPATH "Path to a mipsel-none-elf-gcc or mipsel-linux-gnu-gcc executable"
)
if(NOT IS_DIRECTORY "${N00BROM_SOURCE_DIR}")
	message(FATAL_ERROR "Set N00BROM_SOURCE_DIR to a n00bROM checkout or release source directory")
endif()
if(NOT IS_EXECUTABLE "${ARMIPS_EXECUTABLE}")
	find_program(ARMIPS_EXECUTABLE armips)
endif()
if(NOT ARMIPS_EXECUTABLE)
	message(FATAL_ERROR "Set ARMIPS_EXECUTABLE or add armips to PATH")
endif()
if(NOT IS_EXECUTABLE "${MIPS_GCC_EXECUTABLE}")
	find_program(MIPS_GCC_EXECUTABLE NAMES mipsel-none-elf-gcc mipsel-linux-gnu-gcc)
endif()
if(NOT MIPS_GCC_EXECUTABLE)
	message(FATAL_ERROR "Set MIPS_GCC_EXECUTABLE for the bare-metal target")
endif()

set(DIST_DIR "${CMAKE_BINARY_DIR}/dist")
add_custom_command(
	OUTPUT
		"${DIST_DIR}/n00brom.rom"
		"${DIST_DIR}/n00brom-relocated-legacy.psexe"
		"${DIST_DIR}/manifest.json"
	COMMAND
		"${Python3_EXECUTABLE}"
		"${CMAKE_CURRENT_LIST_DIR}/tools/build_n00brom.py"
		--source-dir "${N00BROM_SOURCE_DIR}"
		--armips "${ARMIPS_EXECUTABLE}"
		--out-dir "${DIST_DIR}"
		WORKING_DIRECTORY "${CMAKE_CURRENT_BINARY_DIR}"
		DEPENDS
		"${CMAKE_CURRENT_LIST_DIR}/tools/build_n00brom.py"
		"${CMAKE_CURRENT_LIST_DIR}/tools/raw_to_psexe.py"
	VERBATIM
)
add_custom_command(
	OUTPUT
		"${DIST_DIR}/n00brom.psexe"
		"${DIST_DIR}/ps1-bare-metal-smoketest.psexe"
	COMMAND
		"${Python3_EXECUTABLE}"
		"${CMAKE_CURRENT_LIST_DIR}/tools/build_baremetal.py"
		--gcc "${MIPS_GCC_EXECUTABLE}"
		--output "${DIST_DIR}/n00brom.psexe"
		--smoke-output "${DIST_DIR}/ps1-bare-metal-smoketest.psexe"
	WORKING_DIRECTORY "${CMAKE_CURRENT_BINARY_DIR}"
	DEPENDS
		"${CMAKE_CURRENT_LIST_DIR}/tools/build_baremetal.py"
		"${CMAKE_CURRENT_LIST_DIR}/tools/elf_to_psexe.py"
		"${CMAKE_CURRENT_LIST_DIR}/standalone/bare.ld"
		"${CMAKE_CURRENT_LIST_DIR}/standalone/start.S"
		"${CMAKE_CURRENT_LIST_DIR}/standalone/cache.s"
		"${CMAKE_CURRENT_LIST_DIR}/standalone/ps1_gpu.h"
		"${CMAKE_CURRENT_LIST_DIR}/standalone/main.c"
		"${CMAKE_CURRENT_LIST_DIR}/standalone/smoke.c"
	VERBATIM
)
add_custom_target(n00brom ALL DEPENDS
	"${DIST_DIR}/n00brom.rom"
	"${DIST_DIR}/n00brom.psexe"
	"${DIST_DIR}/ps1-bare-metal-smoketest.psexe"
	"${DIST_DIR}/n00brom-relocated-legacy.psexe"
	"${DIST_DIR}/manifest.json"
)
