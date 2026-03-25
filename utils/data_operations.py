import pandas as pd
from sqlalchemy import Index
from sqlalchemy.orm import sessionmaker

from models import AirTemperatureHumidity, SoilMoisture, SoilNutrient, LightIntensity
from utils.database import engine
from utils.logger import log_operation

Session = sessionmaker(bind=engine)

# 添加索引定义
INDEXES = [
    Index('idx_air_temperature_humidity_timestamp', AirTemperatureHumidity.timestamp),
    Index('idx_soil_moisture_timestamp', SoilMoisture.timestamp),
    Index('idx_soil_nutrient_timestamp', SoilNutrient.timestamp),
    Index('idx_light_intensity_timestamp', LightIntensity.timestamp)
]


def create_indexes():
    """创建必要的索引

    创建数据库表的索引，提高查询性能。

    Returns:
        None: 无返回值

    Raises:
        Exception: 创建索引失败时会捕获并记录错误信息
    """
    from sqlalchemy import inspect
    inspector = inspect(engine)

    for idx in INDEXES:
        # 检查索引是否已存在
        existing_indexes = inspector.get_indexes(idx.table.name)
        index_exists = any(existing_idx['name'] == idx.name for existing_idx in existing_indexes)

        if not index_exists:
            try:
                idx.create(bind=engine)
            except Exception as e:
                print(f"创建索引 {idx.name} 失败: {str(e)}")
                log_operation("system", "ERROR", "索引创建", f"创建索引 {idx.name} 失败: {str(e)}")


def fetch_data_in_bulk(session, start_time=None, end_time=None):
    """批量查询多个表的数据，减少数据库调用次数

    批量查询多个表的数据，使用LEFT JOIN优化查询性能，
    支持按时间范围过滤，返回包含多个表数据的DataFrame。

    Args:
        session: 数据库会话对象
        start_time: 查询开始时间（可选）
        end_time: 查询结束时间（可选）

    Returns:
        pd.DataFrame: 包含多个表数据的DataFrame
    """
    # 使用LEFT JOIN替代多个OUTER JOIN，优化查询性能
    query = session.query(
        AirTemperatureHumidity.timestamp.label('timestamp'),
        AirTemperatureHumidity.temperature,
        AirTemperatureHumidity.humidity,
        SoilMoisture.value.label('soil_moisture'),
        SoilNutrient.value.label('soil_nutrient'),
        LightIntensity.value.label('light_intensity')
    ).select_from(AirTemperatureHumidity). \
        outerjoin(SoilMoisture,
                  AirTemperatureHumidity.timestamp == SoilMoisture.timestamp). \
        outerjoin(SoilNutrient,
                  AirTemperatureHumidity.timestamp == SoilNutrient.timestamp). \
        outerjoin(LightIntensity,
                  AirTemperatureHumidity.timestamp == LightIntensity.timestamp)

    if start_time and end_time:
        query = query.filter(
            AirTemperatureHumidity.timestamp.between(start_time, end_time)
        )

    # 使用yield_per批量获取数据，减少内存使用
    data = query.yield_per(1000).order_by(AirTemperatureHumidity.timestamp).all()

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


# 在模块导入时创建索引
create_indexes()
