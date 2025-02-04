import numpy as np
import pandas as pd
from datetime import datetime
import io
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import random
import matplotlib.pyplot as plt
from matplotlib.backends.backend_agg import FigureCanvasAgg as FigureCanvas
import matplotlib.dates as mdates
from scipy.interpolate import UnivariateSpline  # 添加Smooth平滑拟合算法所需的库
import streamlit as st
from sqlalchemy import Column, Integer, Float, DateTime, String
from sqlalchemy.ext.declarative import declarative_base
import time  # 导入time模块

# 创建基类
Base = declarative_base()

class AirTemperatureHumidity(Base):
    __tablename__ = 'intelligent_farm_airtemperaturehumidity'  # 修改表名
    id = Column(Integer, primary_key=True)
    temperature = Column(Float)
    humidity = Column(Float)
    timestamp = Column(DateTime)

class SoilMoisture(Base):
    __tablename__ = 'intelligent_farm_soilmoisture'  # 修改表名
    id = Column(Integer, primary_key=True)
    value = Column(Float)
    timestamp = Column(DateTime)

class SoilNutrient(Base):
    __tablename__ = 'intelligent_farm_soilnutrient'  # 修改表名
    id = Column(Integer, primary_key=True)
    value = Column(Float)
    timestamp = Column(DateTime)

# MySQL数据库连接配置
engine = create_engine('mysql+pymysql://root:0000@db/intelligent_farm')
Session = sessionmaker(bind=engine)
session = Session()


def generate_random_data():
    """
    生成随机环境数据并保存到数据库。

    本函数生成随机的温度、湿度、土壤湿度和土壤养分值，
    并将这些数据连同当前时间戳一起保存到相应的数据库模型中。
    """
    # 生成随机环境数据
    temperature = round(random.uniform(20.0, 28.0), 2)  # 修改: 缩小温度范围
    humidity = round(random.uniform(40.0, 60.0), 2)  # 修改: 缩小湿度范围
    soil_moisture = round(random.uniform(30.0, 70.0), 2)  # 修改: 缩小土壤湿度范围
    soil_nutrient = round(random.uniform(1.0, 4.0), 2)  # 修改: 缩小土壤养分范围

    # 获取当前时间戳
    current_time = datetime.now()  # 添加: 获取当前时间戳

    # 创建数据对象
    air_temp_hum = AirTemperatureHumidity(temperature=temperature, humidity=humidity, timestamp=current_time)
    soil_moist = SoilMoisture(value=soil_moisture, timestamp=current_time)
    soil_nutri = SoilNutrient(value=soil_nutrient, timestamp=current_time)

    # 添加数据到数据库会话并提交
    session.add(air_temp_hum)
    session.add(soil_moist)
    session.add(soil_nutri)
    session.commit()


# Streamlit应用逻辑
def main():
    st.title("智能农场数据监控")

    # 数据展示
    st.header("最新数据")
    with session.begin():
        air_temp_hum = session.query(AirTemperatureHumidity).order_by(AirTemperatureHumidity.timestamp.desc()).first()
        soil_moist = session.query(SoilMoisture).order_by(SoilMoisture.timestamp.desc()).first()
        soil_nutri = session.query(SoilNutrient).order_by(SoilNutrient.timestamp.desc()).first()

    st.write(f"空气温度: {air_temp_hum.temperature} °C")
    st.write(f"空气湿度: {air_temp_hum.humidity} %")
    st.write(f"土壤湿度: {soil_moist.value} %")
    st.write(f"土壤养分: {soil_nutri.value}")
    st.write(f"时间戳: {air_temp_hum.timestamp}")

    # 添加数据导出逻辑
    st.header("数据导出")
    export_format = st.selectbox("选择导出格式", ["CSV", "JSON", "Excel"])

    # 添加时间范围选择器
    start_time = st.date_input("选择开始时间")
    end_time = st.date_input("选择结束时间")

    if st.button("导出数据"):
        # 根据时间范围查询数据
        query = session.query(
            AirTemperatureHumidity.timestamp.label('timestamp'),
            AirTemperatureHumidity.temperature,
            AirTemperatureHumidity.humidity,
            SoilMoisture.value.label('soil_moisture'),
            SoilNutrient.value.label('soil_nutrient')
        ).outerjoin(
            SoilMoisture, AirTemperatureHumidity.timestamp == SoilMoisture.timestamp
        ).outerjoin(
            SoilNutrient, AirTemperatureHumidity.timestamp == SoilNutrient.timestamp
        ).filter(
            AirTemperatureHumidity.timestamp >= start_time,
            AirTemperatureHumidity.timestamp <= end_time
        ).order_by(
            AirTemperatureHumidity.timestamp
        )

        data = query.all()
        df = pd.DataFrame(data, columns=[
            'timestamp',
            'temperature',
            'humidity',
            'soil_moisture',
            'soil_nutrient'
        ])

        df['timestamp'] = pd.to_datetime(df['timestamp'])

        # 调用data-visualization-tool.py中的data_analysis函数
        st.session_state['data'] = df

        if export_format == "CSV":
            csv = df.to_csv(index=False)
            st.download_button(
                label="下载CSV文件",
                data=csv,
                file_name='data.csv',
                mime='text/csv',
            )
        elif export_format == "JSON":
            json_str = df.to_json(orient='records')
            st.download_button(
                label="下载JSON文件",
                data=json_str,
                file_name='data.json',
                mime='application/json',
            )
        elif export_format == "Excel":
            excel = io.BytesIO()
            df.to_excel(excel, index=False)
            excel.seek(0)
            st.download_button(
                label="下载Excel文件",
                data=excel,
                file_name='data.xlsx',
                mime='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            )

    # 添加定时任务逻辑，每分钟生成一次随机数据并刷新页面
    while True:
        current_time = datetime.now()
        if 'last_generated_time' not in st.session_state or (current_time - st.session_state['last_generated_time']).total_seconds() >= 60:
            generate_random_data()
            st.session_state['last_generated_time'] = current_time
            st.success("随机数据已生成并保存到数据库中！", icon="✅")
        time.sleep(60)  # 每分钟检查一次

if __name__ == '__main__':
    main()  # 修改: 直接调用main函数
