#pragma once

#include <algorithm>
#include <cmath>
#include <stdexcept>

namespace portfolio {

class CoulombCounter {
 public:
  CoulombCounter(float capacity_ah, float initial_soc)
      : capacity_as_(capacity_ah * 3600.0F), soc_(std::clamp(initial_soc, 0.0F, 1.0F)) {
    if (!(capacity_ah > 0.0F)) {
      throw std::invalid_argument("capacity must be positive");
    }
  }

  float update(float current_a, float dt_seconds) {
    if (!(dt_seconds > 0.0F) || !std::isfinite(current_a)) {
      throw std::invalid_argument("invalid sample");
    }
    soc_ = std::clamp(soc_ - current_a * dt_seconds / capacity_as_, 0.0F, 1.0F);
    return soc_;
  }

  [[nodiscard]] float soc() const noexcept { return soc_; }

 private:
  float capacity_as_;
  float soc_;
};

struct PeriodicTask {
  const char* name;
  float worst_case_ms;
  float period_ms;
};

template <std::size_t N>
float utilization(const PeriodicTask (&tasks)[N]) {
  float total = 0.0F;
  for (const auto& task : tasks) {
    if (!(task.period_ms > 0.0F) || task.worst_case_ms < 0.0F) {
      throw std::invalid_argument("invalid task budget");
    }
    total += task.worst_case_ms / task.period_ms;
  }
  return total;
}

}  // namespace portfolio
