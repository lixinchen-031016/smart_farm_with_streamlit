"""数据库模型定义

定义智能农场系统的数据库模型，包括传感器数据、用户信息和操作日志等。

所有模型都继承自 SQLAlchemy 的 Base 类，用于 ORM 操作。
"""

from sqlalchemy import Column, Integer, Float, DateTime, String, Text, JSON, Computed, Index, Boolean
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()


class AirTemperatureHumidity(Base):
    """空气温湿度数据模型

    存储空气温度和湿度传感器数据。

    Attributes:
        id (int): 主键
        temperature (float): 温度值
        humidity (float): 湿度值
        timestamp (datetime): 数据采集时间
    """
    __tablename__ = 'intelligent_farm_airtemperaturehumidity'
    id = Column(Integer, primary_key=True)
    temperature = Column(Float)
    humidity = Column(Float)
    timestamp = Column(DateTime)


class SoilMoisture(Base):
    """土壤湿度数据模型

    存储土壤湿度传感器数据。

    Attributes:
        id (int): 主键
        value (float): 土壤湿度值
        timestamp (datetime): 数据采集时间
    """
    __tablename__ = 'intelligent_farm_soilmoisture'
    id = Column(Integer, primary_key=True)
    value = Column(Float)
    timestamp = Column(DateTime)


class SoilNutrient(Base):
    """土壤养分数据模型

    存储土壤养分传感器数据。

    Attributes:
        id (int): 主键
        value (float): 土壤养分值
        timestamp (datetime): 数据采集时间
    """
    __tablename__ = 'intelligent_farm_soilnutrient'
    id = Column(Integer, primary_key=True)
    value = Column(Float)
    timestamp = Column(DateTime)


class LightIntensity(Base):
    """光照强度数据模型

    存储光照强度传感器数据。

    Attributes:
        id (int): 主键
        value (float): 光照强度值
        timestamp (datetime): 数据采集时间
    """
    __tablename__ = 'intelligent_farm_light_intensity'
    id = Column(Integer, primary_key=True)
    value = Column(Float)
    timestamp = Column(DateTime)


class User(Base):
    """用户模型

    存储系统用户信息，包括登录凭证和权限信息。

    Attributes:
        id (int): 主键，自增
        username (str): 用户名
        password (str): 密码
        last_login_time (datetime): 最后登录时间
        role (str): 角色，默认为'user'
        admin_request (bool): 管理员申请状态，默认为False
        admin_request_time (datetime): 管理员申请时间，默认为None
    """
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
    """操作日志模型

    存储用户操作日志，支持日志级别、操作类型和详细信息的记录。

    Attributes:
        id (int): 主键，自增
        log_time (datetime): 日志时间，作为复合主键的一部分
        log_level (str): 日志级别，如'INFO', 'ERROR', 'WARNING'等
        username (str): 操作用户名
        action_type (str): 操作类型
        action_details (str): 操作详细信息
        details_json (dict): 计算列，从action_details中提取结构化信息

    Indexes:
        idx_username: 用户名索引
        idx_action_type: 操作类型索引
    """
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
