from functools import lru_cache
import gc
import os
import sys
import time
from datetime import datetime

import pandas as pd
import psutil
import streamlit as st
from streamlit_extras.metric_cards import style_metric_cards  # 添加卡片样式库

from utils.logger import log_operation
from utils.module_manager import get_module_manager


@lru_cache(maxsize=1)
def get_cached_system_metrics():
    """缓存系统指标以提高性能"""
    cpu_usage = psutil.cpu_percent(interval=0.1)  # 减少采样时间
    memory = psutil.virtual_memory()
    disk = psutil.disk_usage('/')
    return cpu_usage, memory, disk


def collect_system_metrics():
    """收集系统性能指标"""
    try:
        # CPU 使用率
        cpu_percent = psutil.cpu_percent(interval=1)

        # 内存使用情况
        memory = psutil.virtual_memory()
        memory_percent = memory.percent
        memory_used = memory.used / (1024 ** 3)  # GB
        memory_total = memory.total / (1024 ** 3)  # GB

        # 磁盘使用情况
        disk = psutil.disk_usage('/')
        disk_percent = disk.percent
        disk_used = disk.used / (1024 ** 3)  # GB
        disk_total = disk.total / (1024 ** 3)  # GB

        metrics = {
            "cpu_percent": cpu_percent,
            "memory_percent": memory_percent,
            "memory_used_gb": memory_used,
            "memory_total_gb": memory_total,
            "disk_percent": disk_percent,
            "disk_used_gb": disk_used,
            "disk_total_gb": disk_total
        }

        return metrics
    except Exception as e:
        log_operation("system", "ERROR", "性能监控", f"收集系统指标时出错: {str(e)}")
        return {}


def get_performance_recommendations(cpu_percent, memory_percent, disk_percent):
    """获取性能优化建议"""
    recommendations = []

    if cpu_percent > 80:
        recommendations.append("CPU 使用率较高，建议检查计算密集型操作")

    if memory_percent > 80:
        recommendations.append("内存使用率较高，建议检查内存泄漏或优化内存使用")

    if disk_percent > 85:
        recommendations.append("磁盘使用率较高，建议清理不必要的文件")

    # 模块启用情况分析
    module_manager = get_module_manager()
    all_modules = module_manager.get_modules(enabled_only=False)
    enabled_count = len([m for m in all_modules if m.enabled])
    total_count = len(all_modules)

    if enabled_count / total_count > 0.8 and total_count > 10:
        recommendations.append("启用模块比例较高，考虑禁用不常用模块以提升性能")

    if not recommendations:
        recommendations.append("系统性能表现良好，暂无明显优化建议")

    return recommendations


def show_realtime_monitoring():
    """显示实时监控信息"""
    st.subheader("实时资源使用情况")
    
    # 使用缓存的系统指标
    cpu_usage, memory, disk = get_cached_system_metrics()
    
    # 使用卡片布局展示核心指标
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric(label="💻 CPU 使用率", value=f"{cpu_usage}%",
                  delta="正常" if cpu_usage < 70 else "过高",
                  help="建议保持低于 70%")
    with col2:
        st.metric(label="🧠 内存使用率", value=f"{memory.percent}%",
                  delta="正常" if memory.percent < 80 else "过高",
                  help="建议保持低于 80%")
    with col3:
        st.metric(label="💾 磁盘使用率", value=f"{disk.percent}%",
                  delta="正常" if disk.percent < 85 else "过高",
                  help="建议保持低于 85%")
    
    # 应用卡片样式
    style_metric_cards(background_color="#FFFFFF", border_color="#E0E0E0",
                       border_left_color="#4CAF50", box_shadow=True)
    
    # 详细资源信息展示
    with st.expander("📊 详细资源信息", expanded=True):
        col1, col2 = st.columns(2)
        with col1:
            st.metric(label="已用内存", value=f"{memory.used / (1024 ** 3):.2f} GB")
            st.metric(label="可用内存", value=f"{memory.available / (1024 ** 3):.2f} GB")
        with col2:
            st.metric(label="已用磁盘空间", value=f"{disk.used / (1024 ** 3):.2f} GB")
            st.metric(label="可用磁盘空间", value=f"{disk.free / (1024 ** 3):.2f} GB")
    
    # 进程级别监控
    st.subheader("🔍 进程资源使用")
    current_process = psutil.Process(os.getpid())
    col1, col2 = st.columns(2)
    with col1:
        st.metric("进程内存使用", f"{current_process.memory_info().rss / (1024 ** 2):.2f} MB")
    with col2:
        st.metric("进程 CPU 使用率", f"{current_process.cpu_percent()}%")
    
    # 添加资源使用趋势图
    st.subheader("📈 资源使用趋势")
    col1, col2 = st.columns(2)
    with col1:
        st.line_chart([psutil.cpu_percent(interval=0.1) for _ in range(5)], height=200)
        st.caption("CPU 使用率趋势")
    with col2:
        st.line_chart([psutil.virtual_memory().percent for _ in range(5)], height=200)
        st.caption("内存使用率趋势")


def show_performance_analysis(username: str):
    """显示性能分析工具"""
    st.subheader("性能分析与优化建议")
    
    # 收集当前系统指标
    metrics = collect_system_metrics()
    
    if metrics:
        # 显示系统资源使用情况
        col1, col2, col3 = st.columns(3)
        col1.metric("CPU 使用率", f"{metrics['cpu_percent']:.1f}%")
        col2.metric("内存使用率", f"{metrics['memory_percent']:.1f}%",
                    f"{metrics['memory_used_gb']:.1f}/{metrics['memory_total_gb']:.1f}GB")
        col3.metric("磁盘使用率", f"{metrics['disk_percent']:.1f}%",
                    f"{metrics['disk_used_gb']:.1f}/{metrics['disk_total_gb']:.1f}GB")
        
        # 显示性能优化建议
        st.subheader("💡 性能优化建议")
        
        recommendations = get_performance_recommendations(
            metrics['cpu_percent'],
            metrics['memory_percent'],
            metrics['disk_percent']
        )
        
        if recommendations:
            for i, recommendation in enumerate(recommendations, 1):
                st.markdown(f"{i}. {recommendation}")
        else:
            st.info("暂无性能优化建议")
    


def show_system_information():
    """显示系统详细信息"""
    st.subheader("🖥️ 系统基本信息")
    
    # 操作系统信息
    try:
        uname = os.uname()
        system_info = {
            "系统名称": uname.sysname,
            "主机名": uname.nodename,
            "发行版本": uname.release,
            "版本信息": uname.version,
            "机器架构": uname.machine
        }
    except AttributeError:
        import platform
        system_info = {
            "系统名称": platform.system(),
            "主机名": platform.node(),
            "发行版本": platform.release(),
            "版本信息": platform.version(),
            "机器架构": platform.machine()
        }
    
    st.json(system_info)
    
    # Python 环境信息
    st.subheader("🐍 Python 环境信息")
    python_info = {
        "Python 版本": sys.version.split()[0],
        "Python 编译器": sys.implementation.name,
        "Python 可执行文件路径": sys.executable,
        "运行路径": os.getcwd()
    }
    st.json(python_info)
    
    # CPU 详细信息
    with st.expander("🧠 CPU 详细信息"):
        cpu_info = {
            "物理核心数": psutil.cpu_count(logical=False),
            "逻辑核心数": psutil.cpu_count(logical=True),
            "最大频率": f"{psutil.cpu_freq().max:.2f}MHz" if psutil.cpu_freq() else "N/A",
        }
        st.json(cpu_info)
        
        # 各核心使用率
        st.subheader("各核心使用率")
        cpu_percent_per_core = psutil.cpu_percent(percpu=True, interval=0.5)
        cores_data = {f"Core {i}": f"{percent}%" for i, percent in enumerate(cpu_percent_per_core)}
        st.json(cores_data)
    
    # 内存详细信息
    with st.expander("💾 内存详细信息"):
        virtual_mem = psutil.virtual_memory()
        memory_info = {
            "总内存": f"{virtual_mem.total / (1024 ** 3):.2f} GB",
            "已用内存": f"{virtual_mem.used / (1024 ** 3):.2f} GB",
            "可用内存": f"{virtual_mem.available / (1024 ** 3):.2f} GB",
            "内存使用率": f"{virtual_mem.percent}%"
        }
        st.json(memory_info)


def show_network_and_storage():
    """显示网络和存储信息"""
    st.subheader("🌐 网络接口信息")
    
    try:
        net_if_addrs = psutil.net_if_addrs()
        for interface_name, interface_addresses in net_if_addrs.items():
            with st.expander(f"🔌 {interface_name}", expanded=False):
                interface_data = []
                for address in interface_addresses:
                    if address.family == psutil.AF_LINK:
                        interface_data.append({"类型": "MAC 地址", "地址": address.address})
                    elif address.family == 2:  # IPv4
                        interface_data.append({"类型": "IPv4", "地址": address.address, "掩码": address.netmask})
                    elif address.family == 10:  # IPv6
                        interface_data.append({"类型": "IPv6", "地址": address.address})
                if interface_data:
                    st.dataframe(pd.DataFrame(interface_data), use_container_width=True, hide_index=True)
    except Exception as e:
        st.warning(f"获取网络接口信息时出错：{str(e)}")
    
    # 网络 IO 统计
    st.subheader("📊 网络 IO 统计")
    net_io = psutil.net_io_counters()
    io_stats = {
        "字节发送": f"{net_io.bytes_sent / (1024 ** 2):.2f} MB",
        "字节接收": f"{net_io.bytes_recv / (1024 ** 2):.2f} MB",
        "数据包发送": net_io.packets_sent,
        "数据包接收": net_io.packets_recv,
        "发送错误": net_io.errin,
        "接收错误": net_io.errout
    }
    st.json(io_stats)
    
    # 磁盘分区信息
    st.subheader("💿 磁盘分区信息")
    try:
        partitions = psutil.disk_partitions()
        for partition in partitions:
            with st.expander(f"📂 {partition.device} ({partition.mountpoint})", expanded=False):
                try:
                    usage = psutil.disk_usage(partition.mountpoint)
                    partition_info = {
                        "文件系统类型": partition.fstype,
                        "总空间": f"{usage.total / (1024 ** 3):.2f} GB",
                        "已用空间": f"{usage.used / (1024 ** 3):.2f} GB",
                        "可用空间": f"{usage.free / (1024 ** 3):.2f} GB",
                        "使用率": f"{usage.percent}%"
                    }
                    st.json(partition_info)
                except PermissionError:
                    st.warning("权限不足，无法获取该分区的使用情况")
    except Exception as e:
        st.warning(f"获取磁盘分区信息时出错：{str(e)}")
    
    # 磁盘 IO 统计
    st.subheader("📈 磁盘 IO 统计")
    disk_io = psutil.disk_io_counters()
    if disk_io:
        io_info = {
            "读取次数": disk_io.read_count,
            "写入次数": disk_io.write_count,
            "读取字节数": f"{disk_io.read_bytes / (1024 ** 2):.2f} MB",
            "写入字节数": f"{disk_io.write_bytes / (1024 ** 2):.2f} MB"
        }
        st.json(io_info)


def system_monitoring(username: str = "system"):
    if not st.session_state.get('logged_in') or st.session_state['role'] != 'admin':
        st.experimental_set_query_params(page="login")
        return

    # 添加卡片样式
    st.markdown("""
    <style>
    .metric-card {
        background: rgba(255, 255, 255, 0.9) !important;
        border-radius: 12px !important;
        padding: 1.5rem !important;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1) !important;
        transition: transform 0.3s ease;
    }
    .metric-card:hover {
        transform: translateY(-5px);
    }
    </style>
    """, unsafe_allow_html=True)

    st.title("🖥️ 系统监控")

    # 创建选项卡 - 增强为 4 个标签页
    tab1, tab2, tab3, tab4 = st.tabs(["实时监控", "性能分析", "系统信息", "网络与存储"])

    with tab1:
        show_realtime_monitoring()

    with tab2:
        show_performance_analysis(username)

    with tab3:
        show_system_information()

    with tab4:
        show_network_and_storage()
