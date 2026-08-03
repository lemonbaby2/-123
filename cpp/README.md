# C++17 reference

This directory contains dependency-free reference operators suitable for profiling before ROS2 integration: a deterministic voxel centroid filter, a fixed-state coulomb counter, and a static periodic-task budget check.

```bash
cmake -S cpp -B build/cpp
cmake --build build/cpp --config Release
ctest --test-dir build/cpp -C Release --output-on-failure
```

The code is educational and does not replace PCL/CUDA, a production BMS estimator, MISRA analysis, WCET proof, or target-board HIL tests.
