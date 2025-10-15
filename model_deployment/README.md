# 机器人部署系统

这是一个基于ROS的机器人控制系统，能够读取机器人状态，使用深度学习模型进行决策，并通过用户界面控制机器人移动。

## 系统架构

```
model_deployment/
├── ludan_model/           # 模型文件
│   ├── policy.onnx       # ONNX格式的策略模型
│   ├── policy.pt          # PyTorch格式的策略模型
│   └── model_loader.py    # 模型加载器
└── run_deployment/        # 部署代码
    ├── state_reader.py    # ROS状态读取器
    ├── robot_controller.py # 机器人控制器
    ├── user_interface.py  # 用户界面
    ├── main_deployment.py # 主部署脚本
    └── start_deployment.sh # 启动脚本
```

## 功能特性

- **状态读取**: 实时读取机器人关节状态（位置、速度、力矩）
- **模型预测**: 支持ONNX、PyTorch和TensorRT模型，将机器人状态和用户指令输入模型
- **TensorRT优化**: 支持NVIDIA TensorRT加速，显著提升推理性能
- **用户控制**: 支持键盘控制（WASD键）和游戏手柄控制
- **日志输出模式**: 仅输出控制指令到日志，不实际控制机器人（安全测试）
- **ROS集成**: 完全基于ROS，发布关节控制指令
- **模块化设计**: 各组件独立，易于扩展和维护

## 依赖要求

### Python包
```bash
# 基础依赖
pip install rospy numpy torch onnxruntime

# TensorRT优化（可选，需要NVIDIA GPU）
pip install tensorrt pycuda
```

### ROS环境
- ROS Noetic (推荐)
- sensor_msgs
- std_msgs

## 使用方法

### 1. 基本启动
```bash
cd run_deployment
./start_deployment.sh
```

### 2. 无模型模式
```bash
./start_deployment.sh --no-model
```

### 3. 无键盘控制模式
```bash
./start_deployment.sh --no-keyboard
```

### 4. TensorRT优化模式
```bash
./start_deployment.sh --tensorrt
```

### 5. 仅日志输出模式（推荐用于测试）
```bash
./start_deployment.sh --log-only
```

### 6. 直接运行Python脚本
```bash
python3 main_deployment.py --model ../ludan_model/policy.onnx
```

## 控制说明

### 键盘控制
- **W**: 前进
- **S**: 后退  
- **A**: 左转
- **D**: 右转
- **空格**: 停止
- **Q**: 退出

### 指令格式
用户指令为二维向量 `[forward_back, left_right]`：
- `forward_back`: -1.0到1.0，负值表示后退
- `left_right`: -1.0到1.0，负值表示左转

## 系统组件

### 1. RobotStateReader
- 订阅 `/mcu_leftleg/joint_states` 和 `/mcu_rightleg/joint_states`
- 实时获取14个关节的状态信息
- 提供状态数据预处理功能

### 2. PolicyModel
- 支持ONNX、PyTorch和TensorRT模型加载
- 输入：机器人状态 + 用户指令
- 输出：动作指令
- TensorRT优化：显著提升推理性能

### 3. RobotController
- 将用户指令转换为速度指令
- 将速度指令转换为关节角度指令
- 发布ROS控制消息

### 4. SimpleUI
- 键盘输入处理
- 实时指令更新
- 支持游戏手柄（可选）

## 配置参数

### 控制参数
```python
max_linear_velocity = 1.0    # 最大线速度
max_angular_velocity = 1.0    # 最大角速度
command_scale = 0.5          # 指令缩放因子
```

### 状态处理
```python
state_dim = 42               # 状态维度 (14关节 × 3种数据)
max_history_length = 10       # 状态历史长度
```

## 故障排除

### 1. ROS环境问题
```bash
# 检查ROS环境
echo $ROS_PACKAGE_PATH

# 设置ROS环境
source /opt/ros/noetic/setup.bash
```

### 2. 模型加载失败
- 检查模型文件路径
- 确认模型文件格式正确
- 使用 `--no-model` 参数跳过模型

### 3. 状态数据超时
- 检查ROS话题是否正常发布
- 确认话题名称正确
- 检查网络连接

### 4. 键盘控制无响应
- 确认终端支持键盘输入
- 使用 `--no-keyboard` 参数禁用键盘控制
- 检查权限设置

## 扩展开发

### 添加新的输入方式
1. 继承 `CommandInterface` 类
2. 实现自定义的输入处理逻辑
3. 在主系统中注册回调函数

### 修改控制算法
1. 编辑 `RobotController.velocity_to_joint_commands()` 方法
2. 实现自定义的运动学模型
3. 调整控制参数

### 支持新的模型格式
1. 扩展 `ModelLoader` 类
2. 添加新的模型加载方法
3. 更新 `PolicyModel` 类

## 日志输出模式

### 功能说明
日志输出模式允许您观察和验证控制逻辑，而不实际控制机器人。这对于调试和测试非常有用。

### 使用方法
```bash
# 启动日志模式
./start_deployment.sh --log-only

# 或者直接运行
python3 main_deployment.py --log-only
```

### 日志输出内容
- **用户指令**: 前后/左右控制指令
- **速度指令**: 线速度和角速度
- **关节指令**: 14个关节的目标角度
- **关节变化**: 与上次指令的差异
- **机器人状态**: 当前关节位置和状态信息
- **控制模式**: 显示当前是日志模式还是实际控制模式

### 示例日志输出
```
============================================================
[1234567890.123] 机器人控制指令
============================================================
用户指令: 前后=0.500, 左右=0.000
速度指令: 线速度=0.250 m/s, 角速度=0.000 rad/s
左腿关节指令:
  leg_l1_joint: -12.500°
  leg_l2_joint: -7.500°
  ...
右腿关节指令:
  leg_r1_joint: 12.500°
  leg_r2_joint: 17.500°
  ...
关节指令变化:
左腿变化:
  leg_l2_joint: +5.000°
  leg_l4_joint: +2.500°
模式: 仅日志输出 (不实际控制机器人)
============================================================
```

### 测试脚本
```bash
# 运行日志输出测试
python3 test_log_output.py
```

## 注意事项

1. **安全第一**: 在真实机器人上测试前，请确保安全措施到位
2. **备份重要文件**: 修改代码前请备份原始文件
3. **测试环境**: 建议先在仿真环境中测试
4. **权限管理**: 确保有足够的权限访问ROS话题和硬件
5. **日志模式**: 使用 `--log-only` 参数进行安全测试

## 版本信息

- 版本: 1.0.0
- 作者: AI Assistant
- 更新日期: 2024年
- 兼容性: ROS Noetic, Python 3.6+
