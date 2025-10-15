#!/usr/bin/env python
# -*- coding: utf-8 -*-

import rospy
import numpy as np
import threading
import time
from sensor_msgs.msg import JointState
from std_msgs.msg import Float64MultiArray
from typing import Dict, List, Optional, Tuple, Callable

class RobotController:
    """机器人控制器，处理用户输入和模型输出"""
    
    def __init__(self, log_only_mode: bool = False):
        """
        初始化机器人控制器
        
        Args:
            log_only_mode: 是否仅输出日志而不实际控制机器人
        """
        self.log_only_mode = log_only_mode
        # 关节名称
        self.joint_names = [
            'leg_l1_joint', 'leg_l2_joint', 'leg_l3_joint', 'leg_l4_joint',
            'leg_l5_joint', 'leg_l6_joint', 'leg_l7_joint',
            'leg_r1_joint', 'leg_r2_joint', 'leg_r3_joint', 'leg_r4_joint',
            'leg_r5_joint', 'leg_r6_joint', 'leg_r7_joint'
        ]
        
        # 用户指令
        self.user_command = np.array([0.0, 0.0])  # [前进/后退, 左转/右转]
        self.command_lock = threading.Lock()
        
        # 控制参数
        self.max_linear_velocity = 1.0  # 最大线速度
        self.max_angular_velocity = 1.0  # 最大角速度
        self.command_scale = 0.5  # 指令缩放因子
        
        # 初始化ROS节点
        if not rospy.get_node_uri():
            rospy.init_node('robot_controller', anonymous=True)
        
        if self.log_only_mode:
            rospy.loginfo("机器人控制器已启动 - 仅日志模式")
        else:
            # 发布器 - 发布关节控制指令
            self.left_leg_pub = rospy.Publisher(
                '/mcu_leftleg/joint_states_cmd', 
                JointState, 
                queue_size=1
            )
            self.right_leg_pub = rospy.Publisher(
                '/mcu_rightleg/joint_states_cmd', 
                JointState, 
                queue_size=1
            )
            
            # 备用发布器 - 如果上述话题不存在
            self.joint_cmd_pub = rospy.Publisher(
                '/joint_commands', 
                Float64MultiArray, 
                queue_size=1
            )
            
            rospy.loginfo("机器人控制器已启动 - 实际控制模式")
    
    def set_user_command(self, forward_back: float, left_right: float):
        """
        设置用户指令
        
        Args:
            forward_back: 前后指令 (-1.0 到 1.0，负值表示后退)
            left_right: 左右指令 (-1.0 到 1.0，负值表示左转)
        """
        with self.command_lock:
            # 限制指令范围
            forward_back = np.clip(forward_back, -1.0, 1.0)
            left_right = np.clip(left_right, -1.0, 1.0)
            
            self.user_command = np.array([forward_back, left_right])
            rospy.loginfo(f"用户指令更新: 前后={forward_back:.2f}, 左右={left_right:.2f}")
    
    def get_user_command(self) -> np.ndarray:
        """获取当前用户指令"""
        with self.command_lock:
            return self.user_command.copy()
    
    def command_to_velocity(self, command: np.ndarray) -> Tuple[float, float]:
        """
        将用户指令转换为速度指令
        
        Args:
            command: 用户指令 [前后, 左右]
            
        Returns:
            (线速度, 角速度)
        """
        forward_back, left_right = command
        
        # 计算线速度和角速度
        linear_velocity = forward_back * self.max_linear_velocity * self.command_scale
        angular_velocity = left_right * self.max_angular_velocity * self.command_scale
        
        return linear_velocity, angular_velocity
    
    def velocity_to_joint_commands(self, linear_vel: float, angular_vel: float) -> Tuple[np.ndarray, np.ndarray]:
        """
        将速度指令转换为关节指令
        
        Args:
            linear_vel: 线速度
            angular_vel: 角速度
            
        Returns:
            (左腿关节指令, 右腿关节指令)
        """
        # 这里需要根据具体的机器人运动学模型来实现
        # 目前使用简化的步态生成
        
        # 基础关节角度
        base_left = np.array([-12.5, -12.5, 12.5, -12.5, -12.5, 12.5, -12.5])
        base_right = np.array([12.5, 12.5, -12.5, 12.5, 12.5, -12.5, 12.5])
        
        # 根据速度调整关节角度
        # 前进时调整髋关节和膝关节
        if abs(linear_vel) > 0.1:
            # 前进步态
            step_phase = time.time() * 2.0  # 步态相位
            step_amplitude = min(abs(linear_vel), 0.5)  # 步幅
            
            # 左腿步态
            left_step = np.sin(step_phase) * step_amplitude * 5.0
            left_commands = base_left.copy()
            left_commands[1] += left_step  # 髋关节
            left_commands[3] += left_step * 0.5  # 膝关节
            
            # 右腿步态 (相位相反)
            right_step = np.sin(step_phase + np.pi) * step_amplitude * 5.0
            right_commands = base_right.copy()
            right_commands[1] += right_step
            right_commands[3] += right_step * 0.5
        else:
            # 静止状态
            left_commands = base_left.copy()
            right_commands = base_right.copy()
        
        # 转向调整
        if abs(angular_vel) > 0.1:
            turn_amplitude = min(abs(angular_vel), 0.3)
            turn_direction = np.sign(angular_vel)
            
            # 转向时调整踝关节
            left_commands[6] += turn_direction * turn_amplitude * 2.0
            right_commands[6] += turn_direction * turn_amplitude * 2.0
        
        return left_commands, right_commands
    
    def publish_joint_commands(self, left_commands: np.ndarray, right_commands: np.ndarray, 
                              linear_vel: float = 0.0, angular_vel: float = 0.0,
                              user_command: np.ndarray = None):
        """
        发布关节控制指令
        
        Args:
            left_commands: 左腿关节指令
            right_commands: 右腿关节指令
            linear_vel: 线速度
            angular_vel: 角速度
            user_command: 用户指令
        """
        # 详细的日志输出
        timestamp = rospy.Time.now().to_sec()
        
        # 输出控制指令摘要
        rospy.loginfo("=" * 60)
        rospy.loginfo(f"[{timestamp:.3f}] 机器人控制指令")
        rospy.loginfo("=" * 60)
        
        # 用户指令
        if user_command is not None:
            rospy.loginfo(f"用户指令: 前后={user_command[0]:.3f}, 左右={user_command[1]:.3f}")
        
        # 速度指令
        rospy.loginfo(f"速度指令: 线速度={linear_vel:.3f} m/s, 角速度={angular_vel:.3f} rad/s")
        
        # 关节指令详情
        rospy.loginfo("左腿关节指令:")
        for i, (name, cmd) in enumerate(zip(self.joint_names[:7], left_commands)):
            rospy.loginfo(f"  {name}: {cmd:.3f}°")
        
        rospy.loginfo("右腿关节指令:")
        for i, (name, cmd) in enumerate(zip(self.joint_names[7:], right_commands)):
            rospy.loginfo(f"  {name}: {cmd:.3f}°")
        
        # 关节指令变化
        if hasattr(self, 'last_left_commands') and hasattr(self, 'last_right_commands'):
            left_diff = left_commands - self.last_left_commands
            right_diff = right_commands - self.last_right_commands
            
            rospy.loginfo("关节指令变化:")
            rospy.loginfo("左腿变化:")
            for i, (name, diff) in enumerate(zip(self.joint_names[:7], left_diff)):
                if abs(diff) > 0.1:  # 只显示变化较大的关节
                    rospy.loginfo(f"  {name}: {diff:+.3f}°")
            
            rospy.loginfo("右腿变化:")
            for i, (name, diff) in enumerate(zip(self.joint_names[7:], right_diff)):
                if abs(diff) > 0.1:  # 只显示变化较大的关节
                    rospy.loginfo(f"  {name}: {diff:+.3f}°")
        
        # 保存当前指令用于下次比较
        self.last_left_commands = left_commands.copy()
        self.last_right_commands = right_commands.copy()
        
        # 如果仅日志模式，不实际发布
        if self.log_only_mode:
            rospy.loginfo("模式: 仅日志输出 (不实际控制机器人)")
            rospy.loginfo("=" * 60)
            return
        
        # 实际发布控制指令
        try:
            # 创建JointState消息
            left_msg = JointState()
            left_msg.header.stamp = rospy.Time.now()
            left_msg.name = self.joint_names[:7]  # 左腿关节
            left_msg.position = left_commands.tolist()
            left_msg.velocity = [0.0] * 7  # 速度设为0，使用位置控制
            left_msg.effort = [0.0] * 7   # 力矩设为0
            
            right_msg = JointState()
            right_msg.header.stamp = rospy.Time.now()
            right_msg.name = self.joint_names[7:]  # 右腿关节
            right_msg.position = right_commands.tolist()
            right_msg.velocity = [0.0] * 7
            right_msg.effort = [0.0] * 7
            
            # 发布消息
            self.left_leg_pub.publish(left_msg)
            self.right_leg_pub.publish(right_msg)
            
            rospy.loginfo("模式: 实际控制 (已发布ROS指令)")
            
        except Exception as e:
            rospy.logerr(f"发布关节指令失败: {e}")
            
            # 备用方案：使用Float64MultiArray
            try:
                all_commands = np.concatenate([left_commands, right_commands])
                cmd_msg = Float64MultiArray()
                cmd_msg.data = all_commands.tolist()
                self.joint_cmd_pub.publish(cmd_msg)
                rospy.loginfo("使用备用发布器发送指令")
            except Exception as e2:
                rospy.logerr(f"备用发布也失败: {e2}")
        
        rospy.loginfo("=" * 60)
    
    def control_loop(self, model_predictor: Optional[Callable] = None, state_reader: Optional[Callable] = None):
        """
        控制循环
        
        Args:
            model_predictor: 模型预测函数
            state_reader: 状态读取函数
        """
        rate = rospy.Rate(50)  # 50Hz控制频率
        
        while not rospy.is_shutdown():
            try:
                # 获取用户指令
                user_cmd = self.get_user_command()
                
                # 获取当前状态
                current_state = None
                if state_reader is not None:
                    current_state = state_reader()
                
                # 模型预测
                if model_predictor is not None and current_state is not None:
                    # 使用模型预测动作
                    model_action = model_predictor(current_state, user_cmd)
                    # 这里可以将模型输出与用户指令结合
                    # 目前直接使用用户指令
                    linear_vel, angular_vel = self.command_to_velocity(user_cmd)
                else:
                    # 直接使用用户指令
                    linear_vel, angular_vel = self.command_to_velocity(user_cmd)
                
                # 转换为关节指令
                left_commands, right_commands = self.velocity_to_joint_commands(linear_vel, angular_vel)
                
                # 发布指令
                self.publish_joint_commands(left_commands, right_commands, 
                                          linear_vel, angular_vel, user_cmd)
                
                rate.sleep()
                
            except Exception as e:
                rospy.logerr(f"控制循环错误: {e}")
                rate.sleep()

class CommandProcessor:
    """指令处理器，处理各种输入格式"""
    
    def __init__(self):
        """初始化指令处理器"""
        self.command_queue = []
        self.queue_lock = threading.Lock()
    
    def add_command(self, command_type: str, value: float):
        """
        添加指令
        
        Args:
            command_type: 指令类型 ("forward", "backward", "left", "right", "stop")
            value: 指令值 (0.0 到 1.0)
        """
        with self.queue_lock:
            self.command_queue.append((command_type, value))
    
    def process_commands(self) -> np.ndarray:
        """
        处理指令队列，返回最终指令
        
        Returns:
            [前后指令, 左右指令]
        """
        with self.queue_lock:
            if not self.command_queue:
                return np.array([0.0, 0.0])
            
            forward_back = 0.0
            left_right = 0.0
            
            for cmd_type, value in self.command_queue:
                if cmd_type == "forward":
                    forward_back += value
                elif cmd_type == "backward":
                    forward_back -= value
                elif cmd_type == "left":
                    left_right -= value
                elif cmd_type == "right":
                    left_right += value
                elif cmd_type == "stop":
                    forward_back = 0.0
                    left_right = 0.0
            
            # 清空队列
            self.command_queue.clear()
            
            # 限制范围
            forward_back = np.clip(forward_back, -1.0, 1.0)
            left_right = np.clip(left_right, -1.0, 1.0)
            
            return np.array([forward_back, left_right])

if __name__ == "__main__":
    # 测试代码
    try:
        controller = RobotController()
        
        # 测试指令设置
        controller.set_user_command(0.5, 0.0)  # 前进
        rospy.sleep(1.0)
        
        controller.set_user_command(0.0, 0.3)  # 右转
        rospy.sleep(1.0)
        
        controller.set_user_command(0.0, 0.0)  # 停止
        
        rospy.loginfo("控制器测试完成")
        
    except rospy.ROSInterruptException:
        print("ROS节点被中断")
    except Exception as e:
        print(f"测试失败: {e}")
