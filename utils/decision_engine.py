import streamlit as st
from datetime import datetime
from models import AirTemperatureHumidity, SoilMoisture, SoilNutrient, LightIntensity
from utils.logger import log_operation

class DecisionEngine:
    def __init__(self, session, username):
        self.session = session
        self.username = username
        self.rules = {
            'soil_moisture': {
                'low_threshold': 30,
                'high_threshold': 60,
                'message': {
                    'low': "土壤湿度低于30%，建议立即灌溉",
                    'high': "土壤湿度高于60%，无需灌溉"
                }
            },
            'temperature': {
                'low_threshold': 15,
                'high_threshold': 30,
                'message': {
                    'low': "温度低于15℃，建议检查大棚保温",
                    'high': "温度高于30℃，建议通风降温"
                }
            },
            'humidity': {
                'low_threshold': 40,
                'high_threshold': 70,
                'message': {
                    'low': "空气湿度低于40%，建议增湿",
                    'high': "空气湿度高于70%，建议通风除湿"
                }
            },
            'light_intensity': {
                'low_threshold': 1000,
                'message': {
                    'low': "光照强度低于1000lux，建议补光",
                    'normal': "光照强度正常"
                }
            }
        }

    def evaluate_conditions(self):
        """评估所有传感器数据并生成建议"""
        latest_data = self.get_latest_sensor_data()
        recommendations = []
        
        # 检查土壤湿度
        soil_moisture = latest_data['soil_moisture']
        if soil_moisture < self.rules['soil_moisture']['low_threshold']:
            recommendations.append({
                'type': 'irrigation',
                'message': self.rules['soil_moisture']['message']['low'],
                'priority': 'high',
                'timestamp': datetime.now()
            })
        elif soil_moisture > self.rules['soil_moisture']['high_threshold']:
            recommendations.append({
                'type': 'irrigation',
                'message': self.rules['soil_moisture']['message']['high'],
                'priority': 'low',
                'timestamp': datetime.now()
            })

        # 检查温度
        temperature = latest_data['temperature']
        if temperature < self.rules['temperature']['low_threshold']:
            recommendations.append({
                'type': 'temperature',
                'message': self.rules['temperature']['message']['low'],
                'priority': 'medium',
                'timestamp': datetime.now()
            })
        elif temperature > self.rules['temperature']['high_threshold']:
            recommendations.append({
                'type': 'temperature',
                'message': self.rules['temperature']['message']['high'],
                'priority': 'medium',
                'timestamp': datetime.now()
            })

        # 检查湿度
        humidity = latest_data['humidity']
        if humidity < self.rules['humidity']['low_threshold']:
            recommendations.append({
                'type': 'humidity',
                'message': self.rules['humidity']['message']['low'],
                'priority': 'medium',
                'timestamp': datetime.now()
            })
        elif humidity > self.rules['humidity']['high_threshold']:
            recommendations.append({
                'type': 'humidity',
                'message': self.rules['humidity']['message']['high'],
                'priority': 'medium',
                'timestamp': datetime.now()
            })

        # 检查光照
        light_intensity = latest_data['light_intensity']
        if light_intensity < self.rules['light_intensity']['low_threshold']:
            recommendations.append({
                'type': 'light',
                'message': self.rules['light_intensity']['message']['low'],
                'priority': 'medium',
                'timestamp': datetime.now()
            })
        else:
            recommendations.append({
                'type': 'light',
                'message': self.rules['light_intensity']['message']['normal'],
                'priority': 'low',
                'timestamp': datetime.now()
            })

        # 记录决策日志
        log_operation(self.username, "INFO", "自动化决策", 
                     f"生成{len(recommendations)}条建议")
        
        return recommendations

    def get_latest_sensor_data(self):
        """获取最新的传感器数据"""
        air_data = self.session.query(AirTemperatureHumidity).order_by(
            AirTemperatureHumidity.timestamp.desc()).first()
        soil_moisture = self.session.query(SoilMoisture).order_by(
            SoilMoisture.timestamp.desc()).first()
        light_intensity = self.session.query(LightIntensity).order_by(
            LightIntensity.timestamp.desc()).first()
        
        return {
            'temperature': air_data.temperature if air_data else 0,
            'humidity': air_data.humidity if air_data else 0,
            'soil_moisture': soil_moisture.value if soil_moisture else 0,
            'light_intensity': light_intensity.value if light_intensity else 0
        }

def show_decision_engine(session, username):
    """显示决策引擎UI"""
    st.title("🤖 自动化决策引擎")
    st.markdown("""
    <style>
    .alert-card {
        border-left: 5px solid #4CAF50;
        padding: 1rem;
        margin: 1rem 0;
        background: rgba(76, 175, 80, 0.1);
        border-radius: 8px;
    }
    .high-priority {
        border-left-color: #F44336 !important;
        background: rgba(244, 67, 54, 0.1) !important;
        animation: pulse 2s infinite;
    }
    .medium-priority {
        border-left-color: #FFC107 !important;
        background: rgba(255, 193, 7, 0.1) !important;
    }
    @keyframes pulse {
        0% { box-shadow: 0 0 0 0 rgba(244, 67, 54, 0.4); }
        70% { box-shadow: 0 0 0 10px rgba(244, 67, 54, 0); }
        100% { box-shadow: 0 0 0 0 rgba(244, 67, 54, 0); }
    }
    </style>
    """, unsafe_allow_html=True)

    engine = DecisionEngine(session, username)
    
    if st.button("评估当前环境条件"):
        recommendations = engine.evaluate_conditions()
        
        if not recommendations:
            st.success("所有环境参数都在理想范围内！")
            return
            
        for rec in recommendations:
            priority_class = ""
            if rec['priority'] == 'high':
                priority_class = "high-priority"
            elif rec['priority'] == 'medium':
                priority_class = "medium-priority"
                
            st.markdown(f"""
            <div class="alert-card {priority_class}">
                <h4>{rec['type'].capitalize()}建议</h4>
                <p>{rec['message']}</p>
                <small>{rec['timestamp'].strftime('%Y-%m-%d %H:%M:%S')}</small>
            </div>
            """, unsafe_allow_html=True)