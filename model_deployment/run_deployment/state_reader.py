#!/usr/bin/env python
# -*- coding: utf-8 -*-

import rospy
import numpy as np
import threading
from sensor_msgs.msg import JointState
from typing import Dict, List, Optional, Tuple

class RobotStateReader:
    """机器人状态读取器，基于ROS JointState消息"""
    
    def __init__(self):
        """初始化状态读取器"""
        self.left_leg_state = None
        self.right_leg_state = None
        self.state_lock = threading.Lock()
        
        # 关节名称映射
        self.joint_names = [
            'leg_l1_joint', 'leg_l2_joint', 'leg_l3_joint', 'leg_l4_joint',
            'leg_l5_joint', 'leg_l6_joint', 'leg_l7_joint',
            'leg_r1_joint', 'leg_r2_joint', 'leg_r3_joint', 'leg_r4_joint',
            'leg_r5_joint', 'leg_r6_joint', 'leg_r7_joint'
        ]
        
        # 初始化ROS节点
        if not rospy.get_node_uri():
            rospy.init_node('robot_state_reader', anonymous=True)
        
        # 订阅关节状态话题
        self.left_leg_sub = rospy.Subscriber(
            '/mcu_leftleg/joint_states', 
            JointState, 
            self.left_leg_callback
        )
        self.right_leg_sub = rospy.Subscriber(
            '/mcu_rightleg/joint_states', 
            JointState, 
            self.right_leg_callback
        )
        
        rospy.loginfo("机器人状态读取器已启动")
        rospy.loginfo("监听话题: /mcu_leftleg/joint_states, /mcu_rightleg/joint_states")
    
    def left_leg_callback(self, msg: JointState):
        """左腿关节状态回调"""
        with self.state_lock:
            # 从消息中提取左腿数据（前7个关节）
            self.left_leg_state = {
                'positions': list(msg.position[:7]),  # 前7个关节是左腿
                'velocities': list(msg.velocity[:7]),
                'efforts': list(msg.effort[:7]),
                'timestamp': msg.header.stamp.to_sec()
            }
            # 同时设置右腿数据（从同一个消息中提取）
            self.right_leg_state = {
                'positions': list(msg.position[7:]),  # 后7个关节是右腿
                'velocities': list(msg.velocity[7:]),
                'efforts': list(msg.effort[7:]),
                'timestamp': msg.header.stamp.to_sec()
            }
    
    def right_leg_callback(self, msg: JointState):
        """右腿关节状态回调"""
        with self.state_lock:
            # 从消息中提取右腿数据（后7个关节）
            self.right_leg_state = {
                'positions': list(msg.position[7:]),  # 后7个关节是右腿
                'velocities': list(msg.velocity[7:]),
                'efforts': list(msg.effort[7:]),
                'timestamp': msg.header.stamp.to_sec()
            }
            # 同时设置左腿数据（从同一个消息中提取）
            self.left_leg_state = {
                'positions': list(msg.position[:7]),  # 前7个关节是左腿
                'velocities': list(msg.velocity[:7]),
                'efforts': list(msg.effort[:7]),
                'timestamp': msg.header.stamp.to_sec()
            }
    
    def get_current_state(self) -> Optional[np.ndarray]:
        """
        获取当前机器人状态
        
        Returns:
            包含位置、速度、力矩的状态向量，如果数据不完整则返回None
        """
        with self.state_lock:
            if self.left_leg_state is None or self.right_leg_state is None:
                return None
            
            # 合并左右腿状态
            state = []
            
            # 添加位置信息
            state.extend(self.left_leg_state['positions'])
            state.extend(self.right_leg_state['positions'])
            
            # 添加速度信息
            state.extend(self.left_leg_state['velocities'])
            state.extend(self.right_leg_state['velocities'])
            
            # 添加力矩信息
            state.extend(self.left_leg_state['efforts'])
            state.extend(self.right_leg_state['efforts'])
            
            return np.array(state, dtype=np.float32)
    
    def get_joint_positions(self) -> Optional[np.ndarray]:
        """获取关节位置"""
        with self.state_lock:
            if self.left_leg_state is None or self.right_leg_state is None:
                return None
            
            positions = []
            positions.extend(self.left_leg_state['positions'])
            positions.extend(self.right_leg_state['positions'])
            
            return np.array(positions, dtype=np.float32)
    
    def get_joint_velocities(self) -> Optional[np.ndarray]:
        """获取关节速度"""
        with self.state_lock:
            if self.left_leg_state is None or self.right_leg_state is None:
                return None
            
            velocities = []
            velocities.extend(self.left_leg_state['velocities'])
            velocities.extend(self.right_leg_state['velocities'])
            
            return np.array(velocities, dtype=np.float32)
    
    def get_joint_efforts(self) -> Optional[np.ndarray]:
        """获取关节力矩"""
        with self.state_lock:
            if self.left_leg_state is None or self.right_leg_state is None:
                return None
            
            efforts = []
            efforts.extend(self.left_leg_state['efforts'])
            efforts.extend(self.right_leg_state['efforts'])
            
            return np.array(efforts, dtype=np.float32)
    
    def is_data_ready(self) -> bool:
        """检查数据是否准备就绪"""
        with self.state_lock:
            return self.left_leg_state is not None and self.right_leg_state is not None
    
    def get_state_info(self) -> Dict[str, any]:
        """获取状态信息"""
        with self.state_lock:
            info = {
                'left_leg_ready': self.left_leg_state is not None,
                'right_leg_ready': self.right_leg_state is not None,
                'total_joints': len(self.joint_names)
            }
            
            if self.left_leg_state is not None:
                info['left_leg_timestamp'] = self.left_leg_state['timestamp']
            if self.right_leg_state is not None:
                info['right_leg_timestamp'] = self.right_leg_state['timestamp']
            
            return info
    
    def wait_for_data(self, timeout: float = 5.0) -> bool:
        """
        等待数据准备就绪
        
        Args:
            timeout: 超时时间（秒）
            
        Returns:
            是否在超时前获得数据
        """
        start_time = rospy.Time.now().to_sec()
        
        while not rospy.is_shutdown():
            if self.is_data_ready():
                return True
            
            if rospy.Time.now().to_sec() - start_time > timeout:
                return False
            
            rospy.sleep(0.1)
        
        return False

class StateProcessor:
    """状态处理器，用于预处理机器人状态数据"""
    
    def __init__(self, state_dim: int = 42):
        """
        初始化状态处理器
        
        Args:
            state_dim: 状态维度 (14个关节 * 3种数据 = 42，包含位置、速度、力矩)
        """
        self.state_dim = state_dim
        self.state_history = []
        self.max_history_length = 10
        self.target_input_dim = 102  # 模型期望的输入维度
    
    def process_state(self, raw_state: np.ndarray) -> np.ndarray:
        """
        处理原始状态数据，扩展为模型期望的输入维度
        
        Args:
            raw_state: 原始状态向量
            
        Returns:
            处理后的状态向量，扩展到目标维度
        """
        if raw_state is None:
            return None
        
        # 确保状态维度正确
        if len(raw_state) != self.state_dim:
            rospy.logwarn(f"状态维度不匹配: 期望 {self.state_dim}, 实际 {len(raw_state)}")
            return None
        
        # 添加到历史记录
        self.state_history.append(raw_state.copy())
        if len(self.state_history) > self.max_history_length:
            self.state_history.pop(0)
        
        # 扩展状态向量以满足模型输入要求
        extended_state = self._extend_state_for_model(raw_state)
        
        return extended_state
    
    def _extend_state_for_model(self, current_state: np.ndarray) -> np.ndarray:
        """
        扩展状态向量以满足模型输入要求
        
        Args:
            current_state: 当前状态向量
            
        Returns:
            扩展后的状态向量
        """
        # 计算需要的历史状态数量
        states_needed = self.target_input_dim // self.state_dim
        
        # 准备状态向量
        state_vector = []
        
        # 添加历史状态（如果可用）
        for i in range(states_needed):
            if i < len(self.state_history):
                # 使用历史状态
                state_vector.extend(self.state_history[-(i+1)])
            else:
                # 如果历史状态不足，用当前状态填充
                state_vector.extend(current_state)
        
        # 确保向量长度正确 - 精确截断到目标维度
        state_vector = state_vector[:self.target_input_dim]
        
        # 如果还不够，用零填充
        while len(state_vector) < self.target_input_dim:
            state_vector.append(0.0)
        
        # 最终确保长度精确匹配
        if len(state_vector) > self.target_input_dim:
            state_vector = state_vector[:self.target_input_dim]
        
        return np.array(state_vector, dtype=np.float32)
    
    def get_state_history(self) -> List[np.ndarray]:
        """获取状态历史"""
        return self.state_history.copy()
    
    def clear_history(self):
        """清空状态历史"""
        self.state_history.clear()

if __name__ == "__main__":
    # 测试代码
    try:
        reader = RobotStateReader()
        
        # 等待数据
        if reader.wait_for_data(timeout=10.0):
            print("数据准备就绪!")
            
            # 获取状态信息
            info = reader.get_state_info()
            print(f"状态信息: {info}")
            
            # 获取当前状态
            state = reader.get_current_state()
            if state is not None:
                print(f"当前状态维度: {len(state)}")
                print(f"关节位置: {reader.get_joint_positions()}")
                print(f"关节速度: {reader.get_joint_velocities()}")
                print(f"关节力矩: {reader.get_joint_efforts()}")
            else:
                print("无法获取状态数据")
        else:
            print("等待数据超时")
            
    except rospy.ROSInterruptException:
        print("ROS节点被中断")
    except Exception as e:
        print(f"测试失败: {e}")
