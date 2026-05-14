cmake_minimum_required(VERSION 3.14)
project(InstitutionalQuantTrader VERSION 1.0)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED True)

# Add subdirectories for our execution engine (C++)
add_subdirectory(src/execution)
