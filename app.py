import base64
import os
from datetime import datetime
from io import BytesIO

import jwt
import pandas as pd
import plotly.express as px
import streamlit as st

# 配置页面，隐藏默认顶栏
st.set_page_config(
    page_title="智能农场管理系统",
    page_icon="🌱",
    layout="wide",
    initial_sidebar_state="auto",
    menu_items={
        'Get Help': None,
        'Report a bug': None,
        'About': None
    }
)

from streamlit_extras.metric_cards import style_metric_cards
from streamlit_option_menu import option_menu

import models
import utils.system_monitoring
from auth import session
from utils.data_analysis import data_analysis
from utils.data_cleaning_ui import data_cleaning
from utils.data_prediction import data_prediction
from utils.data_visualization import data_visualization
# 添加: 引入新的数据库模块
from utils.database import get_session
from utils.lazy_importer import lazy_import, preload_modules
# 添加日志查看器模块导入
from utils.logger import log_operation
from utils.module_config_ui import show_module_config_ui, get_enabled_modules_for_sidebar
from utils.sync_manager import sync_databases_ui
from utils.user_management import user_management
# 添加异常处理模块
from utils.error_handling import exception_handler, safe_execute

# 延迟导入模块
render_header = lazy_import('utils.data_preview', 'render_header')
render_data_metrics = lazy_import('utils.data_preview', 'render_data_metrics')
show_debug_info = lazy_import('utils.debug_utils', 'show_debug_info')
show_decision_engine = lazy_import('utils.decision_engine', 'show_decision_engine')
show_log_viewer = lazy_import('utils.log_viewer', 'show_log_viewer')
fetch_data_in_bulk = lazy_import('utils.data_operations', 'fetch_data_in_bulk')
login = lazy_import('auth', 'login')
register = lazy_import('auth', 'register')
utils_analysis_module = lazy_import('utils.analysis')
perform_prediction = lazy_import('utils.predictions', 'perform_prediction')
multivariate_prediction = lazy_import('utils.predictions', 'multivariate_prediction')
prepare_prediction_ui = lazy_import('utils.predictions', 'prepare_prediction_ui')
get_historical_data = lazy_import('utils.predictions', 'get_historical_data')
show_prediction_results = lazy_import('utils.predictions', 'show_prediction_results')
visualize_data = lazy_import('utils.visualization', 'visualize_data')
enhanced_visualization = lazy_import('utils.enhanced_visualization', 'visualize_data')
create_dual_axis_chart = lazy_import('utils.enhanced_visualization', 'create_dual_axis_chart')
create_time_animation = lazy_import('utils.enhanced_visualization', 'create_time_animation')
create_smart_chart_recommendation = lazy_import('utils.enhanced_visualization', 'create_smart_chart_recommendation')
user_management = lazy_import('utils.user_management', 'user_management')
system_monitoring = lazy_import('utils.system_monitoring', 'system_monitoring')

# AI洞察模块导入
from utils.ai_insights import AIInsightsAnalyzer

# 预加载频繁使用的模块以提高性能
preload_modules([
    'utils.data_preview',  # 数据预览是核心功能，频繁使用
    'utils.analysis',  # 数据分析功能经常使用
    'utils.visualization',  # 可视化功能经常使用
    'utils.dashboard',
    'utils.integrated_dashboard'  # 综合仪表板功能
])


# 函数：获取最新数据
def fetch_latest_data(session):
    """
    获取数据库中最新的空气温度、湿度、土壤湿度、土壤养分和光照强度数据
    :param session: 数据库会话对象
    :return: 包含最新数据的元组
    """
    air_temp_hum = session.query(models.AirTemperatureHumidity).order_by(
        models.AirTemperatureHumidity.timestamp.desc()).first()
    soil_moist = session.query(models.SoilMoisture).order_by(models.SoilMoisture.timestamp.desc()).first()
    soil_nutri = session.query(models.SoilNutrient).order_by(models.SoilNutrient.timestamp.desc()).first()
    light_intens = session.query(models.LightIntensity).order_by(
        models.LightIntensity.timestamp.desc()).first()  # 添加光照强度查询
    return air_temp_hum, soil_moist, soil_nutri, light_intens  # 添加光照强度返回值


# 函数：数据预览
@exception_handler
def data_preview():
    if not st.session_state.get('logged_in'):
        st.query_params.page = "login"
        return

    # 获取数据库会话
    with get_session() as session:
        # 调用render_header时传入session参数
        render_header(session)

        # 渲染数据指标卡片，同时传入session和username参数
        render_data_metrics(session, st.session_state['username'])

        # 优化卡片样式
        style_metric_cards(
            background_color="#FFFFFF",
            border_color="#E0E0E0",
            border_left_color="#4CAF50",
            box_shadow=True,
            border_size_px=2,
            border_radius_px=10
        )


# 函数：读取文件
def read_file(uploaded_file):
    """
    读取上传的文件并将其转换为Pandas DataFrame
    :param uploaded_file: 上传的文件对象
    :return: Pandas DataFrame
    """
    if uploaded_file.type == "application/json":
        data = pd.read_json(uploaded_file)
    elif uploaded_file.type in ["text/csv", "application/vnd.ms-excel"]:
        data = pd.read_csv(uploaded_file)
    elif uploaded_file.type == "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet":
        data = pd.read_excel(uploaded_file)
    else:
        st.error("不支持的文件类型")
        log_operation(st.session_state['username'], "ERROR", "上传数据读取",
                      f"不支持的文件类型")
        return None
    # 新增: 强制转换timestamp列
    if 'timestamp' in data.columns:
        data['timestamp'] = pd.to_datetime(data['timestamp'], errors='coerce')
    return data


# 函数：数据概览
@exception_handler
def data_overview():
    if not st.session_state.get('logged_in'):
        st.query_params.page = "login"
        return

    # 修改：美化数据概览标题和布局
    st.title("📊 数据概览")

    # 添加渐变标题样式
    st.markdown("""
    <style>
    .gradient-header {
        background: linear-gradient(45deg, #4CAF50, #8BC34A);
        color: white;
        padding: 1rem;
        border-radius: 10px;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
    }
    </style>
    <h3 class="gradient-header">数据来源选择</h3>
    """, unsafe_allow_html=True)

    # 新增: 数据来源选择
    data_source = st.radio("选择数据来源", ["从数据库读取", "上传文件"])
    st.session_state['data_source'] = data_source  # 存储数据来源信息

    if data_source == "从数据库读取":
        # 添加时间范围选择器
        st.subheader("选择时间范围")
        start_time = st.date_input("选择开始时间")
        end_time = st.date_input("选择结束时间")

        if st.button("从数据库读取数据"):
            try:
                df = fetch_data_in_bulk(session, start_time, end_time)
                log_operation(st.session_state['username'], "INFO", "数据概览-数据库读取",
                              f"时间范围: {start_time}至{end_time} 获取{len(df)}条记录")
                # 确保timestamp列转换为datetime类型
                df['timestamp'] = pd.to_datetime(df['timestamp'])
                st.session_state['data'] = df
            except Exception as e:
                # 这里的异常会被装饰器捕获
                raise

    elif data_source == "上传文件":
        uploaded_file = st.file_uploader("选择文件", type=["csv", "xlsx", "xls", "json"])

        if uploaded_file is not None:
            try:
                data = read_file(uploaded_file)
                if data is not None:
                    log_operation(st.session_state['username'], "INFO", "数据概览-文件上传",
                                  f"文件名: {uploaded_file.name} 类型: {uploaded_file.type} 记录数: {len(data)}")
                    # 确保timestamp列类型正确
                    if 'timestamp' in data.columns:
                        data['timestamp'] = pd.to_datetime(data['timestamp'], errors='coerce')
                        # 删除无效的datetime数据
                        data = data[data['timestamp'].notna()]
                    st.session_state['data'] = data
            except Exception as e:
                # 这里的异常会被装饰器捕获
                raise

    # 确保数据展示和导出逻辑兼容两种数据读取方式
    if 'data' in st.session_state:
        try:
            data = st.session_state['data'].copy()

            # 确保所有datetime列都转换为Arrow兼容的格式
            for col in data.select_dtypes(include=['datetime64']).columns:
                data[col] = data[col].astype('datetime64[ms]')

            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("行数", data.shape[0])
            with col2:
                st.metric("列数", data.shape[1])
            with col3:
                st.metric("缺失值数", data.isnull().sum().sum())

            style_metric_cards()

            st.subheader("数据预览")
            st.dataframe(data.head())

            st.subheader("数据类型")
            # 显示修改后的数据类型
            st.dataframe(data.dtypes.astype(str).to_frame('dtype'))

            # 数据导出
            st.subheader("数据导出")
            export_format = st.radio("选择导出格式", ["CSV", "Excel", "JSON"])  # 修改: 新增JSON选项
            if st.button("📤 导出数据", type="primary"):
                log_operation(st.session_state['username'], "INFO", "数据概览-数据导出",
                              f"导出格式: {export_format} 文件名: exported_data.{export_format.lower()}")
                if export_format == "CSV":
                    csv = data.to_csv(index=False)
                    b64 = base64.b64encode(csv.encode()).decode()
                    href = f'<a href="data:file/csv;base64,{b64}" download="exported_data.csv">下载 CSV 文件</a>'
                elif export_format == "Excel":
                    towrite = BytesIO()
                    data.to_excel(towrite, index=False, engine="openpyxl")
                    towrite.seek(0)
                    b64 = base64.b64encode(towrite.read()).decode()
                    href = f'<a href="data:application/vnd.openxmlformats-officedocument.spreadsheetml.sheet;base64,{b64}" download="exported_data.xlsx">下载 Excel 文件</a>'
                elif export_format == "JSON":  # 新增: JSON导出逻辑
                    json_str = data.to_json(orient='records', force_ascii=False)
                    b64 = base64.b64encode(json_str.encode()).decode()
                    href = f'<a href="data:application/json;base64,{b64}" download="exported_data.json">下载 JSON 文件</a>'
                st.markdown(href, unsafe_allow_html=True)
        except Exception as e:
            # 这里的异常会被装饰器捕获
            raise


# 函数：高级分析
@exception_handler
def advanced_analysis():
    """
    显示高级分析页面，提供数据分组和聚合功能
    """
    if not st.session_state.get('logged_in'):
        st.query_params.page = "login"
        return

    st.title("高级分析")
    if 'data' not in st.session_state:
        st.warning("请先在数据概览页面上传数据")
        return

    data = st.session_state['data']

    # 添加标签页以组织复杂功能
    tab1, tab2 = st.tabs(["📊 智能分组分析", "📈 详细图表"])

    with tab1:
        st.subheader("数据分组和聚合")
        group_column = st.selectbox("选择分组列", data.columns)

        # 修改: 过滤掉与分组列相同的列
        available_columns = [col for col in data.select_dtypes(include=['float64', 'int64']).columns if
                             col != group_column]
        if not available_columns:
            st.error("没有可用的数值列用于聚合，请检查数据。")
            return

        agg_column = st.selectbox("选择聚合列", available_columns)
        agg_function = st.selectbox("选择聚合函数", ["平均值", "总和", "最大值", "最小值"])

        if st.button("开始分析"):
            try:
                log_operation(st.session_state['username'], "INFO", "高级分析-分组聚合",
                              f"分组列: {group_column} 聚合列: {agg_column} 函数: {agg_function}")
                grouped_data = utils_analysis_module().group_and_aggregate(data, group_column, agg_column, agg_function)

                # 提供通俗易懂的分析结果
                st.write("**分组聚合结果解读：**")

                # 根据聚合函数提供不同的解释
                if agg_function == "平均值":
                    st.write(f"• 计算了每组 **{group_column}** 的 **{agg_column}** 平均值")
                    if 'temperature' in agg_column.lower() or '温' in agg_column:
                        st.write(f"• 平均温度可以帮助了解不同分组条件下温度的整体情况")
                    elif 'humidity' in agg_column.lower() or '湿' in agg_column:
                        st.write(f"• 平均湿度可以反映不同分组条件下的湿度状况")
                    elif 'moisture' in agg_column.lower() or '土壤' in agg_column:
                        st.write(f"• 平均土壤湿度有助于判断灌溉效果")
                elif agg_function == "总和":
                    st.write(f"• 计算了每组 **{group_column}** 的 **{agg_column}** 总和")
                elif agg_function == "最大值":
                    st.write(f"• 找出了每组 **{group_column}** 的 **{agg_column}** 最大值")
                    st.write(f"• 最大值可以帮助识别极端情况或最佳表现")
                elif agg_function == "最小值":
                    st.write(f"• 找出了每组 **{group_column}** 的 **{agg_column}** 最小值")
                    st.write(f"• 最小值可以帮助识别潜在问题或最低表现")

                # 显示结果表格
                st.write("**详细结果：**")
                st.dataframe(grouped_data)

                # 提供洞察和建议
                if len(grouped_data) > 1:
                    max_group = grouped_data.loc[grouped_data[agg_column].idxmax()][group_column]
                    min_group = grouped_data.loc[grouped_data[agg_column].idxmin()][group_column]
                    st.info(f"💡 **智能洞察**: {agg_column} 最高的分组是 **{max_group}**，最低的是 **{min_group}**")

                    # 提供基于数据的建议
                    if agg_function in ["平均值", "最大值"] and ('temperature' in agg_column.lower() or '温' in agg_column):
                        if grouped_data[agg_column].max() > 30:
                            st.warning(f"⚠️ 最高平均温度达到 {grouped_data[agg_column].max():.2f}°C，可能需要加强通风降温")
                        elif grouped_data[agg_column].min() < 15:
                            st.warning(f"⚠️ 最低平均温度仅为 {grouped_data[agg_column].min():.2f}°C，可能需要加强保温措施")

                    elif agg_function in ["平均值", "最大值"] and ('humidity' in agg_column.lower() or '湿' in agg_column):
                        if grouped_data[agg_column].max() > 70:
                            st.warning(f"⚠️ 最高平均湿度达到 {grouped_data[agg_column].max():.2f}%，可能需要加强通风除湿")
                        elif grouped_data[agg_column].min() < 40:
                            st.warning(f"⚠️ 最低平均湿度仅为 {grouped_data[agg_column].min():.2f}%，可能需要增加加湿措施")
            except Exception as e:
                # 这里的异常会被装饰器捕获
                raise

    with tab2:
        st.subheader("可视化图表")
        group_column_viz = st.selectbox("选择分组列 (图表)", data.columns, key="viz_group")

        # 修改: 过滤掉与分组列相同的列
        available_columns_viz = [col for col in data.select_dtypes(include=['float64', 'int64']).columns if
                                 col != group_column_viz]
        if not available_columns_viz:
            st.error("没有可用的数值列用于聚合，请检查数据。(图表版)")
            return

        agg_column_viz = st.selectbox("选择聚合列 (图表)", available_columns_viz, key="viz_agg")
        agg_function_viz = st.selectbox("选择聚合函数 (图表)", ["平均值", "总和", "最大值", "最小值"], key="viz_func")

        if st.button("生成图表"):
            try:
                grouped_data_viz = utils_analysis_module().group_and_aggregate(data, group_column_viz, agg_column_viz,
                                                                               agg_function_viz)

                fig = px.bar(grouped_data_viz, x=group_column_viz, y=agg_column_viz,
                             title=f"{group_column_viz} 分组的 {agg_column_viz} {agg_function_viz}")
                st.plotly_chart(fig, use_container_width=True)
            except Exception as e:
                # 这里的异常会被装饰器捕获
                raise


# 函数：使用说明
def show_instructions():
    """
    显示使用说明页面
    """
    from utils.instruction_manual import show_instructions as show_full_manual
    show_full_manual()

# 函数：日志分析
def show_log_analysis():
    """
    显示日志分析页面
    """
    from utils.log_analyzer import show_log_analysis as show_log_analysis_ui
    show_log_analysis_ui()


# 函数：系统监控
def system_monitoring():
    """
    显示系统监控页面，实时查看服务器资源使用情况
    """
    utils.system_monitoring.system_monitoring()


# 函数：日志分析
def log_analysis():
    """
    显示日志分析页面
    """
    show_log_analysis()


# 函数：数据备份
def data_backup():
    """
    显示数据备份页面，允许管理员按时间范围备份数据
    """
    if not st.session_state.get('logged_in') or st.session_state['role'] != 'admin':
        st.query_params.page = "login"
        return

    st.title("数据备份")

    # 添加开始和结束时间选择器
    start_time = st.date_input("选择开始时间")
    end_time = st.date_input("选择结束时间")

    if st.button("执行备份"):
        log_operation(st.session_state['username'], "INFO", "数据备份",
                      f"时间范围: {start_time}至{end_time}")
        # 调用 utils/backup.py 中的备份函数
        from utils.backup import backup_ui
        backup_ui(session, start_time, end_time, st.session_state['username'])


# 函数：数据恢复
def data_restore():
    """
    显示数据恢复页面，允许管理员恢复备份的数据
    """
    if not st.session_state.get('logged_in') or st.session_state['role'] != 'admin':
        st.query_params.page = "login"
        return

    st.title("数据恢复")

    # 调用 utils/restore.py 中的恢复UI函数
    from utils.restore import restore_ui
    restore_ui(st.session_state['username'])


@exception_handler
def ai_insights_analysis():
    """AI洞察分析页面，结合数据分析和预测结果进行智能解读"""
    if not st.session_state.get('logged_in'):
        st.query_params.page = "login"
        return

    st.title("🤖 AI洞察分析")
    st.caption("利用AI大模型对数据分析和预测结果进行智能解读和建议")

    # 初始化AI分析器
    if 'ai_analyzer' not in st.session_state:
        st.session_state.ai_analyzer = AIInsightsAnalyzer("qwen3.5:4b")

    analyzer = st.session_state.ai_analyzer

    # 检查模型可用性
    try:
        is_available, available_models = analyzer.chat.check_model_available()

        if not is_available:
            st.warning(f"⚠️ AI模型 {analyzer.model_name} 未安装或不可用")
            col1, col2 = st.columns([3, 1])
            with col1:
                model_input = st.text_input("输入要使用的AI模型名称:", value=analyzer.model_name)
            with col2:
                if st.button("🔄 切换模型"):
                    analyzer.chat.model_name = model_input
                    analyzer.model_name = model_input
                    st.rerun()

            if st.button("📥 拉取AI模型", type="primary"):
                success = analyzer.chat.pull_model_if_needed()
                if success:
                    st.rerun()
        else:
            st.success(f"✅ AI模型 {analyzer.model_name} 可用")

            # 选择分析类型

            st.markdown("### 数据洞察分析")

            if 'data' not in st.session_state:
                st.warning("请先在数据概览页面上传数据")
                return

            data = st.session_state['data']
            data_description = st.text_area("数据背景描述（可选）",
                                                placeholder="请输入关于数据来源、用途或其他相关信息的描述...", height=100)

            if st.button("执行AI数据洞察分析", type="primary"):
                    with st.spinner("AI正在分析数据并生成洞察..."):
                        ai_insights, data_summary = analyzer.integrate_analysis_with_ai(data, data_description)
    except Exception as e:
        # 这里的异常会被装饰器捕获
        raise

# 函数：主函数
@exception_handler
def main():
    """
    应用的主函数，负责页面路由和功能调用
    """
    # 初始化应用，预加载关键模块
    initialize_app()

    # 新增：自动登录逻辑
    if 'jwt_token' in st.query_params:
        try:
            token = st.query_params['jwt_token']
            decoded = jwt.decode(token, os.getenv("SECRET_KEY"), algorithms=["HS256"])
            if decoded['exp'] > datetime.now().timestamp():
                st.session_state['logged_in'] = True
                st.session_state['username'] = decoded['username']
                st.session_state['role'] = decoded['role']
        except (jwt.ExpiredSignatureError, jwt.InvalidTokenError):
            st.query_params.clear()  # 新API清除无效token

    # 修改后的登录状态检查逻辑
    if 'logged_in' not in st.session_state:
        st.session_state['logged_in'] = False

    # 新增：退出登录逻辑
    if st.session_state.get('logout_clicked'):
        st.query_params.clear()  # 新API清除所有参数
        st.session_state.clear()
        st.rerun()

    # 初始化路由状态
    if 'menu_selection' not in st.session_state:
        st.session_state.menu_selection = "综合监控仪表板"

    # 修改: 使用新API获取页面参数
    page = st.query_params.get("page", "login")

    # 优化登录态处理逻辑
    if page in ["login", "register"] and st.session_state['logged_in']:
        # 保持用户之前的页面状态
        if 'previous_page' in st.session_state:
            st.query_params.page = st.session_state['previous_page']
        else:
            st.query_params.page = "integrated_dashboard"
        st.rerun()

    # 未登录用户访问受限页面时重定向到登录页
    if not st.session_state['logged_in'] and page not in ["login", "register"]:
        st.session_state['previous_page'] = page  # 保存用户想要访问的页面
        st.query_params.page = "login"
        st.rerun()

    # 新增：统一路由处理逻辑
    if page == "login":
        safe_execute(login, session, st)
    elif page == "register":
        safe_execute(register, session, st)
    elif page == "module_config":
        if st.session_state.get('role') == 'admin':
            safe_execute(show_module_config_ui, st.session_state['username'], True)
        else:
            st.error("仅管理员可以访问模块配置管理")
            # 重定向到综合仪表板
            st.query_params.page = "integrated_dashboard"
            st.rerun()
    elif page == "dashboard":
        from utils.dashboard import show_dashboard
        safe_execute(show_dashboard)
    else:
        # 登录成功后显示欢迎信息
        if st.session_state.get('logged_in'):
            # 只在刚登录时显示欢迎信息
            if st.session_state.get('just_logged_in', False):
                st.success(f"欢迎您，{st.session_state['username']}！您已成功登录智能农场管理系统。")
                st.session_state['just_logged_in'] = False

        # 重构侧边栏菜单逻辑
        with st.sidebar:
            # 新增：显示当前登录用户信息
            if st.session_state.get('logged_in'):
                st.markdown(f"""
                <div style="background-color: #f0f8ff; padding: 10px; border-radius: 5px; margin-bottom: 15px;">
                    <p style="margin: 0; font-weight: bold;">当前用户:</p>
                    <p style="margin: 0; color: #4CAF50;">{st.session_state['username']}</p>
                    <p style="margin: 0; font-size: 0.9em;">角色: {'管理员' if st.session_state['role'] == 'admin' else '普通用户'}</p>
                </div>
                """, unsafe_allow_html=True)

                # 添加退出登录按钮到侧边栏用户信息处
                if st.button("🚪 退出登录"):
                    st.session_state['logout_clicked'] = True
                    st.rerun()

                # 为管理员添加模块配置管理快捷链接
                if st.session_state.get('role') == 'admin':
                    if st.button("🔧 模块配置管理"):
                        # 保存当前页面作为返回页面
                        st.session_state['previous_page'] = page
                        st.query_params.page = "module_config"
                        st.rerun()

            # 新增：根据当前页面自动选中对应菜单项
            page_to_menu_mapping = {
                "dashboard": "控制面板",
                "data_preview": "实时数据预览",
                "data_overview": "数据概览",
                "data_cleaning": "数据清洗",
                "data_analysis": "数据分析",
                "data_visualization": "可视化",
                "advanced_analysis": "高级分析",
                "data_prediction": "本地数据预测",
                "user_management": "用户管理",
                "system_monitoring": "系统监控",
                "data_backup": "数据备份",
                "data_restore": "数据恢复",
                "log_viewer": "日志查看",
                "use_instruction": "使用说明",
                "automated_decision": "自动化决策",
                "debug_info": "调试信息",
                "module_config": "模块配置管理",
                "integrated_dashboard": "综合监控仪表板",
                "ai_insights_analysis": "AI洞察分析"
            }
            
            # 根据当前page获取对应的菜单项
            selected = page_to_menu_mapping.get(page, "综合监控仪表板")

            # 使用模块管理系统获取启用的模块
            enabled_modules = get_enabled_modules_for_sidebar(st.session_state.get('role') == 'admin')

            # 添加综合监控仪表板选项
            integrated_dashboard_option = ("综合监控仪表板", "activity")
            # 将综合监控仪表板插入到实时数据预览和数据概览之间
            insert_index = next((i for i, module in enumerate(enabled_modules) if module[0] == "数据概览"), 1)
            enabled_modules.insert(insert_index, integrated_dashboard_option)

            # 添加AI洞察分析选项
            ai_insights_option = ("AI洞察分析", "brain")
            # 将AI洞察分析插入到数据分析和可视化之间
            analysis_insert_index = next((i for i, module in enumerate(enabled_modules) if module[0] == "数据分析"), 3)
            enabled_modules.insert(analysis_insert_index + 1, ai_insights_option)

            # 根据用户角色过滤菜单项
            menu_options = []
            menu_icons = []
            for module in enabled_modules:
                # 管理员可以看到所有菜单项
                if st.session_state.get('role') == 'admin':
                    menu_options.append(module[0])
                    menu_icons.append(module[1])
                # 普通用户只能看到部分菜单项
                else:
                    # 过滤掉管理员专属功能
                    restricted_modules = ["用户管理", "系统监控", "数据备份", "数据恢复", "模块配置管理"]
                    if module[0] not in restricted_modules:
                        menu_options.append(module[0])
                        menu_icons.append(module[1])

            # 确保当前选中的页面在菜单选项中
            if selected not in menu_options:
                selected = menu_options[0] if menu_options else "综合监控仪表板"

            # 显示选项菜单
            # 这里不使用session state来设置默认值，而是直接使用从page映射来的selected
            # 这样可以确保菜单与当前URL保持同步
            selected = option_menu(
                menu_title="📚 功能菜单",
                options=menu_options,
                icons=menu_icons,
                default_index=menu_options.index(selected) if selected in menu_options else 0,
                styles={
                    "container": {"padding": "5px"},
                    "icon": {"color": "#4CAF50", "font-size": "18px"},
                    "nav-link": {"font-size": "16px", "text-align": "left", "margin": "5px"},
                    "nav-link-selected": {"background-color": "#4CAF50", "font-weight": "normal"},
                }
            )
            
            # 菜单到页面的映射
            menu_to_page_mapping = {
                "综合监控仪表板": "integrated_dashboard",
                "数据概览": "data_overview",
                "数据清洗": "data_cleaning",
                "数据分析": "data_analysis",
                "可视化": "data_visualization",
                "高级分析": "advanced_analysis",
                "本地数据预测": "data_prediction",
                "AI洞察分析": "ai_insights_analysis",
                "用户管理": "user_management",
                "系统监控": "system_monitoring",
                "日志查看": "log_viewer",
                "数据备份": "data_backup",
                "数据恢复": "data_restore",
                "数据库同步": "sync_databases",
                "自动化决策": "automated_decision",
                "调试信息": "debug_info",
                "使用说明": "use_instruction",
                "模块配置管理": "module_config"
            }
            
            # 当菜单选择发生变化时更新URL
            # 直接比较选中的菜单项和当前URL中的页面参数
            # 这样可以确保菜单点击时能够正确更新URL
            if selected in menu_to_page_mapping:
                new_page = menu_to_page_mapping[selected]
                # 只有当页面发生变化时才更新URL并重新运行
                if new_page != page:
                    # 更新URL参数
                    st.query_params.page = new_page
                    # 强制重新运行以确保路由生效
                    st.rerun()

        from utils.integrated_dashboard import show_integrated_dashboard
        # 统一路由映射
        route_mapping = {
            "integrated_dashboard": show_integrated_dashboard,
            "data_overview": data_overview,
            "data_cleaning": data_cleaning,
            "data_analysis": data_analysis,
            "data_visualization": data_visualization,
            "advanced_analysis": advanced_analysis,
            "data_prediction": data_prediction,
            "ai_insights_analysis": ai_insights_analysis,
            "user_management": lambda: safe_execute(user_management, session, st.session_state['username'], st.session_state['role']),
            "system_monitoring": system_monitoring,
            "log_viewer": show_log_viewer,
            "data_backup": data_backup,
            "data_restore": data_restore,
            "sync_databases": sync_databases_ui,
            "automated_decision": lambda: safe_execute(show_decision_engine, session, st.session_state['username']),
            "debug_info": lambda: safe_execute(show_debug_info, st.session_state['username']),
            "use_instruction": show_instructions,
            "module_config": lambda: safe_execute(show_module_config_ui, st.session_state['username'],
                                                          st.session_state.get('role') == 'admin')
        }

        # 执行路由跳转
        if page in route_mapping:
            route_mapping[page]()
        else:
            # 默认显示综合监控仪表板
            st.query_params.page = "integrated_dashboard"
            st.rerun()


def initialize_app():
    """
    初始化应用，预加载关键模块
    """
    # 获取当前页面参数
    page = st.query_params.get("page", "login")
    
    # 检查是否已经登录或在注册页面，如果是则不进行重定向
    if st.session_state.get('logged_in') or page == "register":
        pass  # 已登录或在注册页面，不进行重定向
    else:
        # 自动重定向功能：确保未登录用户访问都重定向到登录页面
        # 检查是否已经在登录页面
        if 'page' not in st.query_params or st.query_params['page'] != 'login':
            # 重定向到登录页面
            st.query_params.page = "login"
            st.rerun()
    # 这里可以添加任何需要在应用启动时执行的初始化代码
    pass


if __name__ == '__main__':
    main()
