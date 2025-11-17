# Raw integration of VK-GL-CTS GLES2 without add_subdirectory

# Pull in CTS platform/compiler defs (does not create targets)
include(${CMAKE_SOURCE_DIR}/VK-GL-CTS/framework/delibs/cmake/Defs.cmake NO_POLICY_SCOPE)
include(${CMAKE_SOURCE_DIR}/VK-GL-CTS/framework/delibs/cmake/CFlags.cmake NO_POLICY_SCOPE)

# Basic third-party deps used by the framework
find_package(ZLIB)
set(ZLIB_INCLUDE_PATH ${ZLIB_INCLUDE_DIRS})
set(ZLIB_LIBRARY ${ZLIB_LIBRARIES})
if (NOT ZLIB_INCLUDE_PATH OR NOT ZLIB_LIBRARY)
    message(FATAL_ERROR "zlib is required (install zlib dev)")
endif()
include_directories(${ZLIB_INCLUDE_PATH})

find_package(PNG)
set(PNG_INCLUDE_PATH ${PNG_INCLUDE_DIRS})
set(PNG_LIBRARY ${PNG_LIBRARIES})
if (NOT PNG_INCLUDE_PATH OR NOT PNG_LIBRARY)
    message(FATAL_ERROR "libpng is required (install libpng dev)")
endif()
include_directories(${PNG_INCLUDE_PATH})

# RenderDoc header (optional)
include_directories(${CMAKE_SOURCE_DIR}/VK-GL-CTS/external/renderdoc/src)

# Core framework include dirs expected by modules
include_directories(
    ${CMAKE_CURRENT_LIST_DIR}
    ${CMAKE_SOURCE_DIR}/VK-GL-CTS/framework/delibs/debase
    ${CMAKE_SOURCE_DIR}/VK-GL-CTS/framework/delibs/decpp
    ${CMAKE_SOURCE_DIR}/VK-GL-CTS/framework/delibs/depool
    ${CMAKE_SOURCE_DIR}/VK-GL-CTS/framework/delibs/dethread
    ${CMAKE_SOURCE_DIR}/VK-GL-CTS/framework/delibs/deutil
    ${CMAKE_SOURCE_DIR}/VK-GL-CTS/framework/delibs/destream
    ${CMAKE_SOURCE_DIR}/VK-GL-CTS/framework/common
    ${CMAKE_SOURCE_DIR}/VK-GL-CTS/framework/qphelper
    ${CMAKE_SOURCE_DIR}/VK-GL-CTS/framework/opengl
    ${CMAKE_SOURCE_DIR}/VK-GL-CTS/framework/opengl/wrapper
    ${CMAKE_SOURCE_DIR}/VK-GL-CTS/framework/referencerenderer
    ${CMAKE_SOURCE_DIR}/VK-GL-CTS/framework/opengl/simplereference
    ${CMAKE_SOURCE_DIR}/VK-GL-CTS/framework/randomshaders
    ${CMAKE_SOURCE_DIR}/VK-GL-CTS/framework/egl
    ${CMAKE_SOURCE_DIR}/VK-GL-CTS/framework/egl/wrapper
    ${CMAKE_SOURCE_DIR}/VK-GL-CTS/framework/xexml
    ${CMAKE_SOURCE_DIR}/VK-GL-CTS/modules
    ${CMAKE_SOURCE_DIR}/VK-GL-CTS/modules/glshared
    ${CMAKE_SOURCE_DIR}/VK-GL-CTS/modules/gles2
    ${CMAKE_SOURCE_DIR}/VK-GL-CTS/modules/gles2/functional
    ${CMAKE_SOURCE_DIR}/VK-GL-CTS/modules/gles2/accuracy
    ${CMAKE_SOURCE_DIR}/VK-GL-CTS/modules/gles2/performance
    ${CMAKE_SOURCE_DIR}/VK-GL-CTS/modules/gles2/stress
)

# Platform selection defines (mimic minimal defaults)
add_definitions(-DDEQP_TARGET_NAME="Default")

# Prefer runtime loading (no direct link) inside CTS wrappers
add_definitions(-DDEQP_SUPPORT_DRM=0)

# Collect framework sources (UNIX selection only where applicable)
file(GLOB_RECURSE DE_DEBASE_SRC        ${CMAKE_SOURCE_DIR}/VK-GL-CTS/framework/delibs/debase/*.c)
file(GLOB_RECURSE DE_DEPOOL_SRC        ${CMAKE_SOURCE_DIR}/VK-GL-CTS/framework/delibs/depool/*.c)
file(GLOB         DE_DETHREAD_SRC
    ${CMAKE_SOURCE_DIR}/VK-GL-CTS/framework/delibs/dethread/*.c
    ${CMAKE_SOURCE_DIR}/VK-GL-CTS/framework/delibs/dethread/unix/*.c)
file(GLOB_RECURSE DE_DESTREAM_SRC      ${CMAKE_SOURCE_DIR}/VK-GL-CTS/framework/delibs/destream/*.cpp)
file(GLOB_RECURSE DE_DEUTIL_SRC        ${CMAKE_SOURCE_DIR}/VK-GL-CTS/framework/delibs/deutil/*.c)
file(GLOB_RECURSE DE_DECPP_SRC         ${CMAKE_SOURCE_DIR}/VK-GL-CTS/framework/delibs/decpp/*.cpp)

file(GLOB QPHELPER_SRC                 ${CMAKE_SOURCE_DIR}/VK-GL-CTS/framework/qphelper/*.c)
file(GLOB XEXML_SRC                    ${CMAKE_SOURCE_DIR}/VK-GL-CTS/framework/xexml/*.cpp)

file(GLOB_RECURSE GL_WRAPPER_SRC       ${CMAKE_SOURCE_DIR}/VK-GL-CTS/framework/opengl/wrapper/*.cpp)
file(GLOB_RECURSE EGL_WRAPPER_SRC      ${CMAKE_SOURCE_DIR}/VK-GL-CTS/framework/egl/wrapper/*.cpp)
file(GLOB_RECURSE GL_UTIL_SRC          ${CMAKE_SOURCE_DIR}/VK-GL-CTS/framework/opengl/*.cpp)
file(GLOB_RECURSE EGL_UTIL_SRC         ${CMAKE_SOURCE_DIR}/VK-GL-CTS/framework/egl/*.cpp)
list(FILTER GL_UTIL_SRC EXCLUDE REGEX ".*/wrapper/.*")
list(FILTER EGL_UTIL_SRC EXCLUDE REGEX ".*/wrapper/.*")

file(GLOB_RECURSE RANDOMSHADERS_SRC    ${CMAKE_SOURCE_DIR}/VK-GL-CTS/framework/randomshaders/*.cpp)
file(GLOB_RECURSE REFERENCE_RENDERER_SRC ${CMAKE_SOURCE_DIR}/VK-GL-CTS/framework/referencerenderer/*.cpp)
file(GLOB_RECURSE COMMON_SRC           ${CMAKE_SOURCE_DIR}/VK-GL-CTS/framework/common/*.cpp)

# GL shared module utilities
file(GLOB_RECURSE GLSHARED_SRC         ${CMAKE_SOURCE_DIR}/VK-GL-CTS/modules/glshared/*.cpp)

# GLES2 modules
file(GLOB_RECURSE GLES2_ACC_SRC        ${CMAKE_SOURCE_DIR}/VK-GL-CTS/modules/gles2/accuracy/*.cpp)
file(GLOB_RECURSE GLES2_FUNC_SRC       ${CMAKE_SOURCE_DIR}/VK-GL-CTS/modules/gles2/functional/*.cpp)
file(GLOB_RECURSE GLES2_PERF_SRC       ${CMAKE_SOURCE_DIR}/VK-GL-CTS/modules/gles2/performance/*.cpp)
file(GLOB_RECURSE GLES2_STRESS_SRC     ${CMAKE_SOURCE_DIR}/VK-GL-CTS/modules/gles2/stress/*.cpp)
file(GLOB         GLES2_PKG_SRC
    ${CMAKE_SOURCE_DIR}/VK-GL-CTS/modules/gles2/tes2*.cpp
    ${CMAKE_SOURCE_DIR}/VK-GL-CTS/framework/platform/tcuMain.cpp)

# Minimal headless EGL platform to avoid Vulkan WSI/X11
include_directories(
    ${CMAKE_SOURCE_DIR}/VK-GL-CTS/framework/platform/null
)
file(GLOB PLATFORM_EGL_SRC
    ${CMAKE_SOURCE_DIR}/VK-GL-CTS/framework/platform/null/*.cpp)

# Define one big static lib to simplify link order
add_library(cts_gles2_objects STATIC
    ${DE_DEBASE_SRC}
    ${DE_DEPOOL_SRC}
    ${DE_DETHREAD_SRC}
    ${DE_DESTREAM_SRC}
    ${DE_DEUTIL_SRC}
    ${DE_DECPP_SRC}
    ${QPHELPER_SRC}
    ${XEXML_SRC}
    ${GL_WRAPPER_SRC}
    ${EGL_WRAPPER_SRC}
    ${GL_UTIL_SRC}
    ${EGL_UTIL_SRC}
    ${RANDOMSHADERS_SRC}
    ${REFERENCE_RENDERER_SRC}
    ${COMMON_SRC}
    ${GLSHARED_SRC}
    ${GLES2_ACC_SRC}
    ${GLES2_FUNC_SRC}
    ${GLES2_PERF_SRC}
    ${GLES2_STRESS_SRC}
    ${PLATFORM_EGL_SRC}
)

# Link public deps
target_link_libraries(cts_gles2_objects PUBLIC
    ${ZLIB_LIBRARY}
    ${PNG_LIBRARY}
)

# Ensure sufficient POSIX feature level for pthread TLS etc.
target_compile_definitions(cts_gles2_objects PRIVATE _XOPEN_SOURCE=600)

# Final executable similar to deqp-gles2
add_executable(deqp-gles2 ${GLES2_PKG_SRC})

# CTS expects runtime loading for GLES/EGL unless direct link is enabled.
# We still link the system libs to satisfy symbols when available.
target_link_libraries(deqp-gles2 PRIVATE
    cts_gles2_objects
    ${EGL_LIBRARIES}
    ${GLES2_LIBRARIES}
    m
    dl
    pthread
)

# Put it near our build bin
set_target_properties(deqp-gles2 PROPERTIES RUNTIME_OUTPUT_DIRECTORY ${CMAKE_BINARY_DIR}/VK-GL-CTS/modules/gles2)
