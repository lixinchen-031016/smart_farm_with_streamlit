from functools import lru_cache

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
        memory_used = memory.used / (1024**3)  # GB
        memory_total = memory.total / (1024**3)  # GB
        
        # 磁盘使用情况
        disk = psutil.disk_usage('/')
        disk_percent = disk.percent
        disk_used = disk.used / (1024**3)  # GB
        disk_total = disk.total / (1024**3)  # GB
        
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
        recommendations.append("_initializer_CPU 使用率较高，建议检查计算密集型操作")
    
    if memory_percent > 80:
        recommendations.append("_initializer_内存使用率较高，建议检查内存泄漏或优化内存使用")
    
    if disk_percent > 85:
        recommendations.append("_initializer_磁盘使用率较高，建议清理不必要的文件")
    
    # 模块启用情况分析
    module_manager = get_module_manager()
    all_modules = module_manager.get_modules(enabled_only=False)
    enabled_count = len([m for m in all_modules if m.enabled])
    total_count = len(all_modules)
    
    if enabled_count / total_count > 0.8 and total_count > 10:
        recommendations.append("_initializer_启用模块比例较高，考虑禁用不常用模块以提升性能")
    
    if not recommendations:
        recommendations.append("_initializer_系统性能表现良好，暂无明显优化建议")
    
    return recommendations

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
    
    # 创建选项卡
    tab1, tab2 = st.tabs(["实时监控", "性能分析"])
    
    with tab1:
        st.subheader("实时资源使用情况")
        st.write("服务器资源使用情况：")

        # 使用缓存的系统指标
        cpu_usage, memory, disk = get_cached_system_metrics()

        # 使用卡片布局展示核心指标
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric(label="💻 CPU 使用率", value=f"{cpu_usage}%",
                     delta="正常" if cpu_usage < 70 else "过高",
                     help="建议保持低于70%")
        with col2:
            st.metric(label="🧠 内存使用率", value=f"{memory.percent}%",
                     delta="正常" if memory.percent < 80 else "过高",
                     help="建议保持低于80%")
        with col3:
            st.metric(label="💾 磁盘使用率", value=f"{disk.percent}%",
                     delta="正常" if disk.percent < 85 else "过高",
                     help="建议保持低于85%")
        
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
        
        # 添加资源使用趋势图
        st.subheader("📈 资源使用趋势")
        col1, col2 = st.columns(2)
        with col1:
            # 使用更少的数据点和更快的采样速度
            st.line_chart([psutil.cpu_percent(interval=0.1) for _ in range(5)], height=200)
            st.caption("CPU 使用率趋势")
        with col2:
            st.line_chart([psutil.virtual_memory().percent for _ in range(5)], height=200)
            st.caption("内存使用率趋势")
    
    with tab2:
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
                    # 移除前缀以便显示
                    clean_recommendation = recommendation.replace("_initializer_", "")
                    st.markdown(f"{i}. {clean_recommendation}")
            else:
                st.info("暂无性能优化建议")
        else:
            st.error("无法收集系统性能指标")