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
import pandas as pd
import numpy as np
import traceback
import sys

def show_debug_info(username):
    """
    显示调试信息，仅在DEBUG_MODE环境变量设置时可用
    """
    if not os.getenv('DEBUG_MODE', 'False').lower() == 'true':
        st.error("🚫 调试模式未启用")
        return

    st.title("🐛 调试信息面板")
    
    # 创建选项卡
    tab1, tab2, tab3, tab4, tab5, tab6, tab7 = st.tabs(["环境信息", "系统资源", "数据库状态", "性能分析", "调试工具", "应用状态", "网络与异常"])
    
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
        
    with tab6:
        show_application_state()
        
    with tab7:
        show_network_and_exceptions(username)

def show_environment_info():
    """显示环境信息"""
    st.subheader("🖥️ 环境信息")
    st.info("基础环境配置")
    st.write(f"运行路径: {os.getcwd()}")
    st.write(f"Python版本: {os.sys.version}")
    st.write(f"环境变量 DEBUG_MODE: {os.getenv('DEBUG_MODE')}")
    
    # 显示所有相关环境变量
    st.subheader("⚙️ 相关环境变量")
    env_vars = ['DEBUG_MODE', 'DATABASE_URL', 'SECRET_KEY', 'LOG_LEVEL']
    for var in env_vars:
        st.write(f"{var}: {os.getenv(var, '未设置')}")
    
    # 显示已安装的包信息
    st.subheader("📦 已安装的Python包")
    try:
        import pkg_resources
        installed_packages = [str(dist) for dist in list(pkg_resources.working_set)]
        installed_packages.sort()
        st.text("\n".join(installed_packages))
    except Exception as e:
        st.error(f"无法获取包信息: {str(e)}")

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
    
    # 显示网络信息
    st.subheader("🌐 网络信息")
    net_io = psutil.net_io_counters()
    st.write(f"字节发送: {net_io.bytes_sent / (1024**2):.2f} MB")
    st.write(f"字节接收: {net_io.bytes_recv / (1024**2):.2f} MB")

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
        
        # 显示表信息
        st.subheader("📋 数据表信息")
        tables = ['intelligent_farm_airtemperaturehumidity', 'intelligent_farm_soilmoisture', 
                 'intelligent_farm_soilnutrient', 'intelligent_farm_light_intensity']
        
        table_data = []
        for table in tables:
            try:
                from sqlalchemy import text
                result = session.execute(text(f"SELECT COUNT(*) as count FROM {table}")).fetchone()
                table_data.append({'表名': table, '记录数': result[0]})
            except Exception as e:
                table_data.append({'表名': table, '记录数': f'错误: {str(e)}'})
        
        st.dataframe(pd.DataFrame(table_data))
        
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
            
    # 模拟异常功能
    st.subheader("💥 异常模拟")
    if st.checkbox("启用异常模拟"):
        exception_type = st.selectbox("选择异常类型", ["ValueError", "TypeError", "RuntimeError"])
        if st.button("🔥 触发异常"):
            if exception_type == "ValueError":
                raise ValueError("调试模式下模拟的ValueError异常")
            elif exception_type == "TypeError":
                raise TypeError("调试模式下模拟的TypeError异常")
            elif exception_type == "RuntimeError":
                raise RuntimeError("调试模式下模拟的RuntimeError异常")

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

# 添加新的应用状态显示功能
def show_application_state():
    """
    显示应用状态信息
    """
    st.subheader("应用查看")
    
    # 显示Streamlit会话状态
    st.subheader("📱 Streamlit会话状态")
    session_state_dict = dict(st.session_state)
    st.json(session_state_dict)
    
    # 显示查询参数 - 修改此处以使用新的API
    st.subheader("🌐 查询参数")
    query_params = st.query_params
    st.json(dict(query_params))
    
    # 显示缓存信息
    st.subheader("缓存信息")
    st.info("缓存统计信息:")
    st.write(f"- 缓存命中次数: {getattr(st, '_cache_stats', {}).get('hits', 'N/A')}")
    st.write(f"- 缓存未命中次数: {getattr(st, '_cache_stats', {}).get('misses', 'N/A')}")
    
    # 显示Widget状态
    st.subheader("🎛️ Widget状态")
    widgets_info = {
        "按钮数量": len([k for k in session_state_dict.keys() if "button" in k.lower()]),
        "输入框数量": len([k for k in session_state_dict.keys() if "input" in k.lower()]),
        "选择框数量": len([k for k in session_state_dict.keys() if "select" in k.lower()]),
    }
    st.json(widgets_info)
    
    # 显示内存使用情况
    st.subheader("💾 应用内存使用")
    process = psutil.Process(os.getpid())
    memory_info = process.memory_info()
    st.write(f"RSS内存: {memory_info.rss / (1024**2):.2f} MB")
    st.write(f"VMS内存: {memory_info.vms / (1024**2):.2f} MB")
    
    # 显示应用运行时间
    st.subheader("⏱️ 应用运行时间")
    if 'app_start_time' not in st.session_state:
        st.session_state['app_start_time'] = time.time()
    
    uptime = time.time() - st.session_state['app_start_time']
    st.write(f"应用已运行: {uptime:.2f} 秒 ({uptime/60:.2f} 分钟)")

# 新增：网络与异常监控功能
def show_network_and_exceptions(username):
    """显示网络和异常监控信息"""
    st.subheader("🌐 网络连接状态")
    
    # 显示网络接口信息
    try:
        net_if_addrs = psutil.net_if_addrs()
        for interface, addresses in net_if_addrs.items():
            st.write(f"**{interface}**:")
            for addr in addresses:
                if addr.family == 2:  # AF_INET
                    st.write(f"  - IPv4: {addr.address}")
                elif addr.family == 17:  # AF_PACKET
                    st.write(f"  - MAC: {addr.address}")
    except Exception as e:
        st.warning(f"无法获取网络接口信息: {str(e)}")
    
    # 显示网络连接统计
    st.subheader("🔌 网络连接统计")
    try:
        net_connections = psutil.net_connections()
        st.write(f"活动连接数: {len(net_connections)}")
    except psutil.AccessDenied:
        st.warning("访问网络连接信息被拒绝，这在某些系统上是正常的。需要更高权限才能查看详细网络连接信息。")
    except Exception as e:
        st.warning(f"获取网络连接信息时出错: {str(e)}")
    
    # 显示最近的异常信息
    st.subheader("❗ 最近异常信息")
    
    # 创建一个简单的异常日志记录器
    if 'exception_log' not in st.session_state:
        st.session_state['exception_log'] = []
    
    # 模拟捕获异常
    if st.button("🧪 模拟捕获异常"):
        try:
            # 故意引发一个异常
            1/0
        except Exception as e:
            exc_type, exc_value, exc_traceback = sys.exc_info()
            exception_info = {
                'timestamp': datetime.now(),
                'type': str(exc_type),
                'message': str(exc_value),
                'traceback': ''.join(traceback.format_exception(exc_type, exc_value, exc_traceback))
            }
            st.session_state['exception_log'].append(exception_info)
            st.success("已模拟捕获异常")
    
    # 显示异常日志
    if st.session_state['exception_log']:
        for i, exc in enumerate(reversed(st.session_state['exception_log'][-10:])):  # 显示最近10个异常
            with st.expander(f"异常 #{len(st.session_state['exception_log'])-i}: {exc['type']}"):
                st.write(f"**时间**: {exc['timestamp']}")
                st.write(f"**类型**: {exc['type']}")
                st.write(f"**消息**: {exc['message']}")
                st.code(exc['traceback'], language='python')
    else:
        st.info("暂无异常记录")
    
    # 添加异常捕获开关
    st.subheader("⚙️ 异常捕获设置")
    enable_exception_capture = st.checkbox("启用全局异常捕获", value=True)
    if enable_exception_capture:
        st.info("全局异常捕获已启用")
        
        # 注册全局异常处理器
        def global_exception_handler(exc_type, exc_value, exc_traceback):
            if 'exception_log' not in st.session_state:
                st.session_state['exception_log'] = []
                
            exception_info = {
                'timestamp': datetime.now(),
                'type': str(exc_type),
                'message': str(exc_value),
                'traceback': ''.join(traceback.format_exception(exc_type, exc_value, exc_traceback))
            }
            st.session_state['exception_log'].append(exception_info)
            
            # 同时记录到日志
            log_operation(username, "ERROR", "全局异常捕获", 
                         f"类型: {exc_type}, 消息: {exc_value}")
        
        sys.excepthook = global_exception_handler
    
    # 添加系统诊断工具
    st.subheader("🛠️ 系统诊断工具")
    
    # 磁盘空间检查
    if st.button("🔍 检查磁盘空间"):
        st.info("正在检查磁盘空间...")
        try:
            disk_usage = psutil.disk_usage('/')
            st.write(f"总空间: {disk_usage.total / (1024**3):.2f} GB")
            st.write(f"已使用: {disk_usage.used / (1024**3):.2f} GB")
            st.write(f"可用空间: {disk_usage.free / (1024**3):.2f} GB")
            st.write(f"使用率: {disk_usage.percent}%")
            
            if disk_usage.percent > 90:
                st.error("⚠️ 磁盘空间不足！")
            elif disk_usage.percent > 75:
                st.warning("⚠️ 磁盘空间紧张")
            else:
                st.success("✅ 磁盘空间充足")
        except Exception as e:
            st.error(f"检查磁盘空间时出错: {str(e)}")
        
    # 内存泄漏检测
    if st.button("🔍 检查内存泄漏"):
        st.info("正在检查内存使用情况...")
        try:
            process = psutil.Process(os.getpid())
            memory_info = process.memory_info()
            
            st.write(f"RSS内存: {memory_info.rss / (1024**2):.2f} MB")
            st.write(f"VMS内存: {memory_info.vms / (1024**2):.2f} MB")
            
            # 检查内存增长趋势
            if 'prev_memory' not in st.session_state:
                st.session_state['prev_memory'] = memory_info.rss
                st.session_state['memory_check_time'] = time.time()
            
            time_diff = time.time() - st.session_state['memory_check_time']
            memory_diff = memory_info.rss - st.session_state['prev_memory']
            
            if time_diff > 0:
                memory_growth_rate = memory_diff / time_diff / (1024**2)  # MB/s
                st.write(f"内存增长速率: {memory_growth_rate:.2f} MB/s")
                
                if memory_growth_rate > 1.0:  # 如果每秒增长超过1MB
                    st.warning("⚠️ 检测到可能的内存泄漏")
                else:
                    st.success("✅ 内存使用稳定")
            
            st.session_state['prev_memory'] = memory_info.rss
            st.session_state['memory_check_time'] = time.time()
        except Exception as e:
            st.error(f"检查内存使用情况时出错: {str(e)}")
