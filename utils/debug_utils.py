import cProfile
import gc
import io
import os
import pstats
import sys
import time
import traceback
from datetime import datetime

import pandas as pd
import psutil
import streamlit as st

from sqlalchemy.orm import load_only
from models import User, OperationLog
from utils.database import get_session
from utils.logger import log_operation


def show_debug_info(username):
    """
    显示调试信息，仅在DEBUG_MODE环境变量设置时可用
    """
    if not os.getenv('DEBUG_MODE', 'False').lower() == 'true':
        st.error("🚫 调试模式未启用")
        return

    st.title("🐛 调试信息面板")

    # 创建选项卡，添加新的"系统信息查看器"选项卡
    tab1, tab2, tab3, tab4, tab5, tab6, tab7, tab8, tab9, tab10 = st.tabs(
        ["环境信息", "系统资源", "数据库状态", "性能分析", "调试工具", "应用状态", "网络与异常", "配置管理",
         "数据库查询分析器", "系统信息查看器"])

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

    with tab8:
        show_config_management()

    with tab9:
        show_database_query_analyzer(username)

    # 添加新的系统信息查看器选项卡
    with tab10:
        show_system_info_viewer()


def show_environment_info():
    """显示环境信息"""
    st.subheader("🖥️ 环境信息")

    # 修改:将运行路径单独一行显示
    st.write(f"**运行路径:** {os.getcwd()}")

    # 使用列布局美化基础环境配置显示
    col1, col2 = st.columns(2)
    with col1:
        st.metric("Python版本", os.sys.version.split()[0])
    with col2:
        st.metric("调试模式", os.getenv('DEBUG_MODE', 'False'))

    # 美化环境变量显示
    st.subheader("⚙️ 相关环境变量")
    env_vars = ['DEBUG_MODE', 'DATABASE_URL', 'SECRET_KEY', 'LOG_LEVEL']

    env_data = []
    for var in env_vars:
        value = os.getenv(var, '未设置')
        status = "✅ 已设置" if value != '未设置' else "❌ 未设置"
        env_data.append({"变量名": var, "状态": status, "值": value if value != '未设置' else ""})

    env_df = pd.DataFrame(env_data)
    st.dataframe(env_df, use_container_width=True, hide_index=True)

    # 美化已安装的包信息显示
    st.subheader("📦 已安装的Python包")
    try:
        import pkg_resources
        installed_packages = [str(dist) for dist in list(pkg_resources.working_set)]
        installed_packages.sort()

        # 使用多列显示包信息，提高可读性
        packages_df = pd.DataFrame({
            "包名称": installed_packages
        })
        st.dataframe(packages_df, use_container_width=True, hide_index=True)
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
    st.write(f"总内存: {memory.total / (1024 ** 3):.2f} GB")
    st.write(f"已用内存: {memory.used / (1024 ** 3):.2f} GB")
    st.write(f"可用内存: {memory.available / (1024 ** 3):.2f} GB")

    # 显示进程信息
    st.subheader("sPid 进程信息")
    current_process = psutil.Process(os.getpid())
    st.write(f"进程ID: {current_process.pid}")
    st.write(f"进程内存使用: {current_process.memory_info().rss / (1024 ** 2):.2f} MB")
    st.write(f"进程CPU使用率: {current_process.cpu_percent()}%")

    # 显示网络信息
    st.subheader("🌐 网络信息")
    net_io = psutil.net_io_counters()
    st.write(f"字节发送: {net_io.bytes_sent / (1024 ** 2):.2f} MB")
    st.write(f"字节接收: {net_io.bytes_recv / (1024 ** 2):.2f} MB")


def show_database_status():
    """显示数据库连接状态"""
    st.subheader("🗄️ 数据库状态")
    try:
        with get_session() as session:
            user_count = session.query(User).count()
            log_count = session.query(OperationLog).count()
            st.success(f"✅ 数据库连接正常 - 用户数: {user_count}, 日志数: {log_count}")

            # 显示最近的用户活动
            st.subheader("👥 最近用户活动")
            recent_users = session.query(User).options(
                load_only(
                    User.username,
                    User.last_login_time,
                    User.role
                )
            ).order_by(User.last_login_time.desc()).limit(5).all()
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

    # 添加性能趋势图
    st.subheader("📊 性能趋势监控")
    if 'perf_data' not in st.session_state:
        st.session_state.perf_data = []

    # 模拟性能数据收集
    if st.button("📈 收集当前性能数据"):
        cpu_percent = psutil.cpu_percent(interval=1)
        memory = psutil.virtual_memory()
        current_process = psutil.Process(os.getpid())
        process_memory = current_process.memory_info().rss / (1024 ** 2)

        perf_point = {
            'time': datetime.now().strftime('%H:%M:%S'),
            'cpu': cpu_percent,
            'memory_percent': memory.percent,
            'process_memory': process_memory
        }

        st.session_state.perf_data.append(perf_point)
        # 保持最近30个数据点
        if len(st.session_state.perf_data) > 30:
            st.session_state.perf_data.pop(0)

        st.success("性能数据已收集")

    # 显示性能趋势图
    if st.session_state.perf_data:
        perf_df = pd.DataFrame(st.session_state.perf_data)
        st.line_chart(perf_df.set_index('time')[['cpu', 'memory_percent', 'process_memory']])

        # 显示当前值
        latest = st.session_state.perf_data[-1]
        col1, col2, col3 = st.columns(3)
        col1.metric("CPU使用率", f"{latest['cpu']}%")
        col2.metric("内存使用率", f"{latest['memory_percent']}%")
        col3.metric("进程内存", f"{latest['process_memory']:.2f}MB")

    # 添加重置按钮
    if st.button("🗑️ 清空性能数据"):
        st.session_state.perf_data = []
        st.success("性能数据已清空")


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
    execution_times = []

    def wrapper(*args, **kwargs):
        if os.getenv('DEBUG_MODE', 'False').lower() == 'true':
            start_time = time.perf_counter()
            result = func(*args, **kwargs)
            end_time = time.perf_counter()
            execution_time = end_time - start_time
            execution_times.append(execution_time)

            # 计算平均执行时间
            if len(execution_times) > 10:  # 保留最近10次的执行时间
                execution_times.pop(0)
            avg_time = sum(execution_times) / len(execution_times)

            st.sidebar.info(f"⏱️ {func.__name__} 执行时间: {execution_time:.4f} 秒 (平均: {avg_time:.4f} 秒)")
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
    st.write(f"RSS内存: {memory_info.rss / (1024 ** 2):.2f} MB")
    st.write(f"VMS内存: {memory_info.vms / (1024 ** 2):.2f} MB")

    # 显示应用运行时间
    st.subheader("⏱️ 应用运行时间")
    if 'app_start_time' not in st.session_state:
        st.session_state['app_start_time'] = time.time()

    uptime = time.time() - st.session_state['app_start_time']
    st.write(f"应用已运行: {uptime:.2f} 秒 ({uptime / 60:.2f} 分钟)")


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
            1 / 0
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
            with st.expander(f"异常 #{len(st.session_state['exception_log']) - i}: {exc['type']}"):
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
            st.write(f"总空间: {disk_usage.total / (1024 ** 3):.2f} GB")
            st.write(f"已使用: {disk_usage.used / (1024 ** 3):.2f} GB")
            st.write(f"可用空间: {disk_usage.free / (1024 ** 3):.2f} GB")
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

            st.write(f"RSS内存: {memory_info.rss / (1024 ** 2):.2f} MB")
            st.write(f"VMS内存: {memory_info.vms / (1024 ** 2):.2f} MB")

            # 检查内存增长趋势
            if 'prev_memory' not in st.session_state:
                st.session_state['prev_memory'] = memory_info.rss
                st.session_state['memory_check_time'] = time.time()

            time_diff = time.time() - st.session_state['memory_check_time']
            memory_diff = memory_info.rss - st.session_state['prev_memory']

            if time_diff > 0:
                memory_growth_rate = memory_diff / time_diff / (1024 ** 2)  # MB/s
                st.write(f"内存增长速率: {memory_growth_rate:.2f} MB/s")

                if memory_growth_rate > 1.0:  # 如果每秒增长超过1MB
                    st.warning("⚠️ 检测到可能的内存泄漏")
                else:
                    st.success("✅ 内存使用稳定")

            st.session_state['prev_memory'] = memory_info.rss
            st.session_state['memory_check_time'] = time.time()
        except Exception as e:
            st.error(f"检查内存使用情况时出错: {str(e)}")


def show_config_management():
    """显示配置管理面板"""
    st.subheader("⚙️ 配置管理")
    st.info("查看和修改应用程序配置")

    # 添加配置类型选择
    config_type = st.radio(
        "选择配置类型",
        ("程序配置", "全局配置"),
        help="程序配置仅在当前会话中生效，全局配置将影响整个应用程序"
    )

    # 根据配置类型决定显示哪些环境变量
    env_vars = dict(os.environ)
    if config_type == "程序配置":
        # 定义程序相关的环境变量前缀或名称
        program_config_prefixes = ['DEBUG_MODE', 'DATABASE_URL', 'SECRET_KEY', 'LOG_LEVEL']
        program_configs = {}
        for key, value in env_vars.items():
            # 匹配特定前缀或在预定义列表中的配置项
            if (key.startswith('DEBUG_') or
                    key.startswith('DATABASE_') or
                    key.startswith('LOG_') or
                    key in program_config_prefixes or
                    'SECRET' in key):
                program_configs[key] = value
        env_vars = program_configs

    # 显示当前配置
    st.subheader("应用查看配置")
    config_df = pd.DataFrame([
        {"配置项": key, "当前值": value}
        for key, value in env_vars.items()
        if not key.startswith('_')  # 过滤掉私有变量
    ])
    st.dataframe(config_df, use_container_width=True)

    # 配置修改区域
    st.subheader("✏️ 修改配置")

    # 选择要修改的配置项
    selected_config = st.selectbox(
        "选择配置项",
        options=[key for key in env_vars.keys() if not key.startswith('_')],
        key="config_selector"
    )

    # 显示当前值并允许修改
    current_value = os.getenv(selected_config, "")
    new_value = st.text_input("新值", value=current_value, key="config_value")

    # 保存修改
    if st.button("💾 保存配置"):
        if new_value != current_value:
            os.environ[selected_config] = new_value
            st.success(f"✅ 配置项 '{selected_config}' 已更新为 '{new_value}'")
            # 根据配置类型给出不同的提示信息
            if config_type == "全局配置":
                st.warning("⚠️ 全局配置修改后需要重启应用程序才能完全生效")
            st.rerun()
        else:
            st.info("ℹ️ 配置值未发生变化")

    # 添加新配置项
    st.subheader("➕ 添加新配置项")
    new_config_key = st.text_input("新配置项名称")
    new_config_value = st.text_input("新配置项值")

    if st.button("➕ 添加配置项"):
        if new_config_key and new_config_value:
            os.environ[new_config_key] = new_config_value
            st.success(f"✅ 新配置项 '{new_config_key}' 已添加")
            # 根据配置类型给出不同的提示信息
            if config_type == "全局配置":
                st.warning("⚠️ 全局配置添加后需要重启应用程序才能完全生效")
            st.rerun()
        else:
            st.warning("⚠️ 请填写配置项名称和值")

    # 配置导入/导出
    st.subheader("📂 配置导入/导出")

    # 导出配置
    config_export = "\n".join([f"{k}={v}" for k, v in env_vars.items()])
    st.download_button(
        label="📥 导出配置",
        data=config_export,
        file_name="app_config.env",
        mime="text/plain"
    )

    # 导入配置
    uploaded_file = st.file_uploader("📤 导入配置文件", type=['env'])
    if uploaded_file is not None:
        try:
            content = uploaded_file.getvalue().decode('utf-8')
            lines = content.split('\n')
            imported_count = 0

            for line in lines:
                if line.strip() and '=' in line and not line.startswith('#'):
                    key, value = line.split('=', 1)
                    os.environ[key.strip()] = value.strip()
                    imported_count += 1

            st.success(f"✅ 成功导入 {imported_count} 个配置项")
            if config_type == "全局配置":
                st.warning("⚠️ 全局配置导入后需要重启应用程序才能完全生效")
            st.rerun()
        except Exception as e:
            st.error(f"❌ 导入配置时出错: {str(e)}")


def show_database_query_analyzer(username):
    """显示数据库查询分析器"""
    st.subheader("🔍 数据库查询分析器")
    st.info("直接执行SQL查询并分析结果")

    try:
        with get_session() as session:
            # SQL查询输入区域
            st.subheader("⌨️ SQL查询")
            default_query = """SELECT *
                               FROM intelligent_farm_airtemperaturehumidity LIMIT 10;"""

            # 使用session_state存储当前查询内容
            if 'current_query' not in st.session_state:
                st.session_state.current_query = default_query

            sql_query = st.text_area("输入SQL查询语句:", st.session_state.current_query, height=150, key="sql_query_input")

            # 更新session_state中的查询内容
            st.session_state.current_query = sql_query

            # 查询执行按钮
            col1, col2, col3 = st.columns(3)
            with col1:
                execute_btn = st.button("▶️ 执行查询")
            with col2:
                explain_btn = st.button("🔍 EXPLAIN查询")
            with col3:
                format_btn = st.button("✨ 格式化SQL")

            # 格式化SQL功能
            if format_btn:
                try:
                    import sqlparse
                    formatted_sql = sqlparse.format(sql_query, reindent=True, keyword_case='upper')
                    st.session_state.current_query = formatted_sql
                    st.rerun()
                except ImportError:
                    st.warning("需要安装sqlparse库来格式化SQL: pip install sqlparse")
                except Exception as e:
                    st.error(f"格式化SQL时出错: {str(e)}")

            # EXPLAIN查询功能
            if explain_btn:
                if sql_query.strip():
                    try:
                        # 检查查询是否适用于EXPLAIN（只适用于DML语句）
                        query_upper = sql_query.strip().upper()
                        if not any(query_upper.startswith(stmt) for stmt in ['SELECT', 'INSERT', 'UPDATE', 'DELETE']):
                            st.warning(
                                "⚠️ EXPLAIN只能用于SELECT、INSERT、UPDATE、DELETE等DML语句，不能用于SHOW、CREATE等DDL语句")
                        else:
                            from sqlalchemy import text
                            explain_query = f"EXPLAIN {sql_query}"
                            result = session.execute(text(explain_query))
                            columns = result.keys()
                            rows = result.fetchall()

                            st.subheader("🔍 EXPLAIN结果")
                            df = pd.DataFrame(rows, columns=columns)
                            st.dataframe(df, use_container_width=True)
                    except Exception as e:
                        st.error(f"执行EXPLAIN查询失败: {str(e)}")
                else:
                    st.warning("⚠️ 请输入SQL查询语句")

            # 查询执行按钮
            if execute_btn:
                if sql_query.strip():
                    log_operation(username, "INFO", "调试信息-数据库查询", f"执行了查询: {sql_query[:100]}...")
                    st.info("🔍 正在执行查询...")

                    try:
                        start_time = time.time()

                        # 执行查询
                        from sqlalchemy import text
                        result = session.execute(text(sql_query))

                        end_time = time.time()
                        execution_time = end_time - start_time

                        # 获取列名
                        columns = result.keys()

                        # 获取结果数据
                        rows = result.fetchall()

                        # 显示执行时间
                        st.success(f"✅ 查询执行成功 (耗时: {execution_time:.4f} 秒)")

                        # 显示结果统计
                        st.subheader("📈 查询结果统计")
                        st.write(f"返回行数: {len(rows)}")
                        st.write(f"列数: {len(columns)}")

                        # 显示结果数据
                        if rows:
                            st.subheader("📋 查询结果")
                            # 转换为DataFrame显示
                            df = pd.DataFrame(rows, columns=columns)
                            st.dataframe(df, use_container_width=True)

                            # 提供数据导出
                            csv = df.to_csv(index=False)
                            st.download_button(
                                label="📥 下载CSV结果",
                                data=csv,
                                file_name="query_result.csv",
                                mime="text/csv"
                            )
                        else:
                            st.info("ℹ️ 查询执行成功，但没有返回数据")

                    except Exception as e:
                        st.error(f"❌ 查询执行失败: {str(e)}")
                        log_operation(username, "ERROR", "调试信息-数据库查询", f"查询执行失败: {str(e)}")
                else:
                    st.warning("⚠️ 请输入SQL查询语句")

            # 常用查询模板
            st.subheader("📝 常用查询模板")
            st.info("选择一个模板，然后点击'应用选中模板'按钮将其加载到查询编辑器中")

            templates = {
                "查看最近的温湿度数据": "SELECT * FROM intelligent_farm_airtemperaturehumidity ORDER BY timestamp DESC LIMIT 10;",
                "查看最近的土壤湿度数据": "SELECT * FROM intelligent_farm_soilmoisture ORDER BY timestamp DESC LIMIT 10;",
                "查看最近的光照强度数据": "SELECT * FROM intelligent_farm_light_intensity ORDER BY timestamp DESC LIMIT 10;",
                "统计数据表行数": "SELECT 'intelligent_farm_airtemperaturehumidity' as table_name, COUNT(*) as count FROM intelligent_farm_airtemperaturehumidity UNION ALL SELECT 'intelligent_farm_soilmoisture' as table_name, COUNT(*) as count FROM intelligent_farm_soilmoisture UNION ALL SELECT 'intelligent_farm_light_intensity' as table_name, COUNT(*) as count FROM intelligent_farm_light_intensity;",
                "查看表结构": "SELECT table_name FROM information_schema.tables WHERE table_schema = DATABASE();",
                "查看索引信息": "SHOW INDEX FROM intelligent_farm_airtemperaturehumidity;",
                "查看表创建语句": "SHOW CREATE TABLE intelligent_farm_airtemperaturehumidity;"
            }

            selected_template = st.selectbox("选择查询模板", list(templates.keys()))
            if st.button("📋 应用选中模板"):
                st.session_state.current_query = templates[selected_template]
                st.success(f"已应用模板: {selected_template}")
                st.rerun()

    except Exception as e:
        st.error(f"❌ 数据库连接异常: {str(e)}")
        log_operation(username, "ERROR", "调试信息-数据库查询", f"数据库连接异常: {str(e)}")


def show_system_info_viewer():
    """显示系统详细信息查看器"""
    st.subheader("🖥️ 系统信息查看器")
    st.info("查看详细的系统硬件和软件信息")

    # 创建子选项卡
    sys_tab1, sys_tab2, sys_tab3, sys_tab4, sys_tab5 = st.tabs(
        ["基本系统信息", "CPU详细信息", "内存详细信息", "磁盘信息", "网络信息"])

    # 基本系统信息
    with sys_tab1:
        st.subheader("📋 基本系统信息")
        try:
            uname = os.uname()
            system_info = {
                "系统名称": uname.sysname,
                "主机名": uname.nodename,
                "发行版本": uname.release,
                "版本信息": uname.version,
                "机器架构": uname.machine
            }
            st.json(system_info)
        except AttributeError:
            # Windows系统不支持uname
            import platform
            system_info = {
                "系统名称": platform.system(),
                "主机名": platform.node(),
                "发行版本": platform.release(),
                "版本信息": platform.version(),
                "机器架构": platform.machine()
            }
            st.json(system_info)

        # Python信息
        st.subheader("🐍 Python信息")
        python_info = {
            "Python版本": sys.version,
            "Python编译器": sys.implementation.name,
            "Python可执行文件路径": sys.executable,
            "Python路径": sys.path
        }
        st.json(python_info)

    # CPU详细信息
    with sys_tab2:
        st.subheader("🧠 CPU详细信息")
        try:
            # CPU基本信息
            cpu_info = {
                "物理核心数": psutil.cpu_count(logical=False),
                "逻辑核心数": psutil.cpu_count(logical=True),
                "最大频率": f"{psutil.cpu_freq().max:.2f}MHz" if psutil.cpu_freq() else "N/A",
                "当前频率": f"{psutil.cpu_freq().current:.2f}MHz" if psutil.cpu_freq() else "N/A"
            }
            st.json(cpu_info)

            # CPU使用率（每个核心）
            st.subheader("📈 各核心使用率")
            cpu_percent_per_core = psutil.cpu_percent(percpu=True, interval=1)
            cores_data = {f"Core {i}": f"{percent}%" for i, percent in enumerate(cpu_percent_per_core)}
            st.json(cores_data)

            # CPU时间统计
            st.subheader("⏱️ CPU时间统计")
            cpu_times = psutil.cpu_times()
            times_info = {
                "用户时间": f"{cpu_times.user:.2f}秒",
                "系统时间": f"{cpu_times.system:.2f}秒",
                "空闲时间": f"{cpu_times.idle:.2f}秒",
                "中断时间": f"{cpu_times.interrupt:.2f}秒" if hasattr(cpu_times, 'interrupt') else "N/A"
            }
            st.json(times_info)

        except Exception as e:
            st.error(f"获取CPU信息时出错: {str(e)}")

    # 内存详细信息
    with sys_tab3:
        st.subheader("💾 内存详细信息")
        try:
            # 虚拟内存
            virtual_mem = psutil.virtual_memory()
            virtual_info = {
                "总内存": f"{virtual_mem.total / (1024 ** 3):.2f} GB",
                "已用内存": f"{virtual_mem.used / (1024 ** 3):.2f} GB",
                "可用内存": f"{virtual_mem.available / (1024 ** 3):.2f} GB",
                "内存使用率": f"{virtual_mem.percent}%",
                "缓冲区": f"{virtual_mem.buffers / (1024 ** 3):.2f} GB" if hasattr(virtual_mem, 'buffers') else "N/A",
                "缓存": f"{virtual_mem.cached / (1024 ** 3):.2f} GB" if hasattr(virtual_mem, 'cached') else "N/A"
            }
            st.json(virtual_info)

            # 交换内存
            st.subheader("🔁 交换内存")
            swap_mem = psutil.swap_memory()
            swap_info = {
                "总交换空间": f"{swap_mem.total / (1024 ** 3):.2f} GB",
                "已用交换空间": f"{swap_mem.used / (1024 ** 3):.2f} GB",
                "可用交换空间": f"{swap_mem.free / (1024 ** 3):.2f} GB",
                "交换空间使用率": f"{swap_mem.percent}%",
                "交换次数": f"输入: {swap_mem.sin}, 输出: {swap_mem.sout}" if hasattr(swap_mem, 'sin') else "N/A"
            }
            st.json(swap_info)

        except Exception as e:
            st.error(f"获取内存信息时出错: {str(e)}")

    # 磁盘信息
    with sys_tab4:
        st.subheader("💿 磁盘信息")
        try:
            # 磁盘分区信息
            st.subheader("📂 磁盘分区")
            partitions = psutil.disk_partitions()
            partition_data = []
            for partition in partitions:
                partition_info = {
                    "设备": partition.device,
                    "挂载点": partition.mountpoint,
                    "文件系统类型": partition.fstype,
                }

                try:
                    partition_usage = psutil.disk_usage(partition.mountpoint)
                    partition_info.update({
                        "总空间": f"{partition_usage.total / (1024 ** 3):.2f} GB",
                        "已用空间": f"{partition_usage.used / (1024 ** 3):.2f} GB",
                        "可用空间": f"{partition_usage.free / (1024 ** 3):.2f} GB",
                        "使用率": f"{partition_usage.percent}%"
                    })
                except PermissionError:
                    partition_info.update({
                        "总空间": "N/A (权限不足)",
                        "已用空间": "N/A (权限不足)",
                        "可用空间": "N/A (权限不足)",
                        "使用率": "N/A (权限不足)"
                    })

                partition_data.append(partition_info)

            for i, partition in enumerate(partition_data):
                st.write(f"**分区 {i + 1}**")
                st.json(partition)

            # 磁盘IO统计
            st.subheader("📊 磁盘IO统计")
            disk_io = psutil.disk_io_counters()
            if disk_io:
                io_info = {
                    "读取次数": disk_io.read_count,
                    "写入次数": disk_io.write_count,
                    "读取字节数": f"{disk_io.read_bytes / (1024 ** 2):.2f} MB",
                    "写入字节数": f"{disk_io.write_bytes / (1024 ** 2):.2f} MB",
                    "读取时间": f"{disk_io.read_time} ms" if hasattr(disk_io, 'read_time') else "N/A",
                    "写入时间": f"{disk_io.write_time} ms" if hasattr(disk_io, 'write_time') else "N/A"
                }
                st.json(io_info)

        except Exception as e:
            st.error(f"获取磁盘信息时出错: {str(e)}")

    # 网络信息
    with sys_tab5:
        st.subheader("🌐 网络信息")
        try:
            # 网络接口信息
            st.subheader("🔌 网络接口")
            net_if_addrs = psutil.net_if_addrs()
            for interface_name, interface_addresses in net_if_addrs.items():
                st.write(f"**{interface_name}**")
                interface_data = []
                for address in interface_addresses:
                    if address.family == psutil.AF_LINK:  # MAC地址
                        interface_data.append({"类型": "MAC地址", "地址": address.address})
                    elif address.family == 2:  # IPv4
                        interface_data.append({"类型": "IPv4", "地址": address.address, "掩码": address.netmask})
                    elif address.family == 10:  # IPv6
                        interface_data.append({"类型": "IPv6", "地址": address.address, "掩码": address.netmask})
                st.dataframe(pd.DataFrame(interface_data), use_container_width=True)

            # 网络IO统计
            st.subheader("📊 网络IO统计")
            net_io = psutil.net_io_counters()
            io_info = {
                "字节发送": f"{net_io.bytes_sent / (1024 ** 2):.2f} MB",
                "字节接收": f"{net_io.bytes_recv / (1024 ** 2):.2f} MB",
                "数据包发送": net_io.packets_sent,
                "数据包接收": net_io.packets_recv,
                "发送错误": net_io.errin,
                "接收错误": net_io.errout,
                "发送丢弃": net_io.dropin,
                "接收丢弃": net_io.dropout
            }
            st.json(io_info)

            # 网络连接信息
            st.subheader("🔗 网络连接")
            try:
                connections = psutil.net_connections()
                conn_data = []
                for conn in connections[:50]:  # 限制显示前50个连接
                    conn_data.append({
                        "类型": str(conn.type),
                        "本地地址": f"{conn.laddr.ip}:{conn.laddr.port}" if conn.laddr else "N/A",
                        "远程地址": f"{conn.raddr.ip}:{conn.raddr.port}" if conn.raddr else "N/A",
                        "状态": conn.status
                    })
                if conn_data:
                    st.dataframe(pd.DataFrame(conn_data), use_container_width=True)
                    if len(connections) > 50:
                        st.info(f"共 {len(connections)} 个连接，仅显示前50个")
                else:
                    st.info("暂无网络连接")
            except psutil.AccessDenied:
                st.warning("访问网络连接信息需要管理员权限")

        except Exception as e:
            st.error(f"获取网络信息时出错: {str(e)}")
