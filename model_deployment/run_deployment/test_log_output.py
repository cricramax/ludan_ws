#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
日志输出模式测试脚本
用于验证机器人控制指令的日志输出功能
"""

import os
import sys
import numpy as np
import time
import rospy

# 添加模块路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'ludan_model'))

def test_log_output_mode():
    """测试日志输出模式"""
    print("=== 测试日志输出模式 ===")
    
    try:
        from state_reader import RobotStateReader, StateProcessor
        from robot_controller import RobotController
        from user_interface import CommandInterface
        
        # 初始化ROS节点
        rospy.init_node('log_output_test', anonymous=True)
        
        # 创建组件
        state_reader = RobotStateReader()
        state_processor = StateProcessor()
        controller = RobotController(log_only_mode=True)  # 启用日志模式
        command_interface = CommandInterface()
        
        print("组件初始化完成")
        
        # 等待状态数据
        print("等待机器人状态数据...")
        if not state_reader.wait_for_data(timeout=5.0):
            print("警告: 未获取到状态数据，使用模拟数据")
            # 使用模拟数据
            mock_state = np.random.randn(42) * 10  # 模拟42维状态
            processed_state = state_processor.process_state(mock_state)
        else:
            print("获取到真实状态数据")
            current_state = state_reader.get_current_state()
            processed_state = state_processor.process_state(current_state)
        
        # 测试不同的用户指令
        test_commands = [
            np.array([0.0, 0.0]),    # 停止
            np.array([0.5, 0.0]),    # 前进
            np.array([-0.3, 0.0]),  # 后退
            np.array([0.0, 0.4]),    # 右转
            np.array([0.0, -0.3]),  # 左转
            np.array([0.2, 0.1]),   # 前进+右转
        ]
        
        command_names = ["停止", "前进", "后退", "右转", "左转", "前进+右转"]
        
        print("\n开始测试控制指令日志输出...")
        print("=" * 80)
        
        for i, (command, name) in enumerate(zip(test_commands, command_names)):
            print(f"\n测试 {i+1}: {name}")
            print("-" * 40)
            
            # 设置用户指令
            command_interface.set_command(command[0], command[1])
            
            # 获取控制指令
            linear_vel, angular_vel = controller.command_to_velocity(command)
            
            # 生成关节指令
            left_commands, right_commands = controller.velocity_to_joint_commands(
                linear_vel, angular_vel
            )
            
            # 输出详细日志
            controller.publish_joint_commands(
                left_commands, right_commands,
                linear_vel, angular_vel, command
            )
            
            # 等待一下
            time.sleep(1.0)
        
        print("\n" + "=" * 80)
        print("日志输出测试完成!")
        
        # 测试状态监控
        print("\n=== 测试状态监控日志 ===")
        if processed_state is not None:
            print(f"状态维度: {len(processed_state)}")
            print(f"状态范围: [{processed_state.min():.3f}, {processed_state.max():.3f}]")
            
            # 输出关节位置
            joint_positions = state_reader.get_joint_positions()
            if joint_positions is not None:
                print("当前关节位置:")
                for i, name in enumerate(state_reader.joint_names):
                    print(f"  {name}: {joint_positions[i]:.3f}°")
        
        return True
        
    except Exception as e:
        print(f"测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_continuous_logging():
    """测试连续日志输出"""
    print("\n=== 测试连续日志输出 ===")
    
    try:
        from robot_controller import RobotController
        from user_interface import CommandInterface
        
        controller = RobotController(log_only_mode=True)
        command_interface = CommandInterface()
        
        print("开始连续日志输出测试 (10秒)...")
        print("模拟用户输入不同的控制指令...")
        
        start_time = time.time()
        test_duration = 10.0
        
        while time.time() - start_time < test_duration:
            # 生成随机指令
            forward_back = np.random.uniform(-0.5, 0.5)
            left_right = np.random.uniform(-0.3, 0.3)
            
            command = np.array([forward_back, left_right])
            command_interface.set_command(forward_back, left_right)
            
            # 生成控制指令
            linear_vel, angular_vel = controller.command_to_velocity(command)
            left_commands, right_commands = controller.velocity_to_joint_commands(
                linear_vel, angular_vel
            )
            
            # 输出日志
            controller.publish_joint_commands(
                left_commands, right_commands,
                linear_vel, angular_vel, command
            )
            
            time.sleep(0.5)  # 每0.5秒输出一次
        
        print("连续日志输出测试完成!")
        return True
        
    except Exception as e:
        print(f"连续日志测试失败: {e}")
        return False

def main():
    """主测试函数"""
    print("机器人控制指令日志输出测试")
    print("=" * 60)
    
    # 检查ROS环境
    try:
        import rospy
        print("ROS环境: 可用")
    except ImportError:
        print("ROS环境: 不可用")
        return False
    
    # 运行测试
    success1 = test_log_output_mode()
    success2 = test_continuous_logging()
    
    print("\n" + "=" * 60)
    if success1 and success2:
        print("✅ 所有测试通过!")
        print("\n使用方法:")
        print("1. 仅日志模式: ./start_deployment.sh --log-only")
        print("2. 日志+键盘控制: ./start_deployment.sh --log-only")
        print("3. 直接运行: python3 main_deployment.py --log-only")
    else:
        print("❌ 部分测试失败")
    
    return success1 and success2

if __name__ == "__main__":
    try:
        success = main()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n测试被用户中断")
        sys.exit(1)
    except Exception as e:
        print(f"测试运行失败: {e}")
        sys.exit(1)
