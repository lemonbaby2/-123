cmake_minimum_required(VERSION 3.16)
project(week12_odometry)

find_package(ament_cmake REQUIRED)

# 资源：launch / 参数 / 世界 / RViz
install(DIRECTORY launch config worlds rviz
        DESTINATION share/${PROJECT_NAME}
        USE_SOURCE_PERMISSIONS)

# 可执行脚本统一装到 lib/<包名>/，ros2 run 才能找到
install(PROGRAMS
        scripts/velocity_arbiter.py
        scripts/odom_relay.py
        scripts/telemetry_node.py
        scripts/odom_eval.py
        scripts/check_w12.sh
        scripts/drive_demo.sh
        scripts/save_map.sh
        scripts/stop_all.sh
        DESTINATION lib/${PROJECT_NAME})

ament_package()
