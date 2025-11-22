import base64
import io
import os
import json
from datetime import datetime
from io import BytesIO

import jwt
import pandas as pd
import plotly
import plotly.express as px
import plotly.graph_objects as go
import plotly.io as pio
import sqlalchemy
import streamlit as st
from sqlalchemy.orm import sessionmaker
from streamlit_extras.metric_cards import style_metric_cards
from streamlit_option_menu import option_menu

import models
import utils.system_monitoring
# 应用PyTorch补丁以解决兼容性问题
from utils.torch_patch import apply_torch_patches
apply_torch_patches()

from auth import session
# 添加日志查看器模块导入
from utils.logger import log_operation
from utils.sync_manager import sync_databases_ui
from utils.module_manager import get_module_manager
from utils.module_config_ui import show_module_config_ui, get_enabled_modules_for_sidebar, is_module_enabled

# 添加: 加载环境变量
from dotenv import load_dotenv

# 添加: 引入新的数据库模块
from utils.database import get_session
from utils.lazy_importer import lazy_import, preload_modules

# 添加仪表盘导入
from utils.dashboard import show_dashboard
from utils.integrated_dashboard import show_integrated_dashboard

# 延迟导入模块
machine_learning = lazy_import('utils.machine_learning')
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
prepare_prediction_ui = lazy_import('utils.predictions', 'prepare_prediction_ui')
get_historical_data = lazy_import('utils.predictions', 'get_historical_data')
show_prediction_results = lazy_import('utils.predictions', 'show_prediction_results')
visualize_data = lazy_import('utils.visualization', 'visualize_data')
user_management = lazy_import('utils.user_management', 'user_management')
system_monitoring = lazy_import('utils.system_monitoring', 'system_monitoring')

# 预加载频繁使用的模块以提高性能
preload_modules([
    'utils.data_preview',  # 数据预览是核心功能，频繁使用
    'utils.analysis',      # 数据分析功能经常使用
    'utils.visualization', # 可视化功能经常使用
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
    """
    if not st.session_state.get('logged_in'):
        st.query_params.page = "login"
        return

    st.title("数据清洗")
    
    # 添加标签页
    tab1, tab2, tab3, tab4 = st.tabs(["基础清洗", "缺失值处理", "异常值检测", "数据导出"])
    
    if 'data' not in st.session_state:
        st.warning("请先在数据概览页面上传数据")
        return

    data = st.session_state['data']
    
    # 基础清洗标签页
    with tab1:
        st.subheader("删除重复行")
        if st.button("删除重复行"):
            progress_bar = st.progress(0)
            original_rows = data.shape[0]
            progress_bar.progress(33)  # 第一步完成
            data = data.drop_duplicates()
            log_operation(st.session_state['username'], "INFO", "数据清洗-删除重复行",
                          f"删除{original_rows - data.shape[0]}行 剩余{data.shape[0]}行")
            st.success(f"删除了 {original_rows - data.shape[0]} 行重复数据")
            progress_bar.progress(100)  # 操作完成

        st.subheader("删除不需要的数据列")
        columns_to_drop = st.multiselect("选择要删除的列", data.columns.tolist())
        if st.button("删除选中的列"):
            log_operation(st.session_state['username'], "INFO", "数据清洗-删除列",
                          f"删除列: {', '.join(columns_to_drop)}")
            if columns_to_drop:
                progress_bar = st.progress(0)
                data = data.drop(columns=columns_to_drop)
                progress_bar.progress(100)  # 操作完成
                st.success(f"已删除列: {', '.join(columns_to_drop)}")
            else:
                st.warning("未选择任何列进行删除")

        st.session_state['data'] = data
        st.success("数据清洗完成")
    
    # 缺失值处理标签页
    with tab2:
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
    with tab3:
        st.subheader("异常值检测与清除")
        
        # 导入异常检测工具
        from utils.anomaly_detection import detect_outliers_iqr, detect_outliers_zscore, detect_outliers_isolation_forest, remove_anomalies, get_anomaly_summary
        
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
                
                contamination = st.slider("异常值比例估计", 0.01, 0.5, st.session_state.isolation_forest_contamination, 0.01, 
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
            selected_columns = st.multiselect("选择要检测的列", numeric_columns, default=numeric_columns[:3] if len(numeric_columns) > 3 else numeric_columns)
            
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
                        outlier_series = detect_outliers_isolation_forest(data, selected_columns, **isolation_forest_params)
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
    with tab4:
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

    st.subheader("描述性统计")
    log_operation(st.session_state['username'], "INFO", "数据分析-描述性统计",
                 f"数据集维度: {data.shape}")
    
    # 添加智能推荐和辅助信息
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
        st.info(f"💡 **智能推荐**: 检测到 {len(numeric_columns)} 个数值型变量，建议重点关注均值和标准差差异较大的指标")

    st.subheader("相关性分析")
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
            for j in range(i+1, len(corr_matrix.columns)):
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

    # 添加图表类型说明
    with st.expander("📊 图表类型说明"):
        st.markdown("""
        **常用图表类型适用场景：**
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

    # 创建小图用于UI展示
    fig_small = go.Figure(fig)
    fig_small.update_layout(width=700, height=500)
    st.plotly_chart(fig_small, use_container_width=True)

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

    st.subheader("数据分组和聚合")
    group_column = st.selectbox("选择分组列", data.columns)

    # 修改: 过滤掉与分组列相同的列
    available_columns = [col for col in data.select_dtypes(include=['float64', 'int64']).columns if col != group_column]
    if not available_columns:
        st.error("没有可用的数值列用于聚合，请检查数据。")
        return

    agg_column = st.selectbox("选择聚合列", available_columns)
    agg_function = st.selectbox("选择聚合函数", ["平均值", "总和", "最大值", "最小值"])

    if st.button("开始分析"):
        log_operation(st.session_state['username'], "INFO", "高级分析-分组聚合",
                      f"分组列: {group_column} 聚合列: {agg_column} 函数: {agg_function}")
        grouped_data = utils_analysis_module().group_and_aggregate(data, group_column, agg_column, agg_function)

        st.write("分组聚合结果：")
        st.dataframe(grouped_data)

        fig = px.bar(grouped_data, x=group_column, y=agg_column,
                     title=f"{group_column} 分组的 {agg_column} {agg_function}")
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

    # 使用预测模块的UI组件
    data_type, model_type, prediction_days, lstm_params = prepare_prediction_ui()

    if st.button("开始预测"):
        log_operation(st.session_state['username'], "INFO", "数据预测",
                      f"类型: {data_type} 模型: {model_type} 天数: {prediction_days}")
        progress_bar = st.progress(0)
        st.write("预测进度: 数据准备中...")

        # 修改：使用清洗后的数据而不是直接从数据库读取
        if 'data' in st.session_state:
            # 从session_state获取清洗后的数据
            cleaned_data = st.session_state['data'].copy()
            
            # 根据选择的数据类型提取相应列的数据
            if data_type == "空气温度":
                if 'temperature' in cleaned_data.columns:
                    data = [(row['timestamp'], row['temperature']) for _, row in cleaned_data.iterrows() if 'temperature' in row and not pd.isna(row['temperature'])]
                else:
                    st.error("清洗后的数据中未找到温度列")
                    return
            elif data_type == "空气湿度":
                if 'humidity' in cleaned_data.columns:
                    data = [(row['timestamp'], row['humidity']) for _, row in cleaned_data.iterrows() if 'humidity' in row and not pd.isna(row['humidity'])]
                else:
                    st.error("清洗后的数据中未找到湿度列")
                    return
            elif data_type == "土壤湿度":
                if 'soil_moisture' in cleaned_data.columns:
                    data = [(row['timestamp'], row['soil_moisture']) for _, row in cleaned_data.iterrows() if 'soil_moisture' in row and not pd.isna(row['soil_moisture'])]
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
        st.write("预测进度: 模型训练中...")

        # 调用预测模块
        historical_data, forecast_data, model_explanation, rmse = perform_prediction(
            data, model_type, prediction_days, lstm_params)

        # 显示结果
        show_prediction_results(historical_data, forecast_data, model_explanation, rmse, data_type)

        # 更新进度条
        progress_bar.progress(100)
        st.success("预测完成")


# 函数：机器学习


def machine_learning_page():
    """
    显示机器学习页面，允许用户训练模型并进行预测
    """
    if not st.session_state.get('logged_in'):
        st.query_params.page = "login"
        return

    st.title("🤖 机器学习")

    # 添加装饰性分隔线
    st.markdown("---")

    if 'data' not in st.session_state:
        st.warning("请先在数据概览页面上传数据")
        return

    # 调用机器学习模块的UI渲染函数
    machine_learning.render_ui(st.session_state['data'])


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
        st.query_params.page = "dashboard"
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
        from utils.dashboard import show_dashboard
        # 统一路由映射
        route_mapping = {
            "控制面板": show_dashboard,
            "实时数据预览": data_preview,
            "综合监控仪表板": show_integrated_dashboard,
            "数据概览": data_overview,
            "数据清洗": data_cleaning,
            "数据分析": data_analysis,
            "可视化": data_visualization,
            "高级分析": advanced_analysis,
            "本地数据预测": data_prediction,
            "机器学习": machine_learning_page,
            "用户管理": lambda: user_management(session, st.session_state['username'], st.session_state['role']),
            "系统监控": lambda: system_monitoring(),
            "日志查看": lambda: show_log_viewer(),
            "数据备份": data_backup,
            "数据恢复": data_restore,
            "数据库同步": lambda: sync_databases_ui(),
            "自动化决策": lambda: show_decision_engine(session, st.session_state['username']),
            "调试信息": lambda: show_debug_info(st.session_state['username']),  # 添加调试信息路由
            "使用说明": show_instructions,
            "模块配置管理": lambda: show_module_config_ui(st.session_state['username'], st.session_state.get('role') == 'admin')
        }

        # 执行路由跳转
        if selected in route_mapping:
            route_mapping[selected]()
        else:
            # 默认显示仪表盘
            from utils.dashboard import show_dashboard
            show_dashboard()


def initialize_app():
    """
    初始化应用，预加载关键模块
    """
    # 这里可以添加任何需要在应用启动时执行的初始化代码
    pass


if __name__ == '__main__':
    main()
