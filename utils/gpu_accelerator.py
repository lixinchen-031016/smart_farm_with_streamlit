"""
GPU加速工具模块 - 支持Apple Silicon MPS加速

提供GPU设备检测、配置和性能监控功能，专为Apple M系列芯片优化。
"""

import time
import psutil
import torch
import streamlit as st
from typing import Dict, Optional, Tuple


class GPUAccelerator:
    """GPU加速器管理类，支持Apple MPS和CUDA"""
    
    def __init__(self):
        self.device = self._detect_device()
        self.device_name = self._get_device_name()
        self.performance_log = []
        
    def _detect_device(self) -> torch.device:
        """检测可用的计算设备
        
        Returns:
            torch.device: 最优的可用设备 (MPS > CUDA > CPU)
        """
        # 优先使用Apple MPS (Metal Performance Shaders)
        if hasattr(torch.backends, 'mps') and torch.backends.mps.is_available():
            try:
                # 验证MPS是否正常工作
                test_tensor = torch.ones(1).to('mps')
                test_result = test_tensor * 2
                if test_result.device.type == 'mps':
                    print("✅ Apple MPS (Metal) 加速已启用")
                    return torch.device('mps')
            except Exception as e:
                print(f"⚠️ MPS初始化失败: {e}，回退到CPU")
        
        # 其次使用NVIDIA CUDA
        if torch.cuda.is_available():
            print(f"✅ NVIDIA CUDA 加速已启用 (GPU: {torch.cuda.get_device_name(0)})")
            return torch.device('cuda')
        
        # 最后使用CPU
        print("ℹ️ 使用CPU进行计算")
        return torch.device('cpu')
    
    def _get_device_name(self) -> str:
        """获取设备名称"""
        if self.device.type == 'mps':
            return "Apple Silicon (MPS)"
        elif self.device.type == 'cuda':
            return f"NVIDIA {torch.cuda.get_device_name(0)}"
        else:
            return "CPU"
    
    def get_device_info(self) -> Dict:
        """获取设备详细信息
        
        Returns:
            dict: 包含设备类型、名称、内存等信息
        """
        info = {
            'device_type': self.device.type,
            'device_name': self.device_name,
            'pytorch_version': torch.__version__,
        }
        
        if self.device.type == 'mps':
            # Apple MPS设备信息
            info['memory_allocated'] = self._get_mps_memory_usage()
            info['system_memory_total'] = psutil.virtual_memory().total / (1024**3)  # GB
            info['system_memory_available'] = psutil.virtual_memory().available / (1024**3)  # GB
            
        elif self.device.type == 'cuda':
            # NVIDIA CUDA设备信息
            info['gpu_name'] = torch.cuda.get_device_name(0)
            info['memory_allocated'] = torch.cuda.memory_allocated(0) / (1024**2)  # MB
            info['memory_reserved'] = torch.cuda.memory_reserved(0) / (1024**2)  # MB
            info['memory_total'] = torch.cuda.get_device_properties(0).total_mem / (1024**2)  # MB
            
        else:
            # CPU信息
            info['cpu_count'] = psutil.cpu_count()
            info['cpu_percent'] = psutil.cpu_percent(interval=0.1)
            info['memory_total'] = psutil.virtual_memory().total / (1024**3)  # GB
            info['memory_available'] = psutil.virtual_memory().available / (1024**3)  # GB
        
        return info
    
    def _get_mps_memory_usage(self) -> float:
        """估算MPS内存使用情况（MB）
        
        Note: PyTorch MPS后端不直接提供内存API，通过系统内存变化估算
        """
        try:
            process = psutil.Process()
            memory_info = process.memory_info()
            return memory_info.rss / (1024**2)  # MB
        except:
            return 0.0
    
    def to_device(self, tensor: torch.Tensor) -> torch.Tensor:
        """将张量移动到计算设备
        
        Args:
            tensor: 输入张量
            
        Returns:
            移动后的张量
        """
        return tensor.to(self.device)
    
    def clear_cache(self):
        """清理设备缓存"""
        if self.device.type == 'cuda':
            torch.cuda.empty_cache()
        elif self.device.type == 'mps':
            # MPS暂不支持显式缓存清理
            pass
    
    def benchmark_computation(self, size: int = 10000, iterations: int = 10) -> Dict:
        """执行计算基准测试
        
        Args:
            size: 测试矩阵大小
            iterations: 迭代次数
            
        Returns:
            dict: 包含平均时间、标准差等性能指标
        """
        times = []
        
        for i in range(iterations):
            # 创建测试数据
            start_time = time.time()
            
            a = torch.randn(size, size, device=self.device)
            b = torch.randn(size, size, device=self.device)
            
            # 执行矩阵乘法
            c = torch.mm(a, b)
            
            # 确保计算完成 (MPS是异步的)
            if self.device.type == 'mps':
                torch.mps.synchronize()
            elif self.device.type == 'cuda':
                torch.cuda.synchronize()
            
            end_time = time.time()
            times.append(end_time - start_time)
        
        # 统计结果
        avg_time = sum(times) / len(times)
        std_time = (sum((t - avg_time) ** 2 for t in times) / len(times)) ** 0.5
        
        result = {
            'device': self.device_name,
            'matrix_size': f"{size}x{size}",
            'iterations': iterations,
            'avg_time_ms': avg_time * 1000,
            'std_time_ms': std_time * 1000,
            'min_time_ms': min(times) * 1000,
            'max_time_ms': max(times) * 1000,
        }
        
        self.performance_log.append(result)
        return result
    
    def monitor_performance(self) -> Dict:
        """监控当前性能状态
        
        Returns:
            dict: 包含设备利用率和内存使用情况
        """
        monitoring = {
            'device': self.device_name,
            'timestamp': time.time(),
        }
        
        if self.device.type == 'mps':
            monitoring['process_memory_mb'] = self._get_mps_memory_usage()
            monitoring['cpu_percent'] = psutil.cpu_percent(interval=0.1)
            
        elif self.device.type == 'cuda':
            monitoring['gpu_memory_allocated_mb'] = torch.cuda.memory_allocated(0) / (1024**2)
            monitoring['gpu_memory_reserved_mb'] = torch.cuda.memory_reserved(0) / (1024**2)
            monitoring['gpu_utilization'] = self._get_gpu_utilization()
            
        else:
            monitoring['cpu_percent'] = psutil.cpu_percent(interval=0.1)
            monitoring['memory_percent'] = psutil.virtual_memory().percent
        
        return monitoring
    
    def _get_gpu_utilization(self) -> Optional[float]:
        """获取GPU利用率（仅CUDA）"""
        try:
            import subprocess
            result = subprocess.run(
                ['nvidia-smi', '--query-gpu=utilization.gpu', '--format=csv,noheader,nounits'],
                capture_output=True, text=True, timeout=5
            )
            if result.returncode == 0:
                return float(result.stdout.strip())
        except:
            pass
        return None
    
    def display_device_info(self):
        """在Streamlit中显示设备信息"""
        st.subheader("🖥️ 计算设备信息")
        
        info = self.get_device_info()
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.metric("设备类型", info['device_name'])
            st.metric("PyTorch版本", info['pytorch_version'])
        
        with col2:
            if self.device.type == 'mps':
                st.metric("系统内存总量", f"{info.get('system_memory_total', 0):.1f} GB")
                st.metric("系统内存可用", f"{info.get('system_memory_available', 0):.1f} GB")
            elif self.device.type == 'cuda':
                st.metric("GPU显存总量", f"{info.get('memory_total', 0):.0f} MB")
                st.metric("GPU显存已分配", f"{info.get('memory_allocated', 0):.0f} MB")
            else:
                st.metric("CPU核心数", info.get('cpu_count', 0))
                st.metric("CPU使用率", f"{info.get('cpu_percent', 0):.1f}%")
        
        with col3:
            # 显示加速状态
            if self.device.type in ['mps', 'cuda']:
                st.success("✅ GPU加速已启用")
            else:
                st.warning("⚠️ 使用CPU计算")


# 全局GPU加速器实例
_gpu_accelerator = None


def get_gpu_accelerator() -> GPUAccelerator:
    """获取全局GPU加速器实例
    
    Returns:
        GPUAccelerator: 单例实例
    """
    global _gpu_accelerator
    if _gpu_accelerator is None:
        _gpu_accelerator = GPUAccelerator()
    return _gpu_accelerator


def check_gpu_availability() -> bool:
    """检查GPU是否可用
    
    Returns:
        bool: GPU是否可用
    """
    accelerator = get_gpu_accelerator()
    return accelerator.device.type in ['mps', 'cuda']


def run_benchmark_test():
    """运行基准测试并在Streamlit中显示结果"""
    st.subheader("⚡ 性能基准测试")
    
    accelerator = get_gpu_accelerator()
    
    # 测试参数
    sizes = [1000, 5000, 10000]
    iterations = 5
    
    results_data = []
    
    progress_bar = st.progress(0)
    total_tests = len(sizes)
    
    for idx, size in enumerate(sizes):
        st.write(f"正在测试矩阵大小: {size}x{size}...")
        result = accelerator.benchmark_computation(size=size, iterations=iterations)
        results_data.append(result)
        progress_bar.progress((idx + 1) / total_tests)
    
    # 显示结果
    import pandas as pd
    df_results = pd.DataFrame(results_data)
    
    st.dataframe(df_results[[
        'matrix_size', 'avg_time_ms', 'std_time_ms', 'min_time_ms'
    ]].rename(columns={
        'matrix_size': '矩阵大小',
        'avg_time_ms': '平均耗时(ms)',
        'std_time_ms': '标准差(ms)',
        'min_time_ms': '最短耗时(ms)'
    }), use_container_width=True)
    
    # 可视化
    import plotly.graph_objects as go
    
    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=df_results['matrix_size'],
        y=df_results['avg_time_ms'],
        name='平均耗时',
        error_y=dict(type='data', array=df_results['std_time_ms']),
    ))
    
    fig.update_layout(
        title=f"不同矩阵大小的计算性能 ({accelerator.device_name})",
        xaxis_title="矩阵大小",
        yaxis_title="耗时 (毫秒)",
    )
    
    st.plotly_chart(fig, use_container_width=True)
    
    st.success(f"✅ 基准测试完成！设备: {accelerator.device_name}")


if __name__ == "__main__":
    # 独立测试
    accelerator = GPUAccelerator()
    print("\n=== 设备信息 ===")
    info = accelerator.get_device_info()
    for key, value in info.items():
        print(f"{key}: {value}")
    
    print("\n=== 基准测试 ===")
    result = accelerator.benchmark_computation(size=5000, iterations=5)
    for key, value in result.items():
        print(f"{key}: {value}")
