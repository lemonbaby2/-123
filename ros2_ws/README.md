# ROS2 workspace skeleton

The workspace demonstrates the public contract for publishing a tiny synthetic Gaussian set as `visualization_msgs/MarkerArray`. It intentionally has no dependency on GraphDeco assets.

Target: Ubuntu 22.04 + ROS2 Humble (adapt package versions for newer distributions).

```bash
cd ros2_ws
colcon build --symlink-install
source install/setup.bash
ros2 launch gaussian_ros_viz demo.launch.py
```

In RViz2 set Fixed Frame to `map` and add a MarkerArray display on `/gaussian_markers`.
