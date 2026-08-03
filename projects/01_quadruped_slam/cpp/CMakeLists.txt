cmake_minimum_required(VERSION 3.16)
project(quadruped_slam_cpp LANGUAGES CXX)

add_executable(quadruped_voxel_demo src/demo.cpp)
target_include_directories(quadruped_voxel_demo PRIVATE include)
target_compile_features(quadruped_voxel_demo PRIVATE cxx_std_17)

if(MSVC)
  target_compile_options(quadruped_voxel_demo PRIVATE /W4 /permissive-)
else()
  target_compile_options(quadruped_voxel_demo PRIVATE -Wall -Wextra -Wpedantic -Werror)
endif()

enable_testing()
add_test(NAME quadruped_voxel_demo COMMAND quadruped_voxel_demo)
