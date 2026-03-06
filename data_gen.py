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
    """获取并验证用户输入，提供更友好的交互体验"""
    print("=" * 50)
    print("🚜 智能大棚数据生成器")
    print("=" * 50)

    # 获取起始日期
    while True:
        start_date_str = input("📅 请输入起始日期（格式：YYYY-MM-DD，如：2024-01-01）: ")
        try:
            start_date = datetime.strptime(start_date_str, "%Y-%m-%d")
            if start_date.year < 2020:
                print("⚠️  建议使用2020年以后的日期以获得更真实的现代农业数据")
                confirm = input("是否继续使用此日期？(y/n): ")
                if confirm.lower() != 'y':
                    continue
            break
        except ValueError:
            print("❌ 日期格式错误，请使用 YYYY-MM-DD 格式")

    # 获取天数
    while True:
        days_str = input("🗓️  请输入要生成的天数（建议1-365天）: ")
        try:
            days = int(days_str)
            if days <= 0:
                print("❌ 天数必须为正整数")
            elif days > 1000:
                print("⚠️  天数较大，可能需要较长时间生成")
                confirm = input("是否继续？(y/n): ")
                if confirm.lower() == 'y':
                    break
            else:
                break
        except ValueError:
            print("❌ 请输入有效的整数")

    # 获取采样间隔
    while True:
        print("\n⏱️  数据采样间隔选项：")
        print("  1. 每分钟（高频监测）")
        print("  2. 每10分钟（标准监测）")
        print("  3. 每小时（节能监测）")
        print("  4. 自定义间隔")

        choice = input("请选择采样间隔（1-4）: ")

        if choice == '1':
            interval_minutes = 1
            break
        elif choice == '2':
            interval_minutes = 10
            break
        elif choice == '3':
            interval_minutes = 60
            break
        elif choice == '4':
            while True:
                interval_str = input("请输入自定义间隔时间（分钟，1-1440）: ")
                try:
                    interval_minutes = int(interval_str)
                    if 1 <= interval_minutes <= 1440:
                        break
                    print("❌ 间隔时间必须在1到1440分钟之间")
                except ValueError:
                    print("❌ 请输入有效的整数")
            break
        else:
            print("❌ 请输入1-4之间的数字")

    # 显示生成预览
    total_points = int((days * 24 * 60) / interval_minutes)
    print(f"\n📊 数据生成预览：")
    print(f"   • 起始日期: {start_date.strftime('%Y-%m-%d')}")
    print(f"   • 持续天数: {days} 天")
    print(f"   • 采样间隔: {interval_minutes} 分钟")
    print(f"   • 预计数据点: {total_points:,} 个")

    confirm = input("\n✅ 确认生成以上数据？(y/n): ")
    if confirm.lower() != 'y':
        print("❌ 数据生成已取消")
        exit()

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
    """生成更真实的温度数据，考虑大棚环境特征"""
    # 基础温度随季节和地理位置变化
    # 北半球典型农业区域温度模式
    seasonal_base = 18 + 8 * np.sin(2 * np.pi * (timestamps.dayofyear - 80) / 365)

    # 日变化模式（更真实的温室效应）
    hour_float = timestamps.hour + timestamps.minute / 60
    # 温室日温差模式：升温快，降温慢
    daily_variation = 12 * np.sin(np.pi * (hour_float - 6) / 12)  # 6点到18点升温
    daily_variation = np.maximum(daily_variation, daily_variation * 0.3)  # 夜间保温效果

    # 大棚保温系数（根据外界温度调节）
    greenhouse_insulation = np.where(seasonal_base > 15, 4.0, 6.0)  # 冬季保温更好

    # 天气影响因子
    weather_factor = np.random.choice(
        [-3, -1, 0, 1, 2],  # 晴天、多云、阴天、小雨、大雨
        size=len(timestamps),
        p=[0.25, 0.35, 0.25, 0.1, 0.05]
    )

    # 极端天气事件（热浪、寒潮）
    extreme_event = np.zeros(len(timestamps))
    # 热浪（夏季）
    summer_mask = (timestamps.month >= 6) & (timestamps.month <= 8)
    heat_wave = np.random.choice([0, 1], size=len(timestamps), p=[0.97, 0.03]) & summer_mask
    extreme_event += heat_wave * np.random.uniform(5, 12, len(timestamps))

    # 寒潮（冬季）
    winter_mask = (timestamps.month >= 12) | (timestamps.month <= 2)
    cold_wave = np.random.choice([0, 1], size=len(timestamps), p=[0.97, 0.03]) & winter_mask
    extreme_event -= cold_wave * np.random.uniform(4, 8, len(timestamps))

    # 通风降温效果（白天高温时）
    ventilation_cooling = np.where(
        (daily_variation > 8) & (np.random.rand(len(timestamps)) < 0.3),
        -np.random.uniform(1, 3, len(timestamps)),
        0
    )

    # 微气候扰动
    microclimate_noise = np.random.normal(0, 0.8, len(timestamps))
    # 添加短期相关性（1-2小时内的温度连续性）
    for i in range(1, len(timestamps)):
        if abs((timestamps[i] - timestamps[i - 1]).total_seconds()) <= 7200:  # 2小时内
            microclimate_noise[i] = 0.7 * microclimate_noise[i - 1] + 0.3 * microclimate_noise[i]

    temperature = (seasonal_base +
                   daily_variation +
                   greenhouse_insulation +
                   weather_factor +
                   extreme_event +
                   ventilation_cooling +
                   microclimate_noise)

    # 确保温度在合理范围内
    return np.clip(np.round(temperature, 1), 5, 45)


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
            [rain_prob < 0.4, (rain_prob >= 0.4) & (rain_prob < 0.7), (rain_prob >= 0.7) & (rain_prob < 0.9),
             rain_prob >= 0.9],
            [15, 10, 5, 0]
        ),
        np.select(
            [rain_prob < 0.1, (rain_prob >= 0.1) & (rain_prob < 0.3), (rain_prob >= 0.3) & (rain_prob < 0.6),
             rain_prob >= 0.6],
            [15, 10, 5, 0]
        )
    )

    # 大棚通风效果（白天通风降低湿度）
    ventilation_effect = -5 * np.sin(2 * np.pi * (timestamps.hour + timestamps.minute / 60) / 24)

    # 随机噪声
    noise = np.random.normal(0, 3, len(timestamps))

    return np.clip(base_humidity + rain_effect + ventilation_effect + noise, 30, 100)


def generate_soil_moisture(humidity, temperature, timestamps):
    """生成更真实的土壤湿度数据，考虑作物根系吸水和土壤特性"""
    # 土壤基础含水量（受气候和土壤类型影响）
    base_soil_moisture = 35 + 0.3 * humidity + 0.2 * np.maximum(25 - temperature, 0)

    # 季节性土壤湿度模式
    seasonal_soil = 10 * np.sin(2 * np.pi * (timestamps.dayofyear - 100) / 365)

    # 作物生长阶段影响（根系吸水）
    # 作物生长旺盛期（5-9月）吸水更强
    growing_season = (timestamps.month >= 5) & (timestamps.month <= 9)
    crop_water_uptake = np.where(
        growing_season,
        -np.random.uniform(0.1, 0.3, len(timestamps)),
        -np.random.uniform(0.02, 0.1, len(timestamps))
    )

    # 智能灌溉系统
    # 根据土壤湿度和时间决定灌溉
    irrigation_needed = (base_soil_moisture + seasonal_soil < 40) & (
            (timestamps.hour == 6) | (timestamps.hour == 18)  # 早晚灌溉时间
    )
    irrigation_success = irrigation_needed & (np.random.rand(len(timestamps)) < 0.95)
    irrigation_addition = irrigation_success * np.random.uniform(12, 20, len(timestamps))

    # 蒸发蒸腾损失（ET）
    # 综合考虑温度、湿度、风速等因素
    et_base = 0.08 * np.maximum(temperature - 15, 0) * (1 - humidity / 100)
    # 白天蒸发更强
    daytime_et = et_base * (1 + 0.5 * np.sin(np.pi * (timestamps.hour - 6) / 12))

    # 降雨入渗补给
    precipitation_effect = np.zeros(len(timestamps))
    rainy_conditions = np.random.choice([0, 1], size=len(timestamps), p=[0.85, 0.15])
    precipitation_effect = rainy_conditions * np.random.uniform(5, 15, len(timestamps))

    # 土壤水分运移滞后效应
    soil_memory = np.zeros(len(timestamps))
    for i in range(1, len(timestamps)):
        time_diff_hours = (timestamps[i] - timestamps[i - 1]).total_seconds() / 3600
        if time_diff_hours <= 6:  # 短期内的变化较缓和
            soil_memory[i] = 0.9 * soil_memory[i - 1] + 0.1 * np.random.normal(0, 1.5)
        else:
            soil_memory[i] = np.random.normal(0, 1.5)

    # 土壤层次差异（表层vs深层）
    depth_factor = np.random.uniform(0.8, 1.2, len(timestamps))  # 不同深度传感器差异

    soil_moisture = (base_soil_moisture +
                     seasonal_soil +
                     crop_water_uptake.cumsum() * 0.1 +  # 累积效应
                     irrigation_addition -
                     daytime_et +
                     precipitation_effect +
                     soil_memory) * depth_factor

    return np.clip(np.round(soil_moisture, 1), 15, 85)


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
    """生成更真实的土壤营养成分数据，考虑作物生长周期和施肥管理"""
    # 作物生长周期影响营养吸收
    growth_stage = np.sin(2 * np.pi * timestamps.dayofyear / 365)  # 年度生长周期
    # 生长期（4-9月）营养消耗更快
    growing_season = (timestamps.month >= 4) & (timestamps.month <= 9)
    seasonal_absorption = np.where(growing_season, 0.08, 0.02)  # 生长期吸收率更高

    # 基础营养水平（考虑土壤本底值）
    base_nitrogen = 45 + 10 * np.sin(2 * np.pi * timestamps.dayofyear / 365)
    base_phosphorus = 25 + 8 * np.sin(2 * np.pi * (timestamps.dayofyear - 30) / 365)
    base_potassium = 35 + 12 * np.sin(2 * np.pi * (timestamps.dayofyear - 60) / 365)

    # 营养元素间的相互作用
    # 氮磷钾协同效应：一种元素充足时促进其他元素吸收
    nutrient_interaction = np.random.uniform(0.9, 1.1, len(timestamps))

    # 施肥管理系统
    # 基础施肥计划（每月1号和15号）
    monthly_fertilizer = ((timestamps.day == 1) | (timestamps.day == 15)) & (timestamps.hour == 8)
    # 根据作物需求调整施肥量
    crop_demand = 1 + 0.5 * np.abs(growth_stage)  # 生长期需求更高

    # 不同营养元素的施肥
    nitrogen_fertilizer = monthly_fertilizer * np.random.uniform(15, 25, len(timestamps)) * crop_demand
    phosphorus_fertilizer = monthly_fertilizer * np.random.uniform(8, 15, len(timestamps)) * crop_demand
    potassium_fertilizer = monthly_fertilizer * np.random.uniform(12, 20, len(timestamps)) * crop_demand

    # 有机肥施用（季度性）
    organic_fertilizer = (timestamps.dayofyear % 90 == 0) & (np.random.rand(len(timestamps)) < 0.7)
    organic_boost = organic_fertilizer * np.random.uniform(5, 12, len(timestamps))

    # 营养流失（雨水冲刷、挥发等）
    rainfall_days = np.random.choice([True, False], size=len(timestamps), p=[0.2, 0.8])
    leaching_loss = rainfall_days * np.random.uniform(0.5, 2.0, len(timestamps))

    # 土壤缓冲效应（营养变化相对缓慢）
    nutrient_stability = np.zeros(len(timestamps))
    for i in range(1, len(timestamps)):
        time_diff_days = (timestamps[i] - timestamps[i - 1]).total_seconds() / 86400
        if time_diff_days <= 1:  # 相邻天数
            nutrient_stability[i] = 0.95 * nutrient_stability[i - 1] + 0.05 * np.random.normal(0, 0.5)
        else:
            nutrient_stability[i] = np.random.normal(0, 0.5)

    # 计算最终营养含量
    nitrogen = (base_nitrogen -
                np.cumsum(seasonal_absorption) * 0.1 +  # 累积吸收
                nitrogen_fertilizer +
                organic_boost * 0.7 -  # 有机肥主要补充氮
                leaching_loss * 0.3 +  # 氮易流失
                nutrient_stability) * nutrient_interaction

    phosphorus = (base_phosphorus -
                  np.cumsum(seasonal_absorption) * 0.05 +  # 磷吸收较慢
                  phosphorus_fertilizer +
                  organic_boost * 0.3 -  # 有机肥补充磷
                  leaching_loss * 0.1 +  # 磷不易流失
                  nutrient_stability * 0.8) * nutrient_interaction

    potassium = (base_potassium -
                 np.cumsum(seasonal_absorption) * 0.08 +  # 钾吸收中等
                 potassium_fertilizer +
                 organic_boost * 0.5 -  # 有机肥补充钾
                 leaching_loss * 0.2 +  # 钾中等流失
                 nutrient_stability * 0.9) * nutrient_interaction

    return {
        'Nitrogen': np.clip(np.round(nitrogen, 1), 20, 120),
        'Phosphorus': np.clip(np.round(phosphorus, 1), 10, 90),
        'Potassium': np.clip(np.round(potassium, 1), 15, 100)
    }


def generate_data(start_date, days, interval_minutes=10):
    """生成更真实的模拟数据，包含环境因素相关性"""
    timestamps = generate_timestamps(start_date, days, interval_minutes)

    # 生成温度数据
    temperatures = generate_temperature(timestamps)

    # 基于温度生成湿度（考虑物理相关性）
    humidities = generate_humidity(temperatures, timestamps)

    # 基于温湿度生成土壤湿度
    soil_moistures = generate_soil_moisture(humidities, temperatures, timestamps)

    # 生成光照强度
    light_intensities = generate_light_intensity(timestamps)

    # 生成营养成分
    nutrients = generate_nutrients(timestamps)

    # 计算综合盐分浓度（基于营养成分）
    salt_concentration = (nutrients['Nitrogen'] * 0.4 +
                          nutrients['Phosphorus'] * 0.3 +
                          nutrients['Potassium'] * 0.3)

    # 添加传感器误差和校准偏移
    def add_sensor_noise(data, noise_level=1.0):
        """为传感器数据添加现实的噪声"""
        # 系统性偏差（传感器校准问题）
        calibration_offset = np.random.normal(0, noise_level * 0.5)
        # 随机噪声
        random_noise = np.random.normal(0, noise_level, len(data))
        # 短期漂移
        drift = np.cumsum(np.random.normal(0, noise_level * 0.1, len(data))) * 0.01
        return data + calibration_offset + random_noise + drift

    # 为不同类型传感器添加适当噪声
    temperatures = add_sensor_noise(temperatures, 0.3)
    humidities = add_sensor_noise(humidities, 1.0)
    soil_moistures = add_sensor_noise(soil_moistures, 1.5)
    light_intensities = add_sensor_noise(light_intensities, 10.0)
    salt_concentration = add_sensor_noise(salt_concentration, 2.0)

    # 确保数据在合理范围内
    temperatures = np.clip(temperatures, 5, 45)
    humidities = np.clip(humidities, 20, 100)
    soil_moistures = np.clip(soil_moistures, 15, 85)
    light_intensities = np.clip(light_intensities, 0, 2000)
    salt_concentration = np.clip(salt_concentration, 15, 100)

    return {
        'air': list(zip(timestamps, np.round(temperatures, 1), np.round(humidities, 1))),
        'soil_moisture': list(zip(timestamps, np.round(soil_moistures, 1))),
        'soil_nutrient': list(zip(timestamps, np.round(salt_concentration, 1))),
        'light': list(zip(timestamps, np.round(light_intensities, 0))),
        'nutrients_detail': nutrients  # 详细的营养成分数据
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
            details=f"插入 {len(air_records) + len(soil_moisture_records) + len(soil_nutrient_records) + len(light_records)} 条数据失败: {str(e)}")
        print(f"数据库错误: {str(e)}")
    finally:
        session.close()


if __name__ == "__main__":
    try:
        # 获取用户输入
        start_date, days, interval_minutes = get_user_input()

        # 显示开始信息
        print("\n" + "=" * 60)
        print("🚀 开始生成智能大棚环境数据...")
        print("=" * 60)

        # 记录开始时间
        start_time = datetime.now()

        # 生成模拟数据
        log_operation("system", "INFO", "数据生成", "开始生成数据")
        print(f"\n🌱 正在生成 {days} 天的环境数据...")
        print(f"   起始日期: {start_date.strftime('%Y-%m-%d')}")
        print(f"   采样频率: 每 {interval_minutes} 分钟")

        generated_data = generate_data(start_date, days, interval_minutes)

        # 显示生成统计
        air_count = len(generated_data['air'])
        soil_moisture_count = len(generated_data['soil_moisture'])
        soil_nutrient_count = len(generated_data['soil_nutrient'])
        light_count = len(generated_data['light'])

        print(f"\n✅ 数据生成完成！统计信息：")
        print(f"   🌡️  空气温湿度数据: {air_count:,} 条")
        print(f"   💧 土壤湿度数据: {soil_moisture_count:,} 条")
        print(f"   🧪 土壤营养数据: {soil_nutrient_count:,} 条")
        print(f"   ☀️  光照强度数据: {light_count:,} 条")
        print(f"   📊 总数据量: {air_count + soil_moisture_count + soil_nutrient_count + light_count:,} 条")

        # 显示数据范围示例
        if air_count > 0:
            temps = [item[1] for item in generated_data['air']]
            humis = [item[2] for item in generated_data['air']]
            print(f"\n📈 数据范围预览：")
            print(f"   温度范围: {min(temps):.1f}°C ~ {max(temps):.1f}°C")
            print(f"   湿度范围: {min(humis):.1f}% ~ {max(humis):.1f}%")

        # 插入数据库
        log_operation("system", "INFO", "数据写入", "数据正在写入数据库")
        print(f"\n💾 正在将数据写入数据库...")

        insert_data_to_mysql(generated_data)

        # 记录结束时间
        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()

        print(f"\n🎉 数据生成和入库完成！")
        print(f"⏰ 总耗时: {duration:.1f} 秒")
        print(
            f"📊 平均处理速度: {(air_count + soil_moisture_count + soil_nutrient_count + light_count) / duration:.0f} 条/秒")
        print("=" * 60)

        log_operation("system", "INFO", "数据生成完成",
                      f"成功生成并插入 {air_count + soil_moisture_count + soil_nutrient_count + light_count} 条数据，耗时 {duration:.1f} 秒")

    except KeyboardInterrupt:
        print("\n\n❌ 用户中断了数据生成过程")
        log_operation("system", "WARNING", "数据生成中断", "用户中断了数据生成过程")
    except Exception as e:
        print(f"\n❌ 数据生成过程中发生错误: {str(e)}")
        log_operation("system", "ERROR", "数据生成错误", f"数据生成失败: {str(e)}")
        raise
