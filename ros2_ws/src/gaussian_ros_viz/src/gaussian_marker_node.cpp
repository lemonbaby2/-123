#include <array>
#include <chrono>
#include <memory>
#include <vector>

#include "rclcpp/rclcpp.hpp"
#include "visualization_msgs/msg/marker.hpp"
#include "visualization_msgs/msg/marker_array.hpp"

class GaussianMarkerNode final : public rclcpp::Node {
 public:
  GaussianMarkerNode() : Node("gaussian_marker_node") {
    frame_id_ = declare_parameter<std::string>("frame_id", "map");
    publisher_ = create_publisher<visualization_msgs::msg::MarkerArray>(
        "gaussian_markers", rclcpp::QoS(1).transient_local().reliable());
    timer_ = create_wall_timer(std::chrono::milliseconds(500), [this] { publish_once(); });
  }

 private:
  void publish_once() {
    visualization_msgs::msg::MarkerArray message;
    const std::vector<std::array<double, 4>> points{{0.0, 0.0, 0.0, 0.06},
                                                     {0.2, 0.0, 0.05, 0.05},
                                                     {0.4, 0.1, 0.10, 0.07}};
    for (std::size_t index = 0; index < points.size(); ++index) {
      visualization_msgs::msg::Marker marker;
      marker.header.frame_id = frame_id_;
      marker.header.stamp = now();
      marker.ns = "synthetic_gaussians";
      marker.id = static_cast<int>(index);
      marker.type = visualization_msgs::msg::Marker::SPHERE;
      marker.action = visualization_msgs::msg::Marker::ADD;
      marker.pose.orientation.w = 1.0;
      marker.pose.position.x = points[index][0];
      marker.pose.position.y = points[index][1];
      marker.pose.position.z = points[index][2];
      marker.scale.x = marker.scale.y = marker.scale.z = 2.0 * points[index][3];
      marker.color.r = static_cast<float>(0.2 + 0.3 * index);
      marker.color.g = static_cast<float>(0.8 - 0.2 * index);
      marker.color.b = 0.9F;
      marker.color.a = 0.9F;
      message.markers.push_back(marker);
    }
    publisher_->publish(message);
    timer_->cancel();
  }

  std::string frame_id_;
  rclcpp::Publisher<visualization_msgs::msg::MarkerArray>::SharedPtr publisher_;
  rclcpp::TimerBase::SharedPtr timer_;
};

int main(int argc, char** argv) {
  rclcpp::init(argc, argv);
  rclcpp::spin(std::make_shared<GaussianMarkerNode>());
  rclcpp::shutdown();
  return 0;
}
