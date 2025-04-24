import pandas as pd
from sqlalchemy.orm import sessionmaker

from models import AirTemperatureHumidity, SoilMoisture, SoilNutrient, LightIntensity
from utils.database import engine

Session = sessionmaker(bind=engine)


def fetch_data_in_bulk(session, start_time=None, end_time=None):
    """
    批量查询多个表的数据，减少数据库调用次数。
    :param session: 数据库会话对象
    :param start_time: 查询开始时间（可选）
    :param end_time: 查询结束时间（可选）
    :return: 包含多个表数据的DataFrame
    """
    query = session.query(
        AirTemperatureHumidity.timestamp.label('timestamp'),
        AirTemperatureHumidity.temperature,
        AirTemperatureHumidity.humidity,
        SoilMoisture.value.label('soil_moisture'),
        SoilNutrient.value.label('soil_nutrient'),
        LightIntensity.value.label('light_intensity')
    ).outerjoin(
        SoilMoisture, AirTemperatureHumidity.timestamp == SoilMoisture.timestamp
    ).outerjoin(
        SoilNutrient, AirTemperatureHumidity.timestamp == SoilNutrient.timestamp
    ).outerjoin(
        LightIntensity, AirTemperatureHumidity.timestamp == LightIntensity.timestamp
    )

    if start_time and end_time:
        query = query.filter(
            AirTemperatureHumidity.timestamp >= start_time,
            AirTemperatureHumidity.timestamp <= end_time
        )

    data = query.order_by(AirTemperatureHumidity.timestamp).all()
    df = pd.DataFrame(data, columns=[
        'timestamp',
        'temperature',
        'humidity',
        'soil_moisture',
        'soil_nutrient',
        'light_intensity'
    ])
    df['timestamp'] = pd.to_datetime(df['timestamp'])
    return df
