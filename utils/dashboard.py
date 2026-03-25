from datetime import datetime, timedelta

import plotly.graph_objects as go
import psutil
import streamlit as st

from models import AirTemperatureHumidity, SoilMoisture, SoilNutrient, LightIntensity
from utils.database import get_session
from utils.logger import log_operation


def get_user_role():
    """获取当前用户角色

    从会话状态中获取当前用户的角色。

    Returns:
        str: 用户角色，默认为'user'
    """
    return st.session_state.get('role', 'user')


def get_user_preferences(username):
    """获取用户仪表板偏好设置

    获取用户的仪表板偏好设置，包括布局、显示的指标和时间范围。

    Args:
        username (str): 用户名

    Returns:
        dict: 用户仪表板偏好设置
    """
    # In a real implementation, this would fetch from a database
    # For now, we'll use session state
    pref_key = f"dashboard_pref_{username}"
    if pref_key not in st.session_state:
        st.session_state[pref_key] = {
            "layout": "grid",
            "metrics": ["temperature", "humidity", "soil_moisture", "light_intensity"],
            "time_range": "24h"
        }
    return st.session_state[pref_key]


def save_user_preferences(username, preferences):
    """保存用户仪表板偏好设置

    保存用户的仪表板偏好设置到会话状态中。

    Args:
        username (str): 用户名
        preferences (dict): 用户仪表板偏好设置

    Returns:
        None: 无返回值
    """
    pref_key = f"dashboard_pref_{username}"
    st.session_state[pref_key] = preferences


def fetch_sensor_data(session, hours=24):
    """获取指定时间范围内的传感器数据

    获取指定时间范围内的传感器数据，包括温度、湿度、土壤湿度、土壤养分和光照强度。

    Args:
        session: 数据库会话对象
        hours (int, optional): 时间范围（小时），默认为24

    Returns:
        dict: 传感器数据字典，包含温度、土壤湿度、土壤养分和光照强度数据
    """
    end_time = datetime.now()
    start_time = end_time - timedelta(hours=hours)

    # Fetch data for each sensor type
    temp_data = session.query(AirTemperatureHumidity).filter(
        AirTemperatureHumidity.timestamp >= start_time,
        AirTemperatureHumidity.timestamp <= end_time
    ).order_by(AirTemperatureHumidity.timestamp.desc()).all()

    soil_moisture_data = session.query(SoilMoisture).filter(
        SoilMoisture.timestamp >= start_time,
        SoilMoisture.timestamp <= end_time
    ).order_by(SoilMoisture.timestamp.desc()).all()

    soil_nutrient_data = session.query(SoilNutrient).filter(
        SoilNutrient.timestamp >= start_time,
        SoilNutrient.timestamp <= end_time
    ).order_by(SoilNutrient.timestamp.desc()).all()

    light_data = session.query(LightIntensity).filter(
        LightIntensity.timestamp >= start_time,
        LightIntensity.timestamp <= end_time
    ).order_by(LightIntensity.timestamp.desc()).all()

    # 如果没有最近的数据，则获取最新的数据
    if not temp_data:
        temp_data = session.query(AirTemperatureHumidity).order_by(
            AirTemperatureHumidity.timestamp.desc()).limit(100).all()

    if not soil_moisture_data:
        soil_moisture_data = session.query(SoilMoisture).order_by(
            SoilMoisture.timestamp.desc()).limit(100).all()

    if not soil_nutrient_data:
        soil_nutrient_data = session.query(SoilNutrient).order_by(
            SoilNutrient.timestamp.desc()).limit(100).all()

    if not light_data:
        light_data = session.query(LightIntensity).order_by(
            LightIntensity.timestamp.desc()).limit(100).all()

    return {
        "temperature": temp_data,
        "soil_moisture": soil_moisture_data,
        "soil_nutrient": soil_nutrient_data,
        "light_intensity": light_data
    }


def create_trend_chart(data, title, y_label, thresholds=None):
    """创建传感器数据趋势图表

    创建传感器数据的趋势图表，支持添加阈值线。

    Args:
        data: 传感器数据列表
        title (str): 图表标题
        y_label (str): Y轴标签
        thresholds (dict, optional): 阈值字典，默认为None

    Returns:
        plotly.graph_objects.Figure or None: 图表对象，如果数据为空则返回None
    """
    if not data:
        return None

    # Extract values and timestamps
    timestamps = [d.timestamp for d in data]
    if hasattr(data[0], 'value'):
        values = [d.value for d in data]
    elif hasattr(data[0], 'temperature'):
        values = [d.temperature for d in data]
    elif hasattr(data[0], 'humidity'):
        values = [d.humidity for d in data]
    else:
        return None

    # Create the figure
    fig = go.Figure()

    # Add the main line
    fig.add_trace(go.Scatter(
        x=timestamps,
        y=values,
        mode='lines+markers',
        name=y_label,
        line=dict(width=2),
        marker=dict(size=4)
    ))

    # Add thresholds if provided
    if thresholds:
        for threshold_name, threshold_value in thresholds.items():
            fig.add_hline(
                y=threshold_value,
                line_dash="dash",
                line_color="red",
                annotation_text=threshold_name
            )

    # Update layout
    fig.update_layout(
        title=title,
        xaxis_title="时间",
        yaxis_title=y_label,
        height=300,
        margin=dict(l=20, r=20, t=40, b=20)
    )

    return fig


def render_admin_dashboard(session, username):
    """渲染管理员仪表板

    渲染管理员仪表板，包括关键指标、快捷操作、数据趋势和系统状态。

    Args:
        session: 数据库会话对象
        username (str): 用户名

    Returns:
        None: 无返回值，直接在页面上显示内容
    """
    st.title("🎛️ 管理员仪表板")

    # User preferences
    preferences = get_user_preferences(username)

    # Dashboard controls
    with st.expander("⚙️ 仪表板设置", expanded=False):
        col1, col2 = st.columns(2)
        with col1:
            layout = st.selectbox("布局方式", ["网格", "列表"],
                                  index=0 if preferences["layout"] == "grid" else 1)
        with col2:
            time_range = st.selectbox("时间范围", ["1小时", "6小时", "24小时", "7天"],
                                      index=["1小时", "6小时", "24小时", "7天"].index(
                                          {"1h": "1小时", "6h": "6小时", "24h": "24小时", "7d": "7天"}.get(
                                              preferences["time_range"], "24小时")))

        # Map time range to hours
        time_map = {"1小时": 1, "6小时": 6, "24小时": 24, "7天": 168}
        selected_hours = time_map[time_range]

        # Update preferences
        preferences["layout"] = "grid" if layout == "网格" else "list"
        preferences["time_range"] = {"1小时": "1h", "6小时": "6h", "24小时": "24h", "7天": "7d"}[time_range]
        save_user_preferences(username, preferences)

    # Fetch data
    sensor_data = fetch_sensor_data(session, selected_hours)

    # Key metrics row
    st.subheader("📊 关键指标")

    # Get latest values
    latest_temp = sensor_data["temperature"][0] if sensor_data["temperature"] else None
    latest_soil_moisture = sensor_data["soil_moisture"][0] if sensor_data["soil_moisture"] else None
    latest_soil_nutrient = sensor_data["soil_nutrient"][0] if sensor_data["soil_nutrient"] else None
    latest_light = sensor_data["light_intensity"][0] if sensor_data["light_intensity"] else None

    # Display metrics
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        temp_value = latest_temp.temperature if latest_temp else 0
        temp_status = "🟢 正常" if 20 <= temp_value <= 30 else "🔴 异常"
        st.metric("🌡️ 空气温度", f"{temp_value:.1f}°C", temp_status)

    with col2:
        humidity_value = latest_temp.humidity if latest_temp else 0
        humidity_status = "🟢 正常" if 40 <= humidity_value <= 70 else "🔴 异常"
        st.metric("💧 空气湿度", f"{humidity_value:.1f}%", humidity_status)

    with col3:
        soil_moisture_value = latest_soil_moisture.value if latest_soil_moisture else 0
        soil_moisture_status = "🟢 正常" if 30 <= soil_moisture_value <= 60 else "🔴 异常"
        st.metric("🌱 土壤湿度", f"{soil_moisture_value:.1f}%", soil_moisture_status)

    with col4:
        light_value = latest_light.value if latest_light else 0
        light_status = "🟢 充足" if light_value >= 1000 else "🟡 不足"
        st.metric("☀️ 光照强度", f"{light_value:.0f} lux", light_status)

    # Quick actions for admins
    st.subheader("⚡ 管理员快捷操作")

    # First row of admin actions
    admin_action_cols = st.columns(4)

    with admin_action_cols[0]:
        if st.button("🔄 刷新数据"):
            st.rerun()

    with admin_action_cols[1]:
        if st.button("📊 数据分析"):
            st.query_params.page = "data_analysis"
            st.rerun()

    with admin_action_cols[2]:
        if st.button("🤖 模型预测"):
            st.query_params.page = "data_prediction"
            st.rerun()

    with admin_action_cols[3]:
        if st.button("🔧 系统监控"):
            st.query_params.page = "system_monitoring"
            st.rerun()

    # Second row of admin actions
    admin_action_cols2 = st.columns(4)

    with admin_action_cols2[0]:
        if st.button("👥 用户管理"):
            st.query_params.page = "user_management"
            st.rerun()

    with admin_action_cols2[1]:
        if st.button("💾 数据备份"):
            st.query_params.page = "data_backup"
            st.rerun()

    with admin_action_cols2[2]:
        if st.button("💾 数据恢复"):
            st.query_params.page = "data_restore"
            st.rerun()

    with admin_action_cols2[3]:
        if st.button("⚙️ 模块配置"):
            st.query_params.page = "module_config"
            st.rerun()

    # Charts section
    st.subheader("📈 数据趋势")

    # Create charts
    temp_chart = create_trend_chart(
        sensor_data["temperature"],
        "空气温度趋势",
        "温度 (°C)",
        {"适宜范围上限": 30, "适宜范围下限": 20}
    )

    humidity_chart = create_trend_chart(
        sensor_data["temperature"],
        "空气湿度趋势",
        "湿度 (%)",
        {"适宜范围上限": 70, "适宜范围下限": 40}
    )

    soil_moisture_chart = create_trend_chart(
        sensor_data["soil_moisture"],
        "土壤湿度趋势",
        "湿度 (%)",
        {"适宜范围上限": 60, "适宜范围下限": 30}
    )

    light_chart = create_trend_chart(
        sensor_data["light_intensity"],
        "光照强度趋势",
        "光照强度 (lux)",
        {"建议阈值": 1000}
    )

    # Display charts in a grid
    chart_cols = st.columns(2)

    with chart_cols[0]:
        if temp_chart:
            st.plotly_chart(temp_chart, use_container_width=True)
        if soil_moisture_chart:
            st.plotly_chart(soil_moisture_chart, use_container_width=True)

    with chart_cols[1]:
        if humidity_chart:
            st.plotly_chart(humidity_chart, use_container_width=True)
        if light_chart:
            st.plotly_chart(light_chart, use_container_width=True)

    # System metrics
    st.subheader("🖥️ 系统状态")
    cpu_percent = psutil.cpu_percent(interval=1)
    memory = psutil.virtual_memory()
    disk = psutil.disk_usage('/')

    sys_col1, sys_col2, sys_col3 = st.columns(3)

    with sys_col1:
        st.metric("CPU使用率", f"{cpu_percent:.1f}%")

    with sys_col2:
        st.metric("内存使用率", f"{memory.percent:.1f}%")

    with sys_col3:
        st.metric("磁盘使用率", f"{disk.percent:.1f}%")


def render_user_dashboard(session, username):
    """渲染普通用户仪表板

    渲染普通用户仪表板，包括环境指标、快捷操作和数据趋势。

    Args:
        session: 数据库会话对象
        username (str): 用户名

    Returns:
        None: 无返回值，直接在页面上显示内容
    """
    st.title("🌿 用户仪表板")

    # User preferences
    preferences = get_user_preferences(username)

    # Dashboard controls
    with st.expander("⚙️ 仪表板设置", expanded=False):
        col1, col2 = st.columns(2)
        with col1:
            layout = st.selectbox("布局方式", ["网格", "列表"],
                                  index=0 if preferences["layout"] == "grid" else 1)
        with col2:
            time_range = st.selectbox("时间范围", ["1小时", "6小时", "24小时", "7天"],
                                      index=["1小时", "6小时", "24小时", "7天"].index(
                                          {"1h": "1小时", "6h": "6小时", "24h": "24小时", "7d": "7天"}.get(
                                              preferences["time_range"], "24小时")))

        # Map time range to hours
        time_map = {"1小时": 1, "6小时": 6, "24小时": 24, "7天": 168}
        selected_hours = time_map[time_range]

        # Update preferences
        preferences["layout"] = "grid" if layout == "网格" else "list"
        preferences["time_range"] = {"1小时": "1h", "6小时": "6h", "24小时": "24h", "7天": "7d"}[time_range]
        save_user_preferences(username, preferences)

    # Fetch data
    sensor_data = fetch_sensor_data(session, selected_hours)

    # Key metrics row
    st.subheader("📊 环境指标")

    # Get latest values
    latest_temp = sensor_data["temperature"][0] if sensor_data["temperature"] else None
    latest_soil_moisture = sensor_data["soil_moisture"][0] if sensor_data["soil_moisture"] else None
    latest_soil_nutrient = sensor_data["soil_nutrient"][0] if sensor_data["soil_nutrient"] else None
    latest_light = sensor_data["light_intensity"][0] if sensor_data["light_intensity"] else None

    # Display metrics
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        temp_value = latest_temp.temperature if latest_temp else 0
        temp_status = "🟢 正常" if 20 <= temp_value <= 30 else "🔴 异常"
        st.metric("🌡️ 空气温度", f"{temp_value:.1f}°C", temp_status)

    with col2:
        humidity_value = latest_temp.humidity if latest_temp else 0
        humidity_status = "🟢 正常" if 40 <= humidity_value <= 70 else "🔴 异常"
        st.metric("💧 空气湿度", f"{humidity_value:.1f}%", humidity_status)

    with col3:
        soil_moisture_value = latest_soil_moisture.value if latest_soil_moisture else 0
        soil_moisture_status = "🟢 正常" if 30 <= soil_moisture_value <= 60 else "🔴 异常"
        st.metric("🌱 土壤湿度", f"{soil_moisture_value:.1f}%", soil_moisture_status)

    with col4:
        light_value = latest_light.value if latest_light else 0
        light_status = "🟢 充足" if light_value >= 1000 else "🟡 不足"
        st.metric("☀️ 光照强度", f"{light_value:.0f} lux", light_status)

    # Quick actions for users
    st.subheader("⚡ 快捷操作")

    # First row of user actions
    user_action_cols = st.columns(4)

    with user_action_cols[0]:
        if st.button("🔄 刷新数据"):
            st.rerun()

    with user_action_cols[1]:
        if st.button("📊 数据分析"):
            st.query_params.page = "data_analysis"
            st.rerun()

    with user_action_cols[2]:
        if st.button("🤖 模型预测"):
            st.query_params.page = "data_prediction"
            st.rerun()

    with user_action_cols[3]:
        if st.button("💡 决策建议"):
            st.query_params.page = "decision_engine"
            st.rerun()

    # Second row of user actions
    user_action_cols2 = st.columns(4)

    with user_action_cols2[0]:
        if st.button("📈 数据可视化"):
            st.query_params.page = "data_visualization"
            st.rerun()

    with user_action_cols2[1]:
        if st.button("📋 数据概览"):
            st.query_params.page = "data_overview"
            st.rerun()

    with user_action_cols2[2]:
        if st.button("🔍 日志查看"):
            st.query_params.page = "log_viewer"
            st.rerun()

    with user_action_cols2[3]:
        if st.button("📱 同步管理"):
            st.query_params.page = "database_sync"
            st.rerun()

    # Charts section
    st.subheader("📈 数据趋势")

    # Create charts
    temp_chart = create_trend_chart(
        sensor_data["temperature"],
        "空气温度趋势",
        "温度 (°C)",
        {"适宜范围上限": 30, "适宜范围下限": 20}
    )

    humidity_chart = create_trend_chart(
        sensor_data["temperature"],
        "空气湿度趋势",
        "湿度 (%)",
        {"适宜范围上限": 70, "适宜范围下限": 40}
    )

    soil_moisture_chart = create_trend_chart(
        sensor_data["soil_moisture"],
        "土壤湿度趋势",
        "湿度 (%)",
        {"适宜范围上限": 60, "适宜范围下限": 30}
    )

    light_chart = create_trend_chart(
        sensor_data["light_intensity"],
        "光照强度趋势",
        "光照强度 (lux)",
        {"建议阈值": 1000}
    )

    # Display charts in a grid
    chart_cols = st.columns(2)

    with chart_cols[0]:
        if temp_chart:
            st.plotly_chart(temp_chart, use_container_width=True)
        if soil_moisture_chart:
            st.plotly_chart(soil_moisture_chart, use_container_width=True)

    with chart_cols[1]:
        if humidity_chart:
            st.plotly_chart(humidity_chart, use_container_width=True)
        if light_chart:
            st.plotly_chart(light_chart, use_container_width=True)


def show_dashboard():
    """主仪表板函数

    主仪表板函数，根据用户角色显示相应的仪表板。

    Returns:
        None: 无返回值，直接在页面上显示内容

    Raises:
        Exception: 仪表板加载失败时会捕获并显示错误信息
    """
    if not st.session_state.get('logged_in'):
        st.query_params.page = "login"
        return

    # Get user info
    username = st.session_state.get('username', 'Unknown')
    role = get_user_role()

    # Log dashboard access
    log_operation(username, "INFO", "仪表板访问", f"用户 {username} 访问了{role}仪表板")

    try:
        # Get database session
        with get_session() as session:
            # Render appropriate dashboard based on role
            if role == 'admin':
                render_admin_dashboard(session, username)
            else:
                render_user_dashboard(session, username)
    except Exception as e:
        st.error(f"仪表板加载失败: {str(e)}")
        log_operation(username, "ERROR", "仪表板错误", f"仪表板加载失败: {str(e)}")
