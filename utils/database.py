import os

from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# 加载环境变量
load_dotenv()

# MySQL数据库连接配置
DATABASE_URL = os.getenv('DATABASE_URL')
engine = create_engine(DATABASE_URL)

# 创建会话工厂
Session = sessionmaker(bind=engine)


def get_session():
    """获取数据库会话对象"""
    return Session()
