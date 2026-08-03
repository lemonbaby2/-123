from launch import LaunchDescription
from launch_ros.actions import Node


def generate_launch_description():
    return LaunchDescription(
        [
            Node(
                package="gaussian_ros_viz",
                executable="gaussian_marker_node",
                name="gaussian_marker_node",
                parameters=[{"frame_id": "map"}],
                output="screen",
            )
        ]
    )
