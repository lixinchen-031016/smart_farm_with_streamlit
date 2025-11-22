"""
传感器数据访问模块
提供统一的传感器数据获取接口，供各个模块使用
"""

from datetime import datetime, timedelta
from sqlalchemy import text

from models import AirTemperatureHumidity, SoilMoisture, LightIntensity, SoilNutrient


def get_latest_sensor_data(session):
    """
    获取所有传感器的最新数据
    
    Args:
        session: 数据库会话对象
        
    Returns:
        dict: 包含所有传感器最新数据的字典
    """
    # 使用原生SQL查询一次性获取所有最新数据，提高查询效率
    query = text("""
        SELECT 
            (SELECT temperature FROM intelligent_farm_airtemperaturehumidity ORDER BY timestamp DESC LIMIT 1) as temperature,
            (SELECT humidity FROM intelligent_farm_airtemperaturehumidity ORDER BY timestamp DESC LIMIT 1) as humidity,
            (SELECT value FROM intelligent_farm_soilmoisture ORDER BY timestamp DESC LIMIT 1) as soil_moisture,
            (SELECT value FROM intelligent_farm_soilnutrient ORDER BY timestamp DESC LIMIT 1) as soil_nutrient,
            (SELECT value FROM intelligent_farm_light_intensity ORDER BY timestamp DESC LIMIT 1) as light_intensity
    """)
    
    result = session.execute(query).fetchone()
    
    if result:
        return {
            'temperature': result.temperature if result.temperature is not None else 0,
            'humidity': result.humidity if result.humidity is not None else 0,
            'soil_moisture': result.soil_moisture if result.soil_moisture is not None else 0,
            'soil_nutrient': result.soil_nutrient if result.soil_nutrient is not None else 0,
            'light_intensity': result.light_intensity if result.light_intensity is not None else 0
        }
    else:
        return {
            'temperature': 0,
            'humidity': 0,
            'soil_moisture': 0,
            'soil_nutrient': 0,
            'light_intensity': 0
        }


def get_historical_sensor_data(session, hours=24):
    """
    获取历史传感器数据用于趋势分析
    
    Args:
        session: 数据库会话对象
        hours: 获取多少小时的历史数据，默认24小时
        
    Returns:
        dict: 包含各传感器历史数据的字典
    """
    since = datetime.now() - timedelta(hours=hours)
    
    # 获取历史空气温湿度数据
    air_data = session.query(AirTemperatureHumidity).filter(
        AirTemperatureHumidity.timestamp >= since
    ).order_by(AirTemperatureHumidity.timestamp).all()
    
    # 获取历史土壤湿度数据
    soil_moisture_data = session.query(SoilMoisture).filter(
        SoilMoisture.timestamp >= since
    ).order_by(SoilMoisture.timestamp).all()
    
    # 获取历史土壤养分数据
    soil_nutrient_data = session.query(SoilNutrient).filter(
        SoilNutrient.timestamp >= since
    ).order_by(SoilNutrient.timestamp).all()
    
    # 获取历史光照强度数据
    light_data = session.query(LightIntensity).filter(
        LightIntensity.timestamp >= since
    ).order_by(LightIntensity.timestamp).all()
    
    return {
        'air': [(d.timestamp, d.temperature, d.humidity) for d in air_data],
        'soil_moisture': [(d.timestamp, d.value) for d in soil_moisture_data],
        'soil_nutrient': [(d.timestamp, d.value) for d in soil_nutrient_data],
        'light': [(d.timestamp, d.value) for d in light_data]
    }


def get_last_day_data(session, model_class):
    """
    获取最近24小时的数据
    
    Args:
        session: 数据库会话对象
        model_class: 数据模型类
        
    Returns:
        list: 按时间升序排列的数据列表
    """
    # 获取数据库中最新一条记录的时间
    latest_data = session.query(model_class).order_by(model_class.timestamp.desc()).first()
    if not latest_data:
        return None
        
    end_time = latest_data.timestamp
    start_time = end_time - timedelta(days=1)
    
    # 查询数据并按时间降序排列，确保获取的是最新数据
    data = session.query(model_class).filter(
        model_class.timestamp >= start_time,
        model_class.timestamp <= end_time
    ).order_by(model_class.timestamp.desc()).all()
    
    if not data:
        return None
        
    return data[::-1]  # 将数据按时间升序返回