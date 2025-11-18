cmake_minimum_required(VERSION 3.15)
project(RailwaySchedulerCpp VERSION 0.1.0 LANGUAGES CXX)

# C++ Standard
set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)

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

# ============================================================================
# Shared Library: Railway AI API (for external C++ applications)
# ============================================================================

add_library(railwayai SHARED
    cpp/src/railway_api.cpp
    cpp/src/railway_scheduler.cpp
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

# Install API documentation
install(FILES API_REFERENCE.md
    DESTINATION share/doc/railwayai
)

# ============================================================================
# Testing (Optional)
# ============================================================================

option(BUILD_TESTS "Build test suite" OFF)
if(BUILD_TESTS)
    enable_testing()
    
    # Find Google Test
    find_package(GTest REQUIRED)
    
    add_executable(test_scheduler
        tests/test_scheduler.cpp
    )
    
    target_link_libraries(test_scheduler
        railway_scheduler_core
        GTest::gtest_main
    )
    
    add_test(NAME SchedulerTests COMMAND test_scheduler)
endif()

# ============================================================================
# Documentation
# ============================================================================

option(BUILD_DOCS "Build documentation with Doxygen" OFF)
if(BUILD_DOCS)
    find_package(Doxygen)
    if(DOXYGEN_FOUND)
        set(DOXYGEN_IN ${CMAKE_CURRENT_SOURCE_DIR}/docs/Doxyfile.in)
        set(DOXYGEN_OUT ${CMAKE_CURRENT_BINARY_DIR}/Doxyfile)
        
        configure_file(${DOXYGEN_IN} ${DOXYGEN_OUT} @ONLY)
        
        add_custom_target(docs ALL
            COMMAND ${DOXYGEN_EXECUTABLE} ${DOXYGEN_OUT}
            WORKING_DIRECTORY ${CMAKE_CURRENT_BINARY_DIR}
            COMMENT "Generating API documentation with Doxygen"
            VERBATIM
        )
    endif()
endif()

# ============================================================================
# Print Configuration Summary
# ============================================================================

message(STATUS "")
message(STATUS "==================== Configuration Summary ====================")
message(STATUS "Project: ${PROJECT_NAME} v${PROJECT_VERSION}")
message(STATUS "Build Type: ${CMAKE_BUILD_TYPE}")
message(STATUS "C++ Standard: ${CMAKE_CXX_STANDARD}")
message(STATUS "Python: ${Python_VERSION} (${Python_EXECUTABLE})")
message(STATUS "pybind11: ${pybind11_VERSION}")
if(USE_LIBTORCH)
    message(STATUS "LibTorch: Enabled")
else()
    message(STATUS "LibTorch: Disabled (set USE_LIBTORCH=ON to enable)")
endif()
message(STATUS "Build Tests: ${BUILD_TESTS}")
message(STATUS "Build Docs: ${BUILD_DOCS}")
message(STATUS "===============================================================")
message(STATUS "")
