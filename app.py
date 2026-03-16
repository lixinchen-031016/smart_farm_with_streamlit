import base64
import io
import json
import os
from datetime import datetime
from io import BytesIO

import jwt
import numpy as np
import pandas as pd
import plotly
import plotly.express as px
import plotly.graph_objects as go
import plotly.io as pio
import streamlit as st
from streamlit_extras.metric_cards import style_metric_cards
from streamlit_option_menu import option_menu

import models
import utils.system_monitoring
from auth import session
# 添加: 引入新的数据库模块
from utils.database import get_session
from utils.enhanced_visualization import create_multi_subplot_chart
from utils.lazy_importer import lazy_import, preload_modules
# 添加日志查看器模块导入
from utils.logger import log_operation
from utils.module_config_ui import show_module_config_ui, get_enabled_modules_for_sidebar
from utils.sync_manager import sync_databases_ui

# 添加: 加载环境变量

# 添加仪表盘导入

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
def data_preview():
    if not st.session_state.get('logged_in'):
        st.query_params.page = "login"
        return

    # 获取数据库会话
    session = get_session()

    # 调用render_header时传入session参数
    render_header(session)

    # 渲染数据指标卡片，同时传入session和username参数
    render_data_metrics(session, st.session_state['username'])

    # 关闭会话
    session.close()

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
            df = fetch_data_in_bulk(session, start_time, end_time)
            log_operation(st.session_state['username'], "INFO", "数据概览-数据库读取",
                          f"时间范围: {start_time}至{end_time} 获取{len(df)}条记录")
            # 确保timestamp列转换为datetime类型
            df['timestamp'] = pd.to_datetime(df['timestamp'])
            st.session_state['data'] = df

    elif data_source == "上传文件":
        uploaded_file = st.file_uploader("选择文件", type=["csv", "xlsx", "xls", "json"])

        if uploaded_file is not None:
            data = read_file(uploaded_file)
            log_operation(st.session_state['username'], "INFO", "数据概览-文件上传",
                          f"文件名: {uploaded_file.name} 类型: {uploaded_file.type} 记录数: {len(data)}")
            if data is not None:
                # 确保timestamp列类型正确
                if 'timestamp' in data.columns:
                    data['timestamp'] = pd.to_datetime(data['timestamp'], errors='coerce')
                    # 删除无效的datetime数据
                    data = data[data['timestamp'].notna()]
                st.session_state['data'] = data

    # 确保数据展示和导出逻辑兼容两种数据读取方式
    if 'data' in st.session_state:
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


# 函数：数据清洗
def data_cleaning():
    """
    显示数据清洗页面，提供删除重复行、处理缺失值和删除列的功能
    使用新的数据清洗模块，支持规则模板和效果评估
    """
    if not st.session_state.get('logged_in'):
        st.query_params.page = "login"
        return

    st.title("🧹 数据清洗")
    
    # 导入新的数据清洗模块
    from utils.data_cleaning import (
        DataCleaner, 
        DataCleaningRule,
        create_agricultural_standard_template,
        create_machine_learning_template
    )

    # 添加标签页
    tab1, tab2, tab3, tab4, tab5 = st.tabs(["⚙️ 规则模板", "🔧 基础清洗", "💧 缺失值处理", "📊 异常值检测", "📤 数据导出"])
    
    # 初始化数据清洗器
    if 'cleaner' not in st.session_state:
        st.session_state['cleaner'] = DataCleaner()
    
    cleaner = st.session_state['cleaner']
    
    # 规则模板标签页
    with tab1:
        st.subheader("🎯 清洗规则模板")
        st.markdown("使用预设的清洗规则模板，快速应用标准化的清洗流程")
        
        if 'data' not in st.session_state:
            st.warning("请先在数据概览页面上传数据")
            return
        
        data = st.session_state['data']
        
        # 添加规则管理子标签页
        rule_tab1, rule_tab2 = st.tabs(["📋 应用模板", "💾 规则管理"])
        
        with rule_tab1:
            template_choice = st.selectbox(
                "选择清洗模板",
                ["农业数据标准清洗流程", "机器学习数据清洗模板", "自定义规则"],
                help="选择预设的清洗规则模板"
            )
            
            if st.button("应用模板并查看效果", key="apply_template"):
                progress_bar = st.progress(0)
                
                # 创建规则
                if template_choice == "农业数据标准清洗流程":
                    rule = create_agricultural_standard_template()
                elif template_choice == "机器学习数据清洗模板":
                    rule = create_machine_learning_template(data)
                else:
                    rule = DataCleaningRule("自定义规则")
                    rule.set_duplicate_removal(True)
                
                progress_bar.progress(30)
                
                # 应用规则
                cleaned_data, report = cleaner.apply_rule(data, rule)
                
                progress_bar.progress(100)
                
                # 显示清洗报告
                col1, col2 = st.columns(2)
                with col1:
                    st.metric("原始数据行数", report['original_shape'][0])
                    st.metric("清洗后数据行数", report['final_shape'][0])
                    st.metric("删除行数", report['original_shape'][0] - report['final_shape'][0])
                
                with col2:
                    st.metric("清洗前完整率", f"{report['quality_before']['completeness']:.2f}%")
                    st.metric("清洗后完整率", f"{report['quality_after']['completeness']:.2f}%")
                    st.metric("质量提升", f"{report['improvement']['completeness_improvement']:+.2f}%")
                
                # 保存清洗后的数据
                st.session_state['data'] = cleaned_data
                data = cleaned_data
                
                # 显示详细报告
                with st.expander("查看详细清洗报告", expanded=True):
                    st.code(cleaner.generate_report(report))
                
                # 保存当前规则到 session state
                st.session_state['current_rule'] = rule
        
        with rule_tab2:
            st.subheader("💾 规则管理")
            st.markdown("导出已配置的规则或加载已保存的规则")
            
            # 导出规则
            st.subheader("导出规则")
            if 'current_rule' in st.session_state:
                rule = st.session_state['current_rule']
                st.info(f"当前规则：**{rule.name}**")
                
                # 显示规则详情
                with st.expander("查看规则详情"):
                    st.json(rule.to_dict())
                
                # 导出按钮
                rule_name = st.text_input("规则文件名", value=rule.name.replace(" ", "_"))
                
                if st.button("导出规则到文件"):
                    try:
                        filepath = f"{rule_name}.json"
                        rule.save(filepath)
                        
                        # 读取文件内容用于下载
                        with open(filepath, 'r', encoding='utf-8') as f:
                            file_content = f.read()
                        
                        st.success(f"✅ 规则已保存到：{filepath}")
                        
                        # 提供下载链接
                        st.download_button(
                            label="📥 下载规则文件",
                            data=file_content,
                            file_name=f"{rule_name}.json",
                            mime="application/json"
                        )
                        
                        log_operation(st.session_state['username'], "INFO", "数据清洗 - 导出规则",
                                      f"规则名：{rule.name} 文件：{filepath}")
                    except Exception as e:
                        st.error(f"❌ 导出失败：{str(e)}")
            else:
                st.warning("请先应用一个模板以创建规则")
            
            st.divider()
            
            # 加载规则
            st.subheader("加载规则")
            uploaded_rule = st.file_uploader("上传规则文件 (.json)", type=["json"])
            
            if uploaded_rule is not None:
                try:
                    # 读取 JSON 内容
                    rule_json = json.load(uploaded_rule)
                    loaded_rule = DataCleaningRule.from_dict(rule_json)
                    
                    st.success(f"✅ 成功加载规则：**{loaded_rule.name}**")
                    
                    # 显示规则信息
                    st.info(f"描述：{loaded_rule.description}")
                    st.write(f"创建时间：{loaded_rule.created_at}")
                    
                    # 显示规则配置
                    with st.expander("查看规则配置"):
                        st.json(loaded_rule.rules)
                    
                    # 提供应用按钮
                    if st.button("应用加载的规则"):
                        progress_bar = st.progress(0)
                        cleaned_data, report = cleaner.apply_rule(data, loaded_rule)
                        progress_bar.progress(100)
                        
                        # 显示报告
                        col1, col2 = st.columns(2)
                        with col1:
                            st.metric("原始数据行数", report['original_shape'][0])
                            st.metric("清洗后数据行数", report['final_shape'][0])
                        with col2:
                            st.metric("清洗前完整率", f"{report['quality_before']['completeness']:.2f}%")
                            st.metric("清洗后完整率", f"{report['quality_after']['completeness']:.2f}%")
                        
                        st.session_state['data'] = cleaned_data
                        data = cleaned_data
                        st.session_state['current_rule'] = loaded_rule
                        
                        with st.expander("查看清洗报告"):
                            st.code(cleaner.generate_report(report))
                    
                    log_operation(st.session_state['username'], "INFO", "数据清洗 - 加载规则",
                                  f"规则名：{loaded_rule.name} 文件：{uploaded_rule.name}")
                    
                except Exception as e:
                    st.error(f"❌ 加载规则失败：{str(e)}")
                    st.error("请确保上传的文件是有效的规则 JSON 文件")

    # 基础清洗标签页
    with tab2:
        st.subheader("删除重复行")
        if st.button("删除重复行", key="drop_duplicates_btn"):
            progress_bar = st.progress(0)
            original_rows = data.shape[0]
            progress_bar.progress(33)
            data = data.drop_duplicates()
            log_operation(st.session_state['username'], "INFO", "数据清洗-删除重复行",
                          f"删除{original_rows - data.shape[0]}行 剩余{data.shape[0]}行")
            st.success(f"删除了 {original_rows - data.shape[0]} 行重复数据")
            progress_bar.progress(100)
            st.session_state['data'] = data
        
        st.subheader("批量删除列")
        st.markdown("选择要删除的列类型，支持批量操作")
                
        # 列类型分类
        numeric_cols = data.select_dtypes(include=[np.number]).columns.tolist()
        categorical_cols = data.select_dtypes(include=['object']).columns.tolist()
        datetime_cols = data.select_dtypes(include=['datetime64']).columns.tolist()
                
        col1, col2, col3 = st.columns(3)
        with col1:
            drop_numeric = st.checkbox(f"删除数值列 ({len(numeric_cols)}个)", value=False)
        with col2:
            drop_categorical = st.checkbox(f"删除分类型列 ({len(categorical_cols)}个)", value=False)
        with col3:
            drop_datetime = st.checkbox(f"删除时间列 ({len(datetime_cols)}个)", value=False)
                
        if st.button("删除选中的列类型", key="drop_columns_batch"):
            columns_to_drop = []
            if drop_numeric:
                columns_to_drop.extend(numeric_cols)
            if drop_categorical:
                columns_to_drop.extend(categorical_cols)
            if drop_datetime:
                columns_to_drop.extend(datetime_cols)
                    
            # 确保不删除 timestamp 列（如果存在）
            if 'timestamp' in columns_to_drop:
                columns_to_drop.remove('timestamp')
                    
            if columns_to_drop:
                progress_bar = st.progress(0)
                original_cols = len(data.columns)
                data = data.drop(columns=columns_to_drop)
                progress_bar.progress(100)
                log_operation(st.session_state['username'], "INFO", "数据清洗 - 批量删除列",
                              f"删除{len(columns_to_drop)}列 剩余{len(data.columns)}列")
                st.success(f"已删除 {len(columns_to_drop)} 列，剩余 {len(data.columns)} 列")
            else:
                st.warning("未选择任何列进行删除")
                
        st.subheader("手动选择删除列")
        columns_to_drop_manual = st.multiselect("选择要删除的列", data.columns.tolist())
        if st.button("删除选中的列", key="drop_columns_manual"):
            log_operation(st.session_state['username'], "INFO", "数据清洗 - 删除列",
                          f"删除列：{', '.join(columns_to_drop_manual)}")
            if columns_to_drop_manual:
                progress_bar = st.progress(0)
                data = data.drop(columns=columns_to_drop_manual)
                progress_bar.progress(100)
                st.success(f"已删除列：{', '.join(columns_to_drop_manual)}")
                st.session_state['data'] = data
            else:
                st.warning("未选择任何列进行删除")
        
        st.success("基础清洗完成")

    # 缺失值处理标签页
    with tab3:
        st.subheader("处理缺失值")
        missing_columns = data.columns[data.isnull().any()].tolist()
        if not missing_columns:
            st.info("当前数据没有缺失值")
        else:
            for column in missing_columns:
                method = st.selectbox(f"选择处理 {column} 缺失值的方法",
                                      ["保持不变", "删除", "填充平均值", "填充中位数", "填充众数"])
                if method != "保持不变":
                    log_operation(st.session_state['username'], "INFO", "数据清洗-处理缺失值",
                                  f"列: {column} 方法: {method}")
                    progress_bar = st.progress(0)
                    if method == "删除":
                        data = data.dropna(subset=[column])
                    else:
                        # 新增: 创建标识列
                        fill_flag_col = f"{column}_filled"

                        # 初始化标识列为False
                        data[fill_flag_col] = False

                        # 获取缺失值的索引
                        missing_index = data[column].isnull()

                        # 确定环境数据类型
                        env_type = "其他"
                        if 'temperature' in column.lower():
                            env_type = "空气温度"
                        elif 'humidity' in column.lower():
                            env_type = "空气湿度"
                        elif 'soil' in column.lower():
                            env_type = "土壤数据"
                        elif 'light' in column.lower():
                            env_type = "光照强度"

                        # 计算填充值
                        if method == "填充平均值":
                            fill_value = data[column].mean()
                        elif method == "填充中位数":
                            fill_value = data[column].median()
                        elif method == "填充众数":
                            fill_value = data[column].mode()[0]

                        # 填充并记录信息
                        data.loc[missing_index, column] = fill_value
                        data.loc[missing_index, fill_flag_col] = data.loc[missing_index].apply(
                            lambda row: f"行号:{row.name} | 类型:{env_type} | 填充值:{fill_value:.2f}",
                            axis=1
                        )
                        log_operation(st.session_state['username'], "INFO", "数据清洗-数据填充",
                                      f"已填充{missing_index.sum()}个缺失值并添加标识列: {fill_flag_col}")
                        st.success(f"已填充{missing_index.sum()}个缺失值并添加标识列: {fill_flag_col}")

                    progress_bar.progress(100)  # 操作完成

            st.session_state['data'] = data
            st.success("缺失值处理完成")

    # 异常值检测标签页
    with tab4:
        st.subheader("异常值检测与清除")

        # 导入异常检测工具
        from utils.anomaly_detection import detect_outliers_iqr, detect_outliers_zscore, \
            detect_outliers_isolation_forest, remove_anomalies, get_anomaly_summary

        # 选择检测方法
        detection_method = st.radio("选择异常值检测方法",
                                    ["四分位距法 (IQR)", "Z-Score法", "孤立森林算法"],
                                    horizontal=True)

        # 为孤立森林算法提供参数调整选项
        isolation_forest_params = {}
        if detection_method == "孤立森林算法":
            st.subheader("孤立森林算法参数设置")
            col1, col2 = st.columns(2)
            with col1:
                # 使用session state保存contamination值
                if 'isolation_forest_contamination' not in st.session_state:
                    st.session_state.isolation_forest_contamination = 0.1

                contamination = st.slider("异常值比例估计", 0.01, 0.5, st.session_state.isolation_forest_contamination,
                                          0.01,
                                          help="预计数据中异常值的比例，较低的值会使算法更敏感",
                                          key="isolation_forest_contamination_slider")
                st.session_state.isolation_forest_contamination = contamination

            with col2:
                # 使用session state保存n_estimators值
                if 'isolation_forest_n_estimators' not in st.session_state:
                    st.session_state.isolation_forest_n_estimators = 100

                n_estimators = st.slider("树的数量", 50, 500, st.session_state.isolation_forest_n_estimators, 10,
                                         help="孤立树的数量，更多的树可以提高准确性但会增加计算时间",
                                         key="isolation_forest_n_estimators_slider")
                st.session_state.isolation_forest_n_estimators = n_estimators

            # 使用session state保存max_samples值
            if 'isolation_forest_max_samples' not in st.session_state:
                st.session_state.isolation_forest_max_samples = 1.0

            max_samples = st.slider("样本数量", 0.1, 1.0, st.session_state.isolation_forest_max_samples, 0.1,
                                    help="每棵树使用的样本比例，较小的值可以提高速度但可能降低准确性",
                                    key="isolation_forest_max_samples_slider")
            st.session_state.isolation_forest_max_samples = max_samples

            isolation_forest_params = {
                'contamination': contamination,
                'n_estimators': n_estimators,
                'max_samples': max_samples if max_samples < 1.0 else 'auto'
            }

        # 选择要检测的列
        numeric_columns = data.select_dtypes(include=['float64', 'int64']).columns.tolist()
        if not numeric_columns:
            st.warning("数据中没有数值型列，无法进行异常值检测")
        else:
            selected_columns = st.multiselect("选择要检测的列", numeric_columns, default=numeric_columns[:3] if len(
                numeric_columns) > 3 else numeric_columns)

            if st.button("检测异常值"):
                if not selected_columns:
                    st.warning("请至少选择一列进行检测")
                else:
                    # 根据选择的方法进行异常值检测
                    anomalies = {}
                    method_key = ""
                    if detection_method == "四分位距法 (IQR)":
                        method_key = "iqr"
                        for col in selected_columns:
                            anomalies[col] = data[detect_outliers_iqr(data, col)].index.tolist()
                    elif detection_method == "Z-Score法":
                        method_key = "zscore"
                        for col in selected_columns:
                            anomalies[col] = data[detect_outliers_zscore(data, col)].index.tolist()
                    elif detection_method == "孤立森林算法":
                        method_key = "isolation_forest"
                        # 使用改进的孤立森林算法
                        outlier_series = detect_outliers_isolation_forest(data, selected_columns,
                                                                          **isolation_forest_params)
                        for col in selected_columns:
                            anomalies[col] = data[outlier_series].index.tolist()

                    # 显示异常值摘要
                    summary = get_anomaly_summary(anomalies)
                    st.write("异常值检测结果:")
                    summary_df = pd.DataFrame(summary).T
                    st.dataframe(summary_df)

                    # 保存异常值索引到session_state
                    st.session_state['anomalies'] = anomalies
                    st.session_state['anomaly_summary'] = summary

                    # 显示详细异常值
                    with st.expander("查看详细异常值"):
                        for col, indices in anomalies.items():
                            if indices:
                                st.write(f"**{col}** 列的异常值:")
                                st.dataframe(data.loc[indices, [col]])

            # 提供清除异常值的选项
            if 'anomalies' in st.session_state:
                if st.button("清除检测到的异常值"):
                    data = remove_anomalies(data, st.session_state['anomalies'])
                    st.session_state['data'] = data
                    st.success("已清除异常值")
                    # 清除异常值信息
                    del st.session_state['anomalies']
                    del st.session_state['anomaly_summary']

    # 数据导出标签页
    with tab5:
        st.subheader("导出清洗后的数据")
        export_format = st.selectbox("选择导出格式", ["CSV", "Excel", "JSON"])
        if st.button("导出数据"):
            log_operation(st.session_state['username'], "INFO", "数据清洗-数据导出",
                          f"导出格式: {export_format} 文件名: cleaned_data.{export_format.lower()}")
            progress_bar = st.progress(0)
            if export_format == "CSV":
                csv = data.to_csv(index=False)
                b64 = base64.b64encode(csv.encode()).decode()
                href = f'<a href="data:file/csv;base64,{b64}" download="cleaned_data.csv">下载 CSV 文件</a>'
            elif export_format == "Excel":
                excel = io.BytesIO()
                data.to_excel(excel, index=False)
                excel.seek(0)
                b64 = base64.b64encode(excel.read()).decode()
                href = f'<a href="data:application/vnd.openxmlformats-officedocument.spreadsheetml.sheet;base64,{b64}" download="cleaned_data.xlsx">下载 Excel 文件</a>'
            elif export_format == "JSON":
                json_str = data.to_json(orient='records')
                b64 = base64.b64encode(json_str.encode()).decode()
                href = f'<a href="data:application/json;base64,{b64}" download="cleaned_data.json">下载 JSON 文件</a>'
            progress_bar.progress(100)  # 操作完成
            st.markdown(href, unsafe_allow_html=True)


# 函数：数据分析
def data_analysis():
    """
    显示数据分析页面，提供描述性统计和相关性分析功能
    """
    if not st.session_state.get('logged_in'):
        st.query_params.page = "login"
        return

    st.title("数据分析")
    if 'data' not in st.session_state:
        st.warning("请先在数据概览页面上传数据")
        return

    data = st.session_state['data']

    # 添加标签页以组织复杂功能
    tab1, tab2 = st.tabs(["📊 智能分析解读", "📈 详细数据图表"])

    with tab1:
        st.subheader("通俗易懂的数据分析")
        log_operation(st.session_state['username'], "INFO", "数据分析-智能解读",
                      f"数据集维度: {data.shape}")

        # 使用增强版分析工具提供通俗易懂的分析结果
        try:
            from utils.enhanced_analysis import enhanced_data_analysis
            enhanced_data_analysis(data)
        except ImportError:
            st.error("增强版分析工具不可用，使用基础分析功能")
            # 原始基础分析功能
            st.subheader("描述性统计")
            with st.expander("📊 查看统计指标说明"):
                st.markdown("""
                **关键统计指标解释：**
                - **均值(Mean)**: 数据的平均值，反映数据集中趋势
                - **标准差(Std)**: 数据离散程度的度量，值越大表示数据波动越大
                - **最小值/最大值**: 数据的取值范围
                - **25%/75%分位数**: 四分位数，帮助了解数据分布情况
                """)

            desc_data = utils_analysis_module().describe_data(data)
            st.dataframe(desc_data)

            # 添加智能推荐
            numeric_columns = data.select_dtypes(include=['float64', 'int64']).columns
            if len(numeric_columns) > 0:
                st.info(
                    f"💡 **智能推荐**: 检测到 {len(numeric_columns)} 个数值型变量，建议重点关注均值和标准差差异较大的指标")

    with tab2:
        st.subheader("详细相关性分析")
        numeric_columns = data.select_dtypes(include=['float64', 'int64']).columns
        if len(numeric_columns) < 2:
            st.warning("数据集中数值列不足两列，无法进行相关性分析。")
        else:
            # 添加相关性分析说明
            with st.expander("🔗 相关性分析说明"):
                st.markdown("""
                **相关系数解读：**
                - **1**: 完全正相关
                - **0**: 无线性相关性
                - **-1**: 完全负相关
                - **0.7~1**: 强正相关
                - **0.3~0.7**: 中等正相关
                - **0~0.3**: 弱正相关
                """)

            corr_matrix = utils_analysis_module().calculate_correlation(data)

            # 性能优化：对大数据集进行采样
            sample_size = min(1000, len(data)) if len(data) > 1000 else len(data)
            if len(data) > sample_size:
                st.info(f"🚀 **性能优化**: 数据集较大，已对 {sample_size} 行数据进行采样以提升渲染性能")

            fig = px.imshow(corr_matrix,
                            text_auto=True,
                            aspect="auto",
                            color_continuous_scale='RdBu_r',
                            zmin=-1,
                            zmax=1,
                            labels=dict(color="相关系数"))
            fig.update_traces(text=corr_matrix.round(2),
                              texttemplate="%{text}",
                              hovertemplate="变量1: %{x}<br>变量2: %{y}<br>相关系数: %{text}<extra></extra>")
            fig.update_layout(
                title="变量相关性热力图",
                font=dict(size=12)
            )
            st.plotly_chart(fig, use_container_width=True)

            # 添加智能推荐
            high_corr_pairs = []
            for i in range(len(corr_matrix.columns)):
                for j in range(i + 1, len(corr_matrix.columns)):
                    corr_value = corr_matrix.iloc[i, j]
                    if abs(corr_value) > 0.7:
                        high_corr_pairs.append((corr_matrix.columns[i], corr_matrix.columns[j], corr_value))

            if high_corr_pairs:
                st.info("💡 **智能推荐**: 检测到以下强相关变量对，建议深入分析其因果关系:")
                for col1, col2, corr in high_corr_pairs[:3]:  # 只显示前3个
                    st.markdown(f"- **{col1}** 与 **{col2}** 的相关系数为 **{corr:.2f}**")


# 函数：数据可视化
def data_visualization():
    """
    显示数据可视化页面，允许用户创建各种图表
    """
    if not st.session_state.get('logged_in'):
        st.query_params.page = "login"
        return

    st.title("数据可视化")
    if 'data' not in st.session_state:
        st.warning("请先在数据概览页面上传数据")
        return

    data = st.session_state['data']

    # 添加标签页以组织复杂功能
    tab1, tab2 = st.tabs(["📊 智能可视化", "📈 详细图表"])

    with tab1:
        # 动态参数调节面板
        has_timestamp = 'timestamp' in data.columns
        is_from_database = st.session_state.get('data_source', '') == "从数据库读取"

        # 仅在有时间戳列时显示时间范围选择器
        if has_timestamp:
            st.subheader("时间范围筛选")
            start_time = st.date_input("选择开始时间")
            end_time = st.date_input("选择结束时间")
            filtered_data = data[
                (data['timestamp'] >= pd.Timestamp(start_time)) &
                (data['timestamp'] <= pd.Timestamp(end_time))]
        else:
            filtered_data = data
            st.info("当前数据没有时间戳列，将使用全部数据进行可视化")

        # 数据质量检查
        st.subheader("数据质量检查")
        missing_values = filtered_data.isnull().sum().sum()
        duplicate_rows = filtered_data.duplicated().sum()

        col1, col2 = st.columns(2)
        with col1:
            st.metric("缺失值", missing_values)
        with col2:
            st.metric("重复行", duplicate_rows)

        if missing_values > 0:
            st.warning(f"⚠️ 检测到 {missing_values} 个缺失值，可能影响可视化效果")
        if duplicate_rows > 0:
            st.warning(f"⚠️ 检测到 {duplicate_rows} 个重复行，建议先进行数据清洗")

        # 智能推荐图表类型
        numeric_columns = filtered_data.select_dtypes(include=['float64', 'int64']).columns
        categorical_columns = filtered_data.select_dtypes(include=['object']).columns

        st.subheader("智能推荐")
        if len(numeric_columns) >= 2:
            st.info("💡 检测到多个数值型变量，推荐使用散点图探索变量间关系")
        elif len(numeric_columns) == 1 and len(categorical_columns) >= 1:
            st.info("💡 检测到数值型和分类型变量，推荐使用柱状图或箱线图进行比较分析")
        elif len(categorical_columns) >= 1 and 'timestamp' in filtered_data.columns:
            st.info("💡 检测到时间序列数据，推荐使用线图展示趋势变化")
        else:
            st.info("💡 根据当前数据特征，推荐使用直方图查看数据分布")

        # 设置统一的主题
        pio.templates.default = "plotly_white"
        color_sequence = px.colors.qualitative.Plotly
                
        # 添加高级可视化选项卡
        basic_tab, advanced_tab = st.tabs(["📊 基础图表", "🚀 高级图表"])
                
        with basic_tab:
            # 智能推荐图表类型
            if 'data' in st.session_state and len(st.session_state['data']) > 0:
                rec_result = create_smart_chart_recommendation(filtered_data)
                if rec_result[0] is not None:  # 检查是否成功返回推荐
                    rec_chart, rec_params, rec_reason = rec_result
                    with st.expander(f"💡 智能推荐：{rec_chart}", expanded=True):
                        st.markdown(f"**推荐理由**: {rec_reason}")
                        if rec_params.get('x_column'):
                            st.code(f"X 轴：{rec_params['x_column']}, Y 轴：{rec_params.get('y_column', 'N/A')}")
                    
            # 图表类型说明
            with st.expander("📊 图表类型说明"):
                st.markdown("""
                **常用图表类型适用场景:**
                - **散点图**: 展示两个数值变量之间的关系
                - **线图**: 展示数据随时间的变化趋势
                - **柱状图**: 比较不同类别的数值大小
                - **箱线图**: 展示数据分布和异常值
                - **直方图**: 展示单个数值变量的分布情况
                - **饼图**: 展示各类别占比情况
                - **热力图**: 展示矩阵数据或相关性分析
                """)
        
            chart_type = st.selectbox("选择图表类型", ["散点图", "线图", "柱状图", "箱线图", "直方图", "饼图", "热力图"])

        if len(numeric_columns) == 0:
            st.warning("数据集中没有数值列，无法进行可视化。")
            return

        x_column = None
        y_column = None
        color_column = None
        column = None

        if chart_type in ["散点图", "线图", "柱状图"]:
            x_column = st.selectbox("选择X轴", filtered_data.columns)
            y_column = st.selectbox("选择Y轴", numeric_columns)
            color_column = st.selectbox("选择颜色列（可选）", ["无"] + list(categorical_columns))
            if color_column == "无":
                color_column = None

        elif chart_type in ["箱线图", "直方图"]:
            column = st.selectbox("选择列", numeric_columns)

        elif chart_type == "饼图":
            if len(categorical_columns) == 0:
                st.warning("数据集中没有分类列，无法创建饼图。")
                return
            column = st.selectbox("选择列", categorical_columns)

        # 使用新的可视化模块生成图表
        fig = visualize_data(filtered_data, chart_type, x_column, y_column, color_column, column)
        
        with advanced_tab:
            st.subheader("🚀 高级可视化功能")
            st.markdown("探索更强大的图表类型和分析工具")
            
            # 高级图表类型选择
            adv_chart_type = st.selectbox(
                "选择高级图表类型",
                ["双轴图", "多子图"],
                help="双轴图：同时展示两个不同量纲的变量\n多子图：并列展示多个相关图表"
            )
            
            if adv_chart_type == "双轴图":
                st.markdown("### 📊 双 Y 轴图表")
                st.info("适合展示两个不同量纲或数量级的变量关系")
                
                dual_x = st.selectbox("X 轴", filtered_data.columns, key="dual_x")
                dual_y1 = st.selectbox("左 Y 轴变量", numeric_columns, key="dual_y1")
                dual_y2 = st.selectbox("右 Y 轴变量", numeric_columns, key="dual_y2")
                
                if dual_y1 != dual_y2:
                    if st.button("生成双轴图", key="gen_dual"):
                        dual_fig = create_dual_axis_chart(
                            filtered_data,
                            dual_x,
                            dual_y1,
                            dual_y2,
                            y1_title=dual_y1,
                            y2_title=dual_y2,
                            title=f"{dual_y1} vs {dual_y2} 双轴对比"
                        )
                        st.plotly_chart(dual_fig, use_container_width=True)
                        
                        # 双轴图解读
                        st.markdown("**💡 图表解读**:")
                        st.write(f"- 展示了 **{dual_y1}** (左轴) 和 **{dual_y2}** (右轴) 随 **{dual_x}** 的变化趋势")
                        
                        # 计算相关性
                        if dual_x in filtered_data.columns:
                            corr = filtered_data[[dual_y1, dual_y2]].corr().iloc[0, 1]
                            if abs(corr) > 0.7:
                                st.success(f"✅ 两者存在强相关性 (r={corr:.2f})")
                            elif abs(corr) > 0.3:
                                st.info(f"ℹ️ 两者存在中等相关性 (r={corr:.2f})")
                            else:
                                st.write(f"ℹ️ 两者相关性较弱 (r={corr:.2f})")
                else:
                    st.warning("⚠️ 左右 Y 轴变量不能相同")
            
            elif adv_chart_type == "多子图":
                    st.markdown("### 📈 多变量对比分析")
                    st.info("同时展示多个变量的变化趋势")
                    
                    # 使用 session_state 保存配置
                    if 'multi_x' not in st.session_state:
                        st.session_state.multi_x = filtered_data.columns[0]
                    if 'multi_vars' not in st.session_state:
                        st.session_state.multi_vars = numeric_columns[:3] if len(numeric_columns) >= 3 else numeric_columns
                    
                    multi_x = st.selectbox(
                        "共享 X 轴",
                        filtered_data.columns,
                        index=list(filtered_data.columns).index(st.session_state.multi_x) if st.session_state.multi_x in filtered_data.columns else 0,
                        key="multi_x_select"
                    )
                    selected_vars = st.multiselect(
                        "选择要展示的变量",
                        numeric_columns,
                        default=st.session_state.multi_vars,
                        key="multi_vars_select"
                    )
                    
                    if len(selected_vars) >= 2:
                        # 构建设置字典
                        data_dict = {}
                        titles = {}
                        for var in selected_vars:
                            data_dict[var] = {
                                'x_column': multi_x,
                                'y_column': var
                            }
                            titles[var] = var
                        
                        multi_fig = create_multi_subplot_chart(
                            filtered_data,
                            data_dict,
                            multi_x,
                            titles,
                            subplot_titles=[f"{var} 趋势" for var in selected_vars],
                            title="多变量对比分析"
                        )
                        st.plotly_chart(multi_fig, use_container_width=True)
                        
                        st.markdown("**💡 图表解读**:")
                        st.write(f"- 并列展示了 {len(selected_vars)} 个变量的变化趋势")
                        st.write("- 可以通过共享 X 轴对比不同变量在同一时间点的表现")
                    else:
                        st.warning("⚠️ 至少需要选择 2 个变量")
        
        with basic_tab:
            # 创建小图用于 UI 展示
            fig_small = go.Figure(fig)
            fig_small.update_layout(width=700, height=500)
            st.plotly_chart(fig_small, use_container_width=True)
        
            # 提供图表解读
            st.subheader("📊 图表解读")
            if chart_type == "散点图":
                st.write(f"• 散点图展示了 **{x_column}** 与 **{y_column}** 之间的关系")
                if x_column and y_column:
                    corr = filtered_data[[x_column, y_column]].corr().iloc[0, 1]
                    if abs(corr) > 0.7:
                        st.success(f"💡 **智能洞察**: {x_column} 和 {y_column} 之间存在强相关性 (相关系数：{corr:.2f})")
                        if corr > 0:
                            st.write(f"  - 两者呈现明显的正相关关系，即一个变量增加时另一个变量也倾向于增加")
                        else:
                            st.write(f"  - 两者呈现明显的负相关关系，即一个变量增加时另一个变量倾向于减少")
                    elif abs(corr) > 0.3:
                        st.info(f"💡 **智能洞察**: {x_column} 和 {y_column} 之间存在中等相关性 (相关系数：{corr:.2f})")
                        if corr > 0:
                            st.write(f"  - 两者存在一定的正相关关系")
                        else:
                            st.write(f"  - 两者存在一定的负相关关系")
                    else:
                        st.write(f"  - 两者相关性较弱，可能没有明显的线性关系")
            
                    # 提供农业相关的解读
                    if ('temperature' in x_column.lower() or '温' in x_column) and (
                            'humidity' in y_column.lower() or '湿' in y_column):
                        if corr > 0:
                            st.write(f"  - 温度与湿度呈正相关，说明高温时湿度也相对较高")
                        elif corr < 0:
                            st.write(f"  - 温度与湿度呈负相关，说明高温时湿度相对较低，符合蒸发原理")

            elif chart_type == "线图":
                st.write(f"• 线图展示了 **{y_column}** 随 **{x_column}** 变化的趋势")
                if 'timestamp' in x_column.lower() or '时间' in x_column:
                    trend_data = filtered_data[y_column].dropna()
                    if len(trend_data) > 1:
                        first_val = trend_data.iloc[0]
                        last_val = trend_data.iloc[-1]
                        if last_val > first_val * 1.1:
                            st.write(f"  - {y_column} 呈现上升趋势，从 {first_val:.2f} 增加到 {last_val:.2f}")
                        elif last_val < first_val * 0.9:
                            st.write(f"  - {y_column} 呈现下降趋势，从 {first_val:.2f} 下降到 {last_val:.2f}")
                        else:
                            st.write(f"  - {y_column} 基本保持稳定")

            elif chart_type == "柱状图":
                st.write(f"• 柱状图比较了不同 **{x_column}** 类别下的 **{y_column}** 值")

            elif chart_type == "箱线图":
                st.write(f"• 箱线图展示了 **{column}** 的数据分布情况")
                q75, q25 = filtered_data[column].quantile([0.75, 0.25])
                iqr = q75 - q25
                median_val = filtered_data[column].median()
                st.write(f"  - 中位数：{median_val:.2f}")
                st.write(f"  - 四分位距 (IQR): {iqr:.2f} (Q1: {q25:.2f}, Q3: {q75:.2f})")
        
                # 检查异常值
                outliers = filtered_data[
                    (filtered_data[column] < q25 - 1.5 * iqr) | (filtered_data[column] > q75 + 1.5 * iqr)]
                if len(outliers) > 0:
                    st.warning(f"  - 检测到 {len(outliers)} 个异常值")
                else:
                    st.write(f"  - 未检测到明显异常值")
        
            elif chart_type == "直方图":
                st.write(f"• 直方图展示了 **{column}** 的分布情况")
                mean_val = filtered_data[column].mean()
                std_val = filtered_data[column].std()
                median_val = filtered_data[column].median()
                mode_val = filtered_data[column].mode().iloc[0] if not filtered_data[column].mode().empty else 'N/A'

                st.write(f"  - 平均值: {mean_val:.2f}, 中位数: {median_val:.2f}, 众数: {mode_val:.2f}")
                st.write(f"  - 标准差: {std_val:.2f}, 方差: {filtered_data[column].var():.2f}")

                # 判断分布形状
                skewness = filtered_data[column].skew()
                kurtosis = filtered_data[column].kurtosis()

                if skewness > 1:
                    st.write(f"  - 分布右偏（正偏）：数据集中在较低值区域，右侧有长尾")
                    st.write(f"  - 数据分布不对称，平均值大于中位数，存在较高值的异常点")
                elif skewness < -1:
                    st.write(f"  - 分布左偏（负偏）：数据集中在较高值区域，左侧有长尾")
                    st.write(f"  - 数据分布不对称，平均值小于中位数，存在较低值的异常点")
                else:
                    st.write(f"  - 分布接近对称")

                # 峰度解释
                if kurtosis > 0:
                    st.write(f"  - 峰度为{kurtosis:.2f}，分布比正态分布更尖锐，数据更集中")
                elif kurtosis < 0:
                    st.write(f"  - 峰度为{kurtosis:.2f}，分布比正态分布更平坦，数据更分散")

                # 农业相关解读
                if 'temperature' in column.lower() or '温' in column:
                    temp_range = filtered_data[column].max() - filtered_data[column].min()
                    if temp_range > 15:
                        st.write(f"  - 温度变化范围较大({temp_range:.2f}°C)，可能存在明显日温差")
                    else:
                        st.write(f"  - 温度变化范围较小({temp_range:.2f}°C)，环境相对稳定")

            elif chart_type == "饼图":
                st.write(f"• 饼图展示了 **{column}** 各类别的占比情况")
                value_counts = filtered_data[column].value_counts()
                total_count = len(filtered_data)

                for idx, (cat, count) in enumerate(value_counts.items()):
                    percentage = (count / total_count) * 100
                    st.write(f"  - {cat}: {count} 个 ({percentage:.1f}%, {count / total_count:.3f})")

                # 饼图多样性指数
                proportions = value_counts / total_count
                diversity_index = -(proportions * np.log(proportions)).sum()
                max_diversity = np.log(len(value_counts))
                normalized_diversity = diversity_index / max_diversity if max_diversity != 0 else 0

                if normalized_diversity > 0.7:
                    st.write(f"  - 类别分布较为均匀，多样性高")
                elif normalized_diversity > 0.3:
                    st.write(f"  - 类别分布中等，存在一定多样性")
                else:
                    st.write(f"  - 类别分布不均匀，某一类别占主导地位")

            elif chart_type == "热力图":
                st.write("• 热力图展示了数据相关性矩阵")
                numeric_cols = filtered_data.select_dtypes(include=['float64', 'int64']).columns
                if len(numeric_cols) >= 2:
                    corr_matrix = filtered_data[numeric_cols].corr()

                    # 计算整体相关性特征
                    abs_corr_values = corr_matrix.abs().values
                    upper_triangle_indices = np.triu_indices_from(abs_corr_values, k=1)
                    upper_triangle_values = abs_corr_values[upper_triangle_indices]

                    if len(upper_triangle_values) > 0:
                        avg_corr = np.mean(upper_triangle_values)
                        max_corr = np.max(upper_triangle_values)
                        min_corr = np.min(upper_triangle_values)

                        st.write(f"  - 平均相关系数: {avg_corr:.3f}")
                        st.write(f"  - 最强相关性: {max_corr:.3f}")
                        st.write(f"  - 最弱相关性: {min_corr:.3f}")

                    # 显示最高相关性对
                    corr_pairs = []
                    for i in range(len(corr_matrix.columns)):
                        for j in range(i + 1, len(corr_matrix.columns)):
                            corr_val = corr_matrix.iloc[i, j]
                            corr_pairs.append((corr_matrix.columns[i], corr_matrix.columns[j], corr_val, abs(corr_val)))

                    if corr_pairs:
                        max_corr_pair = max(corr_pairs, key=lambda x: x[3])
                        st.write(
                            f"  - 最强相关性: {max_corr_pair[0]} 与 {max_corr_pair[1]} (相关系数: {max_corr_pair[2]:.3f})")

                        # 农业相关解读
                        if ('temperature' in max_corr_pair[0].lower() or '温' in max_corr_pair[0].lower()) and \
                                ('humidity' in max_corr_pair[1].lower() or '湿' in max_corr_pair[1].lower()) or \
                                ('humidity' in max_corr_pair[0].lower() or '湿' in max_corr_pair[0].lower()) and \
                                ('temperature' in max_corr_pair[1].lower() or '温' in max_corr_pair[1].lower()):
                            if max_corr_pair[2] > 0:
                                st.write(f"    • 温湿度呈正相关，说明温度升高时湿度也倾向上升")
                            else:
                                st.write(f"    • 温湿度呈负相关，符合典型的蒸发型环境特征")

        with tab2:
            # 创建下载链接
            fig_large = go.Figure(fig)
            fig_large.update_layout(width=1200, height=800)

            # 将Plotly图表转换为JSON
            fig_json = json.dumps(fig_large, cls=plotly.utils.PlotlyJSONEncoder)

            # 添加图表说明
            with st.expander("📈 图表交互说明"):
                st.markdown("""
            **图表交互功能：**
            - **缩放**: 在图表上拖拽可缩放区域
            - **平移**: 按住Shift键并拖拽可平移视图
            - **图例**: 点击图例项可显示/隐藏对应数据系列
            - **导出**: 点击右上角相机图标可下载图表
            """)

            # 添加智能推荐
            if chart_type == "散点图" and x_column and y_column:
                corr = filtered_data[[x_column, y_column]].corr().iloc[0, 1]
            if abs(corr) > 0.7:
                st.success(f"💡 **智能洞察**: {x_column} 和 {y_column} 之间存在强相关性 (相关系数: {corr:.2f})")
            elif abs(corr) > 0.3:
                st.info(f"💡 **智能洞察**: {x_column} 和 {y_column} 之间存在中等相关性 (相关系数: {corr:.2f})")


# 函数：高级分析
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
            grouped_data_viz = utils_analysis_module().group_and_aggregate(data, group_column_viz, agg_column_viz,
                                                                           agg_function_viz)

            fig = px.bar(grouped_data_viz, x=group_column_viz, y=agg_column_viz,
                         title=f"{group_column_viz} 分组的 {agg_column_viz} {agg_function_viz}")
            st.plotly_chart(fig, use_container_width=True)


# 函数：使用说明
def show_instructions():
    """
    显示使用说明页面
    """
    from utils.instruction_manual import show_instructions as show_full_manual
    show_full_manual()


# 函数：用户管理
from utils.user_management import user_management  # 添加导入


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


# 函数：数据预测
def data_prediction():
    """显示数据预测页面，允许用户进行本地数据预测"""
    if not st.session_state.get('logged_in'):
        st.query_params.page = "login"
        return

    st.title("数据预测")

    # 使用预测模块的 UI 组件
    data_type, model_type, prediction_days, lstm_params, pred_mode = prepare_prediction_ui()
    
    # 默认使用单变量预测模式（向后兼容）
    if pred_mode is None or pred_mode == "单变量时间序列预测":
        model_mapping = {
            "Prophet+SARIMA(推荐)": "SARIMA",
            "纯 Prophet": "Prophet",
            "纯 SARIMA": "SARIMA",
            "LSTM": "LSTM",
            "Transformer": "Transformer"
        }
        actual_model_type = model_mapping.get(model_type, model_type)
    else:
        actual_model_type = "multivariate"

    if st.button("开始预测"):
        # 根据预测模式调用不同的处理函数
        if pred_mode == "多变量耦合预测":
            # 多变量预测模式
            st.info("🔬 多变量耦合预测 - 同时分析温度、湿度、光照的相互作用")
            log_operation(st.session_state['username'], "INFO", "多变量预测",
                          f"天数：{prediction_days}")
            progress_bar = st.progress(0)
            st.write("预测进度：获取多源环境数据中...")
                
            try:
                # 从数据库获取三种数据
                temp_data = session.query(models.AirTemperatureHumidity).order_by(
                    models.AirTemperatureHumidity.timestamp.desc()).limit(200).all()
                humid_data = session.query(models.AirTemperatureHumidity).order_by(
                    models.AirTemperatureHumidity.timestamp.desc()).limit(200).all()
                light_data = session.query(models.LightIntensity).order_by(
                    models.LightIntensity.timestamp.desc()).limit(200).all()
                    
                if not temp_data or not humid_data or not light_data:
                    st.error("❌ 数据库中没有足够的环境数据，无法进行多变量预测")
                    progress_bar.empty()
                    return
                    
                progress_bar.progress(33)
                st.write("预测进度：多变量模型训练中...")
                    
                # 调用多变量预测函数
                merged_df, rf_temp, rf_humid, feature_importance, explanation = multivariate_prediction(
                    temp_data, humid_data, light_data, prediction_days, lstm_params
                )
                    
                if merged_df is not None:
                    progress_bar.progress(66)
                    st.write("预测进度：生成可视化结果...")
                        
                    # 显示特征重要性
                    with st.expander("🔍 特征重要性分析", expanded=True):
                        st.markdown(explanation)
                        
                    # 显示多变量数据趋势
                    st.subheader("📊 多变量数据趋势")
                    fig = go.Figure()
                        
                    # 温度
                    fig.add_trace(go.Scatter(
                        x=merged_df.index,
                        y=merged_df['temperature'],
                        name='温度',
                        line=dict(color='red')
                    ))
                        
                    # 湿度
                    fig.add_trace(go.Scatter(
                        x=merged_df.index,
                        y=merged_df['humidity'],
                        name='湿度',
                        line=dict(color='blue'),
                        yaxis='y2'
                    ))
                        
                    # 光照 (归一化)
                    if 'light' in merged_df.columns and merged_df['light'].max() > 0:
                        normalized_light = merged_df['light'] / merged_df['light'].max() * 50
                        fig.add_trace(go.Scatter(
                            x=merged_df.index,
                            y=normalized_light,
                            name='光照 (归一化)',
                            line=dict(color='orange', dash='dash')
                        ))
                        
                    fig.update_layout(
                        title="温度、湿度、光照多维度趋势",
                        xaxis_title="时间",
                        yaxis_title="温度 (°C)",
                        yaxis2=dict(title="湿度 (%)", overlaying='y', side='right'),
                        hovermode='x unified'
                    )
                        
                    st.plotly_chart(fig, use_container_width=True)
                        
                    progress_bar.progress(100)
                    st.success("✅ 多变量分析完成！\n\n💡 **提示**: 基于随机森林模型的特征重要性结果，您可以了解各因素对预测目标的影响程度。")
                else:
                    st.warning("⚠️ 多变量预测失败，请检查数据质量")
                    progress_bar.empty()
                        
            except Exception as e:
                st.error(f"❌ 多变量预测出错：{str(e)}")
                import traceback
                st.code(traceback.format_exc())
                progress_bar.empty()
            
        else:
            # 单变量预测逻辑
            log_operation(st.session_state['username'], "INFO", "数据预测",
                          f"类型：{data_type} 模型：{model_type} 天数：{prediction_days}")
            progress_bar = st.progress(0)
            st.write("预测进度：数据准备中...")
        
            # 修改：使用清洗后的数据而不是直接从数据库读取
            if 'data' in st.session_state:
                # 从 session_state 获取清洗后的数据
                cleaned_data = st.session_state['data'].copy()
        
                # 根据选择的数据类型提取相应列的数据
                if data_type == "空气温度":
                    if 'temperature' in cleaned_data.columns:
                        data = [(row['timestamp'], row['temperature']) for _, row in cleaned_data.iterrows() if
                                'temperature' in row and not pd.isna(row['temperature'])]
                    else:
                        st.error("清洗后的数据中未找到温度列")
                        return
                elif data_type == "空气湿度":
                    if 'humidity' in cleaned_data.columns:
                        data = [(row['timestamp'], row['humidity']) for _, row in cleaned_data.iterrows() if
                                'humidity' in row and not pd.isna(row['humidity'])]
                    else:
                        st.error("清洗后的数据中未找到湿度列")
                        return
                elif data_type == "土壤湿度":
                    if 'soil_moisture' in cleaned_data.columns:
                        data = [(row['timestamp'], row['soil_moisture']) for _, row in cleaned_data.iterrows() if
                                'soil_moisture' in row and not pd.isna(row['soil_moisture'])]
                    else:
                        st.error("清洗后的数据中未找到土壤湿度列")
                        return
                else:
                    st.error("不支持的数据类型")
                    return
            else:
                # 如果没有清洗后的数据，则从数据库读取（保持向后兼容）
                data = get_historical_data(session, data_type)
        
            # 更新进度条
            progress_bar.progress(33)
            st.write("预测进度：模型训练中...")
        
            # 调用预测模块
            historical_data, forecast_data, model_explanation, rmse = perform_prediction(
                data, actual_model_type, prediction_days, lstm_params)
        
            # 显示结果
            show_prediction_results(historical_data, forecast_data, model_explanation, rmse, data_type)
        
            # 更新进度条
            progress_bar.progress(100)
            st.success("预测完成")


def ai_insights_analysis():
    """AI洞察分析页面，结合数据分析和预测结果进行智能解读"""
    if not st.session_state.get('logged_in'):
        st.query_params.page = "login"
        return

    st.title("🤖 AI洞察分析")
    st.caption("利用AI大模型对数据分析和预测结果进行智能解读和建议")

    # 初始化AI分析器
    if 'ai_analyzer' not in st.session_state:
        st.session_state.ai_analyzer = AIInsightsAnalyzer("qwen3:4b")

    analyzer = st.session_state.ai_analyzer

    # 检查模型可用性
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


# 函数：主函数
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

    # 修改: 使用新API获取页面参数
    page = st.query_params.get("page", "login")

    # 优化登录态处理逻辑
    if page in ["login", "register"] and st.session_state['logged_in']:
        st.query_params.page = "integrated_dashboard"
        st.rerun()

    # 新增：统一路由处理逻辑
    if page == "login":
        login(session, st)
    elif page == "register":
        register(session, st)
    elif page == "module_config":
        if st.session_state.get('role') == 'admin':
            show_module_config_ui(st.session_state['username'], True)
        else:
            st.error("仅管理员可以访问模块配置管理")
    elif page == "dashboard":
        from utils.dashboard import show_dashboard
        show_dashboard()
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
                        if 'page' in st.query_params:
                            st.session_state['previous_page'] = st.query_params['page']
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
                "debug_info": "调试信息",  # 添加调试信息页面映射
                "module_config": "模块配置管理"  # 添加模块配置管理页面映射
            }
            selected = page_to_menu_mapping.get(page, "控制面板")

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

            menu_options = [module[0] for module in enabled_modules]
            menu_icons = [module[1] for module in enabled_modules]

            # 确保当前选中的页面在菜单选项中
            if selected not in menu_options:
                selected = menu_options[0] if menu_options else "数据概览"

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
        from utils.integrated_dashboard import show_integrated_dashboard
        # 统一路由映射
        route_mapping = {
            "综合监控仪表板": show_integrated_dashboard,
            "数据概览": data_overview,
            "数据清洗": data_cleaning,
            "数据分析": data_analysis,
            "可视化": data_visualization,
            "高级分析": advanced_analysis,
            "本地数据预测": data_prediction,
            "AI洞察分析": ai_insights_analysis,

            "用户管理": lambda: user_management(session, st.session_state['username'], st.session_state['role']),
            "系统监控": lambda: system_monitoring(),
            "日志查看": lambda: show_log_viewer(),
            "数据备份": data_backup,
            "数据恢复": data_restore,
            "数据库同步": lambda: sync_databases_ui(),
            "自动化决策": lambda: show_decision_engine(session, st.session_state['username']),
            "调试信息": lambda: show_debug_info(st.session_state['username']),  # 添加调试信息路由
            "使用说明": show_instructions,
            "模块配置管理": lambda: show_module_config_ui(st.session_state['username'],
                                                          st.session_state.get('role') == 'admin')
        }

        # 执行路由跳转
        if selected in route_mapping:
            route_mapping[selected]()
        else:
            # 默认显示综合监控仪表板
            from utils.integrated_dashboard import show_integrated_dashboard
            show_integrated_dashboard()


def initialize_app():
    """
    初始化应用，预加载关键模块
    """
    # 这里可以添加任何需要在应用启动时执行的初始化代码
    pass


if __name__ == '__main__':
    main()
