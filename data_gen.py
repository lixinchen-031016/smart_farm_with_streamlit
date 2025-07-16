import os

import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from sqlalchemy import create_engine, Column, Integer, Float, DateTime
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy.exc import SQLAlchemyError
from models import AirTemperatureHumidity,SoilMoisture,SoilNutrient,LightIntensity
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

    return start_date, days


def generate_timestamps(start_date, days, interval_minutes=10):
    """生成时间戳序列"""
    timestamps = []
    current_time = start_date
    while (current_time - start_date).days < days:
        timestamps.append(current_time)
        current_time += timedelta(minutes=interval_minutes)
    return pd.DatetimeIndex(timestamps)


def generate_temperature(timestamps):
    """模拟温度变化"""
    base_temp = 20 + 5 * np.sin(2 * np.pi * (timestamps.dayofyear - 10) / 365)
    diurnal_cycle = 10 * np.sin(2 * np.pi * (timestamps.hour + timestamps.minute / 60) / 24)
    noise = np.random.normal(0, 0.5, len(timestamps))
    return base_temp + diurnal_cycle + noise


def generate_humidity(temperature):
    """基于温度生成湿度"""
    base_humidity = 60 + 30 * np.exp(-0.05 * (temperature - 15))
    noise = np.random.normal(0, 3, len(temperature))
    return np.clip(base_humidity + noise, 30, 100)


def generate_soil_moisture(humidity, temperature):
    """基于空气湿度和温度生成土壤湿度"""
    base_moisture = 0.6 * humidity + 0.3 * temperature
    irrigation_events = np.random.rand(len(base_moisture)) < 0.2
    base_moisture += irrigation_events * np.random.uniform(15, 25, len(base_moisture))
    noise = np.random.normal(0, 2, len(base_moisture))
    return np.clip(base_moisture + noise, 10, 100)


def generate_light_intensity(timestamps):
    """模拟光照强度"""
    hour = timestamps.hour + timestamps.minute / 60
    light_cycle = 1000 * (1 + np.sin(2 * np.pi * (hour - 6) / 24)) / 2
    noise = np.random.normal(0, 50, len(light_cycle))
    return np.clip(light_cycle + noise, 0, 2000)


def generate_nutrients(timestamps):
    """模拟土壤营养成分"""
    base_nitrogen = 50 + np.random.normal(0, 5, len(timestamps)).cumsum() * 0.01
    base_phosphorus = 30 + np.random.normal(0, 3, len(timestamps)).cumsum() * 0.01
    base_potassium = 40 + np.random.normal(0, 4, len(timestamps)).cumsum() * 0.01

    fertilizer_events = np.random.rand(len(timestamps)) < 0.05
    base_nitrogen += fertilizer_events * np.random.uniform(5, 15, len(timestamps))
    base_phosphorus += fertilizer_events * np.random.uniform(3, 8, len(timestamps))
    base_potassium += fertilizer_events * np.random.uniform(4, 10, len(timestamps))

    return {
        'Nitrogen': np.clip(base_nitrogen, 20, 100),
        'Phosphorus': np.clip(base_phosphorus, 10, 80),
        'Potassium': np.clip(base_potassium, 15, 90)
    }


def generate_data(start_date, days):
    """生成模拟数据"""
    timestamps = generate_timestamps(start_date, days, interval_minutes=10)

    temperatures = generate_temperature(timestamps)
    humidities = generate_humidity(temperatures)
    soil_moistures = generate_soil_moisture(humidities, temperatures)
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
            log_operation(
                user="system",
                log_level="INFO",
                action="数据插入",
                details=f"插入 {len(air_records)+len(soil_moisture_records)+len(soil_nutrient_records)+len(light_records)} 条数据")
        print(f"成功插入 {len(air_records)+len(soil_moisture_records)+len(soil_nutrient_records)+len(light_records)} 条数据")

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
    start_date, days = get_user_input()

    # 生成模拟数据
    log_operation("system", "INFO", "数据生成", "开始生成数据")
    print(f"\n正在生成 {days} 天的数据，起始日期: {start_date.strftime('%Y-%m-%d')}")
    generated_data = generate_data(start_date, days)

    # 插入数据库
    log_operation("system", "INFO", "数据写入", "数据正在写入数据库")
    print("\n正在将数据写入数据库...")
    insert_data_to_mysql(generated_data)