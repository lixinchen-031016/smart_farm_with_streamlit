import os

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from models import Base, AirTemperatureHumidity, SoilMoisture, SoilNutrient, LightIntensity, User, OperationLog
from utils.logger import log_operation

# 替换为你的数据库连接字符串
DATABASE_URI =  os.getenv('DATABASE_URL')

engine = create_engine(DATABASE_URI)
Session = sessionmaker(bind=engine)
session = Session()

try:
    # 清空不包含 user 和 operation_logs 的其他表
    session.query(AirTemperatureHumidity).delete()
    session.query(SoilMoisture).delete()
    session.query(SoilNutrient).delete()
    session.query(LightIntensity).delete()
    
    # 提交事务
    session.commit()
    log_operation("system", "INFO", "数据清理", "成功清空非用户和日志表的数据")
    print("非用户和日志表的数据已成功清空。")
except Exception as e:
    session.rollback()
    log_operation("system", "ERROR", "数据清理失败", f"发生错误: {e}")
    print(f"发生错误: {e}")
finally:
    session.close()