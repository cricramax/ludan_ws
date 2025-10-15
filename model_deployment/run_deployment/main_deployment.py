#!/usr/bin/env python
# -*- coding: utf-8 -*-

import rospy
import numpy as np
import os
import sys
import threading
import time
import argparse
import datetime
from typing import Optional

# 添加模块路径
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
ludan_model_dir = os.path.join(parent_dir, 'ludan_model')

sys.path.append(current_dir)
sys.path.append(parent_dir)
sys.path.append(ludan_model_dir)

# 导入自定义模块
from state_reader import RobotStateReader, StateProcessor
from robot_controller import RobotController, CommandProcessor
from user_interface import SimpleUI, CommandInterface

# 尝试导入增强模型加载器（支持TensorRT）
try:
    from ludan_model.enhanced_model_loader import EnhancedPolicyModel
    ENHANCED_MODEL_AVAILABLE = True
except ImportError:
    from ludan_model.model_loader import PolicyModel as EnhancedPolicyModel
    ENHANCED_MODEL_AVAILABLE = False

class RobotDeploymentSystem:
    """机器人部署系统主类"""
    
    def __init__(self, model_path: str, use_model: bool = True, use_keyboard: bool = True, 
                 use_tensorrt: bool = False, log_only_mode: bool = False):
        """
        初始化部署系统
        
        Args:
            model_path: 模型文件路径
            use_model: 是否使用模型预测
            use_keyboard: 是否使用键盘控制
            use_tensorrt: 是否使用TensorRT优化
            log_only_mode: 是否仅输出日志而不实际控制机器人
        """
        self.model_path = model_path
        self.use_model = use_model
        self.use_keyboard = use_keyboard
        self.use_tensorrt = use_tensorrt
        self.log_only_mode = log_only_mode
        
        # 初始化ROS节点
        rospy.init_node('robot_deployment_system', anonymous=True)
        
        # 初始化组件
        self.state_reader = RobotStateReader()
        self.state_processor = StateProcessor()
        self.robot_controller = RobotController(log_only_mode=self.log_only_mode)
        self.command_interface = CommandInterface()
        
        # 模型相关
        self.policy_model = None
        if self.use_model and os.path.exists(model_path):
            try:
                if ENHANCED_MODEL_AVAILABLE and self.use_tensorrt:
                    self.policy_model = EnhancedPolicyModel(model_path, use_tensorrt=True)
                    rospy.loginfo(f"TensorRT模型加载成功: {model_path}")
                else:
                    self.policy_model = EnhancedPolicyModel(model_path, use_tensorrt=False)
                    rospy.loginfo(f"模型加载成功: {model_path}")
            except Exception as e:
                rospy.logerr(f"模型加载失败: {e}")
                self.use_model = False
        
        # 用户界面
        self.user_interface = None
        if self.use_keyboard:
            # 创建键盘控制日志文件
            log_file = f"keyboard_control_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
            self.user_interface = SimpleUI(self._on_user_command, log_file)
        
        # 控制线程
        self.control_thread = None
        self.running = False
        
        # 状态监控
        self.last_state_time = 0
        self.state_timeout = 1.0  # 1秒超时
        
        rospy.loginfo("机器人部署系统初始化完成")
    
    def _on_user_command(self, forward_back: float, left_right: float):
        """用户指令回调"""
        self.command_interface.set_command(forward_back, left_right)
        rospy.loginfo(f"用户指令: 前后={forward_back:.2f}, 左右={left_right:.2f}")
    
    def _control_loop(self):
        """主控制循环"""
        rate = rospy.Rate(50)  # 50Hz
        
        while self.running and not rospy.is_shutdown():
            try:
                # 获取当前机器人状态
                current_state = self.state_reader.get_current_state()
                
                if current_state is not None:
                    self.last_state_time = time.time()
                    
                    # 处理状态数据
                    processed_state = self.state_processor.process_state(current_state)
                    
                    if processed_state is not None:
                        # 获取用户指令
                        user_command = self.command_interface.get_command()
                        
                        # 模型预测
                        if self.use_model and self.policy_model is not None:
                            try:
                                # 使用模型预测动作（不传递用户命令，因为模型期望102维输入）
                                model_action = self.policy_model.get_action(processed_state)
                                
                                # 将模型输出转换为控制指令
                                # 这里需要根据具体模型输出格式进行调整
                                if len(model_action) >= 2:
                                    # 假设模型输出前两个值对应线速度和角速度
                                    linear_vel = model_action[0]
                                    angular_vel = model_action[1]
                                else:
                                    # 如果模型输出格式不同，使用用户指令
                                    linear_vel, angular_vel = self.robot_controller.command_to_velocity(user_command)
                            except Exception as e:
                                rospy.logwarn(f"模型预测失败: {e}")
                                linear_vel, angular_vel = self.robot_controller.command_to_velocity(user_command)
                        else:
                            # 直接使用用户指令
                            linear_vel, angular_vel = self.robot_controller.command_to_velocity(user_command)
                        
                        # 转换为关节指令并发布
                        left_commands, right_commands = self.robot_controller.velocity_to_joint_commands(
                            linear_vel, angular_vel
                        )
                        self.robot_controller.publish_joint_commands(
                            left_commands, right_commands, 
                            linear_vel, angular_vel, user_command
                        )
                        
                        # 状态监控 - 详细日志
                        if self.log_only_mode:
                            # 在日志模式下，输出更详细的状态信息
                            rospy.loginfo(f"当前机器人状态维度: {len(processed_state)}")
                            rospy.loginfo(f"状态数据范围: [{processed_state.min():.3f}, {processed_state.max():.3f}]")
                            
                            # 输出关节位置信息
                            joint_positions = self.state_reader.get_joint_positions()
                            if joint_positions is not None:
                                rospy.loginfo("当前关节位置:")
                                for i, name in enumerate(self.state_reader.joint_names):
                                    rospy.loginfo(f"  {name}: {joint_positions[i]:.3f}°")
                        
                        # 控制指令摘要
                        if abs(linear_vel) > 0.01 or abs(angular_vel) > 0.01:
                            rospy.loginfo(f"控制指令摘要: 线速度={linear_vel:.3f}, 角速度={angular_vel:.3f}")
                
                else:
                    # 检查状态超时
                    if time.time() - self.last_state_time > self.state_timeout:
                        rospy.logwarn("机器人状态数据超时")
                        self.last_state_time = time.time()
                
                rate.sleep()
                
            except Exception as e:
                rospy.logerr(f"控制循环错误: {e}")
                rate.sleep()
    
    def start(self):
        """启动部署系统"""
        if self.running:
            return
        
        self.running = True
        
        # 等待状态数据准备就绪
        rospy.loginfo("等待机器人状态数据...")
        if not self.state_reader.wait_for_data(timeout=10.0):
            rospy.logerr("等待状态数据超时")
            return False
        
        rospy.loginfo("状态数据准备就绪")
        
        # 启动用户界面
        if self.user_interface:
            self.user_interface.start()
            rospy.loginfo("用户界面已启动")
        
        # 启动控制线程
        self.control_thread = threading.Thread(target=self._control_loop)
        self.control_thread.daemon = True
        self.control_thread.start()
        
        rospy.loginfo("机器人部署系统已启动")
        return True
    
    def stop(self):
        """停止部署系统"""
        self.running = False
        
        # 停止用户界面
        if self.user_interface:
            self.user_interface.stop()
        
        # 等待控制线程结束
        if self.control_thread:
            self.control_thread.join(timeout=2.0)
        
        # 发送停止指令
        self.command_interface.stop_command()
        
        rospy.loginfo("机器人部署系统已停止")
    
    def get_status(self) -> dict:
        """获取系统状态"""
        status = {
            'running': self.running,
            'model_loaded': self.policy_model is not None,
            'state_ready': self.state_reader.is_data_ready(),
            'user_interface_active': self.user_interface is not None,
            'current_command': self.command_interface.get_command().tolist(),
            'state_info': self.state_reader.get_state_info()
        }
        
        if self.state_reader.is_data_ready():
            current_state = self.state_reader.get_current_state()
            if current_state is not None:
                status['state_dimension'] = len(current_state)
                status['joint_positions'] = self.state_reader.get_joint_positions().tolist()
        
        return status

def main():
    """主函数"""
    parser = argparse.ArgumentParser(description='机器人部署系统')
    parser.add_argument('--model', type=str, 
                       default='../ludan_model/policy.onnx',
                       help='模型文件路径')
    parser.add_argument('--no-model', action='store_true',
                       help='不使用模型预测')
    parser.add_argument('--no-keyboard', action='store_true',
                       help='不使用键盘控制')
    parser.add_argument('--test', action='store_true',
                       help='运行测试模式')
    parser.add_argument('--tensorrt', action='store_true',
                       help='使用TensorRT优化')
    parser.add_argument('--log-only', action='store_true',
                       help='仅输出日志，不实际控制机器人')
    
    args = parser.parse_args()
    
    # 检查模型文件
    model_path = os.path.abspath(args.model)
    if not os.path.exists(model_path):
        print(f"警告: 模型文件不存在: {model_path}")
        args.no_model = True
    
    try:
        # 创建部署系统
        deployment = RobotDeploymentSystem(
            model_path=model_path,
            use_model=not args.no_model,
            use_keyboard=not args.no_keyboard,
            use_tensorrt=args.tensorrt,
            log_only_mode=args.log_only
        )
        
        if args.test:
            # 测试模式
            print("运行测试模式...")
            status = deployment.get_status()
            print(f"系统状态: {status}")
            
            if deployment.start():
                print("测试运行中，按Ctrl+C停止...")
                try:
                    while not rospy.is_shutdown():
                        time.sleep(1.0)
                        status = deployment.get_status()
                        print(f"当前状态: 运行={status['running']}, "
                              f"指令={status['current_command']}")
                except KeyboardInterrupt:
                    pass
                finally:
                    deployment.stop()
            else:
                print("系统启动失败")
        else:
            # 正常模式
            if deployment.start():
                print("系统运行中，按Ctrl+C停止...")
                try:
                    rospy.spin()
                except KeyboardInterrupt:
                    pass
                finally:
                    deployment.stop()
            else:
                print("系统启动失败")
                
    except rospy.ROSInterruptException:
        print("ROS节点被中断")
    except Exception as e:
        print(f"系统运行失败: {e}")

if __name__ == "__main__":
    main()
