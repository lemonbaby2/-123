cmake_minimum_required(VERSION 3.16)
project(diffbot_description)

find_package(ament_cmake REQUIRED)

# 描述包没有可编译代码，全部是 URDF/YAML/RViz 资源。
# 用 install(DIRECTORY ...) 把它们装到 share/<包名>/ 下，
# 这样 $(find diffbot_description)/urdf/xxx.xacro 在 install 空间也能找到。
install(DIRECTORY urdf config launch rviz
        DESTINATION share/${PROJECT_NAME}
        USE_SOURCE_PERMISSIONS)

install(PROGRAMS
        scripts/check_urdf_deps.sh
        DESTINATION lib/${PROJECT_NAME}
        OPTIONAL)

ament_package()
