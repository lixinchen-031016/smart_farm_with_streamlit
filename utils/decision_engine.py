from datetime import datetime, timedelta

import numpy as np
import streamlit as st

from models import AirTemperatureHumidity, SoilMoisture, LightIntensity
from utils.logger import log_operation
from utils.sensor_data import get_latest_sensor_data, get_historical_sensor_data


class DecisionEngine:
    def __init__(self, session, username):
        self.session = session
        self.username = username
        # 默认规则配置
        self.default_rules = {
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

    def get_historical_data(self, hours=24):
        """获取历史传感器数据用于趋势分析"""
        return get_historical_sensor_data(self.session, hours)

    def calculate_trend(self, data_points):
        """计算数据趋势"""
        if len(data_points) < 2:
            return 0
        
        # 简单线性回归计算趋势
        x = np.arange(len(data_points))
        y = np.array([point[1] for point in data_points])
        
        # 计算斜率
        slope = np.polyfit(x, y, 1)[0] if len(x) > 1 else 0
        return slope

    def analyze_trends(self, historical_data):
        """分析各项指标的趋势"""
        trends = {}
        
        # 分析温度趋势
        if historical_data['air']:
            temp_data = [(point[0], point[1]) for point in historical_data['air']]
            trends['temperature'] = self.calculate_trend(temp_data)
        
        # 分析湿度趋势
        if historical_data['air']:
            humidity_data = [(point[0], point[2]) for point in historical_data['air']]
            trends['humidity'] = self.calculate_trend(humidity_data)
        
        # 分析土壤湿度趋势
        if historical_data['soil_moisture']:
            trends['soil_moisture'] = self.calculate_trend(historical_data['soil_moisture'])
        
        # 分析光照趋势
        if historical_data['light']:
            trends['light_intensity'] = self.calculate_trend(historical_data['light'])
            
        return trends

    def evaluate_conditions(self):
        """评估所有传感器数据并生成建议"""
        # 使用优化版本获取最新数据
        latest_data = self.get_latest_sensor_data_optimized()
        historical_data = self.get_historical_data()
        trends = self.analyze_trends(historical_data)
        
        recommendations = []
        
        # 检查土壤湿度
        soil_moisture = latest_data['soil_moisture']
        soil_trend = trends.get('soil_moisture', 0)
        
        if soil_moisture < self.default_rules['soil_moisture']['low_threshold']:
            priority = 'high'
            if soil_trend < 0:  # 持续下降趋势
                message = f"土壤湿度低于30%({soil_moisture:.1f}%)且呈下降趋势，建议立即灌溉"
                reason = f"当前土壤湿度为{soil_moisture:.1f}%，低于阈值30%，且过去24小时呈下降趋势(斜率:{soil_trend:.4f})，预计将继续下降"
            else:
                message = f"土壤湿度低于30%({soil_moisture:.1f}%)，建议灌溉"
                reason = f"当前土壤湿度为{soil_moisture:.1f}%，低于阈值30%"
                
            recommendations.append({
                'type': 'irrigation',
                'message': message,
                'reason': reason,
                'priority': priority,
                'timestamp': datetime.now(),
                'current_value': soil_moisture,
                'threshold': self.default_rules['soil_moisture']['low_threshold']
            })
        elif soil_moisture > self.default_rules['soil_moisture']['high_threshold']:
            priority = 'low'
            message = f"土壤湿度高于60%({soil_moisture:.1f}%)，无需灌溉"
            reason = f"当前土壤湿度为{soil_moisture:.1f}%，高于阈值60%"
            
            recommendations.append({
                'type': 'irrigation',
                'message': message,
                'reason': reason,
                'priority': priority,
                'timestamp': datetime.now(),
                'current_value': soil_moisture,
                'threshold': self.default_rules['soil_moisture']['high_threshold']
            })

        # 检查温度
        temperature = latest_data['temperature']
        temp_trend = trends.get('temperature', 0)
        
        if temperature < self.default_rules['temperature']['low_threshold']:
            priority = 'medium'
            if temp_trend < 0:  # 持续下降趋势
                message = f"温度低于15℃({temperature:.1f}℃)且呈下降趋势，建议检查大棚保温"
                reason = f"当前温度为{temperature:.1f}℃，低于阈值15℃，且过去24小时呈下降趋势(斜率:{temp_trend:.4f})，需加强保温措施"
            else:
                message = f"温度低于15℃({temperature:.1f}℃)，建议检查大棚保温"
                reason = f"当前温度为{temperature:.1f}℃，低于阈值15℃"
                
            recommendations.append({
                'type': 'temperature',
                'message': message,
                'reason': reason,
                'priority': priority,
                'timestamp': datetime.now(),
                'current_value': temperature,
                'threshold': self.default_rules['temperature']['low_threshold']
            })
        elif temperature > self.default_rules['temperature']['high_threshold']:
            priority = 'medium'
            if temp_trend > 0:  # 持续上升趋势
                message = f"温度高于30℃({temperature:.1f}℃)且呈上升趋势，建议通风降温"
                reason = f"当前温度为{temperature:.1f}℃，高于阈值30℃，且过去24小时呈上升趋势(斜率:{temp_trend:.4f})，需加强通风"
            else:
                message = f"温度高于30℃({temperature:.1f}℃)，建议通风降温"
                reason = f"当前温度为{temperature:.1f}℃，高于阈值30℃"
                
            recommendations.append({
                'type': 'temperature',
                'message': message,
                'reason': reason,
                'priority': priority,
                'timestamp': datetime.now(),
                'current_value': temperature,
                'threshold': self.default_rules['temperature']['high_threshold']
            })

        # 检查湿度
        humidity = latest_data['humidity']
        humidity_trend = trends.get('humidity', 0)
        
        if humidity < self.default_rules['humidity']['low_threshold']:
            priority = 'medium'
            if humidity_trend < 0:  # 持续下降趋势
                message = f"空气湿度低于40%({humidity:.1f}%)且呈下降趋势，建议增湿"
                reason = f"当前空气湿度为{humidity:.1f}%，低于阈值40%，且过去24小时呈下降趋势(斜率:{humidity_trend:.4f})"
            else:
                message = f"空气湿度低于40%({humidity:.1f}%)，建议增湿"
                reason = f"当前空气湿度为{humidity:.1f}%，低于阈值40%"
                
            recommendations.append({
                'type': 'humidity',
                'message': message,
                'reason': reason,
                'priority': priority,
                'timestamp': datetime.now(),
                'current_value': humidity,
                'threshold': self.default_rules['humidity']['low_threshold']
            })
        elif humidity > self.default_rules['humidity']['high_threshold']:
            priority = 'medium'
            if humidity_trend > 0:  # 持续上升趋势
                message = f"空气湿度高于70%({humidity:.1f}%)且呈上升趋势，建议通风除湿"
                reason = f"当前空气湿度为{humidity:.1f}%，高于阈值70%，且过去24小时呈上升趋势(斜率:{humidity_trend:.4f})"
            else:
                message = f"空气湿度高于70%({humidity:.1f}%)，建议通风除湿"
                reason = f"当前空气湿度为{humidity:.1f}%，高于阈值70%"
                
            recommendations.append({
                'type': 'humidity',
                'message': message,
                'reason': reason,
                'priority': priority,
                'timestamp': datetime.now(),
                'current_value': humidity,
                'threshold': self.default_rules['humidity']['high_threshold']
            })

        # 检查光照
        light_intensity = latest_data['light_intensity']
        light_trend = trends.get('light_intensity', 0)
        
        if light_intensity < self.default_rules['light_intensity']['low_threshold']:
            priority = 'medium'
            if light_trend < 0:  # 持续下降趋势
                message = f"光照强度低于1000lux({light_intensity:.1f}lux)且呈下降趋势，建议补光"
                reason = f"当前光照强度为{light_intensity:.1f}lux，低于阈值1000lux，且过去24小时呈下降趋势(斜率:{light_trend:.4f})"
            else:
                message = f"光照强度低于1000lux({light_intensity:.1f}lux)，建议补光"
                reason = f"当前光照强度为{light_intensity:.1f}lux，低于阈值1000lux"
                
            recommendations.append({
                'type': 'light',
                'message': message,
                'reason': reason,
                'priority': priority,
                'timestamp': datetime.now(),
                'current_value': light_intensity,
                'threshold': self.default_rules['light_intensity']['low_threshold']
            })
        else:
            priority = 'low'
            message = f"光照强度正常({light_intensity:.1f}lux)"
            reason = f"当前光照强度为{light_intensity:.1f}lux，高于阈值1000lux，满足作物生长需求"
            
            recommendations.append({
                'type': 'light',
                'message': message,
                'reason': reason,
                'priority': priority,
                'timestamp': datetime.now(),
                'current_value': light_intensity,
                'threshold': self.default_rules['light_intensity']['low_threshold']
            })

        # 记录决策日志
        log_operation(self.username, "INFO", "自动化决策", 
                     f"生成{len(recommendations)}条建议")
        
        return recommendations

    def get_latest_sensor_data(self):
        """获取最新的传感器数据 - 优化版本，使用单次查询提高性能"""
        return get_latest_sensor_data(self.session)

    def get_latest_sensor_data_optimized(self):
        """获取最新的传感器数据 - 进一步优化版本"""
        return get_latest_sensor_data(self.session)

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
    .detail-section {
        background-color: #f0f2f6;
        padding: 10px;
        border-radius: 5px;
        margin-top: 10px;
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
        with st.spinner("正在分析环境数据和历史趋势..."):
            recommendations = engine.evaluate_conditions()
        
        if not recommendations:
            st.success("所有环境参数都在理想范围内！")
            return
            
        st.subheader("决策建议")
        for rec in recommendations:
            priority_class = ""
            if rec['priority'] == 'high':
                priority_class = "high-priority"
            elif rec['priority'] == 'medium':
                priority_class = "medium-priority"
                
            st.markdown(f"""
            <div class="alert-card {priority_class}">
                <h4>{rec['type'].capitalize()}建议</h4>
                <p><strong>{rec['message']}</strong></p>
                <div class="detail-section">
                    <p><strong>决策依据:</strong> {rec['reason']}</p>
                    <p><strong>当前值:</strong> {rec.get('current_value', 'N/A')} | <strong>阈值:</strong> {rec.get('threshold', 'N/A')}</p>
                </div>
                <small>{rec['timestamp'].strftime('%Y-%m-%d %H:%M:%S')}</small>
            </div>
            """, unsafe_allow_html=True)