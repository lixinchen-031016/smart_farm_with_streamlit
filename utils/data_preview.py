from datetime import datetime
import streamlit as st
from models import AirTemperatureHumidity, SoilMoisture, SoilNutrient, LightIntensity
from utils.logger import log_operation

def get_styles():
    """返回数据预览页面的CSS样式"""
    return """
    <style>
    .main-header {
        background: linear-gradient(135deg, #4CAF50 30%, #8BC34A 70%);
        color: white;
        padding: 2rem;
        border-radius: 15px;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        margin-bottom: 2rem;
    }
    .metric-card {
        background: rgba(255, 255, 255, 0.9) !important;
        border-radius: 12px !important;
        padding: 1.5rem !important;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1) !important;
        transition: all 0.3s ease;
    }
    .metric-card:hover {
        transform: translateY(-5px);
        box-shadow: 0-6px 8px rgba(0,0,0,0.2) !important;
    }
    .alert-container {
        position: relative;
        padding: 5px;
        border-radius: 15px;
    }
    .alert-container .alert-card {
        position: absolute;
        top: 0;
        left: 0;
        right: 0;
        bottom: 0;
        border-radius: 15px;
        animation: pulse 1.5s infinite;
    }
    @keyframes pulse {
        0% { box-shadow: 0 0 0 0 rgba(255,82,82,0.4); }
        70% { box-shadow: 0 0 0 10px rgba(255,82,82,0); }
        100% { box-shadow: 0 0 0 0 rgba(255,82,82,0); }
    }
    </style>
    """

def render_header():
    """渲染页面头部"""
    st.markdown(get_styles(), unsafe_allow_html=True)
    st.markdown('<h1 class="main-header">🌱 智能农场数据监控中心</h1>', unsafe_allow_html=True)
    st.markdown("---")

def render_metric_card(container, label, value, delta, help_text, is_alert=False):
    """渲染一个指标卡"""
    alert_card = '<div class="alert-card"></div>' if is_alert else ''
    container.markdown(f'<div class="alert-container">{alert_card}', unsafe_allow_html=True)
    container.metric(label=label, value=value, delta=delta, help=help_text)
    container.markdown('</div>', unsafe_allow_html=True)

def render_data_metrics(session, username):
    """渲染数据指标卡片"""
    if st.button("🔄 实时更新数据", help="点击获取最新传感器数据"):
        air_temp_hum, soil_moist, soil_nutri, light_intens = fetch_latest_data(session)
        log_operation(username, "INFO", "数据预览-更新数据",
                     f"获取时间: {air_temp_hum.timestamp} 温度: {air_temp_hum.temperature} 湿度: {air_temp_hum.humidity} 土壤湿度: {soil_moist.value} 土壤营养含量: {soil_nutri.value} 光照强度: {light_intens.value}")

        # 使用卡片布局展示数据
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            is_temp_alert = not (20 <= air_temp_hum.temperature <= 30)
            render_metric_card(col1, "🌡️ 空气温度", f"{air_temp_hum.temperature} °C",
                              "正常" if not is_temp_alert else "异常",
                              "适宜范围：20°C - 30°C", is_temp_alert)
        
        with col2:
            is_humidity_alert = not (40 <= air_temp_hum.humidity <= 70)
            render_metric_card(col2, "💧 空气湿度", f"{air_temp_hum.humidity} %",
                              "理想" if not is_humidity_alert else "注意",
                              "适宜范围：40% - 70%", is_humidity_alert)
        
        with col3:
            is_soil_moist_alert = not (30 <= soil_moist.value <= 60)
            render_metric_card(col3, "🌱 土壤湿度", f"{soil_moist.value} %",
                              "适宜" if not is_soil_moist_alert else "需灌溉",
                              "适宜范围：30% - 60%", is_soil_moist_alert)
        
        with col4:
            is_nutri_alert = not (10 <= soil_nutri.value <= 20)
            render_metric_card(col4, "🌱 土壤无机盐含量", f"{soil_nutri.value} ppm",
                              "正常" if not is_nutri_alert else "需施肥",
                              "适宜范围：10ppm - 20ppm", is_nutri_alert)

        col5, col6 = st.columns(2)
        with col5:
            is_light_alert = light_intens.value < 1000
            render_metric_card(col5, "☀️ 光照强度", f"{light_intens.value} lux",
                              "充足" if not is_light_alert else "不足",
                              "建议光照强度 ≥ 1000 lux", is_light_alert)
        
        with col6:
            st.metric(label="📅 数据更新时间", 
                     value=f"{air_temp_hum.timestamp.strftime('%Y-%m-%d %H:%M')}",
                     help="最新数据采集时间")

def fetch_latest_data(session):
    """获取最新传感器数据"""
    air_temp_hum = session.query(AirTemperatureHumidity).order_by(
        AirTemperatureHumidity.timestamp.desc()).first()
    soil_moist = session.query(SoilMoisture).order_by(SoilMoisture.timestamp.desc()).first()
    soil_nutri = session.query(SoilNutrient).order_by(SoilNutrient.timestamp.desc()).first()
    light_intens = session.query(LightIntensity).order_by(
        LightIntensity.timestamp.desc()).first()
    return air_temp_hum, soil_moist, soil_nutri, light_intens