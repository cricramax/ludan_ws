#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import numpy as np
import torch
import onnxruntime as ort
from typing import Union, Optional, Dict, Any

class ModelLoader:
    """模型加载器，支持ONNX和PyTorch模型"""
    
    def __init__(self, model_path: str, model_type: str = "auto"):
        """
        初始化模型加载器
        
        Args:
            model_path: 模型文件路径
            model_type: 模型类型 ("onnx", "pytorch", "auto")
        """
        self.model_path = model_path
        self.model_type = model_type
        self.model = None
        self.session = None
        
        if not os.path.exists(model_path):
            raise FileNotFoundError(f"模型文件不存在: {model_path}")
        
        self._load_model()
    
    def _load_model(self):
        """加载模型"""
        if self.model_type == "auto":
            # 自动检测模型类型
            if self.model_path.endswith('.onnx'):
                self._load_onnx_model()
            elif self.model_path.endswith('.pt') or self.model_path.endswith('.pth'):
                self._load_pytorch_model()
            else:
                raise ValueError(f"不支持的模型文件格式: {self.model_path}")
        elif self.model_type == "onnx":
            self._load_onnx_model()
        elif self.model_type == "pytorch":
            self._load_pytorch_model()
        else:
            raise ValueError(f"不支持的模型类型: {self.model_type}")
    
    def _load_onnx_model(self):
        """加载ONNX模型"""
        try:
            self.session = ort.InferenceSession(self.model_path)
            print(f"成功加载ONNX模型: {self.model_path}")
        except Exception as e:
            raise RuntimeError(f"加载ONNX模型失败: {e}")
    
    def _load_pytorch_model(self):
        """加载PyTorch模型"""
        try:
            self.model = torch.load(self.model_path, map_location='cpu')
            if isinstance(self.model, dict):
                # 如果保存的是state_dict，需要模型结构
                print("警告: 检测到state_dict格式，需要模型结构定义")
            self.model.eval()
            print(f"成功加载PyTorch模型: {self.model_path}")
        except Exception as e:
            raise RuntimeError(f"加载PyTorch模型失败: {e}")
    
    def predict(self, input_data: np.ndarray) -> np.ndarray:
        """
        模型预测
        
        Args:
            input_data: 输入数据 (numpy array)
            
        Returns:
            预测结果 (numpy array)
        """
        if self.session is not None:
            # ONNX模型推理
            input_name = self.session.get_inputs()[0].name
            output = self.session.run(None, {input_name: input_data})
            return output[0]
        elif self.model is not None:
            # PyTorch模型推理
            with torch.no_grad():
                input_tensor = torch.from_numpy(input_data).float()
                output = self.model(input_tensor)
                return output.numpy()
        else:
            raise RuntimeError("模型未正确加载")
    
    def get_input_shape(self) -> tuple:
        """获取模型输入形状"""
        if self.session is not None:
            return self.session.get_inputs()[0].shape
        elif self.model is not None:
            # 对于PyTorch模型，需要特殊处理
            return None  # 需要根据具体模型结构确定
        else:
            raise RuntimeError("模型未正确加载")
    
    def get_output_shape(self) -> tuple:
        """获取模型输出形状"""
        if self.session is not None:
            return self.session.get_outputs()[0].shape
        elif self.model is not None:
            return None  # 需要根据具体模型结构确定
        else:
            raise RuntimeError("模型未正确加载")

class PolicyModel:
    """策略模型包装器，专门用于机器人控制"""
    
    def __init__(self, model_path: str, model_type: str = "auto"):
        """
        初始化策略模型
        
        Args:
            model_path: 模型文件路径
            model_type: 模型类型
        """
        self.loader = ModelLoader(model_path, model_type)
        self.input_shape = self.loader.get_input_shape()
        self.output_shape = self.loader.get_output_shape()
        
        print(f"模型输入形状: {self.input_shape}")
        print(f"模型输出形状: {self.output_shape}")
    
    def get_action(self, observation: np.ndarray, command: Optional[np.ndarray] = None) -> np.ndarray:
        """
        根据观测获取动作
        
        Args:
            observation: 机器人状态观测
            command: 用户指令 (可选)
            
        Returns:
            动作指令
        """
        # 准备输入数据
        if command is not None:
            # 如果有用户指令，将其与观测合并
            input_data = np.concatenate([observation, command])
        else:
            input_data = observation
        
        # 确保输入数据形状正确
        if self.input_shape is not None:
            expected_shape = self.input_shape[1:]  # 去掉batch维度
            if input_data.shape != expected_shape:
                # 尝试reshape或padding
                if input_data.size == np.prod(expected_shape):
                    input_data = input_data.reshape(expected_shape)
                else:
                    raise ValueError(f"输入数据形状不匹配: 期望 {expected_shape}, 实际 {input_data.shape}")
        
        # 添加batch维度
        input_data = input_data.reshape(1, -1)
        
        # 模型预测
        action = self.loader.predict(input_data)
        
        return action.flatten()  # 返回一维数组

if __name__ == "__main__":
    # 测试代码
    model_path = os.path.join(os.path.dirname(__file__), "policy.onnx")
    if os.path.exists(model_path):
        try:
            policy = PolicyModel(model_path)
            print("模型加载成功!")
            
            # 测试预测
            test_obs = np.random.randn(28)  # 假设观测维度为28
            test_command = np.array([0.0, 0.0])  # 前进指令
            action = policy.get_action(test_obs, test_command)
            print(f"测试动作输出: {action}")
            
        except Exception as e:
            print(f"测试失败: {e}")
    else:
        print(f"模型文件不存在: {model_path}")
