import datetime

import streamlit as st

from models import AirTemperatureHumidity, SoilMoisture, SoilNutrient, LightIntensity
from utils.logger import log_operation
from utils.sensor_data import get_latest_sensor_data, get_last_day_data


def fetch_last_day_data(session, model_class):
    """获取最近24小时的数据"""
    try:
        data = get_last_day_data(session, model_class)
        if not data:
            st.warning(f"没有找到{model_class.__name__}在最近24小时内的数据")
        return data
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
        line=dict(color='#4CAF50', width=2),
        fill='tozeroy',  # 增加填充效果
        fillcolor='rgba(76, 175, 80, 0.2)'  # 半透明填充
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
        height=250,  # 调整图表高度
        margin=dict(l=20, r=20, t=40, b=20, pad=10),
        # 添加渐变背景
        plot_bgcolor='rgba(0,0,0,0)',
        paper_bgcolor='rgba(0,0,0,0)'
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
        text-align: center;
    }
    .metric-card {
        background: rgba(255, 255, 255, 0.9) !important;
        border-radius: 12px !important;
        padding: 1.5rem !important;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1) !important;
        transition: all 0.3s ease;
        height: 100%;
    }
    .metric-card:hover {
        transform: translateY(-5px);
        box-shadow: 0 6px 8px rgba(0,0,0,0.2) !important;
    }
    .alert-container {
        position: relative;
        padding: 5px;
        border-radius: 15px;
        height: 100%;
    }
    .alert-card {
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
    /* 新增系统状态面板样式 */
    .status-panel {
        background: linear-gradient(135deg, #2196F3 30%, #21CBF3 70%);
        color: white;
        padding: 1rem;
        border-radius: 10px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        margin-bottom: 1rem;
    }
    .status-panel.offline {
        background: linear-gradient(135deg, #f44336 30%, #ff9800 70%);
    }
    .status-panel.warning {
        background: linear-gradient(135deg, #ff9800 30%, #ffc107 70%);
    }
    /* 新增图表容器样式 */
    .chart-container {
        background: rgba(255, 255, 255, 0.7);
        border-radius: 10px;
        padding: 1rem;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        margin-top: 1rem;
    }
    /* 新增控制面板样式 */
    .control-panel {
        background: rgba(245, 245, 245, 0.9);
        border-radius: 10px;
        padding: 1rem;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        margin-bottom: 1rem;
    }
    </style>
    """

def render_header(session):
    """渲染页面头部"""
    st.markdown(get_styles(), unsafe_allow_html=True)
    st.markdown('<h1 class="main-header">🌱 智能农场数据监控中心</h1>', unsafe_allow_html=True)
    
    # 检查数据库连接状态
    db_status = check_database_status(session)
    
    # 添加系统状态面板，根据实际状态显示不同样式
    with st.container():
        status_class = "status-panel"
        status_text = "在线"
        update_text = "实时"
        connection_text = "稳定"
        
        if not db_status['connected']:
            status_class += " offline"
            status_text = "离线"
            update_text = "N/A"
            connection_text = "断开"
        elif db_status['latency'] > 1.0:  # 延迟大于1秒认为是警告状态
            status_class += " warning"
            connection_text = "延迟较高"
        
        last_update = datetime.datetime.now().strftime("%H:%M:%S")
        st.markdown(f'<div class="{status_class}">📡 系统状态: <b>{status_text}</b> | ⏱️ 最后更新: <b>{last_update}</b> | 🌐 连接状态: <b>{connection_text}</b></div>', unsafe_allow_html=True)

def check_database_status(session):
    """
    检查数据库连接状态
    返回包含连接状态和延迟信息的字典
    """
    import time
    try:
        start_time = time.time()
        # 执行一个简单的查询来测试连接
        session.query(AirTemperatureHumidity).first()
        latency = time.time() - start_time
        return {'connected': True, 'latency': latency}
    except Exception as e:
        return {'connected': False, 'latency': None, 'error': str(e)}

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
    elif isinstance(value, datetime.datetime):  # 新增对datetime类型的处理
        display_value = value.strftime("%Y-%m-%d %H:%M:%S")
        
    container.metric(label=label, value=display_value, delta=delta, help=help_text)
    container.markdown('</div>', unsafe_allow_html=True)

def render_data_metrics(session, username):
    """渲染数据指标卡片"""
    # 添加控制面板
    with st.container():
        st.markdown('<div class="control-panel">', unsafe_allow_html=True)
        col1, col2 = st.columns([3, 1])
        with col1:
            st.markdown("### 🎛️ 控制面板")
        with col2:
            # 添加刷新按钮
            if st.button("🔄 刷新数据", key="refresh_button"):
                # 重新获取最新数据
                air_temp_hum, soil_moist, soil_nutri, light_intens = fetch_latest_data(session)
                # 更新日志
                log_operation(username, "INFO", "数据预览-更新数据",
                             f"获取时间: {air_temp_hum.timestamp} 温度: {air_temp_hum.temperature:.2f}°C 湿度: {air_temp_hum.humidity:.2f}% 土壤湿度: {soil_moist.value:.2f}% 土壤营养含量: {soil_nutri.value:.2f}ppm 光照强度: {light_intens.value:.2f}lux")
                # 使用st.experimental_rerun()强制重新渲染页面
                st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)
    

        air_temp_hum, soil_moist, soil_nutri, light_intens = fetch_latest_data(session)
        log_operation(username, "INFO", "数据预览-更新数据",
                     f"获取时间: {air_temp_hum.timestamp} 温度: {air_temp_hum.temperature:.2f}°C 湿度: {air_temp_hum.humidity:.2f}% 土壤湿度: {soil_moist.value:.2f}% 土壤营养含量: {soil_nutri.value:.2f}ppm 光照强度: {light_intens.value:.2f}lux")

        # 第一行指标卡片
        row1_col1, row1_col2 = st.columns(2)
        
        with row1_col1:
            is_temp_alert = not (20 <= air_temp_hum.temperature <= 30)
            with st.container():
                st.markdown('<div class="metric-card">', unsafe_allow_html=True)
                render_metric_card(st, "🌡️ 空气温度", air_temp_hum.temperature,
                                  "正常" if not is_temp_alert else "异常",
                                  "适宜范围：20°C - 30°C", is_temp_alert)
                st.markdown('</div>', unsafe_allow_html=True)
            
            # 添加温度趋势图表
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
            
            # 添加湿度趋势图表
            with st.container():
                st.markdown('<div class="chart-container">', unsafe_allow_html=True)
                humidity_data = fetch_last_day_data(session, AirTemperatureHumidity)
                fig = create_line_chart(humidity_data, "24小时湿度变化", "湿度 (%)", [40, 70])
                if fig:
                    st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})
                st.markdown('</div>', unsafe_allow_html=True)
        
        # 第二行指标卡片
        row2_col1, row2_col2 = st.columns(2)
        
        with row2_col1:
            is_soil_moist_alert = not (30 <= soil_moist.value <= 60)
            with st.container():
                st.markdown('<div class="metric-card">', unsafe_allow_html=True)
                render_metric_card(st, "🌱 土壤湿度", soil_moist.value,
                                  "适宜" if not is_soil_moist_alert else "需灌溉",
                                  "适宜范围：30% - 60%", is_soil_moist_alert)
                st.markdown('</div>', unsafe_allow_html=True)
            
            # 添加土壤湿度趋势图表
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
            
            # 添加土壤养分趋势图表
            with st.container():
                st.markdown('<div class="chart-container">', unsafe_allow_html=True)
                soil_nutri_data = fetch_last_day_data(session, SoilNutrient)
                fig = create_line_chart(soil_nutri_data, "24小时土壤养分变化", "养分 (ppm)", [10, 20])
                if fig:
                    st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})
                st.markdown('</div>', unsafe_allow_html=True)
        
        # 第三行指标卡片 - 只显示光照强度
        row3_col1, row3_col2 = st.columns([2, 1])  # 调整列宽比例
        
        with row3_col1:
            is_light_alert = light_intens.value < 1000
            with st.container():
                st.markdown('<div class="metric-card">', unsafe_allow_html=True)
                render_metric_card(st, "☀️ 光照强度", light_intens.value,
                                  "充足" if not is_light_alert else "不足",
                                  "建议光照强度 ≥ 1000 lux", is_light_alert)
                st.markdown('</div>', unsafe_allow_html=True)
            
            # 添加光照强度趋势图表
            with st.container():
                st.markdown('<div class="chart-container">', unsafe_allow_html=True)
                light_data = fetch_last_day_data(session, LightIntensity)
                fig = create_line_chart(light_data, "24小时光照强度变化", "光照 (lux)", 1000)
                if fig:
                    st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})
                st.markdown('</div>', unsafe_allow_html=True)
        
        with row3_col2:
            # 添加系统信息卡片
            with st.container():
                st.markdown('<div class="metric-card">', unsafe_allow_html=True)
                st.markdown("### 📊 系统信息")
                st.metric(label="数据点数量", value=len(temp_data) if temp_data else 0, help="最近24小时数据点数量")
                st.metric(label="传感器状态", value="🟢 正常", help="所有传感器运行正常")
                st.metric(label="数据获取时间", value=light_intens.timestamp.strftime("%H:%M:%S") if light_intens else "N/A", help="最新数据获取时间")
                st.markdown('</div>', unsafe_allow_html=True)

def fetch_latest_data(session):
    """获取最新传感器数据"""
    sensor_data = get_latest_sensor_data(session)
    
    # 创建模拟对象以保持接口兼容性
    class MockSensorData:
        def __init__(self, **kwargs):
            for key, value in kwargs.items():
                setattr(self, key, value)
    
    air_temp_hum = MockSensorData(
        temperature=sensor_data['temperature'],
        humidity=sensor_data['humidity'],
        timestamp=datetime.datetime.now()
    )
    soil_moist = MockSensorData(value=sensor_data['soil_moisture'], timestamp=datetime.datetime.now())
    soil_nutri = MockSensorData(value=sensor_data['soil_nutrient'], timestamp=datetime.datetime.now())
    light_intens = MockSensorData(value=sensor_data['light_intensity'], timestamp=datetime.datetime.now())
    
    return air_temp_hum, soil_moist, soil_nutri, light_intens
