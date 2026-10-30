// 验证：不同 CUDA Toolkit 对 sm_89(Ada) / sm_120(Blackwell) 的支持
//
// 编译:
//   nvcc -arch=sm_89  -o t89  sm_arch_check.cu    # 4060
//   nvcc -arch=sm_120 -o t120 sm_arch_check.cu    # 5060 Ti
//
// CUDA 12.6 编译 sm_120 会报:
//   nvcc fatal : Unsupported gpu architecture 'compute_120'
// CUDA 12.8+ 才支持。
#include <cstdio>
#include <cuda_runtime.h>

__global__ void fill(float* out, int n) {
    int i = blockIdx.x * blockDim.x + threadIdx.x;
    if (i < n) out[i] = static_cast<float>(i) * 0.5f;
}

int main(int argc, char** argv) {
    int dev = 0;
    if (argc > 1) dev = atoi(argv[1]);
    cudaSetDevice(dev);

    cudaDeviceProp p{};
    cudaGetDeviceProperties(&p, dev);
    printf("device[%d] %s\n", dev, p.name);
    printf("  compute capability : sm_%d%d\n", p.major, p.minor);
    printf("  SM count           : %d\n", p.multiProcessorCount);
    printf("  global memory      : %.2f GiB\n",
           static_cast<double>(p.totalGlobalMem) / 1073741824.0);

    const int n = 1 << 20;
    float* d = nullptr;
    cudaError_t e = cudaMalloc(&d, n * sizeof(float));
    if (e != cudaSuccess) {
        printf("  cudaMalloc FAILED: %s\n", cudaGetErrorString(e));
        return 1;
    }
    fill<<<n / 256, 256>>>(d, n);
    e = cudaGetLastError();
    if (e != cudaSuccess) {
        printf("  kernel launch FAILED: %s\n", cudaGetErrorString(e));
        return 1;
    }
    e = cudaDeviceSynchronize();
    if (e != cudaSuccess) {
        printf("  sync FAILED: %s\n", cudaGetErrorString(e));
        return 1;
    }
    float h0 = -1.0f;
    cudaMemcpy(&h0, d, sizeof(float), cudaMemcpyDeviceToHost);
    printf("  kernel ran OK, out[0]=%.1f\n", h0);
    printf("  RESULT: OK\n");
    cudaFree(d);
    return 0;
}
