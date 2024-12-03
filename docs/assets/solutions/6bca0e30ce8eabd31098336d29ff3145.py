import torch
import torch.nn as nn
from torch.utils.cpp_extension import load_inline

# Define the custom CUDA kernel for upper triangular matrix multiplication
upper_triangular_matmul_source = """
#include <torch/extension.h>
#include <cuda_runtime.h>

__global__ void upper_triangular_matmul_kernel(const float* A, const float* B, float* C, int N) {
    int row = blockIdx.y * blockDim.y + threadIdx.y;
    int col = blockIdx.x * blockDim.x + threadIdx.x;

    if (row < N && col < N && row <= col) {
        float sum = 0.0f;
        for (int k = row; k <= col; ++k) {
            sum += A[row * N + k] * B[k * N + col];
        }
        C[row * N + col] = sum;
    }
}

torch::Tensor upper_triangular_matmul_cuda(torch::Tensor A, torch::Tensor B) {
    auto N = A.size(0);
    auto C = torch::zeros({N, N}, A.options());

    const int block_size = 16;
    dim3 dim_block(block_size, block_size);
    dim3 dim_grid((N + block_size - 1) / block_size, (N + block_size - 1) / block_size);

    upper_triangular_matmul_kernel<<<dim_grid, dim_block>>>(A.data_ptr<float>(), B.data_ptr<float>(), C.data_ptr<float>(), N);

    return C;
}
"""

upper_triangular_matmul_cpp_source = "torch::Tensor upper_triangular_matmul_cuda(torch::Tensor A, torch::Tensor B);"

# Compile the inline CUDA code for upper triangular matrix multiplication
upper_triangular_matmul = load_inline(
    name='upper_triangular_matmul',
    cpp_sources=upper_triangular_matmul_cpp_source,
    cuda_sources=upper_triangular_matmul_source,
    functions=['upper_triangular_matmul_cuda'],
    verbose=True,
    extra_cflags=[''],
    extra_ldflags=['']
)

class ModelNew(nn.Module):
    def __init__(self):
        super(ModelNew, self).__init__()
        self.upper_triangular_matmul = upper_triangular_matmul
    
    def forward(self, A, B):
        return self.upper_triangular_matmul.upper_triangular_matmul_cuda(A, B)