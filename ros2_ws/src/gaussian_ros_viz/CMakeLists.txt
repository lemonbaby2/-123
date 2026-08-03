cmake_minimum_required(VERSION 3.8)
project(gaussian_ros_viz)

find_package(ament_cmake REQUIRED)
find_package(rclcpp REQUIRED)
find_package(visualization_msgs REQUIRED)

add_executable(gaussian_marker_node src/gaussian_marker_node.cpp)
ament_target_dependencies(gaussian_marker_node rclcpp visualization_msgs)
target_compile_features(gaussian_marker_node PUBLIC cxx_std_17)

install(TARGETS gaussian_marker_node DESTINATION lib/${PROJECT_NAME})
install(DIRECTORY launch config DESTINATION share/${PROJECT_NAME})
ament_package()
