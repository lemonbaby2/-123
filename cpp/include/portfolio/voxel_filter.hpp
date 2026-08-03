#pragma once

#include <algorithm>
#include <cmath>
#include <cstddef>
#include <stdexcept>
#include <tuple>
#include <unordered_map>
#include <vector>

namespace portfolio {

struct Point3f {
  float x{};
  float y{};
  float z{};
};

struct VoxelKey {
  int x{};
  int y{};
  int z{};
  bool operator==(const VoxelKey& other) const noexcept {
    return x == other.x && y == other.y && z == other.z;
  }
};

struct VoxelHash {
  std::size_t operator()(const VoxelKey& key) const noexcept {
    auto h = static_cast<std::size_t>(key.x) * 73856093U;
    h ^= static_cast<std::size_t>(key.y) * 19349663U;
    h ^= static_cast<std::size_t>(key.z) * 83492791U;
    return h;
  }
};

inline std::vector<Point3f> voxel_downsample(const std::vector<Point3f>& input,
                                             float leaf_size) {
  if (!(leaf_size > 0.0F)) {
    throw std::invalid_argument("leaf_size must be positive");
  }
  struct Accumulator {
    double x{};
    double y{};
    double z{};
    std::size_t count{};
  };
  std::unordered_map<VoxelKey, Accumulator, VoxelHash> voxels;
  voxels.reserve(input.size());
  for (const auto& point : input) {
    if (!std::isfinite(point.x) || !std::isfinite(point.y) || !std::isfinite(point.z)) {
      continue;
    }
    const VoxelKey key{static_cast<int>(std::floor(point.x / leaf_size)),
                       static_cast<int>(std::floor(point.y / leaf_size)),
                       static_cast<int>(std::floor(point.z / leaf_size))};
    auto& value = voxels[key];
    value.x += point.x;
    value.y += point.y;
    value.z += point.z;
    ++value.count;
  }
  std::vector<std::pair<VoxelKey, Accumulator>> ordered(voxels.begin(), voxels.end());
  std::sort(ordered.begin(), ordered.end(), [](const auto& left, const auto& right) {
    return std::tie(left.first.x, left.first.y, left.first.z) <
           std::tie(right.first.x, right.first.y, right.first.z);
  });
  std::vector<Point3f> output;
  output.reserve(ordered.size());
  for (const auto& [key, value] : ordered) {
    (void)key;
    const auto count = static_cast<double>(value.count);
    output.push_back(Point3f{static_cast<float>(value.x / count),
                            static_cast<float>(value.y / count),
                            static_cast<float>(value.z / count)});
  }
  return output;
}

}  // namespace portfolio
