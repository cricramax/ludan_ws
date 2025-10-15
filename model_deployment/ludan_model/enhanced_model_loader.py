#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import numpy as np
import torch
import onnxruntime as ort
from typing import Union, Optional, Dict, Any

# TensorRT相关导入（可选）
try:
    import tensorrt as trt
    import pycuda.driver as cuda
    import pycuda.autoinit
    TENSORRT_AVAILABLE = True
except ImportError:
    TENSORRT_AVAILABLE = False
    print("警告: TensorRT未安装，将使用ONNX Runtime")

class TensorRTEngine:
    """TensorRT推理引擎"""
    
    def __init__(self, engine_path: str):
        """
        初始化TensorRT引擎
        
        Args:
            engine_path: TensorRT引擎文件路径
        """
        if not TENSORRT_AVAILABLE:
            raise RuntimeError("TensorRT不可用")
        
        self.engine_path = engine_path
        self.engine = None
        self.context = None
        self.inputs = []
        self.outputs = []
        self.bindings = []
        self.stream = None
        
        self._load_engine()
    
    def _load_engine(self):
        """加载TensorRT引擎"""
        try:
            # 创建TensorRT logger
            TRT_LOGGER = trt.Logger(trt.Logger.WARNING)
            
            # 加载引擎
            with open(self.engine_path, 'rb') as f:
                runtime = trt.Runtime(TRT_LOGGER)
                self.engine = runtime.deserialize_cuda_engine(f.read())
            
            # 创建执行上下文
            self.context = self.engine.create_execution_context()
            
            # 分配内存
            self._allocate_buffers()
            
            print(f"TensorRT引擎加载成功: {self.engine_path}")
            
        except Exception as e:
            raise RuntimeError(f"TensorRT引擎加载失败: {e}")
    
    def _allocate_buffers(self):
        """分配GPU内存缓冲区"""
        self.inputs = []
        self.outputs = []
        self.bindings = []
        
        for i in range(self.engine.num_bindings):
            size = trt.volume(self.engine.get_binding_shape(i)) * self.engine.max_batch_size
            dtype = trt.nptype(self.engine.get_binding_dtype(i))
            
            # 分配GPU内存
            host_mem = cuda.pagelocked_empty(size, dtype)
            device_mem = cuda.mem_alloc(host_mem.nbytes)
            
            self.bindings.append(int(device_mem))
            
            if self.engine.binding_is_input(i):
                self.inputs.append({'host': host_mem, 'device': device_mem})
            else:
                self.outputs.append({'host': host_mem, 'device': device_mem})
        
        # 创建CUDA流
        self.stream = cuda.Stream()
    
    def infer(self, input_data: np.ndarray) -> np.ndarray:
        """
        执行推理
        
        Args:
            input_data: 输入数据
            
        Returns:
            推理结果
        """
        if not TENSORRT_AVAILABLE:
            raise RuntimeError("TensorRT不可用")
        
        # 复制输入数据到GPU
        np.copyto(self.inputs[0]['host'], input_data.ravel())
        
        # 异步传输数据到GPU
        cuda.memcpy_htod_async(self.inputs[0]['device'], self.inputs[0]['host'], self.stream)
        
        # 执行推理
        self.context.execute_async_v2(bindings=self.bindings, stream_handle=self.stream.handle)
        
        # 异步传输结果回CPU
        cuda.memcpy_dtoh_async(self.outputs[0]['host'], self.outputs[0]['device'], self.stream)
        
        # 同步等待完成
        self.stream.synchronize()
        
        # 返回结果
        return self.outputs[0]['host'].copy()

class EnhancedModelLoader:
    """增强的模型加载器，支持TensorRT、ONNX Runtime和PyTorch"""
    
    def __init__(self, model_path: str, model_type: str = "auto", use_tensorrt: bool = False):
        """
        初始化增强模型加载器
        
        Args:
            model_path: 模型文件路径
            model_type: 模型类型 ("onnx", "pytorch", "tensorrt", "auto")
            use_tensorrt: 是否优先使用TensorRT
        """
        self.model_path = model_path
        self.model_type = model_type
        self.use_tensorrt = use_tensorrt
        self.model = None
        self.session = None
        self.trt_engine = None
        self.inference_method = None
        
        if not os.path.exists(model_path):
            raise FileNotFoundError(f"模型文件不存在: {model_path}")
        
        self._load_model()
    
    def _load_model(self):
        """加载模型"""
        if self.model_type == "auto":
            self._auto_detect_and_load()
        elif self.model_type == "tensorrt":
            self._load_tensorrt_model()
        elif self.model_type == "onnx":
            self._load_onnx_model()
        elif self.model_type == "pytorch":
            self._load_pytorch_model()
        else:
            raise ValueError(f"不支持的模型类型: {self.model_type}")
    
    def _auto_detect_and_load(self):
        """自动检测并加载模型"""
        if self.use_tensorrt and TENSORRT_AVAILABLE:
            # 优先尝试TensorRT
            trt_path = self.model_path.replace('.onnx', '.trt')
            if os.path.exists(trt_path):
                self.model_path = trt_path
                self._load_tensorrt_model()
                return
        
        # 根据文件扩展名选择
        if self.model_path.endswith('.trt'):
            self._load_tensorrt_model()
        elif self.model_path.endswith('.onnx'):
            self._load_onnx_model()
        elif self.model_path.endswith('.pt') or self.model_path.endswith('.pth'):
            self._load_pytorch_model()
        else:
            raise ValueError(f"不支持的模型文件格式: {self.model_path}")
    
    def _load_tensorrt_model(self):
        """加载TensorRT模型"""
        if not TENSORRT_AVAILABLE:
            raise RuntimeError("TensorRT不可用，请安装TensorRT和pycuda")
        
        try:
            self.trt_engine = TensorRTEngine(self.model_path)
            self.inference_method = "tensorrt"
            print(f"成功加载TensorRT模型: {self.model_path}")
        except Exception as e:
            raise RuntimeError(f"加载TensorRT模型失败: {e}")
    
    def _load_onnx_model(self):
        """加载ONNX模型"""
        try:
            # 尝试使用GPU提供者
            providers = ['CUDAExecutionProvider', 'CPUExecutionProvider']
            self.session = ort.InferenceSession(self.model_path, providers=providers)
            self.inference_method = "onnx"
            print(f"成功加载ONNX模型: {self.model_path}")
        except Exception as e:
            raise RuntimeError(f"加载ONNX模型失败: {e}")
    
    def _load_pytorch_model(self):
        """加载PyTorch模型"""
        try:
            self.model = torch.load(self.model_path, map_location='cpu')
            if isinstance(self.model, dict):
                print("警告: 检测到state_dict格式，需要模型结构定义")
            self.model.eval()
            self.inference_method = "pytorch"
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
        if self.inference_method == "tensorrt":
            return self.trt_engine.infer(input_data)
        elif self.inference_method == "onnx":
            input_name = self.session.get_inputs()[0].name
            output = self.session.run(None, {input_name: input_data})
            return output[0]
        elif self.inference_method == "pytorch":
            with torch.no_grad():
                input_tensor = torch.from_numpy(input_data).float()
                output = self.model(input_tensor)
                return output.numpy()
        else:
            raise RuntimeError("模型未正确加载")
    
    def get_input_shape(self) -> tuple:
        """获取模型输入形状"""
        if self.inference_method == "tensorrt":
            return self.trt_engine.engine.get_binding_shape(0)
        elif self.inference_method == "onnx":
            return self.session.get_inputs()[0].shape
        elif self.inference_method == "pytorch":
            return None  # 需要根据具体模型结构确定
        else:
            raise RuntimeError("模型未正确加载")
    
    def get_output_shape(self) -> tuple:
        """获取模型输出形状"""
        if self.inference_method == "tensorrt":
            return self.trt_engine.engine.get_binding_shape(1)
        elif self.inference_method == "onnx":
            return self.session.get_outputs()[0].shape
        elif self.inference_method == "pytorch":
            return None  # 需要根据具体模型结构确定
        else:
            raise RuntimeError("模型未正确加载")
    
    def benchmark(self, input_data: np.ndarray, num_runs: int = 100) -> Dict[str, float]:
        """
        性能基准测试
        
        Args:
            input_data: 测试输入数据
            num_runs: 测试运行次数
            
        Returns:
            性能统计信息
        """
        import time
        
        # 预热
        for _ in range(10):
            self.predict(input_data)
        
        # 测试
        times = []
        for _ in range(num_runs):
            start_time = time.time()
            self.predict(input_data)
            end_time = time.time()
            times.append(end_time - start_time)
        
        return {
            'method': self.inference_method,
            'avg_time_ms': np.mean(times) * 1000,
            'min_time_ms': np.min(times) * 1000,
            'max_time_ms': np.max(times) * 1000,
            'std_time_ms': np.std(times) * 1000,
            'fps': 1.0 / np.mean(times)
        }

class EnhancedPolicyModel:
    """增强的策略模型包装器，支持TensorRT优化"""
    
    def __init__(self, model_path: str, model_type: str = "auto", use_tensorrt: bool = False):
        """
        初始化增强策略模型
        
        Args:
            model_path: 模型文件路径
            model_type: 模型类型
            use_tensorrt: 是否使用TensorRT优化
        """
        self.loader = EnhancedModelLoader(model_path, model_type, use_tensorrt)
        self.input_shape = self.loader.get_input_shape()
        self.output_shape = self.loader.get_output_shape()
        
        print(f"模型加载方法: {self.loader.inference_method}")
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
            input_data = np.concatenate([observation, command])
        else:
            input_data = observation
        
        # 确保输入数据形状正确
        if self.input_shape is not None:
            expected_shape = self.input_shape[1:]  # 去掉batch维度
            if input_data.shape != expected_shape:
                if input_data.size == np.prod(expected_shape):
                    input_data = input_data.reshape(expected_shape)
                else:
                    raise ValueError(f"输入数据形状不匹配: 期望 {expected_shape}, 实际 {input_data.shape}")
        
        # 添加batch维度
        input_data = input_data.reshape(1, -1)
        
        # 模型预测
        action = self.loader.predict(input_data)
        
        return action.flatten()
    
    def benchmark_performance(self, observation: np.ndarray, command: Optional[np.ndarray] = None, num_runs: int = 100) -> Dict[str, float]:
        """性能基准测试"""
        if command is not None:
            input_data = np.concatenate([observation, command])
        else:
            input_data = observation
        
        input_data = input_data.reshape(1, -1)
        return self.loader.benchmark(input_data, num_runs)

def convert_onnx_to_tensorrt(onnx_path: str, trt_path: str, precision: str = "fp16"):
    """
    将ONNX模型转换为TensorRT引擎
    
    Args:
        onnx_path: ONNX模型路径
        trt_path: 输出TensorRT引擎路径
        precision: 精度 ("fp32", "fp16", "int8")
    """
    if not TENSORRT_AVAILABLE:
        raise RuntimeError("TensorRT不可用")
    
    TRT_LOGGER = trt.Logger(trt.Logger.WARNING)
    
    with trt.Builder(TRT_LOGGER) as builder, builder.create_network(1 << int(trt.NetworkDefinitionCreationFlag.EXPLICIT_BATCH)) as network, trt.OnnxParser(network, TRT_LOGGER) as parser:
        
        # 解析ONNX模型
        with open(onnx_path, 'rb') as model:
            if not parser.parse(model.read()):
                print("解析ONNX模型失败")
                for error in range(parser.num_errors):
                    print(parser.get_error(error))
                return False
        
        # 配置构建器
        config = builder.create_builder_config()
        config.max_workspace_size = 1 << 30  # 1GB
        
        # 设置精度
        if precision == "fp16":
            config.set_flag(trt.BuilderFlag.FP16)
        elif precision == "int8":
            config.set_flag(trt.BuilderFlag.INT8)
        
        # 构建引擎
        print("构建TensorRT引擎...")
        engine = builder.build_engine(network, config)
        
        if engine is None:
            print("构建TensorRT引擎失败")
            return False
        
        # 保存引擎
        with open(trt_path, 'wb') as f:
            f.write(engine.serialize())
        
        print(f"TensorRT引擎保存成功: {trt_path}")
        return True

if __name__ == "__main__":
    # 测试代码
    model_path = os.path.join(os.path.dirname(__file__), "policy.onnx")
    
    if os.path.exists(model_path):
        try:
            # 测试不同推理方法
            print("=== 测试ONNX Runtime ===")
            policy_onnx = EnhancedPolicyModel(model_path, use_tensorrt=False)
            
            test_obs = np.random.randn(28)
            test_command = np.array([0.0, 0.0])
            
            # 性能测试
            perf_onnx = policy_onnx.benchmark_performance(test_obs, test_command)
            print(f"ONNX Runtime性能: {perf_onnx}")
            
            # 如果TensorRT可用，测试TensorRT
            if TENSORRT_AVAILABLE:
                print("\n=== 测试TensorRT ===")
                trt_path = model_path.replace('.onnx', '.trt')
                
                # 转换ONNX到TensorRT
                if not os.path.exists(trt_path):
                    print("转换ONNX到TensorRT...")
                    convert_onnx_to_tensorrt(model_path, trt_path)
                
                if os.path.exists(trt_path):
                    policy_trt = EnhancedPolicyModel(trt_path, model_type="tensorrt")
                    perf_trt = policy_trt.benchmark_performance(test_obs, test_command)
                    print(f"TensorRT性能: {perf_trt}")
                    
                    # 性能比较
                    speedup = perf_onnx['avg_time_ms'] / perf_trt['avg_time_ms']
                    print(f"TensorRT加速比: {speedup:.2f}x")
            
        except Exception as e:
            print(f"测试失败: {e}")
    else:
        print(f"模型文件不存在: {model_path}")
