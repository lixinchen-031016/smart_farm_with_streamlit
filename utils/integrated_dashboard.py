"""
Integrated dashboard module combining real-time data preview and dashboard functionalities.
Provides a unified view with real-time monitoring and analytical capabilities.
"""

from datetime import datetime, timedelta

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import psutil
import streamlit as st

from models import AirTemperatureHumidity, SoilMoisture, SoilNutrient, LightIntensity
from utils.data_preview import (
    fetch_last_day_data,
    create_line_chart,
    render_metric_card,
    fetch_latest_data
)
from utils.database import get_session
from utils.logger import log_operation
from utils.anomaly_detection import detect_anomalies
from utils.predictions import perform_prediction


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
            "time_range": "24h",
            "custom_thresholds": {
                "temperature": {"min": 20, "max": 30},
                "humidity": {"min": 40, "max": 70},
                "soil_moisture": {"min": 30, "max": 60},
                "soil_nutrient": {"min": 10, "max": 20},
                "light_intensity": {"min": 1000, "max": 50000}
            },
            "crop_stage": "growth",  # growth, flowering, fruiting
            "show_predictions": True,
            "show_anomalies": True
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


def create_trend_chart(data, title, y_label, thresholds=None, prediction_data=None, anomaly_indices=None):
    """Create a trend chart for sensor data with predictions and anomalies"""
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
    
    # Highlight anomalies if provided
    if anomaly_indices is not None and len(anomaly_indices) > 0:
        anomaly_x = [timestamps[i] for i in anomaly_indices if i < len(timestamps)]
        anomaly_y = [values[i] for i in anomaly_indices if i < len(values)]
        if anomaly_x:
            fig.add_trace(go.Scatter(
                x=anomaly_x,
                y=anomaly_y,
                mode='markers',
                name='异常数据',
                marker=dict(color='red', size=8, symbol='x'),
                hovertemplate='异常点： %{y:.2f}<br>时间：%{x}<extra></extra>'
            ))
    
    # Add prediction trend if provided
    if prediction_data is not None and not prediction_data.empty:
        pred_timestamps = prediction_data['timestamp']
        pred_values = prediction_data['value']
        fig.add_trace(go.Scatter(
            x=pred_timestamps,
            y=pred_values,
            mode='lines',
            name='预测趋势',
            line=dict(width=3, dash='dash', color='orange'),
            hovertemplate='预测值： %{y:.2f}<br>时间：%{x}<extra></extra>'
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
        margin=dict(l=20, r=20, t=40, b=20),
        hovermode='x unified'
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
        st.metric("CPU 使用率", f"{cpu_percent:.1f}%")

    with sys_col2:
        st.metric("内存使用率", f"{memory.percent:.1f}%")

    with sys_col3:
        st.metric("磁盘使用率", f"{disk.percent:.1f}%")


def get_crop_stage_recommendations(crop_stage):
    """Get recommended environmental parameters for different crop growth stages"""
    recommendations = {
        "growth": {
            "name": "生长期",
            "temperature": {"min": 20, "max": 28, "optimal": 24},
            "humidity": {"min": 50, "max": 70, "optimal": 60},
            "soil_moisture": {"min": 35, "max": 65, "optimal": 50},
            "light_intensity": {"min": 1500, "max": 40000, "optimal": 20000}
        },
        "flowering": {
            "name": "开花期",
            "temperature": {"min": 18, "max": 26, "optimal": 22},
            "humidity": {"min": 40, "max": 60, "optimal": 50},
            "soil_moisture": {"min": 30, "max": 55, "optimal": 45},
            "light_intensity": {"min": 2000, "max": 45000, "optimal": 25000}
        },
        "fruiting": {
            "name": "结果期",
            "temperature": {"min": 22, "max": 30, "optimal": 26},
            "humidity": {"min": 45, "max": 65, "optimal": 55},
            "soil_moisture": {"min": 40, "max": 70, "optimal": 55},
            "light_intensity": {"min": 2500, "max": 50000, "optimal": 30000}
        }
    }
    return recommendations.get(crop_stage, recommendations["growth"])


def render_threshold_config_ui(username, preferences):
    """Render threshold configuration UI"""
    with st.expander("⚙️ 自定义告警阈值配置", expanded=False):
        st.markdown("#### 🎯 作物生长阶段选择")
        crop_stage = st.selectbox(
            "选择当前作物生长阶段",
            options=["growth", "flowering", "fruiting"],
            format_func=lambda x: get_crop_stage_recommendations(x)["name"],
            index=["growth", "flowering", "fruiting"].index(preferences.get('crop_stage', 'growth'))
        )
        
        # Apply preset button
        if st.button("✅ 应用推荐阈值"):
            recommendations = get_crop_stage_recommendations(crop_stage)
            preferences['custom_thresholds'] = {
                "temperature": {"min": recommendations["temperature"]["min"], "max": recommendations["temperature"]["max"]},
                "humidity": {"min": recommendations["humidity"]["min"], "max": recommendations["humidity"]["max"]},
                "soil_moisture": {"min": recommendations["soil_moisture"]["min"], "max": recommendations["soil_moisture"]["max"]},
                "light_intensity": {"min": recommendations["light_intensity"]["min"], "max": recommendations["light_intensity"]["max"]},
                "soil_nutrient": preferences['custom_thresholds'].get("soil_nutrient", {"min": 10, "max": 20})
            }
            preferences['crop_stage'] = crop_stage
            save_user_preferences(username, preferences)
            st.success(f"已应用{get_crop_stage_recommendations(crop_stage)['name']}推荐阈值！")
            st.rerun()
        
        st.markdown("#### 📊 手动调整阈值")
        col1, col2 = st.columns(2)
        
        with col1:
            temp_min = st.number_input("🌡️ 温度最小值 (°C)", 
                                      value=preferences['custom_thresholds']['temperature']['min'],
                                      min_value=-10, max_value=50)
            temp_max = st.number_input("🌡️ 温度最大值 (°C)", 
                                      value=preferences['custom_thresholds']['temperature']['max'],
                                      min_value=-10, max_value=50)
            
            humid_min = st.number_input("💧 湿度最小值 (%)", 
                                       value=preferences['custom_thresholds']['humidity']['min'],
                                       min_value=0, max_value=100)
            humid_max = st.number_input("💧 湿度最大值 (%)", 
                                       value=preferences['custom_thresholds']['humidity']['max'],
                                       min_value=0, max_value=100)
        
        with col2:
            soil_m_min = st.number_input("🌱 土壤湿度最小值 (%)", 
                                        value=preferences['custom_thresholds']['soil_moisture']['min'],
                                        min_value=0, max_value=100)
            soil_m_max = st.number_input("🌱 土壤湿度最大值 (%)", 
                                        value=preferences['custom_thresholds']['soil_moisture']['max'],
                                        min_value=0, max_value=100)
            
            light_min = st.number_input("☀️ 光照强度最小值 (lux)", 
                                       value=preferences['custom_thresholds']['light_intensity']['min'],
                                       min_value=0, max_value=100000)
            light_max = st.number_input("☀️ 光照强度最大值 (lux)", 
                                       value=preferences['custom_thresholds']['light_intensity']['max'],
                                       min_value=0, max_value=100000)
        
        if st.button("💾 保存自定义阈值"):
            preferences['custom_thresholds'] = {
                "temperature": {"min": temp_min, "max": temp_max},
                "humidity": {"min": humid_min, "max": humid_max},
                "soil_moisture": {"min": soil_m_min, "max": soil_m_max},
                "light_intensity": {"min": light_min, "max": light_max}
            }
            preferences['crop_stage'] = crop_stage
            save_user_preferences(username, preferences)
            st.success("阈值已保存！")
            st.rerun()
        
        # Display recommendations
        recommendations = get_crop_stage_recommendations(crop_stage)
        st.markdown("#### 📋 当前阶段推荐值参考")
        rec_cols = st.columns(4)
        with rec_cols[0]:
            st.info(f"🌡️ 温度：{recommendations['temperature']['min']}-{recommendations['temperature']['max']}°C\n\n最优：{recommendations['temperature']['optimal']}°C")
        with rec_cols[1]:
            st.info(f"💧 湿度：{recommendations['humidity']['min']}-{recommendations['humidity']['max']}%\n\n最优：{recommendations['humidity']['optimal']}%")
        with rec_cols[2]:
            st.info(f"🌱 土壤湿度：{recommendations['soil_moisture']['min']}-{recommendations['soil_moisture']['max']}%\n\n最优：{recommendations['soil_moisture']['optimal']}%")
        with rec_cols[3]:
            st.info(f"☀️ 光照：{recommendations['light_intensity']['min']}-{recommendations['light_intensity']['max']} lux\n\n最优：{recommendations['light_intensity']['optimal']} lux")


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
    """Render real-time metrics with enhanced visualization, anomaly detection and predictions"""
    st.subheader("📊 实时环境指标")
    
    # Get user preferences
    preferences = get_user_preferences(username)
    custom_thresholds = preferences['custom_thresholds']
    crop_stage = preferences.get('crop_stage', 'growth')
    show_predictions = preferences.get('show_predictions', True)
    show_anomalies = preferences.get('show_anomalies', True)
    
    # Render threshold configuration UI
    render_threshold_config_ui(username, preferences)

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
    log_operation(username, "INFO", "综合仪表板 - 更新数据",
                  f"获取时间：{air_temp_hum.timestamp} 温度：{air_temp_hum.temperature:.2f}°C 湿度：{air_temp_hum.humidity:.2f}% 土壤湿度：{soil_moist.value:.2f}% 土壤营养含量：{soil_nutri.value:.2f}ppm 光照强度：{light_intens.value:.2f}lux")

    # Get thresholds from preferences
    temp_min = custom_thresholds['temperature']['min']
    temp_max = custom_thresholds['temperature']['max']
    humid_min = custom_thresholds['humidity']['min']
    humid_max = custom_thresholds['humidity']['max']
    soil_m_min = custom_thresholds['soil_moisture']['min']
    soil_m_max = custom_thresholds['soil_moisture']['max']
    light_min = custom_thresholds['light_intensity']['min']

    # First row metrics
    row1_col1, row1_col2 = st.columns(2)

    with row1_col1:
        is_temp_alert = not (temp_min <= air_temp_hum.temperature <= temp_max)
        with st.container():
            st.markdown('<div class="metric-card">', unsafe_allow_html=True)
            render_metric_card(st, "🌡️ 空气温度", air_temp_hum.temperature,
                               "正常" if not is_temp_alert else "异常",
                               f"适宜范围：{temp_min}°C - {temp_max}°C", is_temp_alert)
            st.markdown('</div>', unsafe_allow_html=True)
    
        # Temperature trend chart with anomalies and predictions
        with st.container():
            st.markdown('<div class="chart-container">', unsafe_allow_html=True)
            temp_data = fetch_last_day_data(session, AirTemperatureHumidity)
            
            # Anomaly detection
            temp_anomaly_indices = None
            if show_anomalies and temp_data:
                temp_df = pd.DataFrame([(d.timestamp, d.temperature) for d in temp_data], columns=['timestamp', 'value'])
                temp_anomalies = detect_anomalies(temp_df, method='iqr')
                temp_anomaly_indices = temp_anomalies.get('value', [])
            
            # Short-term prediction
            temp_prediction = None
            if show_predictions and temp_data:
                try:
                    temp_data_for_pred = [(d.timestamp, d.temperature) for d in temp_data]
                    _, temp_pred_df, _, _ = perform_prediction(temp_data_for_pred, "Prophet", 1)
                    temp_prediction = temp_pred_df
                except Exception as e:
                    pass
            
            fig = create_trend_chart(temp_data, "24 小时温度变化", "温度 (°C)", 
                                    thresholds={"最低": temp_min, "最高": temp_max},
                                    prediction_data=temp_prediction,
                                    anomaly_indices=temp_anomaly_indices)
            if fig:
                st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})
            st.markdown('</div>', unsafe_allow_html=True)

    with row1_col2:
        is_humidity_alert = not (humid_min <= air_temp_hum.humidity <= humid_max)
        with st.container():
            st.markdown('<div class="metric-card">', unsafe_allow_html=True)
            render_metric_card(st, "💧 空气湿度", air_temp_hum.humidity,
                               "理想" if not is_humidity_alert else "注意",
                               f"适宜范围：{humid_min}% - {humid_max}%", is_humidity_alert)
            st.markdown('</div>', unsafe_allow_html=True)
    
        # Humidity trend chart with anomalies and predictions
        with st.container():
            st.markdown('<div class="chart-container">', unsafe_allow_html=True)
            humidity_data = fetch_last_day_data(session, AirTemperatureHumidity)
            
            # Anomaly detection
            humid_anomaly_indices = None
            if show_anomalies and humidity_data:
                humid_df = pd.DataFrame([(d.timestamp, d.humidity) for d in humidity_data], columns=['timestamp', 'value'])
                humid_anomalies = detect_anomalies(humid_df, method='iqr')
                humid_anomaly_indices = humid_anomalies.get('value', [])
            
            # Short-term prediction
            humid_prediction = None
            if show_predictions and humidity_data:
                try:
                    humid_data_for_pred = [(d.timestamp, d.humidity) for d in humidity_data]
                    _, humid_pred_df, _, _ = perform_prediction(humid_data_for_pred, "Prophet", 1)
                    humid_prediction = humid_pred_df
                except Exception as e:
                    pass
            
            fig = create_trend_chart(humidity_data, "24 小时湿度变化", "湿度 (%)", 
                                    thresholds={"最低": humid_min, "最高": humid_max},
                                    prediction_data=humid_prediction,
                                    anomaly_indices=humid_anomaly_indices)
            if fig:
                st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})
            st.markdown('</div>', unsafe_allow_html=True)

    # Second row metrics
    row2_col1, row2_col2 = st.columns(2)

    with row2_col1:
        is_soil_moist_alert = not (soil_m_min <= soil_moist.value <= soil_m_max)
        with st.container():
            st.markdown('<div class="metric-card">', unsafe_allow_html=True)
            render_metric_card(st, "🌱 土壤湿度", soil_moist.value,
                               "适宜" if not is_soil_moist_alert else "需灌溉",
                               "适宜范围：30% - 60%", is_soil_moist_alert)
            st.markdown('</div>', unsafe_allow_html=True)

        # Soil moisture trend chart with anomalies and predictions
        with st.container():
            st.markdown('<div class="chart-container">', unsafe_allow_html=True)
            soil_moist_data = fetch_last_day_data(session, SoilMoisture)
            
            # Anomaly detection
            soil_m_anomaly_indices = None
            if show_anomalies and soil_moist_data:
                soil_m_df = pd.DataFrame([(d.timestamp, d.value) for d in soil_moist_data], columns=['timestamp', 'value'])
                soil_m_anomalies = detect_anomalies(soil_m_df, method='iqr')
                soil_m_anomaly_indices = soil_m_anomalies.get('value', [])
            
            # Short-term prediction
            soil_m_prediction = None
            if show_predictions and soil_moist_data:
                try:
                    soil_m_data_for_pred = [(d.timestamp, d.value) for d in soil_moist_data]
                    _, soil_m_pred_df, _, _ = perform_prediction(soil_m_data_for_pred, "Prophet", 1)
                    soil_m_prediction = soil_m_pred_df
                except Exception as e:
                    pass
            
            fig = create_trend_chart(soil_moist_data, "24 小时土壤湿度变化", "湿度 (%)", 
                                    thresholds={"最低": soil_m_min, "最高": soil_m_max},
                                    prediction_data=soil_m_prediction,
                                    anomaly_indices=soil_m_anomaly_indices)
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

        # Soil nutrient trend chart with anomalies and predictions
        with st.container():
            st.markdown('<div class="chart-container">', unsafe_allow_html=True)
            soil_nutri_data = fetch_last_day_data(session, SoilNutrient)
            
            # Anomaly detection
            soil_n_anomaly_indices = None
            if show_anomalies and soil_nutri_data:
                soil_n_df = pd.DataFrame([(d.timestamp, d.value) for d in soil_nutri_data], columns=['timestamp', 'value'])
                soil_n_anomalies = detect_anomalies(soil_n_df, method='iqr')
                soil_n_anomaly_indices = soil_n_anomalies.get('value', [])
            
            # Short-term prediction
            soil_n_prediction = None
            if show_predictions and soil_nutri_data:
                try:
                    soil_n_data_for_pred = [(d.timestamp, d.value) for d in soil_nutri_data]
                    _, soil_n_pred_df, _, _ = perform_prediction(soil_n_data_for_pred, "Prophet", 1)
                    soil_n_prediction = soil_n_pred_df
                except Exception as e:
                    pass
            
            fig = create_trend_chart(soil_nutri_data, "24 小时土壤养分变化", "养分 (ppm)", 
                                    thresholds={"最低": 10, "最高": 20},
                                    prediction_data=soil_n_prediction,
                                    anomaly_indices=soil_n_anomaly_indices)
            if fig:
                st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})
            st.markdown('</div>', unsafe_allow_html=True)

    # Third row - Light intensity
    row3_col1, row3_col2 = st.columns([2, 1])

    with row3_col1:
        is_light_alert = light_intens.value < light_min
        with st.container():
            st.markdown('<div class="metric-card">', unsafe_allow_html=True)
            render_metric_card(st, "☀️ 光照强度", light_intens.value,
                               "充足" if not is_light_alert else "不足",
                               "建议光照强度 ≥ 1000 lux", is_light_alert)
            st.markdown('</div>', unsafe_allow_html=True)

        # Light intensity trend chart with anomalies and predictions
        with st.container():
            st.markdown('<div class="chart-container">', unsafe_allow_html=True)
            light_data = fetch_last_day_data(session, LightIntensity)
            
            # Anomaly detection
            light_anomaly_indices = None
            if show_anomalies and light_data:
                light_df = pd.DataFrame([(d.timestamp, d.value) for d in light_data], columns=['timestamp', 'value'])
                light_anomalies = detect_anomalies(light_df, method='iqr')
                light_anomaly_indices = light_anomalies.get('value', [])
            
            # Short-term prediction
            light_prediction = None
            if show_predictions and light_data:
                try:
                    light_data_for_pred = [(d.timestamp, d.value) for d in light_data]
                    _, light_pred_df, _, _ = perform_prediction(light_data_for_pred, "Prophet", 1)
                    light_prediction = light_pred_df
                except Exception as e:
                    pass
            
            fig = create_trend_chart(light_data, "24 小时光照强度变化", "光照 (lux)", 
                                    thresholds={"最低建议值": light_min},
                                    prediction_data=light_prediction,
                                    anomaly_indices=light_anomaly_indices)
            if fig:
                st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})
            st.markdown('</div>', unsafe_allow_html=True)

    with row3_col2:
        # System info card
        with st.container():
            st.markdown('<div class="metric-card">', unsafe_allow_html=True)
            st.markdown("### 📊 系统信息")
            st.metric(label="数据点数量", value=len(temp_data) if temp_data else 0, help="最近24小时数据点数量")
            st.metric(label="数据获取时间",
                      value=light_intens.timestamp.strftime("%H:%M:%S") if light_intens else "N/A",
                      help="最新数据获取时间")
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
