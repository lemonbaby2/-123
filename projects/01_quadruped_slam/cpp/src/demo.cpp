#include <iostream>
#include <vector>

#include "quadruped_slam/voxel_filter.hpp"

int main() {
  const std::vector<portfolio::Point3f> cloud{{0.01F, 0.01F, 0.0F},
                                               {0.02F, 0.02F, 0.0F},
                                               {1.0F, 1.0F, 1.0F}};
  const auto filtered = portfolio::voxel_downsample(cloud, 0.1F);
  if (filtered.size() != 2U) {
    std::cerr << "voxel filter check failed\n";
    return 1;
  }

  std::cout << "voxels=" << filtered.size() << '\n';
  return 0;
}
