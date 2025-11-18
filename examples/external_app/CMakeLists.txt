cmake_minimum_required(VERSION 3.15)
project(RailwayClientApp VERSION 1.0.0 LANGUAGES CXX)

# C++ Standard
set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

# Find Railway AI library
find_library(RAILWAY_AI_LIB 
    NAMES railwayai
    HINTS 
        /usr/local/lib
        ${CMAKE_SOURCE_DIR}/../../build
    REQUIRED
)

find_path(RAILWAY_AI_INCLUDE
    NAMES railway_api.h
    HINTS
        /usr/local/include
        ${CMAKE_SOURCE_DIR}/../../cpp/include
    REQUIRED
)

message(STATUS "Found Railway AI library: ${RAILWAY_AI_LIB}")
message(STATUS "Found Railway AI headers: ${RAILWAY_AI_INCLUDE}")

# Create executable
add_executable(simple_client simple_client.cpp)

target_include_directories(simple_client PRIVATE ${RAILWAY_AI_INCLUDE})
target_link_libraries(simple_client PRIVATE ${RAILWAY_AI_LIB})

# Installation
install(TARGETS simple_client
    RUNTIME DESTINATION bin
)
