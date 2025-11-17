cmake_minimum_required(VERSION 3.20)
project(openglcts C CXX)

# Language standard
set(CMAKE_C_STANDARD 99)
set(CMAKE_CXX_STANDARD 17)

# Build type
option(ENABLE_DEBUG "Enable debug build" ON)
if(ENABLE_DEBUG)
        message(STATUS "Build type: Debug")
        set(CMAKE_BUILD_TYPE "Debug")
else()
        message(STATUS "Build type: Release")
        set(CMAKE_BUILD_TYPE "Release")
endif()

# Warnings
add_compile_options(-Wall -Wextra)

# Dependencies: minimal, only EGL + OpenGL ES 2.0 via pkg-config
find_package(PkgConfig REQUIRED)
pkg_check_modules(EGL REQUIRED egl)
pkg_check_modules(GLES2 REQUIRED glesv2)

# Executable: integrate GLES2 test harness (C++)
add_executable(openglcts
        main.cpp
        VK-GL-CTS/modules/gles2/tes2TestCase.cpp
        VK-GL-CTS/modules/gles2/tes2TestPackage.cpp
        VK-GL-CTS/modules/gles2/tes2CapabilityTests.cpp
        VK-GL-CTS/modules/gles2/tes2TestPackageEntry.cpp
        VK-GL-CTS/modules/gles2/tes2Context.cpp
        VK-GL-CTS/modules/gles2/tes2InfoTests.cpp
)

# Includes and compile flags from pkg-config
target_include_directories(openglcts PRIVATE
        ${EGL_INCLUDE_DIRS}
        ${GLES2_INCLUDE_DIRS}
)

target_compile_options(openglcts PRIVATE
        ${EGL_CFLAGS_OTHER}
        ${GLES2_CFLAGS_OTHER}
)

# Link libraries
target_link_libraries(openglcts PRIVATE
        cts_gles2_objects
        ${EGL_LIBRARIES}
        ${GLES2_LIBRARIES}
        m dl pthread
)

# Output directory
set_target_properties(openglcts PROPERTIES
        RUNTIME_OUTPUT_DIRECTORY "${CMAKE_BINARY_DIR}/bin"
)

# Optional: integrate VK-GL-CTS but only GLES2 without modifying internal files
option(BUILD_CTS_GLES2 "Build only the VK-GL-CTS GLES2 test binary (deqp-gles2)" ON)
if(BUILD_CTS_GLES2)
        # Raw, no add_subdirectory: directly add sources/headers to build deqp-gles2
        include(${CMAKE_CURRENT_LIST_DIR}/cts_gles2.cmake)
endif()
