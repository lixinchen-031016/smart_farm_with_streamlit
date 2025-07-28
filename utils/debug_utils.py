import os
import psutil
import streamlit as st
from utils.logger import log_operation
from utils.database import get_session
from models import User, OperationLog
import cProfile
import pstats
import io
import time
import gc
from datetime import datetime

def show_debug_info(username):
    """
    显示调试信息，仅在DEBUG_MODE环境变量设置时可用
    """
    if not os.getenv('DEBUG_MODE', 'False').lower() == 'true':
        st.error("🚫 调试模式未启用")
        return

    st.title("🐛 调试信息面板")
    
    # 创建选项卡
    tab1, tab2, tab3, tab4, tab5 = st.tabs(["环境信息", "系统资源", "数据库状态", "性能分析", "调试工具"])
    
    with tab1:
        show_environment_info()
    
    with tab2:
        show_system_resources(username)
    
    with tab3:
        show_database_status()
    
    with tab4:
        show_performance_analysis(username)
        
    with tab5:
        show_debug_tools(username)

def show_environment_info():
    """显示环境信息"""
    st.subheader("🖥️ 环境信息")
    st.info("基础环境配置")
    st.write(f"运行路径: {os.getcwd()}")
    st.write(f"Python版本: {os.sys.version}")
    st.write(f"环境变量 DEBUG_MODE: {os.getenv('DEBUG_MODE')}")
    
    # 显示所有相关环境变量
    st.subheader("⚙️ 相关环境变量")
    env_vars = ['DEBUG_MODE', 'DATABASE_URL', 'SECRET_KEY']
    for var in env_vars:
        st.write(f"{var}: {os.getenv(var, '未设置')}")

def show_system_resources(username):
    """显示系统资源使用情况"""
    st.subheader("📊 系统资源监控")
    cpu_percent = psutil.cpu_percent(interval=1)
    memory = psutil.virtual_memory()
    disk = psutil.disk_usage('/')
    
    col1, col2, col3 = st.columns(3)
    col1.metric("💻 CPU使用率", f"{cpu_percent}%")
    col2.metric("🧠 内存使用率", f"{memory.percent}%")
    col3.metric("💾 磁盘使用率", f"{disk.percent}%")
    
    # 显示详细内存信息
    st.subheader("💾 内存详细信息")
    st.write(f"总内存: {memory.total / (1024**3):.2f} GB")
    st.write(f"已用内存: {memory.used / (1024**3):.2f} GB")
    st.write(f"可用内存: {memory.available / (1024**3):.2f} GB")
    
    # 显示进程信息
    st.subheader("sPid 进程信息")
    current_process = psutil.Process(os.getpid())
    st.write(f"进程ID: {current_process.pid}")
    st.write(f"进程内存使用: {current_process.memory_info().rss / (1024**2):.2f} MB")
    st.write(f"进程CPU使用率: {current_process.cpu_percent()}%")

def show_database_status():
    """显示数据库连接状态"""
    st.subheader("🗄️ 数据库状态")
    try:
        session = get_session()
        user_count = session.query(User).count()
        log_count = session.query(OperationLog).count()
        st.success(f"✅ 数据库连接正常 - 用户数: {user_count}, 日志数: {log_count}")
        
        # 显示最近的用户活动
        st.subheader("👥 最近用户活动")
        recent_users = session.query(User).order_by(User.last_login_time.desc()).limit(5).all()
        for user in recent_users:
            st.text(f"{user.username} - {user.last_login_time} - {user.role}")
        
        session.close()
    except Exception as e:
        st.error(f"❌ 数据库连接异常: {str(e)}")

def show_performance_analysis(username):
    """显示性能分析工具"""
    st.subheader("⚡ 性能分析工具")
    
    # 垃圾回收信息
    st.subheader("🗑️ 垃圾回收状态")
    gc_stats = gc.get_stats()
    st.write(f"垃圾回收次数: {gc.get_count()}")
    st.write(f"垃圾回收阈值: {gc.get_threshold()}")
    
    # 内存分析
    if st.button("🔬 运行内存分析"):
        log_operation(username, "INFO", "调试信息-性能分析", "用户运行了内存分析")
        st.info("🔍 正在分析内存使用情况...")
        
        # 获取对象计数
        obj_counts = {}
        for obj in gc.get_objects():
            obj_type = type(obj).__name__
            obj_counts[obj_type] = obj_counts.get(obj_type, 0) + 1
        
        # 显示前10个最常见对象类型
        sorted_counts = sorted(obj_counts.items(), key=lambda x: x[1], reverse=True)[:10]
        st.subheader("🔢 最常见的对象类型")
        for obj_type, count in sorted_counts:
            st.write(f"{obj_type}: {count}")
    
    # 函数性能分析
    st.subheader("⏱️ 函数性能分析")
    code_to_profile = st.text_area("⌨️ 输入要分析的Python代码:", 
                                  "import time\nfor i in range(1000000):\n    pass",
                                  height=150)
    
    if st.button("📊 分析代码性能"):
        log_operation(username, "INFO", "调试信息-代码分析", "用户分析了自定义代码")
        st.info("🔍 正在分析代码性能...")
        
        # 创建性能分析器
        pr = cProfile.Profile()
        pr.enable()
        
        try:
            # 执行用户代码
            exec(code_to_profile)
        except Exception as e:
            st.error(f"❌ 执行代码时出错: {str(e)}")
            return
        
        pr.disable()
        
        # 输出分析结果
        s = io.StringIO()
        ps = pstats.Stats(pr, stream=s)
        ps.sort_stats('cumulative')
        ps.print_stats(10)  # 显示前10个最耗时的函数
        
        st.subheader("📈 性能分析结果")
        st.text(s.getvalue())

def show_debug_tools(username):
    """显示调试工具"""
    st.subheader("🛠️ 调试工具箱")
    
    # 日志级别调整
    st.subheader("📋 日志级别设置")
    log_levels = ["INFO", "DEBUG", "WARNING", "ERROR"]
    current_log_level = st.selectbox("选择日志级别", log_levels, index=log_levels.index(os.getenv("LOG_LEVEL", "INFO")))
    if st.button("💾 应用日志级别"):
        st.success(f"✅ 日志级别已设置为: {current_log_level}")
        os.environ["LOG_LEVEL"] = current_log_level
    
    # 性能监控开关
    st.subheader("🎚️ 性能监控")
    enable_profiling = st.checkbox("启用详细性能监控")
    if enable_profiling:
        st.info("✅ 详细性能监控已启用")
    
    # 系统信息刷新
    st.subheader("🔄 系统信息")
    if st.button("🔄 刷新系统信息"):
        st.rerun()
    
    # 调试日志记录
    st.subheader("📝 调试日志")
    debug_message = st.text_input("输入调试信息")
    if st.button("📤 记录调试信息"):
        if debug_message:
            log_operation(username, "DEBUG", "调试工具", debug_message)
            st.success("✅ 调试信息已记录")
        else:
            st.warning("⚠️ 请输入调试信息")

def debug_mode_warning():
    """
    显示调试模式警告信息
    """
    if os.getenv('DEBUG_MODE', 'False').lower() == 'true':
        st.warning("⚠️ 系统处于调试模式，仅用于开发和故障排查")

def show_debug_config():
    """
    显示调试配置选项
    """
    if not os.getenv('DEBUG_MODE', 'False').lower() == 'true':
        return
    
    st.subheader("🔧 调试配置")
    
    # 日志级别调整
    log_level = st.selectbox("📋 日志级别", ["INFO", "DEBUG", "WARNING", "ERROR"])
    if st.button("💾 应用日志级别"):
        st.success(f"✅ 日志级别已设置为: {log_level}")
    
    # 性能监控开关
    enable_profiling = st.checkbox("🎚️ 启用详细性能监控")
    if enable_profiling:
        st.info("✅ 详细性能监控已启用")

# 添加新的调试工具函数
def log_debug_event(username, event_type, details):
    """
    记录调试事件到专门的日志表（如果存在）或普通日志
    """
    if os.getenv('DEBUG_MODE', 'False').lower() == 'true':
        log_operation(username, "DEBUG", f"调试-{event_type}", details)

def measure_execution_time(func):
    """
    装饰器：测量函数执行时间
    """
    def wrapper(*args, **kwargs):
        if os.getenv('DEBUG_MODE', 'False').lower() == 'true':
            start_time = time.time()
            result = func(*args, **kwargs)
            end_time = time.time()
            st.sidebar.info(f"⏱️ {func.__name__} 执行时间: {end_time - start_time:.4f} 秒")
            return result
        else:
            return func(*args, **kwargs)
    return wrapper