cmake_minimum_required(VERSION 3.16)
project(bms_reference_cpp LANGUAGES CXX)

add_executable(bms_reference_demo src/demo.cpp)
target_include_directories(bms_reference_demo PRIVATE include)
target_compile_features(bms_reference_demo PRIVATE cxx_std_17)

if(MSVC)
  target_compile_options(bms_reference_demo PRIVATE /W4 /permissive-)
else()
  target_compile_options(bms_reference_demo PRIVATE -Wall -Wextra -Wpedantic -Werror)
endif()

enable_testing()
add_test(NAME bms_reference_demo COMMAND bms_reference_demo)
