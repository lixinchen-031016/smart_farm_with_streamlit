import os
from datetime import datetime, timedelta

import numpy as np
import pandas as pd
from sqlalchemy import create_engine
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

from models import AirTemperatureHumidity, SoilMoisture, SoilNutrient, LightIntensity
from utils.logger import log_operation

Base = declarative_base()


def get_user_input():
    """获取并验证用户输入"""
    while True:
        start_date_str = input("请输入起始日期（格式：YYYY-MM-DD）: ")
        try:
            start_date = datetime.strptime(start_date_str, "%Y-%m-%d")
            break
        except ValueError:
            print("日期格式错误，请使用 YYYY-MM-DD 格式")

    while True:
        days_str = input("请输入要生成的天数（整数）: ")
        try:
            days = int(days_str)
            if days > 0:
                break
            print("天数必须为正整数")
        except ValueError:
            print("请输入有效的整数")
    
    while True:
        interval_str = input("请输入数据生成间隔时间（分钟，必须是1到1440之间的整数）: ")
        try:
            interval_minutes = int(interval_str)
            if 1 <= interval_minutes <= 1440:
                break
            print("间隔时间必须在1到1440分钟之间")
        except ValueError:
            print("请输入有效的整数")

    return start_date, days, interval_minutes


def generate_timestamps(start_date, days, interval_minutes=10):
    """生成时间戳序列"""
    timestamps = []
    current_time = start_date
    while (current_time - start_date).days < days:
        timestamps.append(current_time)
        current_time += timedelta(minutes=interval_minutes)
    return pd.DatetimeIndex(timestamps)


def generate_temperature(timestamps):
    """生成更精确的温度数据，考虑大棚保温效果"""
    # 基础温度随季节变化（年周期）
    base_temp = 20 + 5 * np.sin(2 * np.pi * (timestamps.dayofyear - 10) / 365)
    
    # 极端天气模拟（寒潮/热浪）
    season = (timestamps.dayofyear // 91) % 4  # 0:春季,1:夏季,2:秋季,3:冬季
    extreme_weather = np.random.choice([0, 1], size=len(timestamps), p=[0.95, 0.05])
    extreme_effect = np.where(extreme_weather, 
                            np.where(season == 1, 10, -10),  # 夏季热浪+10度，冬季寒潮-10度
                            0)
    
    # 昼夜周期变化（24小时周期）
    diurnal_cycle = 10 * np.sin(2 * np.pi * (timestamps.hour + timestamps.minute / 60) / 24)
    
    # 大棚保温效果（夜间保温，白天减弱）
    greenhouse_effect = 3 * (1 - np.sin(2 * np.pi * (timestamps.hour + timestamps.minute / 60) / 24))
    
    # 云量影响（随机因素）
    cloud_effect = np.random.choice([-2, -1, 0, 1, 2], size=len(timestamps), p=[0.1, 0.2, 0.4, 0.2, 0.1])
    
    # 随机噪声（更真实的微小波动）
    noise = np.random.normal(0, 0.5, len(timestamps))
    
    return np.round(base_temp + diurnal_cycle + greenhouse_effect + cloud_effect + extreme_effect + noise, 1)


def generate_humidity(temperature, timestamps):
    """生成更精确的湿度数据，考虑大棚通风情况"""
    # 雨季/旱季影响（夏季多雨，冬季干燥）
    season_factor = 0.5 * np.sin(2 * np.pi * (timestamps.dayofyear - 10) / 365)
    
    # 基础湿度随温度变化（温度越高，最大湿度越高）
    base_humidity = 60 + 30 * np.exp(-0.05 * (temperature - 15)) + 10 * season_factor
    
    # 降雨影响（随机因素，雨季概率更高）
    is_rainy_season = (timestamps.dayofyear > 150) & (timestamps.dayofyear < 240)  # 5-8月为雨季
    # 修改：为每个时间点单独生成降雨概率
    rain_prob = np.random.rand(len(timestamps))
    rain_effect = np.where(
        is_rainy_season,
        np.select(
            [rain_prob < 0.4, (rain_prob >= 0.4) & (rain_prob < 0.7), (rain_prob >= 0.7) & (rain_prob < 0.9), rain_prob >= 0.9],
            [15, 10, 5, 0]
        ),
        np.select(
            [rain_prob < 0.1, (rain_prob >= 0.1) & (rain_prob < 0.3), (rain_prob >= 0.3) & (rain_prob < 0.6), rain_prob >= 0.6],
            [15, 10, 5, 0]
        )
    )
    
    # 大棚通风效果（白天通风降低湿度）
    ventilation_effect = -5 * np.sin(2 * np.pi * (timestamps.hour + timestamps.minute / 60) / 24)
    
    # 随机噪声
    noise = np.random.normal(0, 3, len(timestamps))
    
    return np.clip(base_humidity + rain_effect + ventilation_effect + noise, 30, 100)


def generate_soil_moisture(humidity, temperature, timestamps):
    """生成更精确的土壤湿度数据，考虑自动灌溉系统"""
    # 雨季/旱季基础湿度调整
    is_dry_season = (timestamps.dayofyear < 60) | (timestamps.dayofyear > 300)  # 冬季和早春为旱季
    season_adjustment = np.where(is_dry_season, -15, 5)
    
    # 基础土壤湿度
    base_moisture = 0.6 * humidity + 0.3 * temperature + season_adjustment
    
    # 自动灌溉系统影响（每天定时灌溉）
    irrigation_schedule = (timestamps.hour == 6) & (np.random.rand(len(timestamps)) < 0.9)  # 早上6点灌溉，90%概率
    irrigation_amount = irrigation_schedule * np.random.uniform(15, 25, len(timestamps))
    
    # 蒸发损失（与温度和湿度有关）
    evaporation_loss = 0.05 * temperature * (1 - humidity / 100)
    
    # 随机噪声
    noise = np.random.normal(0, 2, len(timestamps))
    
    return np.clip(base_moisture + irrigation_amount - evaporation_loss + noise, 10, 100)


def generate_light_intensity(timestamps):
    """生成更精确的光照强度数据，考虑大棚覆盖材料"""
    # 阴雨天光照减弱
    is_rainy_day = np.random.rand(len(timestamps)) < 0.1  # 10%概率是阴雨天
    rain_reduction = np.where(is_rainy_day, 0.3, 1.0)  # 阴雨天光照减少70%
    
    # 计算日出和日落时间（简化模型）
    day_length = 12 + 6 * np.sin(2 * np.pi * timestamps.dayofyear / 365)
    sunrise = 6 - 3 * np.sin(2 * np.pi * timestamps.dayofyear / 365)
    sunset = sunrise + day_length
    
    # 白天/黑夜标识
    daylight = (timestamps.hour + timestamps.minute / 60 > sunrise) & \
               (timestamps.hour + timestamps.minute / 60 < sunset)
    
    # 基础光照强度（考虑季节性日照长度）
    base_light = 1200 * ((timestamps.hour + timestamps.minute / 60 - sunrise) / day_length) * daylight
    
    # 加入阴雨天气影响
    base_light *= rain_reduction
    
    # 大棚覆盖材料透光率（70%-90%）
    cover_transparency = np.random.uniform(0.7, 0.9, len(timestamps))
    
    return np.clip(base_light * cover_transparency, 0, 1500)


def generate_nutrients(timestamps):
    """模拟土壤营养成分，考虑作物吸收"""
    # 作物吸收速率（每天减少）
    absorption_rate = 0.05
    
    # 营养成分随时间缓慢减少
    base_nitrogen = 50 + np.random.normal(0, 5, len(timestamps)).cumsum() * 0.01 - np.arange(len(timestamps)) * absorption_rate
    base_phosphorus = 30 + np.random.normal(0, 3, len(timestamps)).cumsum() * 0.01 - np.arange(len(timestamps)) * absorption_rate
    base_potassium = 40 + np.random.normal(0, 4, len(timestamps)).cumsum() * 0.01 - np.arange(len(timestamps)) * absorption_rate

    # 施肥事件（定期补充营养）
    fertilizer_events = np.random.rand(len(timestamps)) < 0.05
    base_nitrogen += fertilizer_events * np.random.uniform(10, 20, len(timestamps))
    base_phosphorus += fertilizer_events * np.random.uniform(5, 10, len(timestamps))
    base_potassium += fertilizer_events * np.random.uniform(8, 15, len(timestamps))

    return {
        'Nitrogen': np.clip(base_nitrogen, 20, 100),
        'Phosphorus': np.clip(base_phosphorus, 10, 80),
        'Potassium': np.clip(base_potassium, 15, 90)
    }


def generate_data(start_date, days, interval_minutes=10):
    """生成模拟数据"""
    timestamps = generate_timestamps(start_date, days, interval_minutes)

    temperatures = generate_temperature(timestamps)
    humidities = generate_humidity(temperatures, timestamps)
    soil_moistures = generate_soil_moisture(humidities, temperatures, timestamps)
    light_intensities = generate_light_intensity(timestamps)

    nutrients = generate_nutrients(timestamps)
    salt_concentration = (nutrients['Nitrogen'] + nutrients['Phosphorus'] + nutrients['Potassium']) / 3

    return {
        'air': list(zip(timestamps, temperatures, humidities)),
        'soil_moisture': list(zip(timestamps, soil_moistures)),
        'soil_nutrient': list(zip(timestamps, salt_concentration)),
        'light': list(zip(timestamps, light_intensities))
    }


def insert_data_to_mysql(data, batch_size=1000):
    """批量插入数据到MySQL"""
    # 修改以下连接参数以匹配您的MySQL配置
    DATABASE_URI = os.getenv('DATABASE_URL')

    engine = create_engine(DATABASE_URI, pool_pre_ping=True)
    Base.metadata.create_all(engine)

    Session = sessionmaker(bind=engine)
    session = Session()

    try:
        # 创建记录列表
        air_records = [AirTemperatureHumidity(
            temperature=temp,
            humidity=humi,
            timestamp=ts
        ) for ts, temp, humi in data['air']]

        soil_moisture_records = [SoilMoisture(
            value=value,
            timestamp=ts
        ) for ts, value in data['soil_moisture']]

        soil_nutrient_records = [SoilNutrient(
            value=value,
            timestamp=ts
        ) for ts, value in data['soil_nutrient']]

        light_records = [LightIntensity(
            value=value,
            timestamp=ts
        ) for ts, value in data['light']]

        # 分批插入
        for i in range(0, len(air_records), batch_size):
            session.bulk_save_objects(air_records[i:i + batch_size])
            session.bulk_save_objects(soil_moisture_records[i:i + batch_size])
            session.bulk_save_objects(soil_nutrient_records[i:i + batch_size])
            session.bulk_save_objects(light_records[i:i + batch_size])
            session.commit()
        print(f"成功插入 {len(air_records)} 条数据")
        log_operation(
            user="system",
            log_level="INFO",
            action="数据插入",
            details=f"插入 {len(air_records)} 条数据")

    except SQLAlchemyError as e:
        session.rollback()
        log_operation(
            user="system",
            log_level="ERROR",
            action="数据插入失败",
            details=f"插入 {len(air_records)+len(soil_moisture_records)+len(soil_nutrient_records)+len(light_records)} 条数据失败: {str(e)}")
        print(f"数据库错误: {str(e)}")
    finally:
        session.close()


if __name__ == "__main__":
    # 获取用户输入
    start_date, days, interval_minutes = get_user_input()

    # 生成模拟数据
    log_operation("system", "INFO", "数据生成", "开始生成数据")
    print(f"\n正在生成 {days} 天的数据，起始日期: {start_date.strftime('%Y-%m-%d')}，间隔时间: {interval_minutes} 分钟")
    log_operation("system", "INFO", "数据生成", f"生成 {days} 天的数据，起始日期: {start_date.strftime('%Y-%m-%d')},间隔时间: {interval_minutes} 分钟")
    generated_data = generate_data(start_date, days)

    # 插入数据库
    log_operation("system", "INFO", "数据写入", "数据正在写入数据库")
    print("\n正在将数据写入数据库...")
    insert_data_to_mysql(generated_data)