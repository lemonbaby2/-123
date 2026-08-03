#include <iostream>

#include "bms/bms_estimator.hpp"

int main() {
  portfolio::CoulombCounter counter(3.0F, 0.8F);
  const auto soc = counter.update(1.0F, 1.0F);
  if (!(soc < 0.8F && soc > 0.79F)) {
    std::cerr << "SOC check failed\n";
    return 1;
  }

  const portfolio::PeriodicTask tasks[]{{"sample", 0.2F, 10.0F},
                                         {"estimate", 1.4F, 100.0F}};
  const auto load = portfolio::utilization(tasks);
  std::cout << "soc=" << soc << " utilization=" << load << '\n';
  return load < 0.7F ? 0 : 2;
}
