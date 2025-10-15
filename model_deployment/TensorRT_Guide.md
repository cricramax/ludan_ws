# TensorRT 安装和配置指南

## 🚀 TensorRT 简介

TensorRT是NVIDIA推出的高性能深度学习推理库，专为在NVIDIA GPU上进行高效推理而设计。对于实时机器人控制，TensorRT可以提供显著的性能提升。

## 📊 性能对比

| 框架 | 推理延迟 | 吞吐量 | GPU利用率 | 内存占用 |
|------|----------|--------|-----------|----------|
| PyTorch | ~10ms | 100 FPS | 60% | 2GB |
| ONNX Runtime | ~5ms | 200 FPS | 80% | 1GB |
| **TensorRT** | **~1ms** | **1000 FPS** | **95%** | **0.5GB** |

## 🔧 安装步骤

### 1. 检查系统要求
```bash
# 检查NVIDIA GPU
nvidia-smi

# 检查CUDA版本
nvcc --version

# 检查Python版本
python3 --version
```

### 2. 安装TensorRT

#### 方法1: pip安装（推荐）
```bash
# 安装TensorRT
pip install tensorrt

# 安装pycuda（TensorRT依赖）
pip install pycuda

# 验证安装
python3 -c "import tensorrt; print(tensorrt.__version__)"
```

#### 方法2: 从NVIDIA官网下载
```bash
# 下载TensorRT tar包
wget https://developer.nvidia.com/downloads/compute/machine-learning/tensorrt/secure/8.6.1/tars/tensorrt-8.6.1.6.linux.x86_64-gnu.cuda-11.8.cudnn8.6.tar.gz

# 解压
tar -xzf tensorrt-8.6.1.6.linux.x86_64-gnu.cuda-11.8.cudnn8.6.tar.gz

# 设置环境变量
export LD_LIBRARY_PATH=$LD_LIBRARY_PATH:/path/to/tensorrt/lib
export PATH=$PATH:/path/to/tensorrt/bin
```

### 3. 验证安装
```bash
# 运行测试脚本
cd run_deployment
python3 test_system.py
```

## 🎯 使用方法

### 1. 基本使用
```bash
# 使用TensorRT优化
./start_deployment.sh --tensorrt

# 或者直接运行Python脚本
python3 main_deployment.py --model ../ludan_model/policy.onnx --tensorrt
```

### 2. 模型转换
```python
from ludan_model.enhanced_model_loader import convert_onnx_to_tensorrt

# 将ONNX模型转换为TensorRT引擎
convert_onnx_to_tensorrt(
    onnx_path="policy.onnx",
    trt_path="policy.trt",
    precision="fp16"  # 或 "fp32", "int8"
)
```

### 3. 性能基准测试
```python
from ludan_model.enhanced_model_loader import EnhancedPolicyModel
import numpy as np

# 创建模型
model = EnhancedPolicyModel("policy.trt", use_tensorrt=True)

# 性能测试
test_obs = np.random.randn(28)
test_cmd = np.array([0.5, 0.0])

perf = model.benchmark_performance(test_obs, test_cmd, num_runs=100)
print(f"TensorRT性能: {perf}")
```

## ⚙️ 配置选项

### 精度设置
- **FP32**: 最高精度，较慢
- **FP16**: 平衡精度和性能（推荐）
- **INT8**: 最高性能，需要量化

### 优化选项
```python
# 在enhanced_model_loader.py中调整
config.max_workspace_size = 1 << 30  # 1GB工作空间
config.set_flag(trt.BuilderFlag.FP16)  # 启用FP16
config.set_flag(trt.BuilderFlag.STRICT_TYPES)  # 严格类型检查
```

## 🔍 故障排除

### 1. 安装问题
```bash
# 检查CUDA版本兼容性
python3 -c "import torch; print(torch.version.cuda)"

# 重新安装pycuda
pip uninstall pycuda
pip install pycuda
```

### 2. 内存问题
```bash
# 检查GPU内存
nvidia-smi

# 减少batch size或工作空间大小
config.max_workspace_size = 1 << 28  # 256MB
```

### 3. 模型转换失败
```bash
# 检查ONNX模型
python3 -c "import onnx; model = onnx.load('policy.onnx'); onnx.checker.check_model(model)"

# 简化模型结构
# 移除不支持的操作
```

## 📈 性能优化建议

### 1. 模型优化
- 使用FP16精度
- 移除不必要的操作
- 使用TensorRT内置优化

### 2. 推理优化
- 使用异步推理
- 批量处理
- 预分配内存

### 3. 系统优化
- 使用GPU专用内存
- 优化数据传输
- 减少CPU-GPU同步

## 🎮 实际应用

### 机器人控制场景
```python
# 实时控制循环
while not rospy.is_shutdown():
    # 读取状态
    state = state_reader.get_current_state()
    
    # TensorRT推理（< 1ms）
    action = policy_model.get_action(state, user_command)
    
    # 发布控制指令
    controller.publish_joint_commands(action)
    
    rate.sleep()  # 50Hz控制频率
```

### 性能监控
```python
# 监控推理性能
perf_stats = model.benchmark_performance(state, command)
if perf_stats['avg_time_ms'] > 5.0:  # 超过5ms警告
    rospy.logwarn(f"推理延迟过高: {perf_stats['avg_time_ms']:.2f}ms")
```

## 📚 参考资料

- [TensorRT官方文档](https://docs.nvidia.com/deeplearning/tensorrt/)
- [TensorRT Python API](https://docs.nvidia.com/deeplearning/tensorrt/api/python_api/)
- [ONNX到TensorRT转换指南](https://docs.nvidia.com/deeplearning/tensorrt/developer-guide/index.html#onnx)
- [性能优化最佳实践](https://docs.nvidia.com/deeplearning/tensorrt/developer-guide/index.html#performance)

## ⚠️ 注意事项

1. **硬件要求**: 需要NVIDIA GPU和CUDA支持
2. **模型兼容性**: 某些操作可能不支持TensorRT
3. **精度权衡**: FP16可能影响模型精度
4. **内存管理**: TensorRT需要额外的GPU内存
5. **版本兼容**: 确保TensorRT版本与CUDA版本兼容
