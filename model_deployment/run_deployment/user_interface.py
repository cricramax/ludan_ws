#!/usr/bin/env python
# -*- coding: utf-8 -*-

import rospy
import numpy as np
import threading
import time
import sys
import select
import tty
import os
import datetime
import termios
from typing import Optional, Callable

class KeyboardController:
    """键盘控制器，支持前后左右控制"""
    
    def __init__(self, command_callback: Optional[Callable] = None, log_file: str = None):
        """
        初始化键盘控制器
        
        Args:
            command_callback: 指令回调函数，接收 (forward_back, left_right) 参数
            log_file: 日志文件路径，如果为None则不写入文件
        """
        self.command_callback = command_callback
        self.running = False
        self.control_thread = None
        self.log_file = log_file
        
        # 控制参数
        self.linear_step = 0.1  # 线速度步长
        self.angular_step = 0.1  # 角速度步长
        self.max_linear = 1.0   # 最大线速度
        self.max_angular = 1.0  # 最大角速度
        
        # 当前指令
        self.current_forward_back = 0.0
        self.current_left_right = 0.0
        
        # 保存终端设置
        self.old_settings = None
        
        # 初始化日志文件
        if self.log_file:
            self._init_log_file()
        
        print("键盘控制器已初始化")
        print("控制说明:")
        print("  W/S: 前进/后退")
        print("  A/D: 左转/右转")
        print("  Q: 退出")
        print("  Space: 停止")
    
    def _init_log_file(self):
        """初始化日志文件"""
        try:
            with open(self.log_file, 'w', encoding='utf-8') as f:
                f.write(f"键盘控制日志 - 开始时间: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                f.write("格式: [时间] 前后指令, 左右指令\n")
                f.write("-" * 50 + "\n")
            print(f"键盘控制日志将写入文件: {self.log_file}")
        except Exception as e:
            print(f"初始化日志文件失败: {e}")
            self.log_file = None
    
    def _log_command(self, forward_back: float, left_right: float):
        """记录键盘指令到日志"""
        timestamp = datetime.datetime.now().strftime('%H:%M:%S.%f')[:-3]
        log_msg = f"[{timestamp}] 前后={forward_back:+.2f}, 左右={left_right:+.2f}"
        
        # 输出到控制台
        print(f"\r键盘状态: {log_msg}", end='', flush=True)
        
        # 写入文件
        if self.log_file:
            try:
                with open(self.log_file, 'a', encoding='utf-8') as f:
                    f.write(f"{log_msg}\n")
            except Exception as e:
                print(f"\n写入日志文件失败: {e}")
    
    def _get_key(self) -> str:
        """获取键盘输入"""
        if sys.stdin in select.select([sys.stdin], [], [], 0)[0]:
            return sys.stdin.read(1)
        return ""
    
    def _update_command(self, forward_back: float, left_right: float):
        """更新指令"""
        self.current_forward_back = np.clip(forward_back, -self.max_linear, self.max_linear)
        self.current_left_right = np.clip(left_right, -self.max_angular, self.max_angular)
        
        # 记录指令到日志
        self._log_command(self.current_forward_back, self.current_left_right)
        
        if self.command_callback:
            self.command_callback(self.current_forward_back, self.current_left_right)
    
    def _keyboard_loop(self):
        """键盘输入循环"""
        # 设置终端为非阻塞模式
        self.old_settings = termios.tcgetattr(sys.stdin)
        tty.setraw(sys.stdin.fileno())
        
        try:
            while self.running:
                key = self._get_key()
                
                if key == 'w' or key == 'W':
                    # 前进
                    new_forward = self.current_forward_back + self.linear_step
                    self._update_command(new_forward, self.current_left_right)
                    
                elif key == 's' or key == 'S':
                    # 后退
                    new_forward = self.current_forward_back - self.linear_step
                    self._update_command(new_forward, self.current_left_right)
                    
                elif key == 'a' or key == 'A':
                    # 左转
                    new_left = self.current_left_right - self.angular_step
                    self._update_command(self.current_forward_back, new_left)
                    
                elif key == 'd' or key == 'D':
                    # 右转
                    new_left = self.current_left_right + self.angular_step
                    self._update_command(self.current_forward_back, new_left)
                    
                elif key == ' ':
                    # 停止
                    self._update_command(0.0, 0.0)
                    
                elif key == 'q' or key == 'Q':
                    # 退出
                    print("\n退出键盘控制")
                    self.running = False
                    break
                
                time.sleep(0.05)  # 控制输入频率
                
        finally:
            # 恢复终端设置
            if self.old_settings:
                termios.tcsetattr(sys.stdin, termios.TCSADRAIN, self.old_settings)
    
    def start(self):
        """启动键盘控制"""
        if self.running:
            return
        
        self.running = True
        self.control_thread = threading.Thread(target=self._keyboard_loop)
        self.control_thread.daemon = True
        self.control_thread.start()
        print("键盘控制已启动")
    
    def stop(self):
        """停止键盘控制"""
        self.running = False
        if self.control_thread:
            self.control_thread.join(timeout=1.0)
        print("键盘控制已停止")
    
    def get_current_command(self) -> tuple:
        """获取当前指令"""
        return self.current_forward_back, self.current_left_right

class SimpleUI:
    """简单用户界面"""
    
    def __init__(self, controller_callback: Optional[Callable] = None, log_file: str = None):
        """
        初始化用户界面
        
        Args:
            controller_callback: 控制器回调函数
            log_file: 键盘控制日志文件路径
        """
        self.controller_callback = controller_callback
        self.running = False
        self.keyboard_controller = KeyboardController(self._on_command, log_file)
        
        print("简单用户界面已初始化")
    
    def _on_command(self, forward_back: float, left_right: float):
        """指令回调"""
        if self.controller_callback:
            self.controller_callback(forward_back, left_right)
    
    def start(self):
        """启动用户界面"""
        if self.running:
            return
        
        self.running = True
        self.keyboard_controller.start()
        print("用户界面已启动")
    
    def stop(self):
        """停止用户界面"""
        self.running = False
        self.keyboard_controller.stop()
        print("用户界面已停止")

class CommandInterface:
    """指令接口，提供多种输入方式"""
    
    def __init__(self):
        """初始化指令接口"""
        self.current_command = np.array([0.0, 0.0])
        self.command_lock = threading.Lock()
        self.callbacks = []
    
    def add_callback(self, callback: Callable):
        """添加指令回调"""
        self.callbacks.append(callback)
    
    def set_command(self, forward_back: float, left_right: float):
        """设置指令"""
        with self.command_lock:
            self.current_command = np.array([forward_back, left_right])
            
            # 调用所有回调
            for callback in self.callbacks:
                try:
                    callback(forward_back, left_right)
                except Exception as e:
                    print(f"回调执行失败: {e}")
    
    def get_command(self) -> np.ndarray:
        """获取当前指令"""
        with self.command_lock:
            return self.current_command.copy()
    
    def stop_command(self):
        """停止指令"""
        self.set_command(0.0, 0.0)

class GamepadController:
    """游戏手柄控制器（可选）"""
    
    def __init__(self, command_callback: Optional[Callable] = None):
        """
        初始化游戏手柄控制器
        
        Args:
            command_callback: 指令回调函数
        """
        self.command_callback = command_callback
        self.joystick = None
        
        try:
            import pygame
            pygame.init()
            pygame.joystick.init()
            
            if pygame.joystick.get_count() > 0:
                self.joystick = pygame.joystick.Joystick(0)
                self.joystick.init()
                print(f"游戏手柄已连接: {self.joystick.get_name()}")
            else:
                print("未检测到游戏手柄")
                
        except ImportError:
            print("pygame未安装，无法使用游戏手柄控制")
        except Exception as e:
            print(f"游戏手柄初始化失败: {e}")
    
    def update(self):
        """更新游戏手柄状态"""
        if self.joystick is None:
            return
        
        try:
            import pygame
            pygame.event.pump()
            
            # 获取左摇杆输入 (通常为轴0和轴1)
            left_x = self.joystick.get_axis(0)  # 左右
            left_y = -self.joystick.get_axis(1)  # 前后 (取反)
            
            # 转换为指令
            forward_back = left_y
            left_right = left_x
            
            if self.command_callback:
                self.command_callback(forward_back, left_right)
                
        except Exception as e:
            print(f"游戏手柄更新失败: {e}")

if __name__ == "__main__":
    # 测试代码
    try:
        def test_callback(forward_back, left_right):
            print(f"指令: 前后={forward_back:.2f}, 左右={left_right:.2f}")
        
        ui = SimpleUI(test_callback)
        ui.start()
        
        print("按任意键开始测试，按Q退出")
        
        try:
            while True:
                time.sleep(0.1)
        except KeyboardInterrupt:
            pass
        finally:
            ui.stop()
            
    except Exception as e:
        print(f"测试失败: {e}")
