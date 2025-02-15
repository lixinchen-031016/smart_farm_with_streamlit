import base64
import io
import json
from datetime import datetime
from io import BytesIO

import bcrypt  # 添加: 引入bcrypt库
import os
from openai import OpenAI  # 添加: 引入OpenAI库
import pandas as pd
import plotly
import plotly.express as px
import plotly.graph_objects as go
import plotly.io as pio
import psutil
import sqlalchemy
import streamlit as st
from plotly.colors import n_colors
from sqlalchemy import Column, Integer, Float, DateTime, String  # 修改: 将Binary替换为LargeBinary
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from streamlit_extras.metric_cards import style_metric_cards
from streamlit_option_menu import option_menu

# 创建基类
Base = sqlalchemy.orm.declarative_base()

class AirTemperatureHumidity(Base):
    __tablename__ = 'intelligent_farm_airtemperaturehumidity'  # 修改表名
    id = Column(Integer, primary_key=True)
    temperature = Column(Float)
    humidity = Column(Float)
    timestamp = Column(DateTime)

class SoilMoisture(Base):
    __tablename__ = 'intelligent_farm_soilmoisture'  # 修改表名
    id = Column(Integer, primary_key=True)
    value = Column(Float)
    timestamp = Column(DateTime)

class SoilNutrient(Base):
    __tablename__ = 'intelligent_farm_soilnutrient'  # 修改表名
    id = Column(Integer, primary_key=True)
    value = Column(Float)
    timestamp = Column(DateTime)

class LightIntensity(Base):
    __tablename__ = 'intelligent_farm_light_intensity'  # 添加表名
    id = Column(Integer, primary_key=True)
    value = Column(Float)
    timestamp = Column(DateTime)

class User(Base):
    __tablename__ = 'user'
    id = Column(Integer, primary_key=True, autoincrement=True)  # 修改: 设置id字段为自增
    username = Column(String(255), nullable=False)
    password = Column(String(255), nullable=False)
    last_login_time = Column(DateTime, nullable=False)
    role = Column(String(50), nullable=False, default='user')  # 添加: 用户角色字段

# MySQL数据库连接配置
engine = create_engine('mysql+pymysql://root:0000@db/intelligent_farm')
Session = sessionmaker(bind=engine)
session = Session()

# 创建OpenAI客户端
client = OpenAI(
    api_key="your_api_key",
    base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
)

def login():
    st.title("登录")
    username = st.text_input("用户名", key="login_username")  # 添加: 唯一key
    password = st.text_input("密码", type="password", key="login_password")  # 添加: 唯一key
    user_type = st.radio("选择登录类型", ["用户", "管理员"], index=0)  # 添加: 选择登录类型
    if st.button("登录"):
        user = session.query(User).filter_by(username=username).first()
        if user and bcrypt.checkpw(password.encode('utf-8'), user.password.encode('utf-8')):
            st.session_state['logged_in'] = True
            st.session_state['username'] = username
            st.session_state['role'] = user.role  # 添加: 存储用户角色
            user.last_login_time = datetime.now()
            session.commit()
            if user.role == 'admin':
                st.experimental_set_query_params(page="user_management")  # 添加: 管理员登录后跳转到用户管理页面
            else:
                st.experimental_set_query_params(page="data_preview")
        else:
            st.error("用户名或密码错误")
    
    if st.button("注册"):
        st.experimental_set_query_params(page="register")

def register():
    st.title("注册")
    username = st.text_input("用户名", key="register_username")  # 添加: 唯一key
    password = st.text_input("密码", type="password", key="register_password")  # 添加: 唯一key
    confirm_password = st.text_input("确认密码", type="password", key="confirm_password")  # 添加: 唯一key
    if st.button("注册"):
        if password != confirm_password:
            st.error("密码不一致")
        else:
            existing_user = session.query(User).filter_by(username=username).first()
            if existing_user:
                st.error("用户名已存在")
            else:
                hashed_password = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())  # 修改: 使用bcrypt加密密码
                new_user = User(username=username, password=hashed_password.decode('utf-8'), last_login_time=datetime.now())
                session.add(new_user)
                session.commit()
                st.success("注册成功，请登录")
                st.experimental_set_query_params(page="login")

def fetch_latest_data(session):
    air_temp_hum = session.query(AirTemperatureHumidity).order_by(AirTemperatureHumidity.timestamp.desc()).first()
    soil_moist = session.query(SoilMoisture).order_by(SoilMoisture.timestamp.desc()).first()
    soil_nutri = session.query(SoilNutrient).order_by(SoilNutrient.timestamp.desc()).first()
    light_intens = session.query(LightIntensity).order_by(LightIntensity.timestamp.desc()).first()  # 添加光照强度查询
    return air_temp_hum, soil_moist, soil_nutri, light_intens  # 添加光照强度返回值

def data_preview():
    if not st.session_state.get('logged_in'):
        st.experimental_set_query_params(page="login")
        return

    st.title("智能农场数据监控")

    # 添加更新数据按钮
    st.header("最新数据")
    if st.button("更新数据"):
        air_temp_hum, soil_moist, soil_nutri, light_intens = fetch_latest_data(session)  # 添加光照强度
        st.write(f"空气温度: {air_temp_hum.temperature} °C")
        st.write(f"空气湿度: {air_temp_hum.humidity} %")
        st.write(f"土壤湿度: {soil_moist.value} %")
        st.write(f"土壤无机盐含量: {soil_nutri.value}")
        st.write(f"光照强度: {light_intens.value}")  # 添加光照强度显示
        st.write(f"数据获取时间: {air_temp_hum.timestamp}")

    # 添加数据导出逻辑
    st.header("数据导出")
    export_format = st.selectbox("选择导出格式", ["CSV", "JSON", "Excel"])

    # 添加时间范围选择器
    start_time = st.date_input("选择开始时间")
    end_time = st.date_input("选择结束时间")

    if st.button("导出数据"):
        # 根据时间范围查询数据
        query = session.query(
            AirTemperatureHumidity.timestamp.label('timestamp'),
            AirTemperatureHumidity.temperature,
            AirTemperatureHumidity.humidity,
            SoilMoisture.value.label('soil_moisture'),
            SoilNutrient.value.label('soil_nutrient')
        ).outerjoin(
            SoilMoisture, AirTemperatureHumidity.timestamp == SoilMoisture.timestamp
        ).outerjoin(
            SoilNutrient, AirTemperatureHumidity.timestamp == SoilNutrient.timestamp
        ).filter(
            AirTemperatureHumidity.timestamp >= start_time,
            AirTemperatureHumidity.timestamp <= end_time
        ).order_by(
            AirTemperatureHumidity.timestamp
        )

        data = query.all()
        df = pd.DataFrame(data, columns=[
            'timestamp',
            'temperature',
            'humidity',
            'soil_moisture',
            'soil_nutrient'
        ])

        df['timestamp'] = pd.to_datetime(df['timestamp'])

        # 调用data-visualization-tool.py中的data_analysis函数
        st.session_state['data'] = df

        if export_format == "CSV":
            csv = df.to_csv(index=False)
            st.download_button(
                label="下载CSV文件",
                data=csv,
                file_name='data.csv',
                mime='text/csv',
            )
        elif export_format == "JSON":
            json_str = df.to_json(orient='records')
            st.download_button(
                label="下载JSON文件",
                data=json_str,
                file_name='data.json',
                mime='application/json',
            )
        elif export_format == "Excel":
            excel = io.BytesIO()
            df.to_excel(excel, index=False)
            excel.seek(0)
            st.download_button(
                label="下载Excel文件",
                data=excel,
                file_name='data.xlsx',
                mime='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            )

# 定义 read_file 函数
def read_file(uploaded_file):
    import pandas as pd

    if uploaded_file.type == "application/json":
        data = pd.read_json(uploaded_file)
    elif uploaded_file.type in ["text/csv", "application/vnd.ms-excel"]:
        data = pd.read_csv(uploaded_file)
    elif uploaded_file.type == "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet":
        data = pd.read_excel(uploaded_file)
    else:
        st.error("不支持的文件类型")
        return None

    return data

# 数据概览函数
def data_overview():
    if not st.session_state.get('logged_in'):
        st.experimental_set_query_params(page="login")
        return

    st.title("数据概览")
    uploaded_file = st.file_uploader("选择文件", type=["csv", "xlsx", "xls", "json"])

    if uploaded_file is not None:
        data = read_file(uploaded_file)
        if data is not None:
            st.success("文件读取成功")
            st.session_state['data'] = data

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
            export_format = st.radio("选择导出格式", ["CSV", "Excel"])
            if st.button("导出数据"):
                if export_format == "CSV":
                    csv = data.to_csv(index=False)
                    b64 = base64.b64encode(csv.encode()).decode()
                    href = f'<a href="data:file/csv;base64,{b64}" download="exported_data.csv">下载 CSV 文件</a>'
                else:
                    towrite = BytesIO()
                    data.to_excel(towrite, index=False, engine="openpyxl")
                    towrite.seek(0)
                    b64 = base64.b64encode(towrite.read()).decode()
                    href = f'<a href="data:application/vnd.openxmlformats-officedocument.spreadsheetml.sheet;base64,{b64}" download="exported_data.xlsx">下载 Excel 文件</a>'
                st.markdown(href, unsafe_allow_html=True)

# 数据清洗函数
def data_cleaning():
    if not st.session_state.get('logged_in'):
        st.experimental_set_query_params(page="login")
        return

    st.title("数据清洗")
    if 'data' not in st.session_state:
        st.warning("请先在数据概览页面上传数据")
        return

    data = st.session_state['data']

    st.subheader("删除重复行")
    if st.button("删除重复行"):
        original_rows = data.shape[0]
        data = data.drop_duplicates()
        st.success(f"删除了 {original_rows - data.shape[0]} 行重复数据")

    st.subheader("处理缺失值")
    missing_columns = data.columns[data.isnull().any()].tolist()
    for column in missing_columns:
        method = st.selectbox(f"选择处理 {column} 缺失值的方法", ["保持不变", "删除", "填充平均值", "填充中位数", "填充众数"])
        if method == "删除":
            data = data.dropna(subset=[column])
        elif method == "填充平均值":
            data[column].fillna(data[column].mean(), inplace=True)
        elif method == "填充中位数":
            data[column].fillna(data[column].median(), inplace=True)
        elif method == "填充众数":
            data[column].fillna(data[column].mode()[0], inplace=True)

    st.session_state['data'] = data
    st.success("数据清洗完成")

    # 添加交互式数据编辑功能
    st.subheader("交互式数据编辑")
    edited_df = st.data_editor(st.session_state['data'])
    if st.button("保存编辑"):
        st.session_state['data'] = edited_df
        st.success("数据编辑已保存")

# 数据分析函数
def data_analysis():
    if not st.session_state.get('logged_in'):
        st.experimental_set_query_params(page="login")
        return

    st.title("数据分析")
    if 'data' not in st.session_state:
        st.warning("请先在数据概览页面上传数据")
        return

    data = st.session_state['data']

    st.subheader("描述性统计")
    st.dataframe(data.describe())

    st.subheader("相关性分析")
    numeric_columns = data.select_dtypes(include=['float64', 'int64']).columns
    if len(numeric_columns) < 2:
        st.warning("数据集中数值列不足两列，无法进行相关性分析。")
    else:
        corr_matrix = data[numeric_columns].corr()
        fig = px.imshow(corr_matrix, text_auto=True, aspect="auto", color_continuous_scale='RdBu_r', zmin=-1, zmax=1, labels=dict(color="相关系数"))
        fig.update_traces(text=corr_matrix.round(2), texttemplate="%{text}")
        st.plotly_chart(fig, use_container_width=True)

# 数据可视化函数
def data_visualization():
    if not st.session_state.get('logged_in'):
        st.experimental_set_query_params(page="login")
        return

    st.title("数据可视化")
    if 'data' not in st.session_state:
        st.warning("请先在数据概览页面上传数据")
        return

    data = st.session_state['data']

    # 设置统一的主题
    pio.templates.default = "plotly_white"

    chart_type = st.selectbox("选择图表类型", ["散点图", "线图", "柱状图", "箱线图", "直方图", "饼图", "热力图"])

    numeric_columns = data.select_dtypes(include=['float64', 'int64']).columns
    categorical_columns = data.select_dtypes(include=['object']).columns

    if len(numeric_columns) == 0:
        st.warning("数据集中没有数值列，无法进行可视化。")
        return

    # 定义现代科技感的颜色方案
    color_scheme = n_colors('rgb(0, 122, 255)', 'rgb(10, 132, 255)', 6, colortype='rgb')

    x_column = None
    y_column = None
    column = None

    if chart_type in ["散点图", "线图", "柱状图"]:
        x_column = st.selectbox("选择X轴", data.columns)
        y_column = st.selectbox("选择Y轴", numeric_columns)
        color_column = st.selectbox("选择颜色列（可选）", ["无"] + list(categorical_columns))

        if chart_type == "散点图":
            fig = px.scatter(data, x=x_column, y=y_column, color=color_column if color_column != "无" else None,
                             color_discrete_sequence=color_scheme)
        elif chart_type == "线图":
            fig = px.line(data, x=x_column, y=y_column, color=color_column if color_column != "无" else None,
                          color_discrete_sequence=color_scheme)
        else:  # 柱状图
            fig = px.bar(data, x=x_column, y=y_column, color=color_column if color_column != "无" else None,
                         color_discrete_sequence=color_scheme)

    elif chart_type in ["箱线图", "直方图"]:
        column = st.selectbox("选择列", numeric_columns)
        if chart_type == "箱线图":
            fig = px.box(data, y=column, color_discrete_sequence=color_scheme)
        else:  # 直方图
            fig = px.histogram(data, x=column, nbins=30, marginal="box",
                               color_discrete_sequence=color_scheme)
            fig.update_traces(opacity=0.75)
            fig.update_layout(bargap=0.1)

    elif chart_type == "饼图":
        if len(categorical_columns) == 0:
            st.warning("数据集中没有分类列，无法创建饼图。")
            return
        column = st.selectbox("选择列", categorical_columns)
        value_counts = data[column].value_counts()
        fig = px.pie(values=value_counts.values, names=value_counts.index, title=f'{column} 的分布',
                     color_discrete_sequence=color_scheme)

    elif chart_type == "热力图":
        if len(numeric_columns) < 2:
            st.warning("数据集中数值列不足两列，无法创建热力图。")
            return
        corr_matrix = data[numeric_columns].corr()
        fig = px.imshow(corr_matrix,
                        text_auto=True,
                        aspect="auto",
                        color_continuous_scale='RdBu_r',  # 使用红蓝色阶
                        zmin=-1,
                        zmax=1,
                        labels=dict(color="相关系数"))
        fig.update_traces(text=corr_matrix.round(2), texttemplate="%{text}")
        fig.update_layout(coloraxis_colorbar=dict(
            title="相关系数",
            tickvals=[-1, -0.5, 0, 0.5, 1],
            ticktext=["-1", "-0.5", "0", "0.5", "1"]
        ))

    # 更新图表布局
    fig.update_layout(
        title={
            'text': f"{chart_type.capitalize()} - {y_column if chart_type in ['散点图', '线图', '柱状图'] else column if column else ''}",
            'y':0.95,
            'x':0.5,
            'xanchor': 'center',
            'yanchor': 'top',
            'font': dict(size=24, color='#1D3557')
        },
        xaxis_title=x_column if chart_type in ["散点图", "线图", "柱状图"] else column if column else '',
        yaxis_title=y_column if chart_type in ["散点图", "线图", "柱状图"] else "频率" if chart_type != "热力图" else '',
        legend_title="图例",
        font=dict(family="-apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen-Sans, Ubuntu, Cantarell, 'Helvetica Neue', sans-serif", size=14),
        hovermode="closest",
        plot_bgcolor='rgba(240, 240, 244, 0.8)',
        paper_bgcolor='rgba(240, 240, 244, 0.8)',
        xaxis=dict(showgrid=True, gridcolor='rgba(0, 122, 255, 0.1)'),
        yaxis=dict(showgrid=True, gridcolor='rgba(0, 122, 255, 0.1)')
    )

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
    st.markdown(href, unsafe_allow_html=True)

    # 添加说明
    st.markdown("""
    下载的JSON文件可以在 [Plotly Chart Studio](https://chart-studio.plotly.com/create/) 中导入以查看和编辑图表。
    或者，您可以使用Python的Plotly库来加载和显示这个JSON文件。
    """)

# 高级分析函数
def advanced_analysis():
    if not st.session_state.get('logged_in'):
        st.experimental_set_query_params(page="login")
        return

    st.title("高级分析")
    if 'data' not in st.session_state:
        st.warning("请先在数据概览页面上传数据")
        return

    data = st.session_state['data']

    st.subheader("数据分组和聚合")
    group_column = st.selectbox("选择分组列", data.columns)
    agg_column = st.selectbox("选择聚合列", data.select_dtypes(include=['float64', 'int64']).columns)
    agg_function = st.selectbox("选择聚合函数", ["平均值", "总和", "最大值", "最小值"])

    agg_dict = {"平均值": "mean", "总和": "sum", "最大值": "max", "最小值": "min"}
    grouped_data = data.groupby(group_column)[agg_column].agg(agg_dict[agg_function]).reset_index()

    st.write("分组聚合结果：")
    st.dataframe(grouped_data)

    fig = px.bar(grouped_data, x=group_column, y=agg_column, title=f"{group_column} 分组的 {agg_column} {agg_function}")
    st.plotly_chart(fig, use_container_width=True)

# 使用说明函数
def show_instructions():
    if not st.session_state.get('logged_in'):
        st.experimental_set_query_params(page="login")
        return

    st.title("使用说明")
    st.markdown("""
    1. **数据导入**：在"数据概览"页面上传您的 CSV、Excel 或 JSON 文件。
    2. **数据清洗**：使用"数据清洗"页面处理缺失值和删除重复行。
    3. **数据分析**：在"数据分析"页面查看描述性统计和相关性分析。
    4. **数据可视化**：使用"可视化"页面创建各种图表。
    5. **高级分析**：在"高级分析"页面进行更深入的数据探索。
    
    如需更多帮助，请参阅 [GitHub 仓库](https://github.com/lixinchen-031016/smart_farm_with_streamlit)。
    """)

def user_management():
    if not st.session_state.get('logged_in') or st.session_state['role'] != 'admin':
        st.experimental_set_query_params(page="login")
        return

    st.title("用户管理")

    # 添加用户
    st.header("添加用户")
    new_username = st.text_input("新用户名", key="new_username")  # 添加: 唯一key
    new_password = st.text_input("新密码", type="password", key="new_password")  # 添加: 唯一key
    new_role = st.selectbox("角色", ["user", "admin"])
    if st.button("添加用户"):
        existing_user = session.query(User).filter_by(username=new_username).first()
        if existing_user:
            st.error("用户名已存在")
        else:
            hashed_password = bcrypt.hashpw(new_password.encode('utf-8'), bcrypt.gensalt())
            new_user = User(username=new_username, password=hashed_password.decode('utf-8'), last_login_time=datetime.now(), role=new_role)
            session.add(new_user)
            session.commit()
            st.success("用户添加成功")

    # 用户列表
    st.header("用户列表")
    users = session.query(User).all()
    user_data = [(user.id, user.username, user.role) for user in users]
    df = pd.DataFrame(user_data, columns=['ID', '用户名', '角色'])
    st.dataframe(df)

    # 编辑和删除用户
    user_id = st.number_input("输入要编辑或删除的用户ID", min_value=1, step=1, key="user_id")  # 添加: 唯一key
    action = st.selectbox("选择操作", ["编辑", "删除"])
    if action == "编辑":
        user = session.query(User).filter_by(id=user_id).first()
        if user:
            new_username = st.text_input("新用户名", value=user.username, key="edit_username")  # 添加: 唯一key
            new_password = st.text_input("新密码", type="password", key="edit_password")  # 添加: 唯一key
            new_role = st.selectbox("角色", ["uesr", "admin"], index=["user", "admin"].index(user.role))
            if st.button("保存更改"):
                user.username = new_username
                if new_password:
                    user.password = bcrypt.hashpw(new_password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
                user.role = new_role
                session.commit()
                st.success("用户信息已更新")
        else:
            st.error("用户不存在")
    elif action == "删除":
        if st.button("确认删除"):
            user = session.query(User).filter_by(id=user_id).first()
            if user:
                session.delete(user)
                session.commit()
                st.success("用户已删除")
            else:
                st.error("用户不存在")

def system_monitoring():
    if not st.session_state.get('logged_in') or st.session_state['role'] != 'admin':
        st.experimental_set_query_params(page="login")
        return

    st.title("系统监控")
    st.write("服务器资源使用情况：")

    # 获取CPU使用情况
    cpu_usage = psutil.cpu_percent(interval=1)
    st.write(f"CPU 使用率: {cpu_usage}%")

    # 获取内存使用情况
    memory = psutil.virtual_memory()
    st.write(f"内存使用率: {memory.percent}%")
    st.write(f"已用内存: {memory.used / (1024 ** 3):.2f} GB")
    st.write(f"可用内存: {memory.available / (1024 ** 3):.2f} GB")

    # 获取磁盘使用情况
    disk = psutil.disk_usage('/')
    st.write(f"磁盘使用率: {disk.percent}%")
    st.write(f"已用磁盘空间: {disk.used / (1024 ** 3):.2f} GB")
    st.write(f"可用磁盘空间: {disk.free / (1024 ** 3):.2f} GB")


def data_backup():
    if not st.session_state.get('logged_in') or st.session_state['role'] != 'admin':
        st.experimental_set_query_params(page="login")
        return

    st.title("数据备份")

    # 添加开始和结束时间选择器
    start_time = st.date_input("选择开始时间")
    end_time = st.date_input("选择结束时间")

    if st.button("执行备份"):
        # 根据时间范围查询数据
        query = session.query(
            AirTemperatureHumidity.timestamp.label('timestamp'),
            AirTemperatureHumidity.temperature,
            AirTemperatureHumidity.humidity,
            SoilMoisture.value.label('soil_moisture'),
            SoilNutrient.value.label('soil_nutrient')
        ).outerjoin(
            SoilMoisture, AirTemperatureHumidity.timestamp == SoilMoisture.timestamp
        ).outerjoin(
            SoilNutrient, AirTemperatureHumidity.timestamp == SoilNutrient.timestamp
        ).filter(
            AirTemperatureHumidity.timestamp >= start_time,
            AirTemperatureHumidity.timestamp <= end_time
        ).order_by(
            AirTemperatureHumidity.timestamp
        )

        data = query.all()
        df = pd.DataFrame(data, columns=[
            'timestamp',
            'temperature',
            'humidity',
            'soil_moisture',
            'soil_nutrient'
        ])

        df['timestamp'] = pd.to_datetime(df['timestamp'])

        # 将数据导出为SQL文件
        sql_file = io.StringIO()
        for _, row in df.iterrows():
            sql_file.write(f"INSERT INTO intelligent_farm_airtemperaturehumidity (temperature, humidity, timestamp) VALUES ({row['temperature']}, {row['humidity']}, '{row['timestamp']}');\n")
            sql_file.write(f"INSERT INTO intelligent_farm_soilmoisture (value, timestamp) VALUES ({row['soil_moisture']}, '{row['timestamp']}');\n")
            sql_file.write(f"INSERT INTO intelligent_farm_soilnutrient (value, timestamp) VALUES ({row['soil_nutrient']}, '{row['timestamp']}');\n")
            sql_file.write(f"\n")
        sql_file.seek(0)

        # 将StringIO对象转换为字节流
        sql_bytes = sql_file.getvalue().encode('utf-8')

        # 提供下载链接
        st.download_button(
            label="下载SQL文件",
            data=sql_bytes,
            file_name='backup.sql',
            mime='application/sql',
        )

        st.success("数据已备份")

def data_restore():
    if not st.session_state.get('logged_in') or st.session_state['role'] != 'admin':
        st.experimental_set_query_params(page="login")
        return

    st.title("数据恢复")
    uploaded_file = st.file_uploader("选择备份文件", type=["sql"])
    if uploaded_file is not None:
        if st.button("恢复数据"):
            # 读取上传的SQL文件内容
            sql_script = uploaded_file.read().decode('utf-8')
            
            # 将SQL脚本拆分为单个SQL语句
            sql_statements = sql_script.split(';')
            
            # 执行SQL脚本
            try:
                with engine.connect() as connection:
                    for statement in sql_statements:
                        statement = statement.strip()
                        if statement:  # 确保语句不为空
                            # 检查并处理nan值
                            if 'nan' in statement:
                                # 删除包含nan的语句
                                continue
                            connection.execute(sqlalchemy.text(statement))
                st.success("数据已恢复")
            except Exception as e:
                st.error(f"恢复数据时出错: {e}")

def data_prediction():
    if not st.session_state.get('logged_in'):
        st.experimental_set_query_params(page="login")
        return

    st.title("数据预测")

    # 选择预测的数据类型
    data_type = st.selectbox("选择预测的数据类型", ["空气温度", "空气湿度", "土壤湿度"])

    # 选择预测模型
    model_type = st.selectbox("选择预测模型", ["ARIMA", "SARIMA"])  # 添加模型选择

    # 设置预测的时间范围
    prediction_days = st.number_input("预测天数", min_value=1, max_value=30, value=7)

    if st.button("开始预测"):
        # 获取历史数据
        if data_type == "空气温度":
            query = session.query(AirTemperatureHumidity.timestamp, AirTemperatureHumidity.temperature).order_by(AirTemperatureHumidity.timestamp)
        elif data_type == "空气湿度":
            query = session.query(AirTemperatureHumidity.timestamp, AirTemperatureHumidity.humidity).order_by(AirTemperatureHumidity.timestamp)
        elif data_type == "土壤湿度":
            query = session.query(SoilMoisture.timestamp, SoilMoisture.value).order_by(SoilMoisture.timestamp)

        data = query.all()
        df = pd.DataFrame(data, columns=['timestamp', 'value'])
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        df.set_index('timestamp', inplace=True)

        # 使用选择的模型进行预测
        if model_type == "ARIMA":
            from statsmodels.tsa.arima.model import ARIMA
            model = ARIMA(df['value'], order=(5,1,0))
        elif model_type == "SARIMA":
            from statsmodels.tsa.statespace.sarimax import SARIMAX
            model = SARIMAX(df['value'], order=(5,1,0), seasonal_order=(1,1,1,12))  # 示例季节性参数

        model_fit = model.fit()
        forecast = model_fit.forecast(steps=prediction_days)

        # 生成预测结果图表
        forecast_dates = pd.date_range(start=df.index[-1], periods=prediction_days+1, freq='D')[1:]
        forecast_df = pd.DataFrame({'timestamp': forecast_dates, 'value': forecast})

        fig = go.Figure()
        fig.add_trace(go.Scatter(x=df.index, y=df['value'], mode='lines', name='历史数据'))
        fig.add_trace(go.Scatter(x=forecast_df['timestamp'], y=forecast_df['value'], mode='lines', name='预测数据'))
        fig.update_layout(
            title=f"{data_type} 预测结果",
            xaxis_title="时间",
            yaxis_title="值",
            legend_title="数据类型"
        )
        st.plotly_chart(fig, use_container_width=True)

        st.success("预测完成")

def ai_data_analysis_and_prediction():
    if not st.session_state.get('logged_in'):
        st.experimental_set_query_params(page="login")
        return

    st.title("AI数据处理")
    uploaded_file = st.file_uploader("选择文件", type=["csv", "xlsx", "xls", "json"])

    if uploaded_file is not None:
        data = read_file(uploaded_file)
        if data is not None:
            st.success("文件读取成功")
            st.session_state['data'] = data

            # 使用 st.text_area 组件用于输入用户消息
            user_message = st.text_area("请输入上传数据相关的问题或指示：", key="user_message")

            # 调用Qwen2.5 API进行数据分析和预测
            if st.button("开始分析"):
                # 将数据转换为JSON格式
                data_json = data.to_json(orient='records')

                # 构建 messages 参数
                messages = [
                    {'role': 'system', 'content': 'You are a helpful assistant.'},
                    {'role': 'user', 'content': f'{user_message}\n数据如下：\n{data_json}'},
                ]

                # 调用API
                completion = client.chat.completions.create(
                    model="qwen2.5-14b-instruct-1m",
                    messages=messages,
                )

                # 解析API响应
                response = completion.model_dump_json()
                response_data = json.loads(response)

                analysis = response_data.get('choices', [{}])[0].get('message', {}).get('content', '')

                # 显示分析结果
                st.subheader("数据分析预测结果")
                st.write(analysis)

def main():
    if 'logged_in' not in st.session_state:
        st.session_state['logged_in'] = False

    params = st.experimental_get_query_params()
    page = params.get("page", ["login"])[0]

    if page == "login":
        login()
    elif page == "register":
        register()
    else:
        with st.sidebar:
            options = ["实时数据预览", "数据概览", "数据清洗", "数据分析", "可视化", "高级分析", "使用说明"]
            options.append("本地数据预测")
            options.append("AI数据处理")# 添加AI数据分析及预测菜单项
            if st.session_state.get('role') == 'admin':
                options.extend(["用户管理", "系统监控", "数据备份", "数据恢复"])
            selected = option_menu(
                menu_title="主菜单",
                options=options,
                icons=["table", "tools", "bar-chart", "graph-up", "gear-fill", "question-circle", "person-check", "cpu", "cloud-upload", "cloud-upload", "save", "table"], # 修改: 调整icons顺序
                menu_icon="cast",
                default_index=0,
            )

        # 主内容区
        if selected == "数据概览":
            data_overview()
        elif selected == "数据清洗":
            data_cleaning()
        elif selected == "数据分析":
            data_analysis()
        elif selected == "可视化":
            data_visualization()
        elif selected == "高级分析":
            advanced_analysis()
        elif selected == "使用说明":
            show_instructions()
        elif selected == "实时数据预览":
            data_preview()
        elif selected == "用户管理":
            user_management()
        elif selected == "系统监控":
            system_monitoring()
        elif selected == "数据备份":
            data_backup()
        elif selected == "数据恢复":
            data_restore()
        elif selected == "本地数据预测":
            data_prediction()
        elif selected == "AI数据处理":  # 添加AI数据分析及预测页面
            ai_data_analysis_and_prediction()

if __name__ == '__main__':
    main()