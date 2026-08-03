#include <cmath>
#include <iostream>
#include <vector>

#include "portfolio/bms_estimator.hpp"
#include "portfolio/voxel_filter.hpp"

int main() {
  const std::vector<portfolio::Point3f> cloud{{0.01F, 0.01F, 0.0F},
                                               {0.02F, 0.02F, 0.0F},
                                               {1.0F, 1.0F, 1.0F}};
  const auto filtered = portfolio::voxel_downsample(cloud, 0.1F);
  if (filtered.size() != 2U) {
    std::cerr << "voxel filter check failed\n";
    return 1;
  }

  portfolio::CoulombCounter counter(3.0F, 0.8F);
  const auto soc = counter.update(1.0F, 1.0F);
  if (!(soc < 0.8F && soc > 0.79F)) {
    std::cerr << "SOC check failed\n";
    return 2;
  }

  const portfolio::PeriodicTask tasks[]{{"sample", 0.2F, 10.0F},
                                         {"estimate", 1.4F, 100.0F}};
  const auto load = portfolio::utilization(tasks);
  std::cout << "voxels=" << filtered.size() << " soc=" << soc
            << " utilization=" << load << '\n';
  return load < 0.7F ? 0 : 3;
}
