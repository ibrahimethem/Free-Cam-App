cmake_minimum_required(VERSION 3.24)
project(NoSubCamera LANGUAGES CXX)
if(NOT WIN32 OR NOT MSVC OR NOT CMAKE_SIZEOF_VOID_P EQUAL 8)
  message(FATAL_ERROR "Build on 64-bit Windows with Visual Studio 2022 or newer and Windows 11 SDK")
endif()
set(CMAKE_CXX_STANDARD 20)
set(CMAKE_MSVC_RUNTIME_LIBRARY "MultiThreaded$<$<CONFIG:Debug>:Debug>")
include(FetchContent)
# Official MIT-licensed Microsoft sources, pinned rather than following HEAD.
FetchContent_Declare(camera_sample GIT_REPOSITORY https://github.com/microsoft/Windows-Camera.git
  GIT_TAG 626f8b19c5f367602f2e89c6b314573d3776c9df)
FetchContent_Declare(wil GIT_REPOSITORY https://github.com/microsoft/wil.git
  GIT_TAG f6f3069ab39fb19c1f89fa5f2d3aa8a1118ace43)
FetchContent_GetProperties(camera_sample)
if(NOT camera_sample_POPULATED)
  FetchContent_Populate(camera_sample)
endif()
FetchContent_GetProperties(wil)
if(NOT wil_POPULATED)
  FetchContent_Populate(wil)
endif()
find_package(Python3 REQUIRED COMPONENTS Interpreter)
set(staged "${CMAKE_CURRENT_BINARY_DIR}/source")
execute_process(COMMAND "${Python3_EXECUTABLE}" "${CMAKE_CURRENT_SOURCE_DIR}/prepare_source.py"
  "${camera_sample_SOURCE_DIR}" "${staged}" COMMAND_ERROR_IS_FATAL ANY)
add_library(NoSubCamera SHARED
  "${staged}/SimpleMediaSource.cpp" "${staged}/SimpleMediaStream.cpp"
  "${staged}/VirtualCameraMediaSourceActivate.cpp" "${staged}/winrtCommon.cpp"
  "${staged}/dllmain.cpp" FrameReader.cpp Host.cpp NoSubCamera.def)
target_include_directories(NoSubCamera PRIVATE "${staged}" "${CMAKE_CURRENT_SOURCE_DIR}" "${wil_SOURCE_DIR}/include")
target_compile_definitions(NoSubCamera PRIVATE UNICODE _UNICODE NOMINMAX WIN32_LEAN_AND_MEAN)
target_compile_options(NoSubCamera PRIVATE /W4 /EHsc /permissive-)
target_link_libraries(NoSubCamera PRIVATE mfplat mf mfuuid mfreadwrite mfsensorgroup
  windowsapp advapi32 ole32 bcrypt shlwapi)
add_executable(NoSubCameraSetup Setup.cpp)
target_compile_definitions(NoSubCameraSetup PRIVATE UNICODE _UNICODE NOMINMAX WIN32_LEAN_AND_MEAN)
target_link_libraries(NoSubCameraSetup PRIVATE advapi32 shell32 ole32 uuid user32)
target_link_options(NoSubCameraSetup PRIVATE "/MANIFESTUAC:level='requireAdministrator' uiAccess='false'")
file(MAKE_DIRECTORY "${CMAKE_CURRENT_BINARY_DIR}/licenses")
configure_file("${camera_sample_SOURCE_DIR}/LICENSE" "${CMAKE_CURRENT_BINARY_DIR}/licenses/Microsoft-Windows-Camera.txt" COPYONLY)
configure_file("${wil_SOURCE_DIR}/LICENSE" "${CMAKE_CURRENT_BINARY_DIR}/licenses/Microsoft-WIL.txt" COPYONLY)
add_custom_command(TARGET NoSubCamera POST_BUILD COMMAND "${CMAKE_COMMAND}" -E copy_directory
  "${CMAKE_CURRENT_BINARY_DIR}/licenses" "$<TARGET_FILE_DIR:NoSubCamera>/licenses")
add_executable(NoSubPixelTests tests/FramePixels.cpp)
target_include_directories(NoSubPixelTests PRIVATE "${CMAKE_CURRENT_SOURCE_DIR}")
add_executable(NoSubSourceTests tests/MediaSource.cpp)
target_include_directories(NoSubSourceTests PRIVATE "${CMAKE_CURRENT_SOURCE_DIR}")
target_compile_definitions(NoSubSourceTests PRIVATE UNICODE _UNICODE NOMINMAX WIN32_LEAN_AND_MEAN)
target_link_libraries(NoSubSourceTests PRIVATE mfplat mf mfuuid mfreadwrite ole32)
