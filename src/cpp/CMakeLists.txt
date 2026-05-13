find_package(ZeroMQ REQUIRED)
find_package(nlohmann_json REQUIRED)

add_executable(QuantEngine main.cpp)

target_include_directories(QuantEngine PRIVATE ${CMAKE_CURRENT_SOURCE_DIR})
target_link_libraries(QuantEngine PRIVATE libzmq nlohmann_json::nlohmann_json)
