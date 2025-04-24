from sqlalchemy import Column, Integer, Float, DateTime, String
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
