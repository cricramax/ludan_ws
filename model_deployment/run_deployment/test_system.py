#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
机器人部署系统测试脚本
用于验证各个组件的功能
"""

import os
import sys
import numpy as np
import time

# 添加模块路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'ludan_model'))

def test_model_loader():
    """测试模型加载器"""
    print("=== 测试模型加载器 ===")
    
    try:
        from ludan_model.model_loader import ModelLoader, PolicyModel
        
        # 测试ONNX模型
        onnx_path = "../ludan_model/policy.onnx"
        if os.path.exists(onnx_path):
            print(f"测试ONNX模型: {onnx_path}")
            loader = ModelLoader(onnx_path, "onnx")
            print(f"输入形状: {loader.get_input_shape()}")
            print(f"输出形状: {loader.get_output_shape()}")
            
            # 测试预测
            test_input = np.random.randn(1, 28).astype(np.float32)
            output = loader.predict(test_input)
            print(f"预测输出形状: {output.shape}")
            
            # 测试PolicyModel
            policy = PolicyModel(onnx_path)
            test_obs = np.random.randn(28)
            test_cmd = np.array([0.5, 0.0])
            action = policy.get_action(test_obs, test_cmd)
            print(f"策略输出: {action}")
            
        else:
            print(f"ONNX模型文件不存在: {onnx_path}")
        
        # 测试PyTorch模型
        pt_path = "../ludan_model/policy.pt"
        if os.path.exists(pt_path):
            print(f"测试PyTorch模型: {pt_path}")
            loader = ModelLoader(pt_path, "pytorch")
            print("PyTorch模型加载成功")
        else:
            print(f"PyTorch模型文件不存在: {pt_path}")
            
    except Exception as e:
        print(f"模型加载器测试失败: {e}")

def test_state_processor():
    """测试状态处理器"""
    print("\n=== 测试状态处理器 ===")
    
    try:
        from state_reader import StateProcessor
        
        processor = StateProcessor()
        
        # 测试状态处理
        test_state = np.random.randn(42)
        processed_state = processor.process_state(test_state)
        
        if processed_state is not None:
            print(f"状态处理成功: {len(processed_state)} 维")
            print(f"状态历史长度: {len(processor.get_state_history())}")
        else:
            print("状态处理失败")
            
    except Exception as e:
        print(f"状态处理器测试失败: {e}")

def test_command_interface():
    """测试指令接口"""
    print("\n=== 测试指令接口 ===")
    
    try:
        from robot_controller import CommandProcessor
        
        processor = CommandProcessor()
        
        # 测试指令处理
        processor.add_command("forward", 0.5)
        processor.add_command("right", 0.3)
        
        command = processor.process_commands()
        print(f"处理后的指令: {command}")
        
    except Exception as e:
        print(f"指令接口测试失败: {e}")

def test_robot_controller():
    """测试机器人控制器"""
    print("\n=== 测试机器人控制器 ===")
    
    try:
        from robot_controller import RobotController
        
        controller = RobotController()
        
        # 测试指令转换
        test_command = np.array([0.5, 0.3])
        linear_vel, angular_vel = controller.command_to_velocity(test_command)
        print(f"速度指令: 线速度={linear_vel:.3f}, 角速度={angular_vel:.3f}")
        
        # 测试关节指令生成
        left_commands, right_commands = controller.velocity_to_joint_commands(linear_vel, angular_vel)
        print(f"左腿指令: {left_commands}")
        print(f"右腿指令: {right_commands}")
        
    except Exception as e:
        print(f"机器人控制器测试失败: {e}")

def test_user_interface():
    """测试用户界面"""
    print("\n=== 测试用户界面 ===")
    
    try:
        from user_interface import CommandInterface
        
        interface = CommandInterface()
        
        # 测试指令设置
        interface.set_command(0.5, 0.0)
        command = interface.get_command()
        print(f"当前指令: {command}")
        
        # 测试停止
        interface.stop_command()
        command = interface.get_command()
        print(f"停止后指令: {command}")
        
    except Exception as e:
        print(f"用户界面测试失败: {e}")

def test_integration():
    """测试系统集成"""
    print("\n=== 测试系统集成 ===")
    
    try:
        # 模拟完整的数据流
        from state_reader import StateProcessor
        from robot_controller import RobotController
        from user_interface import CommandInterface
        
        processor = StateProcessor()
        controller = RobotController()
        interface = CommandInterface()
        
        # 模拟状态数据
        test_state = np.random.randn(42)
        processed_state = processor.process_state(test_state)
        
        # 模拟用户指令
        interface.set_command(0.3, 0.2)
        user_command = interface.get_command()
        
        # 模拟控制流程
        linear_vel, angular_vel = controller.command_to_velocity(user_command)
        left_commands, right_commands = controller.velocity_to_joint_commands(linear_vel, angular_vel)
        
        print(f"集成测试成功:")
        print(f"  状态维度: {len(processed_state)}")
        print(f"  用户指令: {user_command}")
        print(f"  速度指令: 线速度={linear_vel:.3f}, 角速度={angular_vel:.3f}")
        print(f"  关节指令: 左腿={len(left_commands)}, 右腿={len(right_commands)}")
        
    except Exception as e:
        print(f"系统集成测试失败: {e}")

def main():
    """主测试函数"""
    print("机器人部署系统组件测试")
    print("=" * 50)
    
    # 检查ROS环境
    try:
        import rospy
        print("ROS环境: 可用")
    except ImportError:
        print("ROS环境: 不可用 (某些测试可能失败)")
    
    # 运行各项测试
    test_model_loader()
    test_state_processor()
    test_command_interface()
    test_robot_controller()
    test_user_interface()
    test_integration()
    
    print("\n" + "=" * 50)
    print("测试完成!")

if __name__ == "__main__":
    main()
