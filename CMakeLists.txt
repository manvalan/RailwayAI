cmake_minimum_required(VERSION 3.15)
project(RailwaySchedulerCpp VERSION 2.0.0 LANGUAGES CXX)

# C++ Standard
set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)

# Ensure all targets are compiled with -fPIC (needed for Python bindings)
set(CMAKE_POSITION_INDEPENDENT_CODE ON)

# Compiler flags
if(MSVC)
    add_compile_options(/W4)
else()
    add_compile_options(-Wall -Wextra -pedantic)
endif()

# Release optimization
if(CMAKE_BUILD_TYPE STREQUAL "Release")
    if(MSVC)
        add_compile_options(/O2)
    else()
        add_compile_options(-O3)
    endif()
endif()

# ============================================================================
# Dependencies
# ============================================================================

# Find Python
find_package(Python COMPONENTS Interpreter Development REQUIRED)

# Find pybind11 from pip package
execute_process(
    COMMAND ${Python_EXECUTABLE} -m pybind11 --cmakedir
    OUTPUT_VARIABLE pybind11_DIR
    OUTPUT_STRIP_TRAILING_WHITESPACE
)
find_package(pybind11 CONFIG REQUIRED PATHS ${pybind11_DIR})

# Find nlohmann_json (header-only)
include(FetchContent)
FetchContent_Declare(
    json
    URL https://github.com/nlohmann/json/releases/download/v3.11.3/json.tar.xz
)
FetchContent_MakeAvailable(json)

# Optional: LibTorch for ML model inference
option(USE_LIBTORCH "Enable LibTorch support for ML inference" OFF)
if(USE_LIBTORCH)
    find_package(Torch REQUIRED)
    set(CMAKE_CXX_FLAGS "${CMAKE_CXX_FLAGS} ${TORCH_CXX_FLAGS}")
    add_definitions(-DUSE_LIBTORCH)
endif()

# ============================================================================
# Library: Core Scheduler
# ============================================================================

add_library(railway_scheduler_core STATIC
    cpp/src/railway_scheduler.cpp
    cpp/src/ml_inference.cpp
)

target_include_directories(railway_scheduler_core PUBLIC
    cpp/include
    ${Python_INCLUDE_DIRS}
)

if(USE_LIBTORCH)
    target_link_libraries(railway_scheduler_core PUBLIC
        ${TORCH_LIBRARIES}
    )
endif()
target_link_libraries(railway_scheduler_core PUBLIC nlohmann_json::nlohmann_json)

# ============================================================================
# Shared Library: Railway AI API (for external C++ applications)
# ============================================================================

add_library(railwayai SHARED
    cpp/src/railway_api.cpp
    cpp/src/railway_scheduler.cpp
    cpp/src/ml_inference.cpp
)

target_include_directories(railwayai PUBLIC
    $<BUILD_INTERFACE:${CMAKE_CURRENT_SOURCE_DIR}/cpp/include>
    $<INSTALL_INTERFACE:include>
)

target_compile_definitions(railwayai PRIVATE RAILWAY_API_EXPORTS)

set_target_properties(railwayai PROPERTIES
    VERSION ${PROJECT_VERSION}
    SOVERSION 1
    PUBLIC_HEADER cpp/include/railway_api.h
    CXX_VISIBILITY_PRESET hidden
    VISIBILITY_INLINES_HIDDEN ON
)

if(USE_LIBTORCH)
    target_link_libraries(railwayai PUBLIC ${TORCH_LIBRARIES})
endif()
target_link_libraries(railwayai PUBLIC nlohmann_json::nlohmann_json)

# ============================================================================
# Python Module: railway_cpp
# ============================================================================

pybind11_add_module(railway_cpp 
    cpp/src/bindings.cpp
)

target_link_libraries(railway_cpp PRIVATE
    railway_scheduler_core
)

target_include_directories(railway_cpp PRIVATE
    cpp/include
)

# Set output directory for Python module
set_target_properties(railway_cpp PROPERTIES
    LIBRARY_OUTPUT_DIRECTORY "${CMAKE_BINARY_DIR}/python"
    ARCHIVE_OUTPUT_DIRECTORY "${CMAKE_BINARY_DIR}/python"
    RUNTIME_OUTPUT_DIRECTORY "${CMAKE_BINARY_DIR}/python"
)

# ============================================================================
# Installation
# ============================================================================

# Install shared library for external C++ apps
install(TARGETS railwayai
    LIBRARY DESTINATION lib
    ARCHIVE DESTINATION lib
    RUNTIME DESTINATION bin
    PUBLIC_HEADER DESTINATION include
)

# Install Python module
install(TARGETS railway_cpp
    LIBRARY DESTINATION python
    ARCHIVE DESTINATION python
    RUNTIME DESTINATION python
)

# Install all headers
install(DIRECTORY cpp/include/
    DESTINATION include
    FILES_MATCHING PATTERN "*.h"
)
