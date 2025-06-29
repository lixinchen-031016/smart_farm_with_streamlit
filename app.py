import base64
import io
import json
from datetime import datetime
from io import BytesIO

import bcrypt  # 添加: 引入bcrypt库
import jwt
import pandas as pd
import plotly
import plotly.express as px
import plotly.graph_objects as go
import plotly.io as pio
import sqlalchemy
import streamlit as st
import numpy
from openai import OpenAI, APITimeoutError  # 修改: 引入超时异常类
from sqlalchemy.orm import sessionmaker
from streamlit_extras.metric_cards import style_metric_cards
from streamlit_option_menu import option_menu

import models
import utils.system_monitoring
from utils import machine_learning
from utils.backup import restore_data, backup_data
from utils.data_preview import render_header, render_data_metrics
from utils.logger import log_operation

# 添加日志查看器模块导入
from utils.log_viewer import show_log_viewer

# 创建基类
Base = sqlalchemy.orm.declarative_base()

import os
from dotenv import load_dotenv

# 添加: 加载环境变量
load_dotenv()
# 添加: 引入新的数据库模块
from utils.database import get_session

# 替换: 使用get_session()方法获取会话对象
session = get_session()
# 创建OpenAI客户端
client = OpenAI(
    api_key=os.getenv('OPENAI_API_KEY'),
    base_url=os.getenv('OPENAI_BASE_URL'),
)

from auth import login, register  # 导入登录和注册函数
import utils.analysis  # 导入新的数据分析模块
from utils.predictions import perform_prediction  # 导入预测模块
from utils.visualization import visualize_data  # 导入可视化模块

from utils.data_operations import fetch_data_in_bulk


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

    render_header()
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
            st.session_state['data'] = df

    elif data_source == "上传文件":
        uploaded_file = st.file_uploader("选择文件", type=["csv", "xlsx", "xls", "json"])

        if uploaded_file is not None:
            data = read_file(uploaded_file)
            log_operation(st.session_state['username'], "INFO", "数据概览-文件上传",
                         f"文件名: {uploaded_file.name} 类型: {uploaded_file.type} 记录数: {len(data)}")
            if data is not None:
                # 新增: 确保timestamp列类型正确
                if 'timestamp' in data.columns:
                    data['timestamp'] = pd.to_datetime(data['timestamp'], errors='coerce')
                st.session_state['data'] = data

    # 确保数据展示和导出逻辑兼容两种数据读取方式
    if 'data' in st.session_state:
        data = st.session_state['data']

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
        st.dataframe(data.dtypes)

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
    if 'data' not in st.session_state:
        st.warning("请先在数据概览页面上传数据")
        return

    data = st.session_state['data']

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

    st.subheader("处理缺失值")
    missing_columns = data.columns[data.isnull().any()].tolist()
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

    # 拖拽式数据列映射功能
    st.subheader("拖拽式数据列映射")
    columns = data.columns.tolist()
    reordered_columns = st.columns(len(columns))
    for i, col in enumerate(columns):
        with reordered_columns[i]:
            st.write(col)
            if st.button(f"拖拽 {col}", key=f"drag_{col}"):
                columns.remove(col)
                columns.insert(0, col)  # 将拖拽的列移到第一位
    data = data[columns]  # 更新数据列顺序

    st.session_state['data'] = data
    st.success("数据清洗完成")

    # 添加交互式数据编辑功能
    st.subheader("交互式数据编辑")
    if st.button("保存编辑"):
        progress_bar = st.progress(0)
        edited_df = st.data_editor(st.session_state['data'])
        edited_df['timestamp'] = pd.to_datetime(edited_df['timestamp'], errors='coerce')
        st.session_state['data'] = edited_df
        progress_bar.progress(100)  # 操作完成
        st.success("数据编辑已保存")

    # 新增: 数据导出功能
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
    log_operation(st.session_state['username'],  "INFO", "数据分析-描述性统计",
                 f"数据集维度: {data.shape}")
    st.dataframe(utils.analysis.describe_data(data))

    st.subheader("相关性分析")
    numeric_columns = data.select_dtypes(include=['float64', 'int64']).columns
    if len(numeric_columns) < 2:
        st.warning("数据集中数值列不足两列，无法进行相关性分析。")
    else:
        corr_matrix = utils.analysis.calculate_correlation(data)
        fig = px.imshow(corr_matrix, text_auto=True, aspect="auto", color_continuous_scale='RdBu_r', zmin=-1, zmax=1,
                        labels=dict(color="相关系数"))
        fig.update_traces(text=corr_matrix.round(2), texttemplate="%{text}")
        st.plotly_chart(fig, use_container_width=True)


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

    # 设置统一的主题
    pio.templates.default = "plotly_white"
    color_sequence = px.colors.qualitative.Plotly
    
    chart_type = st.selectbox("选择图表类型", ["散点图", "线图", "柱状图", "箱线图", "直方图", "饼图", "热力图"])

    numeric_columns = filtered_data.select_dtypes(include=['float64', 'int64']).columns
    categorical_columns = filtered_data.select_dtypes(include=['object']).columns

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

    # 创建下载链接
    b64 = base64.b64encode(fig_json.encode()).decode()
    href = f'<a href="data:application/json;base64,{b64}" download="chart.json">下载图表数据 (JSON格式)</a>'
    log_operation(st.session_state['username'], "INFO", "数据可视化-图表导出", 
                 f"图表类型: {chart_type} 文件名: chart.json")
    st.markdown(href, unsafe_allow_html=True)

    # 添加说明
    st.markdown("""
    下载的JSON文件可以在 [Plotly Chart Studio](https://chart-studio.plotly.com/create/) 中导入以查看和编辑图表。
    或者，您可以使用Python的Plotly库来加载和显示这个JSON文件。
    """)


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
        grouped_data = utils.analysis.group_and_aggregate(data, group_column, agg_column, agg_function)

        st.write("分组聚合结果：")
        st.dataframe(grouped_data)

        fig = px.bar(grouped_data, x=group_column, y=agg_column, title=f"{group_column} 分组的 {agg_column} {agg_function}")
        st.plotly_chart(fig, use_container_width=True)


# 函数：使用说明
def show_instructions():
    """
    显示使用说明页面
    """
    from utils.instruction_manual import show_instructions as show_full_manual
    show_full_manual()


# 函数：用户管理
def user_management():
    """
    显示用户管理页面，允许管理员添加、编辑和删除用户
    """
    if not st.session_state.get('logged_in') or st.session_state['role'] != 'admin':
        st.query_params.page = "login"
        return

    st.title("用户管理")

    # 添加用户
    st.header("添加用户")
    new_username = st.text_input("新用户名", key="new_username")
    new_password = st.text_input("新密码", type="password", key="new_password")
    new_role = st.selectbox("角色", ["user", "admin"], key="new_role")
    if st.button("添加用户"):
        existing_user = session.query(models.User).filter_by(username=new_username).first()
        if existing_user:
            st.error("用户名已存在")
        else:
            hashed_password = bcrypt.hashpw(new_password.encode('utf-8'), bcrypt.gensalt())
            new_user = models.User(username=new_username, password=hashed_password.decode('utf-8'),
                                   last_login_time=datetime.now(), role=new_role)
            session.add(new_user)
            session.commit()
            log_operation(st.session_state['username'], 'INFO',"添加用户", f"添加用户 {new_username}")
            st.success("用户添加成功")

    # 用户列表
    st.header("用户列表")
    users = session.query(models.User).all()
    user_data = [(user.id, user.username, user.role) for user in users]
    df = pd.DataFrame(user_data, columns=['ID', '用户名', '角色'])
    st.dataframe(df)

    # 编辑和删除用户
    user_id = st.number_input("输入要编辑或删除的用户ID", min_value=1, step=1, key="user_id")
    action = st.selectbox("选择操作", ["编辑", "删除"], key="action_selectbox")
    if action == "编辑":
        user = session.query(models.User).filter_by(id=user_id).first()
        if user:
            new_username = st.text_input("新用户名", value=user.username, key="edit_username")
            new_role = st.selectbox("角色", ["user", "admin"], index=["user", "admin"].index(user.role),
                                    key="edit_role_selectbox")
            if st.button("保存更改"):
                user.username = new_username
                user.role = new_role
                session.commit()
                log_operation(st.session_state['username'], "INFO","编辑用户", f"编辑用户 {user.username}")
                st.success("用户信息已更新")
        else:
            st.error("用户不存在")
    elif action == "删除":
        if st.button("确认删除"):
            user = session.query(models.User).filter_by(id=user_id).first()
            if user:
                session.delete(user)
                session.commit()
                log_operation(st.session_state['username'], 'WARING',"删除用户", f"删除用户 {user.username}")
                st.success("用户已删除")
            else:
                st.error("用户不存在")

    # 新增: 修改用户密码功能
    st.header("修改用户密码")
    password_user_id = st.number_input("输入要修改密码的用户ID", min_value=1, step=1, key="password_user_id")
    new_password = st.text_input("新密码", type="password", key="password_new_password")
    confirm_password = st.text_input("确认新密码", type="password", key="password_confirm_password")
    if st.button("修改密码"):
        log_operation(st.session_state['username'], "INFO","用户管理-修改密码",
                     f"修改用户ID: {password_user_id} 的密码")
        user = session.query(models.User).filter_by(id=password_user_id).first()
        if user:
            if new_password != confirm_password:
                st.error("两次输入的密码不一致")
            else:
                hashed_password = bcrypt.hashpw(new_password.encode('utf-8'), bcrypt.gensalt())
                user.password = hashed_password.decode('utf-8')
                session.commit()
                log_operation(st.session_state['username'], 'WARING',"修改用户密码",
                              f"修改用户 {user.username} 的密码")
                st.success("密码修改成功")
        else:
            st.error("用户不存在")


# 函数：系统监控
def system_monitoring():
    """
    显示系统监控页面，实时查看服务器资源使用情况
    """
    utils.system_monitoring.system_monitoring()


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
        log_operation(st.session_state['username'], "INFO","数据备份",
                     f"时间范围: {start_time}至{end_time}")
        # 调用 utils/backup.py 中的备份函数
        zip_buffer = backup_data(session, start_time, end_time)

        # 提供下载链接（修改为下载压缩文件）
        st.download_button(
            label="下载备份文件",
            data=zip_buffer,
            file_name='backup.zip',
            mime='application/zip',
        )

        st.success("数据已备份并加密")


# 函数：数据恢复
def data_restore():
    """
    显示数据恢复页面，允许管理员恢复备份的数据
    """
    if not st.session_state.get('logged_in') or st.session_state['role'] != 'admin':
        st.query_params.page = "login"
        return

    st.title("数据恢复")

    # 修改: 增加SQL文件和密钥文件上传功能
    uploaded_sql_file = st.file_uploader("选择加密的SQL备份文件", type=["encrypted"])
    uploaded_key_file = st.file_uploader("选择密钥文件", type=["txt"])

    if uploaded_sql_file is not None and uploaded_key_file is not None:
        if st.button("恢复数据"):
            try:
                # 读取密钥文件内容
                key = uploaded_key_file.read().decode('utf-8').strip()
                if not key:
                    raise ValueError("密钥文件为空或无效")
                log_operation(st.session_state['username'], "INFO", "数据恢复失败",
                              f"文件: {uploaded_key_file}")
                # 调用 utils/backup.py 中的恢复函数
                restore_data(uploaded_sql_file, key)
                log_operation(st.session_state['username'], "INFO","数据恢复",
                             f"文件: {uploaded_sql_file.name}")
                st.success("数据已恢复")
            except Exception as e:
                st.error(f"恢复数据时出错: {e}")
                log_operation(st.session_state['username'], "ERROR", "数据恢复失败",
                              f"文件: {uploaded_sql_file.name}")


# 函数：数据预测
def data_prediction():
    """
    显示数据预测页面，允许用户进行本地数据预测
    """
    if not st.session_state.get('logged_in'):
        st.query_params.page = "login"
        return

    st.title("数据预测")

    # 选择预测的数据类型
    data_type = st.selectbox("选择预测的数据类型", ["空气温度", "空气湿度", "土壤湿度", "光照强度"])
    # 修改: 添加混合预测选项
    model_type = st.selectbox("选择预测模型", ["ARIMA", "SARIMA", "LSTM", "混合预测(SARIMA+LSTM)"])
    prediction_days = st.number_input("预测天数", min_value=1, max_value=30, value=7)

    # LSTM参数配置面板
    lstm_params = {}
    # 修改: 当选择混合预测时也需要显示LSTM参数
    if model_type == "LSTM" or model_type == "混合预测(SARIMA+LSTM)":
        with st.expander("LSTM参数配置"):
            lstm_params['look_back'] = st.slider("时间窗口大小", 1, 30, 7, 
                help="模型观察的历史数据点数")
            lstm_params['epochs'] = st.slider("训练轮次", 10, 200, 50)
            lstm_params['batch_size'] = st.slider("批次大小", 8, 64, 16)
            lstm_params['units'] = st.slider("LSTM单元数", 16, 128, 50)

    if st.button("开始预测"):
        log_operation(st.session_state['username'], "INFO","数据预测",
                     f"类型: {data_type} 模型: {model_type} 天数: {prediction_days}")
        progress_bar = st.progress(0)
        st.write("预测进度: 数据准备中...")

        # 获取历史数据
        if data_type == "空气温度":
            query = session.query(models.AirTemperatureHumidity.timestamp,
                                  models.AirTemperatureHumidity.temperature).order_by(
                models.AirTemperatureHumidity.timestamp)
        elif data_type == "空气湿度":
            query = session.query(models.AirTemperatureHumidity.timestamp,
                                  models.AirTemperatureHumidity.humidity).order_by(
                models.AirTemperatureHumidity.timestamp)
        elif data_type == "土壤湿度":
            query = session.query(models.SoilMoisture.timestamp, models.SoilMoisture.value).order_by(
                models.SoilMoisture.timestamp)
        elif data_type == "光照强度":
            query = session.query(models.LightIntensity.timestamp, models.LightIntensity.value).order_by(
                models.LightIntensity.timestamp)

        data = query.all()

        # 更新进度条
        progress_bar.progress(33)
        st.write("预测进度: 模型训练中...")

        # 调用预测模块
        # 修改: 接收额外的rmse返回值
        historical_data, forecast_data, model_explanation, rmse = perform_prediction( 
            data, model_type, prediction_days, lstm_params)

        # 显示模型训练解释
        if model_explanation:
            with st.expander("模型训练说明", expanded=True):
                st.markdown(model_explanation)
                
                # 新增: 显示RMSE指标
                st.markdown(f"**模型评价指标:**")
                col1, col2 = st.columns(2)
                with col1:
                    st.metric("RMSE (均方根误差)", f"{rmse:.4f}")
                with col2:
                    st.markdown("RMSE值越小表示模型预测精度越高")

        # 生成预测结果图表
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=historical_data.index, y=historical_data['value'], mode='lines', name='历史数据'))
        fig.add_trace(go.Scatter(x=forecast_data['timestamp'], y=forecast_data['value'], mode='lines', name='预测数据'))
        fig.update_layout(
            title=f"{data_type} 预测结果",
            xaxis_title="时间",
            yaxis_title="值",
            legend_title="数据类型"
        )
        st.plotly_chart(fig, use_container_width=True)

        # 更新进度条
        progress_bar.progress(100)
        st.success("预测完成")
        
        # 新增: 显示预测结果评价卡片
        st.subheader("预测结果评价")
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("预测天数", prediction_days)
        with col2:
            st.metric("历史数据量", len(historical_data))
        with col3:
            st.metric("模型精度 (RMSE)", f"{rmse:.4f}", 
                     delta="优" if rmse < 1.0 else "良" if rmse < 2.5 else "一般",
                     delta_color="inverse")

# 函数：AI数据处理
def ai_data_analysis_and_prediction():
    """
    显示AI数据处理页面，允许用户使用Qwen大模型进行智能数据分析和预测
    """
    st.title("AI数据处理")

    # 初始化聊天记录（如果未初始化）
    if 'chat_history' not in st.session_state:
        st.session_state.chat_history = []

    # 添加选项以选择数据来源
    data_source = st.radio("选择数据来源", ["使用数据概览上传的数据", "在此功能上传新数据"], key="ai_data_source")

    if data_source == "使用数据概览上传的数据":
        if 'data' not in st.session_state:
            st.warning("请先在数据概览页面上传数据")
            return
        data = st.session_state['data']
        st.success("已加载数据概览页面上传的数据")
    else:
        uploaded_file = st.file_uploader("选择文件", type=["csv", "xlsx", "xls", "json"], key="ai_file_uploader")
        if uploaded_file is not None:
            data = read_file(uploaded_file)
            if data is None:
                return
            st.success("文件读取成功")
        else:
            st.warning("请上传文件以继续")
            return

    # 显示历史聊天记录
    for chat in st.session_state.chat_history:
        with st.chat_message("user"):
            st.write(chat["user"])
        with st.chat_message("assistant"):
            st.write(chat["assistant"])

    # 用户输入部分
    user_message = st.chat_input("请输入您的问题或指令...", key="ai_chat_input")

    if user_message:
        log_operation(st.session_state['username'],"INFO", "AI数据分析",
                     f"问题: {user_message} 数据量: {len(data)}条")
        # 构建包含历史对话的messages
        messages = [
            {'role': 'system', 'content': 'You are a helpful assistant.'}
        ]

        # 添加历史对话
        for chat in st.session_state.chat_history:
            messages.append({'role': 'user', 'content': chat["user"]})
            messages.append({'role': 'assistant', 'content': chat["assistant"]})

        # 添加当前用户消息和数据
        data_json = data.to_json(orient='records')
        current_message = f"{user_message}\n数据如下：\n{data_json}"
        messages.append({'role': 'user', 'content': current_message})

        try:
            # 修改: 增加超时参数(30秒)
            completion = client.chat.completions.create(
                model=os.getenv("LLM_MODEL"),
                messages=messages,
                timeout=30.0  # 新增: 设置30秒超时
            )
        except APITimeoutError:
            # 新增: 处理超时异常
            st.error("AI请求超时，请稍后再试或简化问题")
            log_operation(st.session_state['username'], "ERROR", "AI数据分析-请求超时",
                         f"问题: {user_message}")
            return
        except Exception as e:
            # 新增: 处理其他异常
            st.error(f"AI处理出错: {str(e)}")
            log_operation(st.session_state['username'], "ERROR", "AI数据分析-异常",
                         f"问题: {user_message} 错误: {str(e)}")
            return

        # 解析响应
        response = completion.model_dump_json()
        response_data = json.loads(response)
        analysis = response_data.get('choices', [{}])[0].get('message', {}).get('content', '')

        # 添加到聊天记录
        st.session_state.chat_history.append({
            "user": user_message,
            "assistant": analysis
        })

        # 显示当前回复
        with st.chat_message("assistant"):
            st.write(analysis)
            log_operation(st.session_state['username'], "INFO","AI数据分析-问题处理",
                         f"问题: {user_message} 回复: {analysis}")

    # 导出聊天记录
    export_format = st.radio("选择导出格式", ["JSON", "Text"], key="export_format")
    if st.button("导出聊天记录"):
        log_operation(st.session_state['username'], "INFO","AI数据分析-聊天记录导出",
                     f"导出格式: {export_format} 记录数: {len(st.session_state.chat_history)}")
        if export_format == "JSON":
            content = json.dumps(st.session_state.chat_history, ensure_ascii=False, indent=2)
            file_name = "chat_history.json"
            mime_type = "application/json"
        else:
            content = "\n".join([
                f"用户: {chat['user']}\nAI回复: {chat['assistant']}"
                for chat in st.session_state.chat_history
            ])
            file_name = "chat_history.txt"
            mime_type = "text/plain"

        st.download_button(
            label="下载聊天记录",
            data=content.encode("utf-8"),
            file_name=file_name,
            mime=mime_type
        )


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
        if st.session_state['role'] == 'admin':
            st.query_params.page = "user_management"
        else:
            st.query_params.page = "data_preview"
        st.rerun()

    # 新增：统一路由处理逻辑
    if page == "login":
        login(session, st)
    elif page == "register":
        register(session, st)
    else:
        # 重构侧边栏菜单逻辑
        with st.sidebar:
            # 新增：根据当前页面自动选中对应菜单项
            page_to_menu_mapping = {
                "data_preview": "实时数据预览",
                "data_overview": "数据概览",
                "data_cleaning": "数据清洗",
                "data_analysis": "数据分析",
                "data_visualization": "可视化",
                "advanced_analysis": "高级分析",
                #"ai_data_analysis": "AI数据分析",
                "data_prediction": "本地数据预测",
                "user_management": "用户管理",
                "system_monitoring": "系统监控",
                "data_backup": "数据备份",
                "data_restore": "数据恢复",
                "log_viewer": "日志查看",
                "use_instruction": "使用说明"
            }
            selected = page_to_menu_mapping.get(page, "数据概览")

            # 修改后的菜单配置逻辑
            if st.session_state.get('role') == 'admin':
                menu_options = [
                    "实时数据预览", "数据概览", "数据清洗", "数据分析", "可视化",
                    "高级分析", "本地数据预测", "机器学习", 
                    "用户管理", "系统监控", "日志查看", "数据备份", "数据恢复" ,"使用说明"

                ]
            else:
                menu_options = [
                    "实时数据预览", "数据概览", "数据清洗", "数据分析", "可视化",
                    "高级分析",  "本地数据预测", "机器学习","使用说明"
                ]

            selected = option_menu(
                menu_title="📚 功能菜单",
                options=menu_options,
                icons=["speedometer", "table", "brush", "bar-chart", "graph-up",
                       "gear", "robot", "cpu", "person",  # 新增: brain图标对应机器学习
                       "cloud-upload", "save", "arrow-counterclockwise",  "gear-fill","question-circle"],
                default_index=menu_options.index(selected) if selected in menu_options else 0,
                styles={
                    "container": {"padding": "5px"},
                    "icon": {"color": "#4CAF50", "font-size": "18px"},
                    "nav-link": {"font-size": "16px", "text-align": "left", "margin": "5px"},
                    "nav-link-selected": {"background-color": "#4CAF50", "font-weight": "normal"},
                }
            )

        # 统一路由映射
        route_mapping = {
            "实时数据预览": data_preview,
            "数据概览": data_overview,
            "数据清洗": data_cleaning,
            "数据分析": data_analysis,
            "可视化": data_visualization,
            "高级分析": advanced_analysis,
            "AI数据分析": ai_data_analysis_and_prediction,
            "本地数据预测": data_prediction,
            "机器学习": machine_learning_page,
            "用户管理": user_management,
            "系统监控": system_monitoring,
            # 修复日志查看功能映射
            "日志查看": show_log_viewer,  # 修改前: log_viewer_page
            "数据备份": data_backup,
            "数据恢复": data_restore,
            "使用说明": show_instructions
        }

        # 执行路由跳转
        if selected in route_mapping:
            route_mapping[selected]()
        else:
            st.error("无效的页面配置")

if __name__ == '__main__':
    main()
