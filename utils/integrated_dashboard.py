"""
Integrated dashboard module combining real-time data preview and dashboard functionalities.
Provides a unified view with real-time monitoring and analytical capabilities.
"""

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime, timedelta
import psutil

from utils.logger import log_operation
from models import AirTemperatureHumidity, SoilMoisture, SoilNutrient, LightIntensity
from utils.database import get_session
from utils.data_preview import (
    fetch_last_day_data, 
    create_line_chart, 
    render_metric_card,
    fetch_latest_data
)


def get_user_role():
    """Get current user role from session state"""
    return st.session_state.get('role', 'user')


def get_user_preferences(username):
    """Get user dashboard preferences"""
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
    """Save user dashboard preferences"""
    pref_key = f"dashboard_pref_{username}"
    st.session_state[pref_key] = preferences


def fetch_sensor_data(session, hours=24):
    """Fetch sensor data for the specified time range"""
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
    """Create a trend chart for sensor data"""
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


def render_system_status():
    """Render system status panel"""
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


def render_admin_controls(session, username):
    """Render admin-specific controls and actions"""
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


def render_user_controls(session, username):
    """Render user-specific controls and actions"""
    # Quick actions for users
    st.subheader("⚡ 快捷操作")
    
    # First row of user actions
    user_action_cols = st.columns(3)
    
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
    

    
    # Second row of user actions
    user_action_cols2 = st.columns(3)
    
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




def render_realtime_metrics(session, username):
    """Render real-time metrics with enhanced visualization"""
    st.subheader("📊 实时环境指标")
    
    # Control panel
    with st.container():
        st.markdown('<div class="control-panel">', unsafe_allow_html=True)
        col1, col2 = st.columns([3, 1])
        with col1:
            if st.button("🔄 刷新数据", key="refresh_button"):
                st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)
    
    # Fetch latest data
    air_temp_hum, soil_moist, soil_nutri, light_intens = fetch_latest_data(session)
    log_operation(username, "INFO", "综合仪表板-更新数据",
                 f"获取时间: {air_temp_hum.timestamp} 温度: {air_temp_hum.temperature:.2f}°C 湿度: {air_temp_hum.humidity:.2f}% 土壤湿度: {soil_moist.value:.2f}% 土壤营养含量: {soil_nutri.value:.2f}ppm 光照强度: {light_intens.value:.2f}lux")

    # First row metrics
    row1_col1, row1_col2 = st.columns(2)
    
    with row1_col1:
        is_temp_alert = not (20 <= air_temp_hum.temperature <= 30)
        with st.container():
            st.markdown('<div class="metric-card">', unsafe_allow_html=True)
            render_metric_card(st, "🌡️ 空气温度", air_temp_hum.temperature,
                              "正常" if not is_temp_alert else "异常",
                              "适宜范围：20°C - 30°C", is_temp_alert)
            st.markdown('</div>', unsafe_allow_html=True)
        
        # Temperature trend chart
        with st.container():
            st.markdown('<div class="chart-container">', unsafe_allow_html=True)
            temp_data = fetch_last_day_data(session, AirTemperatureHumidity)
            fig = create_line_chart(temp_data, "24小时温度变化", "温度 (°C)", [20, 30])
            if fig:
                st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})
            st.markdown('</div>', unsafe_allow_html=True)
    
    with row1_col2:
        is_humidity_alert = not (40 <= air_temp_hum.humidity <= 70)
        with st.container():
            st.markdown('<div class="metric-card">', unsafe_allow_html=True)
            render_metric_card(st, "💧 空气湿度", air_temp_hum.humidity,
                              "理想" if not is_humidity_alert else "注意",
                              "适宜范围：40% - 70%", is_humidity_alert)
            st.markdown('</div>', unsafe_allow_html=True)
        
        # Humidity trend chart
        with st.container():
            st.markdown('<div class="chart-container">', unsafe_allow_html=True)
            humidity_data = fetch_last_day_data(session, AirTemperatureHumidity)
            fig = create_line_chart(humidity_data, "24小时湿度变化", "湿度 (%)", [40, 70])
            if fig:
                st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})
            st.markdown('</div>', unsafe_allow_html=True)
    
    # Second row metrics
    row2_col1, row2_col2 = st.columns(2)
    
    with row2_col1:
        is_soil_moist_alert = not (30 <= soil_moist.value <= 60)
        with st.container():
            st.markdown('<div class="metric-card">', unsafe_allow_html=True)
            render_metric_card(st, "🌱 土壤湿度", soil_moist.value,
                              "适宜" if not is_soil_moist_alert else "需灌溉",
                              "适宜范围：30% - 60%", is_soil_moist_alert)
            st.markdown('</div>', unsafe_allow_html=True)
        
        # Soil moisture trend chart
        with st.container():
            st.markdown('<div class="chart-container">', unsafe_allow_html=True)
            soil_moist_data = fetch_last_day_data(session, SoilMoisture)
            fig = create_line_chart(soil_moist_data, "24小时土壤湿度变化", "湿度 (%)", [30, 60])
            if fig:
                st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})
            st.markdown('</div>', unsafe_allow_html=True)
    
    with row2_col2:
        is_nutri_alert = not (10 <= soil_nutri.value <= 20)
        with st.container():
            st.markdown('<div class="metric-card">', unsafe_allow_html=True)
            render_metric_card(st, "🌱 土壤无机盐含量", soil_nutri.value,
                              "正常" if not is_nutri_alert else "需施肥",
                              "适宜范围：10ppm - 20ppm", is_nutri_alert)
            st.markdown('</div>', unsafe_allow_html=True)
        
        # Soil nutrient trend chart
        with st.container():
            st.markdown('<div class="chart-container">', unsafe_allow_html=True)
            soil_nutri_data = fetch_last_day_data(session, SoilNutrient)
            fig = create_line_chart(soil_nutri_data, "24小时土壤养分变化", "养分 (ppm)", [10, 20])
            if fig:
                st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})
            st.markdown('</div>', unsafe_allow_html=True)
    
    # Third row - Light intensity
    row3_col1, row3_col2 = st.columns([2, 1])
    
    with row3_col1:
        is_light_alert = light_intens.value < 1000
        with st.container():
            st.markdown('<div class="metric-card">', unsafe_allow_html=True)
            render_metric_card(st, "☀️ 光照强度", light_intens.value,
                              "充足" if not is_light_alert else "不足",
                              "建议光照强度 ≥ 1000 lux", is_light_alert)
            st.markdown('</div>', unsafe_allow_html=True)
        
        # Light intensity trend chart
        with st.container():
            st.markdown('<div class="chart-container">', unsafe_allow_html=True)
            light_data = fetch_last_day_data(session, LightIntensity)
            fig = create_line_chart(light_data, "24小时光照强度变化", "光照 (lux)", 1000)
            if fig:
                st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})
            st.markdown('</div>', unsafe_allow_html=True)
    
    with row3_col2:
        # System info card
        with st.container():
            st.markdown('<div class="metric-card">', unsafe_allow_html=True)
            st.markdown("### 📊 系统信息")
            st.metric(label="数据点数量", value=len(temp_data) if temp_data else 0, help="最近24小时数据点数量")
            st.metric(label="数据获取时间", value=light_intens.timestamp.strftime("%H:%M:%S") if light_intens else "N/A", help="最新数据获取时间")
            st.markdown('</div>', unsafe_allow_html=True)


def render_analytical_dashboard(session, username):
    """Render analytical dashboard with trends and charts"""
    # This function is intentionally left empty as per user request to remove the data trends module
    pass


def show_integrated_dashboard():
    """Main integrated dashboard function"""
    if not st.session_state.get('logged_in'):
        st.query_params.page = "login"
        return
    
    # Get database session
    session = get_session()
    
    # Get user info
    username = st.session_state.get('username', 'Unknown')
    role = get_user_role()
    
    # Log dashboard access
    log_operation(username, "INFO", "综合仪表板访问", f"用户 {username} 访问了{role}综合仪表板")
    
    try:
        # Page title
        st.title("🌱 智能农场综合监控仪表板")
        
        # Render role-specific controls first
        if role == 'admin':
            render_admin_controls(session, username)
            render_system_status()
        else:
            render_user_controls(session, username)
            
        # Render real-time metrics section
        render_realtime_metrics(session, username)
        
    except Exception as e:
        st.error(f"仪表板加载失败: {str(e)}")
        log_operation(username, "ERROR", "综合仪表板错误", f"仪表板加载失败: {str(e)}")
    finally:
        session.close()