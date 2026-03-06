from sqlalchemy import Column, Integer, Float, DateTime, String, Text, JSON, Computed, Index, Boolean
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()


class AirTemperatureHumidity(Base):
    __tablename__ = 'intelligent_farm_airtemperaturehumidity'
    id = Column(Integer, primary_key=True)
    temperature = Column(Float)
    humidity = Column(Float)
    timestamp = Column(DateTime)


class SoilMoisture(Base):
    __tablename__ = 'intelligent_farm_soilmoisture'
    id = Column(Integer, primary_key=True)
    value = Column(Float)
    timestamp = Column(DateTime)


class SoilNutrient(Base):
    __tablename__ = 'intelligent_farm_soilnutrient'
    id = Column(Integer, primary_key=True)
    value = Column(Float)
    timestamp = Column(DateTime)


class LightIntensity(Base):
    __tablename__ = 'intelligent_farm_light_intensity'
    id = Column(Integer, primary_key=True)
    value = Column(Float)
    timestamp = Column(DateTime)


class User(Base):
    __tablename__ = 'user'
    id = Column(Integer, primary_key=True, autoincrement=True)
    username = Column(String(255), nullable=False)
    password = Column(String(255), nullable=False)
    last_login_time = Column(DateTime, nullable=False)
    role = Column(String(50), nullable=False, default='user')
    # 添加管理员申请状态字段
    admin_request = Column(Boolean, nullable=False, default=False)
    # 添加管理员申请时间字段
    admin_request_time = Column(DateTime, nullable=True)


class OperationLog(Base):
    __tablename__ = 'operation_logs'
    id = Column(Integer, primary_key=True, autoincrement=True)
    log_time = Column(DateTime, nullable=False, primary_key=True)
    log_level = Column(String(10), nullable=False)
    username = Column(String(50))
    action_type = Column(String(50), nullable=False)
    action_details = Column(Text)
    details_json = Column(
        JSON,
        Computed(
            """JSON_OBJECT(
                'time_range', TRIM(SUBSTRING_INDEX(SUBSTRING_INDEX(action_details, '时间范围:', -1), ' ', 2)),
                'filename', NULLIF(SUBSTRING_INDEX(SUBSTRING_INDEX(action_details, '文件名:', -1), ' ', 1), ''),
                'metrics', JSON_OBJECT(
                    'temperature', NULLIF(SUBSTRING_INDEX(SUBSTRING_INDEX(action_details, '温度:', -1), ' ', 1), ''),
                    'humidity', NULLIF(SUBSTRING_INDEX(SUBSTRING_INDEX(action_details, '湿度:', -1), ' ', 1), ''),
                    'soil_moisture', NULLIF(SUBSTRING_INDEX(SUBSTRING_INDEX(action_details, '土壤湿度:', -1), ' ', 1), '')
                )
            )"""
        )
    )

    __table_args__ = (
        Index('idx_username', 'username'),
        Index('idx_action_type', 'action_type'),
    )
