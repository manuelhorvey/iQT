cmake_minimum_required(VERSION 3.14)

include(FetchContent)
find_package(PkgConfig REQUIRED)

# 1. Handle nlohmann_json (Header-only)
FetchContent_Declare(
  json
  GIT_REPOSITORY https://github.com/nlohmann/json.git
  GIT_TAG v3.11.2
)
FetchContent_MakeAvailable(json)

# 2. Handle cppzmq (ZMQ C++ headers)
FetchContent_Declare(
  cppzmq
  GIT_REPOSITORY https://github.com/zeromq/cppzmq.git
  GIT_TAG v4.10.0
)
FetchContent_MakeAvailable(cppzmq)

# 3. Handle libzmq (System library)
pkg_check_modules(ZMQ REQUIRED libzmq)

add_executable(QuantEngine main.cpp)

target_include_directories(QuantEngine PRIVATE 
    ${CMAKE_CURRENT_SOURCE_DIR}
    ${ZMQ_INCLUDE_DIRS}
)

target_link_libraries(QuantEngine PRIVATE 
    ${ZMQ_LIBRARIES}
    nlohmann_json
    cppzmq
)
