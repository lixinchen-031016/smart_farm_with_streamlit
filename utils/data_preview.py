from datetime import timedelta

import streamlit as st

from models import AirTemperatureHumidity, SoilMoisture, SoilNutrient, LightIntensity
from utils.logger import log_operation


def fetch_last_day_data(session, model_class):
    """获取最近24小时的数据"""
    try:
        # 获取数据库中最新一条记录的时间
        latest_data = session.query(model_class).order_by(model_class.timestamp.desc()).first()
        if not latest_data:
            st.warning(f"没有找到{model_class.__name__}的数据")
            return None
            
        end_time = latest_data.timestamp
        start_time = end_time - timedelta(days=1)
        
        # 查询数据并按时间降序排列，确保获取的是最新数据
        data = session.query(model_class).filter(
            model_class.timestamp >= start_time,
            model_class.timestamp <= end_time
        ).order_by(model_class.timestamp.desc()).all()
        
        if not data:
            st.warning(f"没有找到{model_class.__name__}在最近24小时内的数据")
            return None
            
        return data[::-1]  # 将数据按时间升序返回
    except Exception as e:
        st.error(f"获取数据时发生错误: {str(e)}")
        return None


def create_line_chart(data_list, title, y_title, threshold=None):
    """创建折线图"""
    import plotly.graph_objects as go
    
    if not data_list:
        st.warning(f"没有可用的数据来创建'{title}'图表")
        return None
        
    # 确保数据对象有正确的属性
    try:
        if hasattr(data_list[0], 'value'):
            values = [data.value for data in data_list]
        elif hasattr(data_list[0], 'temperature'):
            values = [data.temperature for data in data_list]
        elif hasattr(data_list[0], 'humidity'):
            values = [data.humidity for data in data_list]
        else:
            st.error(f"数据对象缺少必要的值属性: {data_list[0]}")
            return None
            
        timestamps = [data.timestamp for data in data_list]
    except Exception as e:
        st.error(f"处理图表数据时出错: {str(e)}")
        return None
    
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=timestamps,
        y=values,
        mode='lines+markers',
        name=y_title,
        line=dict(color='#4CAF50', width=2)
    ))
    
    if threshold:
        if isinstance(threshold, (list, tuple)):
            fig.add_hline(y=threshold[0], line_dash="dash", line_color="red", annotation_text=f"最低阈值 {threshold[0]}")
            fig.add_hline(y=threshold[1], line_dash="dash", line_color="red", annotation_text=f"最高阈值 {threshold[1]}")
        else:
            fig.add_hline(y=threshold, line_dash="dash", line_color="red", annotation_text=f"阈值 {threshold}")
    
    fig.update_layout(
        title=title,
        xaxis_title="时间",
        yaxis_title=y_title,
        template="plotly_white",
        height=200,  # 降低图表高度
        margin=dict(l=20, r=20, t=40, b=20, pad=10)  # 增加内边距
    )
    return fig


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
    
    # 根据指标类型自动添加单位
    display_value = f"{value:.2f}" if isinstance(value, (int, float)) else value
    if "温度" in label:
        display_value += " °C"
    elif "湿度" in label:
        display_value += " %"
    elif "无机盐含量" in label:
        display_value += " ppm"
    elif "光照强度" in label:
        display_value += " lux"
        
    container.metric(label=label, value=display_value, delta=delta, help=help_text)
    container.markdown('</div>', unsafe_allow_html=True)

def render_data_metrics(session, username):
    """渲染数据指标卡片"""
    if st.button("🔄 实时更新数据", help="点击获取最新传感器数据"):
        air_temp_hum, soil_moist, soil_nutri, light_intens = fetch_latest_data(session)
        log_operation(username, "INFO", "数据预览-更新数据",
                     f"获取时间: {air_temp_hum.timestamp} 温度: {air_temp_hum.temperature:.2f}°C 湿度: {air_temp_hum.humidity:.2f}% 土壤湿度: {soil_moist.value:.2f}% 土壤营养含量: {soil_nutri.value:.2f}ppm 光照强度: {light_intens.value:.2f}lux")

        # 第一行指标卡片
        row1_col1, row1_col2 = st.columns(2)
        
        with row1_col1:
            is_temp_alert = not (20 <= air_temp_hum.temperature <= 30)
            render_metric_card(row1_col1, "🌡️ 空气温度", air_temp_hum.temperature,
                              "正常" if not is_temp_alert else "异常",
                              "适宜范围：20°C - 30°C", is_temp_alert)
            temp_data = fetch_last_day_data(session, AirTemperatureHumidity)
            fig = create_line_chart(temp_data, "24小时温度变化", "温度 (°C)", [20, 30])
            if fig:
                st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})
        
        with row1_col2:
            is_humidity_alert = not (40 <= air_temp_hum.humidity <= 70)
            render_metric_card(row1_col2, "💧 空气湿度", air_temp_hum.humidity,
                              "理想" if not is_humidity_alert else "注意",
                              "适宜范围：40% - 70%", is_humidity_alert)
            humidity_data = fetch_last_day_data(session, AirTemperatureHumidity)
            fig = create_line_chart(humidity_data, "24小时湿度变化", "湿度 (%)", [40, 70])
            if fig:
                st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})
        
        # 第二行指标卡片
        row2_col1, row2_col2 = st.columns(2)
        
        with row2_col1:
            is_soil_moist_alert = not (30 <= soil_moist.value <= 60)
            render_metric_card(row2_col1, "🌱 土壤湿度", soil_moist.value,
                              "适宜" if not is_soil_moist_alert else "需灌溉",
                              "适宜范围：30% - 60%", is_soil_moist_alert)
            soil_moist_data = fetch_last_day_data(session, SoilMoisture)
            fig = create_line_chart(soil_moist_data, "24小时土壤湿度变化", "湿度 (%)", [30, 60])
            if fig:
                st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})
        
        with row2_col2:
            is_nutri_alert = not (10 <= soil_nutri.value <= 20)
            render_metric_card(row2_col2, "🌱 土壤无机盐含量", soil_nutri.value,
                              "正常" if not is_nutri_alert else "需施肥",
                              "适宜范围：10ppm - 20ppm", is_nutri_alert)
            soil_nutri_data = fetch_last_day_data(session, SoilNutrient)
            fig = create_line_chart(soil_nutri_data, "24小时土壤养分变化", "养分 (ppm)", [10, 20])
            if fig:
                st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})
        
        # 第三行指标卡片
        row3_col1, row3_col2 = st.columns(2)
        
        with row3_col1:
            is_light_alert = light_intens.value < 1000
            render_metric_card(row3_col1, "☀️ 光照强度", light_intens.value,
                              "充足" if not is_light_alert else "不足",
                              "建议光照强度 ≥ 1000 lux", is_light_alert)
            light_data = fetch_last_day_data(session, LightIntensity)
            fig = create_line_chart(light_data, "24小时光照强度变化", "光照 (lux)", 1000)
            if fig:
                st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})

def fetch_latest_data(session):
    """获取最新传感器数据"""
    air_temp_hum = session.query(AirTemperatureHumidity).order_by(
        AirTemperatureHumidity.timestamp.desc()).first()
    soil_moist = session.query(SoilMoisture).order_by(SoilMoisture.timestamp.desc()).first()
    soil_nutri = session.query(SoilNutrient).order_by(SoilNutrient.timestamp.desc()).first()
    light_intens = session.query(LightIntensity).order_by(
        LightIntensity.timestamp.desc()).first()
    return air_temp_hum, soil_moist, soil_nutri, light_intens
