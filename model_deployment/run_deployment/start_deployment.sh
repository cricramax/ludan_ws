#!/bin/bash
# -*- coding: utf-8 -*-

# 机器人部署系统启动脚本

# 设置工作目录
cd "$(dirname "$0")"

# 激活虚拟环境
echo "激活虚拟环境..."
source ~/virtualenv/py38_torch21/bin/activate

# 检查ROS环境
if [ -z "$ROS_PACKAGE_PATH" ]; then
    echo "错误: ROS环境未设置，请先source ROS环境"
    echo "例如: source /opt/ros/noetic/setup.bash"
    exit 1
fi

# 检查Python依赖
echo "检查Python依赖..."
python3 -c "import rospy, numpy, torch, onnxruntime" 2>/dev/null
if [ $? -ne 0 ]; then
    echo "警告: 部分Python依赖可能缺失"
    echo "请确保在虚拟环境中安装了: rospy, numpy, torch, onnxruntime"
fi

# 检查模型文件
MODEL_PATH="../ludan_model/policy.onnx"
if [ ! -f "$MODEL_PATH" ]; then
    echo "警告: 模型文件不存在: $MODEL_PATH"
    echo "将使用无模型模式运行"
    MODEL_ARGS="--no-model"
else
    echo "找到模型文件: $MODEL_PATH"
    MODEL_ARGS="--model $MODEL_PATH"
fi

# 解析命令行参数
USE_KEYBOARD=true
TEST_MODE=false
USE_TENSORRT=false
LOG_ONLY_MODE=false
USE_SIMPLE=false

while [[ $# -gt 0 ]]; do
    case $1 in
        --no-keyboard)
            USE_KEYBOARD=false
            shift
            ;;
        --test)
            TEST_MODE=true
            shift
            ;;
        --tensorrt)
            USE_TENSORRT=true
            shift
            ;;
        --log-only)
            LOG_ONLY_MODE=true
            shift
            ;;
        --simple)
            USE_SIMPLE=true
            shift
            ;;
        --help)
            echo "用法: $0 [选项]"
            echo "选项:"
            echo "  --no-keyboard    不使用键盘控制"
            echo "  --test          运行测试模式"
            echo "  --tensorrt      使用TensorRT优化"
            echo "  --log-only      仅输出日志，不实际控制机器人"
            echo "  --simple        使用简化版本（不依赖深度学习库）"
            echo "  --help          显示此帮助信息"
            exit 0
            ;;
        *)
            echo "未知选项: $1"
            echo "使用 --help 查看帮助信息"
            exit 1
            ;;
    esac
done

# 构建启动参数
ARGS="$MODEL_ARGS"
if [ "$USE_KEYBOARD" = false ]; then
    ARGS="$ARGS --no-keyboard"
fi
if [ "$TEST_MODE" = true ]; then
    ARGS="$ARGS --test"
fi
if [ "$USE_TENSORRT" = true ]; then
    ARGS="$ARGS --tensorrt"
fi
if [ "$LOG_ONLY_MODE" = true ]; then
    ARGS="$ARGS --log-only"
fi

echo "启动机器人部署系统..."
echo "参数: $ARGS"
echo "提示: 使用 Ctrl+C 退出程序"
echo "============================================================"

# 设置信号处理，确保Ctrl+C能正常退出
trap 'echo -e "\n正在退出..."; exit 0' INT

# 启动系统
python3 main_deployment.py $ARGS
