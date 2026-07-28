cmake_minimum_required(VERSION 3.25)

project(
	n00brom-Standaloneexe
	VERSION 1.0.0
	DESCRIPTION "n00bROM native ROM and standalone PS-X EXE builder"
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
if(NOT IS_DIRECTORY "${N00BROM_SOURCE_DIR}")
	message(FATAL_ERROR "Set N00BROM_SOURCE_DIR to a n00bROM checkout or release source directory")
endif()
if(NOT IS_EXECUTABLE "${ARMIPS_EXECUTABLE}")
	find_program(ARMIPS_EXECUTABLE armips)
endif()
if(NOT ARMIPS_EXECUTABLE)
	message(FATAL_ERROR "Set ARMIPS_EXECUTABLE or add armips to PATH")
endif()

set(DIST_DIR "${CMAKE_BINARY_DIR}/dist")
add_custom_command(
	OUTPUT
		"${DIST_DIR}/n00brom.rom"
		"${DIST_DIR}/n00brom.psexe"
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
add_custom_target(n00brom ALL DEPENDS
	"${DIST_DIR}/n00brom.rom"
	"${DIST_DIR}/n00brom.psexe"
	"${DIST_DIR}/manifest.json"
)
